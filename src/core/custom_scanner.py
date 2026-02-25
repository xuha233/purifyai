"""
自定义清理扫描器
扫描用户指定的自定义路径
支持增量扫描模式
"""
import os
import logging
from typing import List, Set, Tuple, Dict, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker
from pathlib import Path

from .models import ScanItem
from .rule_engine import get_rule_engine, RiskLevel
from .whitelist import get_whitelist
from .risk_assessment import get_risk_assessment_system
from .annotation_generator import AnnotationGenerator
from .incremental_scanner import get_incremental_scanner, IncrementalConfig

logger = logging.getLogger(__name__)


class CustomScanner(QObject):
    """自定义路径扫描器 - 使用AI智能评估（危险场景），支持增量扫描"""
    # Signals
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)
    scan_stats = pyqtSignal(dict)  # 扫描统计信号

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.scan_thread = None
        self.scan_results: List[ScanItem] = []
        self.whitelist = get_whitelist()
        self.rule_engine = get_rule_engine()
        self._ai_filter_enabled = False
        self._incremental_enabled = True  # 默认启用增量扫描

        # 增量扫描器
        try:
            self.incremental_scanner = get_incremental_scanner()
            logger.info("增量扫描器初始化成功")
        except Exception as e:
            logger.warning(f"增量扫描器初始化失败: {e}")
            self.incremental_scanner = None

        try:
            self.risk_assessment_system = get_risk_assessment_system()
            logger.info("风险评估系统初始化成功")
        except Exception as e:
            logger.warning(f"风险评估系统初始化失败: {e}")
            self.risk_assessment_system = None

        # 初始化批注生成器
        try:
            self.annotation_generator = AnnotationGenerator()
            logger.info("批注生成器初始化成功")
        except Exception as e:
            logger.warning(f"批注生成器初始化失败: {e}")
            self.annotation_generator = None

    def set_ai_filter_enabled(self, enabled: bool):
        """设置是否启用 AI 筛查"""
        self._ai_filter_enabled = enabled
        if self.risk_assessment_system:
            self.risk_assessment_system.enable_ai(enabled)

    def set_incremental_enabled(self, enabled: bool):
        """设置是否启用增量扫描"""
        self._incremental_enabled = enabled
        if self.incremental_scanner:
            self.incremental_scanner.config.enabled = enabled
        logger.info(f"增量扫描: {'启用' if enabled else '禁用'}")

    def is_incremental_enabled(self) -> bool:
        """检查增量扫描是否启用"""
        return self._incremental_enabled and self.incremental_scanner is not None

    def get_last_scan_time(self, path: str) -> float:
        """获取路径的上次扫描时间"""
        if self.incremental_scanner:
            return self.incremental_scanner.get_last_scan_time(path)
        return 0.0

    def clear_incremental_history(self, path: str = None):
        """清除增量扫描历史"""
        if self.incremental_scanner:
            self.incremental_scanner.clear_history(path)
            logger.info(f"清除增量扫描历史: {path or '全部'}")

    def estimate_scan_speedup(self, path: str) -> Dict:
        """预估增量扫描加速效果"""
        if self.incremental_scanner:
            return self.incremental_scanner.estimate_speedup(path)
        return {'estimated_speedup': 1.0, 'message': '增量扫描不可用'}

    def assess_item_risk(self, path: str, size: int, is_file: bool) -> Tuple[str, str]:
        """
        评估项目风险 - 在扫描期间只使用规则引擎，不调用AI

        Args:
            path: 文件/文件夹路径
            size: 大小
            is_file: 是否为文件

        Returns:
            (risk_level, description) 风险评估结果
        """
        # 1. 检查白名单
        if self.whitelist.is_protected(path):
            return RiskLevel.DANGEROUS.value, f'{os.path.basename(path)} (白名单保护)'

        description = os.path.basename(path)

        # 2. 使用规则引擎进行基础评估（扫描期间不调用 AI）
        risk_level = self.rule_engine.classify(path, size, None, is_file)

        # 3. 添加评估标签
        description = f'{description} (规则)'

        return risk_level.value, description

    def start_scan(self, paths: List[str], file_types: List[str] = None,
                  min_size: int = 0, max_size: int = None, incremental: bool = True):
        """
        开始扫描自定义路径

        Args:
            paths: 扫描路径列表
            file_types: 文件类型过滤
            min_size: 最小文件大小
            max_size: 最大文件大小
            incremental: 是否使用增量扫描（默认 True）
        """
        if self.is_running:
            return

        self.is_running = True
        self.is_cancelled = False
        self.scan_results.clear()

        self.file_patterns = file_types or []
        self.min_size = min_size
        self.max_size = max_size
        self._use_incremental = incremental and self._incremental_enabled

        self.scan_thread = CustomScanThread(
            self, paths, self.file_patterns, self.min_size, self.max_size,
            use_incremental=self._use_incremental
        )
        self.scan_thread.progress.connect(self.progress)
        self.scan_thread.item_found.connect(self.item_found)
        self.scan_thread.error.connect(self.error)
        self.scan_thread.complete.connect(self.on_scan_complete)

        # 启动扫描线程
        self.scan_thread.start()

    def cancel_scan(self):
        """取消扫描"""
        logger.info("自定义扫描器: 取消扫描被调用")
        self.is_cancelled = True
        if self.scan_thread:
            self.scan_thread.cancel()

    def on_scan_complete(self, results):
        """扫描完成"""
        self.scan_results.extend(results)
        self.complete.emit(self.scan_results)
        self.is_running = False


class CustomScanThread(QThread):
    """自定义扫描线程 - 支持增量扫描"""
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    def __init__(self, scanner: CustomScanner, paths: List[str],
                 file_patterns: List[str], min_size: int, max_size: int,
                 use_incremental: bool = False):
        super().__init__()
        self.scanner = scanner
        self.paths = paths
        self.file_patterns = file_patterns
        self.min_size = min_size
        self.max_size = max_size
        self.use_incremental = use_incremental
        self.is_cancelled = False
        self.mutex = QMutex()
        self.scan_stats = {
            'total_files': 0,
            'new_files': 0,
            'skipped_files': 0,
            'incremental_used': use_incremental
        }

    def run(self):
        """执行扫描"""
        import time
        results = []
        total = len(self.paths)
        start_time = time.time()

        logger.info(f"自定义扫描线程启动，路径数: {total}, 增量模式: {self.use_incremental}")

        for i, path in enumerate(self.paths):
            if self._is_cancelled():
                logger.info("扫描被取消")
                break

            self.progress.emit(f'扫描中 ({i+1}/{total}): {path}')
            logger.debug(f"扫描路径: {path}")

            try:
                if os.path.exists(path):
                    if self.use_incremental and self.scanner.incremental_scanner:
                        # 增量扫描模式
                        path_results = self._scan_path_incremental(path)
                    else:
                        # 完整扫描模式
                        path_results = self._scan_path(path)

                    results.extend(path_results)

                    for item in path_results:
                        # 检查是否在扫描过程中取消
                        if self._is_cancelled():
                            break
                        self.item_found.emit(item)
            except Exception as e:
                logger.error(f"扫描 {path} 失败: {e}")
                self.error.emit(f'Error scanning {path}: {str(e)}')

        # 检查是否被取消
        scan_duration = time.time() - start_time
        self.scan_stats['scan_duration'] = scan_duration
        self.scan_stats['result_count'] = len(results)

        if self._is_cancelled():
            self.progress.emit('扫描已取消')
            logger.info("扫描被取消，返回空结果")
            self.complete.emit([])
        else:
            self.progress.emit('扫描完成')
            logger.info(f"扫描完成，结果数: {len(results)}, 耗时: {scan_duration:.2f}s")
            if self.use_incremental:
                logger.info(f"增量扫描统计: 新文件 {self.scan_stats['new_files']}, 跳过 {self.scan_stats['skipped_files']}")
            self.complete.emit(results)

    def cancel(self):
        """取消扫描"""
        logger.info("自定义扫描线程: cancel 被调用")
        with QMutexLocker(self.mutex):
            self.is_cancelled = True

    def _is_cancelled(self) -> bool:
        """检查是否已取消（线程安全）"""
        with QMutexLocker(self.mutex):
            return self.is_cancelled

    def _scan_path(self, path: str, depth: int = 0, max_depth: int = 5) -> List[ScanItem]:
        """扫描单个路径"""
        results = []

        if depth > max_depth or self._is_cancelled():
            return results

        try:
            if os.path.isfile(path):
                item = self._scan_file(path)
                if item:
                    results.append(item)

            elif os.path.isdir(path):
                results.extend(self._scan_directory(path, depth, max_depth))

        except Exception as e:
            logger.warning(f"扫描路径失败 {path}: {e}")

        return results

    def _scan_path_incremental(self, path: str, depth: int = 0, max_depth: int = 5) -> List[ScanItem]:
        """
        增量扫描单个路径 - 只扫描新增/修改的文件

        Args:
            path: 扫描路径
            depth: 当前递归深度
            max_depth: 最大递归深度

        Returns:
            扫描结果列表
        """
        results = []

        if depth > max_depth or self._is_cancelled():
            return results

        # 获取上次扫描时间
        last_scan_time = self.scanner.incremental_scanner.get_last_scan_time(path)

        logger.debug(f"增量扫描 {path}, 上次扫描时间: {last_scan_time}")

        try:
            if os.path.isfile(path):
                # 单文件检查
                mtime = os.path.getmtime(path)
                if mtime > last_scan_time:
                    item = self._scan_file(path)
                    if item:
                        results.append(item)
                        self.scan_stats['new_files'] += 1
                else:
                    self.scan_stats['skipped_files'] += 1

            elif os.path.isdir(path):
                results.extend(self._scan_directory_incremental(path, last_scan_time, depth, max_depth))

        except Exception as e:
            logger.warning(f"增量扫描路径失败 {path}: {e}")

        # 标记扫描完成
        if not self._is_cancelled():
            self.scanner.incremental_scanner.mark_scanned(
                path,
                file_count=self.scan_stats['new_files'],
                total_size=sum(r.size for r in results if hasattr(r, 'size'))
            )

        return results

    def _scan_directory_incremental(self, dir_path: str, last_scan_time: float,
                                     depth: int, max_depth: int) -> List[ScanItem]:
        """
        增量扫描目录

        Args:
            dir_path: 目录路径
            last_scan_time: 上次扫描时间
            depth: 当前递归深度
            max_depth: 最大递归深度

        Returns:
            扫描结果列表
        """
        results = []

        try:
            for entry in os.listdir(dir_path):
                if self._is_cancelled():
                    break

                entry_path = os.path.join(dir_path, entry)

                try:
                    if os.path.isfile(entry_path):
                        self.scan_stats['total_files'] += 1
                        mtime = os.path.getmtime(entry_path)

                        if mtime > last_scan_time:
                            # 文件是新的或被修改过
                            item = self._scan_file(entry_path)
                            if item:
                                results.append(item)
                            self.scan_stats['new_files'] += 1
                        else:
                            # 跳过未修改的文件
                            self.scan_stats['skipped_files'] += 1

                    elif os.path.isdir(entry_path):
                        # 递归扫描子目录
                        sub_results = self._scan_path_incremental(entry_path, depth + 1, max_depth)
                        results.extend(sub_results)

                except (OSError, PermissionError) as e:
                    logger.debug(f"无法访问 {entry_path}: {e}")

                # 限制单次返回数量
                if len(results) >= 100:
                    break

        except PermissionError:
            pass
        except Exception as e:
            logger.debug(f"增量扫描目录失败 {dir_path}: {e}")

        return results[:100]

    def _scan_file(self, file_path: str) -> ScanItem or None:
        """扫描单个文件"""
        try:
            if self.scanner.whitelist.is_protected(file_path):
                return None

            if self.file_patterns:
                file_name = os.path.basename(file_path)
                if not self._matches_file_pattern(file_name):
                    return None

            size = os.path.getsize(file_path)

            if self.min_size > 0 and size < self.min_size:
                return None
            if self.max_size is not None and size > self.max_size:
                return None

            # 使用风险评估系统（包含AI评估）
            risk_level, description = self.scanner.assess_item_risk(
                path=file_path,
                size=size,
                is_file=True
            )

            # 不在扫描时生成批注，批注生成在 AI 评估时进行
            annotation = None

            return ScanItem(
                path=file_path,
                size=size,
                item_type='file',
                description=description,
                risk_level=risk_level,
                annotation=annotation
            )

        except Exception as e:
            logger.debug(f"扫描文件失败 {file_path}: {e}")
            return None

    def _scan_directory(self, dir_path: str, depth: int, max_depth: int) -> List[ScanItem]:
        """扫描目录"""
        results = []

        try:
            for entry in os.listdir(dir_path):
                if self._is_cancelled():
                    break

                entry_path = os.path.join(dir_path, entry)

                if os.path.isfile(entry_path):
                    item = self._scan_file(entry_path)
                    if item:
                        results.append(item)
                        # 限制单次返回数量
                        if len(results) >= 100:
                            break
                elif os.path.isdir(entry_path):
                    # 递归扫描子目录
                    sub_results = self._scan_path(entry_path, depth + 1, max_depth)
                    results.extend(sub_results)
                    if len(results) >= 100:
                        break

        except PermissionError:
            pass
        except Exception as e:
            logger.debug(f"扫描目录失败 {dir_path}: {e}")

        return results[:100]  # 限制返回数量

    def _matches_file_pattern(self, file_name: str) -> bool:
        """检查文件名是否匹配模式"""
        import re
        for pattern in self.file_patterns:
            regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
            if re.match(regex, file_name, re.IGNORECASE):
                return True
        return False


def get_custom_scanner() -> CustomScanner:
    """获取自定义扫描器实例"""
    return CustomScanner()
