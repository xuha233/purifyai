"""
智能清理页面 UI - Smart Cleanup Integration

集成 SmartCleaner 的完整界面：
- 清理计划预览
- 执行进度显示
- 清理报告展示
- 智能模式切换

Phase 4: UI Complete Integration
"""
import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QDialog, QScrollArea, QFrame, QSplitter,
    QGridLayout, QPushButton
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ProgressBar, FluentIcon, InfoBar,
    InfoBarPosition, CardWidget, StrongBodyLabel, IconWidget,
    HyperlinkCard, MessageBox
)

from core.smart_cleaner import (
    SmartCleaner, SmartCleanConfig, SmartCleanPhase, ScanType,
    get_smart_cleaner, CleanupPlan, CleanupItem, CleanupStatus
)
from core.rule_engine import RiskLevel
from core.backup_manager import BackupManager, get_backup_manager
from core.models_smart import BackupType
from utils.logger import get_logger

logger = get_logger(__name__)


class CleanupItemWidget(QWidget):
    """清理项目列表项组件"""

    def __init__(self, item: CleanupItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.is_selected = False
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.stateChanged.connect(self.on_check_changed)
        layout.addWidget(self.checkbox)

        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 名称 + 风险/备份信息行
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        # 文件名
        name_label = BodyLabel(os.path.basename(self.item.path))
        name_label.setStyleSheet('font-size: 13px; font-weight: 600; color: #2c2c2c;')
        name_label.setMaximumWidth(200)
        name_row.addWidget(name_label)

        # AI 风险标签
        risk_colors = {
            RiskLevel.SAFE: ('#e6f7e6', '#28a745'),
            RiskLevel.SUSPICIOUS: ('#fff3e0', '#ff9800'),
            RiskLevel.DANGEROUS: ('#fee2e2', '#dc3545'),
        }
        risk_labels = {
            RiskLevel.SAFE: '安全',
            RiskLevel.SUSPICIOUS: '可疑',
            RiskLevel.DANGEROUS: '危险',
        }

        bg_color, fg_color = risk_colors.get(self.item.ai_risk, risk_colors[RiskLevel.SAFE])
        risk_text = risk_labels.get(self.item.ai_risk, '未知')

        risk_label = BodyLabel(risk_text)
        risk_label.setStyleSheet(f'''
            font-size: 10px; padding: 2px 8px; border-radius: 4px;
            background: {bg_color}; color: {fg_color}; font-weight: 500;
        ''')
        name_row.addWidget(risk_label)

        # 备份类型标签
        backup_types = {
            BackupType.NONE: '无备份',
            BackupType.HARDLINK: '硬链接',
            BackupType.FULL: '完整备份'
        }
        # 根据风险等级推断备份类型
        backup_type_map = {
            RiskLevel.SAFE: BackupType.NONE,
            RiskLevel.SUSPICIOUS: BackupType.HARDLINK,
            RiskLevel.DANGEROUS: BackupType.FULL
        }
        backup_type = backup_type_map.get(self.item.ai_risk, BackupType.NONE)
        backup_text = backup_types.get(backup_type, '未知')

        backup_label = BodyLabel(backup_text)
        if backup_type == BackupType.NONE:
            backup_label.setStyleSheet('font-size: 10px; color: #999;')
        elif backup_type == BackupType.HARDLINK:
            backup_label.setStyleSheet('font-size: 10px; color: #66bb6a;')
        else:
            backup_label.setStyleSheet('font-size: 10px; color: #42a5f5;')
        name_row.addWidget(backup_label)

        name_row.addStretch()
        info_layout.addLayout(name_row)

        # 路径 + 大小区
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        # 路径 (截断)
        path_display = self.item.path
        if len(path_display) > 50:
            path_display = path_display[:20] + '...' + path_display[-30:]
        path_label = BodyLabel(path_display)
        path_label.setStyleSheet('font-size: 11px; color: #666;')
        row2.addWidget(path_label)

        # 大小
        size_label = BodyLabel(self._format_size(self.item.size))
        size_label.setStyleSheet('font-size: 11px; color: #9997000; font-weight: 500;')
        row2.addStretch()
        row2.addWidget(size_label)

        info_layout.addLayout(row2)
        layout.addLayout(info_layout)

    def on_check_changed(self, state):
        """复选框状态变化"""
        self.is_selected = (state == Qt.Checked)

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class CleanupPlanPreviewDialog(QDialog):
    """清理计划预览对话框"""

    def __init__(self, plan: CleanupPlan, backup_mgr: BackupManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("清理计划预览")
        self.setMinimumSize(700, 500)
        self.plan = plan
        self.backup_mgr = backup_mgr

        self.item_widgets: list[tuple[CleanupItemWidget, CleanupItem]] = []
        self.selected_items: list[CleanupItem] = []

        self.init_ui()
        self._load_items()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = SubtitleLabel("清理计划预览")
        layout.addWidget(title)

        # 统计卡片
        stats_card = self._create_stats_card()
        layout.addWidget(stats_card)

        # 风险过滤
        filter_row = QHBoxLayout()
        filter_label = BodyLabel("筛选:")
        filter_row.addWidget(filter_label)

        self.filter_all_btn = PushButton("全部", clicked=lambda: self._filter_items('all'))
        self.filter_safe_btn = PushButton("安全", clicked=lambda: self._filter_items(RiskLevel.SAFE))
        self.filter_suspicious_btn = PushButton("可疑", clicked=lambda: self._filter_items(RiskLevel.SUSPICIOUS))
        self.filter_dangerous_btn = PushButton("危险", clicked=lambda: self._filter_items(RiskLevel.DANGEROUS))

        for btn in [self.filter_all_btn, self.filter_safe_btn, self.filter_suspicious_btn, self.filter_dangerous_btn]:
            btn.setFixedHeight(32)
            btn.setFixedWidth(80)
            filter_row.addWidget(btn)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # 项目列表
        list_card = SimpleCardWidget()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(8, 8, 8, 8)
        list_layout.setSpacing(4)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setSpacing(0)
        self.items_layout.addStretch()

        scroll.setWidget(self.items_container)
        list_layout.addWidget(scroll)

        layout.addWidget(list_card)

        # 底部按钮
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.select_all_btn = PushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all)
        self.select_all_btn.setFixedHeight(36)
        button_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = PushButton("清空")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        self.deselect_all_btn.setFixedHeight(36)
        button_row.addWidget(self.deselect_all_btn)

        self.execute_btn = PrimaryPushButton("执行清理")
        self.execute_btn.clicked.connect(self.accept)
        self.execute_btn.setFixedHeight(40)
        button_row.addWidget(self.execute_btn)

        layout.addLayout(button_row)

    def _create_stats_card(self) -> CardWidget:
        """创建统计卡片"""
        card = CardWidget()
        card.setFixedHeight(80)

        layout = QGridLayout(card)
        layout.setSpacing(12)

        # Safe
        safe_label = SubtitleLabel("安全")
        safe_label.setStyleSheet('font-size: 16px; color: #28a745;')
        safe_count = SubtitleLabel(str(self.plan.safe_count))
        safe_count.setStyleSheet('font-size: 20px; color: #28a745;')
        safe_size = BodyLabel(f"{self._format_size(sum(i.size for i in self.plan.items if i.ai_risk == RiskLevel.SAFE))}")

        safe_widget = SimpleCardWidget()
        safe_layout = QVBoxLayout(safe_widget)
        safe_layout.setContentsMargins(10, 10, 10, 10)
        safe_layout.setSpacing(2)
        safe_layout.addWidget(safe_label)
        safe_layout.addWidget(safe_count, 0, Qt.AlignCenter)
        safe_layout.addWidget(safe_size)
        layout.addWidget(safe_widget, 0, 0)

        # Suspicious
        susp_label = SubtitleLabel("可疑")
        susp_label.setStyleSheet('font-size: 16px; color: #ff9800;')
        susp_count = SubtitleLabel(str(self.plan.suspicious_count))
        susp_count.setStyleSheet('font-size: 20px; color: #ff9800;')
        susp_size = BodyLabel(f"{self._format_size(sum(i.size for i in self.plan.items if i.ai_risk == RiskLevel.SUSPICIOUS))}")

        susp_widget = SimpleCardWidget()
        susp_layout = QVBoxLayout(susp_widget)
        susp_layout.setContentsMargins(10, 10, 10, 10)
        susp_layout.setSpacing(2)
        susp_layout.addWidget(susp_label)
        susp_layout.addWidget(susp_count, 0, Qt.AlignCenter)
        susp_layout.addWidget(susp_size)
        layout.addWidget(susp_widget, 0, 1)

        # Dangerous
        danger_label = SubtitleLabel("危险")
        danger_label.setStyleSheet('font-size: 16px; color: #dc3545;')
        danger_count = SubtitleLabel(str(self.plan.dangerous_count))
        danger_count.setStyleSheet('font-size: 20px; color: #dc3545;')
        danger_size = BodyLabel(f"{self._format_size(sum(i.size for i in self.plan.items if i.ai_risk == RiskLevel.DANGEROUS))}")

        danger_widget = SimpleCardWidget()
        danger_layout = QVBoxLayout(danger_widget)
        danger_layout.setContentsMargins(10, 10, 10, 10)
        danger_layout.setSpacing(2)
        danger_layout.addWidget(danger_label)
        danger_layout.addWidget(danger_count, 0, Qt.AlignCenter)
        danger_layout.addWidget(danger_size)
        layout.addWidget(danger_widget, 0, 2)

        # 预计释放
        freed_label = SubtitleLabel("预计释放")
        freed_label.setStyleSheet('font-size: 16px; color: #007bff;')
        freed_size = SubtitleLabel(self._format_size(self.plan.estimated_freed))
        freed_size.setStyleSheet('font-size: 20px; color: #007bff; AI调用')
        ai_calls = BodyLabel(f"AI评估: {self.plan.ai_call_count} 次调用")

        freed_widget = SimpleCardWidget()
        freed_layout = QVBoxLayout(freed_widget)
        freed_layout.setContentsMargins(10, 10, 10, 10)
        freed_layout.setSpacing(2)
        freed_layout.addWidget(freed_label)
        freed_layout.addWidget(freed_size, 0, Qt.AlignCenter)
        freed_layout.addWidget(ai_calls)
        layout.addWidget(freed_widget, 0, 3)

        return card

    def _load_items(self):
        """加载清理项目"""
        # 清除现有项目
        for widget, _ in self.item_widgets:
            widget.deleteLater()
        self.item_widgets.clear()

        # 按大小排序（降序）
        sorted_items = sorted(self.plan.items, key=lambda x: x.size, reverse=True)

        for item in sorted_items:
            widget = CleanupItemWidget(item)
            self.items_layout.insertWidget(self.items_layout.count() - 1, widget)
            self.item_widgets.append((widget, item))

            # 默认选择 Safe 项
            if item.ai_risk == RiskLevel.SAFE:
                widget.checkbox.setChecked(True)

    def _filter_items(self, risk_filter):
        """过滤项目

        Args:
            risk_filter: 风险筛选 ('all', RiskLevel.SAFE, RiskLevel.SUSPICIOUS, RiskLevel.DANGEROUS)
        """
        for widget, item in self.item_widgets:
            if risk_filter == 'all' or item.ai_risk == risk_filter:
                widget.setVisible(True)
            else:
                widget.setVisible(False)

    def _select_all(self):
        """全选"""
        for widget, _ in self.item_widgets:
            if widget.isVisible():
                widget.checkbox.setChecked(True)

    def _deselect_all(self):
        """清空选择"""
        for widget, _ in self.item_widgets:
            widget.checkbox.setChecked(False)

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_selected_items(self) -> list[CleanupItem]:
        """获取选中的项目

        Returns:
            选中的 CleanupItem 列表
        """
        selected = []
        for widget, item in self.item_widgets:
            if widget.isVisible() and widget.is_selected:
                selected.append(item)
        return selected


class CleanupReportCard(SimpleCardWidget):
    """清理报告卡片"""

    def __init__(self, execution_result=None, parent=None):
        super().__init__(parent)
        self.execution_result = execution_result
        self.setMinimumHeight(100)
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        header = QHBoxLayout()
        icon = IconWidget(FluentIcon.CHECKBOX)
        icon.setFixedSize(24, 24)
        header.addWidget(icon)

        title = SubtitleLabel("清理完成")
        title.setStyleSheet('font-size: 18px;')
        header.addWidget(title)

        header.addStretch()
        layout.addLayout(header)

        # 统计信息
        if self.execution_result:
            stats_text = (
                f"已清理 {self.execution_result.success_items} 项 | "
                f"释放 {self._format_size(self.execution_result.freed_size)} | "
                f"失败 {self.execution_result.failed_items} 项 | "
                f"跳过 {self.execution_result.skipped_items} 项"
            )
        else:
            stats_text = "等待执行..."

        stats_label = BodyLabel(stats_text)
        stats_label.setStyleSheet('font-size: 14px; color: #333;')
        layout.addWidget(stats_label)

    def update_result(self, result):
        """更新执行结果

        Args:
            result: ExecutionResult
        """
        self.execution_result = result

        # 更新统计文本
        stats_text = (
            f"已清理 {result.success_items} 项 | "
            f"释放 {self._format_size(result.freed_size)} | "
            f"失败 {result.failed_items} 项 | "
            f"跳过 {result.skipped_items} 项"
        )

        # 查找并更新统计标签
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, BodyLabel):
                widget.setText(stats_text)
                break

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class SmartCleanupPage(QWidget):
    """智能清理页面

    使用 SmartCleaner 的清理流程界面
    """

    # 信号
    cleanup_phase_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # 初始化组件
        self.config = SmartCleanConfig()
        self.backup_mgr = get_backup_manager()
        self.cleaner = get_smart_cleaner(
            config=self.config,
            backup_mgr=self.backup_mgr
        )

        self.current_plan: Optional[CleanupPlan] = None
        self.preview_dialog: Optional[CleanupPlanPreviewDialog] = None

        # 连接信号
        self._connect_signals()

        self.init_ui()
        self.logger.info("[UI:SMART_CLEANUP] 智能清理页面初始化完成")

    def _connect_signals(self):
        """连接 SmartCleaner 信号"""
        self.cleaner.phase_changed.connect(self._on_phase_changed)
        self.cleaner.scan_progress.connect(self._on_scan_progress)
        self.cleaner.analyze_progress.connect(self._on_analyze_progress)
        self.cleaner.execute_progress.connect(self._on_execute_progress)
        self.cleaner.item_found.connect(self._on_item_found)
        self.cleaner.plan_ready.connect(self._on_plan_ready)
        self.cleaner.execution_completed.connect(self._on_execution_completed)
        self.cleaner.error.connect(self._on_error)

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # ========== 标题栏 ==========
        header = QHBoxLayout()

        icon = IconWidget(FluentIcon.SYNC)
        icon.setFixedSize(32, 32)
        header.addWidget(icon)

        title = SubtitleLabel("智能清理")
        title.setStyleSheet('font-size: 24px;')
        header.addWidget(title)

        header.addStretch()

        # AI 状态
        self.ai_status_label = BodyLabel(f"AI: {'启用' if self.config.enable_ai else '禁用'}")
        self.ai_status_label.setStyleSheet('color: #666;')
        header.addWidget(self.ai_status_label)

        main_layout.addLayout(header)

        # ========== 阶段指示器 ==========
        self.phase_card = SimpleCardWidget()
        phase_layout = QHBoxLayout(self.phase_card)
        phase_layout.setContentsMargins(16, 12, 16, 12)

        self.phase_label = BodyLabel("准备中")
        self.phase_label.setStyleSheet('font-size: 14px; color: #333; font-weight: 600;')
        phase_layout.addWidget(self.phase_label)

        phase_layout.addStretch()

        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        phase_layout.addWidget(self.progress_bar)

        main_layout.addWidget(self.phase_card)

        # ========== 扫描选择 ==========
        scan_card = SimpleCardWidget()
        scan_layout = QVBoxLayout(scan_card)
        scan_layout.setContentsMargins(16, 16, 16, 16)
        scan_layout.setSpacing(12)

        # 扫描类型
        scan_type_layout = QHBoxLayout()
        scan_type_layout.addWidget(BodyLabel("扫描类型:"))

        self.scan_type_combo = ['system', 'browser', 'appdata', 'custom']
        self.scan_type_index = 0

        for i, scan_type in enumerate(self.scan_type_combo):
            btn = PushButton(scan_type.title())
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda ch, idx=i: self._on_scan_type_changed(idx))
            setattr(self, f'scan_type_{i}_btn', btn)
            scan_type_layout.addWidget(btn)

        # 自定义路径输入（仅在 custom 模式显示）
        self.custom_path_input = BodyLabel()
        self.custom_path_input.setStyleSheet('color: #666;')
        self.custom_path_input.setText("自定义路径: 未选择")
        self.custom_path_input.setVisible(False)
        self.custom_browse_btn = PushButton(FluentIcon.FOLDER, "浏览")
        self.custom_browse_btn.setVisible(False)
        self.custom_browse_btn.clicked.connect(self._select_custom_path)

        scan_type_layout.addStretch()
        scan_type_layout.addWidget(self.custom_path_input)
        scan_type_layout.addWidget(self.custom_browse_btn)
        scan_layout.addLayout(scan_type_layout)

        # 扫描/预览/执行按钮
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        actions_layout.addStretch()

        self.scan_btn = PrimaryPushButton(FluentIcon.SEARCH, "开始扫描")
        self.scan_btn.clicked.connect(self._on_scan_start)
        self.scan_btn.setFixedHeight(40)
        actions_layout.addWidget(self.scan_btn)

        self.preview_btn = PrimaryPushButton(FluentIcon.EDIT, "预览计划")
        self.preview_btn.clicked.connect(self._on_preview_plan)
        self.preview_btn.setEnabled(False)
        self.preview_btn.setFixedHeight(40)
        actions_layout.addWidget(self.preview_btn)

        self.execute_btn = PrimaryPushButton(FluentIcon.DELETE, "执行清理")
        self.execute_btn.clicked.connect(self._on_execute_cleanup)
        self.execute_btn.setEnabled(False)
        self.execute_btn.setFixedHeight(40)
        actions_layout.addWidget(self.execute_btn)

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(40)
        actions_layout.addWidget(self.cancel_btn)

        scan_layout.addLayout(actions_layout)
        main_layout.addWidget(scan_card)

        # ========== 报告卡片 ==========
        self.report_card = CleanupReportCard()
        self.report_card.setVisible(False)
        main_layout.addWidget(self.report_card)

        main_layout.addStretch()

    def _on_scan_type_changed(self, index: int):
        """扫描类型变化回调

        Args:
            index: 扫描类型索引
        """
        # 更新按钮状态
        for i in range(len(self.scan_type_combo)):
            btn = getattr(self, f'scan_type_{i}_btn')
            btn.setChecked(i == index)

        self.scan_type_index = index

        # 显示/隐藏自定义路径输入
        if self.scan_type_combo[index] == 'custom':
            self.custom_path_input.setVisible(True)
            self.custom_browse_btn.setVisible(True)
        else:
            self.custom_path_input.setVisible(False)
            self.custom_browse_btn.setVisible(False)

    def _select_custom_path(self):
        """选择自定义路径"""
        from PyQt5.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "选择扫描路径")
        if path:
            self.custom_path_input.setText(f"自定义路径: {path}")
            self.custom_path = path

    def _on_scan_start(self):
        """开始扫描"""
        scan_type = self.scan_type_combo[self.scan_type_index]
        scan_target = ""

        if scan_type == 'custom':
            if not hasattr(self, 'custom_path'):
                InfoBar.warning("提示", "请先选择扫描路径", parent=self, position=InfoBarPosition.TOP)
                return
            scan_target = self.custom_path

        self.cleaner.start_scan(scan_type, scan_target)
        self._set_ui_state('scanning')

    def _on_preview_plan(self):
        """预览清理计划"""
        if not self.current_plan:
            InfoBar.warning("提示", "没有可预览的清理计划", parent=self, position=InfoBarPosition.TOP)
            return

        self.preview_dialog = CleanupPlanPreviewDialog(self.current_plan, self.backup_mgr, self)
        if self.preview_dialog.exec() == QDialog.Accepted:
            selected = self.preview_dialog.get_selected_items()
            if selected:
                self.cleaner.execute_cleanup(selected)
            else:
                InfoBar.info("提示", "未选择要清理的项目", parent=self, position=InfoBarPosition.TOP)

    def _on_execute_cleanup(self):
        """执行清理"""
        if not self.current_plan:
            InfoBar.warning("提示", "请先预览清理计划", parent=self, position=InfoBarPosition.TOP)
            return

        self.cleaner.execute_cleanup()

    def _on_cancel(self):
        """取消操作"""
        self.cleaner.cancel()
        self._set_ui_state('idle')

    # ---------- 信号回调 ----------

    def _on_phase_changed(self, phase: str):
        """阶段变化回调

        Args:
            phase: 阶段名称
        """
        self.phase_label.setText(f"阶段: {phase.title()}")
        self.cleanup_phase_changed.emit(phase)

        phase_map = {
            'idle': ('空闲', False),
            'scanning': ('扫描中', True),
            'analyzing': ('分析中', True),
            'preview': ('预览中', False),
            'executing': ('执行中', True),
            'completed': ('完成', False),
            'error': ('错误', False)
        }

        if phase in phase_map:
            label, show_progress = phase_map[phase]
            self.phase_label.setText(label)
            self.progress_bar.setVisible(show_progress)

    def _on_scan_progress(self, current: int, total: int):
        """扫描进度回调

        Args:
            current: 当前进度
            total: 总数
        """
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def _on_analyze_progress(self, current: int, total: int):
        """分析进度回调

        Args:
            current: 当前进度
            total: 总数
        """
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def _on_execute_progress(self, current: int, total: int):
        """执行进度回调

        Args:
            current: 当前进度
            total: 总数
        """
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def _on_item_found(self, item):
        """发现清理项目

        Args:
            item: ScanItem
        """
        # 可以在这里显示发现的项
        pass

    def _on_plan_ready(self, plan: CleanupPlan):
        """清理计划就绪回调

        Args:
            plan: 清理计划
        """
        self.current_plan = plan
        self._set_ui_state('preview')

        # 显示计划摘要
        summary = f"Safe: {plan.safe_count} | Suspicious: {plan.suspicious_count} | Dangerous: {plan.dangerous_count}"
        self.phase_label.setText(summary)

    def _on_execution_completed(self, result):
        """执行完成回调

        Args:
            result: ExecutionResult
        """
        self.report_card.update_result(result)
        self.report_card.setVisible(True)
        self._set_ui_state('idle')

    def _on_error(self, error_msg: str):
        """错误回调

        Args:
            error_msg: 错误消息
        """
        InfoBar.error("错误", error_msg, parent=self, position=InfoBarPosition.TOP, duration=5000)
        self._set_ui_state('idle')

    def _set_ui_state(self, state: str):
        """设置 UI 状态

        Args:
            state: 状态标识
        """
        if state == 'idle':
            self.scan_btn.setEnabled(True)
            self.preview_btn.setEnabled(False)
            self.execute_btn.setEnabled(False)
            self.cancel_btn.setVisible(False)
            self.progress_bar.setVisible(False)

        elif state == 'scanning' or state == 'analyzing' or state == 'executing':
            self.scan_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
            self.execute_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)

        elif state == 'preview':
            self.scan_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            self.execute_btn.setEnabled(False)
            self.cancel_btn.setVisible(False)
            self.progress_bar.setVisible(False)

    def toggle_ai(self, enabled: bool):
        """切换 AI 状态

        Args:
            enabled: 是否启用 AI
        """
        self.config.enable_ai = enabled
        self.ai_status_label.setText(f"AI: {'启用' if enabled else '禁用'}")

        # 重置清理器以应用新配置
        self.cleaner = get_smart_cleaner(
            config=self.config,
            backup_mgr=self.backup_mgr
        )
        self._connect_signals()
