# -*- coding: utf-8 -*-
"""
AI 思考流显示组件 - Agent Thinking Stream

实时显示 AI 的思考过程、工具调用和结果
类似 ChatGPT 的对话界面
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
    QSizePolicy,
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QMargins,
)
from PyQt5.QtGui import QFont, QColor

from qfluentwidgets import (
    FluentIcon,
    IconWidget,
    ToolButton,
    StrongBodyLabel,
    BodyLabel,
)

from .agent_theme import AgentTheme
from utils.logger import get_logger

logger = get_logger(__name__)


class MessageType:
    """消息类型"""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"
    THINKING = "thinking"


class MessageBubble(QFrame):
    """消息气泡组件"""

    copy_requested = pyqtSignal(str)  # 请求复制文本

    def __init__(
        self, msg_type: str, content: str = "", tool_name: str = "", parent=None
    ):
        super().__init__(parent)
        self.msg_type = msg_type
        self.content = content
        self.tool_name = tool_name
        self.collapsed = False
        self.collapsible = msg_type in [
            MessageType.ASSISTANT,
            MessageType.TOOL,
            MessageType.THINKING,
        ]

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 创建消息内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 8, 12, 8)
        self.content_layout.setSpacing(4)

        # 顶部标签栏（可折叠区域）
        self._create_header()
        layout.addWidget(self.content_widget)

    def _create_header(self):
        """创建消息头部"""
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        # 图标
        if self.msg_type == MessageType.USER:
            icon = FluentIcon.PERSON
            icon_color = AgentTheme.SCAN_COLOR
            label_text = "用户"
        elif self.msg_type == MessageType.ASSISTANT:
            icon = FluentIcon.ROBOT
            icon_color = AgentTheme.CLEANUP_COLOR
            label_text = "AI 助手"
        elif self.msg_type == MessageType.TOOL:
            icon = FluentIcon.DEVELOPER_TOOLS
            icon_color = AgentTheme.REVIEW_COLOR
            label_text = f"工具: {self.tool_name}"
        elif self.msg_type == MessageType.THINKING:
            icon = FluentIcon.LIGHTBULB
            icon_color = AgentTheme.REPORT_COLOR
            label_text = "AI 思考"
        else:  # SYSTEM
            icon = FluentIcon.SETTING
            icon_color = "#666"
            label_text = "系统"

        # 图标和标签
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(16, 16)
        icon_widget.setStyleSheet(f"color: {icon_color};")
        header.addWidget(icon_widget)

        type_label = QLabel(label_text)
        type_label.setStyleSheet(
            f"font-size: 11px; color: {icon_color}; font-weight: 600;"
        )
        header.addWidget(type_label)

        header.addStretch()

        # 折叠按钮（如果可折叠）
        if self.collapsible:
            self.collapse_btn = QPushButton()
            self.collapse_btn.setFixedSize(20, 20)
            self.collapse_btn.setText("▼")
            self.collapse_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #999;
                    font-size: 8px;
                }
                QPushButton:hover {
                    background: #f0f0f0;
                }
            """)
            self.collapse_btn.clicked.connect(self._toggle_collapse)
            header.addWidget(self.collapse_btn)

        self.content_layout.addLayout(header)

        # 内容文本
        if self.content:
            text_label = BodyLabel(self.content)
            text_label.setWordWrap(True)
            text_label.setStyleSheet("font-size: 12px; color: #333; line-height: 1.6;")

            # 给工具调用结果添加特殊样式
            if self.msg_type == MessageType.TOOL:
                self.content_widget.setStyleSheet(f"""
                    QWidget {{
                        background: {AgentTheme.REVIEW_COLOR}10;
                        border-left: 3px solid {AgentTheme.REVIEW_COLOR};
                        border-radius: 4px;
                    }}
                """)
            elif self.msg_type == MessageType.ASSISTANT:
                self.content_widget.setStyleSheet("""
                    QWidget {
                        background: #f5f5f5;
                        border-radius: 8px;
                    }
                """)
            elif self.msg_type == MessageType.THINKING:
                self.content_widget.setStyleSheet(f"""
                    QWidget {{
                        background: {AgentTheme.REPORT_COLOR}08;
                        border-left: 3px solid {AgentTheme.REPORT_COLOR};
                        border-radius: 4px;
                    }}
                """)
            else:  # USER
                self.content_widget.setStyleSheet("""
                    QWidget {
                        background: #e3f2fd;
                        border-radius: 8px;
                    }
                """)

            self.content_layout.addWidget(text_label)

    def _toggle_collapse(self):
        """切换折叠状态"""
        self.collapsed = not self.collapsed

        if self.collapsed:
            self.collapse_btn.setText("▶")
            # 隐藏内容，只保留头部
            for i in reversed(range(self.content_layout.count())):
                item = self.content_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if widget not in self._get_header_widgets():
                        widget.setVisible(False)
                    self.content_layout.update()
        else:
            self.collapse_btn.setText("▼")
            # 显示所有内容
            for i in range(self.content_layout.count()):
                item = self.content_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    widget.setVisible(True)

    def _get_header_widgets(self):
        """获取头部组件列表"""
        widgets = []
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widgets.append(widget)
                if isinstance(widget, QHBoxLayout):
                    for j in range(widget.count()):
                        sub_item = widget.itemAt(j)
                        if sub_item and sub_item.widget():
                            widgets.append(sub_item.widget())
        return widgets


class ThinkingStreamWidget(QWidget):
    """AI 思考流显示组件 - 优化版，支持消息限制和批量更新

    特性:
    - 实时滚动：新消息自动滚动显示
    - 可折叠：点击展开/折叠每条消息
    - 类型区分：文本/工具调用/思考使用不同样式
    - 性能优化：限制消息数量，批量处理更新
    """

    message_added = pyqtSignal(str)
    tool_executed = pyqtSignal(str, str)

    MAX_MESSAGES = 50
    VISIBLE_THROTTLE_MS = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.auto_scroll = True
        self.auto_collapse_historical = True
        self._scroll_throttle = QTimer()
        self._scroll_throttle.setSingleShot(True)
        self._scroll_throttle.timeout.connect(self._do_scroll_to_bottom)

        self._init_ui()
        self._setup_scroll_behavior()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._create_header()
        layout.addWidget(self.header_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, stretch=1)

        self._create_footer()
        layout.addWidget(self.footer_widget)

    def _create_header(self):
        """创建顶部控制栏"""
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(40)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(12)

        title = StrongBodyLabel("AI 思考过程")
        title.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.count_label = BodyLabel("0 条消息")
        self.count_label.setStyleSheet("color: #999; font-size: 11px;")
        header_layout.addWidget(self.count_label)

        self.collapse_all_btn = QPushButton("折叠全部")
        self.collapse_all_btn.setFixedSize(80, 26)
        self.collapse_all_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #e8e8e8;
            }
        """)
        self.collapse_all_btn.clicked.connect(self._collapse_all)
        self.collapse_all_btn.setVisible(False)
        header_layout.addWidget(self.collapse_all_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedSize(60, 26)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #f5f5f5;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #e8e8e8;
            }
        """)
        self.clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(self.clear_btn)

    def _create_footer(self):
        """创建底部控制栏"""
        self.footer_widget = QWidget()
        self.footer_widget.setFixedHeight(35)
        footer_layout = QHBoxLayout(self.footer_widget)
        footer_layout.setContentsMargins(12, 4, 12, 8)
        footer_layout.setSpacing(8)

        self.auto_scroll_btn = QPushButton("自动滚动: 开")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.toggled.connect(self._toggle_auto_scroll)
        self.auto_scroll_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 10px;
                padding: 4px 8px;
            }
            QPushButton:checked {
                background: #e3f2fd;
                border: 1px solid #0078D4;
            }
        """)
        footer_layout.addWidget(self.auto_scroll_btn)

        footer_layout.addStretch()

        self.scroll_bottom_btn = QPushButton("↓")
        self.scroll_bottom_btn.setFixedSize(30, 24)
        self.scroll_bottom_btn.clicked.connect(self._scroll_to_bottom)
        self.scroll_bottom_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #005a9e;
            }
        """)
        footer_layout.addWidget(self.scroll_bottom_btn)

    def _setup_scroll_behavior(self):
        """设置滚动行为"""
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _add_message(self, msg_type: str, content: str, tool_name: str = ""):
        """内部方法：添加消息（带限制）"""
        # 限制消息数量
        while len(self.messages) >= self.MAX_MESSAGES:
            oldest = self.messages.pop(0)
            oldest.deleteLater()
            self.messages_layout.removeWidget(oldest)

        bubble = MessageBubble(msg_type, content, tool_name)
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, bubble)

        self.messages.append(bubble)
        self._update_count()

        if self.auto_scroll:
            self._scroll_throttle.start(self.VISIBLE_THROTTLE_MS)

        if self.auto_collapse_historical and len(self.messages) > 5:
            self._collapse_historical()

    def _do_scroll_to_bottom(self):
        """执行滚动到底部"""
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def add_user_message(self, text: str):
        """添加用户消息"""
        self._add_message(MessageType.USER, text)

    def add_assistant_message(self, text: str):
        """添加助手消息"""
        self._add_message(MessageType.ASSISTANT, text)
        self.message_added.emit(MessageType.ASSISTANT)

    def add_tool_result(self, tool_name: str, result: str):
        """添加工具执行结果"""
        if len(result) > 2000:
            result = result[:2000] + "\n... (已截断)"
        self._add_message(MessageType.TOOL, result, tool_name)
        self.tool_executed.emit(tool_name, result)

    def add_thinking(self, thought_text: str):
        """添加 AI 思考内容"""
        self._add_message(MessageType.THINKING, thought_text)

    def add_system_message(self, text: str):
        """添加系统消息"""
        self._add_message(MessageType.SYSTEM, text)

    def toggle_collapse_all(self, collapsed: bool):
        """切换所有消息折叠状态"""
        for bubble in self.messages:
            if bubble.collapsed != collapsed:
                bubble._toggle_collapse()
        self.collapse_all_btn.setText("展开全部" if collapsed else "折叠全部")

    def _collapse_all(self):
        """折叠全部消息"""
        currently_collapsed = self.collapse_all_btn.text() == "展开全部"
        self.toggle_collapse_all(not currently_collapsed)

    def _collapse_historical(self):
        """自动折叠历史消息"""
        if len(self.messages) <= 3:
            return
        for i, bubble in enumerate(self.messages[:-3]):
            if not bubble.collapsed:
                bubble._toggle_collapse()

    def clear(self):
        """清空消息历史"""
        for bubble in self.messages:
            bubble.deleteLater()
        self.messages.clear()
        self._update_count()
        logger.info("[ThinkingStream] 已清空消息历史")

    def _update_count(self):
        """更新消息计数"""
        count = len(self.messages)
        self.count_label.setText(f"{count} 条消息")
        self.collapse_all_btn.setVisible(count > 2)

    def _scroll_to_bottom(self):
        """滚动到底部（节流）"""
        self._scroll_throttle.start(self.VISIBLE_THROTTLE_MS)

    def _toggle_auto_scroll(self, enabled: bool):
        """切换自动滚动"""
        self.auto_scroll = enabled
        self.auto_scroll_btn.setText(f"自动滚动: {'开' if enabled else '关'}")
        if enabled:
            self._do_scroll_to_bottom()

    def _on_scroll(self, value: int):
        """滚动事件处理"""
        max_val = self.scroll_area.verticalScrollBar().maximum()
        if max_val - value < 50:
            if not self.auto_scroll:
                self.auto_scroll_btn.setChecked(True)
        elif value < max_val - 200:
            if self.auto_scroll and max_val > 100:
                self.auto_scroll_btn.setChecked(False)


# 导出
__all__ = ["ThinkingStreamWidget", "MessageBubble", "MessageType"]
