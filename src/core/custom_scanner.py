"""
自定义清理扫描器
扫描用户指定的自定义路径
"""
import os
import logging
from typing import List, Set, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker
from pathlib import Path

from .models import ScanItem
from .rule_engine import get_rule_engine, RiskLevel
from .whitelist import get_whitelist
from .risk_assessment import get_risk_assessment_system
from .annotation_generator import AnnotationGenerator

logger = logging.getLogger(__name__)


class CustomScanner(QObject):
    """自定义路径扫描器 - 使用AI智能评估（危险场景）"""
    # Signals
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.scan_thread = None
        self.scan_results: List[ScanItem] = []
        self.whitelist = get_whitelist()
        self.rule_engine = get_rule_engine()
        self._ai_filter_enabled = False
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
                  min_size: int = 0, max_size: int = None):
        """开始扫描自定义路径"""
        if self.is_running:
            return

        self.is_running = True
        self.is_cancelled = False
        self.scan_results.clear()

        self.file_patterns = file_types or []
        self.min_size = min_size
        self.max_size = max_size

        self.scan_thread = CustomScanThread(
            self, paths, self.file_patterns, self.min_size, self.max_size
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
    """自定义扫描线程"""
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    def __init__(self, scanner: CustomScanner, paths: List[str],
                 file_patterns: List[str], min_size: int, max_size: int):
        super().__init__()
        self.scanner = scanner
        self.paths = paths
        self.file_patterns = file_patterns
        self.min_size = min_size
        self.max_size = max_size
        self.is_cancelled = False
        self.mutex = QMutex()

    def run(self):
        """执行扫描"""
        results = []
        total = len(self.paths)

        logger.info(f"自定义扫描线程启动，路径数: {total}")

        for i, path in enumerate(self.paths):
            if self._is_cancelled():
                logger.info("扫描被取消")
                break

            self.progress.emit(f'扫描中 ({i+1}/{total}): {path}')
            logger.debug(f"扫描路径: {path}")

            try:
                if os.path.exists(path):
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
        if self._is_cancelled():
            self.progress.emit('扫描已取消')
            logger.info("扫描被取消，返回空结果")
            self.complete.emit([])
        else:
            self.progress.emit('扫描完成')
            logger.info(f"扫描完成，结果数: {len(results)}")
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
