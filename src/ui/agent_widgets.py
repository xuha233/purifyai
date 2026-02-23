# -*- coding: utf-8 -*-
"""
通用智能体 UI 组件 - Agent Widgets

提供智能体系统中常用的可复用组件
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QProgressBar, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from qfluentwidgets import (
    SimpleCardWidget, StrongBodyLabel, BodyLabel, IconWidget,
    FluentIcon
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

        title_icon = IconWidget(FluentIcon.TASK)
        title_icon.setFixedSize(20, 20)
        title_icon.setStyleSheet('color: #0078D4;')
        title_row.addWidget(title_icon)

        self.task_title = StrongBodyLabel("当前任务")
        self.task_title.setStyleSheet('font-size: 15px;')
        title_row.addWidget(self.task_title)

        title_row.addStretch()
        layout.addLayout(title_row)

        # 任务状态
        self.task_status_label = BodyLabel("准备就绪")
        self.task_status_label.setStyleSheet('font-size: 13px; color: #999;')
        layout.addWidget(self.task_status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('''
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
        ''')
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
        btn.setStyleSheet(f'''
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
        ''')
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
            self.start_btn.setStyleSheet('''
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
            ''')
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif status == "running":
            self.start_btn.setText("运行中")
            self.start_btn.setEnabled(False)
            self.start_btn.setStyleSheet('''
                QPushButton {
                    background: #e0e0e0;
                    color: #999;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            ''')
            self.pause_btn.setText("暂停")
            self.pause_btn.setEnabled(True)
            self.pause_btn.setStyleSheet('''
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
            ''')
            self.stop_btn.setEnabled(True)
        elif status == "paused":
            self.start_btn.setText("继续")
            self.start_btn.setEnabled(True)
            self.start_btn.setStyleSheet('''
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
            ''')
            self.pause_btn.setText("已暂停")
            self.pause_btn.setEnabled(False)
            self.pause_btn.setStyleSheet('''
                QPushButton {
                    background: #e0e0e0;
                    color: #999;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            ''')
            self.stop_btn.setEnabled(True)
        elif status == "completed":
            self.start_btn.setText("完成")
            self.start_btn.setEnabled(False)
            self.start_btn.setStyleSheet('''
                QPushButton {
                    background: #e0e0e0;
                    color: #999;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            ''')
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
        elif status == "error":
            self.start_btn.setText("重试")
            self.start_btn.setEnabled(True)
            self.start_btn.setStyleSheet('''
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
            ''')
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)


class AgentStatCard(SimpleCardWidget):
    """智能体统计卡片"""

    def __init__(self, value: str, label: str, icon: FluentIcon, color: str, parent=None):
        super().__init__(parent)
        self.color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(36, 36)
        icon_widget.setStyleSheet(f'color: {color};')
        layout.addWidget(icon_widget)

        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        value_label = StrongBodyLabel(value)
        value_label.setStyleSheet(f'font-size: 22px; color: {color}; font-weight: 700;')
        content_layout.addWidget(value_label)

        text_label = BodyLabel(label)
        text_label.setStyleSheet('font-size: 11px; color: #999;')
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
    """工具调用日志组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toolbar_height = 40
        self.max_entries = 50
        self.entries = []

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 表头
        header = QWidget()
        header.setFixedHeight(self.toolbar_height)
        header.setStyleSheet('''
            QWidget {
                background: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
            }
        ''')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        # 列标题
        headers = ["时间", "阶段", "工具", "状态"]
        widths = [80, 60, 150, 0]  # 最后一个设置为0表示stretch

        for i, (header_text, width) in enumerate(zip(headers, widths)):
            label = StrongBodyLabel(header_text)
            label.setStyleSheet('font-size: 11px; color: #666; font-weight: 600;')
            if width > 0:
                label.setFixedWidth(width)
            else:
                header_layout.addStretch()
                header_layout.addWidget(label)
                break
            header_layout.addWidget(label)

        layout.addWidget(header)

        # 内容区域
        self.content_area = QWidget()
        self.content_area.setStyleSheet('background: white;')
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.addStretch()

        layout.addWidget(self.content_area, stretch=1)

    def add_entry(self, stage: str, tool_name: str, status: str = "success"):
        """添加日志条目

        Args:
            stage: 执行阶段
            tool_name: 工具名称
            status: 执行状态 (success/error)
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        status_colors = {
            "success": "#28a745",
            "error": "#dc3545",
            "pending": "#FFA500"
        }

        entry = QWidget()
        entry.setFixedHeight(32)
        entry.setStyleSheet('''
            QWidget {
                border-bottom: 1px solid #f0f0f0;
            }
            QWidget:hover {
                background: #f8f8f8;
            }
        ''')
        entry_layout = QHBoxLayout(entry)
        entry_layout.setContentsMargins(12, 0, 12, 0)

        # 时间
        time_label = BodyLabel(timestamp)
        time_label.setFixedWidth(80)
        time_label.setStyleSheet('font-size: 11px; color: #999;')
        entry_layout.addWidget(time_label)

        # 阶段
        stage_label = BodyLabel(stage)
        stage_label.setFixedWidth(60)
        stage_label.setStyleSheet('font-size: 11px; color: #666;')
        entry_layout.addWidget(stage_label)

        # 工具名
        tool_label = BodyLabel(tool_name)
        tool_label.setFixedWidth(150)
        tool_label.setStyleSheet('font-size: 11px; color: #333;')
        entry_layout.addWidget(tool_label)

        # 状态
        status_color = status_colors.get(status, "#999")
        status_text = {"success": "成功", "error": "失败", "pending": "进行中"}.get(status, status)
        status_label = BodyLabel(status_text)
        status_label.setStyleSheet(f'font-size: 11px; color: {status_color};')
        entry_layout.addWidget(status_label)

        entry_layout.addStretch()

        # 添加到布局
        self.content_layout.insertWidget(self.content_layout.count() - 1, entry)
        self.entries.append(entry)

        # 限制条目数量
        while len(self.entries) > self.max_entries:
            oldest = self.entries.pop(0)
            oldest.deleteLater()

    def clear(self):
        """清空日志"""
        for entry in self.entries:
            entry.deleteLater()
        self.entries.clear()


class ItemListCard(SimpleCardWidget):
    """项目列表卡片组件"""

    item_selected = pyqtSignal(object)  # item_data
    item_action = pyqtSignal(str)  # action_type

    def __init__(self, title: str = "清理项目", parent=None):
        super().__init__(parent)
        self.items = []
        self.selected_items = set()

        self._init_ui(title)

    def _init_ui(self, title: str):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题栏
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.title_label = StrongBodyLabel(title)
        self.title_label.setStyleSheet('font-size: 13px;')
        header.addWidget(self.title_label)

        header.addStretch()

        # 筛选按钮
        filter_btn = QPushButton("筛选")
        filter_btn.setFixedSize(50, 24)
        filter_btn.clicked.connect(lambda: self.item_action.emit("filter"))
        header.addWidget(filter_btn)

        # 排序按钮
        sort_btn = QPushButton("排序")
        sort_btn.setFixedSize(50, 24)
        sort_btn.clicked.connect(lambda: self.item_action.emit("sort"))
        header.addWidget(sort_btn)

        layout.addLayout(header)

        # 项目计数
        self.count_label = BodyLabel("0 个项目")
        self.count_label.setStyleSheet('color: #999; font-size: 11px;')
        layout.addWidget(self.count_label)

        # 列表容器（滚动区域）
        from PyQt5.QtWidgets import QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet('''
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: #fafafa;
            }
        ''')

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, stretch=1)

    def add_item(self, item_data: dict):
        """添加项目

        Args:
            item_data: 项目数据字典
        """
        item_widget = self._create_item_widget(item_data)
        self.list_layout.insertWidget(self.list_layout.count() - 1, item_widget)
        self.items.append(item_widget)
        self._update_count()

    def _create_item_widget(self, item_data: dict) -> QWidget:
        """创建项目组件"""
        widget = QWidget()
        widget.setFixedHeight(44)
        widget.setStyleSheet('''
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
        ''')

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        # 复选框
        from PyQt5.QtWidgets import QCheckBox
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(lambda state: self._on_item_selected(widget, item_data, state))
        layout.addWidget(checkbox)

        # 图标
        icon = IconWidget(FluentIcon.DOCUMENT)
        icon.setFixedSize(20, 20)
        icon.setStyleSheet('color: #666;')
        layout.addWidget(icon)

        # 名称
        name = item_data.get("name", "未知")
        name_label = BodyLabel(name)
        name_label.setStyleSheet('font-size: 12px; color: #333;')
        name_label.setMaximumWidth(200)
        layout.addWidget(name_label)

        layout.addStretch()

        # 大小
        size = item_data.get("size", 0)
        size_label = BodyLabel(self._format_size(size))
        size_label.setStyleSheet('font-size: 11px; color: #999;')
        layout.addWidget(size_label)

        return widget

    def _on_item_selected(self, widget: QWidget, item_data: dict, state: int):
        """项目选中回调"""
        if state == 2:  # Checked
            self.selected_items.add(item_data.get("id", id(item_data)))
            widget.setProperty("selected", True)
        else:
            self.selected_items.discard(item_data.get("id", id(item_data)))
            widget.setProperty("selected", False)

        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _update_count(self):
        """更新项目计数"""
        self.count_label.setText(f"{len(self.items)} 个项目")

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def clear(self):
        """清空列表"""
        for item in self.items:
            item.deleteLater()
        self.items.clear()
        self.selected_items.clear()
        self._update_count()


# 导出
__all__ = [
    "TaskCard",
    "AgentStatCard",
    "ToolLoggerWidget",
    "ItemListCard"
]
