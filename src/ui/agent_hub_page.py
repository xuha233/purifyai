# -*- coding: utf-8 -*-
"""
智能体中心页面 - Agent Hub Page

智能体系统的核心控制中心，统一管理所有 AI 清理任务
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QSplitter,
    QStackedWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5 import QtWidgets

from qfluentwidgets import (
    StrongBodyLabel,
    SubtitleLabel,
    BodyLabel,
    SimpleCardWidget,
    PushButton,
    PrimaryPushButton,
    FluentIcon,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    ScrollArea,
)

from .agent_status_widgets import AgentStatusFrame, AgentStatsWidget
from .agent_pipeline_widget import AgentPipelineWidget
from .agent_thinking_stream import ThinkingStreamWidget
from .agent_control_panel import AgentControlPanel
from .cleanup_preview_card import CleanupPreviewDialog
from .cleanup_progress_widget import CleanupProgressWidget
from .agent_widgets import (
    TaskCard,
    AgentStatCard,
    ToolLoggerWidget,
    ItemListCard,
    ErrorDisplayWidget,
    ErrorDetailsDialog,
)
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
        self.state = "idle"
        self.timer = QTimer()
        self.last_error = None
        self._initialized = False
        self._deferred_widgets = {}

        # Cleanup 相关组件
        self.user_profile = None
        self.cleanup_plan = None
        self.cleanup_widget = None

        self._init_critical_ui()
        self._connect_critical_signals()
        QTimer.singleShot(0, self._init_deferred_ui)
        logger.info("[AgentHub] 智能体中心页面初始化完成")

    def _init_critical_ui(self):
        """初始化关键UI - 页面切换最关键的部分"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_header()
        main_layout.addWidget(self.header_widget)

        scroll_area = ScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            ScrollArea {
                border: none;
                background: transparent;
            }
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(12)

        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(12)

        self.status_card = AgentStatusFrame()
        self.status_card.setFixedHeight(120)
        top_row_layout.addWidget(self.status_card)

        self.task_panel = SimpleCardWidget()
        self.task_panel.setMinimumWidth(260)
        self.task_panel.setMaximumWidth(300)
        task_panel_layout = QVBoxLayout(self.task_panel)
        task_panel_layout.setContentsMargins(12, 12, 12, 12)

        task_title = SubtitleLabel("任务控制")
        task_title.setStyleSheet("font-size: 14px;")
        task_panel_layout.addWidget(task_title)

        self.task_card = TaskCard()
        self.task_card.setMinimumHeight(100)
        task_panel_layout.addWidget(self.task_card)

        top_row_layout.addWidget(self.task_panel)

        self.stats_panel = SimpleCardWidget()
        self.stats_panel.setMinimumWidth(240)
        self.stats_panel.setMaximumWidth(280)
        stats_layout = QVBoxLayout(self.stats_panel)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(8)

        stats_title = SubtitleLabel("统计概览")
        stats_title.setStyleSheet("font-size: 14px;")
        stats_layout.addWidget(stats_title)

        stats_grid = QVBoxLayout()

        self.scans_card = AgentStatCard(
            "0", "扫描次数", FluentIcon.HISTORY, AgentTheme.SCAN_COLOR
        )
        stats_grid.addWidget(self.scans_card)

        self.ai_calls_card = AgentStatCard(
            "0", "AI 调用", FluentIcon.ROBOT, AgentTheme.REPORT_COLOR
        )
        stats_grid.addWidget(self.ai_calls_card)

        self.files_card = AgentStatCard(
            "0", "清理文件", FluentIcon.DELETE, AgentTheme.CLEANUP_COLOR
        )
        stats_grid.addWidget(self.files_card)

        self.space_card = AgentStatCard(
            "0 MB", "释放空间", FluentIcon.SAVE, AgentTheme.PRIMARY
        )
        stats_grid.addWidget(self.space_card)

        stats_layout.addLayout(stats_grid)

        top_row_layout.addWidget(self.stats_panel)
        top_row_layout.addStretch()

        content_layout.addLayout(top_row_layout)

        pipeline_placeholder = QWidget()
        pipeline_layout = QVBoxLayout(pipeline_placeholder)
        self._deferred_widgets["pipeline_container"] = pipeline_placeholder
        content_layout.addWidget(pipeline_placeholder)

        content_layout.addWidget(self._create_separator())

        split_layout = QHBoxLayout()
        split_layout.setSpacing(12)

        left_placeholder = QWidget()
        left_placeholder.setMinimumWidth(350)
        left_placeholder.setMaximumWidth(450)
        self._deferred_widgets["left_panel"] = left_placeholder
        split_layout.addWidget(left_placeholder)

        right_placeholder = QWidget()
        self._deferred_widgets["right_panel"] = right_placeholder
        split_layout.addWidget(right_placeholder, stretch=1)

        content_layout.addLayout(split_layout, stretch=1)

        tool_placeholder = QWidget()
        tool_layout = QVBoxLayout(tool_placeholder)
        self._deferred_widgets["tool_container"] = tool_placeholder
        content_layout.addWidget(tool_placeholder)

        self._create_status_bar(content_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, stretch=1)

    def _init_deferred_ui(self):
        """延迟初始化次要UI组件"""
        if self._initialized:
            return

        self._create_pipeline_area()
        self._create_left_panel()
        self._create_right_panel()
        self._create_tool_logger_area()
        self._create_cleanup_progress_area()
        self._connect_deferred_signals()
        self._initialized = True

    def _create_pipeline_area(self):
        """创建 AI Pipeline 区域"""
        pipeline_container = SimpleCardWidget()
        pipeline_layout = QVBoxLayout(pipeline_container)
        pipeline_layout.setContentsMargins(16, 12, 16, 12)
        pipeline_layout.setSpacing(8)

        title = StrongBodyLabel("AI 执行流程")
        title.setStyleSheet("font-size: 13px; color: #666;")
        pipeline_layout.addWidget(title)

        self.pipeline = AgentPipelineWidget()
        pipeline_layout.addWidget(self.pipeline)

        self.overall_progress = QLabel("总体进度: 0%")
        self.overall_progress.setStyleSheet(
            "font-size: 11px; color: #999; text-align: right;"
        )
        self.overall_progress.setAlignment(Qt.AlignRight)
        pipeline_layout.addWidget(self.overall_progress)

        old_container = self._deferred_widgets["pipeline_container"]
        old_layout = old_container.layout()
        old_layout.addWidget(pipeline_container)

    def _create_left_panel(self):
        """创建左侧面板"""
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

        old_panel = self._deferred_widgets["left_panel"]
        old_layout = old_panel.parent().layout()
        idx = old_layout.indexOf(old_panel)
        old_layout.removeWidget(old_panel)
        old_panel.deleteLater()
        old_layout.insertWidget(idx, left_panel)

    def _create_right_panel(self):
        """创建右侧面板"""
        right_panel = SimpleCardWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_header = self._create_panel_header("清理项目", FluentIcon.DOCUMENT)
        right_layout.addWidget(right_header)

        self.item_list = ItemListCard()
        right_layout.addWidget(self.item_list)

        old_panel = self._deferred_widgets["right_panel"]
        old_layout = old_panel.parent().layout()
        idx = old_layout.indexOf(old_panel)
        old_layout.removeWidget(old_panel)
        old_panel.deleteLater()
        old_layout.insertWidget(idx, right_panel)

    def _create_tool_logger_area(self):
        """创建工具调用日志区域"""
        tool_container = SimpleCardWidget()
        tool_layout = QVBoxLayout(tool_container)
        tool_layout.setContentsMargins(16, 12, 16, 12)
        tool_layout.setSpacing(8)

        title = StrongBodyLabel("工具调用日志")
        title.setStyleSheet("font-size: 13px; color: #666;")
        tool_layout.addWidget(title)

        self.tool_logger = ToolLoggerWidget()
        tool_layout.addWidget(self.tool_logger)

        old_container = self._deferred_widgets["tool_container"]
        old_layout = old_container.layout()
        old_layout.addWidget(tool_container)

    def _create_cleanup_progress_area(self):
        """创建清理进度区域"""
        self.cleanup_widget = CleanupProgressWidget()
        self.cleanup_widget.setVisible(False)

        # 将清理进度组件添加到任务面板下方
        task_panel_layout = self.task_panel.layout()
        task_panel_layout.addWidget(self.cleanup_widget)

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
        icon_widget.setStyleSheet("color: #0078D4;")
        header_layout.addWidget(icon_widget)

        title = StrongBodyLabel("智能体中心")
        title.setStyleSheet("font-size: 20px; color: #2c2c2c;")
        header_layout.addWidget(title)

        # AI 状态指示
        ai_status_icon = IconWidget(FluentIcon.ACCEPT)
        ai_status_icon.setFixedSize(16, 16)
        ai_status_icon.setStyleSheet("color: #52C41A;")
        header_layout.addWidget(ai_status_icon)

        ai_status = BodyLabel("AI 系统: 就绪")
        ai_status.setStyleSheet("color: #52C41A; font-size: 13px;")
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

        self.one_click_cleanup_btn = PrimaryPushButton(FluentIcon.SEND, "一键清理")
        self.one_click_cleanup_btn.clicked.connect(self._on_one_click_cleanup)
        self.one_click_cleanup_btn.setFixedHeight(36)
        header_layout.addWidget(self.one_click_cleanup_btn)

        execute_btn = PrimaryPushButton(FluentIcon.DELETE, "执行清理")
        execute_btn.clicked.connect(self._on_execute_cleanup)
        execute_btn.setFixedHeight(36)
        header_layout.addWidget(execute_btn)

    def _connect_critical_signals(self):
        """连接关键信号（初始化时立即连接）"""
        self.task_card.action_requested.connect(self._on_task_action)
        self.status_card.status_changed.connect(self._on_status_changed)

    def _connect_deferred_signals(self):
        """连接延迟的信号（在延迟初始化后调用）"""
        self.pipeline.stage_changed.connect(self._on_pipeline_stage_changed)
        self.pipeline.progress_updated.connect(self._on_pipeline_progress_updated)
        self.pipeline.tool_called.connect(self._on_pipeline_tool_called)
        self.thinking_stream.tool_executed.connect(self._on_tool_executed)

    def _create_panel_header(self, title: str, icon: FluentIcon) -> QWidget:
        """创建面板头部"""
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("""
            QWidget {
                background: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(16, 16)
        icon_widget.setStyleSheet("color: #666;")
        header_layout.addWidget(icon_widget)

        label = StrongBodyLabel(title)
        label.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(label)

        header_layout.addStretch()

        return header

    def _create_separator(self) -> QFrame:
        """创建分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background: #e0e0e0;")
        return line

    def _create_status_bar(self, parent_layout):
        """创建底部状态栏"""
        status_bar = QWidget()
        status_bar.setFixedHeight(36)
        status_bar.setStyleSheet("""
            QWidget {
                background: #f8f9fa;
                border-top: 1px solid #e0e0e0;
            }
        """)

        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)

        self.status_text = BodyLabel("准备就绪")
        self.status_text.setStyleSheet("font-size: 11px; color: #666;")
        status_layout.addWidget(self.status_text)

        # 会话信息
        session_label = BodyLabel("会话: 未创建")
        session_label.setStyleSheet("font-size: 11px; color: #999;")
        status_layout.addWidget(session_label)

        status_layout.addStretch()

        # 执行时间
        self.time_label = BodyLabel("耗时: 00:00")
        self.time_label.setStyleSheet("font-size: 11px; color: #999;")
        status_layout.addWidget(self.time_label)

        parent_layout.addWidget(status_bar)

    # ========== 错误处理 ==========

    def show_error(
        self,
        title: str,
        message: str,
        error_code: str = "",
        suggestions: list = None,
        recoverable: bool = True,
    ):
        """显示错误信息

        Args:
            title: 错误标题
            message: 错误消息
            error_code: 错误代码
            suggestions: 建议操作列表
            recoverable: 是否可恢复
        """
        # 保存最后错误
        self.last_error = {
            "title": title,
            "message": message,
            "error_code": error_code,
            "suggestions": suggestions or [],
            "recoverable": recoverable,
        }

        # 更新任务卡片状态
        self.task_card.set_task_status("error", 0, f"错误: {title}")

        # 更新状态卡片
        self.status_card.update_status(AgentStatus.ERROR, title)

        logger.warning(f"[AgentHub] 显示错误: [{error_code}] {title} - {message}")

    def show_error_from_exception(self, exc: Exception, context: dict = None):
        """从异常对象显示错误

        Args:
            exc: 异常对象
            context: 上下文信息
        """
        try:
            # 尝试导入异常处理模块
            from agent.exceptions import unwrap_agent_exception, format_error_for_user

            agent_exc = unwrap_agent_exception(exc)

            if agent_exc:
                title = agent_exc.code.name.replace("_", " ")
                message = agent_exc.message
                error_code = agent_exc.code.value
                suggestions = agent_exc.context.additional_data.get("suggestions", [])
                recoverable = agent_exc.recoverable

                self.show_error(title, message, error_code, suggestions, recoverable)
            else:
                self.show_error(
                    "发生错误", str(exc), "E0000", ["请检查日志获取详细信息"], False
                )

        except ImportError:
            # 如果异常模块不可用，使用通用错误处理
            self.show_error(
                "发生错误", str(exc), "E0000", ["请检查日志获取详细信息"], False
            )

    def clear_error(self):
        """清除错误状态"""
        self.last_error = None
        self.task_card.set_task_status("idle", 0, "准备就绪")
        self.status_card.update_status(AgentStatus.READY, "就绪")

    def _create_error_display_area(self, parent_layout):
        """创建错误显示区域

        Args:
            parent_layout: 父布局
        """
        self.error_display = ErrorDisplayWidget()
        self.error_display.setFixedHeight(0)  # 初始隐藏
        self.error_display.setStyleSheet(
            self.error_display.styleSheet()
            + """
            ErrorDisplayWidget {
                margin: 8px 0;
            }
        """
        )
        parent_layout.addWidget(self.error_display)

        # 连接信号
        self.error_display.retry_requested.connect(self._on_retry_error)
        self.error_display.details_requested.connect(self._on_show_error_details)
        self.error_display.dismissed.connect(self._on_dismiss_error)

    def _on_retry_error(self):
        """重试错误操作"""
        if self.last_error and self.last_error.get("recoverable", False):
            logger.info("[AgentHub] 用户请求重试错误操作")
            # 触发任务重试
            self.task_card.action_requested.emit("start")

    def _on_show_error_details(self):
        """显示错误详情"""
        if self.last_error:
            self._show_error_details_dialog(self.last_error)

    def _on_dismiss_error(self):
        """关闭错误显示"""
        self.error_display.setFixedHeight(0)

    def _show_error_details_dialog(self, error_info: dict):
        """显示错误详情对话框

        Args:
            error_info: 错误信息字典
        """
        if not hasattr(self, "_error_details_dialog"):
            self._error_details_dialog = ErrorDetailsDialog(self)

        dialog = self._error_details_dialog
        dialog.set_error_details(
            error_code=error_info.get("error_code", "E0000"),
            error_type="AgentException",
            error_message=error_info.get("message", "未知错误"),
            stack_trace="",  # 可以从异常中获取
            suggestions=error_info.get("suggestions", []),
        )
        dialog.show()

    # ========== 信号处理 ==========

    def _on_pipeline_stage_changed(self, stage: str, status: str):
        """Pipeline 阶段变化"""
        logger.info(f"[AgentHub] 阶段变化: {stage} -> {status}")
        self._update_status_text(f"阶段: {AgentStage.get_name(stage)} - {status}")
        self._pipeline_stages_to_overall_progress()

    def _on_pipeline_progress_updated(self, stage: str, percent: int):
        """Pipeline 进度更新"""
        self.overall_progress.setText(
            f"总体进度: {self._pipeline_stages_to_overall_progress()}%"
        )

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
            duration=2000,
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
            duration=2000,
        )
        self.pipeline.set_stage_status(AgentStage.CLEANUP, "running")

    def _on_one_click_cleanup(self):
        """一键清理操作"""
        InfoBar.info(
            title="一键清理",
            content="正在生成智能清理计划...",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000,
        )

        try:
            from ..agent.smart_recommender import SmartRecommender, CleanupMode

            # 构建用户画像
            recommender = SmartRecommender()
            if self.user_profile is None:
                self.user_profile = recommender.build_user_profile()

            # 生成清理计划
            self.cleanup_plan = recommender.recommend(
                self.user_profile, mode=CleanupMode.BALANCED.value
            )

            # 显示预览对话框
            preview_dialog = CleanupPreviewDialog(self.cleanup_plan, self)
            if (
                preview_dialog.exec_() == QtWidgets.QDialog.Accepted
                and preview_dialog.is_confirmed()
            ):
                # 用户确认，开始清理
                self._start_one_click_cleanup()

        except Exception as e:
            logger.error(f"[AgentHub] 一键清理失败: {e}")
            InfoBar.error(
                title="一键清理失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _start_one_click_cleanup(self):
        """开始执行一键清理"""
        if not self.cleanup_plan or not self.user_profile:
            logger.error("[AgentHub] 清理计划或用户画像不存在")
            return

        # 显示清理进度组件
        if self.cleanup_widget:
            self.cleanup_widget.setVisible(True)
            self.cleanup_widget.start_cleanup(self.user_profile, self.cleanup_plan.mode)

            # 连接清理完成信号
            if self.cleanup_widget.cleanup_thread:
                self.cleanup_widget.cleanup_thread.cleanup_completed.connect(
                    self._on_one_click_cleanup_completed
                )
                self.cleanup_widget.cleanup_thread.cleanup_failed.connect(
                    self._on_one_click_cleanup_failed
                )

        # 禁用一键清理按钮
        self.one_click_cleanup_btn.setEnabled(False)

        InfoBar.success(
            title="开始清理",
            content="智能清理已启动，请查看进度...",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

        # 更新 pipeline 状态
        self.pipeline.set_stage_status(AgentStage.CLEANUP, "running")

    def _on_one_click_cleanup_completed(self, report):
        """一键清理完成"""
        InfoBar.success(
            title="清理完成",
            content=f"成功清理 {report.success_items} 个文件，释放 {self._format_size(report.freed_size)}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

        # 更新统计
        self._update_stats({"files": report.success_items, "space": report.freed_size})

        # 重新启用按钮
        self.one_click_cleanup_btn.setEnabled(True)

        logger.info(f"[AgentHub] 一键清理完成: {report.report_id}")

    def _on_one_click_cleanup_failed(self, error_message):
        """一键清理失败"""
        InfoBar.error(
            title="清理失败",
            content=error_message,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000,
        )

        # 重新启用按钮
        self.one_click_cleanup_btn.setEnabled(True)

        logger.error(f"[AgentHub] 一键清理失败: {error_message}")

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
            val = self.scans_card.findChild(StrongBodyLabel)
            if val:
                try:
                    current = int(val.text())
                    self.scans_card.update_value(str(current + 1))
                except ValueError:
                    self.scans_card.update_value("1")

        if "ai_calls" in stats:
            val = self.ai_calls_card.findChild(StrongBodyLabel)
            if val:
                text = val.text()
                try:
                    current = int(text)
                    self.ai_calls_card.update_value(str(current + 1))
                except ValueError:
                    self.ai_calls_card.update_value("1")

        if "files" in stats:
            val = self.files_card.findChild(StrongBodyLabel)
            if val:
                try:
                    current = int(val.text())
                    self.files_card.update_value(str(current + 1))
                except ValueError:
                    self.files_card.update_value("1")

        if "space" in stats:
            self.space_card.update_value(self._format_size(stats["space"]))

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _start_task(self):
        """开始任务"""
        self.state = "running"
        self.status_card.set_status(
            "running", stage="扫描中", progress=0, details="正在初始化..."
        )
        self.task_card.set_task_status("running", 0, "正在执行...")
        if hasattr(self, "pipeline"):
            self.pipeline.set_stage_status(AgentStage.SCAN, "running")
        self._simulate_progress()

    def _pause_task(self):
        """暂停任务"""
        self.state = "paused"
        self.status_card.set_status(
            "running",
            stage="已暂停",
            progress=self.pipeline.stages[AgentStage.SCAN].progress,
            details="任务已暂停",
        )
        self.task_card.set_task_status("paused")

    def _resume_task(self):
        """恢复任务"""
        self.state = "running"
        self.status_card.set_status(
            "running",
            stage="执行中",
            progress=self.pipeline.stages[AgentStage.SCAN].progress,
            details="继续执行...",
        )
        self.task_card.set_task_status("running")

    def _stop_task(self):
        """停止任务"""
        self.state = "idle"
        self.status_card.set_status("idle")
        self.task_card.set_task_status("idle")
        if hasattr(self, "pipeline"):
            self.pipeline.reset_all_stages()
        self._update_status_text("准备就绪")

    def _simulate_progress(self):
        """模拟任务进度（用于演示）"""
        if self.state != "running":
            return

        import random

        stage = random.choice(list(AgentStage.get_all_stages()))
        progress = random.randint(0, 100)

        if hasattr(self, "pipeline"):
            self.pipeline.update_progress(stage, progress)

        if self.state == "running":
            QTimer.singleShot(500, self._simulate_progress)

    def reset(self):
        """重置所有状态"""
        self.state = "idle"
        if hasattr(self, "pipeline"):
            self.pipeline.reset_all_stages()
        if hasattr(self, "thinking_stream"):
            self.thinking_stream.clear()
        if hasattr(self, "tool_logger"):
            self.tool_logger.clear()
        if hasattr(self, "item_list"):
            self.item_list.clear()
        self.task_card.set_task_status("idle")
        self.status_card.set_status("idle")
        self._update_status_text("准备就绪")


# 导出
__all__ = ["AgentHubPage"]
