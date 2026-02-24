# -*- coding: utf-8 -*-
"""
智能体中心页面 - Agent Hub Page (v2.0 - Tab Architecture)

智能体系统的核心控制中心，统一管理所有 AI 清理任务

采用 4 选项卡架构：
1. 概览 - 快速状态 + 主操作入口
2. 清理 - 详细清理操作
3. 智能体 - 智能体控制和监控
4. 日志与设置 - 高级功能和日志
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
    QRadioButton,
    QButtonGroup,
    QComboBox,
    QSpinBox,
    QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt5 import QtWidgets

from qfluentwidgets import (
    StrongBodyLabel,
    SubtitleLabel,
    BodyLabel,
    CaptionLabel,
    SimpleCardWidget,
    CardWidget,
    PushButton,
    PrimaryPushButton,
    FluentIcon,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    ScrollArea,
    ProgressBar,
    ToolButton,
    HeaderCardWidget,
    SegmentedWidget,
    ToolTipFilter,
    ToolTipPosition,
    RoundMenu,
    Action,
    MenuAction,
    SubtitleLabel,
    CaptionLabel,
    StrongBodyLabel,
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
)
from .agent_theme import AgentTheme, AgentStage, AgentStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class OverviewTab(QWidget):
    """概览选项卡 - Tab 1

    快速状态显示 + 主操作入口
    """

    cleanup_requested = pyqtSignal(str)  # "one_click" or "incremental"
    scan_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 顶部区域：智能体状态 + AI 健康评分
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        # 智能体状态卡片
        self.status_card = AgentStatusFrame()
        self.status_card.setMinimumWidth(300)
        self.status_card.setMaximumWidth(350)
        top_layout.addWidget(self.status_card)

        # AI 健康评分卡片 (P1, 可选功能)
        health_card = self._create_health_card()
        health_card.setMinimumWidth(200)
        top_layout.addWidget(health_card)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 主操作区域：一键清理 + 增量清理
        action_card = CardWidget()
        action_card.setFixedHeight(200)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(24, 24, 24, 24)
        action_layout.setSpacing(16)

        action_title = SubtitleLabel("快速清理")
        action_title.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(action_title, alignment=Qt.AlignCenter)

        # 主操作按钮容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(12)

        # 一键清理按钮（主入口，更大更显眼）
        self.one_click_btn = PrimaryPushButton()
        self.one_click_btn.setFixedHeight(56)
        self.one_click_btn.setMinimumWidth(240)
        one_icon = IconWidget(FluentIcon.SEND)
        one_icon.setFixedSize(24, 24)
        self.one_click_btn.setIcon(one_icon)
        self.one_click_btn.setText("一键清理")
        self.one_click_btn.clicked.connect(
            lambda: self.cleanup_requested.emit("one_click")
        )

        # 样式：更大更显眼
        self.one_click_btn.setStyleSheet("""
            PrimaryPushButton {
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
        """)

        button_layout.addWidget(self.one_click_btn, stretch=1)

        # 增量清理按钮（次要入口）
        self.incremental_btn = PushButton()
        self.incremental_btn.setFixedHeight(56)
        self.incremental_btn.setMinimumWidth(200)
        incremental_icon = IconWidget(FluentIcon.ADD)
        incremental_icon.setFixedSize(20, 20)
        self.incremental_btn.setIcon(incremental_icon)
        self.incremental_btn.setText("增量清理")
        self.incremental_btn.clicked.connect(
            lambda: self.cleanup_requested.emit("incremental")
        )
        button_layout.addWidget(self.incremental_btn, stretch=0)

        action_layout.addWidget(button_container, alignment=Qt.AlignCenter)

        # 说明文本
        hint_label = CaptionLabel("点击一键清理开始智能扫描，或使用增量清理仅处理新增文件")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #999; margin-top: 8px;")
        action_layout.addWidget(hint_label)

        layout.addWidget(action_card, alignment=Qt.AlignCenter)

        # 快速统计区域
        stats_card = CardWidget()
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(8)

        stats_title = StrongBodyLabel("快速统计")
        stats_title.setStyleSheet("font-size: 14px; margin-bottom: 8px;")
        stats_layout.addWidget(stats_title)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(12)

        # 今日清理次数
        self.today_cleanups = AgentStatCard(
            "0", "今日清理", FluentIcon.UPDATE, AgentTheme.CLEANUP_COLOR
        )
        grid_layout.addWidget(self.today_cleanups, 0, 0)

        # 总释放空间
        self.total_freed = AgentStatCard(
            "0 MB", "总释放空间", FluentIcon.SAVE, AgentTheme.PRIMARY
        )
        grid_layout.addWidget(self.total_freed, 0, 1)

        # 上次清理时间
        self.last_cleanup = AgentStatCard(
            "3 天前", "上次清理", FluentIcon.HISTORY, AgentTheme.REPORT_COLOR
        )
        grid_layout.addWidget(self.last_cleanup, 0, 2)

        # 系统健康评分
        self.system_health = AgentStatCard(
            "85/100", "健康评分", FluentIcon.HEALTH, "#52C41A"
        )
        grid_layout.addWidget(self.system_health, 1, 0)

        # 发现可清理
        self.found_cleanup = AgentStatCard(
            "~2.5 GB", "建议清理", FluentIcon.FOLDER, AgentTheme.SCAN_COLOR
        )
        grid_layout.addWidget(self.found_cleanup, 1, 1)

        # 风险程度
        self.risk_level = AgentStatCard(
            "低 🟢", "风险程度", "#52C41A", "#52C41A"
        )
        grid_layout.addWidget(self.risk_level, 1, 2)

        stats_layout.addLayout(grid_layout)
        layout.addWidget(stats_card)

        layout.addStretch()

    def _create_health_card(self) -> CardWidget:
        """创建 AI 健康评分卡片"""
        card = CardWidget()
        card.setMinimumHeight(140)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = StrongBodyLabel("AI 健康评分")
        title.setStyleSheet("font-size: 13px; color: #666;")
        layout.addWidget(title)

        score_layout = QHBoxLayout()
        score_layout.setSpacing(8)

        score_label = QLabel("85")
        score_label.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: #52C41A;
        """)
        score_layout.addWidget(score_label)

        score_container = QVBoxLayout()
        score_container.setSpacing(2)

        total_label = CaptionLabel("/100")
        total_label.setStyleSheet("color: #999;")
        score_container.addWidget(total_label)

        suggest_label = CaptionLabel("建议清理: 2.5 GB")
        suggest_label.setStyleSheet("color: #666;")
        score_container.addWidget(suggest_label)

        score_layout.addLayout(score_container)
        score_layout.addStretch()

        layout.addLayout(score_layout)

        # 进度条
        health_bar = ProgressBar()
        health_bar.setValue(85)
        health_bar.setStyleSheet("""
            ProgressBar::groove:Horizontal {
                height: 6px;
                background: #F0F0F0;
                border-radius: 3px;
            }
            ProgressBar::chunk:Horizontal {
                background: #52C41A;
                border-radius: 3px;
            }
        """)
        layout.addWidget(health_bar)

        return card


class CleanupTab(QWidget):
    """清理选项卡 - Tab 2

    详细清理操作
    """

    cleanup_started = pyqtSignal(dict)
    preview_shown = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_profile = None
        self.cleanup_plan = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 清理模式选择区域
        mode_card = CardWidget()
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(20, 16, 20, 16)
        mode_layout.setSpacing(12)

        mode_title = StrongBodyLabel("清理模式")
        mode_title.setStyleSheet("font-size: 15px;")
        mode_layout.addWidget(mode_title)

        mode_group = QWidget()
        mode_group_layout = QHBoxLayout(mode_group)
        mode_group_layout.setSpacing(16)

        # 模式选择按钮
        self.mode_buttons = {}
        modes = [
            ("one_click", "一键清理", "智能推荐清理项", FluentIcon.SEND),
            ("incremental", "增量清理", "仅清理新增文件", FluentIcon.ADD),
            ("advanced", "高级模式", "自定义清理选项", FluentIcon.SETTING),
        ]

        button_group = QButtonGroup(self)

        for i, (mode_id, name, desc, icon) in enumerate(modes):
            btn = QRadioButton(name)
            btn.setStyleSheet("""
                QRadioButton {
                    font-size: 14px;
                    padding: 8px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)
            if i == 0:
                btn.setChecked(True)

            btn_layout = QVBoxLayout()
            btn_layout.addWidget(btn)

            desc_label = CaptionLabel(desc)
            desc_label.setStyleSheet("color: #999; margin-left: 32px;")
            btn_layout.addWidget(desc_label)

            mode_group_layout.addLayout(btn_layout)
            button_group.addButton(btn, i)
            self.mode_buttons[mode_id] = (btn, desc_label)

        mode_layout.addWidget(mode_group)
        layout.addWidget(mode_card)

        # 清理预览区域
        preview_card = CardWidget()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 12, 16, 12)
        preview_layout.setSpacing(12)

        preview_title = StrongBodyLabel("清理预览")
        preview_title.setStyleSheet("font-size: 15px;")
        preview_layout.addWidget(preview_title)

        # 预览信息
        preview_info = SimpleCardWidget()
        info_layout = QVBoxLayout(preview_info)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(16, 16, 16, 16)

        self.scan_count_label = StrongBodyLabel("扫描项目: 15,234 个")
        self.cleanup_count_label = BodyLabel("建议清理: 3,456 个")
        self.space_label = BodyLabel("预计释放空间: 2.5 GB")

        for label in [self.scan_count_label, self.cleanup_count_label, self.space_label]:
            label.setStyleSheet("font-size: 13px; margin: 2px 0;")
            info_layout.addWidget(label)

        self.risk_label = BodyLabel("风险程度: 低 🟢")
        self.risk_label.setStyleSheet("font-size: 13px; color: #52C41A;")
        info_layout.addWidget(self.risk_label)

        preview_layout.addWidget(preview_info)

        # 操作按钮
        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        button_row.addStretch()

        view_details_btn = PushButton("查看详情")
        view_details_btn.clicked.connect(self._show_preview_dialog)
        view_details_btn.setMinimumWidth(100)
        button_row.addWidget(view_details_btn)

        self.start_cleanup_btn = PrimaryPushButton("开始清理")
        self.start_cleanup_btn.clicked.connect(self._start_cleanup)
        self.start_cleanup_btn.setMinimumWidth(120)
        button_row.addWidget(self.start_cleanup_btn)

        preview_layout.addLayout(button_row)
        layout.addWidget(preview_card)

        # 清理进度区域
        self.progress_widget = CleanupProgressWidget()
        self.progress_widget.setVisible(False)
        layout.addWidget(self.progress_widget)

        layout.addStretch()

    def _show_preview_dialog(self):
        """显示清理预览对话框"""
        try:
            from ..agent.smart_recommender import SmartRecommender, CleanupMode

            recommender = SmartRecommender()
            if self.user_profile is None:
                self.user_profile = recommender.build_user_profile()

            # 根据当前选择的模式生成清理计划
            current_mode = self._get_current_mode()
            if current_mode == "incremental":
                self.cleanup_plan = recommender.recommend_incremental(
                    mode=CleanupMode.BALANCED.value
                )
            else:
                self.cleanup_plan = recommender.recommend(
                    self.user_profile, mode=CleanupMode.BALANCED.value
                )

            # 更新预览信息
            self._update_preview_info()

            # 显示对话框
            preview_dialog = CleanupPreviewDialog(self.cleanup_plan, self)
            if preview_dialog.exec_() == QtWidgets.QDialog.Accepted:
                self.preview_shown.emit()

        except Exception as e:
            logger.error(f"[CleanupTab] 显示预览失败: {e}")
            InfoBar.error(
                title="预览失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _start_cleanup(self):
        """开始清理"""
        if not self.cleanup_plan:
            self._show_preview_dialog()

        if self.cleanup_plan:
            self.cleanup_widget = self.progress_widget
            self.cleanup_widget.setVisible(True)
            self.cleanup_widget.start_cleanup(self.user_profile, self.cleanup_plan.mode)
            self.cleanup_started.emit({"mode": self.cleanup_plan.mode})

    def _get_current_mode(self) -> str:
        """获取当前选择的模式"""
        for mode_id, (btn, _) in self.mode_buttons.items():
            if btn.isChecked():
                return mode_id
        return "one_click"

    def _update_preview_info(self):
        """更新预览信息"""
        if self.cleanup_plan:
            self.scan_count_label.setText(f"扫描项目: {getattr(self.cleanup_plan, 'scan_count', 15_234)} 个")
            self.cleanup_count_label.setText(f"建议清理: {len(self.cleanup_plan.items)} 个")
            space = sum(item.size for item in self.cleanup_plan.items)
            self.space_label.setText(f"预计释放空间: {space / (1024 ** 3):.2f} GB")


class AgentsTab(QWidget):
    """智能体选项卡 - Tab 3

    智能体控制和监控
    """

    task_action_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 智能体控制面板
        self.control_panel = AgentControlPanel()
        self.control_panel.action_requested.connect(self.task_action_requested.emit)
        layout.addWidget(self.control_panel)

        # AI Pipeline
        pipeline_card = CardWidget()
        pipeline_layout = QVBoxLayout(pipeline_card)
        pipeline_layout.setContentsMargins(16, 12, 16, 12)
        pipeline_layout.setSpacing(8)

        pipeline_title = StrongBodyLabel("AI 执行流程")
        pipeline_title.setStyleSheet("font-size: 15px;")
        pipeline_layout.addWidget(pipeline_title)

        self.pipeline = AgentPipelineWidget()
        pipeline_layout.addWidget(self.pipeline)

        self.overall_progress = BodyLabel("总体进度: 0%")
        self.overall_progress.setStyleSheet("font-size: 13px; color: #999;")
        pipeline_layout.addWidget(self.overall_progress)

        layout.addWidget(pipeline_card)

        # Thinking Stream
        thinking_card = CardWidget()
        thinking_layout = QVBoxLayout(thinking_card)
        thinking_layout.setContentsMargins(16, 12, 16, 12)
        thinking_layout.setSpacing(8)

        thinking_title = StrongBodyLabel("AI 思考流")
        thinking_title.setStyleSheet("font-size: 15px;")
        thinking_layout.addWidget(thinking_title)

        self.thinking_stream = ThinkingStreamWidget()
        thinking_layout.addWidget(self.thinking_stream)

        layout.addWidget(thinking_card)

        # 性能监控
        perf_card = CardWidget()
        perf_layout = QVBoxLayout(perf_card)
        perf_layout.setContentsMargins(16, 12, 16, 12)
        perf_layout.setSpacing(12)

        perf_title = StrongBodyLabel("性能监控")
        perf_title.setStyleSheet("font-size: 15px;")
        perf_layout.addWidget(perf_title)

        perf_info = QHBoxLayout()
        perf_info.setSpacing(24)

        self.cpu_label = BodyLabel("CPU 使用: 15%")
        self.memory_label = BodyLabel("内存使用: 256 MB")
        self.network_label = BodyLabel("网络请求: 12")

        for label in [self.cpu_label, self.memory_label, self.network_label]:
            label.setStyleSheet("font-size: 13px;")
            perf_info.addWidget(label)

        perf_info.addStretch()
        perf_layout.addLayout(perf_info)

        # 性能图表占位符
        perf_placeholder = SimpleCardWidget()
        perf_placeholder.setMinimumHeight(100)
        perf_layout.addWidget(perf_placeholder)

        layout.addWidget(perf_card)

        layout.addStretch()


class LogsSettingsTab(QWidget):
    """日志与设置选项卡 - Tab 4

    高级功能和日志
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(16)

        # 清理偏好设置
        preference_card = CardWidget()
        pref_layout = QVBoxLayout(preference_card)
        pref_layout.setContentsMargins(20, 16, 20, 16)
        pref_layout.setSpacing(12)

        pref_title = StrongBodyLabel("清理偏好")
        pref_title.setStyleSheet("font-size: 15px;")
        pref_layout.addWidget(pref_title)

        pref_group = QHBoxLayout()
        pref_group.setSpacing(16)

        pref_button_group = QButtonGroup(self)
        preference_modes = [
            ("conservative", "保守模式", "仅清理明确可删除的文件"),
            ("balanced", "平衡模式", "智能推荐清理项"),
            ("aggressive", "激进模式", "最大化清理效果"),
        ]

        self.preference_buttons = {}
        for i, (mode_id, name, desc) in enumerate(preference_modes):
            btn = QRadioButton(name)
            if i == 1:
                btn.setChecked(True)
            pref_group.addWidget(btn)

            desc_label = CaptionLabel(desc)
            desc_label.setStyleSheet("color: #999;")
            pref_group.addWidget(desc_label)

            pref_button_group.addButton(btn, i)
            self.preference_buttons[mode_id] = btn

        pref_group.addStretch()
        pref_layout.addLayout(pref_group)

        content_layout.addWidget(preference_card)

        # 备份设置
        backup_card = CardWidget()
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.setContentsMargins(20, 16, 20, 16)
        backup_layout.setSpacing(12)

        backup_title = StrongBodyLabel("备份设置")
        backup_title.setStyleSheet("font-size: 15px;")
        backup_layout.addWidget(backup_title)

        backup_options = QHBoxLayout()
        backup_options.setSpacing(24)

        self.enable_backup = QCheckBox("启用自动备份")
        self.enable_backup.setChecked(True)
        backup_options.addWidget(self.enable_backup)

        backup_days_layout = QHBoxLayout()
        backup_days_label = BodyLabel("保留天数:")
        backup_days_label.setStyleSheet("font-size: 13px;")
        backup_days_layout.addWidget(backup_days_label)

        self.backup_days_spin = QSpinBox()
        self.backup_days_spin.setRange(1, 90)
        self.backup_days_spin.setValue(30)
        self.backup_days_spin.setMinimumWidth(80)
        backup_days_layout.addWidget(self.backup_days_spin)

        backup_options.addLayout(backup_days_layout)
        backup_options.addStretch()
        backup_layout.addLayout(backup_options)

        self.backup_path_label = BodyLabel("备份路径: C:\\ProgramData\\DiskCleaner\\backups")
        self.backup_path_label.setStyleSheet("font-size: 13px; color: #666; margin-top: 8px;")
        backup_layout.addWidget(self.backup_path_label)

        content_layout.addWidget(backup_card)

        # 定时清理设置
        schedule_card = CardWidget()
        schedule_layout = QVBoxLayout(schedule_card)
        schedule_layout.setContentsMargins(20, 16, 20, 16)
        schedule_layout.setSpacing(12)

        schedule_title = StrongBodyLabel("定时清理")
        schedule_title.setStyleSheet("font-size: 15px;")
        schedule_layout.addWidget(schedule_title)

        schedule_options = QHBoxLayout()
        schedule_options.setSpacing(24)

        self.enable_schedule = QCheckBox("启用定时清理")
        self.enable_schedule.setChecked(False)
        schedule_options.addWidget(self.enable_schedule)

        time_layout = QHBoxLayout()
        time_label = BodyLabel("执行时间:")
        time_label.setStyleSheet("font-size: 13px;")
        time_layout.addWidget(time_label)

        self.schedule_time_combo = QComboBox()
        for hour in range(24):
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                self.schedule_time_combo.addItem(time_str)
        self.schedule_time_combo.setCurrentText("02:00")
        time_layout.addWidget(self.schedule_time_combo)

        schedule_options.addLayout(time_layout)
        schedule_options.addStretch()
        schedule_layout.addLayout(schedule_options)

        content_layout.addWidget(schedule_card)

        # 工具调用日志
        log_card = CardWidget()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 12, 16, 12)
        log_layout.setSpacing(8)

        log_header = QHBoxLayout()
        log_title = StrongBodyLabel("工具调用日志")
        log_title.setStyleSheet("font-size: 15px;")
        log_header.addWidget(log_title)
        log_header.addStretch()

        clear_log_btn = PushButton(FluentIcon.DELETE, "清除日志")
        clear_log_btn.setMinimumWidth(100)
        log_header.addWidget(clear_log_btn)

        log_layout.addLayout(log_header)

        self.tool_logger = ToolLoggerWidget()
        log_layout.addWidget(self.tool_logger)

        content_layout.addWidget(log_card)

        content_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)


class AgentHubPage(QWidget):
    """智能体中心页面 - Agent Hub v2.0

    采用 4 选项卡架构：
    概览 | 清理 | 智能体 | 日志与设置

    信号保持与原版本兼容
    """

    # 信号（保持兼容）
    task_started = pyqtSignal(dict)
    task_paused = pyqtSignal()
    task_resumed = pyqtSignal()
    task_stopped = pyqtSignal()
    mode_changed = pyqtSignal(str)
    scan_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.timer = QTimer()
        self.last_error = None
        self._initialized = False

        # Cleanup 相关组件
        self.user_profile = None
        self.cleanup_plan = None
        self.cleanup_widget = None

        self._init_ui()
        self._connect_signals()
        logger.info("[AgentHub] 智能体中心页面初始化完成 (v2.0 - Tab架构)")

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建顶部标题栏
        self._create_header()
        main_layout.addWidget(self.header_widget)

        # 创建选项卡容器
        self.main_tab = SegmentedWidget()
        self.main_tab.setFixedHeight(40)
        self.main_tab.setCheckable(False)
        self.main_tab.addItem(
            routeKey="overview",
            onClick=lambda: self.stacked_widget.setCurrentIndex(0),
            text="概览",
            icon=FluentIcon.HOME,
        )
        self.main_tab.addItem(
            routeKey="cleanup",
            onClick=lambda: self.stacked_widget.setCurrentIndex(1),
            text="清理",
            icon=FluentIcon.CLEAR,
        )
        self.main_tab.addItem(
            routeKey="agents",
            onClick=lambda: self.stacked_widget.setCurrentIndex(2),
            text="智能体",
            icon=FluentIcon.ROBOT,
        )
        self.main_tab.addItem(
            routeKey="logs",
            onClick=lambda: self.stacked_widget.setCurrentIndex(3),
            text="日志与设置",
            icon=FluentIcon.HISTORY,
        )
        self.main_tab.setCurrentItem("overview")

        # 样式设置
        self.main_tab.setStyleSheet("""
            SegmentedWidget {
                font-size: 14px;
                background-color: transparent;
            }
        """)

        main_layout.addWidget(self.main_tab)

        # 创建选项卡内容堆叠容器
        self.stacked_widget = QStackedWidget()

        # 创建各个选项卡
        self.overview_tab = OverviewTab()
        self.cleanup_tab = CleanupTab()
        self.agents_tab = AgentsTab()
        self.logs_tab = LogsSettingsTab()

        self.stacked_widget.addWidget(self.overview_tab)  # index 0
        self.stacked_widget.addWidget(self.cleanup_tab)    # index 1
        self.stacked_widget.addWidget(self.agents_tab)     # index 2
        self.stacked_widget.addWidget(self.logs_tab)       # index 3

        # 连接选项卡切换信号
        self.stacked_widget.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.stacked_widget)

        # 创建状态栏
        self._create_status_bar(main_layout)

        # 连接清理相关信号
        self.cleanup_tab.cleanup_started.connect(self._on_cleanup_started)
        self.overview_tab.cleanup_requested.connect(self._on_cleanup_requested)
        self.agents_tab.task_action_requested.connect(self._on_task_action)

    def _connect_signals(self):
        """连接信号"""
        # Overview tab signals
        self.overview_tab.cleanup_requested.connect(self._on_cleanup_requested)
        self.overview_tab.scan_requested.connect(lambda: self.scan_requested.emit("quick"))

        # Agents tab signals
        self.agents_tab.task_action_requested.connect(self._on_task_action)

        # Cleanup tab signals
        self.cleanup_tab.cleanup_started.connect(self._on_cleanup_started)
        self.cleanup_tab.preview_shown.connect(self._on_preview_shown)

        # Logs tab signals
        self.logs_tab.settings_changed.connect(self._on_settings_changed)

    def _create_header(self):
        """创建顶部标题栏"""
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(50)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(24, 8, 24, 8)
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

        self.ai_status = BodyLabel("AI 系统: 就绪")
        self.ai_status.setStyleSheet("color: #52C41A; font-size: 13px;")
        header_layout.addWidget(self.ai_status)

        header_layout.addStretch()

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

        status_layout.addStretch()

        self.time_label = BodyLabel("耗时: 00:00")
        self.time_label.setStyleSheet("font-size: 11px; color: #999;")
        status_layout.addWidget(self.time_label)

        parent_layout.addWidget(status_bar)

    # ========== 信号处理 ==========

    def _on_tab_changed(self, index: int):
        """选项卡切换"""
        tab_names = ["概览", "清理", "智能体", "日志与设置"]
        self._update_status_text(f"当前选项卡: {tab_names[index]}")

    def _on_cleanup_requested(self, mode: str):
        """清理请求"""
        logger.info(f"[AgentHub] 清理请求: {mode}")

        # 切换到清理选项卡
        self.main_tab.setCurrentItem("cleanup")
        self.stacked_widget.setCurrentIndex(1)

        if mode == "one_click":
            InfoBar.info(
                title="一键清理",
                content="正在生成智能清理计划...",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            self.cleanup_tab._show_preview_dialog()
        elif mode == "incremental":
            InfoBar.info(
                title="增量清理",
                content="正在扫描上次清理后的新增文件...",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            # 设置为增量模式
            for mode_id, (btn, _) in self.cleanup_tab.mode_buttons.items():
                btn.setChecked(mode_id == "incremental")
            self.cleanup_tab._show_preview_dialog()

    def _on_cleanup_started(self, params: dict):
        """清理开始"""
        logger.info(f"[AgentHub] 清理开始: {params}")
        self._update_status_text("正在清理...")
        self.task_started.emit(params)

        # 连接清理完成信号
        if hasattr(self.cleanup_tab, 'progress_widget') and self.cleanup_tab.progress_widget:
            if self.cleanup_tab.progress_widget.cleanup_thread:
                self.cleanup_tab.progress_widget.cleanup_thread.cleanup_completed.connect(
                    self._on_cleanup_completed
                )
                self.cleanup_tab.progress_widget.cleanup_thread.cleanup_failed.connect(
                    self._on_cleanup_failed
                )

    def _on_cleanup_completed(self, report):
        """清理完成"""
        InfoBar.success(
            title="清理完成",
            content=f"成功清理 {report.success_items} 个文件",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )
        self._update_status_text("清理完成")

    def _on_cleanup_failed(self, error_message):
        """清理失败"""
        InfoBar.error(
            title="清理失败",
            content=error_message,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000,
        )
        self._update_status_text("清理失败")

    def _on_preview_shown(self):
        """预览已显示"""
        InfoBar.success(
            title="预览已生成",
            content="请确认清理计划",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000,
        )

    def _on_task_action(self, action: str):
        """任务操作"""
        logger.info(f"[AgentHub] 任务操作: {action}")
        if action == "start":
            self.state = "running"
            self._update_status_text("任务进行中...")
            self.task_started.emit({})
        elif action == "pause":
            self.state = "paused"
            self._update_status_text("任务已暂停")
            self.task_paused.emit()
        elif action == "stop":
            self.state = "idle"
            self._update_status_text("准备就绪")
            self.task_stopped.emit()
        elif action == "resume":
            self.state = "running"
            self._update_status_text("任务进行中...")
            self.task_resumed.emit()

    def _on_settings_changed(self, settings: dict):
        """设置变更"""
        logger.info(f"[AgentHub] 设置变更: {settings}")
        self.mode_changed.emit(settings.get("mode", "balanced"))

    def _update_status_text(self, text: str):
        """更新状态文本"""
        self.status_text.setText(text)

    # ========== 公共方法（兼容性） ==========

    @property
    def status_card(self):
        """兼容性属性：获取状态卡片"""
        return self.overview_tab.status_card

    @property
    def task_card(self):
        """兼容性属性：获取任务卡片"""
        return self.agents_tab.control_panel.task_card if hasattr(self.agents_tab, 'control_panel') else None

    @property
    def one_click_cleanup_btn(self):
        """兼容性属性：一键清理按钮"""
        return self.overview_tab.one_click_btn

    @property
    def incremental_cleanup_btn(self):
        """兼容性属性：增量清理按钮"""
        return self.overview_tab.incremental_btn

    @property
    def pipeline(self):
        """兼容性属性：获取 pipeline"""
        return self.agents_tab.pipeline

    @property
    def thinking_stream(self):
        """兼容性属性：获取思考流"""
        return self.agents_tab.thinking_stream

    @property
    def tool_logger(self):
        """兼容性属性：获取工具日志"""
        return self.logs_tab.tool_logger

    @property
    def cleanup_widget(self):
        """兼容性属性：获取清理组件"""
        return self.cleanup_tab.progress_widget

    @property
    def overall_progress(self):
        """兼容性属性：获取总体进度标签"""
        return self.agents_tab.overall_progress

    def add_user_message(self, text: str):
        """添加用户消息到思考流"""
        if hasattr(self.agents_tab, 'thinking_stream'):
            self.agents_tab.thinking_stream.add_user_message(text)
            self._update_status_text(f"用户: {text}")

    def add_assistant_message(self, text: str):
        """添加助手消息到思考流"""
        if hasattr(self.agents_tab, 'thinking_stream'):
            self.agents_tab.thinking_stream.add_assistant_message(text)

    def add_tool_result(self, tool_name: str, result: str):
        """添加工具执行结果"""
        if hasattr(self.agents_tab, 'thinking_stream'):
            self.agents_tab.thinking_stream.add_tool_result(tool_name, result)
        if hasattr(self.logs_tab, 'tool_logger'):
            self.logs_tab.tool_logger.add_entry(self.state, tool_name, "success")

    def add_thinking(self, thought: str):
        """添加 AI 思考"""
        if hasattr(self.agents_tab, 'thinking_stream'):
            self.agents_tab.thinking_stream.add_thinking(thought)

    def update_status(self, status: str, stage: str = None, progress: int = None, details: str = None):
        """更新状态"""
        if hasattr(self.overview_tab, 'status_card'):
            import sys
            # 导入枚举类型
            from .agent_theme import AgentStatus
            status_enum = AgentStatus.READY if status == "idle" else AgentStatus(status.upper())
            self.overview_tab.status_card.update_status(status_enum, stage)

    def show_error(
        self,
        title: str,
        message: str,
        error_code: str = "",
        suggestions: list = None,
        recoverable: bool = True,
    ):
        """显示错误信息"""
        logger.warning(f"[AgentHub] 显示错误: [{error_code}] {title} - {message}")
        if hasattr(self.agents_tab, 'control_panel'):
            if hasattr(self.agents_tab.control_panel, 'task_card'):
                self.agents_tab.control_panel.task_card.set_task_status("error", 0, f"错误: {title}")

    def clear_error(self):
        """清除错误状态"""
        self.last_error = None
        if hasattr(self.agents_tab, 'control_panel'):
            if hasattr(self.agents_tab.control_panel, 'task_card'):
                self.agents_tab.control_panel.task_card.set_task_status("idle")

    def reset(self):
        """重置所有状态"""
        self.state = "idle"
        if hasattr(self.agents_tab, 'pipeline'):
            self.agents_tab.pipeline.reset_all_stages()
        if hasattr(self.agents_tab, 'thinking_stream'):
            self.agents_tab.thinking_stream.clear()
        if hasattr(self.logs_tab, 'tool_logger'):
            self.logs_tab.tool_logger.clear()
        self._update_status_text("准备就绪")


# 导出
__all__ = ["AgentHubPage"]
