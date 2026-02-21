"""
Windows 系统通知模块
使用 QSystemTrayIcon showMessage 发送系统通知
"""
from PyQt5.QtWidgets import QSystemTrayIcon
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.config_manager import get_config_manager


class WindowsNotification:
    """Windows 通知管理类

    封装 QSystemTrayIcon.showMessage() 方法
    提供统一的通知接口
    """

    # 通知类型
    SCAN_COMPLETE = 'scan_complete'
    CLEAN_COMPLETE = 'clean_complete'
    AUTO_CLEAN_COMPLETE = 'auto_clean_complete'
    ERROR = 'error'

    def __init__(self, tray_icon: QSystemTrayIcon = None):
        """
        初始化通知管理器

        Args:
            tray_icon: QSystemTrayIcon 实例
        """
        self.tray_icon = tray_icon
        self.config_mgr = get_config_manager()

    @staticmethod
    def is_enabled() -> bool:
        """检查通知是否启用

        Returns:
            bool: 是否启用通知
        """
        config_mgr = get_config_manager()
        return config_mgr.get('notification/enabled', True)

    def show(self, title: str, message: str, notification_type: str = None, duration: int = 3000):
        """
        显示通知

        Args:
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型枚举
            duration: 显示持续时间（毫秒）
        """
        # 检查通知是否启用
        if not self.is_enabled():
            return

        # 如果没有托盘图标，无法显示通知
        if self.tray_icon is None:
            return

        # 根据类型选择图标
        icon = QSystemTrayIcon.Information
        if notification_type == self.ERROR:
            icon = QSystemTrayIcon.Warning

        # 显示通知
        self.tray_icon.showMessage(title, message, icon, duration)

    # 预定义通知方法

    def show_scan_complete(self, item_count: int, total_size: int):
        """
        显示扫描完成通知

        Args:
            item_count: 发现的项目数量
            total_size: 总大小（字节）
        """
        from core.scanner import format_size
        message = f'发现 {item_count} 个可清理项目，大小 {format_size(total_size)}'
        self.show('PurifyAI', message, self.SCAN_COMPLETE)

    def show_clean_complete(self, deleted_count: int, freed_size: int):
        """
        显示清理完成通知

        Args:
            deleted_count: 删除的项目数量
            freed_size: 释放的空间（字节）
        """
        from core.scanner import format_size
        message = f'清理完成！删除了 {deleted_count} 个项目，释放 {format_size(freed_size)}'
        self.show('PurifyAI', message, self.CLEAN_COMPLETE)

    def show_auto_clean_complete(self, type: str, deleted_count: int, freed_size: int):
        """
        显示自动清理完成通知

        Args:
            type: 清理类型
            deleted_count: 删除的项目数量
            freed_size: 释放的空间（字节）
        """
        from core.scanner import format_size
        message = f'自动{type}清理完成！删除了 {deleted_count} 个项目，释放 {format_size(freed_size)}'
        self.show('PurifyAI', message, self.AUTO_CLEAN_COMPLETE)

    def show_error(self, message: str):
        """
        显示错误通知

        Args:
            message: 错误信息
        """
        self.show('PurifyAI 错误', message, self.ERROR)

    def show_custom(self, title: str, message: str, duration: int = 3000):
        """
        显示自定义通知

        Args:
            title: 标题
            message: 消息
            duration: 持续时间
        """
        self.show(title, message, duration=duration)

    def set_tray_icon(self, tray_icon: QSystemTrayIcon):
        """
        设置托盘图标

        Args:
            tray_icon: QSystemTrayIcon 实例
        """
        self.tray_icon = tray_icon
