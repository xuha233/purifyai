"""
自定义清理页面 UI - 紧凑高效设计
"""
import os
import functools
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QCheckBox, QFileDialog, QStackedWidget, QDialog, QSpacerItem, QLineEdit
)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QMouseEvent
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, CardWidget, LineEdit, Pivot, ProgressBar,
    SubtitleLabel, FluentIcon, IconWidget, InfoBar, InfoBarPosition
)

# 导入错误处理器
from core.error_handler import get_error_handler
from core.ai_review_models import AIReviewStatus, AIReviewResult
from core.config_manager import get_config_manager
from core.rule_engine import RiskLevel
from ui.ai_review_widgets import AIReviewCard

_thread_logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def handle_errors(func):
    """错误处理装饰器 - 捕获并记录所有异常"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"[CustomCleaner.{func.__name__}] {str(e)}")
            error_handler = get_error_handler()
            error_handler.log_error(e, f"[CustomCleaner.{func.__name__}]")
            if hasattr(self, 'status_label'):
                try:
                    self.status_label.setText(f'错误: {str(e)[:50]}')
                except:
                    pass
            return None
    return wrapper


class ClickableCard(SimpleCardWidget):
    """可点击的卡片组件"""
    clicked = pyqtSignal(object)  # Signal that emits when clicked

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data

    def mousePressEvent(self, event: QMouseEvent):
        """处理鼠标点击事件"""
        # 检查是否点击了复选框区域
        checkbox = self.findChild(QCheckBox)
        if checkbox:
            checkbox_pos = checkbox.mapTo(self, checkbox.rect().topLeft())
            checkbox_rect = Qt.QRect(checkbox_pos, checkbox.size())
            if checkbox_rect.contains(event.pos()):
                # 让复选框正常处理点击
                checkbox.click()
                return

        # 其他区域触发 clicked 信号
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item_data)

        super().mousePressEvent(event)

from core import CustomScanner, Cleaner, format_size, RiskLevel, ScanItem, get_ai_enhancer
from ui.confirm_dialog import ConfirmDialog
from ui.windows_notification import WindowsNotification
from ui.annotation_widget import CompactAnnotationDisplay
from ui.annotation_detail_dialog import AnnotationDetailDialog
from ui.scan_status_widget import ScanStatusWidget

logger = logging.getLogger(__name__)


class CustomCleanerPage(QWidget):
    """自定义清理页面 - 紧凑设计"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = []
        self.checkboxes = []
        self.custom_paths = []
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
        self.path_cards = []
        self.is_cancelled = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # ========== 标题区 ==========
        header_layout = QHBoxLayout()
        title = StrongBodyLabel('自定义管理')
        title.setStyleSheet('font-size: 24px;')
        header_layout.addWidget(title)
        header_layout.addSpacing(20)

        # 快速统计
        self.quick_stats = BodyLabel('0 路径 | 0 项 | 0 B')
        self.quick_stats.setStyleSheet('color: #666666; font-size: 14px;')
        header_layout.addWidget(self.quick_stats)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ========== 扫描状态指示器（显眼的位置）==========
        self.scan_status = ScanStatusWidget()
        main_layout.addWidget(self.scan_status)

        main_layout.addSpacing(4)

        # ========== 主内容 ==========
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(12)

        # ========== 左侧：路径管理 ==========
        self.path_panel = SimpleCardWidget()
        path_layout = QVBoxLayout(self.path_panel)
        path_layout.setContentsMargins(12, 12, 12, 12)
        path_layout.setSpacing(10)
        self.path_panel.setFixedWidth(320)

        # 标题栏
        header_row = QWidget()
        header_inner = QHBoxLayout(header_row)
        header_inner.setContentsMargins(0, 0, 0, 0)

        title = StrongBodyLabel('路径设置')
        title.setStyleSheet('font-size: 14px;')
        header_inner.addWidget(title)
        header_inner.addStretch()

        path_layout.addWidget(header_row)

        # 路径输入
        input_row = QWidget()
        input_inner = QHBoxLayout(input_row)
        input_inner.setContentsMargins(0, 0, 0, 0)

        self.path_input = LineEdit()
        self.path_input.setPlaceholderText('输入路径')
        self.path_input.setFixedHeight(36)
        input_inner.addWidget(self.path_input)

        browse_btn = PushButton('...')
        browse_btn.setFixedWidth(36)
        browse_btn.setFixedHeight(36)
        browse_btn.clicked.connect(self.browse_folder)
        input_inner.addWidget(browse_btn)

        add_btn = PrimaryPushButton('+')
        add_btn.setFixedWidth(36)
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self.add_path)
        input_inner.addWidget(add_btn)

        path_layout.addWidget(input_row)

        # 路径列表（紧凑滚动）
        self.path_list = QScrollArea()
        self.path_list.setWidgetResizable(True)
        self.path_list.setFrameShape(QScrollArea.NoFrame)
        self.path_list.setStyleSheet("QScrollArea { border: 1px solid #e0e0e0; border-radius: 4px; background: white; }")

        self.path_list_container = QWidget()
        self.path_list_inner_layout = QVBoxLayout(self.path_list_container)
        self.path_list_inner_layout.setSpacing(6)
        self.path_list_inner_layout.setContentsMargins(6, 6, 6, 6)
        self.path_list_inner_layout.addStretch()

        self.path_list.setWidget(self.path_list_container)
        path_layout.addWidget(self.path_list, stretch=1)

        # 扫描按钮
        self.scan_btn = PrimaryPushButton(FluentIcon.SEARCH, '扫描')
        self.scan_btn.clicked.connect(self.on_scan)
        self.scan_btn.setFixedHeight(40)
        path_layout.addWidget(self.scan_btn)

        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.on_cancel_scan)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(36)
        path_layout.addWidget(self.cancel_btn)

        content_layout.addWidget(self.path_panel)

        # ========== 右侧：结果 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        # 状态标签（保留用于其他消息）
        self.status_label = BodyLabel('就绪')
        self.status_label.setStyleSheet('font-size: 12px; color: #666;')
        right_layout.addWidget(self.status_label)

        # ========== AI复核进度组件 ==========
        from ai_review_widgets import ReviewSummaryCard, ReviewProgressBar

        self.ai_review_summary = ReviewSummaryCard()
        self.ai_review_summary.setVisible(False)
        right_layout.addWidget(self.ai_review_summary)

        self.ai_review_progress = ReviewProgressBar()
        self.ai_review_progress.setVisible(False)
        right_layout.addWidget(self.ai_review_progress)

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

        # AI 复核按钮

        actions_row.addStretch()
        right_layout.addLayout(actions_row)

        # 结果区域
        results_card = CardWidget()
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # 头部栏：标签 + 视图切换（使用按钮代替 Pivot）
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

            # 使用流式布局或网格布局
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

        self.scanner = CustomScanner()
        self.cleaner = Cleaner()
        self.scanner.set_ai_filter_enabled(get_ai_enhancer().is_enabled())

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

    def get_notification_manager(self):
        return self.notification

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            self.path_input.setText(folder)

    def add_path(self):
        path = self.path_input.text().strip()
        if not path:
            return

        # 解析环境变量
        for key in os.environ:
            path = path.replace(f'%{key}%', os.environ[key])

        if not os.path.exists(path):
            self.status_label.setText('路径不存在')
            return

        if path in self.custom_paths:
            return

        self.custom_paths.append(path)
        self._add_path_item(path)
        self.path_input.clear()
        self._update_stats()

    def _add_path_item(self, path):
        item = QWidget()
        item.setFixedHeight(40)
        item.setStyleSheet('background: #f9f9f9; border-radius: 4px; margin-bottom: 4px;')
        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 0, 8, 0)

        label = BodyLabel(os.path.basename(path))
        label.setStyleSheet('font-size: 12px;')
        layout.addWidget(label, stretch=1)

        del_btn = PushButton('×')
        del_btn.setFixedWidth(28)
        del_btn.setFixedHeight(28)
        del_btn.setStyleSheet('color: #dc3545;')
        del_btn.clicked.connect(lambda: self.remove_path(path, item))
        layout.addWidget(del_btn)

        self.path_list_inner_layout.insertWidget(self.path_list_inner_layout.count() - 1, item)
        self.path_cards.append(item)

    def remove_path(self, path, item):
        if path in self.custom_paths:
            self.custom_paths.remove(path)
        self.path_list_inner_layout.removeWidget(item)
        item.deleteLater()
        self.path_cards = [p for p in self.path_cards if p != item]
        self._update_stats()

    def _update_stats(self):
        total = len(self.scan_results)
        total_size = sum(item.size for item in self.scan_results)
        self.quick_stats.setText(f'{len(self.custom_paths)} 路径 | {total} 项 | {format_size(total_size)}')

        # 更新标签按钮文本：标签名 (数量)
        tab_names = {'safe': '安全', 'suspicious': '疑似', 'dangerous': '危险'}
        for i, (key, btn) in enumerate(zip(['safe', 'suspicious', 'dangerous'], self.tab_buttons)):
            count = self.risk_counts.get(key, 0)
            btn.setText(f'{tab_names[key]} ({count})')

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
    

    def select_all_items(self):
        """全选/取消全选当前标签页的所有项"""
        current_idx = self.result_stack.currentIndex()
        containers = [
            getattr(self, 'safe_cards_container'),
            getattr(self, 'suspicious_cards_container'),
            getattr(self, 'dangerous_cards_container')
        ]
        container = containers[current_idx] if current_idx < len(containers) else None

        if container:
            # 检查是否所有复选框都已选中
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

    def on_ai_filter_changed(self, enabled: bool):
        self.scanner.set_ai_filter_enabled(enabled)
        # AIEnhancer 用其他方法设置启用状态
        enhancer = get_ai_enhancer()
        if hasattr(enhancer, 'set_enabled'):
            enhancer.set_enabled(enabled)

    def _clear_results(self):
        # 清理旧的卡片
        for cb, card, item in self.checkboxes:
            cb.deleteLater()
            card.deleteLater()
        self.checkboxes.clear()
        self.scan_results.clear()
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
        self.clean_btn.setEnabled(False)

        self._update_stats()
        self.scan_status.idle('准备扫描')

        # 重置所有容器布局
        for risk_type in ['safe', 'suspicious', 'dangerous']:
            container = getattr(self, f'{risk_type}_cards_container')
            self._update_container_layout(container)

    @handle_errors
    def on_scan(self, checked=False):
        if not self.custom_paths:
            self.status_label.setText('请添加路径')
            return

        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)

        self._clear_results()
        self.scan_status.scanning('扫描中...', 0, 0)

        # 启动扫描器
        self.scanner.start_scan(self.custom_paths)

    def on_cancel_scan(self):
        self.scanner.cancel_scan()
        self.cancel_btn.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.scan_status.cancelled()
        self.status_label.setText('已取消')

    def on_scan_progress(self, message):
        self.status_label.setText(message)
        # 更新状态指示器
        self.scan_status.scanning(message, len(self.scan_results), len(self.scan_results))

    @handle_errors
    def on_item_found(self, item):
        # 规范化风险等级
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

    def on_scan_error(self, message):
        try:
            self.scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.scan_status.error(message)
            self.status_label.setText(f'错误: {message}')
        except Exception as e:
            logger.error(f"处理扫描错误失败: {e}")

    @handle_errors
    def on_scan_complete(self, results):
        """扫描完成处理"""
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)

        result_count = len(results) if results else 0
        total_size = sum(item.size for item in results) if results else 0
        self.status_label.setText(f'扫描完成！发现 {result_count} 项')

        if results:
            self.scan_status.complete(result_count)
            self.clean_btn.setEnabled(True)

            # AI 复核按钮处理（根据当前选中的风险级别启用按钮）
            # 注意：这个功能可能还未实现，按钮可能不存在
            current_count = self.risk_counts.get(self.current_tab, 0)

            # 安全检查：按钮存在才启用
            if hasattr(self, 'ai_scanner_evaluate_btn'):
                self.ai_scanner_evaluate_btn.setEnabled(current_count > 0)

            if self.notification.is_enabled():
                try:
                    self.notification.show_scan_complete(result_count, total_size)
                except Exception as e:
                    logger.warning(f"发送通知失败: {e}")
        else:
            self.scan_status.cancelled('未发现项目')



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
        self.cleaner.start_clean(selected, clean_type='custom')

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

    def _on_ai_custom_progress(self, idx: int, total: int):
        """AI复核进度回调"""
        status = AIReviewStatus(
            total_items=total,
            reviewed_items=idx,
            is_in_progress=True
        )
        self.ai_review_progress.update_status(status)
        self.ai_review_summary.update_summary(status)

    def _on_ai_evaluate_finished(self, results):
        """AI评估完成回调 - 在主线程中更新UI"""
        # results 格式: {path: (new_risk, reason)}
        # 更新UI控件状态

        self.ai_evaluate_btn.setText("AI评估当前项")
        self.ai_review_progress.setVisible(False)
        self.ai_review_summary.setVisible(False)
        self.scan_status.complete(len(results))
        self.status_label.setText(f'AI 评估完成，共{len(results)}项')

        # 在主线程中更新所有卡片的风险等级
        for path, (new_risk, reason) in results.items():
            # 找到对应的 scan_result 并更新
            for i, item in enumerate(self.scan_results):
                if item.path == path:
                    self.scan_results[i].risk_level = new_risk
                    # 更新或设置 AI 解释
                    if not hasattr(item, 'ai_explanation'):
                        item.ai_explanation = reason
                    # 标记使用 AI 评估
                    if not hasattr(item, 'judgment_method'):
                        item.judgment_method = 'ai'
                    break
            # 更新卡片 UI
            self._update_item_risk_by_path(path, new_risk, reason)

    def _update_item_risk_by_path(self, path, new_risk, reason="AI 评估"):
        """通过路径更新项目风险等级并重新创建 AI 评分卡片"""
        # 找到并移除旧卡片
        card_index_to_remove = None

        for i, (cb, card, it) in enumerate(self.checkboxes):
            if it.path == path:
                # 减少旧风险等级的计数
                old_risk = self._normalize_risk_level(it.risk_level)
                self.risk_counts[old_risk] = max(0, self.risk_counts[old_risk] - 1)

                # 从布局中移除卡片
                parent = card.parent()
                if parent and parent.layout():
                    parent.layout().removeWidget(card)
                cb.deleteLater()
                card.deleteLater()

                card_index_to_remove = i
                break

        if card_index_to_remove is not None:
            self.checkboxes.pop(card_index_to_remove)

        # 找到 scan_results 中对应的项目
        result_item = None
        for item in self.scan_results:
            if item.path == path:
                result_item = item
                break

        if result_item:
            # 确保风险等级已更新
            result_item.risk_level = new_risk

            # 增加新的风险等级计数
            risk_level_str = self._normalize_risk_level(new_risk)
            self.risk_counts[risk_level_str] = self.risk_counts.get(risk_level_str, 0) + 1

            # 创建 AIReviewResult 对象
            ai_risk_enum = RiskLevel.SAFE if new_risk == 'safe' else \
                           RiskLevel.DANGEROUS if new_risk == 'dangerous' else RiskLevel.SUSPICIOUS

            original_risk = RiskLevel.SUSPICIOUS  # 默认为疑似，因为只有疑似项会进行 AI 评估

            ai_result = AIReviewResult(
                item_path=path,
                original_risk=original_risk,
                ai_risk=ai_risk_enum,
                confidence=0.8,
                function_description=reason,
                software_name="",
                risk_reason=reason,
                cleanup_suggestion=reason,
                is_valid=True,
                parse_method="custom_scanner"
            )

            # 获取对应容器
            container = getattr(self, f'{risk_level_str}_cards_container', None)
            if container:
                # 创建 AI 卡片
                ai_card = AIReviewCard(result_item, ai_result)

                # 单列垂直布局 - 插在 spacer 之前
                from PyQt5.QtWidgets import QSpacerItem
                layout = container.layout()

                # 找到 spacer 的位置
                spacer_index = -1
                for i in range(layout.count()):
                    item_at = layout.itemAt(i)
                    if item_at and isinstance(item_at, QSpacerItem):
                        spacer_index = i
                        break

                if spacer_index != -1:
                    layout.insertWidget(spacer_index, ai_card)
                else:
                    layout.insertWidget(layout.count() - 2, ai_card)

                # AI 卡片有复选框，获取复选框
                checkbox = ai_card.get_checkbox()
                self.checkboxes.append((checkbox, ai_card, result_item))

        self._update_stats()

    def _on_ai_evaluate_error(self, error_msg):
        """AI评估错误回调"""

        self.ai_evaluate_btn.setText("AI复核")
        self.ai_review_progress.setVisible(False)
        self.ai_review_summary.setVisible(False)
        self.scan_status.error('AI 评估失败')
        self.status_label.setText(f'AI 评估失败: {error_msg}')
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.error('AI评估失败', error_msg, parent=self, position=InfoBarPosition.TOP, duration=5000)

    def _evaluate_with_rules(self, items):
        """使用默认规则进行评估"""
        key_words = {
            'safe': ['cache', 'cache2', 'temp', 'tmp', 'tempfolder', 'crash', 'dump', 'log',
                      'prefetch', 'thumbnails', 'thumb', 'media cache', 'gpucache', 'codecache',
                      'download', 'downloads', 'session'],
            'suspicious': ['backup', 'save', 'data', 'datastore', 'config', 'setting',
                           'setting', 'history', 'record', 'log', 'database', 'db', 'sync',
                           'plugin', 'extension'],
            'dangerous': ['user data', 'userdata', 'profile', 'appdata', 'program files',
                           'windows', 'system32', 'users', 'documents', 'pictures']
        }

        for i, item in enumerate(items):
            file_path = item.path.lower()
            folder = os.path.basename(file_path)

            is_dangerous = any(d in file_path or d in folder for d in key_words['dangerous'])
            is_safe = any(s in file_path or s in folder for s in key_words['safe'])

            if is_dangerous:
                self._update_item_risk(item, 'dangerous')
            elif is_safe:
                self._update_item_risk(item, 'safe')
            else:
                self._update_item_risk(item, 'suspicious')

            self.scan_status.scanning(f'规则评估中... {i+1}/{len(items)}', i+1, i+1)

        self.scan_status.complete(len(items))

        self.status_label.setText(f'规则评估完成')

    def _update_item_risk(self, item, new_risk):
        """更新项目风险等级并重新创建卡片"""
        # 1. 找到并移除旧卡片
        scan_index = None
        for i, (cb, card, it) in enumerate(self.checkboxes):
            if it.path == item.path:
                # 减少旧风险等级的计数
                old_risk = self._normalize_risk_level(it.risk_level)
                self.risk_counts[old_risk] -= 1

                # 移除旧的卡片和复选框
                cb.deleteLater()
                card.deleteLater()
                self.checkboxes.pop(i)

                # 找到 scan_results 中的索引
                for j, s in enumerate(self.scan_results):
                    if s.path == item.path:
                        scan_index = j
                        break
                break

        # 2. 从 scan_results 中找到并更新该项
        if scan_index is not None:
            # 更新风险等级
            self.scan_results[scan_index].risk_level = new_risk
            updated_item = self.scan_results[scan_index]

            # 3. 创建并添加新卡片到正确的分类
            risk_level_str = self._normalize_risk_level(new_risk)
            self.risk_counts[risk_level_str] += 1

            # 获取对应容器
            container = getattr(self, f'{risk_level_str}_cards_container')

            # 创建卡片
            card, checkbox = self._create_item_card(updated_item)

            # 单列垂直布局
            layout = container.layout()
            layout.insertWidget(layout.count() - 2, card)

            self.checkboxes.append((checkbox, card, updated_item))

            self._update_stats()

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
        from PyQt5.QtWidgets import QVBoxLayout
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
        card = SimpleCardWidget()
        card.setFixedHeight(150)  # 固定单列模式高度
        card.setStyleSheet('''
            SimpleCardWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            SimpleCardWidget:hover {
                border: 1px solid #0078D4;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        ''')
        card.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 第一行：复选框 + 图标 + 路径 + 判断方法标签
        header = QHBoxLayout()
        header.setSpacing(8)

        cb = QCheckBox()
        cb.setChecked(item.risk_level == 'safe')
        cb.setFixedSize(20, 20)
        header.addWidget(cb)

        # 风险图标
        color = {'safe': '#28a745', 'suspicious': '#ffc107', 'dangerous': '#dc3545'}.get(item.risk_level, '#999')
        risk_icon = IconWidget(FluentIcon.CHECKBOX if item.risk_level == 'safe' else
                               FluentIcon.INFO if item.risk_level == 'suspicious' else FluentIcon.DELETE)
        risk_icon.setFixedSize(22, 22)
        risk_icon.setStyleSheet(f'color: {color};')
        header.addWidget(risk_icon)

        # 路径
        path_label = BodyLabel(item.description[:25] + '...' if len(item.description) > 25 else item.description)
        path_label.setStyleSheet('font-size: 13px; font-weight: 500; color: #2c2c2c;')
        path_label.setWordWrap(True)
        header.addWidget(path_label, stretch=1)

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
        header.addWidget(method_label)

        header.addSpacing(-4)  # 减少右边距

        layout.addLayout(header)

        # 中间：批注信息（如果有）
        if item.annotation:
            anno_row = QWidget()
            anno_row.setStyleSheet('background: #fafafa; border-radius: 6px;')
            anno_layout = QVBoxLayout(anno_row)
            anno_layout.setContentsMargins(8, 6, 8, 6)
            anno_layout.setSpacing(4)

            # 批注来源和置信度
            anno_info = BodyLabel(f'{item.annotation.assessment_method.upper()} | {int(item.annotation.confidence * 100)}%')
            anno_info.setStyleSheet('font-size: 10px; color: #666;')
            anno_layout.addWidget(anno_info)

            # 批注说明
            if item.annotation.annotation_note:
                note = BodyLabel(item.annotation.annotation_note[:60] + '...' if len(item.annotation.annotation_note) > 60 else item.annotation.annotation_note)
                note.setStyleSheet('font-size: 10px; color: #888;')
                note.setWordWrap(True)
                anno_layout.addWidget(note)

            layout.addWidget(anno_row)

        # 第二行信息栏：大小 + AI说明 + 推荐操作
        footer = QHBoxLayout()
        footer.setSpacing(12)

        size_label = BodyLabel(format_size(item.size))
        size_label.setStyleSheet('font-size: 11px; color: #888;')
        footer.addWidget(size_label)

        # AI说明（卡片右边灰色小字）
        ai_explanation = getattr(item, 'ai_explanation', '')
        if ai_explanation and getattr(item, 'judgment_method', '') == 'ai':
            ai_label = BodyLabel(f'• {ai_explanation[:30]}...' if len(ai_explanation) > 30 else f'• {ai_explanation}')
            ai_label.setStyleSheet('font-size: 11px; color: #999; font-style: italic;')
            footer.addWidget(ai_label, stretch=1)
        else:
            footer.addStretch()

        rec_colors = {'可以清理': '#28a745', '保留': '#ff9800', '需确认': '#ffc107'}
        rec_color = rec_colors.get(item.annotation.recommendation, '#666') if item.annotation else '#666'
        rec_label = BodyLabel(item.annotation.recommendation if item.annotation else '-')
        rec_label.setStyleSheet(f'font-size: 11px; color: {rec_color}; font-weight: 500;')
        footer.addWidget(rec_label)

        layout.addLayout(footer)

        # 点击事件（如果有批注）
        clickable_card = ClickableCard(item)
        clickable_card.mousePressEvent = lambda e, c=card, i=item: self._on_card_clicked(e, c, i)

        # 将布局传递给 ClickableCard
        for i in range(layout.count()):
            layout_item = layout.itemAt(i)
            if layout_item.widget():
                layout_item.widget().setParent(clickable_card)
                clickable_card.layout().addWidget(layout_item.widget(), i)

        return card, cb

    def _on_card_clicked(self, event, card, item):
        """卡片点击事件"""
        if item and item.annotation:
            # 检查是否点击了复选框
            pos = event.pos()
            cb = card.findChild(QCheckBox)
            if cb:
                cb_pos = cb.mapTo(card, cb.rect().topLeft())
                cb_rect = Qt.QRect(cb_pos, cb.size())
                if not cb_rect.contains(pos):
                    dialog = AnnotationDetailDialog(item.annotation, self)
                    dialog.exec_()

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

