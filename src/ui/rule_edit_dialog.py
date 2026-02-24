# -*- coding: utf-8 -*-
"""
规则编辑对话框 - Rule Edit Dialog

用于创建和编辑清理规则

Part 2: 规则编辑对话框
"""

import uuid
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QWidget,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QDoubleSpinBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from qfluentwidgets import (
    BodyLabel,
    StrongBodyLabel,
    PushButton,
    PrimaryPushButton,
    FluentIcon,
    CardWidget,
    LineEdit,
    ComboBox,
    SwitchButton,
    SpinBox,
    InfoBar,
    InfoBarPosition,
    SubtitleLabel,
)

from core.cleanup_rule import (
    CleanupRule,
    RuleType,
    RuleAction,
    RuleCondition,
    ConditionType,
    RuleOperator,
)
from core.rule_manager import RuleManager
from core.cleanup_rule import FileInfo, convert_bytes_to_size

from ui.components.condition_widget import ConditionWidget


logger = logging.getLogger(__name__)


class RuleEditDialog(QDialog):
    """规则编辑对话框

    包含以下标签页：
    - 基本信息
    - 条件设置
    - 动作设置
    - 预览和测试
    """

    rule_saved = pyqtSignal(str)  # rule_id

    def __init__(self, rule: Optional[CleanupRule] = None, parent=None):
        super().__init__(parent)
        self.rule_manager = RuleManager()
        self.rule = rule  # None 表示新建模式
        self.conditions: List[RuleCondition] = []
        self.condition_logic = "AND"  # AND or OR
        self._init_ui()

        if self.rule:
            self._load_rule()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("编辑规则" if self.rule else "新建规则")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标题
        title = SubtitleLabel(self.rule.rule_name if self.rule else "新建规则")
        layout.addWidget(title)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #e0e0e0; border-radius: 5px; }"
        )

        # 基本信息
        self.basic_info_tab = self._create_basic_info_tab()
        self.tab_widget.addTab(self.basic_info_tab, "基本信息")

        # 条件设置
        self.condition_tab = self._create_condition_tab()
        self.tab_widget.addTab(self.condition_tab, "条件设置")

        # 动作设置
        self.action_tab = self._create_action_tab()
        self.tab_widget.addTab(self.action_tab, "动作设置")

        # 预览和测试
        self.preview_tab = self._create_preview_tab()
        self.tab_widget.addTab(self.preview_tab, "预览和测试")

        layout.addWidget(self.tab_widget)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = PrimaryPushButton("保存")
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def _create_basic_info_tab(self) -> QWidget:
        """创建基本信息标签页

        Returns:
            标签页组件
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 规则基本信息卡片
        basic_card = CardWidget()
        basic_layout = QVBoxLayout(basic_card)
        basic_layout.setContentsMargins(20, 20, 20, 20)
        basic_layout.setSpacing(16)

        # 规则名称
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)

        name_label = StrongBodyLabel("规则名称 *")
        name_label.setStyleSheet("font-size: 13px;")
        name_layout.addWidget(name_label)

        self.name_input = LineEdit()
        self.name_input.setPlaceholderText("例如：大临时文件清理")
        self.name_input.setFixedHeight(36)
        name_layout.addWidget(self.name_input)

        basic_layout.addLayout(name_layout)

        # 规则描述
        desc_layout = QVBoxLayout()
        desc_layout.setSpacing(8)

        desc_label = StrongBodyLabel("规则描述")
        desc_label.setStyleSheet("font-size: 13px;")
        desc_layout.addWidget(desc_label)

        self.desc_input = LineEdit()
        self.desc_input.setPlaceholderText("简要描述此规则的用途")
        self.desc_input.setFixedHeight(36)
        desc_layout.addWidget(self.desc_input)

        basic_layout.addLayout(desc_layout)

        # 规则类型
        type_layout = QVBoxLayout()
        type_layout.setSpacing(8)

        type_label = StrongBodyLabel("规则类型 *")
        type_label.setStyleSheet("font-size: 13px;")
        type_layout.addWidget(type_label)

        self.rule_type_combo = ComboBox()
        self.rule_type_combo.setMinimumHeight(36)
        for rt in RuleType:
            self.rule_type_combo.addItem(rt.value.replace("_", " ").title(), rt)
        type_layout.addWidget(self.rule_type_combo)

        basic_layout.addLayout(type_layout)

        # 优先级
        priority_layout = QVBoxLayout()
        priority_layout.setSpacing(8)

        priority_label = StrongBodyLabel("优先级")
        priority_label.setStyleSheet("font-size: 13px;")
        desc_layout.addWidget(BodyLabel("数字越小优先级越高"))
        priority_layout.addWidget(priority_label)

        self.priority_spin = SpinBox()
        self.priority_spin.setRange(0, 100)
        self.priority_spin.setValue(0)
        self.priority_spin.setFixedHeight(36)
        priority_layout.addWidget(self.priority_spin)

        basic_layout.addLayout(priority_layout)

        # 启用状态
        self.enabled_switch = SwitchButton()
        self.enabled_switch.setChecked(True)

        enabled_layout = QHBoxLayout()
        enabled_layout.addWidget(BodyLabel("启用此规则"))
        enabled_layout.addWidget(self.enabled_switch)
        enabled_layout.addStretch()
        basic_layout.addLayout(enabled_layout)

        layout.addWidget(basic_card)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _create_condition_tab(self) -> QWidget:
        """创建条件设置标签页

        Returns:
            标签页组件
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 条件逻辑选择
        logic_card = CardWidget()
        logic_layout = QHBoxLayout(logic_card)
        logic_layout.setContentsMargins(20, 15, 20, 15)
        logic_layout.setSpacing(20)

        logic_title = StrongBodyLabel("条件逻辑:")
        logic_layout.addWidget(logic_title)

        logic_group = QButtonGroup(self)
        self.and_radio = QRadioButton("满足所有条件 (AND)")
        self.and_radio.setChecked(True)
        self.and_radio.toggled.connect(self._on_logic_changed)
        logic_group.addButton(self.and_radio)

        self.or_radio = QRadioButton("满足任一条件 (OR)")
        self.or_radio.toggled.connect(self._on_logic_changed)
        logic_group.addButton(self.or_radio)

        logic_layout.addWidget(self.and_radio)
        logic_layout.addWidget(self.or_radio)
        logic_layout.addStretch()

        layout.addWidget(logic_card)

        # 条件列表区域
        self.conditions_container = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_container)
        self.conditions_layout.setContentsMargins(0, 0, 0, 0)
        self.conditions_layout.setSpacing(12)

        layout.addWidget(self.conditions_container)

        # 添加条件按钮
        add_btn_layout = QHBoxLayout()
        add_btn_layout.addStretch()

        self.add_condition_btn = PushButton(FluentIcon.ADD, "添加条件")
        self.add_condition_btn.clicked.connect(self._on_add_condition)
        add_btn_layout.addWidget(self.add_condition_btn)

        layout.addLayout(add_btn_layout)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _create_action_tab(self) -> QWidget:
        """创建动作设置标签页

        Returns:
            标签页组件
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 动作类型选择
        action_card = CardWidget()
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(20, 20, 20, 20)
        action_layout.setSpacing(16)

        # 动作类型
        action_type_layout = QVBoxLayout()
        action_type_layout.setSpacing(8)

        action_type_label = StrongBodyLabel("动作类型 *")
        action_type_label.setStyleSheet("font-size: 13px;")
        action_type_layout.addWidget(action_type_label)

        self.action_combo = ComboBox()
        self.action_combo.setMinimumHeight(36)
        for action in RuleAction:
            self.action_combo.addItem(action.value.replace("_", " ").title(), action)
        self.action_combo.currentIndexChanged.connect(self._on_action_changed)
        action_type_layout.addWidget(self.action_combo)

        action_layout.addLayout(action_type_layout)

        # 动作参数
        action_param_layout = QVBoxLayout()
        action_param_layout.setSpacing(8)

        self.action_param_label = StrongBodyLabel("动作参数")
        self.action_param_label.setStyleSheet("font-size: 13px;")
        action_param_layout.addWidget(self.action_param_label)

        # 动作参数容器
        self.action_param_container = QWidget()
        param_layout = QVBoxLayout(self.action_param_container)
        param_layout.setContentsMargins(0, 0, 0, 0)

        # MOVE_TO 参数
        self.move_path_input = LineEdit()
        self.move_path_input.setPlaceholderText("例如：C:\\Archives")
        param_layout.addWidget(self.move_path_input)

        # ARCHIVE 参数
        archive_layout = QHBoxLayout()
        archive_layout.setSpacing(10)

        self.archive_format_combo = ComboBox()
        self.archive_format_combo.addItems(["ZIP", "7Z", "TAR.GZ"])
        archive_layout.addWidget(self.archive_format_combo)
        archive_layout.addWidget(BodyLabel("压缩格式"))

        archive_container = QWidget()
        archive_container.setLayout(archive_layout)
        archive_container.setVisible(False)
        self.archive_container = archive_container
        param_layout.addWidget(archive_container)

        # LOG_ONLY 参数
        log_layout = QHBoxLayout()
        log_layout.setSpacing(10)

        self.log_level_combo = ComboBox()
        self.log_level_combo.addItems(["INFO", "WARNING", "ERROR"])
        log_layout.addWidget(self.log_level_combo)
        log_layout.addWidget(BodyLabel("日志级别"))

        log_container = QWidget()
        log_container.setLayout(log_layout)
        log_container.setVisible(False)
        self.log_container = log_container
        param_layout.addWidget(log_container)

        action_param_layout.addWidget(self.action_param_container)
        action_layout.addLayout(action_param_layout)

        layout.addWidget(action_card)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _create_preview_tab(self) -> QWidget:
        """创建预览和测试标签页

        Returns:
            标签页组件
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 文件选择卡片
        file_card = CardWidget()
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(20, 20, 20, 20)
        file_layout.setSpacing(12)

        file_title = StrongBodyLabel("选择测试文件/文件夹:")
        file_layout.addWidget(file_title)

        file_select_layout = QHBoxLayout()

        self.test_file_path_input = LineEdit()
        self.test_file_path_input.setReadOnly(True)
        self.test_file_path_input.setFixedHeight(36)
        file_select_layout.addWidget(self.test_file_path_input)

        self.browse_btn = PushButton("浏览...")
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.clicked.connect(self._on_browse_test_file)
        file_select_layout.addWidget(self.browse_btn)

        self.run_test_btn = PushButton("运行测试")
        self.run_test_btn.clicked.connect(self._on_run_test)
        file_select_layout.addWidget(self.run_test_btn)

        file_layout.addLayout(file_select_layout)
        layout.addWidget(file_card)

        # 测试结果卡片
        result_card = CardWidget()
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(20, 20, 20, 20)
        result_layout.setSpacing(12)

        result_title = StrongBodyLabel("测试结果:")
        result_layout.addWidget(result_title)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["状态", "文件", "原因"])
        self.result_table.selectionMode = QTableWidget.NoSelection
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        result_layout.addWidget(self.result_table)

        # 统计信息
        self.result_stats_label = BodyLabel("匹配数: 0 / 0")
        self.result_stats_label.setStyleSheet("font-weight: bold;")
        result_layout.addWidget(self.result_stats_label)

        layout.addWidget(result_card)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _load_rule(self):
        """加载规则数据到表单"""
        if not self.rule:
            return

        # 基本信息
        self.name_input.setText(self.rule.rule_name)
        self.desc_input.setText(self.rule.description)

        for i in range(self.rule_type_combo.count()):
            if self.rule_type_combo.itemData(i) == self.rule.rule_type:
                self.rule_type_combo.setCurrentIndex(i)
                break

        self.priority_spin.setValue(self.rule.priority)
        self.enabled_switch.setChecked(self.rule.is_enabled)

        # 条件
        self.conditions = list(self.rule.conditions)
        self._refresh_conditions_list()

        # 动作
        for i in range(self.action_combo.count()):
            if self.action_combo.itemData(i) == self.rule.action:
                self.action_combo.setCurrentIndex(i)
                break

    def _refresh_conditions_list(self):
        """刷新条件列表显示"""
        # 清除现有关联的条件组件
        for i in reversed(range(self.conditions_layout.count())):
            item = self.conditions_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # 添加每个条件
        for cond in self.conditions:
            condition_widget = _ConditionItemWidget(cond, self)
            self.conditions_layout.addWidget(condition_widget)

    def _on_add_condition(self):
        """添加新条件"""
        # 创建默认条件
        default_condition = RuleCondition(
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="tmp",
            is_case_sensitive=False,
        )
        self.conditions.append(default_condition)
        self._refresh_conditions_list()

    def _on_remove_condition(self, condition_widget):
        """删除条件"""
        condition = condition_widget.get_condition()
        if condition in self.conditions:
            self.conditions.remove(condition)
        condition_widget.deleteLater()

    def _on_logic_changed(self):
        """条件逻辑改变"""
        if self.and_radio.isChecked():
            self.condition_logic = "AND"
        else:
            self.condition_logic = "OR"

    def _on_action_changed(self):
        """动作类型改变"""
        action = self.action_combo.currentData()

        # 隐藏所有参数容器
        self.move_path_input.setVisible(False)
        self.archive_container.setVisible(False)
        self.log_container.setVisible(False)

        if action == RuleAction.MOVE_TO:
            self.move_path_input.setVisible(True)
        elif action == RuleAction.ARCHIVE:
            self.archive_container.setVisible(True)
        elif action == RuleAction.LOG_ONLY:
            self.log_container.setVisible(True)

    def _on_browse_test_file(self):
        """浏览测试文件"""
        path = QFileDialog.getExistingDirectory(self, "选择测试文件夹", "")
        if path:
            self.test_file_path_input.setText(path)

    def _on_run_test(self):
        """运行测试"""
        test_path = self.test_file_path_input.text()
        if not test_path:
            InfoBar.warning(
                title="请先选择测试文件/文件夹",
                content="点击浏览按钮选择要测试的路径",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return

        rule = self._get_current_rule()
        if not rule:
            InfoBar.warning(
                title="请先完善规则信息",
                content="至少需要配置名称、类型、条件和动作",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return

        # 测试文件（简化版本，仅显示文件列表）
        self.result_table.setRowCount(0)

        info = FileInfo.from_path(test_path)
        if not info:
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem("✗"))
            self.result_table.setItem(0, 1, QTableWidgetItem(test_path))
            self.result_table.setItem(0, 2, QTableWidgetItem("无法访问该路径"))
            self.result_stats_label.setText("匹配数: 0 / 0")
            return

        is_match = rule.matches(info)

        self.result_table.setRowCount(1)
        self.result_table.setItem(0, 0, QTableWidgetItem("✓" if is_match else "✗"))
        self.result_table.setItem(0, 1, QTableWidgetItem(info.path))
        self.result_table.setItem(
            0, 2, QTableWidgetItem("匹配所有条件" if is_match else "不匹配")
        )

        match_count = 1 if is_match else 0
        self.result_stats_label.setText(f"匹配数: {match_count} / 1")

    def _get_current_rule(self) -> Optional[CleanupRule]:
        """获取当前编辑的规则

        Returns:
            CleanupRule 对象或 None
        """
        # 验证基本信息
        rule_name = self.name_input.text().strip()
        if not rule_name:
            InfoBar.warning(
                title="请输入规则名称",
                content="规则名称不能为空",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return None

        rule_type = self.rule_type_combo.currentData()
        if rule_type is None:
            InfoBar.warning(
                title="请选择规则类型",
                content="请选择一个规则类型",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return None

        # 验证条件
        if not self.conditions:
            InfoBar.warning(
                title="请添加至少一个条件",
                content="规则需要至少一个匹配条件",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return None

        # 验证动作
        action = self.action_combo.currentData()
        if action is None:
            InfoBar.warning(
                title="请选择动作类型",
                content="请选择一个动作类型",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
            return None

        # 获取动作参数
        action_params = {}
        if action == RuleAction.MOVE_TO:
            target_path = self.move_path_input.text().strip()
            if not target_path:
                InfoBar.warning(
                    title="请输入目标路径",
                    content="移动操作需要指定目标路径",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                )
                return None
            action_params["target_path"] = target_path
        elif action == RuleAction.ARCHIVE:
            action_params["format"] = self.archive_format_combo.currentText()
        elif action == RuleAction.LOG_ONLY:
            action_params["log_level"] = self.log_level_combo.currentText()

        # 创建规则对象
        rule_id = self.rule.rule_id if self.rule else str(uuid.uuid4())
        rule = CleanupRule(
            rule_id=rule_id,
            rule_name=rule_name,
            description=self.desc_input.text().strip(),
            rule_type=rule_type,
            conditions=self.conditions,
            action=action,
            is_enabled=self.enabled_switch.isChecked(),
            priority=self.priority_spin.value(),
        )

        return rule

    def _on_save(self):
        """保存规则"""
        rule = self._get_current_rule()
        if not rule:
            return

        try:
            if self.rule:
                # 更新模式
                rule_id = self.rule.rule_id
                success = self.rule_manager.update_rule(rule_id, rule)
            else:
                # 新建模式
                rule_id = self.rule_manager.add_rule(rule)
                success = rule_id is not None

            if success:
                InfoBar.success(
                    title="保存成功",
                    content=f"规则 '{rule.rule_name}' 已保存",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                )
                self.rule_saved.emit(rule_id)
                self.accept()
            else:
                InfoBar.error(
                    title="保存失败",
                    content="保存规则时发生错误",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )

        except Exception as e:
            logger.error(f"保存规则失败: {e}")
            InfoBar.error(
                title="保存失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )


class _ConditionItemWidget(CardWidget):
    """条件条目组件

    用于显示单个条件，支持删除和移动操作
    """

    def __init__(self, condition: RuleCondition, parent=None):
        super().__init__(parent)
        self.condition = condition
        self._init_ui()
        self._load_condition()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # 条件编辑器的简化显示
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(10)

        # 条件类型标签
        type_label = BodyLabel(f"{self.condition.condition_type.value}:")
        type_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(type_label)

        # 操作符和值
        op_value_text = f"{self.condition.operator.value} {self._format_value()}"
        op_value_label = BodyLabel(op_value_text)
        summary_layout.addWidget(op_value_label)

        summary_layout.addStretch()

        # 操作按钮
        self.remove_btn = PushButton(FluentIcon.DELETE, "")
        self.remove_btn.setFixedWidth(80)
        summary_layout.addWidget(self.remove_btn)

        layout.addLayout(summary_layout)

    def _load_condition(self):
        """加载条件"""
        pass

    def _format_value(self) -> str:
        """格式化条件值"""
        value = self.condition.value
        if isinstance(value, list):
            return f"[{', '.join(str(v) for v in value)}]"
        elif isinstance(self.condition.condition_type, ConditionType):
            if self.condition.condition_type == ConditionType.FILE_SIZE:
                return f"{convert_bytes_to_size(value, 'MB'):.1f} MB"
        return str(value)

    def get_condition(self) -> RuleCondition:
        """获取条件"""
        return self.condition


__all__ = ["RuleEditDialog"]
