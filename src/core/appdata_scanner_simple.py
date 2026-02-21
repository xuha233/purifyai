"""
AppData 扫描器 - 简化稳定版
作为系统清理的子扫描功能存在
"""
import os
from typing import List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from .models import ScanItem
from .rule_engine import RiskLevel

# 完整的缓存关键词列表
CACHE_KEYWORDS = [
    'cache', 'Cache', 'CACHE',
    'temp', 'Temp', 'tmp', 'Tmp',
    'log', 'Log', 'logs', 'Logs',
    'thumbnail', 'Thumbnail', 'thumbnails',
    'cache2', 'Code Cache', 'GPUCache',
    'ShaderCache', 'shader_cache',
    'DawnCache', 'dawn_cache',
    'Service Worker', 'ServiceWorker',
    'IndexedDB', 'indexeddb'
]

# 文件扩展名缓存
CACHE_FILE_EXTENSIONS = [
    '.log', '.tmp', '.temp', '.cache',
    '.crdownload', '.opdownload',
    '.part', '.download'
]

def format_file_size_small(size: int) -> str:
    """格式化小文件大小"""
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size // 1024}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size // (1024 * 1024)}MB"
    else:
        return f"{size // (1024 * 1024 * 1024)}GB"


class AppDataScanThread(QThread):
    """AppData 扫描线程"""
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    def __init__(self, scan_types: List[str], scan_depth: int = 3):
        super().__init__()
        self.scan_types = scan_types
        self.is_cancelled = False
        self.results = []
        self.scan_depth = scan_depth
        self.mutex = QMutex()

        # 重要应用列表（评估为疑似而非安全）
        self.important_apps = [
            'google', 'microsoft', 'adobe', 'autodesk',
            'blizzard', 'epic', 'electron', 'code',
            'vscode', 'nodejs', 'python', 'maven', 'gradle',
            'spotify', 'discord', 'slack', 'telegram', 'zoom'
        ]

    def run(self):
        """执行扫描"""
        try:
            logger.info(f"AppData 扫描线程启动，扫描类型: {self.scan_types}, 深度: {self.scan_depth}")

            for i, scan_type in enumerate(self.scan_types):
                if self._is_cancelled():
                    break

                self.progress.emit(f'扫描中 {scan_type}... ({i+1}/{len(self.scan_types)})')
                logger.info(f"开始扫描 {scan_type}")

                # 获取路径
                if scan_type.lower() == 'roaming':
                    base_path = os.environ.get('APPDATA', '')
                elif scan_type.lower() == 'local':
                    base_path = os.environ.get('LOCALAPPDATA', '')
                elif scan_type.lower() == 'local_low':
                    base_path = os.environ.get('LOCALAPPDATA', '')
                    if base_path:
                        base_path = os.path.join(base_path, 'Low')
                else:
                    continue

                logger.info(f"{scan_type} 路径: {base_path}")
                items = self._scan_directory(base_path, scan_type)
                self.results.extend(items)
                logger.info(f"{scan_type} 找到 {len(items)} 个项目")

            logger.info(f"扫描完成，总项目: {len(self.results)}")

            if not self._is_cancelled():
                self.progress.emit('AppData 扫描完成')
                self.complete.emit(self.results)
            else:
                self.progress.emit('扫描已取消')
                self.complete.emit([])
        except Exception as e:
            logger.error(f"扫描异常: {e}")
            self.error.emit(f'扫描错误: {str(e)}')
            self.complete.emit([])

    def cancel(self):
        """取消扫描"""
        logger.info("AppData scan thread: cancel called")
        with QMutexLocker(self.mutex):
            self.is_cancelled = True

    def _is_cancelled(self) -> bool:
        """检查是否已取消（线程安全）"""
        with QMutexLocker(self.mutex):
            return self.is_cancelled

    def _scan_directory(self, base_path: str, scan_type: str) -> List[ScanItem]:
        """扫描单个目录"""
        if not base_path or not os.path.exists(base_path):
            logger.warning(f"路径不存在: {base_path}")
            return []

        results = []

        try:
            logger.info(f"开始深度扫描: {base_path}, 深度: {self.scan_depth}")
            # 先收集缓存文件夹
            cache_folders = []
            other_folders = []
            large_files = []

            try:
                entries = sorted(os.listdir(base_path), key=str.lower)
            except (PermissionError, OSError):
                return results

            for folder_name in entries:
                if self._is_cancelled():
                    break

                entry_path = os.path.join(base_path, folder_name)

                try:
                    if os.path.isdir(entry_path):
                        if any(kw in folder_name.lower() for kw in CACHE_KEYWORDS):
                            cache_folders.append(entry_path)
                        else:
                            # 其他文件夹，但限制数量
                            if len(other_folders) < 100:  # 最多扫描100个其他文件夹
                                other_folders.append(entry_path)
                except (PermissionError, OSError):
                    continue

            logger.info(f"找到 {len(cache_folders)} 个缓存文件夹, {len(other_folders)} 个其他文件夹")

            # 优先扫描缓存文件夹（更安全）
            for folder_path in cache_folders:
                if self._is_cancelled():
                    break

                folder_results = self._scan_folder(folder_path, 0)
                results.extend(folder_results)

            # 扫描其他文件夹（限制数量）
            for folder_path in other_folders:
                if self._is_cancelled():
                    break

                # 快速检查文件夹大小
                size = self._get_directory_size_fast(folder_path, 2)
                if size > 1024 * 1024:  # 大于 1MB
                    folder_results = self._scan_folder(folder_path, 0)
                    results.extend(folder_results)

            logger.info(f"深度扫描完成: {base_path}, 找到 {len(results)} 个项目")
        except Exception as e:
            logger.error(f"扫描目录失败 {base_path}: {e}")

        return results

    def _scan_folder(self, folder_path: str, depth: int) -> List[ScanItem]:
        """扫描单个文件夹"""
        if self._is_cancelled():
            return []

        if depth > self.scan_depth:
            return []

        results = []
        folder_name = os.path.basename(folder_path)

        try:
            # 获取文件夹大小
            size = self._get_directory_size_fast(folder_path, self.scan_depth - depth)

            if size <= 0:
                return results

            # 风险评估
            lower_name = folder_name.lower()
            is_cache = any(kw in folder_name for kw in CACHE_KEYWORDS)

            if is_cache:
                # 缓存文件夹
                if any(app in lower_name for app in self.important_apps):
                    risk_level = RiskLevel.SUSPICIOUS.value
                    description = f'{folder_name} (应用缓存)'
                else:
                    risk_level = RiskLevel.SAFE.value
                    description = f'{folder_name} (缓存-安全)'
            else:
                # 普通文件夹
                risk_level = RiskLevel.SUSPICIOUS.value
                description = f'{folder_name} (需AI评估)'

            scan_item = ScanItem(folder_path, size, 'directory', description, risk_level)
            results.append(scan_item)
            self.item_found.emit(scan_item)

            # 查找大文件（>10MB）
            large_file_results = self._scan_large_files(folder_path, depth)
            results.extend(large_file_results)

        except (PermissionError, OSError):
            pass

        return results

    def _scan_large_files(self, folder_path: str, depth: int) -> List[ScanItem]:
        """扫描大文件（>10MB）"""
        if depth > self.scan_depth:
            return []

        if self._is_cancelled():
            return []

        results = []
        large_threshold = 10 * 1024 * 1024  # 10MB

        try:
            for entry in os.scandir(folder_path):
                if self._is_cancelled():
                    break

                try:
                    if entry.is_file():
                        if entry.path.endswith(tuple(CACHE_FILE_EXTENSIONS)):
                            # 缓存文件，不限制大小
                            file_size = entry.stat().st_size
                            if file_size > 1024:  # 大于 1KB
                                file_name = os.path.basename(entry.path)
                                scan_item = ScanItem(
                                    entry.path, file_size, 'file',
                                    f'{file_name} (缓存文件)',
                                    RiskLevel.SAFE.value
                                )
                                results.append(scan_item)
                                self.item_found.emit(scan_item)
                        elif entry.stat().st_size > large_threshold:
                            # 大文件
                            file_name = os.path.basename(entry.path)
                            scan_item = ScanItem(
                                entry.path, entry.stat().st_size, 'file',
                                f'{file_name} (大文件)',
                                RiskLevel.SUSPICIOUS.value
                            )
                            results.append(scan_item)
                            self.item_found.emit(scan_item)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass

        return results

    def get_cache_keywords(self):
        """获取缓存关键词列表"""
        return CACHE_KEYWORDS

    def get_cache_file_extensions(self):
        """获取缓存文件扩展名列表"""
        return CACHE_FILE_EXTENSIONS

    def _get_directory_size_fast(self, path: str, max_subtree_depth: int) -> int:
        """快速获取目录大小（限制子树深度）"""
        total = 0
        try:
            for entry in os.scandir(path):
                if self._is_cancelled():
                    return total

                try:
                    if entry.is_file():
                        total += entry.stat().st_size
                    elif entry.is_dir() and max_subtree_depth > 0:
                        # 递归但限制深度
                        total += self._get_directory_size_fast(entry.path, max_subtree_depth - 1)
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass

        return total


class AppDataScanner(QObject):
    """AppData 扫描器 - 封装类"""
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.scan_thread = None
        self.is_running = False
        self.default_scan_depth = 3  # 默认扫描深度

    def set_scan_depth(self, depth: int):
        """设置扫描深度"""
        self.default_scan_depth = depth
        logger.info(f"AppData 扫描深度设置为: {depth}")

    def reload_ai_config(self):
        """不需要 AI 配置"""
        pass

    def start_scan(self, scan_types: List[str] = None):
        """开始扫描"""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"启动 AppData 扫描，类型: {scan_types}, is_running: {self.is_running}")

        if scan_types is None:
            scan_types = ['roaming', 'local', 'local_low']

        self.scan_thread = AppDataScanThread(scan_types, self.default_scan_depth)
        self.scan_thread.progress.connect(self.progress)
        self.scan_thread.item_found.connect(self.item_found)
        self.scan_thread.error.connect(self.error)
        self.scan_thread.complete.connect(self._on_complete)
        self.scan_thread.start()

    def _on_complete(self, results):
        """扫描完成"""
        logger.info(f"扫描线程完成，结果数: {len(results)}")
        self.is_running = False
        self.complete.emit(results)

    def cancel_scan(self):
        """取消扫描"""
        logger.info("取消扫描被调用")
        if self.scan_thread:
            self.scan_thread.cancel()
        self.is_running = False
