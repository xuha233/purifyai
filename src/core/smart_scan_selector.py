"""
智能扫描选择器

根据扫描类型选择最优的扫描器进行扫描。
支持混合扫描策略，根据场景自动选择合适的扫描器。
"""
import os
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal

from .scanner import SystemScanner, BrowserScanner, AppDataScanner
from .depth_disk_scanner import DepthDiskScanner
from .models import ScanItem
from .rule_engine import RiskLevel
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ScanType(Enum):
    """扫描类型枚举"""
    SYSTEM = "system"           # 系统垃圾
    BROWSER = "browser"         # 浏览器缓存
    APPDATA = "appdata"         # AppData 数据
    CUSTOM = "custom"           # 自定义路径
    DISK = "disk"               # 磁盘全盘扫描


@dataclass
class ScanConfig:
    """扫描配置"""
    scan_type: ScanType
    scan_target: str            # 扫描目标路径
    include_hidden: bool = False     # 是否包含隐藏文件
    follow_symlinks: bool = False    # 是否跟随符号链接
    use_mft: bool = False            # 是否使用 NTFS MFT (V2功能)
    min_size: int = 0                # 最小文件大小过滤(字节)


class SmartScanSelector(QObject):
    """智能扫描选择器

    根据扫描类型和目标自动选择最优扫描器。
    支持扫描进度信号发射和实时数据返回。

    Signals:
        scan_progress: (current, total, message) - 扫描进度
        item_found: (ScanItem) - 发现清理项
        scan_complete: (List[ScanItem]) - 扫描完成
        scan_error: (str) - 扫描错误
    """

    scan_progress = pyqtSignal(int, int, str)    # current, total, message
    item_found = pyqtSignal(object)              # ScanItem
    scan_complete = pyqtSignal(list)             # List[ScanItem]
    scan_error = pyqtSignal(str)                 # error message

    # 扫描器映射表
    _SCAN_MAP: Dict[ScanType, type] = {
        ScanType.SYSTEM: SystemScanner,
        ScanType.BROWSER: BrowserScanner,
        ScanType.APPDATA: AppDataScanner,
        ScanType.CUSTOM: DepthDiskScanner,  # 深度磁盘扫描器
        ScanType.DISK: DepthDiskScanner,    # 深度磁盘扫描器
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scanners: Dict[ScanType, object] = {}
        self._config: Optional[ScanConfig] = None
        self._current_scanner = None

        # 初始化扫描器
        self._init_scanners()

    def _init_scanners(self):
        """初始化所有扫描器实例"""
        for scan_type, scanner_class in self._SCAN_MAP.items():
            if scanner_class:
                try:
                    self._scanners[scan_type] = scanner_class()
                    logger.info(f"[SCAN_SELECT] 已初始化扫描器: {scan_type.value}")
                except Exception as e:
                    logger.error(f"[SCAN_SELECT] 初始化扫描器失败 {scan_type.value}: {e}")

    def get_scanner(self, scan_type: ScanType) -> Optional[object]:
        """获取指定类型的扫描器

        Args:
            scan_type: 扫描类型

        Returns:
            扫描器实例，不支持的类型返回 None
        """
        return self._scanners.get(scan_type)

    def get_available_scan_types(self) -> List[ScanType]:
        """获取可用的扫描类型列表

        Returns:
            可用的 ScanType 列表
        """
        return list(self._SCAN_MAP.keys())

    def get_scan_type_by_path(self, path: str) -> ScanType:
        """根据路径智能推测扫描类型

        Args:
            path: 扫描路径

        Returns:
            推荐的扫描类型
        """
        # 首先检查是否为 AppData 路径（优先级最高）
        if 'AppData' in path or 'appdata' in path:
            return ScanType.APPDATA

        # 检查是否为浏览器路径（如果不是 AppData 中的）
        browser_keywords = ['Chrome', 'Edge', 'Firefox', 'Brave', 'Opera', 'Cache', 'Browser']
        for keyword in browser_keywords:
            if keyword.lower() in path.lower():
                return ScanType.BROWSER

        # 检查是否为系统路径
        system_paths = ['Windows', 'Program Files', 'ProgramData', 'Temp']
        for sys_path in system_paths:
            if sys_path in path:
                return ScanType.SYSTEM

        # 默认使用自定义扫描
        return ScanType.CUSTOM

    def select_optimal_scanner(self, config: ScanConfig) -> Optional[object]:
        """根据配置选择最优扫描器

        Args:
            config: 扫描配置

        Returns:
            扫描器实例
        """
        # 优先使用指定的扫描类型
        scanner = self.get_scanner(config.scan_type)
        if scanner:
            self._current_scanner = scanner
            return scanner

        # 如果指定类型不可用，尝试智能推测
        guessed_type = self.get_scan_type_by_path(config.scan_target)
        if guessed_type != config.scan_type:
            scanner = self.get_scanner(guessed_type)
            if scanner:
                logger.info(f"[SCAN_SELECT] 使用智能推测的扫描器: {guessed_type.value}")
                self._current_scanner = scanner
                return scanner

        logger.warning(f"[SCAN_SELECT] 未找到合适的扫描器: {config.scan_type.value}")
        return None

    def start_scan(self, config: ScanConfig, callback=None):
        """开始扫描

        Args:
            config: 扫描配置
            callback: 扫描完成回调函数
        """
        self._config = config

        # 选择扫描器
        scanner = self.select_optimal_scanner(config)
        if not scanner:
            error_msg = f"不支持的扫描类型: {config.scan_type.value}"
            logger.error(f"[SCAN_SELECT] {error_msg}")
            self.scan_error.emit(error_msg)
            return

        # 连接信号
        if hasattr(scanner, 'scan_progress'):
            scanner.scan_progress.connect(lambda c, t, m: self.scan_progress.emit(c, t, m))
        if hasattr(scanner, 'item_found'):
            scanner.item_found.connect(lambda item: self.item_found.emit(item))
        if hasattr(scanner, 'scan_complete'):
            scanner.scan_complete.connect(self._on_scan_complete)
        if hasattr(scanner, 'scan_error'):
            scanner.scan_error.connect(lambda e: self.scan_error.emit(e))

        # 开始扫描
        try:
            logger.info(f"[SCAN_SELECT] 开始扫描: {config.scan_type.value} - {config.scan_target}")

            # 根据不同扫描器调用不同的方法
            if hasattr(scanner, 'scan'):
                if config.scan_type == ScanType.SYSTEM:
                    scanner.scan(callback=callback)
                elif config.scan_type == ScanType.BROWSER:
                    # 浏览器扫描需要指定浏览器类型
                    browser_type = self._detect_browser_type(config.scan_target)
                    scanner.scan(callback=callback)
                elif config.scan_type == ScanType.APPDATA:
                    # AppData 扫描需要指定模式
                    scanner.scan(
                        include_roaming=True,
                        include_local=True,
                        include_local_low=True,
                        callback=callback
                    )
                else:
                    scanner.scan(callback=callback)
        except Exception as e:
            error_msg = f"扫描启动失败: {str(e)}"
            logger.error(f"[SCAN_SELECT] {error_msg}")
            self.scan_error.emit(error_msg)

    def _detect_browser_type(self, path: str) -> str:
        """检测浏览器类型

        Args:
            path: 浏览器路径

        Returns:
            浏览器类型字符串
        """
        if 'chrome' in path.lower():
            return 'chrome'
        elif 'edge' in path.lower():
            return 'edge'
        elif 'firefox' in path.lower():
            return 'firefox'
        else:
            return 'unknown'

    def _on_scan_complete(self, items: List[ScanItem]):
        """扫描完成处理

        Args:
            items: 扫描结果列表
        """
        logger.info(f"[SCAN_SELECT] 扫描完成，发现 {len(items)} 个清理项")
        self.scan_complete.emit(items)

    def stop_scan(self):
        """停止当前扫描"""
        if self._current_scanner and hasattr(self._current_scanner, 'stop'):
            logger.info("[SCAN_SELECT] 停止扫描")
            self._current_scanner.stop()

    def is_scanning(self) -> bool:
        """检查是否正在扫描

        Returns:
            是否正在扫描
        """
        if self._current_scanner and hasattr(self._current_scanner, 'is_scanning'):
            return self._current_scanner.is_scanning()
        return False

    def get_scan_config(self) -> Optional[ScanConfig]:
        """获取当前扫描配置

        Returns:
            当前使用的扫描配置
        """
        return self._config

    def get_scan_progress(self) -> Dict[str, any]:
        """获取扫描进度信息

        Returns:
            包含进度信息的字典
        """
        if self._current_scanner and hasattr(self._current_scanner, 'get_progress'):
            return self._current_scanner.get_progress()
        return {
            'current': 0,
            'total': 0,
            'percentage': 0,
            'message': '未开始扫描'
        }


# 便利函数
def get_smart_scan_selector() -> SmartScanSelector:
    """获取智能扫描选择器实例

    Returns:
        SmartScanSelector 实例
    """
    return SmartScanSelector()
