"""
浏览器清理页面 UI - 紧凑高效设计
"""
import os
import functools
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QCheckBox, QDialog, QFrame, QStackedWidget, QSpacerItem
)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ProgressBar, CardWidget, FluentIcon, IconWidget, Pivot, InfoBar, InfoBarPosition
)

from core import BrowserScanner, Cleaner, format_size, ScanItem
from core.annotation import RiskLevel
from core.error_handler import catch_errors, logger, get_error_handler
from core.config_manager import get_config_manager

# 本地logger用于线程
_thread_logger = logging.getLogger(__name__)


# 简化的错误处理装饰器
def handle_errors(func):
    """错误处理装饰器 - 捕获并记录所有异常"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            error_handler = get_error_handler()
            error_handler.log_error(e, f"[BrowserCleaner.{func.__name__}]")
            if hasattr(self, 'status_label'):
                try:
                    self.status_label.setText(f'错误: {str(e)}')
                except:
                    pass
            # 返回 None 避免导致进一步的错误
            return None
    return wrapper
from ui.confirm_dialog import ConfirmDialog
from ui.windows_notification import WindowsNotification
from ui.scan_status_widget import ScanStatusWidget


class BrowserCleanerPage(QWidget):
    """浏览器清理页面 - 紧凑设计"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = []
        self.checkboxes = []
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # ========== 标题区 ==========
        header_layout = QHBoxLayout()
        title = StrongBodyLabel('浏览器清理')
        title.setStyleSheet('font-size: 24px;')
        header_layout.addWidget(title)
        header_layout.addSpacing(20)

        # 快速统计
        self.quick_stats = BodyLabel('0 项 | 0 B')
        self.quick_stats.setStyleSheet('color: #666666; font-size: 14px;')
        header_layout.addWidget(self.quick_stats)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ========== 主内容 ==========
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(12)

        # ========== 左侧：浏览器选择 ==========
        self.settings_panel = SimpleCardWidget()
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(12, 12, 12, 12)
        settings_layout.setSpacing(8)
        self.settings_panel.setFixedWidth(220)

        # 浏览器选项
        browsers = [
            ('chrome', 'Chrome', FluentIcon.GLOBE, True),
            ('edge', 'Edge', FluentIcon.GLOBE, True),
            ('firefox', 'Firefox', FluentIcon.GLOBE, True),
        ]

        for key, label, icon, checked in browsers:
            row = self._create_compact_option(label, icon, checked)
            setattr(self, f'{key}_check', row.checkbox)
            settings_layout.addWidget(row)

        settings_layout.addStretch()

        # 扫描按钮
        self.scan_btn = PrimaryPushButton(FluentIcon.SEARCH, '扫描')
        self.scan_btn.clicked.connect(self.on_scan)
        self.scan_btn.setFixedHeight(40)
        settings_layout.addWidget(self.scan_btn)

        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.on_cancel_scan)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(36)
        settings_layout.addWidget(self.cancel_btn)

        content_layout.addWidget(self.settings_panel)

        # ========== 右侧：结果 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        # 扫描状态组件
        self.scan_status = ScanStatusWidget()
        right_layout.addWidget(self.scan_status)

        # 状态标签（用于其他消息）
        self.status_label = BodyLabel('就绪')
        self.status_label.setStyleSheet('font-size: 12px; color: #666;')
        right_layout.addWidget(self.status_label)

        # 操作行
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.select_all_btn = PushButton('全选')
        self.select_all_btn.clicked.connect(self.select_all_items)
        self.select_all_btn.setFixedHeight(32)
        actions_row.addWidget(self.select_all_btn)

        self.clean_btn = PushButton('清理')
        self.clean_btn.clicked.connect(self.on_clean)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setStyleSheet("PushButton { background: #dc3545; color: white; border: none; }")
        self.clean_btn.setFixedHeight(32)
        self.clean_btn.setMinimumWidth(80)
        actions_row.addWidget(self.clean_btn)

        actions_row.addStretch()
        right_layout.addLayout(actions_row)

        # 结果区域 - Pivot + 卡片网格
        results_card = CardWidget()
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(0, 0, 0, 0)

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

        self.scanner = BrowserScanner()
        self.cleaner = Cleaner()

        self.scanner.progress.connect(self.on_scan_progress)
        self.scanner.item_found.connect(self.on_item_found)
        self.scanner.error.connect(self.on_scan_error)
        self.scanner.complete.connect(self.on_scan_complete)

        self.cleaner.progress.connect(self.on_clean_progress)
        self.cleaner.item_deleted.connect(self.on_item_deleted)
        self.cleaner.error.connect(self.on_clean_error)
        self.cleaner.complete.connect(self.on_clean_complete)

        from core.config_manager import get_config_manager
        self.config_mgr = get_config_manager()
        self.notification = WindowsNotification()

    def _create_compact_option(self, label_text, icon, checked):
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


    def select_all_items(self):
        """全选/取消全选当前标签页的所有项"""
        current_idx = self.result_stack.currentIndex()
        # 获取当前显示的容器
        risk_types = ['safe', 'suspicious', 'dangerous']
        if current_idx < len(risk_types):
            risk_type = risk_types[current_idx]
            container = getattr(self, f'{risk_type}_cards_container')
            layout = container.layout()

            if layout:
                # 收集所有复选框
                all_checkboxes = []
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        # 找到所有复选框
                        all_checkboxes.extend(widget.findChildren(QCheckBox))

                if all_checkboxes:
                    # 判断当前是否全部选中
                    all_checked = all(cb.isChecked() for cb in all_checkboxes)

                    # 切换状态
                    for cb in all_checkboxes:
                        cb.setChecked(not all_checked)

    def _update_stats(self):
        total = len(self.scan_results)
        total_size = sum(item.size for item in self.scan_results)
        self.quick_stats.setText(f'{total} 项 | {format_size(total_size)}')

        # 更新标签按钮文本：标签名 (数量)
        tab_names = {'safe': '安全', 'suspicious': '疑似', 'dangerous': '危险'}
        for i, (key, btn) in enumerate(zip(['safe', 'suspicious', 'dangerous'], self.tab_buttons)):
            count = self.risk_counts.get(key, 0)
            btn.setText(f'{tab_names[key]} ({count})')

    def _clear_results(self):
        # 清空复选框列表并删除组件
        for cb, card, item in self.checkboxes:
            cb.deleteLater()
            card.deleteLater()
        self.checkboxes.clear()
        self.scan_results.clear()
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
        self.clean_btn.setEnabled(False)
        self._update_stats()

        # 清空每个风险类型的容器
        for risk_type in ['safe', 'suspicious', 'dangerous']:
            container = getattr(self, f'{risk_type}_cards_container')
            layout = container.layout()

            # 找到并显示 empty label
            empty = container.findChild(BodyLabel, f'{risk_type}_empty')
            if empty:
                empty.show()
                continue

            # 移除所有卡片widget（空标签除外）
            for i in range(layout.count() - 1, -1, -1):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # 跳过 empty label 和 spacer
                    if widget.objectName() and widget.objectName().endswith('_empty'):
                        continue
                    parent_widget = widget.parent()
                    if parent_widget and parent_widget != container:
                        parent_widget.setParent(None)
                    widget.deleteLater()

    @handle_errors
    def on_scan(self, checked=False):
        browsers = []
        if self.chrome_check.isChecked():
            browsers.append('chrome')
        if self.edge_check.isChecked():
            browsers.append('edge')
        if self.firefox_check.isChecked():
            browsers.append('firefox')

        if not browsers:
            self.status_label.setText('请选择浏览器')
            return

        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)

        self._clear_results()
        # 使用 ScanStatusWidget 显示进度
        self.scan_status.scanning('扫描中...', 0, 0)
        self.scanner.start_scan(browsers)

    def on_cancel_scan(self):
        try:
            self.scanner.cancel_scan()
            self.cancel_btn.setVisible(False)
            self.scan_btn.setEnabled(True)
            self.scan_status.idle('扫描已取消')
            self.status_label.setText('已取消')
        except Exception as e:
            _thread_logger.error(f"取消扫描失败: {e}")
            get_error_handler().log_error(e, "[BrowserCleaner.on_cancel_scan]")

    def on_scan_progress(self, message):
        try:
            self.status_label.setText(message)
        except Exception as e:
            _thread_logger.error(f"更新扫描进度失败: {e}")

    @handle_errors
    def on_item_found(self, item):
        self.scan_results.append(item)
        # 规范化风险等级为字符串
        risk_level_str = self._normalize_risk_level(item.risk_level)
        self.risk_counts[risk_level_str] += 1
        self._update_stats()

        # 获取对应的卡片容器
        container = getattr(self, f'{risk_level_str}_cards_container')
        layout = container.layout()

        # 找到并隐藏 empty label
        empty = container.findChild(BodyLabel, f'{risk_level_str}_empty')
        if empty:
            empty.hide()

        # 创建卡片
        card, checkbox = self._create_item_card(item)

        # 单列垂直布局 - 插在 stretch 和 empty 之前
        from PyQt5.QtWidgets import QSpacerItem
        stretch_index = -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item, QSpacerItem):
                stretch_index = i
                break

        if stretch_index != -1:
            layout.insertWidget(stretch_index, card)
        else:
            layout.insertWidget(layout.count() - 1, card)

        self.checkboxes.append((checkbox, card, item))

    def on_scan_error(self, message):
        try:
            self.scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.scan_status.error(f'错误: {message}')
            self.status_label.setText(f'错误: {message}')
        except Exception as e:
            _thread_logger.error(f"处理扫描错误失败: {e}")

    @handle_errors
    def on_scan_complete(self, results):
        """扫描完成处理"""
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.scan_status.complete(len(results) if results else 0)
        self.status_label.setText(f'扫描完成！发现 {len(results) if results else 0} 项')

        if results and self.notification.is_enabled():
            try:
                self.notification.show_scan_complete(len(results), sum(item.size for item in results))
            except Exception as e:
                _thread_logger.warning(f"发送通知失败: {e}")

        if results:
            self.clean_btn.setEnabled(True)

    def on_clean(self):
        selected = [item for cb, _, item in self.checkboxes if cb.isChecked()]
        if not selected:
            self.status_label.setText('请选择项目')
            return

        if self.config_mgr.get('cleanup/confirm_dialog', True):
            dialog = ConfirmDialog(selected, self)
            if dialog.exec_() != QDialog.Accepted:
                return
            selected = dialog.get_items_to_clean()

        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.cleaner.start_clean(selected, clean_type='browser')

    def on_clean_progress(self, message):
        self.status_label.setText(message)

    def on_item_deleted(self, path, size):
        for i, (cb, row, item) in enumerate(self.checkboxes):
            if item.path == path:
                cb.deleteLater()
                row.deleteLater()
                self.checkboxes.pop(i)
                break

        self.scan_results = [it for it in self.scan_results if it.path != path]
        self._update_stats()

    def on_clean_error(self, message):
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.status_label.setText(f'错误: {message}')

    def on_clean_complete(self, result):
        self.scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)

        if result['success']:
            count = result['deleted_count']
            size = result['total_size']
            self.status_label.setText(f'清理完成！删除 {count} 项')

            if self.notification.is_enabled():
                self.notification.show_clean_complete(count, size)

            if not self.checkboxes:
                self.clean_btn.setEnabled(False)
        else:
            self.status_label.setText(f'失败: {result["errors"]}')

    def get_notification_manager(self):
        return self.notification

    # ========== 结果视图方法 ==========

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
        # 使用标准卡片
        card = SimpleCardWidget()
        card.setFixedHeight(110)  # 固定单列模式高度
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

        # 第一行：复选框 + 图标 + 路径 + 判断方法标签
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # 复选框
        cb = QCheckBox()
        cb.setChecked(risk_level_str == 'safe')
        cb.setFixedSize(20, 20)
        top_row.addWidget(cb)

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
        method_text = '规则判断'
        method_label = BodyLabel(method_text)
        method_style = '''
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 500;
        '''
        method_label.setStyleSheet(method_style + 'background: #f1f3f4; color: #5f6368;')
        top_row.addWidget(method_label)

        top_row.addSpacing(-4)  # 减少右边距

        # 第二行：文件大小
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        # 文件大小
        size_label = BodyLabel(f'{self._format_size(item.size)}')
        size_label.setStyleSheet('font-size: 11px; color: #888;')
        info_row.addWidget(size_label)

        info_row.addStretch()

        layout.addLayout(top_row)
        layout.addLayout(info_row)

        # 获取 checkbox
        checkbox = card.findChild(QCheckBox)

        return card, checkbox

    def _create_card_wrapper(self, item):
        """创建卡片包装器（用于旧代码兼容）"""
        return self._create_item_card(item)[0]

    def _normalize_risk_level(self, risk_level):
        """规范化风险等级"""
        if risk_level is None:
            return 'suspicious'
        if hasattr(risk_level, 'value'):
            return risk_level.value
        risk_str = str(risk_level).lower()
        if risk_str not in ['safe', 'suspicious', 'dangerous']:
            return 'suspicious'
        return risk_str

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
