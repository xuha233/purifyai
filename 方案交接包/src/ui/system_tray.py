"""
系统托盘模块
用于在系统托盘驻留程序，提供快速操作
"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from qfluentwidgets import FluentIcon


class SystemTray(QObject):
    """系统托盘图标类

    提供系统托盘右键菜单和通知功能
    """
    # Signals
    quick_clean_system = pyqtSignal()  # 快速清理系统
    quick_clean_browser = pyqtSignal()  # 快速清理浏览器
    show_window = pyqtSignal()  # 显示主窗口
    open_settings = pyqtSignal()  # 打开设置
    quit_app = pyqtSignal()  # 退出应用

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = None
        self._create_tray_icon()

    def _create_tray_icon(self):
        """创建系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self.parent())

        try:
            # 尝试加载应用图标
            from PyQt5.QtGui import QIcon
            icon = QIcon(":/images/logo.ico")
            self.tray_icon.setIcon(icon)
        except Exception:
            # 如果没有图标，使用默认图标
            pass

        # 创建右键菜单
        self._create_context_menu()

        # 双击显示主窗口
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _create_context_menu(self):
        """创建右键菜单"""
        menu = QMenu()

        # 清理子菜单
        clean_menu = menu.addMenu("快速清理")

        # 清理系统
        clean_system_action = QAction("清理系统", self)
        clean_system_action.triggered.connect(self.quick_clean_system.emit)
        clean_menu.addAction(clean_system_action)

        # 清理浏览器
        clean_browser_action = QAction("清理浏览器", self)
        clean_browser_action.triggered.connect(self.quick_clean_browser.emit)
        clean_menu.addAction(clean_browser_action)

        menu.addSeparator()

        # 打开主窗口
        show_action = QAction("打开 PurifyAI", self)
        show_action.triggered.connect(self.show_window.emit)
        menu.addAction(show_action)

        # 打开设置
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        # 退出
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app.emit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        """处理托盘激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            # 双击显示主窗口
            self.show_window.emit()

    def show_notification(self, title: str, message: str, duration: int = 3000):
        """显示托盘通知

        Args:
            title: 通知标题
            message: 通知内容
            duration: 显示持续时间（毫秒）
        """
        if self.tray_icon is not None:
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, duration)

    def show_tray(self):
        """显示托盘图标"""
        if self.tray_icon is not None:
            self.tray_icon.show()

    def hide_tray(self):
        """隐藏托盘图标"""
        if self.tray_icon is not None:
            self.tray_icon.hide()

    def is_visible(self) -> bool:
        """检查托盘图标是否可见"""
        return self.tray_icon is not None and self.tray_icon.isVisible()
