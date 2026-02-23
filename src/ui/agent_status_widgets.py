# -*- coding: utf-8 -*-
"""
智能体状态显示组件 - Agent Status Widget

显示智能体系统的运行状态和实时信息
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QProgressBar,
    QStackedWidget, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

from utils.logger import get_logger
from .agent_config import (
    AGENT_UI_TEXTS, AI_RISK_POLICY, get_agent_mode_info
)

logger = get_logger(__name__)


class AgentStatusFrame(QFrame):
    """智能体状态框架"""

    status_changed = pyqtSignal(str)  # 状态变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_status = "idle"
        self.agent_mode = "hybrid"
        self.logger = logger

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # 状态指示器
        self.status_container = QStackedWidget()

        # 空闲状态
        self.idle_widget = self._create_idle_widget()
        self.status_container.addWidget(self.idle_widget)

        # 运行状态
        self.running_widget = self._create_running_widget()
        self.status_container.addWidget(self.running_widget)

        # 完成状态
        self.completed_widget = self._create_completed_widget()
        self.status_container.addWidget(self.completed_widget)

        layout.addWidget(self.status_container)

    def _create_idle_widget(self) -> QWidget:
        """创建空闲状态组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 状态图标和文本
        status_label = QLabel("智能体系统就绪")
        status_label.setMinimumWidth(120)
        status_label.setStyleSheet("font-size: 14px; color: rgba(0, 0, 0, 0.6);")

        # 模式显示
        mode_info = QLabel()
        mode_info.setText(f"模式: {AGENT_UI_TEXTS['mode_hybrid']}")
        mode_info.setStyleSheet("""
            QLabel {
                background: rgba(82, 196, 26, 0.1);
                border-radius: 4px;
                padding: 6px 12px;
                color: #52C41A;
                font-size: 13px;
            }
        """)
        mode_info.setObjectName("mode_info")

        layout.addWidget(status_label)
        layout.addStretch()
        layout.addWidget(mode_info)

        return widget

    def _create_running_widget(self) -> QWidget:
        """创建运行状态组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(8)

        # 状态行
        status_layout = QHBoxLayout()

        self.running_status_label = QLabel()
        self.running_status_label.setText(AGENT_UI_TEXTS['agent_scanning'])
        self.running_status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1890FF;")

        self.stage_label = QLabel()
        self.stage_label.setText("扫描")
        self.stage_label.setStyleSheet("""
            QLabel {
                background: rgba(24, 144, 255, 0.1);
                border-radius: 4px;
                padding: 4px 10px;
                color: #1890FF;
                font-size: 12px;
            }
        """)

        status_layout.addWidget(self.running_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.stage_label)
        layout.addLayout(status_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: rgba(0, 0, 0, 0.05);
                border-radius: 4px;
                height: 6px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #1890FF, stop:1 #36CFC9);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 详情行
        self.details_label = QLabel()
        self.details_label.setText("准备中...")
        self.details_label.setStyleSheet("color: rgba(0, 0, 0, 0.5); font-size: 12px;")
        layout.addWidget(self.details_label)

        return widget

    def _create_completed_widget(self) -> QWidget:
        """创建完成状态组件"""
        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 5, 0, 5)
        grid.setSpacing(10)

        # 状态图标
        status_label = QLabel("✓")
        status_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #52C41A;
            }
        """)
        status_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(status_label, 0, 0, 2, 1)

        # 结果摘要
        self.completed_status_label = QLabel()
        self.completed_status_label.setText("执行完成")
        self.completed_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        grid.addWidget(self.completed_status_label, 0, 1)

        # 详情
        self.completed_details_label = QLabel()
        self.completed_details_label.setText("清理了 100 个文件，释放 1GB")
        self.completed_details_label.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-size: 13px;")
        grid.addWidget(self.completed_details_label, 1, 1)

        # 查看报告按钮
        view_report_btn = QPushButton("查看报告")
        view_report_btn.setStyleSheet("""
            QPushButton {
                background: #F0F0F0;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                color: rgba(0, 0, 0, 0.65);
                font-size: 12px;
            }
            QPushButton:hover {
                background: #E6E6E6;
            }
        """)
        view_report_btn.clicked.connect(self._on_view_report)
        grid.addWidget(view_report_btn, 0, 2, 2, 1)

        grid.setColumnStretch(1, 1)

        return widget

    def set_status(self, status: str, **kwargs):
        """设置状态

        Args:
            status: 状态 (idle/running/completed/error)
            **kwargs: 额外参数
        """
        self.current_status = status
        self.status_changed.emit(status)

        if status == "idle":
            self.status_container.setCurrentWidget(self.idle_widget)
            self._update_mode_display()

        elif status == "running":
            self.status_container.setCurrentWidget(self.running_widget)
            self._update_running_display(**kwargs)

        elif status == "completed":
            self.status_container.setCurrentWidget(self.completed_widget)
            self._update_completed_display(**kwargs)

        elif status == "error":
            self.status_container.setCurrentWidget(self.completed_widget)
            self._update_error_display(**kwargs)

    def _update_mode_display(self):
        """更新模式显示"""
        mode_info = self.idle_widget.findChild(QLabel, "mode_info")
        if mode_info:
            mode_name = AGENT_UI_TEXTS.get(f"mode_{self.agent_mode}", self.agent_mode)
            mode_info.setText(f"模式: {mode_name}")

    def _update_running_display(self, stage: str = "", progress: int = 0, details: str = ""):
        """更新运行状态显示

        Args:
            stage: 当前阶段
            progress: 进度 (0-100)
            details: 详情文本
        """
        if stage:
            self.stage_label.setText(stage)

        if progress:
            self.progress_bar.setValue(progress)

        if details:
            self.details_label.setText(details)

    def _update_completed_display(self, summary: str = "", details: str = ""):
        """更新完成状态显示

        Args:
            summary: 摘要
            details: 详情
        """
        if summary:
            self.completed_status_label.setText(summary)

        if details:
            self.completed_details_label.setText(details)

    def _update_error_display(self, error: str = ""):
        """更新错误状态显示

        Args:
            error: 错误信息
        """
        self.completed_status_label.setText("执行失败")
        self.completed_status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF4D4F;")
        self.completed_details_label.setText(error or "未知错误")

    def set_agent_mode(self, mode: str):
        """设置智能体模式

        Args:
            mode: 模式字符串
        """
        self.agent_mode = mode
        if self.current_status == "idle":
            self._update_mode_display()

    def _on_view_report(self):
        """查看报告按钮回调"""
        # TODO: 实现报告查看功能
        pass


class AgentStatsWidget(QWidget):
    """智能体统计组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QGridLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        # 统计项
        self.stats_labels = {}

        stats = [
            ("scan_count", "扫描次数", "0"),
            ("ai_calls", "AI调用", "0"),
            ("files_cleaned", "清理文件", "0"),
            ("space_freed", "释放空间", "0 MB")
        ]

        for i, (key, label, initial) in enumerate(stats):
            # 标签
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: rgba(0, 0, 0, 0.5); font-size: 12px;")

            # 值
            value_label = QLabel(initial)
            value_label.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: rgba(0, 0, 0, 0.85);
                }
            """)
            value_label.setAlignment(Qt.AlignLeft)

            layout.addWidget(label_widget, i // 2, (i % 2) * 2)
            layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)

            self.stats_labels[key] = value_label

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

    def update_stats(self, stats: dict):
        """更新统计数据

        Args:
            stats: 统计数据字典
        """
        mappings = {
            "scan_count": "scan_count",
            "ai_calls": "ai_calls",
            "files_cleaned": "files_cleaned",
            "space_freed": "total_freed_bytes"
        }

        for stat_key, data_key in mappings.items():
            value = 0
            if data_key in stats:
                value = stats[data_key]

            # 格式化显示
            if stat_key == "space_freed":
                value = self._format_bytes(value)
            else:
                value = str(value)

            if stat_key in self.stats_labels:
                self.stats_labels[stat_key].setText(value)

    def _format_bytes(self, bytes_size: int) -> str:
        """格式化字节数

        Args:
            bytes_size: 字节数

        Returns:
            格式化字符串
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    def reset(self):
        """重置统计"""
        for label in self.stats_labels.values():
            if "space" in str(label.text()):
                label.setText("0 MB")
            else:
                label.setText("0")


# 导出
__all__ = [
    "AgentStatusFrame",
    "AgentStatsWidget"
]
