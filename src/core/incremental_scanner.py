"""
增量扫描器
只扫描新增/修改的文件，大幅提升扫描速度
"""
import os
import json
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class ScanHistory:
    """扫描历史记录"""
    path: str
    last_scan_time: float  # Unix timestamp
    file_count: int = 0
    total_size: int = 0
    scan_duration: float = 0.0  # 秒
    last_error: str = ""


@dataclass
class IncrementalConfig:
    """增量扫描配置"""
    # 文件修改时间阈值（秒）- 超过此时间未修改的文件跳过
    mtime_threshold: float = 0.0  # 0 表示使用上次扫描时间
    # 最小扫描间隔（秒）- 防止频繁扫描
    min_scan_interval: float = 60.0  # 1分钟
    # 是否启用增量扫描
    enabled: bool = True
    # 历史文件路径
    history_file: str = ""


class IncrementalScanner:
    """
    增量扫描器 - 只扫描新增/修改的文件

    核心思路：
    1. 记录每个路径的上次扫描时间
    2. 只扫描 mtime > last_scan_time 的文件
    3. 持久化扫描历史到 JSON 文件
    """

    DEFAULT_HISTORY_FILE = "incremental_history.json"

    def __init__(self, config: IncrementalConfig = None):
        self.config = config or IncrementalConfig()
        self._history: Dict[str, ScanHistory] = {}
        self._lock = threading.Lock()
        self._initialized = False

        # 设置默认历史文件路径
        if not self.config.history_file:
            self.config.history_file = self._get_default_history_path()

        # 加载历史
        self._load_history()

    def _get_default_history_path(self) -> str:
        """获取默认历史文件路径"""
        try:
            # 在用户数据目录下创建
            data_dir = Path(os.getenv('APPDATA', '.')) / 'DiskClean'
            data_dir.mkdir(parents=True, exist_ok=True)
            return str(data_dir / self.DEFAULT_HISTORY_FILE)
        except Exception as e:
            logger.warning(f"无法创建数据目录: {e}")
            return self.DEFAULT_HISTORY_FILE

    def _load_history(self):
        """加载扫描历史"""
        try:
            if os.path.exists(self.config.history_file):
                with open(self.config.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = {
                        path: ScanHistory(**item)
                        for path, item in data.items()
                    }
                logger.info(f"加载扫描历史: {len(self._history)} 条记录")
        except Exception as e:
            logger.warning(f"加载扫描历史失败: {e}")
            self._history = {}

        self._initialized = True

    def _save_history(self):
        """保存扫描历史"""
        try:
            with open(self.config.history_file, 'w', encoding='utf-8') as f:
                data = {
                    path: asdict(history)
                    for path, history in self._history.items()
                }
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"保存扫描历史: {len(self._history)} 条记录")
        except Exception as e:
            logger.error(f"保存扫描历史失败: {e}")

    def get_last_scan_time(self, path: str) -> float:
        """
        获取路径的上次扫描时间

        Args:
            path: 扫描路径

        Returns:
            上次扫描时间（Unix timestamp），如果没有历史记录返回 0
        """
        with self._lock:
            normalized = self._normalize_path(path)
            if normalized in self._history:
                return self._history[normalized].last_scan_time
            return 0.0

    def scan_incremental(self, path: str,
                         scanner_func,
                         last_scan_time: float = None,
                         progress_callback=None) -> Tuple[List, Dict]:
        """
        增量扫描 - 只扫描新增/修改的文件

        Args:
            path: 扫描路径
            scanner_func: 实际扫描函数，签名为 (path, is_new_file) -> List[ScanItem]
            last_scan_time: 上次扫描时间，None 则自动获取
            progress_callback: 进度回调函数

        Returns:
            (扫描结果列表, 统计信息字典)
        """
        if not self.config.enabled:
            # 增量扫描禁用，执行完整扫描
            logger.info("增量扫描已禁用，执行完整扫描")
            return scanner_func(path, False), {}

        normalized = self._normalize_path(path)

        # 获取上次扫描时间
        if last_scan_time is None:
            last_scan_time = self.get_last_scan_time(path)

        # 检查最小扫描间隔
        current_time = datetime.now().timestamp()
        with self._lock:
            if normalized in self._history:
                last_time = self._history[normalized].last_scan_time
                if current_time - last_time < self.config.min_scan_interval:
                    logger.info(f"扫描间隔过短，跳过: {path}")
                    return [], {'skipped': True, 'reason': 'interval_too_short'}

        logger.info(f"开始增量扫描: {path}, 上次扫描: {datetime.fromtimestamp(last_scan_time) if last_scan_time > 0 else '无'}")

        # 执行增量扫描
        start_time = datetime.now().timestamp()
        results = []
        stats = {
            'total_files': 0,
            'new_files': 0,
            'skipped_files': 0,
            'errors': 0
        }

        try:
            # 扫描新增/修改文件
            for item in self._scan_path_incremental(path, last_scan_time, stats, progress_callback):
                results.append(item)

            # 执行自定义扫描函数
            if scanner_func:
                custom_results = scanner_func(path, True)
                if custom_results:
                    results.extend(custom_results)

        except Exception as e:
            logger.error(f"增量扫描失败: {e}")
            stats['errors'] += 1

        # 更新扫描历史
        scan_duration = datetime.now().timestamp() - start_time
        self.mark_scanned(path, len(results), sum(getattr(r, 'size', 0) for r in results), scan_duration)

        stats['scan_duration'] = scan_duration
        stats['speedup_ratio'] = self._calculate_speedup(stats)

        logger.info(f"增量扫描完成: 新增/修改 {stats['new_files']} 文件, 跳过 {stats['skipped_files']} 文件, 耗时 {scan_duration:.2f}s")

        return results, stats

    def _scan_path_incremental(self, path: str, last_scan_time: float,
                                stats: Dict, progress_callback=None):
        """
        扫描路径，只返回新增/修改的文件

        Yields:
            ScanItem 或文件路径
        """
        if not os.path.exists(path):
            return

        if os.path.isfile(path):
            # 单文件
            mtime = os.path.getmtime(path)
            if mtime > last_scan_time:
                stats['new_files'] += 1
                yield path
            else:
                stats['skipped_files'] += 1
            return

        # 目录扫描
        for root, dirs, files in os.walk(path):
            for filename in files:
                stats['total_files'] += 1

                try:
                    file_path = os.path.join(root, filename)
                    mtime = os.path.getmtime(file_path)

                    if mtime > last_scan_time:
                        stats['new_files'] += 1
                        yield file_path

                        if progress_callback and stats['new_files'] % 100 == 0:
                            progress_callback(f"扫描中: 已发现 {stats['new_files']} 个新文件")

                    else:
                        stats['skipped_files'] += 1

                except (OSError, PermissionError) as e:
                    stats['errors'] += 1
                    logger.debug(f"无法访问文件: {filename}, 错误: {e}")

    def mark_scanned(self, path: str, file_count: int = 0,
                     total_size: int = 0, scan_duration: float = 0.0,
                     error: str = ""):
        """
        标记路径扫描完成

        Args:
            path: 扫描路径
            file_count: 扫描文件数
            total_size: 总大小
            scan_duration: 扫描耗时
            error: 错误信息（如果有）
        """
        with self._lock:
            normalized = self._normalize_path(path)
            self._history[normalized] = ScanHistory(
                path=normalized,
                last_scan_time=datetime.now().timestamp(),
                file_count=file_count,
                total_size=total_size,
                scan_duration=scan_duration,
                last_error=error
            )

        self._save_history()

    def clear_history(self, path: str = None):
        """
        清除扫描历史

        Args:
            path: 指定路径，None 则清除全部
        """
        with self._lock:
            if path:
                normalized = self._normalize_path(path)
                if normalized in self._history:
                    del self._history[normalized]
            else:
                self._history.clear()

        self._save_history()
        logger.info(f"清除扫描历史: {path or '全部'}")

    def get_scan_stats(self, path: str) -> Optional[ScanHistory]:
        """获取路径的扫描统计"""
        with self._lock:
            normalized = self._normalize_path(path)
            return self._history.get(normalized)

    def get_all_stats(self) -> Dict[str, ScanHistory]:
        """获取所有扫描统计"""
        with self._lock:
            return dict(self._history)

    def _normalize_path(self, path: str) -> str:
        """规范化路径"""
        return os.path.normpath(os.path.abspath(path)).lower()

    def _calculate_speedup(self, stats: Dict) -> float:
        """计算加速比"""
        total = stats.get('total_files', 0)
        new_files = stats.get('new_files', 0)

        if total == 0 or new_files == 0:
            return 0.0

        # 理论加速比 = 总文件数 / 新文件数
        return total / new_files

    def is_file_modified(self, file_path: str, last_scan_time: float = None) -> bool:
        """
        检查文件是否在指定时间后被修改

        Args:
            file_path: 文件路径
            last_scan_time: 检查时间点，None 则使用路径的上次扫描时间

        Returns:
            True 如果文件是新的或被修改过
        """
        if last_scan_time is None:
            # 获取文件所在目录的上次扫描时间
            parent_dir = os.path.dirname(file_path)
            last_scan_time = self.get_last_scan_time(parent_dir)

        try:
            mtime = os.path.getmtime(file_path)
            return mtime > last_scan_time
        except OSError:
            return True  # 无法访问，视为新文件

    def get_new_files(self, path: str, last_scan_time: float = None) -> List[str]:
        """
        获取新增/修改的文件列表

        Args:
            path: 扫描路径
            last_scan_time: 上次扫描时间，None 则自动获取

        Returns:
            新增/修改的文件路径列表
        """
        if last_scan_time is None:
            last_scan_time = self.get_last_scan_time(path)

        new_files = []
        stats = {'total': 0, 'new': 0}

        for file_path in self._scan_path_incremental(path, last_scan_time, stats):
            new_files.append(file_path)

        logger.info(f"发现 {len(new_files)} 个新文件 (总文件数: {stats['total_files']})")
        return new_files

    def estimate_speedup(self, path: str) -> Dict:
        """
        预估增量扫描的加速效果

        Args:
            path: 扫描路径

        Returns:
            预估统计信息
        """
        last_scan_time = self.get_last_scan_time(path)

        if last_scan_time == 0:
            return {
                'is_first_scan': True,
                'estimated_speedup': 1.0,
                'message': '首次扫描，无加速效果'
            }

        total_files = 0
        new_files = 0

        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for filename in files:
                    total_files += 1
                    try:
                        file_path = os.path.join(root, filename)
                        if os.path.getmtime(file_path) > last_scan_time:
                            new_files += 1
                    except OSError:
                        pass

        if total_files == 0:
            return {
                'is_first_scan': False,
                'estimated_speedup': 1.0,
                'total_files': 0,
                'new_files': 0,
                'message': '目录为空'
            }

        speedup = total_files / new_files if new_files > 0 else float('inf')

        return {
            'is_first_scan': False,
            'estimated_speedup': speedup,
            'total_files': total_files,
            'new_files': new_files,
            'last_scan_time': datetime.fromtimestamp(last_scan_time).isoformat(),
            'message': f'预计加速 {speedup:.1f}x ({new_files}/{total_files} 文件需要扫描)'
        }


# 单例模式
_incremental_scanner_instance: Optional[IncrementalScanner] = None
_instance_lock = threading.Lock()


def get_incremental_scanner(config: IncrementalConfig = None) -> IncrementalScanner:
    """
    获取增量扫描器单例

    Args:
        config: 配置对象，仅在首次调用时使用

    Returns:
        IncrementalScanner 实例
    """
    global _incremental_scanner_instance

    if _incremental_scanner_instance is None:
        with _instance_lock:
            if _incremental_scanner_instance is None:
                _incremental_scanner_instance = IncrementalScanner(config)

    return _incremental_scanner_instance


def create_incremental_scanner(config: IncrementalConfig = None) -> IncrementalScanner:
    """
    创建新的增量扫描器实例（非单例）

    Args:
        config: 配置对象

    Returns:
        新的 IncrementalScanner 实例
    """
    return IncrementalScanner(config)
