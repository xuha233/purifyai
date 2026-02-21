"""
自定义清理扫描器
扫描用户指定的自定义路径
"""
import os
from typing import List, Set
from PyQt5.QtCore import QObject, pyqtSignal
from pathlib import Path

from .models import ScanItem
from .whitelist import get_whitelist
from .risk_assessment import get_risk_assessment_system


class CustomScanner(QObject):
    """自定义路径扫描器"""
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
        self.risk_assessment_system = get_risk_assessment_system()

    def reload_ai_config(self):
        """Reload AI configuration from settings"""
        # RiskAssessmentSystem will reload from settings on next assess call
        pass

    def start_scan(self, paths: List[str], file_types: List[str] = None,
                  min_size: int = 0, max_size: int = None):
        """
        开始扫描自定义路径

        Args:
            paths: 要扫描的路径列表
            file_types: 文件类型过滤（如 ['*.tmp', '*.log']）
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
        """
        if self.is_running:
            return

        self.is_running = True
        self.is_cancelled = False
        self.scan_results.clear()

        # 转换文件模式
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

        self.scan_thread.start()

    def cancel_scan(self):
        """取消扫描"""
        self.is_cancelled = True
        self.scan_thread.cancel()

    def on_scan_complete(self, results):
        """扫描完成"""
        self.scan_results.extend(results)
        self.complete.emit(self.scan_results)
        self.is_running = False


class CustomScanThread(QObject):
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

    def run(self):
        """执行扫描"""
        results = []
        total = len(self.paths)

        for i, path in enumerate(self.paths):
            if self.is_cancelled:
                break

            self.progress.emit(f'Scanning ({i+1}/{total}): {path}')

            try:
                if os.path.exists(path):
                    # 扫描路径
                    path_results = self._scan_path(path)
                    results.extend(path_results)

                    # 发送发现的项目
                    for item in path_results:
                        self.item_found.emit(item)
            except Exception as e:
                self.error.emit(f'Error scanning {path}: {str(e)}')

        self.progress.emit('Scan complete!')
        self.complete.emit(results)

    def cancel(self):
        """取消扫描"""
        self.is_cancelled = True

    def _scan_path(self, path: str) -> List[ScanItem]:
        """扫描单个路径

        Args:
            path: 要扫描的路径

        Returns:
            List[ScanItem]: 扫描结果
        """
        results = []

        if os.path.isfile(path):
            # 扫描单个文件
            item = self._scan_file(path)
            if item:
                results.append(item)

        elif os.path.isdir(path):
            # 扫描目录
            results.extend(self._scan_directory(path))

        return results

    def _scan_file(self, file_path: str) -> ScanItem:
        """扫描单个文件

        Args:
            file_path: 文件路径

        Returns:
            ScanItem: 扫描项，不匹配则返回 None
        """
        try:
            # 检查白名单
            if self.scanner.whitelist.is_protected(file_path):
                return None

            # 检查文件名模式
            if self.file_patterns:
                file_name = os.path.basename(file_path)
                if not self._matches_file_pattern(file_name):
                    return None

            # 获取文件大小
            size = os.path.getsize(file_path)

            # 检查大小范围
            if self.min_size > 0 and size < self.min_size:
                return None
            if self.max_size is not None and size > self.max_size:
                return None

            # 使用集成的风险评估系统（包含规则引擎+AI）
            temp_item = ScanItem(file_path, size, 'file', os.path.basename(file_path), RiskLevel.SUSPICIOUS.value)
            assessment = self.scanner.risk_assessment_system.assess_item(temp_item)

            return ScanItem(
                path=file_path,
                size=size,
                item_type='file',
                description=assessment.reason.split('(')[0].strip(),  # 显示评估原因
                risk_level=assessment.risk_level.value
            )

        except Exception:
            return None

    def _scan_directory(self, dir_path: str) -> List[ScanItem]:
        """扫描目录

        Args:
            dir_path: 目录路径

        Returns:
            List[ScanItem]: 扫描结果
        """
        results = []

        try:
            # 遍历目录
            for entry in os.listdir(dir_path):
                if self.is_cancelled:
                    break

                entry_path = os.path.join(dir_path, entry)

                if os.path.isfile(entry_path):
                    item = self._scan_file(entry_path)
                    if item:
                        results.append(item)
                elif os.path.isdir(entry_path):
                    # 递归扫描子目录
                    results.extend(self._scan_directory(entry_path))

        except PermissionError:
            pass  # 跳过无权限的目录

        return results[0:1000]  # 限制返回数量

    def _matches_file_pattern(self, file_name: str) -> bool:
        """检查文件名是否匹配模式

        Args:
            file_name: 文件名

        Returns:
            bool: 是否匹配任一模式
        """
        import re

        for pattern in self.file_patterns:
            # 将通配符转换为正则表达式
            regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
            if re.match(regex, file_name, re.IGNORECASE):
                return True

        return False


def get_custom_scanner() -> CustomScanner:
    """获取自定义扫描器实例

    Returns:
        CustomScanner: 自定义扫描器实例
    """
    return CustomScanner()
