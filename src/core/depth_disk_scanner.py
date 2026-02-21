"""
深度磁盘扫描器 (Depth Disk Scanner)

参考 WinDirStat 的深度磁盘扫描逻辑，实现高效的磁盘文件扫描。
支持自定义路径扫描和磁盘全盘扫描。

功能:
- 基础 API 扫描 (MVP版本)
- 进度信号发射
- 目录跳过逻辑 (白名单/系统目录)
- 内存优化 (流式处理)
"""

import os
import time
from typing import List, Optional, Callable, Set
from pathlib import Path
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal, QThread
import psutil

from .scanner import ScanRiskAssessor
from .models import ScanItem
from .rule_engine import RiskLevel, get_rule_engine
from .whitelist import get_whitelist
from utils.logger import get_logger
from utils.logger import log_scan_event, log_performance

logger = get_logger(__name__)


# 系统目录跳过列表 (避免扫描系统关键目录)
SYSTEM_SKIP_DIRS = {
    # Windows 系统目录
    'C:\\Windows',
    'C:\\Program Files',
    'C:\\Program Files (x86)',
    'C:\\ProgramData',

    # 系统保留目录
    'System Volume Information',
    '$RECYCLE.BIN',
    '$Recycle.Bin',

    # 其他系统目录
    'Recovery',
    'Boot',
}

# 默认跳过的目录名称
DEFAULT_SKIP_NAMES = {
    'node_modules',
    '.git',
    '__pycache__',
    'venv',
    'env',
    '.venv',
    '.virtualenv',
    'site-packages',
}


@dataclass
class ScanProgress:
    """扫描进度信息"""
    current: int = 0
    total: int = 0
    current_path: str = ""
    found_items: int = 0
    skipped_items: int = 0
    start_time: float = 0

    @property
    def percentage(self) -> float:
        """计算进度百分比"""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100

    @property
    def elapsed_time(self) -> float:
        """计算已用时间（秒）"""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    @property
    def estimated_remaining(self) -> float:
        """估算剩余时间（秒）"""
        if self.current == 0 or self.elapsed_time == 0:
            return 0.0
        rate = self.current / self.elapsed_time
        if rate == 0:
            return 0.0
        return (self.total - self.current) / rate


class DepthDiskScannerThread(QThread):
    """深度磁盘扫描线程

    在独立线程中执行扫描操作，避免阻塞 UI。
    """

    # 信号
    progress = pyqtSignal(int, int, str)  # current, total, message
    item_found = pyqtSignal(object)        # ScanItem
    complete = pyqtSignal(list)           # List[ScanItem]
    error = pyqtSignal(str)               # error message

    def __init__(
        self,
        scan_path: str,
        include_hidden: bool = False,
        follow_symlinks: bool = False,
        min_size: int = 0,
        skip_dirs: Optional[Set[str]] = None,
        skip_system_dirs: bool = True
    ):
        """初始化扫描线程

        Args:
            scan_path: 扫描路径
            include_hidden: 是否包含隐藏文件
            follow_symlinks: 是否跟随符号链接
            min_size: 最小文件大小过滤（字节）
            skip_dirs: 要跳过的目录集合
            skip_system_dirs: 是否跳过系统目录
        """
        super().__init__()
        self.scan_path = scan_path
        self.include_hidden = include_hidden
        self.follow_symlinks = follow_symlinks
        self.min_size = min_size
        self.skip_dirs = skip_dirs or set()
        self.skip_system_dirs = skip_system_dirs

        self._is_running = False
        self._is_cancelled = False
        self._progress = ScanProgress(start_time=time.time())
        self._items: List[ScanItem] = []

        # 初始化风险评估
        self.risk_assessor = ScanRiskAssessor(use_ai_evaluation=True)
        self.rule_engine = get_rule_engine()
        self.whitelist = get_whitelist()

    def run(self):
        """执行扫描"""
        self._is_running = True
        self._is_cancelled = False
        self._items.clear()

        log_scan_event(logger, 'START', self.scan_path, scope='depth')

        try:
            # 预扫描 - 统计目录数量
            self._progress.total = self._count_directories(self.scan_path)
            logger.info(f"[SCAN_DEPTH] 预扫描完成，预计 {self._progress.total} 个目录")

            # 开始扫描
            self._scan_directory(self.scan_path)
            logger.info(f"[SCAN_DEPTH] 扫描完成，发现 {len(self._items)} 个清理项")

            logger.info(f"[SCAN_DEPTH] 跳过项目: {self._progress.skipped_items}")
            log_performance(logger, 'SCAN_DEPTH', len(self._items), self._progress.elapsed_time)

            self.complete.emit(self._items)

        except Exception as e:
            error_msg = f"扫描失败: {str(e)}"
            logger.error(f"[SCAN_DEPTH] {error_msg}", exc_info=True)
            self.error.emit(error_msg)
        finally:
            self._is_running = False
            log_scan_event(logger, 'END', self.scan_path, items=len(self._items))

    def _count_directories(self, path: str) -> int:
        """统计目录数量（含跳过检查）

        Args:
            path: 起始路径

        Returns:
            目录数量
        """
        count = 0
        try:
            for root, dirs, files in os.walk(path):
                count += 1
                # 过滤要跳过的目录，减少深度扫描
                if self._should_skip_dir(root):
                    dirs.clear()
        except PermissionError:
            logger.warning(f"[SCAN_DEPTH] 无权限访问: {path}")
        except Exception as e:
            logger.error(f"[SCAN_DEPTH] 统计目录出错 {path}: {e}")
        return count

    def _scan_directory(self, path: str, depth: int = 0):
        """递归扫描目录

        Args:
            path: 目录路径
            depth: 当前深度（用于限制深度）
        """
        if self._is_cancelled:
            return

        # 检查是否应该跳过此目录
        if self._should_skip_dir(path):
            self._progress.skipped_items += 1
            return

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if self._is_cancelled:
                        break

                    try:
                        if entry.is_file(follow_symlinks=self.follow_symlinks):
                            self._process_file(entry)
                        elif entry.is_dir(follow_symlinks=self.follow_symlinks):
                            # 检查是否应该跳过目录
                            if not self._should_skip_dir(entry.path):
                                self._scan_directory(entry.path, depth + 1)
                    except OSError as e:
                        logger.debug(f"[SCAN_DEPTH] 无法访问 {entry.name}: {e}")
                        continue

            # 更新进度
            self._progress.current += 1
            self._progress.current_path = path

            progress_pct = min(100, int(self._progress.percentage))
            message = f"正在扫描: {os.path.basename(path)}"
            self.progress.emit(self._progress.current, self._progress.total, message)

        except PermissionError:
            logger.warning(f"[SCAN_DEPTH] 无权限访问目录: {path}")
        except Exception as e:
            logger.error(f"[SCAN_DEPTH] 扫描目录出错 {path}: {e}")

    def _process_file(self, entry):
        """处理单个文件

        Args:
            entry: DirEntry 对象
        """
        # 过滤隐藏文件
        file_name = entry.name
        if not self.include_hidden and file_name.startswith('.'):
            return

        # 获取文件大小
        try:
            file_size = entry.stat().st_size
        except OSError:
            return

        # 过滤最小大小
        if self.min_size > 0 and file_size < self.min_size:
            return

        # 风险评估
        file_path = entry.path
        risk_level, description = self.risk_assessor.assess(
            file_path,
            description=f"文件: {file_name}",
            size=file_size,
            item_type='file'
        )

        # 检查白名单 - 如果是保护项则不添加
        if self.whitelist.is_protected(file_path):
            return

        # 创建 ScanItem
        try:
            item = ScanItem(
                path=file_path,
                description=description,
                size=file_size,
                item_type='file',
                risk_level=RiskLevel.from_value(risk_level)
            )
            self._items.append(item)
            self._progress.found_items += 1

            # 发射信号 (限制频率避免卡顿)
            if len(self._items) % 100 == 0:
                self.item_found.emit(item)

        except Exception as e:
            logger.debug(f"[SCAN_DEPTH] 创建 ScanItem 失败 {file_path}: {e}")

    def _should_skip_dir(self, path: str) -> bool:
        """检查是否应该跳过目录

        Args:
            path: 目录路径

        Returns:
            是否跳过
        """
        # 检查系统目录
        if self.skip_system_dirs:
            normalized_path = os.path.normpath(path).lower()
            for skip_path in SYSTEM_SKIP_DIRS:
                if normalized_path.startswith(os.path.normpath(skip_path).lower()):
                    return True

        # 检查默认跳过名称
        dir_name = os.path.basename(path)
        if dir_name in DEFAULT_SKIP_DIRS:
            return True

        # 检查自定义跳过目录
        normalized_path = os.path.normpath(path).lower()
        for skip_dir in self.skip_dirs:
            if normalized_path.startswith(os.path.normpath(skip_dir).lower()):
                return True

        return False

    def stop(self):
        """停止扫描"""
        self._is_cancelled = True
        logger.info("[SCAN_DEPTH] 扫描已停止")

    def is_running(self) -> bool:
        """检查是否正在运行

        Returns:
            是否正在运行
        """
        return self._is_running

    def get_progress(self) -> ScanProgress:
        """获取扫描进度

        Returns:
            ScanProgress 对象
        """
        return self._progress


class DepthDiskScanner(QObject):
    """深度磁盘扫描器 (MVP 版本)

    提供统一的扫描接口，封装扫描线程管理。
    支持自定义路径扫描、磁盘全盘扫描。

    使用方法:
        scanner = DepthDiskScanner()
        scanner.scan('C:\\Temp')

        scanner.scan_progress.connect(lambda c, t, m: print(f'{c}/{t}: {m}'))
        scanner.item_found.connect(lambda item: print(item.path))
        scanner.scan_complete.connect(lambda items: print(f'共 {len(items)} 项'))
    """

    # 信号
    scan_progress = pyqtSignal(int, int, str)  # current, total, message
    item_found = pyqtSignal(object)             # ScanItem
    scan_complete = pyqtSignal(list)           # List[ScanItem]
    scan_error = pyqtSignal(str)               # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_thread: Optional[DepthDiskScannerThread] = None
        self._scanned_items: List[ScanItem] = []
        self._config: Optional[dict] = None

    def scan(
        self,
        scan_path: str,
        include_hidden: bool = False,
        follow_symlinks: bool = False,
        min_size: int = 0,
        skip_dirs: Optional[Set[str]] = None,
        callback: Optional[Callable] = None
    ):
        """开始扫描

        Args:
            scan_path: 扫描路径
            include_hidden: 是否包含隐藏文件
            follow_symlinks: 是否跟随符号链接
            min_size: 最小文件大小过滤（字节）
            skip_dirs: 要跳过的目录集合
            callback: 扫描完成回调函数
        """
        self._config = {
            'scan_path': scan_path,
            'include_hidden': include_hidden,
            'follow_symlinks': follow_symlinks,
            'min_size': min_size,
            'skip_dirs': skip_dirs
        }

        # 验证路径
        if not os.path.exists(scan_path):
            error_msg = f"路径不存在: {scan_path}"
            logger.error(f"[SCAN_DEPTH] {error_msg}")
            self.scan_error.emit(error_msg)
            return

        if not os.path.isdir(scan_path):
            error_msg = f"路径不是目录: {scan_path}"
            logger.error(f"[SCAN_DEPTH] {error_msg}")
            self.scan_error.emit(error_msg)
            return

        # 创建扫描线程
        self._scan_thread = DepthDiskScannerThread(
            scan_path=scan_path,
            include_hidden=include_hidden,
            follow_symlinks=follow_symlinks,
            min_size=min_size,
            skip_dirs=skip_dirs,
            skip_system_dirs=True
        )

        # 连接信号
        self._scan_thread.progress.connect(lambda c, t, m: self.scan_progress.emit(c, t, m))
        self._scan_thread.item_found.connect(self._on_item_found)
        self._scan_thread.complete.connect(self._on_scan_complete)
        self._scan_thread.error.connect(lambda e: self.scan_error.emit(e))

        # 如果有回调函数，连接到完成信号
        if callback:
            self.scan_complete.connect(callback)

        # 启动线程
        self._scan_thread.start()
        logger.info(f"[SCAN_DEPTH] 扫描已启动: {scan_path}")

    def _on_item_found(self, item: ScanItem):
        """处理找到的项目

        Args:
            item: ScanItem 对象
        """
        self._scanned_items.append(item)
        self.item_found.emit(item)

    def _on_scan_complete(self, items: List[ScanItem]):
        """处理扫描完成

        Args:
            items: 扫描结果列表
        """
        self._scanned_items = items.copy()
        self.scan_complete.emit(items)
        logger.info(f"[SCAN_DEPTH] 扫描完成，共 {len(items)} 项")

    def stop(self):
        """停止当前扫描"""
        if self._scan_thread and self._scan_thread.is_running():
            self._scan_thread.stop()
            logger.info("[SCAN_DEPTH] 正在停止扫描...")

    def is_scanning(self) -> bool:
        """检查是否正在扫描

        Returns:
            是否正在扫描
        """
        return self._scan_thread is not None and self._scan_thread.is_running()

    def get_progress(self) -> dict:
        """获取扫描进度

        Returns:
            包含进度信息的字典
        """
        if self._scan_thread:
            progress = self._scan_thread.get_progress()
            return {
                'current': progress.current,
                'total': progress.total,
                'percentage': progress.percentage,
                'current_path': progress.current_path,
                'found_items': progress.found_items,
                'skipped_items': progress.skipped_items,
                'elapsed_time': progress.elapsed_time,
                'estimated_remaining': progress.estimated_remaining
            }
        return {
            'current': 0,
            'total': 0,
            'percentage': 0,
            'current_path': '',
            'found_items': 0,
            'skipped_items': 0,
            'elapsed_time': 0,
            'estimated_remaining': 0
        }

    def get_scanned_items(self) -> List[ScanItem]:
        """获取已扫描的项目列表

        Returns:
            ScanItem 列表
        """
        return self._scanned_items.copy()

    def get_config(self) -> Optional[dict]:
        """获取当前扫描配置

        Returns:
            扫描配置字典
        """
        return self._config.copy() if self._config else None


# 便利函数
def get_depth_disk_scanner() -> DepthDiskScanner:
    """获取深度磁盘扫描器实例

    Returns:
        DepthDiskScanner 实例
    """
    return DepthDiskScanner()


# 磁盘信息工具
def get_disk_info(path: str) -> dict:
    """获取磁盘信息

    Args:
        path: 文件系统路径

    Returns:
        磁盘信息字典
    """
    try:
        disk = psutil.disk_usage(path)
        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        }
    except Exception as e:
        logger.error(f"[SCAN_DEPTH] 获取磁盘信息失败 {path}: {e}")
        return {}

def get_available_drives() -> List[str]:
    """获取可用驱动器列表 (Windows)

    Returns:
        驱动器路径列表，如 ['C:\\', 'D:\\', ...]
    """
    try:
        drives = []
        for drive in psutil.disk_partitions():
            if 'fixed' in drive.opts or 'rw' in drive.opts:
                drives.append(drive.mountpoint)
        return drives
    except Exception as e:
        logger.error(f"[SCAN_DEPTH] 获取驱动器列表失败: {e}")
        return []
