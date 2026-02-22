"""
系统清理页面 UI - 紧凑高效设计
支持详细的用户操作和系统行为日志记录
"""
import os
import time
import functools
import threading
import traceback
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QCheckBox, QStackedWidget, QDialog, QSpacerItem, QFrame
)
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, SegmentedWidget, SubtitleLabel, InfoBar, InfoBarPosition,
    ProgressBar, CardWidget, FluentIcon, IconWidget, Pivot
)
import logging

from utils.logger import get_logger, log_ui_event, log_clean_event, log_performance


logger = get_logger(__name__)

# 导入错误处理器
from core.error_handler import get_error_handler
from core.config_manager import get_config_manager
from core.safety.custom_recycle_bin import get_custom_recycle_bin


def handle_errors(func):
    """错误处理装饰器 - 捕获并记录所有异常"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"[SystemCleaner.{func.__name__}] {str(e)}")
            logger.debug(traceback.format_exc())
            error_handler = get_error_handler()
            error_handler.log_error(e, f"[SystemCleaner.{func.__name__}]")
            if hasattr(self, 'status_label'):
                try:
                    self.status_label.setText(f'错误: {str(e)[:50]}')
                except:
                    pass
            return None
    return wrapper

from core import SystemScanner, AppDataScanner, Cleaner, format_size, RiskLevel, ScanItem
from core.ai_review_models import AIReviewResult, AIReviewStatus, ReviewConfig
from core.ai_review_task import AIReviewWorker, AIReviewOrchestrator
from core.ai_client import AIClient, AIConfig
from ui.confirm_dialog import ConfirmDialog
from ui.windows_notification import WindowsNotification
from ui.scan_status_widget import ScanStatusWidget
from ui.ai_review_widgets import ReviewProgressBar, ReviewSummaryCard, AIReviewCard
from ui.appdata_migration_dialog import AppDataMigrationDialog


class SystemCleanerPage(QWidget):
    """系统清理页面 - 紧凑高效设计"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = []
        self.checkboxes = []
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}

        # AI复核相关
        self.ai_review_results = {}  # path -> AIReviewResult
        self.ai_review_worker = None
        self.ai_review_orchestrator = None

        # 扫描状态标记
        self.is_scanning = False

        logger.debug("[UI:PAGE] 系统清理页面初始化")
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # ========== 标题区 ==========
        header_layout = QHBoxLayout()
        title = StrongBodyLabel('系统清理')
        title.setStyleSheet('font-size: 24px;')
        header_layout.addWidget(title)
        header_layout.addSpacing(20)

        # 快速统计
        self.quick_stats = BodyLabel('0 项 | 0 B')
        self.quick_stats.setStyleSheet('color: #666666; font-size: 14px;')
        header_layout.addWidget(self.quick_stats)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ========== 模式切换工具栏 ==========
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(12)

        # 模式切换 - 更紧凑
        self.mode_segment = SegmentedWidget()
        self.mode_segment.addItem('system', '系统文件')
        self.mode_segment.addItem('appdata', 'AppData')
        self.mode_segment.setCurrentItem('system')
        self.mode_segment.currentItemChanged.connect(self.on_mode_changed)
        self.mode_segment.setFixedWidth(180)
        toolbar_layout.addWidget(self.mode_segment)

        # 迁移工具按钮 (仅 AppData 模式下显示)
        self.migration_btn = PushButton(FluentIcon.MOVE, '迁移工具')
        self.migration_btn.clicked.connect(self.show_migration_dialog)
        self.migration_btn.setFixedHeight(32)
        self.migration_btn.setVisible(False)
        toolbar_layout.addWidget(self.migration_btn)

        toolbar_layout.addStretch()

        main_layout.addWidget(toolbar)

        # ========== 主内容区域 ==========
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 左侧：扫描设置面板 ==========
        self.settings_panel = SimpleCardWidget()
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(12, 12, 12, 12)
        settings_layout.setSpacing(8)
        self.settings_panel.setFixedWidth(280)

        # 模式堆栈
        self.stack = QStackedWidget()

        # ========== System 扫描设置 ==========
        self.system_widget = QWidget()
        system_layout = QVBoxLayout(self.system_widget)
        system_layout.setSpacing(8)

        # 扫描选项（紧凑版）
        system_options = [
            ('temp_check', '临时文件', FluentIcon.EDIT, True),
            ('prefetch_check', '预取文件', FluentIcon.SKIP_FORWARD, True),
            ('logs_check', '日志文件', FluentIcon.DOCUMENT, True),
            ('update_cache_check', '更新缓存', FluentIcon.SYNC, True),
        ]

        for attr_name, label_text, icon, checked in system_options:
            option_row = self._create_compact_option(label_text, icon, checked)
            setattr(self, attr_name, option_row.checkbox)
            system_layout.addWidget(option_row)

        system_layout.addStretch()
        self.stack.addWidget(self.system_widget)

        # ========== AppData 扫描设置 ==========
        self.appdata_widget = QWidget()
        appdata_layout = QVBoxLayout(self.appdata_widget)
        appdata_layout.setSpacing(8)

        appdata_options = [
            ('roaming_check', 'Roaming', FluentIcon.FOLDER, True),
            ('local_check', 'Local', FluentIcon.FOLDER, True),
            ('locallow_check', 'LocalLow', FluentIcon.FOLDER_ADD, False),
        ]

        for attr_name, label_text, icon, checked in appdata_options:
            option_row = self._create_compact_option(label_text, icon, checked)
            setattr(self, attr_name, option_row.checkbox)
            appdata_layout.addWidget(option_row)

        appdata_layout.addStretch()
        self.stack.addWidget(self.appdata_widget)

        settings_layout.addWidget(self.stack)

        # 扫描按钮
        self.scan_btn = PrimaryPushButton(FluentIcon.SEARCH, '开始扫描')
        self.scan_btn.clicked.connect(self.on_scan)
        self.scan_btn.setFixedHeight(40)
        settings_layout.addWidget(self.scan_btn)

        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(36)
        settings_layout.addWidget(self.cancel_btn)

        # AI 评估按钮
        self.ai_evaluate_btn = PrimaryPushButton(FluentIcon.INFO, 'AI评估当前项')
        self.ai_evaluate_btn.clicked.connect(self.on_ai_evaluate_current)
        self.ai_evaluate_btn.setEnabled(False)
        self.ai_evaluate_btn.setFixedHeight(36)
        settings_layout.addWidget(self.ai_evaluate_btn)

        content_layout.addWidget(self.settings_panel)

        # ========== 右侧：结果和操作 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 扫描状态组件
        self.scan_status = ScanStatusWidget()
        right_layout.addWidget(self.scan_status)

        # 状态标签（用于其他消息）
        self.status_label = BodyLabel('就绪')
        self.status_label.setStyleSheet('font-size: 12px; color: #666;')
        right_layout.addWidget(self.status_label)

        # ========== AI复核进度组件 ==========
        self.ai_review_summary = ReviewSummaryCard()
        self.ai_review_summary.setVisible(False)
        right_layout.addWidget(self.ai_review_summary)

        self.ai_review_progress = ReviewProgressBar()
        self.ai_review_progress.setVisible(False)
        right_layout.addWidget(self.ai_review_progress)

        # 操作按钮行
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        # 合并的全选/取消全选按钮
        self.select_toggle_btn = PushButton('全选安全')
        self.select_toggle_btn.clicked.connect(self.on_select_toggle)
        self.select_toggle_btn.setFixedHeight(32)
        self.select_toggle_btn.setMinimumWidth(100)
        actions_row.addWidget(self.select_toggle_btn)

        # 清理按钮 - 使用PrimaryPushButton确保可用
        self.clean_btn = PrimaryPushButton('清理选中')
        self.clean_btn.clicked.connect(self.on_clean)
        self.clean_btn.setEnabled(False)
        # 红色样式
        self.clean_btn.setStyleSheet("PrimaryPushButton { background: #dc3545; color: white; border: none; border-radius: 4px; padding: 8px 16px; } PrimaryPushButton:hover { background: #c82333; } PrimaryPushButton:disabled { background: #e9ecef; color: #6c757d; }")
        self.clean_btn.setFixedHeight(36)
        self.clean_btn.setMinimumWidth(120)
        actions_row.addWidget(self.clean_btn)

        actions_row.addStretch()
        right_layout.addLayout(actions_row)

        # 结果区域 - Pivot + 卡片网格
        results_card = CardWidget()
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(0)

        # 标题栏：标签切换 + 视图切换（使用按钮代替 Pivot）
        header_bar = QWidget()
        header_bar.setStyleSheet("background: #f8f9fa; border-bottom: 1px solid #e0e0e0;")
        header_bar.setFixedHeight(44)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(2)

        # 标签切换按钮（使用普通按钮确保可见）
        self.tab_buttons = []
        tab_config = [
            ('safe', '安全', '#28a745', '#ffffff'),
            ('suspicious', '疑似', '#ffc107', '#000000'),
            ('dangerous', '危险', '#dc3545', '#ffffff')
        ]

        for tab_key, text, color, text_color in tab_config:
            btn = PushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(70)
            btn.setProperty('tab_key', tab_key)
            btn.setProperty('tab_color', color)
            btn.setProperty('tab_text_color', text_color)
            btn.clicked.connect(lambda checked, key=tab_key: self.on_tab_changed(key))
            # 美化样式
            btn.setStyleSheet(f'''
                PushButton {{
                    background: transparent;
                    border: 2px solid transparent;
                    color: #555;
                    padding: 6px 14px;
                    font-size: 14px;
                    font-weight: 500;
                    border-radius: 6px;
                    margin: 2px;
                }}
                PushButton:hover {{
                    background: rgba(0, 120, 212, 0.08);
                    border: 2px solid rgba(0, 120, 212, 0.3);
                }}
                PushButton:checked {{
                    background: {color};
                    color: {text_color};
                    border: 2px solid {color};
                    font-weight: 600;
                }}
            ''')
            header_layout.addWidget(btn)
            self.tab_buttons.append(btn)

        # 默认选中第一个
        self.tab_buttons[0].setChecked(True)
        self.current_tab = 'safe'

        header_layout.addStretch()

        results_layout.addWidget(header_bar)

        # 结果堆栈
        self.result_stack = QStackedWidget()

        for risk_type in ['safe', 'suspicious', 'dangerous']:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)
            scroll.setStyleSheet("QScrollArea { border: none; background: #fafafa; }")

            container = QWidget()
            # 创建卡片网格布局容器
            cards_container = QWidget()
            cards_container.setObjectName('cards_container')

            scroll_layout = QVBoxLayout(container)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(0)

            scroll_layout.addWidget(cards_container)
            scroll_layout.addStretch()

            setattr(self, f'{risk_type}_scroll_layout', scroll_layout)
            setattr(self, f'{risk_type}_cards_container', cards_container)

            # 空状态
            empty = BodyLabel('暂无项目')
            empty.setStyleSheet('color: #999; font-size: 13px;')
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName(f'{risk_type}_empty')
            self.empty_label = empty

            cards_layout = QVBoxLayout(cards_container)
            cards_layout.setContentsMargins(0, 0, 0, 0)
            cards_layout.addStretch()
            cards_layout.addWidget(empty)

            # 设置容器布局
            self._update_container_layout(cards_container)

            scroll.setWidget(container)
            self.result_stack.addWidget(scroll)

        results_layout.addWidget(self.result_stack)
        right_layout.addWidget(results_card, stretch=1)

        content_layout.addWidget(right_panel, stretch=1)
        main_layout.addWidget(content_widget, stretch=1)

        # 初始化
        self.system_scanner = SystemScanner()
        self.appdata_scanner = AppDataScanner()
        self.cleaner = Cleaner()

        for scanner in [self.system_scanner, self.appdata_scanner]:
            scanner.progress.connect(self.on_scan_progress)
            scanner.item_found.connect(self.on_item_found)
            scanner.error.connect(self.on_scan_error)
            scanner.complete.connect(self.on_scan_complete)

        # 不再连接Cleaner信号，使用新的CleanThread

        self._clean_thread = None

        self.current_mode = 'system'
        self.current_scanner = self.system_scanner

        from core.config_manager import get_config_manager
        self.config_mgr = get_config_manager()
        self.notification = WindowsNotification()

        # 初始化数据库
        from core.database import get_database
        self.db = get_database()

        # 初始化时根据设置控制AI按钮可见性
        ai_enabled = self.config_mgr.get_ai_config()['enabled']
        if not ai_enabled:
            self.ai_evaluate_btn.setVisible(False)

        # 初始化时根据设置控制AppData迁移按钮可见性
        appdata_migration_enabled = self.config_mgr.get('appdata_migration/enabled', False)
        if not appdata_migration_enabled:
            self.migration_btn.setVisible(False)

    def _create_compact_option(self, label_text, icon, checked):
        """创建紧凑选项行"""
        row = QWidget()
        row.setFixedHeight(36)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        label = BodyLabel(label_text)
        label.setStyleSheet('font-size: 13px;')
        layout.addWidget(label)

        layout.addStretch()

        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
        row.checkbox = checkbox
        layout.addWidget(checkbox)

        return row

    def on_tab_changed(self, tab_key: str):
        """标签切换事件"""
        self.current_tab = tab_key

        # 更新按钮状态
        for btn in self.tab_buttons:
            if btn.property('tab_key') == tab_key:
                btn.setChecked(True)
            else:
                btn.setChecked(False)

        # 更新结果页面
        index_map = {'safe': 0, 'suspicious': 1, 'dangerous': 2}
        self.result_stack.setCurrentIndex(index_map.get(tab_key, 0))

        # 更新 AI 评估按钮状态（仅当扫描完成且有对应风险级别项目时启用）
        if self.scan_results:
            current_count = self.risk_counts.get(tab_key, 0)
            self.ai_evaluate_btn.setEnabled(current_count > 0)

    def select_all_safe_items(self):
        """全选/取消全选当前标签页的所有项"""
        current_idx = self.result_stack.currentIndex()
        containers = [
            getattr(self, 'safe_cards_container'),
            getattr(self, 'suspicious_cards_container'),
            getattr(self, 'dangerous_cards_container')
        ]
        container = containers[current_idx] if current_idx < len(containers) else None

        if container:
            # 收集所有复选框
            all_checkboxes = []
            for i in range(container.layout().count()):
                item = container.layout().itemAt(i)
                if item and item.widget():
                    cb = item.widget().findChild(QCheckBox)
                    if cb:
                        all_checkboxes.append(cb)

            if all_checkboxes:
                # 判断当前是否全部选中
                all_checked = all(cb.isChecked() for cb in all_checkboxes)

                # 切换状态
                for cb in all_checkboxes:
                    cb.setChecked(not all_checked)

    def deselect_all_items(self):
        for risk_type in ['safe', 'suspicious', 'dangerous']:
            container = getattr(self, f'{risk_type}_cards_container')
            if container:
                for i in range(container.layout().count()):
                    item = container.layout().itemAt(i)
                    if item and item.widget():
                        cb = item.widget().findChild(QCheckBox)
                        if cb:
                            cb.setChecked(False)

    def on_select_toggle(self):
        """切换全选/取消全选状态"""
        current_idx = self.result_stack.currentIndex()
        if current_idx == 0:  # 安全选项卡
            risk_type = 'safe'
        elif current_idx == 1:  # 疑似选项卡
            risk_type = 'suspicious'
        else:  # 危险选项卡
            risk_type = 'dangerous'

        container = getattr(self, f'{risk_type}_cards_container')
        if not container:
            return

        # 检查当前容器的复选框状态
        total = 0
        checked = 0
        for i in range(container.layout().count()):
            item = container.layout().itemAt(i)
            if item and item.widget():
                cb = item.widget().findChild(QCheckBox)
                if cb:
                    total += 1
                    if cb.isChecked():
                        checked += 1

        # 如果全部选中则取消全选，否则全选
        should_check_all = (checked < total)

        for i in range(container.layout().count()):
            item = container.layout().itemAt(i)
            if item and item.widget():
                cb = item.widget().findChild(QCheckBox)
                if cb:
                    cb.setChecked(should_check_all)

        # 更新按钮文本
        self._update_select_button()

    def on_mode_changed(self, route_key: str):
        if self.is_scanning:
            InfoBar.warning(
                '扫描进行中',
                '请等待当前扫描完成后再切换选项卡',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            # 恢复原选项卡状态
            if self.current_mode == 'system':
                self.mode_segment.setCurrentItem('system')
            else:
                self.mode_segment.setCurrentItem('appdata')
            return

        appdata_migration_enabled = self.config_mgr.get('appdata_migration/enabled', False)

        if route_key == 'system':
            self.current_mode = 'system'
            self.current_scanner = self.system_scanner
            self.stack.setCurrentIndex(0)
            self.migration_btn.setVisible(False)
        elif route_key == 'appdata':
            self.current_mode = 'appdata'
            self.current_scanner = self.appdata_scanner
            self.stack.setCurrentIndex(1)
            self.migration_btn.setVisible(appdata_migration_enabled)

        self._clear_results()

    def update_appdata_migration_button(self):
        """更新AppData迁移按钮可见性"""
        appdata_migration_enabled = self.config_mgr.get('appdata_migration/enabled', False)
        if self.current_mode == 'appdata':
            self.migration_btn.setVisible(appdata_migration_enabled)
        else:
            self.migration_btn.setVisible(False)

    def _on_route_changed(self, route_key):
        """导航变化时的处理"""
        if route_key == 'system':
            # System Clean: 确保迁移按钮隐藏
            self.migration_btn.setVisible(False)

    def _clear_results(self):
        for checkbox, card, item in self.checkboxes:
            checkbox.deleteLater()
            card.deleteLater()
        self.checkboxes.clear()
        self.scan_results.clear()
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
        self.clean_btn.setEnabled(False)
        self.ai_evaluate_btn.setEnabled(False)
        self.scan_status.idle('准备扫描')
        self._update_stats()
        self.ai_review_results.clear()

        # 重置所有容器布局
        for key in ['safe', 'suspicious', 'dangerous']:
            container = getattr(self, f'{key}_cards_container')
            self._update_container_layout(container)

    def _update_stats(self):
        total = sum(self.risk_counts.values())
        total_size = sum(item.size for item in self.scan_results)
        self.quick_stats.setText(f'{total} 项 | {format_size(total_size)}')

        # 更新标签按钮文本：标签名 (数量)
        tab_names = {'safe': '安全', 'suspicious': '疑似', 'dangerous': '危险'}
        for i, (key, btn) in enumerate(zip(['safe', 'suspicious', 'dangerous'], self.tab_buttons)):
            count = self.risk_counts.get(key, 0)
            btn.setText(f'{tab_names[key]} ({count})')

        # 更新全选/取消全选按钮文本
        self._update_select_button()

    def _update_select_button(self):
        """更新全选/取消全选按钮文本"""
        current_idx = self.result_stack.currentIndex()
        if current_idx == 0:  # 安全选项卡
            risk_type = 'safe'
        elif current_idx == 1:  # 疑似选项卡
            risk_type = 'suspicious'
        else:  # 危险选项卡
            risk_type = 'dangerous'

        container = getattr(self, f'{risk_type}_cards_container')
        if not container:
            self.select_toggle_btn.setText(f'全选{risk_type}')
            return

        # 检查当前容器的复选框状态
        total = 0
        checked = 0
        for i in range(container.layout().count()):
            item = container.layout().itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 跳过空Label等非卡片widget
                if isinstance(widget, QLabel) and widget.objectName() and widget.objectName().endswith('_empty'):
                    continue

                cb = widget.findChild(QCheckBox)
                if cb:
                    total += 1
                    if cb.isChecked():
                        checked += 1

        tab_names = {'safe': '安全', 'suspicious': '疑似', 'dangerous': '危险'}
        name = tab_names.get(risk_type, '')

        if total == 0:
            self.select_toggle_btn.setText(f'全选{name}')
        elif checked == total:
            self.select_toggle_btn.setText(f'取消全选')
        else:
            self.select_toggle_btn.setText(f'全选{name}')

    @handle_errors
    def on_scan(self, checked=False):
        log_ui_event(logger, 'CLICK', 'SystemCleaner', element='扫描按钮')
        if self.current_mode == 'system':
            self.on_system_scan()
        else:
            self.on_appdata_scan()

    @handle_errors
    def on_system_scan(self):
        scan_types = []
        if self.temp_check.isChecked():
            scan_types.append('temp')
        if self.prefetch_check.isChecked():
            scan_types.append('prefetch')
        if self.logs_check.isChecked():
            scan_types.append('logs')
        if self.update_cache_check.isChecked():
            scan_types.append('update_cache')

        if not scan_types:
            logger.warning("[UI:SCAN] 用户未选择任何扫描类型")
            InfoBar.warning('提示', '请至少选择一种扫描类型', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        logger.info(f"[UI:SCAN] 开始系统扫描 - 扫描类型: {', '.join(scan_types)}")
        log_ui_event(logger, 'SCAN', 'SystemCleaner', elements=f"扫描类型: {', '.join(scan_types)}")

        # 设置扫描状态并禁用模式切换
        self.is_scanning = True
        self.mode_segment.setEnabled(False)

        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.ai_evaluate_btn.setEnabled(False)

        self._clear_results()
        self.scan_status.scanning('扫描系统文件...', 0, 0)
        self.status_label.setText('正在扫描...')

        self.system_scanner.start_scan(scan_types)

    @handle_errors
    def on_appdata_scan(self):
        scan_types = []
        if self.roaming_check.isChecked():
            scan_types.append('roaming')
        if self.local_check.isChecked():
            scan_types.append('local')
        if self.locallow_check.isChecked():
            scan_types.append('local_low')

        if not scan_types:
            logger.warning("[UI:SCAN] 用户未选择任何AppData文件夹类型")
            InfoBar.warning('提示', '请至少选择一种文件夹', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        logger.info(f"[UI:SCAN] 开始AppData扫描 - 文件夹类型: {', '.join(scan_types)}")
        log_ui_event(logger, 'SCAN', 'SystemCleaner', elements=f"AppData类型: {', '.join(scan_types)}")

        # 设置扫描状态并禁用模式切换
        self.is_scanning = True
        self.mode_segment.setEnabled(False)

        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.ai_evaluate_btn.setEnabled(False)

        self._clear_results()
        self.scan_status.scanning('扫描AppData...', 0, 0)
        self.status_label.setText('正在扫描...')

        self.appdata_scanner.start_scan(scan_types)

    def on_scan_progress(self, message):
        self.status_label.setText(message)
        logger.debug(f"[UI:SCAN] 进度更新: {message}")
        self.scan_status.scanning(message, len(self.scan_results), len(self.scan_results))

    def on_cancel(self):
        log_ui_event(logger, 'CANCEL', 'SystemCleaner', element='扫描取消按钮')
        logger.info("[UI:SCAN] 用户取消扫描")
        self.current_scanner.cancel_scan()
        self.cancel_btn.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.scan_status.idle('扫描已取消')
        self.status_label.setText('已取消')

        # 重置扫描状态并恢复选项卡切换
        self.is_scanning = False
        self.mode_segment.setEnabled(True)

    @handle_errors
    def on_item_found(self, item):
        risk_level_str = self._normalize_risk_level(item.risk_level)
        self.scan_results.append(item)
        self.risk_counts[risk_level_str] += 1

        # 更新状态指示器（带进度）
        progress = min(100, int(len(self.scan_results) / 100 * 100)) if len(self.scan_results) < 100 else 0
        self.scan_status.scanning(
            f'发现: {item.description[:20]}...',
            len(self.scan_results),
            len(self.scan_results),
            progress
        )

        self._update_stats()

        # 获取对应容器
        container = getattr(self, f'{risk_level_str}_cards_container')

        # 找到并隐藏 empty label
        empty_label = container.findChild(BodyLabel, f'{risk_level_str}_empty')
        if empty_label:
            empty_label.hide()

        # 创建卡片
        card, checkbox = self._create_item_card(item)

        # 单列垂直布局
        layout = container.layout()
        layout.insertWidget(layout.count() - 2, card)  # 插在 stretch 之前

        self.checkboxes.append((checkbox, card, item))

    def _normalize_risk_level(self, risk_level):
        if risk_level is None:
            return 'suspicious'
        if hasattr(risk_level, 'value'):
            return risk_level.value
        risk_str = str(risk_level).lower()
        if risk_str not in ['safe', 'suspicious', 'dangerous']:
            return 'suspicious'
        return risk_str

    def _update_item_explanation(self, item, ai_explanation):
        """第一阶段：只更新项目解释，不改变风险等级"""
        # 移除旧卡片并添加新卡片
        for i, (cb, row, it) in enumerate(self.checkboxes):
            if it.path == item.path:
                cb.deleteLater()
                row.deleteLater()
                self.checkboxes.pop(i)
                break

        # 只更新解释和方法，保持原有风险等级不变
        item.judgment_method = 'ai'
        item.ai_explanation = ai_explanation
        # 直接调用 on_item_found，不修改 risk_counts
        self.on_item_found(item)

    def on_ai_evaluate_current(self):
        """AI 评估当前选中风险级别的项目（排除已评估过的）"""
        tab_names = {'safe': '安全', 'suspicious': '疑似', 'dangerous': '危险'}
        tab_name = tab_names.get(self.current_tab, '')

        # 获取当前风险级别的项目，排除已被 AI 评估过的
        items = [
            item for item in self.scan_results
            if self._normalize_risk_level(item.risk_level) == self.current_tab
            and item.path not in self.ai_review_results  # 排除已评估过的
        ]

        logger.info(f"AI复核：找到 {len(items)} 个{tab_name}项（已过滤{self.risk_counts.get(self.current_tab,0)-len(items)}个已评估项）")

        if not items:
            InfoBar.info('提示', f'没有需要评估的{tab_name}项', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        # 取消现有任务
        self.cancel_ai_review()

        # 检查AI配置 - 使用新的配置管理器
        config_mgr = get_config_manager()
        cfg = config_mgr.get_ai_config()

        logger.info(f"AI配置检查：enabled={cfg['enabled']}, key长度={len(cfg['api_key'])}, url={cfg['api_url'][:50]}, model={cfg['api_model']}")

        # 显示AI复核组件
        self.ai_review_progress.setVisible(True)
        self.ai_review_summary.setVisible(True)
        self.ai_evaluate_btn.setEnabled(False)
        self.ai_evaluate_btn.setText("评估中...")

        # 根据是否有AI配置选择评估方式
        if cfg['enabled'] and cfg['api_key'] and cfg['api_url']:
            # 使用AI复核编排器
            ai_config = AIConfig(api_url=cfg['api_url'], api_key=cfg['api_key'], model=cfg['api_model'])
            ai_client = AIClient(ai_config)

            self.ai_review_orchestrator = AIReviewOrchestrator(
                config=ReviewConfig(max_concurrent=1, max_retries=2),
                ai_client=ai_client,
                parent=self
            )

            # 开始复核
            self.ai_review_worker = self.ai_review_orchestrator.start_review(
                items=items,
                on_progress=self._on_ai_progress,
                on_item_completed=self._on_ai_item_completed,
                on_item_failed=self._on_ai_item_failed,
                on_complete=self._on_ai_batch_complete
            )
        else:
            # 使用默认规则
            reason = 'AI未启用' if not cfg['enabled'] else 'AI配置不完整'
            logger.info(f"{reason}，使用默认规则评估")
            InfoBar.warning(reason, '请在设置中配置API密钥并启用AI开关', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self)
            self._evaluate_with_rules(items)

    def on_ai_evaluate_all(self):
        """AI 评估当前选中的项目（向后兼容）"""
        self.on_ai_evaluate_current()

    def _on_ai_progress(self, status: AIReviewStatus):
        """AI复核进度回调"""
        self.ai_review_progress.update_status(status)
        self.ai_review_summary.update_summary(status)

    def _on_ai_item_completed(self, path: str, result: AIReviewResult):
        """AI复核项目完成回调"""
        # 获取旧的风险等级
        old_risk = None
        for item in self.scan_results:
            if item.path == path:
                old_risk = item.risk_level
                break

        # 存储结果
        self.ai_review_results[path] = result

        # 更新风险等级计数
        if old_risk:
            old_risk_str = self._normalize_risk_level(old_risk)
            self.risk_counts[old_risk_str] = max(0, self.risk_counts.get(old_risk_str, 0) - 1)

        # 更新项目风险等级
        for item in self.scan_results:
            if item.path == path:
                item.risk_level = result.ai_risk
                break

        # 增加新的风险等级计数
        new_risk_str = self._normalize_risk_level(result.ai_risk)
        self.risk_counts[new_risk_str] = self.risk_counts.get(new_risk_str, 0) + 1

        # 更新统计显示
        self._update_stats()

        # 更新卡片显示（将卡片移动到新的风险等级容器）
        self._update_card_with_ai_result(path, result)

    def _on_ai_item_failed(self, path: str, error: str):
        """AI复核项目失败回调"""
        logger.warning(f"AI复核失败: {path}, 错误: {error}")

    def _on_ai_batch_complete(self, results: dict):
        """AI复核批次完成回调"""
        self.ai_evaluate_btn.setEnabled(True)
        self.ai_evaluate_btn.setText("AI评估当前项")
        self.ai_review_progress.setVisible(False)

        status_summary = f'AI复核完成: 成功 {len(results)} 项'
        self.status_label.setText(status_summary)

        InfoBar.success(
            '完成',
            status_summary,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def _update_card_with_ai_result(self, path: str, result: AIReviewResult):
        """使用AI结果更新卡片显示 - 将卡片移动到新的风险等级容器"""
        # 从checkboxes列表中找到并移除旧卡片
        idx_to_remove = None
        old_card = None
        for i, (cb, card, item) in enumerate(self.checkboxes):
            if item.path == path:
                idx_to_remove = i
                old_card = card
                break

        if idx_to_remove is not None:
            self.checkboxes.pop(idx_to_remove)

            # 从旧容器中移除卡片
            if old_card:
                # 从当前容器的布局中移除
                parent_layout = old_card.parent().layout()
                if parent_layout:
                    parent_layout.removeWidget(old_card)
                old_card.deleteLater()

        # 创建并添加新的AI卡片到正确的容器
        self._create_and_add_ai_card(result)

    def _remove_card_by_path(self, container, path: str, checkbox: QCheckBox):
        """移除指定路径的卡片 - 已废弃"""
        pass

    def _create_and_add_ai_card(self, result: AIReviewResult):
        """创建并添加AI复核卡片"""
        # 找到对应的ScanItem
        original_item = None
        for item in self.scan_results:
            if item.path == result.item_path:
                original_item = item
                break

        if not original_item:
            return

        # 转换ScanItem以使用新的风险等级
        original_item.risk_level = result.ai_risk
        risk_level_str = self._normalize_risk_level(result.ai_risk)
        container = getattr(self, f'{risk_level_str}_cards_container')
        layout = container.layout()

        # 创建AI卡片
        ai_card = AIReviewCard(original_item, result)
        ai_card.re_evaluate_requested.connect(self._on_re_evaluate_item)

        # 插入卡片 - 放在spacer前面
        from PyQt5.QtWidgets import QSpacerItem
        stretch_index = -1
        for i in range(layout.count()):
            item_at = layout.itemAt(i)
            if item_at and isinstance(item_at, QSpacerItem):
                stretch_index = i
                break

        if stretch_index != -1:
            layout.insertWidget(stretch_index, ai_card)
        else:
            layout.insertWidget(layout.count() - 1, ai_card)

        # 更新checkboxes - AI卡片有复选框
        self.checkboxes.append((ai_card.get_checkbox(), ai_card, original_item))

    def _on_re_evaluate_item(self, path: str):
        """重新评估单个项目"""
        # 更新卡片显示为"评估中"
        # TODO: 实现单个项目重新评估
        InfoBar.info('提示', f'正在重新评估: {path[:30]}...', position=InfoBarPosition.TOP, parent=self)

    def cancel_ai_review(self):
        """取消AI复核"""
        if self.ai_review_orchestrator:
            self.ai_review_orchestrator.cancel_review()

        if self.ai_review_worker:
            self.ai_review_worker.cancel()

        self.ai_review_progress.setVisible(False)
        self.ai_evaluate_btn.setEnabled(True)
        self.ai_evaluate_btn.setText("AI评估当前项")

    def _evaluate_with_ai(self, items, api_key, api_url, ai_model):
        """使用AI进行评估 - 第一阶段：只更新描述，不改变风险等级"""
        try:
            from qfluentwidgets import InfoBar, InfoBarPosition
            from core.ai_client import AIClient, AIConfig
            from core.annotation import RiskLevel
            import json

            logger.info(f"AI评估开始: 项目数={len(items)}, API={api_url}, Model={ai_model}")

            # 创建AI客户端
            config = AIConfig(api_url=api_url, api_key=api_key, model=ai_model)
            ai_client = AIClient(config)

            # 测试API连接
            logger.info("测试API连接...")
            success, test_msg = ai_client.test_connection()

            if success:
                InfoBar.success('API连接正常', '开始AI评估...', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
                logger.info(f"API连接测试成功: {test_msg}")
            else:
                InfoBar.error('API连接失败', test_msg, orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)
                logger.error(f"API连接测试失败: {test_msg}")
                self.ai_evaluate_btn.setEnabled(True)
                self.scan_status.error('API连接失败')
                return

            evaluated_count = 0
            for item in items:
                try:
                    logger.info(f"评估项目 {evaluated_count+1}/{len(items)}: {os.path.basename(item.path)}")

                    # 构建评估提示词
                    prompt = self._build_ai_prompt(item)
                    logger.debug(f"AI请求: {prompt[:100]}...")

                    messages = [{'role': 'user', 'content': prompt}]
                    success, response = ai_client.chat(messages)

                    logger.debug(f"AI响应: success={success}, 响应长度={len(response) if response else 0}")

                    if success:
                        # 解析AI响应
                        new_risk, reason = self._parse_ai_response(response)
                        # 第一阶段：只更新描述文字，不改变风险等级
                        if reason:
                            logger.info(f"AI分析结果: description={reason}")
                            self._update_item_explanation(item, reason)
                        else:
                            logger.warning(f"AI响应解析未找到有效描述: {response}")
                    else:
                        logger.warning(f"AI评估失败: {response}")

                    evaluated_count += 1
                    self.scan_status.scanning(f'AI 评估中... {evaluated_count}/{len(items)}', evaluated_count, evaluated_count)

                except Exception as e:
                    logger.error(f"AI评估项 {item.path} 失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            logger.info(f"AI评估完成，成功处理 {evaluated_count} 项")

            self.scan_status.complete(evaluated_count)
            self.ai_evaluate_btn.setEnabled(True)
            self.ai_evaluate_btn.setText("AI评估当前项")
            self.status_label.setText(f'AI 评估完成')

            InfoBar.success('完成', f'已评估 {evaluated_count} 项', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self)

        except Exception as e:
            logger.error(f"AI评估过程异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.ai_evaluate_btn.setEnabled(True)
            self.ai_evaluate_btn.setText("AI评估当前项")
            self.scan_status.error('AI 评估失败')
            InfoBar.error('错误', f'AI 评估失败: {str(e)}', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)

    def _evaluate_with_rules(self, items):
        """使用默认规则进行评估"""
        keywords = {
            'safe': ['cache', 'temp', 'tmp', 'logs', 'log', 'download', 'prefetch', 'thumb', 'thumbnail', 'codecache', 'gpucache'],
            'dangerous': ['data', 'settings', 'config', 'profile', 'save', 'sync', 'plugin', 'extension', 'user', 'database', 'db']
        }

        evaluated_count = 0
        for item in items:
            folder = os.path.basename(item.path).lower()

            if any(k in folder for k in keywords['safe']):
                self._update_item_risk(item, 'safe')
            elif any(k in folder for k in keywords['dangerous']):
                self._update_item_risk(item, 'dangerous')
            else:
                # 默认为危险，保守策略
                self._update_item_risk(item, 'dangerous')

            evaluated_count += 1
            self.scan_status.scanning(f'规则评估中... {evaluated_count}/{len(items)}', evaluated_count, evaluated_count)

        self.scan_status.complete(evaluated_count)
        self.ai_evaluate_btn.setEnabled(True)
        self.ai_evaluate_btn.setText("AI评估当前项")
        self.status_label.setText(f'规则评估完成')

    def _create_mock_result(self, item, index):
        """创建模拟AI评估结果"""
        # 简单的规则模拟
        import random
        original_risk = self._normalize_risk_level(item.risk_level)
        risk_options = ['safe', 'dangerous'] if original_risk != 'dangerous' else ['safe', 'suspicious']
        new_risk = random.choice(risk_options)

        reasons = {
            'safe': ['缓存目录可清理', '临时文件', '临时数据'],
            'suspicious': ['需用户确认', '配置文件', '应用数据'],
            'dangerous': ['包含敏感数据', '系统关键文件', '用户数据']
        }

        return {
            'new_risk': new_risk,
            'reason': random.choice(reasons.get(new_risk, ['需确认']))
        }

    def _build_ai_prompt(self, item):
        """构建AI评估提示词 - 第一阶段：只生成描述文字

        参考 AppDataCleaner 项目格式
        """
        size_str = self._format_size(item.size)
        folder_name = os.path.basename(item.path)

        return f"""# 角色：Windows AppData分析专家

## 任务
分析用户提供的[{folder_name}]文件夹信息，给出简要的功能描述。

## 输出格式（严格按照以下格式）
```
- 软件名称：<应用程序名称>
- 数据类别：[配置|缓存|用户数据|日志|临时文件]
- 应用用途：<简要描述（限30字以内）>
- 管理建议：[可安全删除|需用户确认|不建议删除]
```

## 示例输出
缓存文件夹：
- 软件名称：Chrome
- 数据类别：缓存
- 应用用途：浏览器临时缓存数据
- 管理建议：可安全删除

配置文件夹：
- 软件名称：应用名
- 数据类别：配置
- 应用用途：商店应用设置信息
- 管理建议：需用户确认

## 待分析信息
- 文件夹名称: {folder_name}
- 路径: {item.path}
- 大小: {size_str}
- 类型: {item.item_type}

## 处理规则
1. 保持输出格式的严格一致性
2. 应用用途描述必须30字以内
3. 不添加任何额外解释或评论
"""


    def _parse_ai_response(self, response):
        """解析AI响应 - 第一阶段：只解析描述文字，不改变风险等级

        参考 AppDataCleaner 格式：
        - 软件名称：<应用程序名称>
        - 数据类别：[配置|缓存|用户数据|日志|临时文件]
        - 应用用途：<简要描述（限30字以内）>
        - 管理建议：[可安全删除|需用户确认|不建议删除]
        """
        response = response.strip()

        # 提取应用用途（灰色小字显示）
        import re

        # 尝试提取"应用用途"后的内容
        pattern1 = r'(?:应用用途)(?::|：)\s*(.+?)(?:\n|$)'
        match = re.search(pattern1, response)

        # 处理管理建议，可能用于以后的风险评估
        pattern2 = r'(?:管理建议)(?::|：)\s*(.+?)(?:\n|$)'
        recommendation_match = re.search(pattern2, response)

        # 提取数据类别
        pattern3 = r'(?:数据类别)(?::|：)\s*(.+?)(?:\n|$)'
        category_match = re.search(pattern3, response)

        # 提取软件名称
        pattern4 = r'(?:软件名称)(?::|：)\s*(.+?)(?:\n|$)'
        name_match = re.search(pattern4, response)

        if name_match:
            software_name = name_match.group(1).strip()
        else:
            software_name = "未知应用"

        if category_match:
            data_category = category_match.group(1).strip()
        else:
            data_category = "未知类型"

        if match:
            # 找到应用用途
            purpose = match.group(1).strip()

            # 组合简短描述（用于灰色小字）
            # 第一阶段：显示软件名称 + 用途
            description = f"{software_name} - {purpose}"

            # 清理多余的标点和空白
            description = re.sub(r'[，。；;！!？?\n\r]', '', description)

            # 如果描述仍然太长，截断
            if len(description) > 50:
                description = description[:50] + "..."

            # 第一阶段：不改变风险等级
            # 返回空的风险等级，保持规则判断的结果
            return '', description
        else:
            # 备用：尝试直接使用AI返回的文本作为描述
            # 取前40个字符作为描述
            clean_response = re.sub(r'[#\-\*]', '', response)
            clean_response = re.sub(r'\s+', ' ', clean_response)
            clean_response = clean_response.strip()

            if len(clean_response) > 40:
                description = clean_response[:40] + "..."
            else:
                description = clean_response

            return '', description

    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        if size < 1024:
            return str(size)
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        elif size < 1024 * 1024 * 1024:
            return f'{size / (1024 * 1024):.1f} MB'
        else:
            return f'{size / (1024 * 1024 * 1024):.1f} GB'

    def _update_item_risk(self, item, new_risk, method='rule', ai_explanation=''):
        """更新项目风险等级和评估方法

        Args:
            item: 要更新的扫描项目
            new_risk: 新的风险等级
            method: 评估方法 ('rule' 或 'ai')
            ai_explanation: AI输出的说明
        """
        # 移除旧卡片并添加新卡片
        for i, (cb, row, it) in enumerate(self.checkboxes):
            if it.path == item.path:
                self.risk_counts[it.risk_level] -= 1
                cb.deleteLater()
                row.deleteLater()
                self.checkboxes.pop(i)
                break

        item.risk_level = new_risk
        item.judgment_method = method
        item.ai_explanation = ai_explanation
        self.risk_counts[new_risk] += 1
        self._update_stats()
        self.on_item_found(item)

    def on_scan_error(self, message):
        try:
            self.scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.scan_status.error(message)
            InfoBar.error('扫描错误', message, orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)
        except Exception as e:
            logger.error(f"处理扫描错误失败: {e}")

    @handle_errors
    def on_scan_complete(self, results):
        # 重置扫描状态并恢复选项卡切换
        self.is_scanning = False
        self.mode_segment.setEnabled(True)

        self.scan_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)

        result_count = len(results) if results else 0
        total_size = sum(item.size for item in results) if results else 0
        self.status_label.setText(f'扫描完成！发现 {result_count} 项 | {format_size(total_size)}')

        if results:
            self.scan_status.complete(result_count)
            self.clean_btn.setEnabled(True)
            # AI 复核按钮处理（根据当前选中的风险级别启用按钮）
            current_count = self.risk_counts.get(self.current_tab, 0)
            self.ai_evaluate_btn.setEnabled(current_count > 0)

            if self.notification.is_enabled():
                try:
                    self.notification.show_scan_complete(result_count, total_size)
                except Exception as e:
                    logger.warning(f"发送通知失败: {e}")
        else:
            self.scan_status.idle('未发现项目')

    @handle_errors
    def on_clean(self, *args, **kwargs):
        """清理选中项目 - 重新实现的简洁版本"""
        log_ui_event(logger, 'CLEAN', 'SystemCleaner')

        # 获取选中的项目
        selected_items = []
        for cb, _, item in self.checkboxes:
            if cb is not None and cb.isChecked():
                selected_items.append(item)

        if not selected_items:
            logger.warning("[UI:CLEAN] 用户未选择任何要清理的项目")
            InfoBar.warning('提示', '请先选择要清理的项目', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        # 总大小
        total_size = sum(item.size for item in selected_items)

        logger.info(f"[UI:CLEAN] 开始清理选中项目 - 数量: {len(selected_items)}, 大小: {format_size(total_size)}")

        # 提示确认
        from PyQt5.QtWidgets import QMessageBox
        confirm = QMessageBox.question(
            self,
            '确认清理',
            f'将删除 {len(selected_items)} 个项目，释放 {format_size(total_size)}。\n文件将被移到回收站。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            logger.info("[UI:CLEAN] 用户取消清理确认")
            return

        logger.info("[UI:CLEAN] 用户确认清理，开始执行")

        # 禁用按钮
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)

        # 使用扫描状态显示清理进度
        self.scan_status.scanning('准备清理...', 0, len(selected_items))
        self.status_label.setText('')

        # 开始清理
        clean_type = 'system' if self.current_mode == 'system' else 'appdata'

        # 记录清理事件
        log_clean_event(
            logger,
            'START',
            clean_type,
            items=[item.description for item in selected_items[:5]],
            deleted=len(selected_items),
            freed=format_size(total_size)
        )

        # 异步清理
        self._clean_thread = CleanThread(selected_items, clean_type, self)
        self._clean_thread.finished.connect(self._on_clean_finished)
        self._clean_thread.error_occurred.connect(self._on_clean_error)
        self._clean_thread.progress_updated.connect(self._on_clean_progress)
        self._clean_thread.status_message.connect(self._on_clean_status_message)  # 新增：状态消息
        self._clean_thread.item_deleted.connect(self._on_item_deleted_in_thread)  # 新增：单个项目删除回调
        self._clean_thread.start()

    def _on_clean_progress(self, current, total, message=''):
        """清理进度更新 - 使用扫描状态显示"""
        progress = int((current / total) * 100) if total > 0 else 0
        msg = message or '正在清理...'
        self.scan_status.scanning(msg, current, total, progress)

    def _on_clean_status_message(self, message: str):
        """清理状态消息"""
        self.status_label.setText(message)

    def _on_clean_error(self, error_msg):
        """清理错误"""
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.scan_status.error('清理失败')
        self.status_label.setText(f'错误: {error_msg}')
        InfoBar.error('清理失败', error_msg, orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)
        logger.error(f"清理错误: {error_msg}")

    def _on_item_deleted_in_thread(self, path: str, item: ScanItem):
        """实时删除项目卡片（在主线程中执行）"""
        # 从checkboxes中找到并移除对应卡片
        for i, (cb, card, card_item) in list(enumerate(self.checkboxes)):
            if card_item.path == path:
                # 变灰卡片（表示删除中/已删除）
                card.setEnabled(False)

                # 获取卡片样式类
                card_type = type(card).__name__

                # 应用变灰样式
                if card_type == 'SimpleCardWidget':
                    card.setStyleSheet('''
                        SimpleCardWidget {
                            background: #f5f5f5;
                            border: 1px solid #e0e0e0;
                            border-radius: 12px;
                            opacity: 0.5;
                        }
                        SimpleCardWidget * {
                            color: #bbb;
                        }
                    ''')
                else:
                    # AI卡片等其他类型
                    card.setStyleSheet('''
                        * {
                            background: #f5f5f5;
                            opacity: 0.5;
                        }
                        * {
                            color: #bbb;
                        }
                    ''')

                # 从checkboxes列表中移除（稍后完全删除）
                self.checkboxes.pop(i)

                # 使用QTimer延迟完全移除卡片，给用户看到删除效果的时间
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(500, lambda c=card: self._fully_remove_card(c))

                # 更新计数
                norm_risk = str(item.risk_level) if hasattr(item.risk_level, 'value') else str(item.risk_level)
                self.risk_counts[norm_risk.lower()] = max(0, self.risk_counts.get(norm_risk.lower(), 0) - 1)
                self._update_stats()
                break

    def _fully_remove_card(self, card):
        """完全移除卡片"""
        try:
            if card.parent():
                layout = card.parent().layout()
                if layout:
                    layout.removeWidget(card)
            card.deleteLater()
        except:
            pass

    def show_migration_dialog(self):
        """显示 AppData 文件夹迁移对话框"""
        log_ui_event(logger, 'CLICK', 'SystemCleaner', element='迁移工具按钮')
        dialog = AppDataMigrationDialog(self)
        dialog.exec()
        logger.info("[UI:MIGRATION] 迁移对话框已打开")

    def _on_item_delete_failed(self, path: str, error: str):
        """项目删除失败回调"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from qfluentwidgets import InfoBar, InfoBarPosition

        # 显示删除失败提示
        InfoBar.error('删除失败', f'{path}: {error}', orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_clean_finished(self, result):
        """清理完成"""
        # 调试日志
        logger.debug(f"清理完成信号接收: {result}")

        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)

        deleted_count = result.get('deleted_count', 0)
        skipped_count = result.get('skipped_count', 0)  # 因权限等跳过的数量
        total_requested = deleted_count + skipped_count + len(result.get('errors', []))
        errors = result.get('errors', [])

        # 扫描完成后更新状态显示
        if deleted_count > 0:
            self.scan_status.complete(deleted_count)
        elif skipped_count > 0:
            self.scan_status.idle(f'完成！{deleted_count}已删除，{skipped_count}跳过')
        else:
            self.scan_status.idle('清理完成')

        # 构建进度消息
        parts = []
        if deleted_count > 0:
            parts.append(f'删除 {deleted_count} 项')
        if skipped_count > 0:
            parts.append(f'跳过 {skipped_count} 项')
        if errors and deleted_count == 0:
            parts.append(f'失败 {len(errors)} 项')

        status_msg = '，'.join(parts) if parts else '没有项目被清理'
        self.status_label.setText(f'清理完成！{status_msg}')

        # 显示结果提示
        if deleted_count > 0:
            total_size = result.get('total_size', 0)
            InfoBar.success('清理完成', f'成功删除 {deleted_count} 项，释放 {format_size(total_size)}',
                         orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=3000, parent=self)
        elif skipped_count > 0:
            InfoBar.warning('清理部分完成', f'{skipped_count} 项因权限不足跳过（尝试以管理员身份运行以删除系统文件）',
                           orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)
        elif errors:
            InfoBar.error('清理失败', '所有项目删除失败，请检查文件权限',
                         orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)

        # 添加清理历史（记录尝试的操作）
        if total_requested > 0:
            try:
                clean_type = 'system' if self.current_mode == 'system' else 'appdata'
                actual_size = result.get('total_size', 0)
                details_list = []
                if deleted_count > 0:
                    details_list.append(f'成功: {deleted_count}项')
                if skipped_count > 0:
                    details_list.append(f'跳过: {skipped_count}项（权限不足）')
                if errors:
                    details_list.append(f'失败: {len(errors)}项')

                self.db.add_clean_history(
                    clean_type=clean_type,
                    items_count=deleted_count,
                    total_size=actual_size,
                    duration_ms=result.get('duration_ms', 0),
                    details='; '.join(details_list) if details_list else '尝试清理失败'
                )
                logger.info(f"已添加清理历史记录: 尝试{total_requested}项，成功{deleted_count}项，跳过{skipped_count}项")
            except Exception as e:
                logger.error(f"添加清理历史失败: {e}")

        # 检查是否所有项目都被删除了
        if not self.checkboxes:
            self.clean_btn.setEnabled(False)

    def _update_container_layout(self, container):
        """更新容器布局（固定单列模式）"""
        # 获取现有卡片和 empty label
        cards = []
        empty_label = None
        layout = container.layout()

        # 收集所有widget
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.objectName() and widget.objectName().endswith('_empty'):
                    empty_label = widget
                elif not isinstance(widget, QSpacerItem):
                    cards.append(widget)

        # 清除现有布局
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)

        # 设置单列垂直布局
        new_layout = QVBoxLayout(container)
        new_layout.setContentsMargins(12, 12, 12, 12)
        new_layout.setSpacing(8)
        new_layout.setAlignment(Qt.AlignTop)

        # 添加卡片
        for card in cards:
            new_layout.addWidget(card)

        # 添加 spacer
        new_layout.addStretch()

        # 添加 empty label（如果存在）
        if empty_label:
            empty_label.setParent(container)
            new_layout.addWidget(empty_label)

    def _create_item_card(self, item):
        """创建扫描项目卡片"""
        # 检查是否有AI复核结果
        ai_result = self.ai_review_results.get(item.path)

        if ai_result:
            # 使用AI复核卡片
            card = AIReviewCard(item, ai_result)
            card.re_evaluate_requested.connect(self._on_re_evaluate_item)
            # 固定单列模式高度（AI卡片始终显示完整内容）
            # AI卡片高度在内部设置，不再需要外部设置
            return card, card.get_checkbox()

        # 使用标准卡片
        card = SimpleCardWidget()
        card.setFixedHeight(120)  # 固定单列模式高度
        card.setStyleSheet('''
            SimpleCardWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            SimpleCardWidget:hover {
                border: 1px solid #0078D4;
            }
        ''')

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 规范化风险等级
        risk_level_str = self._normalize_risk_level(item.risk_level)

        # 第一行：图标 + 路径 + 判断方法标签 + 复选框（右边）
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # 风险图标
        color = {'safe': '#28a745', 'suspicious': '#ffc107', 'dangerous': '#dc3545'}.get(risk_level_str, '#999')
        risk_icon_map = {'safe': FluentIcon.CHECKBOX, 'suspicious': FluentIcon.INFO, 'dangerous': FluentIcon.DELETE}
        risk_icon = IconWidget(risk_icon_map.get(risk_level_str, FluentIcon.INFO))
        risk_icon.setFixedSize(22, 22)
        risk_icon.setStyleSheet(f'color: {color};')
        top_row.addWidget(risk_icon)

        # 路径
        path_label = BodyLabel(item.description[:20] + '...' if len(item.description) > 20 else item.description)
        path_label.setStyleSheet('font-size: 13px; font-weight: 500; color: #2c2c2c;')
        path_label.setWordWrap(True)
        top_row.addWidget(path_label, stretch=1)

        # 判断方法标签
        method_text = 'AI判断' if getattr(item, 'judgment_method', '') == 'ai' else '规则判断'
        method_label = BodyLabel(method_text)
        method_style = '''
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 500;
        '''
        if getattr(item, 'judgment_method', '') == 'ai':
            method_label.setStyleSheet(method_style + 'background: #e3f2fd; color: #1976d2;')
        else:
            method_label.setStyleSheet(method_style + 'background: #f1f3f4; color: #5f6368;')
        top_row.addWidget(method_label)

        # 复选框（移到右边）
        cb = QCheckBox()
        cb.setChecked(risk_level_str == 'safe')
        cb.setFixedSize(20, 20)
        top_row.addWidget(cb)

        # 第二行：文件大小 + AI说明（如果有）
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        # 文件大小
        size_label = BodyLabel(f'{format_size(item.size)}')
        size_label.setStyleSheet('font-size: 11px; color: #888;')
        info_row.addWidget(size_label)

        # AI说明（灰色小字，如果有的话）
        ai_explanation = getattr(item, 'ai_explanation', '')
        if ai_explanation and getattr(item, 'judgment_method', '') == 'ai':
            ai_label = BodyLabel(f'• {ai_explanation}')
            ai_label.setStyleSheet('font-size: 11px; color: #999; font-style: italic;')
            ai_label.setWordWrap(True)
            info_row.addWidget(ai_label, stretch=1)
        else:
            info_row.addStretch()

        layout.addLayout(top_row)
        layout.addLayout(info_row)

        return card, cb


class CleanThread(QThread):
    """清理线程 - 异步执行清理任务

    支持自定义回收站和系统回收站两种模式：
    - 自定义回收站：将文件移动到自定义目录并压缩
    - 系统回收站：使用 send2trash 移动到 Windows 回收站
    """

    # 信号定义
    finished = pyqtSignal(dict)  # 清理完成
    error_occurred = pyqtSignal(str)  # 清理错误
    progress_updated = pyqtSignal(int, int, str)  # 进度更新 (current, total, message)
    item_deleted = pyqtSignal(str, object)  # 项目删除 (path, card_obj)
    item_delete_failed = pyqtSignal(str, str)  # 项目删除失败 (path, error)
    status_message = pyqtSignal(str)  # 状态消息

    def __init__(self, items, clean_type: str, parent=None):
        super().__init__(parent)
        self.items = items  # 接收的items列表
        self.clean_type = clean_type
        self.is_cancelled = False

        # 加载回收站配置
        self._load_recycle_config()

    def _load_recycle_config(self):
        """加载回收站配置"""
        from core.config_manager import get_config_manager
        config_mgr = get_config_manager()
        recycle_cfg = config_mgr.get('recycle', {})

        self.recycle_enabled = recycle_cfg.get('enabled', False)
        self.recycle_folder = recycle_cfg.get('folder_path', '')

        # 初始化自定义回收站
        if self.recycle_enabled:
            import os
            if not self.recycle_folder:
                self.recycle_folder = os.path.join(os.path.expanduser('~'), 'PurifyAI_RecycleBin')

            # 确保回收站目录存在
            norm_path = os.path.normpath(self.recycle_folder)
            os.makedirs(norm_path, exist_ok=True)
            self.recycle_folder = norm_path

            # 初始化 CustomRecycleBin
            self.custom_recycle = get_custom_recycle_bin(self.recycle_folder)
            logger.info(f"使用自定义回收站: {self.recycle_folder}")
        else:
            # 不使用自定义回收站，使用 Windows 系统回收站
            self.recycle_folder = None
            self.custom_recycle = None
            logger.info("使用 Windows 系统回收站")

    def run(self):
        """执行清理任务"""
        try:
            start_time = time.time()
            deleted_count = 0
            skipped_count = 0  # 权限不足跳过的数量
            total_size = 0
            errors = []
            deleted_paths = []

            self.status_message.emit(f'准备清理 {len(self.items)} 个项目...')

            for i, item in enumerate(self.items):
                if self.is_cancelled:
                    self.status_message.emit('清理已取消')
                    break

                # 更新进度 - 带详细消息
                item_name = os.path.basename(item.path)
                progress_msg = f'正在清理 ({i+1}/{len(self.items)}): {item_name[:50]}'
                self.progress_updated.emit(i + 1, len(self.items), progress_msg)
                self.status_message.emit(progress_msg)

                try:
                    # 根据配置选择删除方式
                    if self.recycle_enabled and self.custom_recycle is not None:
                        # 使用自定义回收站（统一的 CustomRecycleBin）
                        try:
                            # 获取风险等级
                            risk_level = self._normalize_risk_level(item.risk_level)
                            success = self.custom_recycle.recycle_item(
                                item_path=item.path,
                                original_size=item.size,
                                description=item.description,
                                risk_level=risk_level
                            )
                            size = item.size if success else 0

                            # 如果自定义回收站失败，回退到系统回收站
                            if not success:
                                logger.warning(f"自定义回收站失败，回退到系统回收站: {item.path}")
                                success, size = self._move_to_system_recycle(item)
                        except PermissionError:
                            # 权限错误，回退到系统回收站
                            logger.warning(f"权限不足，回退到系统回收站: {item.path}")
                            success, size = self._move_to_system_recycle(item)
                        except Exception as e:
                            logger.warning(f"自定义回收站异常，回退到系统回收站: {item.path} - {e}")
                            success, size = self._move_to_system_recycle(item)
                    else:
                        # 使用系统回收站
                        success, size = self._move_to_system_recycle(item)

                    if success:
                        deleted_count += 1
                        total_size += size
                        deleted_paths.append(item.path)

                        # 发送删除信号（传递路径，UI层需要自己找到对应卡片）
                        self.item_deleted.emit(item.path, item)

                        logger.info(f"删除成功: {item.path[:100]}")
                    else:
                        skipped_count += 1
                        logger.warning(f"跳过项目: {item.description}")

                except FileNotFoundError:
                    # 文件不存在，可能已被删除
                    logger.info(f"文件不存在，跳过: {item.path}")
                    deleted_count += 1
                    deleted_paths.append(item.path)
                    self.item_deleted.emit(item.path, item)

                except PermissionError as e:
                    error_msg = f"权限不足: {item.description}"
                    errors.append(error_msg)
                    skipped_count += 1
                    logger.error(f"{error_msg}: {e}")
                    self.item_delete_failed.emit(item.path, "权限不足")

                except OSError as e:
                    # 处理其他操作系统错误
                    error_msg = f"系统错误: {item.description}"
                    errors.append(f"{error_msg}: {str(e)}")
                    skipped_count += 1
                    logger.error(f"{error_msg}: {e}")
                    self.item_delete_failed.emit(item.path, str(e))

                except Exception as e:
                    import traceback
                    error_msg = f"未知错误: {item.description}"
                    errors.append(f"{error_msg}: {str(e)}")
                    skipped_count += 1
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
                    self.item_delete_failed.emit(item.path, str(e))

            duration_ms = int((time.time() - start_time) * 1000)

            # 返回结果
            result = {
                'success': len(errors) == 0,
                'deleted_count': deleted_count,
                'skipped_count': skipped_count,
                'total_size': total_size,
                'errors': errors,
                'cancelled': self.is_cancelled,
                'duration_ms': duration_ms,
                'deleted_paths': deleted_paths
            }

            if len(errors) > 0 and deleted_count > 0:
                # 部分成功
                result['success'] = True

            logger.info(f"清理完成: 成功{deleted_count}项, 跳过{skipped_count}项, 释放{format_size(total_size)}, {len(errors)}错误")

            self.finished.emit(result)

        except Exception as e:
            import traceback
            error_msg = f"清理过程异常: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.error_occurred.emit(error_msg)

    def _normalize_risk_level(self, risk_level) -> str:
        """规范化风险等级为字符串"""
        if hasattr(risk_level, 'value'):
            return risk_level.value
        elif isinstance(risk_level, str):
            return risk_level
        else:
            return str(risk_level).lower()

    def _move_to_system_recycle(self, item) -> tuple[bool, int]:
        """移动文件到 Windows 系统回收站

        Args:
            item: 要移动的 ScanItem

        Returns:
            (success, size) 是否成功，大小
        """
        try:
            import send2trash

            # 使用 send2trash 安全删除到回收站
            logger.debug(f"移动到系统回收站: {item.path}")
            send2trash.send2trash(item.path)

            return True, item.size

        except Exception as e:
            logger.error(f"系统回收站失败: {item.path} -> {e}")
            raise

    def cancel(self):
        """取消清理"""
        self.is_cancelled = True
