import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'ui'))

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from qfluentwidgets import NavigationInterface, FluentIcon, NavigationItemPosition

from ui.dashboard import DashboardPage
from ui.system_cleaner import SystemCleanerPage
from ui.browser_cleaner import BrowserCleanerPage
from ui.custom_cleaner import CustomCleanerPage
from ui.smart_cleanup_page import SmartCleanupPage
from ui.settings import SettingsPage
from ui.history_page import HistoryPage
from ui.recovery_dialog import RecoveryDialog
from ui.recovery_page import RecoveryPage
from ui.developer_console import DeveloperConsolePage
from ui.cleanup_report_page import CleanupReportPage
from ui.agent_hub_page import AgentHubPage  # 智能体中心页面

from ui.system_tray import SystemTray
from ui.windows_notification import WindowsNotification
from core.scheduler import get_scheduler
from core.config_manager import get_config_manager
from utils.logger import get_logger, log_ui_event, log_config_event


logger = get_logger(__name__)


class PurifyAIApp(QWidget):
    def __init__(self, app: QApplication):
        super().__init__()
        logger.info("[应用:INIT] 开始初始化 PurifyAI 应用的主窗口")

        self.app = app
        self.config_mgr = get_config_manager()
        self._developer_console_page = None  # 开发者控制台页面

        # 初始化系统托盘
        self._init_system_tray()

        # 初始化通知管理器
        self._init_notification()

        # 初始化调度器
        self._init_scheduler()

        self.init_ui()
        self.init_navigation()
        self.connect_dashboard_signals()
        self.stacked_widget.setCurrentWidget(self.dashboard_page)

        logger.info("[应用:INIT] 主窗口初始化完成")

    def _init_system_tray(self):
        """初始化系统托盘"""
        self.tray = SystemTray(self)

        # 连接信号
        self.tray.quick_clean_system.connect(self.on_quick_clean_system)
        self.tray.quick_clean_browser.connect(self.on_quick_clean_browser)
        self.tray.show_window.connect(self.on_show_window)
        self.tray.open_settings.connect(self.on_open_settings)
        self.tray.quit_app.connect(self.on_quit_app)

        # 检查是否启用托盘
        tray_enabled = self.config_mgr.get('system_tray/enabled', True)
        if tray_enabled:
            self.tray.show_tray()

    def _init_notification(self):
        """初始化通知管理器"""
        self.notification = WindowsNotification(self.tray.tray_icon if self.tray else None)

    def _init_scheduler(self):
        """初始化调度器"""
        self.scheduler = get_scheduler()

        # 连接信号
        self.scheduler.clean_system.connect(self.on_scheduler_clean_system)
        self.scheduler.clean_browser.connect(self.on_scheduler_clean_browser)
        self.scheduler.auto_clean_completed.connect(self.on_auto_clean_completed)

        # 自动启动调度器（如果已启用）
        scheduler_enabled = self.scheduler.enabled
        if scheduler_enabled:
            self.scheduler.start()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.navigation = NavigationInterface(self, showMenuButton=True, showReturnButton=False)
        self.navigation.setFixedWidth(260)

        self.stacked_widget = QStackedWidget(self)

        self.main_layout.addWidget(self.navigation)
        self.main_layout.addWidget(self.stacked_widget)

    def init_navigation(self):
        self.dashboard_page = DashboardPage(self)
        self.agent_hub_page = AgentHubPage()  # 智能体中心页面（新增）
        self.system_cleaner_page = SystemCleanerPage()
        self.browser_cleaner_page = BrowserCleanerPage()
        self.custom_cleaner_page = CustomCleanerPage()
        self.smart_cleanup_page = SmartCleanupPage()
        self.recovery_page = RecoveryPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(self)  # 传入 self 以设置回调
        self.cleanup_report_page = CleanupReportPage()

        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.agent_hub_page)  # 智能体中心（新增）
        self.stacked_widget.addWidget(self.system_cleaner_page)
        self.stacked_widget.addWidget(self.browser_cleaner_page)
        self.stacked_widget.addWidget(self.custom_cleaner_page)
        self.stacked_widget.addWidget(self.smart_cleanup_page)
        self.stacked_widget.addWidget(self.recovery_page)
        self.stacked_widget.addWidget(self.history_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.cleanup_report_page)

        self.navigation.addItem(
            routeKey="dashboard",
            icon=FluentIcon.HOME,
            text="首页",
            onClick=lambda: self.navigate_to("dashboard", self.dashboard_page)
        )

        # 智能体中心 - 核心页面（新增，放在首页之后）
        self.navigation.addItem(
            routeKey="agentHub",
            icon=FluentIcon.GLOBE,
            text="智能体中心",
            onClick=lambda: self.navigate_to("agentHub", self.agent_hub_page)
        )

        self.navigation.addItem(
            routeKey="systemCleaner",
            icon=FluentIcon.DELETE,
            text="系统清理",
            onClick=lambda: self.navigate_to("systemCleaner", self.system_cleaner_page)
        )

        self.navigation.addItem(
            routeKey="browserCleaner",
            icon=FluentIcon.GLOBE,
            text="浏览器清理",
            onClick=lambda: self.navigate_to("browserCleaner", self.browser_cleaner_page)
        )

        self.navigation.addItem(
            routeKey="smartCleanup",
            icon=FluentIcon.SYNC,
            text="智能清理",
            onClick=lambda: self.navigate_to("smartCleanup", self.smart_cleanup_page)
        )

        self.navigation.addItem(
            routeKey="customCleaner",
            icon=FluentIcon.FOLDER,
            text="自定义清理",
            onClick=lambda: self.navigate_to("customCleaner", self.custom_cleaner_page)
        )

        self.navigation.addItem(
            routeKey="history",
            icon=FluentIcon.HISTORY,
            text="清理历史",
            onClick=lambda: self.navigate_to("history", self.history_page)
        )

        self.navigation.addItem(
            routeKey="recovery",
            icon=FluentIcon.DELETE,
            text="文件恢复",
            onClick=lambda: self.navigate_to("recovery", self.recovery_page)
        )

        self.navigation.addItem(
            routeKey="settings",
            icon=FluentIcon.SETTING,
            text="设置",
            onClick=lambda: self.navigate_to("settings", self.settings_page)
        )

        # 开发者控制台（根据设置显示）
        self._init_developer_console()

        # 设置开发者控制台回调
        self.settings_page.set_console_callback(self.toggle_developer_console)

        self.navigation.setCurrentItem("dashboard")

    def _init_developer_console(self):
        """初始化开发者控制台（根据设置决定是否显示）"""
        console_enabled = self.config_mgr.get('developer_console/enabled', False)

        if console_enabled:
            self._add_developer_console_ui()

    def _add_developer_console_ui(self):
        """添加开发者控制台 UI"""
        if self._developer_console_page is None:
            self._developer_console_page = DeveloperConsolePage(self)
            self.stacked_widget.addWidget(self._developer_console_page)

            # 添加导航项（在设置之前，底部）
            self.navigation.addItem(
                routeKey="developerConsole",
                icon=FluentIcon.CODE,
                text="开发者控制台",
                position=NavigationItemPosition.BOTTOM,
                onClick=lambda: self.navigate_to("developerConsole", self._developer_console_page)
            )

    def _remove_developer_console_ui(self):
        """移除开发者控制台 UI"""
        if self._developer_console_page is not None:
            # 清理日志处理器
            self._developer_console_page.cleanup_root_logger()
            self._developer_console_page.setParent(None)
            self._developer_console_page.deleteLater()
            self._developer_console_page = None

            # 移除导航项
            self.navigation.removeItem("developerConsole")

    def navigate_to(self, route_key, widget):
        """导航到指定页面并更新导航栏选中状态"""
        self.stacked_widget.setCurrentWidget(widget)
        self.navigation.setCurrentItem(route_key)

    def connect_dashboard_signals(self):
        """连接仪表盘导航信号"""
        self.dashboard_page.navigate_requested.connect(self.on_dashboard_navigate)

        # 连接清理报告页面信号
        self.cleanup_report_page.return_to_scan.connect(self.on_report_return_to_scan)
        self.cleanup_report_page.navigate_to_recovery.connect(self.on_report_navigate_to_recovery)

        # 连接智能清理页面的报告显示信号
        self.smart_cleanup_page.show_cleanup_report.connect(self.on_show_cleanup_report)
        self.smart_cleanup_page.retry_failed.connect(self.on_retry_failed_cleanup)

    def on_show_cleanup_report(self, plan, result):
        """显示清理报告页面

        Args:
            plan: 清理计划
            result: 执行结果
        """
        self.on_show_window()  # 确保窗口可见
        self.cleanup_report_page.show_report(plan, result)
        self.stacked_widget.setCurrentWidget(self.cleanup_report_page)
        # 取消导航栏选中状态（因为报告页面不在导航栏中）
        self.navigation.clearSelection()

    def on_report_return_to_scan(self):
        """从报告页返回扫描页"""
        self.navigate_to("smartCleanup", self.smart_cleanup_page)

    def on_report_navigate_to_recovery(self):
        """从报告页导航到恢复页"""
        self.navigate_to("recovery", self.recovery_page)

    def on_retry_failed_cleanup(self, failed_item_ids):
        """重试失败的清理项

        Args:
            failed_item_ids: 失败项ID列表
        """
        # 导航到智能清理页
        self.navigate_to("smartCleanup", self.smart_cleanup_page)
        # TODO: 调用重试逻辑（需要扩展SmartCleaner支持重试）
        logger.info(f"[App] 收到重试请求: {len(failed_item_ids)} 个失败项")

    def on_dashboard_navigate(self, route_key):
        """处理仪表盘的导航请求"""
        if route_key == "agentHub":
            self.navigate_to("agentHub", self.agent_hub_page)
        elif route_key == "systemCleaner":
            self.navigate_to("systemCleaner", self.system_cleaner_page)
        elif route_key == "browserCleaner":
            self.navigate_to("browserCleaner", self.browser_cleaner_page)
        elif route_key == "smartCleanup":
            self.navigate_to("smartCleanup", self.smart_cleanup_page)
        elif route_key == "customCleaner":
            self.navigate_to("customCleaner", self.custom_cleaner_page)
        elif route_key == "history":
            self.navigate_to("history", self.history_page)
        elif route_key == "recovery":
            self.on_show_window()  # 显示窗口
            self.open_recovery_dialog()
        elif route_key == "settings":
            self.navigate_to("settings", self.settings_page)

    # ============ 系统托盘事件处理 ============

    def on_quick_clean_system(self):
        """快速清理系统"""
        self.navigate_to("systemCleaner", self.system_cleaner_page)
        QTimer.singleShot(100, self.system_cleaner_page.on_scan)

    def on_quick_clean_browser(self):
        """快速清理浏览器"""
        self.navigate_to("browserCleaner", self.browser_cleaner_page)
        QTimer.singleShot(100, self.browser_cleaner_page.on_scan)

    def on_show_window(self):
        """显示主窗口"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_open_settings(self):
        """打开设置"""
        self.on_show_window()
        self.navigate_to("settings", self.settings_page)

    def open_recovery_dialog(self):
        """打开回收站恢复对话框"""
        self.on_show_window()
        dialog = RecoveryDialog(self)
        dialog.exec_()

    def on_quit_app(self):
        """退出应用"""
        # 停止调度器
        if self.scheduler.is_running():
            self.scheduler.stop()

        # 隐藏托盘
        if self.tray:
            self.tray.hide_tray()

        self.app.quit()

    # ============ 调度器事件处理 ============

    def on_scheduler_clean_system(self, items):
        """调度器触发系统清理"""
        self.navigate_to("systemCleaner", self.system_cleaner_page)
        QTimer.singleShot(100, self.system_cleaner_page.on_scan)

    def on_scheduler_clean_browser(self, items):
        """调度器触发浏览器清理"""
        self.navigate_to("browserCleaner", self.browser_cleaner_page)
        QTimer.singleShot(100, self.browser_cleaner_page.on_scan)

    def on_auto_clean_completed(self, result):
        """自动清理完成"""
        if self.notification:
            clean_type = result.get('type', 'unknown')
            if clean_type == 'daily':
                self.notification.show_custom(
                    '自动清理完成',
                    '每日定时清理已完成'
                )
            elif clean_type == 'disk_space':
                self.notification.show_custom(
                    '磁盘空间清理完成',
                    f"磁盘空间已触发清理（低于 {result.get('threshold_gb', 10)}GB）"
                )

    # ============ 窗口事件处理 ============

    def changeEvent(self, event):
        """处理窗口状态变化"""
        if event.type() == event.WindowStateChange:
            # 检查是否最小化到托盘
            minimize_to_tray = self.config_mgr.get('system_tray/minimize_to_tray', True)

            if minimize_to_tray and (self.windowState() & Qt.WindowMinimized):
                self.hide()
                if self.tray and self.tray.is_visible():
                    self.tray.show_notification('PurifyAI', '已最小化到托盘')

        super().changeEvent(event)

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        minimize_on_close = self.config_mgr.get('system_tray/minimize_on_close', True)

        if minimize_on_close:
            # 最小化到托盘
            event.ignore()
            self.hide()
        else:
            # 直接退出，先清理开发者控制台
            if self._developer_console_page is not None:
                self._developer_console_page.cleanup_root_logger()
            if self.tray:
                self.tray.hide_tray()
            event.accept()

    # ============ 开发者控制台 ============
    def toggle_developer_console(self, enabled: bool):
        """切换开发者控制台显示状态

        Args:
            enabled: 是否启用开发者控制台
        """
        if enabled:
            self._add_developer_console_ui()
        else:
            self._remove_developer_console_ui()

    # ============ 公共方法 ============

    def show_notification(self, title: str, message: str):
        """显示通知"""
        if self.notification:
            self.notification.show(title, message)

    def get_notification_manager(self) -> WindowsNotification:
        """获取通知管理器"""
        return self.notification

    def get_scheduler(self):
        """获取调度器"""
        return self.scheduler

    def update_appdata_migration_button(self):
        """更新AppData迁移按钮可见性"""
        if hasattr(self.system_cleaner_page, 'update_appdata_migration_button'):
            self.system_cleaner_page.update_appdata_migration_button()
