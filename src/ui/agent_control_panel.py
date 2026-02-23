# -*- coding: utf-8 -*-
"""
智能体控制面板 - Agent Control Panel

提供智能体模式的快速配置和控制
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt, pyqtSignal

from qfluentwidgets import (
    SimpleCardWidget, SubtitleLabel, BodyLabel, StrongBodyLabel,
    PushButton, PrimaryPushButton, ToolButton, FluentIcon,
    ComboBox, SwitchButton, IconWidget, RoundMenu, Action,
    MenuAnimationType, Flyout, FlyoutAnimationType, InfoBar,
    InfoBarPosition
)

from .agent_config import (
    AGENT_MODE_OPTIONS, AGENT_UI_TEXTS, get_available_models,
    get_agent_mode_info, get_risk_policy
)
from .agent_theme import AgentTheme
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentControlPanel(QWidget):
    """智能体控制面板

    功能:
    - 智能体模式选择（禁用/混合/完全）
    - AI 模型选择
    - 扫描模式选择
    - 备份策略开关
    """

    # 信号
    mode_changed = pyqtSignal(str)  # new_mode
    model_changed = pyqtSignal(str)  # new_model
    scan_type_changed = pyqtSignal(str)  # new_scan_type
    backup_changed = pyqtSignal(bool)  # backup_enabled
    quick_action = pyqtSignal(str)  # action_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "hybrid"
        self.current_model = "claude-opus-4-6"
        self.backup_enabled = True

        self._init_ui()
        self._update_ui_for_mode()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # ========== 智能体模式选择 ==========
        mode_card = self._create_mode_card()
        layout.addWidget(mode_card)

        # ========== AI 模型选择 ==========
        model_card = self._create_model_card()
        layout.addWidget(model_card)

        # ========== 扫描配置 ==========
        scan_card = self._create_scan_card()
        layout.addWidget(scan_card)

        # ========== 备份策略 ==========
        backup_card = self._create_backup_card()
        layout.addWidget(backup_card)

        # ========== 快速操作 ==========
        quick_actions_card = self._create_quick_actions_card()
        layout.addWidget(quick_actions_card)

        layout.addStretch()

    def _create_mode_card(self) -> SimpleCardWidget:
        """创建模式选择卡片"""
        card = SimpleCardWidget()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("智能体模式")
        title.setStyleSheet('font-size: 14px;')
        layout.addWidget(title)

        # 模式选项
        self.mode_button_group = QButtonGroup(card)
        self.mode_buttons = {}

        layout.addSpacing(4)

        modes = [
            ("disabled", "禁用", "使用传统扫描和分析系统"),
            ("hybrid", "混合模式", "智能体辅助，传统系统后备（推荐）", True),
            ("full", "完全智能体", "使用智能体系统处理所有操作")
        ]

        for mode_key, mode_name, description, is_default in modes:
            if is_default:
                self.current_mode = mode_key

            mode_btn = QRadioButton(f"  {mode_name}  ")
            mode_btn.setChecked(is_default)
            mode_btn.setStyleSheet('''
                QRadioButton {
                    spacing: 8px;
                    color: #2c2c2c;
                    font-size: 12px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
            ''')
            layout.addWidget(mode_btn)

            # 描述标签
            desc_label = BodyLabel(f"   {description}")
            desc_label.setStyleSheet('color: #999; font-size: 10px; margin-bottom: 4px;')
            layout.addWidget(desc_label)

            self.mode_button_group.addButton(mode_btn)
            self.mode_buttons[mode_key] = mode_btn

            # 连接信号
            mode_btn.toggled.connect(lambda checked, m=mode_key: self._on_mode_changed(m, checked))

        return card

    def _create_model_card(self) -> SimpleCardWidget:
        """创建 AI 模型选择卡片"""
        card = SimpleCardWidget()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("AI 模型")
        title.setStyleSheet('font-size: 14px;')
        layout.addWidget(title)

        # 模型选择下拉框
        model_row = QHBoxLayout()
        model_row.setContentsMargins(0, 0, 0, 0)

        model_label = BodyLabel("选择模型:")
        model_label.setStyleSheet('font-size: 12px; color: #666;')
        model_row.addWidget(model_label)

        self.model_combo = ComboBox()
        models = get_available_models()
        for model in models:
            self.model_combo.addItem(f"{model['name']} - {model['description']}", model['id'])

        # 设置默认模型
        index = self.model_combo.findData("claude-opus-4-6")
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.model_combo.setFixedHeight(32)
        model_row.addStretch()
        model_row.addWidget(self.model_combo)

        layout.addLayout(model_row)

        # 模型信息
        self.model_info_label = BodyLabel("最强性能模型，适合复杂任务")
        self.model_info_label.setStyleSheet('font-size: 10px; color: #999;')
        layout.addWidget(self.model_info_label)

        return card

    def _create_scan_card(self) -> SimpleCardWidget:
        """创建扫描配置卡片"""
        card = SimpleCardWidget()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("扫描配置")
        title.setStyleSheet('font-size: 14px;')
        layout.addWidget(title)

        # 扫描模式选择
        scan_row = QHBoxLayout()
        scan_row.setContentsMargins(0, 0, 0, 0)

        scan_label = BodyLabel("扫描模式:")
        scan_label.setStyleSheet('font-size: 12px; color: #666;')
        scan_row.addWidget(scan_label)

        self.scan_combo = ComboBox()
        self.scan_combo.addItems(["标准扫描", "快速扫描", "深度扫描"])
        self.scan_combo.setCurrentIndex(0)
        self.scan_combo.currentIndexChanged.connect(self._on_scan_type_changed)
        self.scan_combo.setFixedHeight(32)
        self.scan_combo.setMinimumWidth(140)
        scan_row.addStretch()
        scan_row.addWidget(self.scan_combo)

        layout.addLayout(scan_row)

        # 扫描目标
        target_row = QHBoxLayout()
        target_row.setContentsMargins(0, 0, 0, 0)

        self.target_combo = ComboBox()
        self.target_combo.addItems(["系统文件", "浏览器缓存", "AppData 目录", "自定义路径"])
        self.target_combo.setCurrentIndex(0)
        self.target_combo.currentIndexChanged.connect(self._on_scan_target_changed)
        self.target_combo.setFixedHeight(32)
        target_row.addStretch()
        target_row.addWidget(self.target_combo)

        layout.addLayout(target_row)

        return card

    def _create_backup_card(self) -> SimpleCardWidget:
        """创建备份策略卡片"""
        card = SimpleCardWidget()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("备份策略")
        title.setStyleSheet('font-size: 14px;')
        layout.addWidget(title)

        # 备份开关
        backup_row = QHBoxLayout()
        backup_row.setContentsMargins(0, 0, 0, 0)

        backup_label = BodyLabel("启用自动备份")
        backup_label.setStyleSheet('font-size: 12px; color: #666;')
        backup_row.addWidget(backup_label)

        backup_row.addStretch()

        self.backup_switch = SwitchButton()
        self.backup_switch.setChecked(True)
        self.backup_switch.checkedChanged.connect(self._on_backup_changed)
        backup_row.addWidget(self.backup_switch)

        layout.addLayout(backup_row)

        # 备份说明
        backup_info = BodyLabel(
            "自动备份将保护被删除的文件，支持从回收站恢复"
        )
        backup_info.setStyleSheet('font-size: 10px; color: #999;')
        backup_info.setWordWrap(True)
        layout.addWidget(backup_info)

        return card

    def _create_quick_actions_card(self) -> SimpleCardWidget:
        """创建快速操作卡片"""
        card = SimpleCardWidget()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel("快速操作")
        title.setStyleSheet('font-size: 14px;')
        layout.addWidget(title)

        # 操作按钮网格
        actions_grid = QGridLayout()
        actions_grid.setSpacing(8)

        actions = [
            ("快速扫描", FluentIcon.SEARCH, "quick_scan"),
            ("AI 审查", FluentIcon.ROBOT, "ai_review"),
            ("执行清理", FluentIcon.DELETE, "execute_cleanup"),
            ("查看报告", FluentIcon.DOCUMENT, "view_report")
        ]

        for i, (label, icon, action) in enumerate(actions):
            btn = PushButton(icon, label)
            btn.clicked.connect(lambda _, a=action: self._on_quick_action(a))
            btn.setFixedHeight(36)
            actions_grid.addWidget(btn, i // 2, i % 2)

        layout.addLayout(actions_grid)

        return card

    def _on_mode_changed(self, mode: str, checked: bool):
        """模式变化回调"""
        if checked:
            self.current_mode = mode
            logger.info(f"[ControlPanel] 模式切换到: {mode}")
            self._update_ui_for_mode()
            self.mode_changed.emit(mode)

            InfoBar.success(
                title="模式已切换",
                content=get_agent_mode_info(mode).get("description", ""),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )

    def _on_model_changed(self, index: int):
        """模型变化回调"""
        model_id = self.model_combo.itemData(index)
        if model_id:
            self.current_model = model_id
            logger.info(f"[ControlPanel] 模型切换到: {model_id}")
            self._update_model_info(index)
            self.model_changed.emit(model_id)

    def _on_scan_type_changed(self, index: int):
        """扫描类型变化回调"""
        scan_types = ["standard", "quick", "deep"]
        scan_type = scan_types[index] if index < len(scan_types) else "standard"
        self.scan_type_changed.emit(scan_type)

    def _on_scan_target_changed(self, index: int):
        """扫描目标变化回调"""
        targets = ["system", "browser", "appdata", "custom"]
        target = targets[index] if index < len(targets) else "system"
        self.scan_type_changed.emit(target)

    def _on_backup_changed(self, enabled: bool):
        """备份开关变化回调"""
        self.backup_enabled = enabled
        logger.info(f"[ControlPanel] 备份{'启用' if enabled else '禁用'}")
        self.backup_changed.emit(enabled)

    def _on_quick_action(self, action: str):
        """快速操作回调"""
        logger.info(f"[ControlPanel] 快速操作: {action}")
        self.quick_action.emit(action)

    def _update_ui_for_mode(self):
        """根据模式更新 UI"""
        mode_info = get_agent_mode_info(self.current_mode)

        # 禁用模式下，禁用某些选项
        is_disabled = self.current_mode == "disabled"

        self.model_combo.setEnabled(not is_disabled)
        self.scan_combo.setEnabled(not is_disabled)

    def _update_model_info(self, index: int):
        """更新模型信息显示"""
        models = get_available_models()
        if 0 <= index < len(models):
            model = models[index]
            self.model_info_label.setText(model.get("description", ""))

    def get_current_mode(self) -> str:
        """获取当前模式"""
        return self.current_mode

    def get_current_model(self) -> str:
        """获取当前模型"""
        return self.current_model

    def is_backup_enabled(self) -> bool:
        """获取备份状态"""
        return self.backup_enabled


# 导出
__all__ = [
    "AgentControlPanel"
]
