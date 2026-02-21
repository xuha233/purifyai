"""
AppData 扫描器 v2 - 参考 AppDataCleaner 项目设计
"""
import os
import logging
from typing import List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import time
from pathlib import Path

from .models import ScanItem
from .rule_engine import get_rule_engine, RiskLevel
from .annotation_storage import AnnotationStorage

logger = logging.getLogger(__name__)


class AppDataScanner(QObject):
    """AppData 扫描器 v2 - 参考 AppDataCleaner 的优化设计"""
    # Signals
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    # 常见应用目录 - 参考 AppDataCleaner 的设计
    COMMON_APPS = {
        # 浏览器类
        'Google Chrome': 'safe',
        'Mozilla Firefox': 'safe',
        'Microsoft Edge': 'safe',
        'Brave': 'safe',
        'Opera': 'safe',
        'Vivaldi': 'safe',
        # 生产力工具
        'Microsoft Office': 'suspicious',
        'Adobe': 'suspicious',
        'Autodesk': 'suspicious',
        'Blizzard': 'suspicious',
        'Epic Games': 'suspicious',
        'Steam': 'suspicious',
        # 开发工具
        'JetBrains': 'suspicious',
        'Visual Studio Code': 'suspicious',
        'VSCode': 'safe',
        'Git': 'safe',
        'Node.js': 'suspicious',
        'Python': 'suspicious',
        # 通讯软件
        'WeChat': 'suspicious',
        'Tencent': 'suspicious',
        'QQ': 'suspicious',
        'Telegram': 'suspicious',
        'WeChat Files': 'suspicious',
        # 媒体播放器
        'VLC': 'suspicious',
        'Spotify': 'suspicious',
        'KuGou': 'safe',
        'Netease': 'suspicious',
    }

    # 缓存目录关键字 - 优先扫描
    CACHE_KEYWORDS = [
        'cache', 'Cache', 'CACHE',
        'temp', 'Temp', 'tmp', 'Tmp',
        'log', 'Log', 'logs', 'Logs',
        'thumbnail', 'Thumbnail', 'thumbs', 'thumb',
        'cache2', 'Cache2',
        'gpucache', 'GPUCache',
        'codecache', 'CodeCache',
        'service worker', 'Service Worker',
        'mediacache', 'Media Cache',
        'shadercache', 'ShaderCache',
        'blob_storage', 'Blob Storage',
        'IndexedDB',
        'Local Storage',
        'Cookies',
        'Session Storage',
        'Web Storage'
    ]

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.scan_thread = None
        self.scan_results: List[ScanItem] = []
        self.annotation_storage = AnnotationStorage()

    def reload_ai_config(self):
        """重新加载AI配置"""
        # v2 扫描器不需要重新加载配置
        pass

    def start_scan(self, scan_types: List[str] = None):
        """开始扫描 AppData 目录

        Args:
            scan_types: 扫描类型列表 ['roaming', 'local', 'local_low']
        """
        if self.is_running:
            return

        self.is_running = True
        self.is_cancelled = False
        self.scan_results = []

        if scan_types is None:
            scan_types = ['roaming', 'local', 'local_low']

        self.scan_thread = AppDataScanThread(
            self,
            scan_types,
            self.CACHE_KEYWORDS,
            self.COMMON_APPS
        )
        self.scan_thread.progress.connect(self.progress.emit)
        self.scan_thread.item_found.connect(self.item_found.emit)
        self.scan_thread.error.connect(self.error.emit)
        self.scan_thread.complete.connect(self.complete.emit)

        self.scan_thread.start()

    def cancel_scan(self):
        """取消扫描"""
        self.is_cancelled = True
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.cancel()


class AppDataScanThread(QThread):
    """AppData 扫描线程 - 优化版"""
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqt.emit(list)

    def __init__(self, scanner: AppDataScanner, scan_types: List[str],
                 cache_keywords: List[str], common_apps: dict):
        super().__init__()
        self.scanner = scanner
        self.scan_types = scan_types
        self.cache_keywords = cache_keywords
        self.common_apps = common_apps
        self.is_cancelled = False

    def cancel(self):
        """取消扫描"""
        self.is_cancelled = True

    def run(self):
        """执行扫描"""
        results = []
        total_dirs = 0

        logger.info(f"AppData 扫描线程启动，扫描类型: {self.scan_types}")

        try:
            # 统计总目录数
            for folder_type in self.scan_types:
                try:
                    dirs = self._list_appdata_dirs(folder_type)
                    total_dirs += len(dirs)
                except Exception as e:
                    logger.warning(f"统计 {folder_type} 目录失败: {e}")

            current = 0
            for folder_type in self.scan_types:
                if self.is_cancelled:
                    break

                self.progress.emit(f'扫描 {folder_type}...')
                logger.debug(f"开始扫描 {folder_type} 目录")

                try:
                    dir_items = self._list_appdata_dirs(folder_type)

                    # 分为缓存目录和其他目录
                    cache_dirs = []
                    other_dirs = []

                    for dir_name, dir_path in dir_items:
                        if self.is_cancelled:
                            break

                        folder_lower = dir_name.lower()
                        if any(kw.lower() in folder_lower for kw in self.cache_keywords):
                            cache_dirs.append((dir_name, dir_path))
                        else:
                            other_dirs.append((dir_name, dir_path))

                    # 扫描缓存目录（更安全）
                    for dir_name, dir_path in cache_dirs[:100]:  # 增加数量限制
                        if self.is_cancelled:
                            break

                        try:
                            size = self._calculate_folder_size(dir_path)
                            if size > 0:
                                item = self._create_scan_item(
                                    dir_path, size, folder_type, is_cache=True
                                )
                                results.append(item)
                                self.item_found.emit(item)
                                current += 1
                                self.progress.emit(
                                    f'扫描中 ({current}/{total_dirs}): {dir_name}'
                                )
                        except Exception as e:
                            logger.debug(f"扫描缓存目录失败 {dir_path}: {e}")

                    # 扫描部分其他重要目录
                    for dir_name, dir_path in other_dirs[:100]:  # 增加数量限制
                        if self.is_cancelled:
                            break

                        try:
                            size = self._calculate_folder_size(dir_path)
                            if size > 1 * 1024 * 1024:  # 大于 1MB 的才扫描
                                item = self._create_scan_item(
                                    dir_path, size, folder_type, is_cache=False
                                )
                                results.append(item)
                                self.item_found.emit(item)
                                current += 1
                                self.progress.emit(
                                    f'扫描中 ({current}/{total_dirs}): {dir_name}'
                                )
                        except Exception as e:
                            logger.debug(f"扫描目录失败 {dir_path}: {e}")

                except Exception as e:
                    logger.error(f"扫描 {folder_type} 失败: {e}")

            logger.info(f"AppData 扫描完成，共发现 {len(results)} 个项目")

        except Exception as e:
            logger.error(f"AppData 扫描异常: {e}")
            self.error.emit(f"扫描失败: {str(e)}")

        self.complete.emit(results)
        self.scanner.is_running = False

    def _list_appdata_dirs(self, folder_type: str) -> List[Tuple[str, str]]:
        """列出指定类型的 AppData 目录"""
        dirs = []

        # 参考 AppDataCleaner 的目录获取方式
        if folder_type == 'roaming':
            appdata_path = os.environ.get('APPDATA', '')
        elif folder_type == 'local':
            appdata_path = os.environ.get('LOCALAPPDATA', '')
        elif folder_type == 'local_low':
            # LocalLow 需要从 APPDATA 推导
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                from pathlib import Path
                appdata_path = str(Path(appdata).parent / 'LocalLow')
        else:
            return dirs

        if not appdata_path or not os.path.exists(appdata_path):
            return dirs

        try:
            entries = sorted(os.listdir(appdata_path), key=str.lower)
            for entry in entries:
                if self.is_cancelled:
                    break
                entry_path = os.path.join(appdata_path, entry)
                if os.path.isdir(entry_path):
                    dirs.append((entry, entry_path))
        except Exception as e:
            logger.warning(f"列出 {folder_type} 目录失败: {e}")

        return dirs

    def _create_scan_item(self, path: str, size: int, folder_type: str, is_cache: bool) -> ScanItem:
        """创建扫描项"""
        name = os.path.basename(path)
        lower_name = name.lower()

        # 评估风险
        risk_level, description = self._assess_risk(name, path, size, is_cache)

        return ScanItem(
            path=path,
            size=size,
            item_type='directory',
            description=description,
            risk_level=risk_level
        )

    def _assess_risk(self, name: str, path: str, size: int, is_cache: bool) -> Tuple[str, str]:
        """评估风险等级 - 参考 AppDataCleaner 的设计

        Args:
            name: 目录名
            path: 完整路径
            size: 大小(字节)
            is_cache: 是否为缓存目录

        Returns:
            (risk_level, description)
        """
        lower_name = name.lower()

        # 应用风险评估
        if not is_cache:
            for app_name in self.common_apps:
                if app_name.lower() in lower_name:
                    if name in ['VSCode', 'Google', 'Git', 'Tencent', 'Netease', 'KuGou']:
                        return RiskLevel.SAFE.value, f'{name} (可清理缓存/临时文件)'
                    else:
                        return RiskLevel.SUSPICIOUS.value, f'{name} (应用数据-需审)'

        # 缓存目录评估
        if is_cache:
            # 检查是否包含已知应用的缓存
            for app_name in self.common_apps:
                if app_name.lower() in lower_name:
                    if name in ['VSCode', 'Google', 'Git', 'Tencent', 'Netease', 'KuGou',
                         'MediaMonkey', 'foobar2000']:
                        return RiskLevel.SAFE.value, f'{name} (浏览数据可清理)'

            # 检查缓存关键词
            safe_cache_keywords = ['cache', 'temp', 'log', 'thumb', 'service worker',
                                   'mediacache', 'shadercache', 'blob', 'cookies']
            if any(kw in lower_name for kw in safe_cache_keywords):
                return RiskLevel.SAFE.value, f'{name} (缓存/临时文件)'

            # 小缓存直接安全
            if size < 50 * 1024 * 1024:  # 小于 50MB
                return RiskLevel.SAFE.value, f'{name} (小缓存可清理)'

            return RiskLevel.SAFE.value, f'{name} (缓存目录-可清理)'

        # 非缓存目录评估
        # 危险/疑似关键词
        dangerous_keywords = [
            'user data', 'database', 'db', 'save', 'backup', 'profile',
            'settings', 'config', 'preferences', 'extension', 'plugin',
            'sync', 'auth', 'login', 'credential', 'token', 'cookie'
        ]

        suspicious_keywords = [
            'data', 'storage', 'download', 'upload', 'history', 'logs'
        ]

        # 先检查危险关键字
        for kw in dangerous_keywords:
            if kw in lower_name:
                return RiskLevel.DANGEROUS.value, f'{name} (包含敏感数据)'

        # 检查疑似关键字
        for kw in suspicious_keywords:
            if kw in lower_name:
                return RiskLevel.SUSPICIOUS.value, f'{name} (需AI评估)'

        # 小目录默认安全
        if size < 1024 * 1024:
            return RiskLevel.SAFE.value, f'{name} (小文件)'

        # 大目录未知类型
        return RiskLevel.SUSPICIOUS.value, f'{name} (待评估)'

    def _calculate_folder_size(self, path: str) -> int:
        """计算文件夹大小 - 递归实现

        Args:
            path: 文件夹路径

        Returns:
            大小(字节)
        """
        try:
            size = 0
            for entry in os.scandir(path):
                if self.is_cancelled:
                    return -1

                if entry.is_file(follow_symlinks=False):
                    try:
                        size += entry.stat().st_size
                    except (OSError, PermissionError):
                        pass
                elif entry.is_dir(follow_symlinks=False):
                    # 递归计算子目录大小
                    sub_size = self._calculate_folder_size(entry.path)
                    if sub_size >= 0:
                        size += sub_size

            return size
        except (OSError, PermissionError) as Exception:
            return 0
        except Exception:
            return 0
