"""
首页 Dashboard - 简洁版
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QScrollArea, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import psutil
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, CardWidget,
    PrimaryPushButton, IconWidget, FluentIcon, PushButton,
    ComboBox
)
from PyQt5.QtGui import QFont


class DashboardPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ========== 顶部操作栏 - 简洁版 ==========
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        # Logo
        app_name = StrongBodyLabel('PurifyAI')
        app_name.setStyleSheet('font-size: 24px; font-weight: 700; color: #2c2c2c;')
        top_bar.addWidget(app_name)

        main_layout.addLayout(top_bar)
        main_layout.addSpacing(8)

        # ========== 主内容区域 ==========
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧面板：系统状态
        left_panel = SimpleCardWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_panel.setFixedWidth(220)

        left_title = StrongBodyLabel('系统状态')
        left_title.setStyleSheet('font-size: 12px; color: #666;')
        left_layout.addWidget(left_title)

        # CPU
        self.cpu_card = self._create_min_stat_card('CPU', '#2d2d2d')
        left_layout.addWidget(self.cpu_card)

        # 内存
        self.mem_card = self._create_min_stat_card('RAM', '#2d2d2d')
        left_layout.addWidget(self.mem_card)

        # 磁盘
        self.disk_card = self._create_min_stat_card('C盘', '#2d2d2d')
        left_layout.addWidget(self.disk_card)

        left_layout.addStretch()

        content_layout.addWidget(left_panel)

        # 中间面板：操作
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setSpacing(8)

        # 主要操作卡片
        main_ops_card = SimpleCardWidget()
        ops_layout = QVBoxLayout(main_ops_card)
        ops_layout.setContentsMargins(12, 12, 12, 12)
        ops_layout.setSpacing(8)

        ops_title = StrongBodyLabel('清理操作')
        ops_title.setStyleSheet('font-size: 12px; color: #666;')
        ops_layout.addWidget(ops_title)

        # 快捷操作按钮
        self.sys_scan_btn = self._create_quick_btn('系统文件', FluentIcon.DELETE, 'systemCleaner')
        ops_layout.addWidget(self.sys_scan_btn)

        self.browser_scan_btn = self._create_quick_btn('浏览器缓存', FluentIcon.GLOBE, 'browserCleaner')
        ops_layout.addWidget(self.browser_scan_btn)

        self.custom_scan_btn = self._create_quick_btn('自定义扫描', FluentIcon.FOLDER_ADD, 'customCleaner')
        ops_layout.addWidget(self.custom_scan_btn)

        self.history_btn = self._create_quick_btn('清理历史', FluentIcon.HISTORY, 'history')
        ops_layout.addWidget(self.history_btn)

        # 智能体中心按钮（新增 - 醒目显示）
        self.agent_hub_btn = self._create_agent_hub_btn()
        ops_layout.addWidget(self.agent_hub_btn)

        ops_layout.addStretch()
        center_layout.addWidget(main_ops_card, stretch=1)

        content_layout.addWidget(center_panel, stretch=1)

        # 右侧面板：统计 + 控制台
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)

        # 统计信息
        stats_card = SimpleCardWidget()
        stats_card_layout = QHBoxLayout(stats_card)
        stats_card_layout.setContentsMargins(12, 8, 12, 8)

        self.total_scan = StrongBodyLabel('0')
        self.total_scan.setStyleSheet('font-size: 16px; font-weight: 600; color: #2d2d2d;')

        self.total_clean = StrongBodyLabel('0')
        self.total_clean.setStyleSheet('font-size: 16px; font-weight: 600; color: #2d2d2d;')

        self.freed_size = StrongBodyLabel('0 B')
        self.freed_size.setStyleSheet('font-size: 16px; font-weight: 600; color: #2d2d2d;')

        stats_card_layout.addLayout(self._create_stat_item('扫描', self.total_scan))
        stats_card_layout.addLayout(self._create_stat_item('清理', self.total_clean))
        stats_card_layout.addLayout(self._create_stat_item('释放', self.freed_size))

        right_layout.addWidget(stats_card)

        # AI 状态
        ai_card = SimpleCardWidget()
        ai_card.setStyleSheet('background: #0078D408; border: 1px solid #0078D420;')
        ai_layout = QHBoxLayout(ai_card)
        ai_layout.setContentsMargins(12, 8, 12, 8)

        ai_icon = IconWidget(FluentIcon.INFO)
        ai_icon.setFixedSize(16, 16)
        ai_icon.setStyleSheet('color: #0078D4;')
        ai_layout.addWidget(ai_icon)

        self.ai_status = BodyLabel('AI : 就绪')
        self.ai_status.setStyleSheet('font-size: 11px; color: #0078D4;')
        ai_layout.addWidget(self.ai_status)

        ai_layout.addStretch()

        right_layout.addWidget(ai_card)

        # 快捷工具
        tools_card = SimpleCardWidget()
        tools_layout = QVBoxLayout(tools_card)
        tools_layout.setContentsMargins(8, 8, 8, 8)
        tools_layout.setSpacing(6)

        tools_title = BodyLabel('快捷工具')
        tools_title.setStyleSheet('font-size: 10px; color: #666;')
        tools_layout.addWidget(tools_title)

        # 工具按钮网格
        tools_row = QHBoxLayout()
        tools_row.setSpacing(6)

        self.whitelist_btn = self._create_tool_btn('白名单', FluentIcon.LIBRARY)
        self.whitelist_btn.clicked.connect(lambda: self._show_whitelist_dialog())
        tools_row.addWidget(self.whitelist_btn)

        self.history_btn = self._create_tool_btn('历史', FluentIcon.HISTORY)
        self.history_btn.clicked.connect(lambda: self.navigate_requested.emit('history'))
        tools_row.addWidget(self.history_btn)

        self.settings_btn = self._create_tool_btn('设置', FluentIcon.SETTING)
        self.settings_btn.clicked.connect(lambda: self.navigate_requested.emit('settings'))
        tools_row.addWidget(self.settings_btn)

        self.console_btn = self._create_tool_btn('控制台', FluentIcon.DEVELOPER_TOOLS)
        self.console_btn.clicked.connect(lambda: self._show_console_dialog())
        tools_row.addWidget(self.console_btn)

        tools_layout.addLayout(tools_row)

        right_layout.addWidget(tools_card)

        # AI 缓存统计
        cache_card = SimpleCardWidget()
        cache_card.setStyleSheet('background: #E5A00008; border: 1px solid #E5A00030;')
        cache_layout = QHBoxLayout(cache_card)
        cache_layout.setContentsMargins(10, 6, 10, 6)

        cache_icon = IconWidget(FluentIcon.CLOUD)
        cache_icon.setFixedSize(16, 16)
        cache_icon.setStyleSheet('color: #E5A000;')
        cache_layout.addWidget(cache_icon)

        self.cache_label = BodyLabel('AI缓存: --')
        self.cache_label.setStyleSheet('font-size: 10px; color: #E5A000;')
        cache_layout.addWidget(self.cache_label)

        cache_layout.addStretch()

        right_layout.addWidget(cache_card)

        # 最近清理记录
        recent_card = SimpleCardWidget()
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(10, 8, 10, 8)

        recent_title = BodyLabel('最近清理')
        recent_title.setStyleSheet('font-size: 10px; color: #666;')
        recent_layout.addWidget(recent_title)

        self.recent_label = BodyLabel('暂无记录')
        self.recent_label.setStyleSheet('font-size: 11px; color: #888;')
        recent_layout.addWidget(self.recent_label)

        right_layout.addWidget(recent_card, stretch=1)

        content_layout.addWidget(right_panel)
        main_layout.addWidget(content_widget, stretch=1)

    def _create_tool_btn(self, label, icon):
        """创建工具按钮"""
        from PyQt5.QtWidgets import QToolButton
        from PyQt5.QtGui import QIcon
        from PyQt5.QtCore import QSize

        btn = QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setFixedHeight(60)
        btn.setMinimumWidth(50)
        btn.setText(label)
        btn.setIcon(icon.icon())
        btn.setIconSize(QSize(18, 18))
        btn.setStyleSheet('''
            QToolButton {
                background: #f5f5f5;
                border-radius: 6px;
                font-size: 10px;
                padding: 4px;
            }
            QToolButton:hover {
                background: #0078D410;
                border: 1px solid #0078D430;
            }
        ''')
        return btn

    def _show_whitelist_dialog(self):
        """显示白名单对话框"""
        try:
            from ui.whitelist_dialog import WhitelistDialog
            dialog = WhitelistDialog(self)
            dialog.exec_()
        except Exception as e:
            print(f"无法打开白名单对话框: {e}")

    def _show_console_dialog(self):
        """显示开发者控制台对话框"""
        try:
            from ui.developer_console_window import DeveloperConsoleWindow
            console = DeveloperConsoleWindow(self)
            console.show()
        except Exception as e:
            print(f"无法打开开发者控制台: {e}")

    def _create_min_stat_card(self, label: str, color: str):
        """创建最小统计卡片"""
        card = QWidget()
        card.setStyleSheet(f'background: #f5f5f5; border-radius: 4px;')
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        icon = IconWidget(FluentIcon.DOCUMENT)
        icon.setFixedSize(14, 14)
        icon.setStyleSheet(f'color: {color};')
        layout.addWidget(icon)

        l = BodyLabel(label)
        l.setStyleSheet('font-size: 10px; color: #666;')
        layout.addWidget(l)

        layout.addStretch()

        val = StrongBodyLabel('0%')
        val.setStyleSheet(f'font-size: 12px; color: {color}; font-weight: 600;')
        val.setObjectName(f'{label}_value')
        layout.addWidget(val)

        return card

    def _create_quick_btn(self, label: str, icon, route: str):
        """创建快捷按钮"""
        card = SimpleCardWidget()
        card.setStyleSheet('''
            SimpleCardWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            SimpleCardWidget:hover {
                background: #0078D408;
                border: 1px solid #0078D4;
            }
        ''')
        card.setFixedHeight(40)
        card.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 0, 12, 0)

        i = IconWidget(icon)
        i.setFixedSize(18, 18)
        i.setStyleSheet('color: #555;')
        layout.addWidget(i)

        l = BodyLabel(label)
        l.setStyleSheet('font-size: 13px; color: #2c2c2c;')
        layout.addWidget(l)
        layout.addStretch()

        card.mousePressEvent = lambda e: self.navigate_requested.emit(route)
        return card

    def _create_agent_hub_btn(self):
        """创建智能体中心入口按钮（醒目样式）"""
        card = SimpleCardWidget()
        card.setStyleSheet('''
            SimpleCardWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #0078D4, stop:1 #0096c7);
                border: none;
                border-radius: 8px;
            }
            SimpleCardWidget:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #106ebe, stop:1 #00a8d6);
                border: none;
            }
        ''')
        card.setFixedHeight(44)
        card.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 0, 14, 0)

        i = IconWidget(FluentIcon.ROBOT)
        i.setFixedSize(20, 20)
        i.setStyleSheet('color: white;')
        layout.addWidget(i)

        l = BodyLabel('启动智能体')
        l.setStyleSheet('font-size: 13px; color: white; font-weight: 600;')
        layout.addWidget(l)

        ai_badge = QLabel('AI')
        ai_badge.setStyleSheet('''
            QLabel {
                background: rgba(255, 255, 255, 0.25);
                color: white;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
            }
        ''')
        layout.addWidget(ai_badge)

        layout.addStretch()

        arrow = IconWidget(FluentIcon.CHEVRIR_RIGHT)
        arrow.setFixedSize(14, 14)
        arrow.setStyleSheet('color: white; opacity: 0.8;')
        layout.addWidget(arrow)

        card.mousePressEvent = lambda e: self.navigate_requested.emit('agentHub')
        return card

    def _create_stat_item(self, label, value_label):
        """创建统计项"""
        layout = QVBoxLayout()
        layout.setSpacing(2)

        l = BodyLabel(label)
        l.setStyleSheet('font-size: 10px; color: #888;')
        layout.addWidget(l)

        layout.addWidget(value_label)
        return layout

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(3000)
        self._update_stats()

    def _update_stats(self):
        try:
            cpu = psutil.cpu_percent()
            val = self.cpu_card.findChild(StrongBodyLabel, 'CPU_value')
            if val:
                val.setText(f'{int(cpu)}%')

            mem = psutil.virtual_memory()
            val = self.mem_card.findChild(StrongBodyLabel, 'RAM_value')
            if val:
                val.setText(f'{int(mem.percent)}%')

            c_path = 'C:\\'
            disk = psutil.disk_usage(c_path)
            percent = int((disk.used / disk.total) * 100)
            val = self.disk_card.findChild(StrongBodyLabel, 'C盘_value')
            if val:
                val.setText(f'{percent}%')

        except Exception:
            pass

        # 更新统计信息
        try:
            from core.database import get_database
            db = get_database()
            stats = db.get_statistics()

            total_scan = stats.get('total_scan_count', 0)
            total_clean = stats.get('total_cleaned_files', 0)
            freed_size = self._format_size(stats.get('total_freed_space', 0))

            self.total_scan.setText(str(total_scan))
            self.total_clean.setText(str(total_clean))
            self.freed_size.setText(freed_size)
        except Exception:
            pass

        # 更新 AI 缓存统计
        try:
            from core.ai_cache import get_ai_cache
            cache = get_ai_cache()
            stats = cache.get_statistics()
            cache_size = stats.get('cache_size', 0)
            hit_rate = stats.get('hit_rate', 0)
            self.cache_label.setText(f'AI缓存: {cache_size} ({hit_rate:.0%})')
        except Exception:
            pass

        # 更新最近清理记录
        try:
            from core.database import get_database
            db = get_database()
            recent = db.get_recent_cleans(limit=1)
            if recent:
                clean = recent[0]
                size = self._format_size(clean.get('total_size', 0))
                count = clean.get('items_count', 0)
                self.recent_label.setText(f'最近: {count} 项 ({size})')
            else:
                self.recent_label.setText('暂无清理记录')
        except Exception as e:
            print(f"更新最近记录失败: {e}")
            self.recent_label.setText('暂无清理记录')

    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return '0 B'

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f'{size:.1f} {units[unit_index]}'
