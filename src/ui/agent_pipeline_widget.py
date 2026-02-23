# -*- coding: utf-8 -*-
"""
AI 流水线可视化组件 - Agent Pipeline Widget

展示智能体的 4 阶段执行流程：扫描 → 审查 → 执行 → 报告
"""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QProgressBar, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from qfluentwidgets import FluentIcon, IconWidget

from .agent_theme import AgentTheme, AgentStage
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineStageCard(QFrame):
    """单个阶段卡片组件"""

    status_changed = pyqtSignal(str, str)  # stage_name, status

    def __init__(self, stage: str, icon: FluentIcon, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.icon = icon
        self.status = "idle"  # idle/running/completed/error/paused
        self.progress = 0
        self.tool_calls = []

        self._init_ui()
        self._update_style()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setFixedSize(140, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 顶部：图标和状态指示
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        # 图标
        icon_widget = IconWidget(self.icon)
        icon_widget.setFixedSize(24, 24)
        icon_widget.setStyleSheet(f'color: {AgentTheme.get_stage_color(self.stage)};')
        self.icon_widget = icon_widget
        top_row.addWidget(icon_widget)

        # 工具调用徽章
        self.tool_badge = QLabel()
        self.tool_badge.setFixedSize(16, 16)
        self.tool_badge.setAlignment(Qt.AlignCenter)
        self.tool_badge.setStyleSheet('''
            QLabel {
                background: #FF6B6B;
                color: white;
                border-radius: 8px;
                font-size: 9px;
                font-weight: bold;
            }
        ''')
        self.tool_badge.setVisible(False)
        top_row.addWidget(self.tool_badge)

        top_row.addStretch()
        layout.addLayout(top_row)

        # 阶段名称
        self.name_label = QLabel(AgentStage.get_name(self.stage))
        self.name_label.setStyleSheet('font-size: 13px; font-weight: 600;')
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('''
            QProgressBar {
                border: none;
                background: #e0e0e0;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: #0078D4;
                border-radius: 2px;
            }
        ''')
        layout.addWidget(self.progress_bar)

        # 状态文本
        self.status_label = QLabel("等待")
        self.status_label.setStyleSheet('font-size: 10px; color: #999;')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def set_stage_status(self, status: str):
        """设置阶段状态

        Args:
            status: 状态 (idle/running/completed/error/paused)
        """
        self.status = status
        self._update_style()
        self.status_changed.emit(self.stage, status)

    def update_progress(self, percent: int):
        """更新进度

        Args:
            percent: 进度百分比 (0-100)
        """
        self.progress = min(max(percent, 0), 100)
        self.progress_bar.setValue(self.progress)

    def add_tool_call(self, tool_name: str):
        """添加工具调用记录

        Args:
            tool_name: 工具名称
        """
        self.tool_calls.append(tool_name)
        count = len(self.tool_calls)
        self.tool_badge.setText(str(count) if count > 9 else str(count))
        self.tool_badge.setVisible(True)

    def clear_tool_calls(self):
        """清除工具调用记录"""
        self.tool_calls.clear()
        self.tool_badge.setVisible(False)

    def _update_style(self):
        """更新卡片样式"""
        color = AgentTheme.get_status_color(self.status)

        # 更新边框和背景
        if self.status == "idle":
            self.setStyleSheet(f'''
                QFrame {{
                    background: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }}
            ''')
            self.status_label.setText("等待")
        elif self.status == "running":
            self.setStyleSheet(f'''
                QFrame {{
                    background: {color}15;
                    border: 2px solid {color};
                    border-radius: 8px;
                }}
            ''')
            self.status_label.setText("进行中")
            self.status_label.setStyleSheet(f'font-size: 10px; color: {color};')
            # 启动进度条动画
            self.progress_bar.setStyleSheet(f'''
                QProgressBar {{
                    border: none;
                    background: #e0e0e0;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background: {color};
                    border-radius: 2px;
                }}
            ''')
        elif self.status == "completed":
            self.setStyleSheet(f'''
                QFrame {{
                    background: {color}10;
                    border: 1px solid {color};
                    border-radius: 8px;
                }}
            ''')
            self.status_label.setText("完成")
            self.status_label.setStyleSheet(f'font-size: 10px; color: {color};')
            self.progress_bar.setValue(100)
        elif self.status == "error":
            self.setStyleSheet(f'''
                QFrame {{
                    background: #fee2e2;
                    border: 1px solid {color};
                    border-radius: 8px;
                }}
            ''')
            self.status_label.setText("错误")
            self.status_label.setStyleSheet(f'font-size: 10px; color: {color};')
        elif self.status == "paused":
            self.setStyleSheet(f'''
                QFrame {{
                    background: #fff3cd;
                    border: 1px solid {color};
                    border-radius: 8px;
                }}
            ''')
            self.status_label.setText("已暂停")
            self.status_label.setStyleSheet(f'font-size: 10px; color: {color};')


class ProgressConnector(QFrame):
    """阶段间连接器，带进度动画"""

    def __init__(self, color: str = "#0078D4", parent=None):
        super().__init__(parent)
        self.color = color
        self._opacity = 0.0

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.HLine | QFrame.Sunken)
        self.setFixedHeight(3)
        self.setFixedWidth(30)
        self._opacity = 0.0
        self._update_style()

    def set_active(self, active: bool):
        """设置激活状态

        Args:
            active: 是否激活
        """
        # 创建透明度动画
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0 if active else 0.2)
        self.setGraphicsEffect(effect)

        if active:
            self.setStyleSheet(f'''
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                               stop:0 {self.color}40, stop:1 {self.color});
                    border-radius: 1px;
                }}
            ''')
        else:
            self.setStyleSheet('''
                QFrame {
                    background: #e0e0e0;
                    border-radius: 1px;
                }
            ''')

    def _update_style(self):
        """更新样式"""
        self.set_active(False)


class AgentPipelineWidget(QWidget):
    """AI 流水线可视化组件

    显示 4 阶段流程：扫描 → 审查 → 执行 → 报告
    """

    stage_changed = pyqtSignal(str, str)  # stage_name, new_status
    progress_updated = pyqtSignal(str, int)  # stage_name, percent
    tool_called = pyqtSignal(str, str)  # stage_name, tool_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stages: dict[str, PipelineStageCard] = {}
        self.connectors: dict[str, ProgressConnector] = {}
        self.active_stage = None

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setFixedHeight(120)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # 创建4个阶段卡片
        stages = [
            (AgentStage.SCAN, FluentIcon.SEARCH),
            (AgentStage.REVIEW, FluentIcon.CHECKBOX),
            (AgentStage.CLEANUP, FluentIcon.DELETE),
            (AgentStage.REPORT, FluentIcon.DOCUMENT)
        ]

        for stage_key, icon in stages:
            card = PipelineStageCard(stage_key, icon)
            self.stages[stage_key] = card
            main_layout.addWidget(card)

            # 连接信号
            card.status_changed.connect(self._on_stage_status_changed)

            # 添加连接器（除了最后一个阶段）
            if stage_key != AgentStage.REPORT:
                connector = ProgressConnector(AgentTheme.get_stage_color(stage_key))
                self.connectors[stage_key] = connector
                main_layout.addWidget(connector)

        main_layout.addStretch()

    def set_stage_status(self, stage: str, status: str):
        """设置阶段状态

        Args:
            stage: 阶段名称
            status: 状态 (idle/running/completed/error/paused)
        """
        if stage not in self.stages:
            logger.warning(f"[Pipeline] 未知的阶段: {stage}")
            return

        logger.debug(f"[Pipeline] 设置阶段状态: {stage} -> {status}")

        # 更新当前激活的阶段
        if status == "running":
            self.active_stage = stage
        elif status == "completed" and stage == self.active_stage:
            self.active_stage = None

        # 更新目标阶段状态
        self.stages[stage].set_stage_status(status)

        # 更新连接器状态
        all_stages = AgentStage.get_all_stages()
        for i, s in enumerate(all_stages):
            if s in self.connectors:
                is_active = False
                if self.active_stage:
                    # 连接器在激活阶段之前都应该激活
                    active_idx = all_stages.index(self.active_stage)
                    connector_idx = i
                    is_active = connector_idx < active_idx

                self.connectors[s].set_active(is_active or status == "completed")

    def update_progress(self, stage: str, percent: int):
        """更新阶段进度

        Args:
            stage: 阶段名称
            percent: 进度百分比 (0-100)
        """
        if stage not in self.stages:
            return

        self.stages[stage].update_progress(percent)
        self.progress_updated.emit(stage, percent)

    def add_tool_call_badge(self, stage: str, tool_name: str):
        """为阶段添加工具调用徽章

        Args:
            stage: 阶段名称
            tool_name: 工具名称
        """
        if stage not in self.stages:
            return

        self.stages[stage].add_tool_call(tool_name)
        self.tool_called.emit(stage, tool_name)

    def clear_stage(self, stage: str):
        """清除阶段状态

        Args:
            stage: 阶段名称
        """
        if stage not in self.stages:
            return

        self.stages[stage].set_stage_status("idle")
        self.stages[stage].update_progress(0)
        self.stages[stage].clear_tool_calls()

    def reset_all_stages(self):
        """重置所有阶段"""
        for stage in self.stages:
            self.clear_stage(stage)
        for connector in self.connectors.values():
            connector.set_active(False)
        self.active_stage = None

    def _on_stage_status_changed(self, stage: str, status: str):
        """阶段状态变化回调"""
        logger.debug(f"[Pipeline] 状态变化: {stage} -> {status}")
        self.stage_changed.emit(stage, status)


# 导出
__all__ = [
    "AgentPipelineWidget",
    "PipelineStageCard",
    "ProgressConnector"
]
