# -*- coding: utf-8 -*-
"""
条件编辑组件 - Condition Widget

用于在规则编辑对话框中编辑条件

Part 2: 规则编辑对话框的条件编辑组件
"""

import logging
from typing import Optional, Union, List
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QDateEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIntValidator, QDoubleValidator

from qfluentwidgets import (
    BodyLabel,
    StrongBodyLabel,
    PushButton,
    FluentIcon,
    CardWidget,
    ComboBox,
    LineEdit,
    SwitchButton,
)

from core.cleanup_rule import (
    RuleCondition,
    ConditionType,
    RuleOperator,
)


logger = logging.getLogger(__name__)


class ConditionWidget(CardWidget):
    """条件编辑组件

    允许用户编辑单个条件
    """

    condition_changed = pyqtSignal(object)  # RuleCondition

    def __init__(self, condition: Optional[RuleCondition] = None, parent=None):
        super().__init__(parent)
        self.condition = condition
        self._init_ui()

        if self.condition:
            self._load_condition_from_object()
        else:
            self._set_defaults()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # 第一行：条件类型和操作符
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        # 条件类型标签
        type_label = BodyLabel("条件类型:")
        type_label.setMinimumWidth(70)
        row1_layout.addWidget(type_label)

        # 条件类型下拉框
        self.condition_type_combo = ComboBox()
        self.condition_type_combo.setMinimumWidth(150)
        for ct in ConditionType:
            self.condition_type_combo.addItem(ct.value, ct)
        self.condition_type_combo.currentIndexChanged.connect(
            self._on_condition_type_changed
        )
        row1_layout.addWidget(self.condition_type_combo)

        # 操作符标签
        operator_label = BodyLabel("操作符:")
        operator_label.setMinimumWidth(70)
        operator_label.setMarginLeft(20)
        row1_layout.addWidget(operator_label)

        # 操作符下拉框
        self.operator_combo = ComboBox()
        self.operator_combo.setMinimumWidth(150)
        self._populate_operators()
        self.operator_combo.currentIndexChanged.connect(self._on_operator_changed)
        row1_layout.addWidget(self.operator_combo)

        row1_layout.addStretch()
        layout.addLayout(row1_layout)

        # 第二行：值输入（根据条件类型动态变化）
        self.value_container = QWidget()
        value_layout = QHBoxLayout(self.value_container)
        value_layout.setSpacing(10)
        value_layout.setContentsMargins(0, 0, 0, 0)

        self.value_label = BodyLabel("值:")
        self.value_label.setMinimumWidth(70)
        value_layout.addWidget(self.value_label)

        # 值输入控件（根据类型动态创建）
        self.value_widget = None
        self._create_value_widget(ConditionType.FILE_NAME)

        value_layout.addWidget(self.value_widget)
        value_layout.addStretch()

        layout.addWidget(self.value_container)

        # 第三行：选项
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)

        # 区分大小写
        self.case_sensitive_check = SwitchButton()
        self.case_sensitive_check.setChecked(False)
        self.case_sensitive_check.checkedChanged.connect(self._emit_changed)

        case_layout = QHBoxLayout()
        case_layout.addWidget(BodyLabel("区分大小写"))
        case_layout.addWidget(self.case_sensitive_check)
        options_layout.addLayout(case_layout)

        options_layout.addStretch()
        layout.addLayout(options_layout)

    def _create_value_widget(self, condition_type: ConditionType):
        """根据条件类型创建值输入控件

        Args:
            condition_type: 条件类型
        """
        # 移除旧控件
        if self.value_widget:
            self.value_widget.deleteLater()

        self.value_widget = None

        if condition_type == ConditionType.FILE_NAME:
            self.value_widget = LineEdit()
            self.value_widget.setPlaceholderText("输入文件名，如 *.log 或 test.txt")
            self.value_widget.textChanged.connect(self._emit_changed)

        elif condition_type == ConditionType.FILE_EXTENSION:
            self.value_widget = LineEdit()
            self.value_widget.setPlaceholderText("输入扩展名，如 .log 或 .tmp")
            self.value_widget.textChanged.connect(self._emit_changed)

        elif condition_type == ConditionType.FILE_SIZE:
            size_layout = QHBoxLayout()
            size_layout.setSpacing(10)

            # 数值输入
            size_input = LineEdit()
            size_input.setPlaceholderText("10")
            size_input.setMaximumWidth(100)
            size_input.setValidator(QDoubleValidator(0, 999999, 2))
            size_input.textChanged.connect(self._emit_changed)

            # 单位下拉框
            unit_combo = ComboBox()
            unit_combo.addItems(["B", "KB", "MB", "GB", "TB"])
            unit_combo.setCurrentText("MB")
            unit_combo.setMinimumWidth(80)
            unit_combo.currentIndexChanged.connect(self._emit_changed)

            size_layout.addWidget(size_input)
            size_layout.addWidget(unit_combo)

            self.value_widget = QWidget()
            self.value_widget.setLayout(size_layout)

        elif condition_type in (
            ConditionType.DATE_CREATED,
            ConditionType.DATE_MODIFIED,
        ):
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            date_edit.dateChanged.connect(self._emit_changed)

            self.value_widget = date_edit

        elif condition_type == ConditionType.FILE_PATH:
            self.value_widget = LineEdit()
            self.value_widget.setPlaceholderText("输入路径，如 C:\\Temp 或包含 cache")
            self.value_widget.textChanged.connect(self._emit_changed)

        elif condition_type == ConditionType.FILE_CONTENT:
            self.value_widget = LineEdit()
            self.value_widget.setPlaceholderText("输入要搜索的内容")
            self.value_widget.textChanged.connect(self._emit_changed)

        self.value_container.layout().insertWidget(1, self.value_widget)

    def _populate_operators(self):
        """填充操作符下拉框"""
        self.operator_combo.clear()

        condition_type = self.condition_type_combo.currentData()
        if condition_type is None:
            condition_type = ConditionType.FILE_NAME

        operators = self._get_valid_operators(condition_type)

        for op in operators:
            self.operator_combo.addItem(op.value, op)

    def _get_valid_operators(self, condition_type: ConditionType) -> List[RuleOperator]:
        """获取条件类型的有效操作符

        Args:
            condition_type: 条件类型

        Returns:
            有效操作符列表
        """
        if condition_type in (
            ConditionType.FILE_NAME,
            ConditionType.FILE_EXTENSION,
            ConditionType.FILE_PATH,
        ):
            return [
                RuleOperator.EQUALS,
                RuleOperator.NOT_EQUALS,
                RuleOperator.CONTAINS,
                RuleOperator.STARTS_WITH,
                RuleOperator.ENDS_WITH,
                RuleOperator.MATCHES,
                RuleOperator.IN,
                RuleOperator.NOT_IN,
            ]
        elif condition_type == ConditionType.FILE_SIZE:
            return [
                RuleOperator.EQUALS,
                RuleOperator.NOT_EQUALS,
                RuleOperator.GREATER_THAN,
                RuleOperator.LESS_THAN,
                RuleOperator.GREATER_EQUAL,
                RuleOperator.LESS_EQUAL,
            ]
        elif condition_type in (
            ConditionType.DATE_CREATED,
            ConditionType.DATE_MODIFIED,
        ):
            return [
                RuleOperator.EQUALS,
                RuleOperator.NOT_EQUALS,
                RuleOperator.BEFORE,
                RuleOperator.AFTER,
                RuleOperator.GREATER_THAN,
                RuleOperator.LESS_THAN,
            ]
        elif condition_type == ConditionType.FILE_CONTENT:
            return [
                RuleOperator.CONTAINS,
                RuleOperator.MATCHES,
            ]
        else:
            return list(RuleOperator)

    def _on_condition_type_changed(self):
        """条件类型改变"""
        self._populate_operators()

        condition_type = self.condition_type_combo.currentData()
        self._create_value_widget(condition_type)

        self._emit_changed()

    def _on_operator_changed(self):
        """操作符改变"""
        self._emit_changed()

    def _emit_changed(self):
        """发射条件改变信号"""
        condition = self.get_condition()
        self.condition_changed.emit(condition)

    def _set_defaults(self):
        """设置默认值"""
        self.condition_type_combo.setCurrentIndex(0)
        self.operator_combo.setCurrentIndex(0)
        self.case_sensitive_check.setChecked(False)

        # 清空值输入
        if isinstance(self.value_widget, LineEdit):
            self.value_widget.clear()
        elif isinstance(self.value_widget, QLineEdit):
            self.value_widget.clear()

    def _load_condition_from_object(self):
        """从条件对象加载"""
        if not self.condition:
            return

        # 设置条件类型
        for i in range(self.condition_type_combo.count()):
            if self.condition_type_combo.itemData(i) == self.condition.condition_type:
                self.condition_type_combo.setCurrentIndex(i)
                break

        # 重新创建值控件
        self._create_value_widget(self.condition.condition_type)

        # 设置操作符
        for i in range(self.operator_combo.count()):
            if self.operator_combo.itemData(i) == self.condition.operator:
                self.operator_combo.setCurrentIndex(i)
                break

        # 设置值
        self._set_value(self.condition.value)

        # 设置区分大小写
        self.case_sensitive_check.setChecked(self.condition.is_case_sensitive)

    def _set_value(self, value: Union[str, int, float, List[str], datetime]):
        """设置值到控件

        Args:
            value: 条件值
        """
        if isinstance(self.value_widget, LineEdit):
            if isinstance(value, list):
                self.value_widget.setText(", ".join(str(v) for v in value))
            else:
                self.value_widget.setText(str(value))
        elif isinstance(self.value_widget, QLineEdit):
            if isinstance(value, list):
                self.value_widget.setText(", ".join(str(v) for v in value))
            else:
                self.value_widget.setText(str(value))
        elif isinstance(self.value_widget, QWidget):
            # 处理文件大小输入
            size_layout = self.value_widget.layout()
            if size_layout:
                widgets = [
                    size_layout.itemAt(i).widget()
                    for i in range(size_layout.count())
                    if size_layout.itemAt(i).widget()
                ]
                if len(widgets) >= 2:
                    size_input = widgets[0]
                    unit_combo = widgets[1]

                    if isinstance(size_input, (LineEdit, QLineEdit)) and isinstance(
                        unit_combo, ComboBox
                    ):
                        if isinstance(value, (int, float)):
                            # 默认单位 MB
                            self.value_input = size_input
                            self.value_unit_combo = unit_combo

    def get_condition(self) -> RuleCondition:
        """获取当前编辑的条件

        Returns:
            RuleCondition 对象
        """
        condition_type = self.condition_type_combo.currentData()
        if condition_type is None:
            condition_type = ConditionType.FILE_NAME

        operator = self.operator_combo.currentData()
        if operator is None:
            operator = RuleOperator.EQUALS

        value = self._get_value()
        is_case_sensitive = self.case_sensitive_check.isChecked()

        return RuleCondition(
            condition_type=condition_type,
            operator=operator,
            value=value,
            is_case_sensitive=is_case_sensitive,
        )

    def _get_value(self) -> Union[str, int, float, List[str], datetime]:
        """从控件获取值

        Returns:
            条件值
        """
        if isinstance(self.value_widget, (LineEdit, QLineEdit)):
            text = self.value_widget.text().strip()

            # 如果操作符是 IN 或 NOT_IN，尝试解析为列表
            operator = self.operator_combo.currentData()
            if operator in (RuleOperator.IN, RuleOperator.NOT_IN):
                return [v.strip() for v in text.split(",") if v.strip()]
            return text

        elif isinstance(self.value_widget, QDateEdit):
            from PyQt5.QtCore import QDate

            date = self.value_widget.date()
            return datetime(date.year(), date.month(), date.day())

        elif isinstance(self.value_widget, QWidget):
            # 文件大小输入控件
            size_layout = self.value_widget.layout()
            if size_layout:
                widgets = [
                    size_layout.itemAt(i).widget()
                    for i in range(size_layout.count())
                    if size_layout.itemAt(i).widget()
                ]
                if len(widgets) >= 2:
                    size_input = widgets[0]
                    unit_combo = widgets[1]

                    if isinstance(size_input, (LineEdit, QLineEdit)) and isinstance(
                        unit_combo, ComboBox
                    ):
                        text = size_input.text().strip()
                        unit = unit_combo.currentText()

                        try:
                            value = float(text)
                            # 转换为字节
                            units = {
                                "B": 1,
                                "KB": 1024,
                                "MB": 1024**2,
                                "GB": 1024**3,
                                "TB": 1024**4,
                            }
                            return int(value * units.get(unit, 1024**2))
                        except ValueError:
                            return 0

        return ""

    def set_condition(self, condition: RuleCondition):
        """设置条件

        Args:
            condition: 规则条件对象
        """
        self.condition = condition
        self._load_condition_from_object()


__all__ = ["ConditionWidget"]
