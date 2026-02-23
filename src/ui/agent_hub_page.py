# -*- coding: utf-8 -*-
"""
智能体中心页面 - Agent Hub Page

智能体系统的核心控制中心，统一管理所有 AI 清理任务
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSplitter, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from qfluentwidgets import (
    StrongBodyLabel, SubtitleLabel, BodyLabel, SimpleCardWidget,
    PushButton, PrimaryPushButton, FluentIcon, IconWidget,
    InfoBar, InfoBarPosition, ScrollArea
)

from .agent_status_widgets import AgentStatusFrame, AgentStatsWidget
from .agent_pipeline_widget import AgentPipelineWidget
from .agent_thinking_stream import ThinkingStreamWidget
from .agent_control_panel import AgentControlPanel
from .agent_widgets import TaskCard, AgentStatCard, ToolLoggerWidget, ItemListCard
from .agent_theme import AgentTheme, AgentStage, AgentStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentHubPage(QWidget):
    """智能体中心页面 - Agent Hub

    统一控制面板，管理所有 AI 清理任务

    布局:
    ┌─────────────────────────────────────────────────────────────┐
    │  Agent Status Card  │  任务控制面板           │  统计面板    │
    ├─────────────────────┼───────────────────────┼──────────────┤
    │  AI Pipeline        │                       │              │
    │  [扫描→审查→执行→报告]│                      │              │
    ├─────────────────────┼───────────────────────┤              │
    │  Thinking Stream    │  项目列表             │              │
    │  (AI思考流)         │                       │              │
    ├─────────────────────┼───────────────────────┤              │
    │  Tool Logger        │                       │              │
    │  (工具调用日志)      │                       │              │
    └─────────────────────┴───────────────────────┴──────────────┘
    """

    # 信号
    task_started = pyqtSignal(dict)
    task_paused = pyqtSignal()
    task_resumed = pyqtSignal()
    task_stopped = pyqtSignal()
    mode_changed = pyqtSignal(str)
    scan_requested = pyqtSignal(str)  # scan_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"  # idle, scanning, analyzing, paused, completed, error
        self.timer = QTimer()

        self._init_ui()
        self._connect_signals()

        logger.info("[AgentHub] 智能体中心页面初始化完成")

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== 顶部标题栏 ==========
        self._create_header()
        main_layout.addWidget(self.header_widget)

        # ========== 滚动内容区域 ==========
        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet('''
            ScrollArea {
                border: none;
                background: transparent;
            }
        ''')

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(12)

        # ========== 第一行：状态 + 任务控制 + 统计 ==========
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(12)

        # 智能体状态卡片
        self.status_card = AgentStatusFrame()
        self.status_card.setFixedHeight(120)
        top_row_layout.addWidget(self.status_card)

        # 任务控制面板
        self.task_panel = SimpleCardWidget()
        self.task_panel.setMinimumWidth(260)
        self.task_panel.setMaximumWidth(300)
        task_panel_layout = QVBoxLayout(self.task_panel)
        task_panel_layout.setContentsMargins(12, 12, 12, 12)

        task_title = SubtitleLabel("任务控制")
        task_title.setStyleSheet('font-size: 14px;')
        task_panel_layout.addWidget(task_title)

        self.task_card = TaskCard()
        self.task_card.setMinimumHeight(100)
        task_panel_layout.addWidget(self.task_card)

        top_row_layout.addWidget(self.task_panel)

        # 统计面板
        self.stats_panel = SimpleCardWidget()
        self.stats_panel.setMinimumWidth(240)
        self.stats_panel.setMaximumWidth(280)
        stats_layout = QVBoxLayout(self.stats_panel)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(8)

        stats_title = SubtitleLabel("统计概览")
        stats_title.setStyleSheet('font-size: 14px;')
        stats_layout.addWidget(stats_title)

        # 统计卡片
        stats_grid = QVBoxLayout()

        self.scans_card = AgentStatCard(
            "0", "扫描次数", FluentIcon.HISTORY,
            AgentTheme.SCAN_COLOR
        )
        stats_grid.addWidget(self.scans_card)

        self.ai_calls_card = AgentStatCard(
            "0", "AI 调用", FluentIcon.ROBOT,
            AgentTheme.REPORT_COLOR
        )
        stats_grid.addWidget(self.ai_calls_card)

        self.files_card = AgentStatCard(
            "0", "清理文件", FluentIcon.DELETE,
            AgentTheme.CLEANUP_COLOR
        )
        stats_grid.addWidget(self.files_card)

        self.space_card = AgentStatCard(
            "0 MB", "释放空间", FluentIcon.SAVE,
            AgentTheme.PRIMARY
        )
        stats_grid.addWidget(self.space_card)

        stats_layout.addLayout(stats_grid)

        top_row_layout.addWidget(self.stats_panel)
        top_row_layout.addStretch()

        content_layout.addLayout(top_row_layout)

        # ========== AI Pipeline 区域 ==========
        self._create_pipeline_area(content_layout)

        # ========== 分割线 ==========
        content_layout.addWidget(self._create_separator())

        # ========== 主体区域：左侧思考流 + 右侧项目列表 ==========
        split_layout = QHBoxLayout()
        split_layout.setSpacing(12)

        # 左侧：思考流
        left_panel = SimpleCardWidget()
        left_panel.setMinimumWidth(350)
        left_panel.setMaximumWidth(450)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        left_header = self._create_panel_header("AI 思考流", FluentIcon.EDIT)
        left_layout.addWidget(left_header)

        self.thinking_stream = ThinkingStreamWidget()
        left_layout.addWidget(self.thinking_stream)

        split_layout.addWidget(left_panel)

        # 右侧：项目列表
        right_panel = SimpleCardWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_header = self._create_panel_header("清理项目", FluentIcon.DOCUMENT)
        right_layout.addWidget(right_header)

        self.item_list = ItemListCard()
        right_layout.addWidget(self.item_list)

        split_layout.addWidget(right_panel, stretch=1)

        content_layout.addLayout(split_layout, stretch=1)

        # ========== 工具调用日志 ==========
        self._create_tool_logger_area(content_layout)

        # ========== 底部状态栏 ==========
        self._create_status_bar(content_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, stretch=1)

    def _create_header(self):
        """创建顶部标题栏"""
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(50)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(24, 12, 24, 12)
        header_layout.setSpacing(16)

        # Logo 和标题
        icon_widget = IconWidget(FluentIcon.GLOBE)
        icon_widget.setFixedSize(28, 28)
        icon_widget.setStyleSheet('color: #0078D4;')
        header_layout.addWidget(icon_widget)

        title = StrongBodyLabel('智能体中心')
        title.setStyleSheet('font-size: 20px; color: #2c2c2c;')
        header_layout.addWidget(title)

        # AI 状态指示
        ai_status = BodyLabel("AI 系统: 就绪")
        ai_status.setIcon(FluentIcon.ACCEPT, FluentIcon.VIEW)
        ai_status.setStyleSheet('color: #52C41A; font-size: 13px;')
        header_layout.addWidget(ai_status)

        header_layout.addStretch()

        # 快速操作按钮
        quick_scan_btn = PushButton(FluentIcon.SEARCH, "快速扫描")
        quick_scan_btn.clicked.connect(lambda: self.scan_requested.emit("quick"))
        quick_scan_btn.setFixedHeight(36)
        header_layout.addWidget(quick_scan_btn)

        ai_review_btn = PushButton(FluentIcon.ROBOT, "AI 审查")
        ai_review_btn.clicked.connect(self._on_ai_review)
        ai_review_btn.setFixedHeight(36)
        header_layout.addWidget(ai_review_btn)

        execute_btn = PrimaryPushButton(FluentIcon.DELETE, "执行清理")
        execute_btn.clicked.connect(self._on_execute_cleanup)
        execute_btn.setFixedHeight(36)
        header_layout.addWidget(execute_btn)

    def _create_pipeline_area(self, parent_layout):
        """创建 AI Pipeline 区域"""
        pipeline_container = SimpleCardWidget()
        pipeline_layout = QVBoxLayout(pipeline_container)
        pipeline_layout.setContentsMargins(16, 12, 16, 12)
        pipeline_layout.setSpacing(8)

        # 标题
        title = StrongBodyLabel("AI 执行流程")
        title.setStyleSheet('font-size: 13px; color: #666;')
        pipeline_layout.addWidget(title)

        # Pipeline 组件
        self.pipeline = AgentPipelineWidget()
        pipeline_layout.addWidget(self.pipeline)

        # 通用进度条
        self.overall_progress = QLabel("总体进度: 0%")
        self.overall_progress.setStyleSheet('font-size: 11px; color: #999; text-align: right;')
        self.overall_progress.setAlignment(Qt.AlignRight)
        pipeline_layout.addWidget(self.overall_progress)

        parent_layout.addWidget(pipeline_container)

    def _create_tool_logger_area(self, parent_layout):
        """创建工具调用日志区域"""
        tool_container = SimpleCardWidget()
        tool_layout = QVBoxLayout(tool_container)
        tool_layout.setContentsMargins(16, 12, 16, 12)
        tool_layout.setSpacing(8)

        # 标题
        title = StrongBodyLabel("工具调用日志")
        title.setStyleSheet('font-size: 13px; color: #666;')
        tool_layout.addWidget(title)

        # 工具日志组件
        self.tool_logger = ToolLoggerWidget()
        tool_layout.addWidget(self.tool_logger)

        parent_layout.addWidget(tool_container)

    def _create_panel_header(self, title: str, icon: FluentIcon) -> QWidget:
        """创建面板头部"""
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet('''
            QWidget {
                background: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
            }
        ''')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(16, 16)
        icon_widget.setStyleSheet('color: #666;')
        header_layout.addWidget(icon_widget)

        label = StrongBodyLabel(title)
        label.setStyleSheet('font-size: 12px;')
        header_layout.addWidget(label)

        header_layout.addStretch()

        return header

    def _create_separator(self) -> QFrame:
        """创建分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet('background: #e0e0e0;')
        return line

    def _create_status_bar(self, parent_layout):
        """创建底部状态栏"""
        status_bar = QWidget()
        status_bar.setFixedHeight(36)
        status_bar.setStyleSheet('''
            QWidget {
                background: #f8f9fa;
                border-top: 1px solid #e0e0e0;
            }
        ''')

        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)

        self.status_text = BodyLabel("准备就绪")
        self.status_text.setStyleSheet('font-size: 11px; color: #666;')
        status_layout.addWidget(self.status_text)

        # 会话信息
        session_label = BodyLabel("会话: 未创建")
        session_label.setStyleSheet('font-size: 11px; color: #999;')
        status_layout.addWidget(session_label)

        status_layout.addStretch()

        # 执行时间
        self.time_label = BodyLabel("耗时: 00:00")
        self.time_label.setStyleSheet('font-size: 11px; color: #999;')
        status_layout.addWidget(self.time_label)

        parent_layout.addWidget(status_bar)

    def _connect_signals(self):
        """连接信号"""
        # Pipeline 信号
        self.pipeline.stage_changed.connect(self._on_pipeline_stage_changed)
        self.pipeline.progress_updated.connect(self._on_pipeline_progress_updated)
        self.pipeline.tool_called.connect(self._on_pipeline_tool_called)

        # Task Card 信号
        self.task_card.action_requested.connect(self._on_task_action)

        # Status Card 信号
        self.status_card.status_changed.connect(self._on_status_changed)

        # Thinking Stream 信号
        self.thinking_stream.tool_executed.connect(self._on_tool_executed)

    # ========== 信号处理 ==========

    def _on_pipeline_stage_changed(self, stage: str, status: str):
        """Pipeline 阶段变化"""
        logger.info(f"[AgentHub] 阶段变化: {stage} -> {status}")
        self._update_status_text(f"阶段: {AgentStage.get_name(stage)} - {status}")
        self._pipeline_stages_to_overall_progress()

    def _on_pipeline_progress_updated(self, stage: str, percent: int):
        """Pipeline 进度更新"""
        self.overall_progress.setText(f"总体进度: {self._pipeline_stages_to_overall_progress()}%")

    def _pipeline_stages_to_overall_progress(self) -> int:
        """将各阶段进度转换为总体进度"""
        # 计算总体进度（基于当前阶段）
        all_stages = AgentStage.get_all_stages()
        stage_indices = {s: i for i, s in enumerate(all_stages)}

        total_possible = 25 * len(all_stages)  # 每个阶段最高25分
        current_score = 0

        for stage, card in self.pipeline.stages.items():
            idx = stage_indices.get(stage, 0)
            stage_weight = 25

            if card.status == "completed":
                current_score += stage_weight
            elif card.status == "running":
                # 已完成之前的阶段数 * 25 + 当前阶段进度比例 * 25
                base_score = idx * 25
                current_score += base_score + (card.progress / 100) * stage_weight

        return int(current_score)

    def _on_pipeline_tool_called(self, stage: str, tool_name: str):
        """Pipeline 工具调用"""
        self.thinking_stream.add_tool_result(tool_name, "执行中...")
        self._update_stats({"tool_calls": 1})

    def _on_task_action(self, action: str):
        """任务操作"""
        if action == "start":
            self._start_task()
        elif action == "pause":
            self._pause_task()
        elif action == "stop":
            self._stop_task()
        elif action == "resume":
            self._resume_task()

    def _on_status_changed(self, status: str):
        """状态变化"""
        logger.info(f"[AgentHub] 状态变化: {status}")
        self.state = status

    def _on_tool_executed(self, tool_name: str, result: str):
        """工具执行完成"""
        self.tool_logger.add_entry("running", tool_name, "success")

    def _on_ai_review(self):
        """AI 审查操作"""
        InfoBar.info(
            title="AI 审查",
            content="启动 AI 审查流程...",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )
        # 设置 pipeline 到审查阶段
        self.pipeline.set_stage_status(AgentStage.REVIEW, "running")

    def _on_execute_cleanup(self):
        """执行清理操作"""
        InfoBar.info(
            title="执行清理",
            content="启动清理流程...",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )
        self.pipeline.set_stage_status(AgentStage.CLEANUP, "running")

    # ========== 公共方法 ==========

    def add_user_message(self, text: str):
        """添加用户消息到思考流"""
        self.thinking_stream.add_user_message(text)
        self._update_status_text(f"用户: {text}")

    def add_assistant_message(self, text: str):
        """添加助手消息到思考流"""
        self.thinking_stream.add_assistant_message(text)

    def add_tool_result(self, tool_name: str, result: str):
        """添加工具执行结果"""
        self.thinking_stream.add_tool_result(tool_name, result)
        self.tool_logger.add_entry(self.state, tool_name, "success")

    def add_thinking(self, thought: str):
        """添加 AI 思考"""
        self.thinking_stream.add_thinking(thought)

    def _update_status_text(self, text: str):
        """更新状态文本"""
        self.status_text.setText(text)

    def _update_stats(self, stats: dict):
        """更新统计信息"""
        if "scans" in stats:
            current = int(self.scans_card.findChild(StrongBodyLabel).text())
            self.scans_card.update_value(str(current + 1))

        if "ai_calls" in stats:
            current = int(self.ai_calls_card.findChild(StrongBodyLabel).text())
            self.ai_calls_card.update_value(str(current + 1))

        if "files" in stats:
            current = int(self.files_card.findChild(StrongBodyLabel).text())
            self.files_card.update_value(str(current + 1))

        if "space" in stats:
            self.space_card.update_value(self._format_size(stats["space"]))

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _start_task(self):
        """开始任务"""
        self.state = "running"
        self.status_card.set_status("running", stage="扫描中", progress=0, details="正在初始化...")
        self.task_card.set_task_status("running", 0, "正在执行...")
        self.pipeline.set_stage_status(AgentStage.SCAN, "running")

        # 模拟进度
        self._simulate_progress()

    def _pause_task(self):
        """暂停任务"""
        self.state = "paused"
        self.status_card.set_status("running", stage="已暂停", progress=self.pipeline.stages[AgentStage.SCAN].progress, details="任务已暂停")
        self.task_card.set_task_status("paused")

    def _resume_task(self):
        """恢复任务"""
        self.state = "running"
        self.status_card.set_status("running", stage="执行中", progress=self.pipeline.stages[AgentStage.SCAN].progress, details="继续执行...")
        self.task_card.set_task_status("running")

    def _stop_task(self):
        """停止任务"""
        self.state = "idle"
        self.status_card.set_status("idle")
        self.task_card.set_task_status("idle")
        self.pipeline.reset_all_stages()
        self._update_status_text("准备就绪")

    def _simulate_progress(self):
        """模拟任务进度（用于演示）"""
        if self.state != "running":
            return

        import random
        stage = random.choice(list(AgentStage.get_all_stages()))
        progress = random.randint(0, 100)

        self.pipeline.update_progress(stage, progress)

        # 继续模拟
        if self.state == "running":
            QTimer.singleShot(500, self._simulate_progress)

    def reset(self):
        """重置所有状态"""
        self.state = "idle"
        self.pipeline.reset_all_stages()
        self.thinking_stream.clear()
        self.tool_logger.clear()
        self.item_list.clear()
        self.task_card.set_task_status("idle")
        self.status_card.set_status("idle")
        self._update_status_text("准备就绪")


# 导出
__all__ = [
    "AgentHubPage"
]
