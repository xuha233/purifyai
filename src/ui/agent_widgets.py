# -*- coding: utf-8 -*-
"""
通用智能体 UI 组件 - Agent Widgets

提供智能体系统中常用的可复用组件
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QProgressBar,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
    QTextEdit,
    QScrollArea,
    QApplication,
    QToolTip,
    QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation
from PyQt5.QtGui import QFont, QColor, QPalette

from qfluentwidgets import (
    SimpleCardWidget,
    StrongBodyLabel,
    BodyLabel,
    IconWidget,
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    InfoBar,
    InfoBarIcon,
)

from .agent_theme import AgentTheme
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskCard(QFrame):
    """当前任务面板卡片"""

    action_requested = pyqtSignal(str)  # action_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_task = None
        self.task_stage = "idle"

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMinimumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        title_icon = IconWidget(FluentIcon.CALENDAR)
        title_icon.setFixedSize(20, 20)
        title_icon.setStyleSheet("color: #0078D4;")
        title_row.addWidget(title_icon)

        self.task_title = StrongBodyLabel("当前任务")
        self.task_title.setStyleSheet("font-size: 15px;")
        title_row.addWidget(self.task_title)

        title_row.addStretch()
        layout.addLayout(title_row)

        # 任务状态
        self.task_status_label = BodyLabel("准备就绪")
        self.task_status_label.setStyleSheet("font-size: 13px; color: #999;")
        layout.addWidget(self.task_status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #e0e0e0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #0078D4, stop:1 #00a8cc);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 操作按钮
        self.actions_row = QHBoxLayout()
        self.actions_row.setContentsMargins(0, 0, 0, 0)
        self.actions_row.setSpacing(8)

        self.start_btn = self._create_action_btn("开始", "#28a745", "start")
        self.pause_btn = self._create_action_btn("暂停", "#FFA500", "pause")
        self.stop_btn = self._create_action_btn("停止", "#dc3545", "stop")

        self.actions_row.addWidget(self.start_btn)
        self.actions_row.addWidget(self.pause_btn)
        self.actions_row.addWidget(self.stop_btn)
        self.actions_row.addStretch()

        layout.addLayout(self.actions_row)

    def _create_action_btn(self, label: str, color: str, action: str) -> QPushButton:
        """创建操作按钮"""
        btn = QPushButton(label)
        btn.setFixedHeight(32)
        btn.setMinimumWidth(70)
        btn.clicked.connect(lambda: self.action_requested.emit(action))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {color}dd;
            }}
            QPushButton:pressed {{
                background: {color}bb;
            }}
            QPushButton:disabled {{
                background: #e0e0e0;
                color: #999;
            }}
        """)
        return btn

    def set_task_status(self, status: str, progress: int = 0, message: str = ""):
        """设置任务状态

        Args:
            status: 状态 (idle/running/paused/completed/error)
            progress: 进度百分比
            message: 状态消息
        """
        self.task_stage = status
        self.task_status_label.setText(message or status.upper())
        self.progress_bar.setValue(progress)

        # 更新按钮状态
        if status == "idle":
            self.start_btn.setText("开始")
            self.start_btn.setEnabled(True)
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #218838;
                }
            """)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif status == "running":
            self.start_btn.setText("运行中")
            self.start_btn.setEnabled(False)
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: #e0e0e0;
                    color: #999;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            self.pause_btn.setText("暂停")
            self.pause_btn.setEnabled(True)
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background: #FFA500;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #e69400;
                }
            """)
            self.stop_btn.setEnabled(True)
        elif status == "paused":
            self.start_btn.setText("继续")
            self.start_btn.setEnabled(True)
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: #0078D4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #0056b3;
                }
            """)
            self.pause_btn.setText("已暂停")
            self.pause_btn.setEnabled(False)
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background: #e0e0e0;
                    color: #999;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            self.stop_btn.setEnabled(True)
        elif status == "completed":
            self.start_btn.setText("完成")
            self.start_btn.setEnabled(False)
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: #e0e0e0;
                    color: #999;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif status == "error":
            self.start_btn.setText("重试")
            self.start_btn.setEnabled(True)
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: #0078D4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #0056b3;
                }
            """)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)


class AgentStatCard(SimpleCardWidget):
    """智能体统计卡片"""

    def __init__(
        self, value: str, label: str, icon: FluentIcon, color: str, parent=None
    ):
        super().__init__(parent)
        self.color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(36, 36)
        icon_widget.setStyleSheet(f"color: {color};")
        layout.addWidget(icon_widget)

        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        value_label = StrongBodyLabel(value)
        value_label.setStyleSheet(f"font-size: 22px; color: {color}; font-weight: 700;")
        content_layout.addWidget(value_label)

        text_label = BodyLabel(label)
        text_label.setStyleSheet("font-size: 11px; color: #999;")
        content_layout.addWidget(text_label)

        layout.addLayout(content_layout)
        layout.addStretch()

    def update_value(self, value: str):
        """更新数值"""
        # 查找并更新 value_label（第一个 StrongBodyLabel）
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and isinstance(item.layout(), QVBoxLayout):
                sub_layout = item.layout()
                for j in range(sub_layout.count()):
                    sub_item = sub_layout.itemAt(j)
                    if sub_item and isinstance(sub_item.widget(), StrongBodyLabel):
                        sub_item.widget().setText(value)
                        break
                break


class ToolLoggerWidget(QFrame):
    """工具调用日志组件 - 优化版，支持批量更新"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toolbar_height = 40
        self.max_entries = 100
        self.visible_entries = 50
        self.entries = []
        self._pending_entries = []
        self._update_scheduled = False

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(self.toolbar_height)
        header.setStyleSheet("""
            QWidget {
                background: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        headers = ["时间", "阶段", "工具", "状态"]
        widths = [80, 60, 150, 0]

        for i, (header_text, width) in enumerate(zip(headers, widths)):
            label = StrongBodyLabel(header_text)
            label.setStyleSheet("font-size: 11px; color: #666; font-weight: 600;")
            if width > 0:
                label.setFixedWidth(width)
            else:
                header_layout.addStretch()
                header_layout.addWidget(label)
                break
            header_layout.addWidget(label)

        layout.addWidget(header)

        self.content_area = QWidget()
        self.content_area.setStyleSheet("background: white;")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.addStretch()

        layout.addWidget(self.content_area, stretch=1)

    def add_entry(self, stage: str, tool_name: str, status: str = "success"):
        """添加日志条目（批量优化）"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")

        self._pending_entries.append((timestamp, stage, tool_name, status))
        self._schedule_batch_update()

    def _schedule_batch_update(self):
        """调度批量更新"""
        if self._update_scheduled:
            return
        self._update_scheduled = True
        QTimer.singleShot(16, self._process_batch)

    def _process_batch(self):
        """处理批量更新"""
        self._update_scheduled = False
        if not self._pending_entries:
            return

        insert_position = self.content_layout.count() - 1
        status_colors = {"success": "#28a745", "error": "#dc3545", "pending": "#FFA500"}

        for timestamp, stage, tool_name, status in self._pending_entries:
            status_color = status_colors.get(status, "#999")
            status_text = {"success": "成功", "error": "失败", "pending": "进行中"}.get(
                status, status
            )

            entry = QWidget()
            entry.setFixedHeight(32)
            entry.setStyleSheet("""
                QWidget {
                    border-bottom: 1px solid #f0f0f0;
                }
                QWidget:hover {
                    background: #f8f8f8;
                }
            """)
            entry_layout = QHBoxLayout(entry)
            entry_layout.setContentsMargins(12, 0, 12, 0)

            time_label = BodyLabel(timestamp)
            time_label.setFixedWidth(80)
            time_label.setStyleSheet("font-size: 11px; color: #999;")
            entry_layout.addWidget(time_label)

            stage_label = BodyLabel(stage)
            stage_label.setFixedWidth(60)
            stage_label.setStyleSheet("font-size: 11px; color: #666;")
            entry_layout.addWidget(stage_label)

            tool_label = BodyLabel(tool_name)
            tool_label.setFixedWidth(150)
            tool_label.setStyleSheet("font-size: 11px; color: #333;")
            entry_layout.addWidget(tool_label)

            s_label = BodyLabel(status_text)
            s_label.setStyleSheet(f"font-size: 11px; color: {status_color};")
            entry_layout.addWidget(s_label)

            entry_layout.addStretch()

            self.content_layout.insertWidget(insert_position, entry)
            self.entries.append(entry)
            insert_position += 1

        self._pending_entries.clear()
        self._cleanup_old_entries()

    def _cleanup_old_entries(self):
        """清理旧条目"""
        while len(self.entries) > self.max_entries:
            oldest = self.entries.pop(0)
            oldest.deleteLater()

    def clear(self):
        """清空日志"""
        self._pending_entries.clear()
        for entry in self.entries:
            entry.deleteLater()
        self.entries.clear()


class CleanupItemModel(QWidget):
    """清理项目数据模型（用于虚拟滚动）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None
        item = self._data[index.row()]
        if role == Qt.DisplayRole:
            return item.get("name", "未知")
        elif role == Qt.UserRole:
            return item
        return None

    def add_item(self, item_data: dict):
        self._data.append(item_data)

    def remove_item(self, index: int):
        if 0 <= index < len(self._data):
            self._data.pop(index)

    def clear(self):
        self._data.clear()

    def get_item(self, index: int):
        if 0 <= index < len(self._data):
            return self._data[index]
        return None

    def __len__(self):
        return len(self._data)


class CleanupItemDelegate(QWidget):
    """清理项目自定义委托"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = False
        self._item_data = None
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 4px;
                border: 1px solid #e0e0e0;
            }
            QWidget:hover {
                border: 1px solid #0078D4;
            }
            QWidget[selected="true"] {
                background: #e3f2fd;
                border: 1px solid #0078D4;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)

        self.icon = IconWidget(FluentIcon.DOCUMENT)
        self.icon.setFixedSize(20, 20)
        self.icon.setStyleSheet("color: #666;")
        layout.addWidget(self.icon)

        self.name_label = BodyLabel()
        self.name_label.setStyleSheet("font-size: 12px; color: #333;")
        self.name_label.setMaximumWidth(200)
        layout.addWidget(self.name_label)

        layout.addStretch()

        self.size_label = BodyLabel()
        self.size_label.setStyleSheet("font-size: 11px; color: #999;")
        layout.addWidget(self.size_label)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def paint(self, painter, option, index):
        pass


class ItemListCard(SimpleCardWidget):
    """项目列表卡片组件 - 优化版，支持虚拟滚动"""

    item_selected = pyqtSignal(object)
    item_action = pyqtSignal(str)

    VISIBLE_ITEMS = 100
    BATCH_SIZE = 50

    def __init__(self, title: str = "清理项目", parent=None):
        super().__init__(parent)
        self._model = CleanupItemModel()
        self._visible_range = (0, 0)
        self._widgets = {}
        self._pending_updates = []
        self.selected_items = set()

        self._init_ui(title)

    def _init_ui(self, title: str):
        from PyQt5.QtWidgets import QListView

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.title_label = StrongBodyLabel(title)
        self.title_label.setStyleSheet("font-size: 13px;")
        header.addWidget(self.title_label)
        header.addStretch()

        filter_btn = QPushButton("筛选")
        filter_btn.setFixedSize(50, 24)
        filter_btn.clicked.connect(lambda: self.item_action.emit("filter"))
        header.addWidget(filter_btn)

        sort_btn = QPushButton("排序")
        sort_btn.setFixedSize(50, 24)
        sort_btn.clicked.connect(lambda: self.item_action.emit("sort"))
        header.addWidget(sort_btn)

        layout.addLayout(header)

        self.count_label = BodyLabel("0 个项目")
        self.count_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self.count_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: #fafafa;
            }
        """)
        self.scroll_area.viewport().setStyleSheet("background: #fafafa;")

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, stretch=1)

        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def add_item(self, item_data: dict):
        """添加项目（批量优化）"""
        self._model.add_item(item_data)
        self._pending_updates.append(item_data)
        self._schedule_batch_update()

    def _schedule_batch_update(self):
        """调度批量更新以减少重绘"""
        if len(self._pending_updates) >= self.BATCH_SIZE or not hasattr(
            self, "_update_timer"
        ):
            if hasattr(self, "_update_timer"):
                self._update_timer.stop()
            else:
                self._update_timer = QTimer()
                self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._process_batch)
            self._update_timer.start(16)

    def _process_batch_update(self):
        """处理批量更新"""
        self._update_count()
        self._update_visible_items()

    def _process_batch(self):
        """处理批量更新"""
        self._pending_updates.clear()
        self._update_count()
        self._update_visible_items()

    def _update_count(self):
        """更新项目计数"""
        count = len(self._model)
        self.count_label.setText(f"{count} 个项目")

    def _update_visible_items(self):
        """更新可见项"""
        scroll_value = self.scroll_area.verticalScrollBar().value()
        viewport_height = self.scroll_area.viewport().height()
        item_height = 50
        start_idx = max(0, scroll_value // item_height - 5)
        end_idx = min(
            len(self._model), (scroll_value + viewport_height) // item_height + 10
        )

        self._visible_range = (start_idx, end_idx)

        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if (
                item.widget()
                and item.widget()
                != self.list_layout.itemAt(self.list_layout.count() - 1).widget()
            ):
                item.widget().hide()
                item.widget().deleteLater()

        for idx in range(start_idx, end_idx):
            widget = self._create_visible_widget(idx)
            self.list_layout.insertWidget(idx - start_idx, widget)
            widget.show()

    def _create_visible_widget(self, index: int) -> QWidget:
        """创建可见项组件"""
        item_data = self._model.get_item(index)
        if not item_data:
            return QWidget()

        widget = CleanupItemDelegate()
        widget.name_label.setText(item_data.get("name", "未知"))
        widget.size_label.setText(self._format_size(item_data.get("size", 0)))
        widget.checkbox.setChecked(index in self.selected_items)

        widget.checkbox.stateChanged.connect(
            lambda state, idx=index: self._on_item_selected(idx, state)
        )

        return widget

    def _on_item_selected(self, index: int, state: int):
        """项目选中回调"""
        item_data = self._model.get_item(index)
        if not item_data:
            return

        item_id = item_data.get("id", id(item_data))
        if state == 2:
            self.selected_items.add(item_id)
        else:
            self.selected_items.discard(item_id)

        self.item_selected.emit(item_data)

    def _on_scroll(self, value):
        """滚动事件处理"""
        self._update_visible_items()

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def clear(self):
        """清空列表"""
        self._model.clear()
        self.selected_items.clear()
        self._update_count()
        self._update_visible_items()


# ============ 错误显示组件 ============


class ErrorDisplayWidget(QFrame):
    """错误显示组件

    提供用户友好的错误信息展示
    """

    # 信号
    retry_requested = pyqtSignal()  # 重试请求
    details_requested = pyqtSignal()  # 显示详情请求
    dismissed = pyqtSignal()  # 关闭请求

    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_data = {}
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        """初始化 UI"""
        self.setFixedHeight(120)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        # 错误图标
        self.error_icon = IconWidget(FluentIcon.INFO)
        self.error_icon.setFixedSize(24, 24)
        title_row.addWidget(self.error_icon)

        # 错误标题
        self.error_title = StrongBodyLabel("发生错误")
        self.error_title.setStyleSheet("font-size: 14px;")
        title_row.addWidget(self.error_title)

        title_row.addStretch()

        # 关闭按钮
        self.dismiss_btn = QPushButton("×")
        self.dismiss_btn.setFixedSize(24, 24)
        self.dismiss_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 16px;
                color: #999;
            }
            QPushButton:hover {
                color: #666;
            }
        """)
        self.dismiss_btn.clicked.connect(self._on_dismiss)
        title_row.addWidget(self.dismiss_btn)

        layout.addLayout(title_row)

        # 错误消息
        self.error_message = BodyLabel("")
        self.error_message.setWordWrap(True)
        self.error_message.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.error_message)

        # 操作按钮行
        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)

        self.retry_btn = PushButton("重试")
        self.retry_btn.setFixedHeight(28)
        self.retry_btn.clicked.connect(self.retry_requested.emit)
        actions_row.addWidget(self.retry_btn)

        self.details_btn = PushButton("查看详情")
        self.details_btn.setFixedHeight(28)
        self.details_btn.clicked.connect(self.details_requested.emit)
        actions_row.addWidget(self.details_btn)

        actions_row.addStretch()
        layout.addLayout(actions_row)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            ErrorDisplayWidget {
                background: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 6px;
            }
        """)
        self.error_icon.setStyleSheet("color: #ffc107;")

    def set_error(
        self,
        title: str,
        message: str,
        error_code: str = "",
        suggestions: list = None,
        recoverable: bool = True,
    ):
        """设置错误信息

        Args:
            title: 错误标题
            message: 错误消息
            error_code: 错误代码
            suggestions: 建议操作列表
            recoverable: 是否可恢复
        """
        self.error_data = {
            "title": title,
            "message": message,
            "error_code": error_code,
            "suggestions": suggestions or [],
            "recoverable": recoverable,
        }

        self.error_title.setText(title)

        # 构建用户消息
        full_message = message
        if error_code:
            full_message = f"[{error_code}] {message}"
        if suggestions:
            full_message += "\n" + " | ".join([f"建议: {s}" for s in suggestions[:2]])

        self.error_message.setText(full_message)

        # 更新状态
        if not recoverable:
            self.retry_btn.setEnabled(False)
            self.retry_btn.setToolTip("此错误无法自动恢复")

    def _on_dismiss(self):
        """关闭错误显示"""
        self.hide()
        self.dismissed.emit()

    def show_error(
        self,
        title: str,
        message: str,
        error_code: str = "",
        suggestions: list = None,
        recoverable: bool = True,
    ):
        """显示错误（公共接口）"""
        self.set_error(title, message, error_code, suggestions, recoverable)
        self.show()
        self.setFixedHeight(120)
        self._animate_show()

    def _animate_show(self):
        """动画显示"""
        self.setGraphicsEffect(None)

        from PyQt5.QtWidgets import QGraphicsOpacityEffect

        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(200)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.start()


class ErrorDetailsDialog(QFrame):
    """错误详情对话框

    显示完整的错误信息，包括堆栈跟踪和诊断信息
    """

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_details = {}
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("错误详情")
        self.setMinimumSize(600, 400)
        self.setWindowFlags(Qt.Dialog)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("""
            QWidget {
                background: #f8f9fa;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 8, 0)

        # 标题
        title = StrongBodyLabel("错误详情")
        title.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 关闭按钮
        close_btn = PushButton("关闭")
        close_btn.setFixedSize(70, 32)
        close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # 内容区域（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: white;
            }
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # 错误摘要
        self.summary_label = BodyLabel("")
        self.summary_label.setStyleSheet("""
            BodyLabel {
                font-size: 13px;
                color: #333;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self.summary_label)

        # 详细信息（可展开）
        details_header = StrongBodyLabel("详细信息")
        details_header.setStyleSheet("font-size: 12px; color: #666;")
        content_layout.addWidget(details_header)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                background: #2d2d2d;
                color: #f0f0f0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        content_layout.addWidget(self.details_text, stretch=1)

        # 建议操作
        suggestions_header = StrongBodyLabel("建议操作")
        suggestions_header.setStyleSheet("font-size: 12px; color: #666;")
        content_layout.addWidget(suggestions_header)

        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        self.suggestions_text.setMaximumHeight(150)
        self.suggestions_text.setStyleSheet("""
            QTextEdit {
                font-size: 12px;
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        content_layout.addWidget(self.suggestions_text)

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

    def set_error_details(
        self,
        error_code: str,
        error_type: str,
        error_message: str,
        stack_trace: str = "",
        suggestions: list = None,
        context: dict = None,
    ):
        """设置错误详情

        Args:
            error_code: 错误代码
            error_type: 错误类型
            error_message: 错误消息
            stack_trace: 堆栈跟踪
            suggestions: 建议列表
            context: 上下文信息
        """
        self.error_details = {
            "error_code": error_code,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "suggestions": suggestions or [],
            "context": context or {},
        }

        # 更新摘要
        summary = f"错误代码: {error_code}\n"
        summary += f"错误类型: {error_type}\n"
        summary += f"错误消息: {error_message}"

        if context:
            if context.get("session_id"):
                summary += f"\n会话ID: {context['session_id']}"
            if context.get("agent_type"):
                summary += f"\n智能体类型: {context['agent_type']}"

        self.summary_label.setText(summary)

        # 更新详细信息
        details = f"错误代码: {error_code}\n"
        details += f"错误类型: {error_type}\n"
        details += f"错误消息: {error_message}\n"

        if stack_trace:
            details += f"\n堆栈跟踪:\n{stack_trace}"

        if context:
            details += f"\n\n上下文信息:\n"
            for key, value in context.items():
                details += f"  {key}: {value}\n"

        self.details_text.setText(details)

        # 更新建议
        if suggestions:
            suggestions_text = "建议操作:\n"
            for i, suggestion in enumerate(suggestions, 1):
                suggestions_text += f"{i}. {suggestion}\n"
            self.suggestions_text.setText(suggestions_text)
        else:
            self.suggestions_text.setText("暂无建议，请查看日志获取更多帮助")

    def _on_close(self):
        """关闭对话框"""
        self.hide()
        self.closed.emit()


class ErrorToast(QFrame):
    """错误提示条

    顶部显示的错误提示通知
    """

    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 5000  # 显示时间（毫秒）
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFixedHeight(50)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(12)

        # 图标
        self.icon = IconWidget(FluentIcon.INFO)
        self.icon.setFixedSize(24, 24)
        layout.addWidget(self.icon)

        # 消息
        self.message = BodyLabel("")
        self.message.setStyleSheet("font-size: 12px; color: #333;")
        layout.addWidget(self.message, stretch=1)

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 16px;
                color: #666;
            }
            QPushButton:hover {
                color: #333;
            }
        """)
        close_btn.clicked.connect(self._on_dismiss)
        layout.addWidget(close_btn)

        self.setStyleSheet("""
            ErrorToast {
                background: #fff3cd;
                border-bottom: 2px solid #ffc107;
                border-radius: 4px;
            }
        """)
        self.icon.setStyleSheet("color: #ffc107;")

    def show_error(self, message: str, error_code: str = "", duration: int = None):
        """显示错误提示

        Args:
            message: 错误消息
            error_code: 错误代码
            duration: 显示时长（毫秒）
        """
        if error_code:
            self.message.setText(f"[{error_code}] {message}")
        else:
            self.message.setText(message)

        self.show()

        # 自动消失
        show_duration = duration or self.duration
        QTimer.singleShot(show_duration, self._on_dismiss)

    def _on_dismiss(self):
        """关闭提示"""
        self.hide()
        self.dismissed.emit()


def show_error_banner(
    parent,
    title: str,
    message: str,
    error_code: str = "",
    suggestions: list = None,
    recoverable: bool = True,
) -> ErrorDisplayWidget:
    """便捷函数：在父窗口中显示错误横幅

    Args:
        parent: 父窗口
        title: 标题
        message: 消息
        error_code: 错误代码
        suggestions: 建议列表
        recoverable: 是否可恢复

    Returns:
        ErrorDisplayWidget 实例
    """
    error_widget = ErrorDisplayWidget(parent)
    error_widget.set_error(title, message, error_code, suggestions, recoverable)
    return error_widget


# 导出
__all__ = [
    "TaskCard",
    "AgentStatCard",
    "ToolLoggerWidget",
    "ItemListCard",
    "ErrorDisplayWidget",
    "ErrorDetailsDialog",
    "ErrorToast",
    "show_error_banner",
]
