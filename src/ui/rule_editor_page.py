# -*- coding: utf-8 -*-
"""
规则编辑器页面 - Rule Editor Page

可视化规则编辑器的 UI 界面，让用户可以直观地创建、编辑、删除和管理清理规则。

Part 1: 规则列表页面
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QComboBox,
    QAbstractItemView,
    QProgressBar,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from qfluentwidgets import (
    StrongBodyLabel,
    BodyLabel,
    SimpleCardWidget,
    CardWidget,
    PushButton,
    PrimaryPushButton,
    FluentIcon,
    IconWidget,
    InfoBar,
    InfoBarPosition,
    ScrollArea,
)

from core.rule_manager import RuleManager
from core.cleanup_rule import (
    CleanupRule,
    RuleType,
    RuleAction,
    ConditionType,
    RuleOperator,
)
from ui.rule_edit_dialog import RuleEditDialog


logger = logging.getLogger(__name__)


class RuleEditorPage(QWidget):
    """规则编辑器页面

    Part 1: 规则列表页面
    """

    rule_edited = pyqtSignal(str)  # rule_id
    rule_added = pyqtSignal(str)  # rule_id
    rule_deleted = pyqtSignal(str)  # rule_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rule_manager = RuleManager()
        self._init_ui()
        self._load_rules()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题栏
        header_layout = QHBoxLayout()

        # Icon
        icon_widget = IconWidget(FluentIcon.DOCUMENT)
        icon_widget.setFixedSize(28, 28)
        icon_widget.setStyleSheet("color: #0078D4;")
        header_layout.addWidget(icon_widget)

        # 标题和描述
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        title = StrongBodyLabel("规则编辑器")
        title.setStyleSheet("font-size: 24px; color: #2c2c2c;")
        title_layout.addWidget(title)

        desc = BodyLabel("创建、编辑和管理清理规则")
        desc.setStyleSheet("color: #666; font-size: 13px;")
        title_layout.addWidget(desc)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # 工具栏按钮
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.new_rule_btn = PushButton(FluentIcon.ADD, "新建规则")
        self.new_rule_btn.clicked.connect(self._on_new_rule)
        toolbar.addWidget(self.new_rule_btn)

        self.import_btn = PushButton(FluentIcon.DOWNLOAD, "导入规则")
        self.import_btn.clicked.connect(self._on_import_rules)
        toolbar.addWidget(self.import_btn)

        self.export_btn = PushButton(FluentIcon.SYNC, "导出规则")
        self.export_btn.clicked.connect(self._on_export_rules)
        toolbar.addWidget(self.export_btn)

        self.refresh_btn = PushButton(FluentIcon.UPDATE, "刷新")
        self.refresh_btn.clicked.connect(self._load_rules)
        toolbar.addWidget(self.refresh_btn)

        self.delete_btn = PushButton(FluentIcon.DELETE, "删除所选")
        self.delete_btn.clicked.connect(self._on_delete_selected)
        self.delete_btn.setEnabled(False)
        toolbar.addWidget(self.delete_btn)

        header_layout.addLayout(toolbar)

        layout.addLayout(header_layout)

        # 统计卡片
        stats_card = SimpleCardWidget()
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 15, 20, 15)

        self.total_rules_label = BodyLabel("总规则数: 0")
        self.total_rules_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        stats_layout.addWidget(self.total_rules_label)

        stats_layout.addSpacing(30)

        self.enabled_rules_label = BodyLabel("已启用: 0")
        self.enabled_rules_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #52C41A;"
        )
        stats_layout.addWidget(self.enabled_rules_label)

        stats_layout.addSpacing(30)

        self.disabled_rules_label = BodyLabel("已禁用: 0")
        self.disabled_rules_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #F5222D;"
        )
        stats_layout.addWidget(self.disabled_rules_label)

        stats_layout.addStretch()

        layout.addWidget(stats_card)

        # 规则列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["", "规则名称", "规则类型", "条件", "动作", "优先级", "状态"]
        )

        # 设置表格属性
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 60)

        # 启用拖拽排序
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.setDragDropMode(QTableWidget.InternalMove)

        # 连接信号
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellChanged.connect(self._on_cell_changed)

        layout.addWidget(self.table)

        # 底部操作栏
        bottom_toolbar = QHBoxLayout()
        bottom_toolbar.setSpacing(10)
        bottom_toolbar.addStretch()

        self.edit_btn = PushButton(FluentIcon.EDIT, "编辑")
        self.edit_btn.clicked.connect(self._on_edit_rule)
        bottom_toolbar.addWidget(self.edit_btn)

        self.copy_btn = PushButton(FluentIcon.COPY, "复制")
        self.copy_btn.clicked.connect(self._on_copy_rule)
        bottom_toolbar.addWidget(self.copy_btn)

        self.test_btn = PushButton(FluentIcon.CODE, "测试...")
        bottom_toolbar.addWidget(self.test_btn)

        layout.addLayout(bottom_toolbar)

    def _load_rules(self):
        """加载规则列表"""
        try:
            logger.info("[RuleEditor] 加载规则列表")

            rules = self.rule_manager.list_rules(enabled_only=False)
            rules.sort(key=lambda r: r.priority)

            # 更新统计
            self.total_rules_label.setText(f"总规则数: {len(rules)}")
            enabled_count = sum(1 for r in rules if r.is_enabled)
            disabled_count = len(rules) - enabled_count
            self.enabled_rules_label.setText(f"已启用: {enabled_count}")
            self.disabled_rules_label.setText(f"已禁用: {disabled_count}")

            # 填充表格
            self._fill_table(rules)

            logger.info(f"[RuleEditor] 成功加载 {len(rules)} 条规则")
            InfoBar.success(
                title="加载完成",
                content=f"成功加载 {len(rules)} 条规则",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )

        except Exception as e:
            logger.error(f"[RuleEditor] 加载规则失败: {e}")
            InfoBar.error(
                title="加载失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )

    def _fill_table(self, rules: List[CleanupRule]):
        """填充表格

        Args:
            rules: 规则列表
        """
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row, rule in enumerate(rules):
            self.table.insertRow(row)

            # 启用/禁用复选框
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)

            checkbox = QCheckBox()
            checkbox.setChecked(rule.is_enabled)
            checkbox.stateChanged.connect(
                lambda state, r=rule: self._on_toggle_rule(r, state)
            )
            checkbox_layout.addWidget(checkbox)

            self.table.setCellWidget(row, 0, checkbox_widget)

            # 规则名称
            name_item = QTableWidgetItem(rule.rule_name)
            name_item.setData(Qt.UserRole, rule.rule_id)  # 存储 rule_id
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name_item)

            # 规则类型
            type_item = QTableWidgetItem(rule.rule_type.value)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, type_item)

            # 条件
            condition_text = self._format_conditions(rule.conditions)
            condition_item = QTableWidgetItem(condition_text)
            condition_item.setFlags(condition_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, condition_item)

            # 动作
            action_item = QTableWidgetItem(rule.action.value)
            action_item.setFlags(action_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, action_item)

            # 优先级
            priority_item = QTableWidgetItem(str(rule.priority))
            priority_item.setFlags(priority_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, priority_item)

            # 状态
            status_text = "启用" if rule.is_enabled else "禁用"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)

            if rule.is_enabled:
                status_item.setForeground(QColor("#52C41A"))
            else:
                status_item.setForeground(QColor("#999999"))

            self.table.setItem(row, 6, status_item)

        self.table.blockSignals(False)

    def _format_conditions(self, conditions: List) -> str:
        """格式化条件文本

        Args:
            conditions: 条件列表

        Returns:
            格式化后的文本
        """
        if not conditions:
            return "-"

        parts = []
        for cond in conditions:
            cond_type = getattr(cond, "condition_type", None)
            cond.__dict__.get("condition_type") if hasattr(cond, "__dict__") else None
            operator = getattr(cond, "operator", None)
            value = getattr(cond, "value", None)

            cond_type_str = cond_type.value if cond_type else "?"
            operator_str = operator.value if operator else "?"
            value_str = str(value) if value is not None else "?"

            if isinstance(value, list):
                value_str = f"[{', '.join(str(v) for v in value)}]"

            parts.append(f"{cond_type_str} {operator_str} {value_str}")

        return ", ".join(parts)

    def _on_selection_changed(self):
        """选择行改变"""
        selected_rows = self.table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0

        self.delete_btn.setEnabled(has_selection)
        self.edit_btn.setEnabled(has_selection)
        self.copy_btn.setEnabled(has_selection)

    def _on_cell_changed(self, row: int, column: int):
        """单元格内容改变（用于拖拽排序）"""
        if row == 0:
            # 重新排序
            self._on_reorder_rules()

    def _on_reorder_rules(self):
        """重新排序规则（拖拽后）"""
        try:
            rule_ids = []
            for row in range(self.table.rowCount()):
                name_item = self.table.item(row, 1)
                if name_item:
                    rule_id = name_item.data(Qt.UserRole)
                    if rule_id:
                        rule_ids.append(rule_id)

            if rule_ids:
                self.rule_manager.reorder_rules(rule_ids)
                logger.info(f"[RuleEditor] 重新排序 {len(rule_ids)} 条规则")

        except Exception as e:
            logger.error(f"[RuleEditor] 排序失败: {e}")

    def _on_toggle_rule(self, rule: CleanupRule, state: int):
        """切换规则启用状态

        Args:
            rule: 规则对象
            state: QCheckBox 状态
        """
        try:
            is_enabled = state == Qt.Checked
            rule_id = rule.rule_id

            if is_enabled:
                self.rule_manager.enable_rule(rule_id)
            else:
                self.rule_manager.disable_rule(rule_id)

            logger.info(
                f"[RuleEditor] {'启用' if is_enabled else '禁用'}规则: {rule.rule_name}"
            )

            # 刷新表格
            self._load_rules()
            self.rule_edited.emit(rule_id)

        except Exception as e:
            logger.error(f"[RuleEditor] 切换规则状态失败: {e}")

    def _on_new_rule(self):
        """新建规则"""
        try:
            # TODO: 打开规则编辑对话框（Part 2）
            InfoBar.info(
                title="新建规则",
                content="规则编辑对话框将在 Part 2 实现",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
        except Exception as e:
            logger.error(f"[RuleEditor] 新建规则失败: {e}")

    def _on_edit_rule(self):
        """编辑规则"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        try:
            row = selected_rows[0].row()
            name_item = self.table.item(row, 1)
            rule_id = name_item.data(Qt.UserRole)

            rule = self.rule_manager.get_rule(rule_id)
            if rule:
                # TODO: 打开编辑对话框（Part 2）
                InfoBar.info(
                    title="编辑规则",
                    content=f"正在编辑规则: {rule.rule_name}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                )

        except Exception as e:
            logger.error(f"[RuleEditor] 编辑规则失败: {e}")

    def _on_copy_rule(self):
        """复制规则"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        try:
            row = selected_rows[0].row()
            name_item = self.table.item(row, 1)
            rule_id = name_item.data(Qt.UserRole)

            rule = self.rule_manager.get_rule(rule_id)
            if rule:
                # 复制规则
                rule_dict = rule.to_dict()
                rule_dict["rule_id"] = ""  # 清空 ID 以生成新的
                rule_dict["rule_name"] = f"{rule.rule_name} (副本)"

                new_rule = CleanupRule.from_dict(rule_dict)
                new_rule_id = self.rule_manager.add_rule(new_rule)

                logger.info(
                    f"[RuleEditor] 复制规则: {rule.rule_name} -> {new_rule.rule_name}"
                )

                self._load_rules()
                self.rule_added.emit(new_rule_id)

                InfoBar.success(
                    title="复制成功",
                    content=f"已复制规则: {new_rule.rule_name}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                )

        except Exception as e:
            logger.error(f"[RuleEditor] 复制规则失败: {e}")
            InfoBar.error(
                title="复制失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )

    def _on_delete_selected(self):
        """删除所选规则"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        try:
            # 确认对话框
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除选中的 {len(selected_rows)} 条规则吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                return

            # 删除规则
            deleted_count = 0
            for selected_row in reversed(selected_rows):
                row = selected_row.row()
                name_item = self.table.item(row, 1)
                rule_id = name_item.data(Qt.UserRole)

                if self.rule_manager.delete_rule(rule_id):
                    deleted_count += 1
                    logger.info(f"[RuleEditor] 删除规则: {rule_id}")

            self._load_rules()

            InfoBar.success(
                title="删除成功",
                content=f"成功删除 {deleted_count} 条规则",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )

        except Exception as e:
            logger.error(f"[RuleEditor] 删除规则失败: {e}")
            InfoBar.error(
                title="删除失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )

    def _on_import_rules(self):
        """导入规则"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "导入规则",
                "",
                "JSON 文件 (*.json);;所有文件 (*.*)",
            )

            if not file_path:
                return

            # 显示导入预览对话框
            import_dialog = _ImportPreviewDialog(file_path, self)
            if import_dialog.exec_() == QDialog.Accepted:
                # 检查合并策略
                merge_strategy = import_dialog.get_merge_strategy()

                # 导入规则
                imported_count, skipped, overwritten = self.rule_manager.import_rules(
                    file_path, merge_strategy=merge_strategy
                )

                logger.info(
                    f"[RuleEditor] 导入规则: 成功 {imported_count}, 跳过 {len(skipped)}, 覆盖 {len(overwritten)}"
                )

                self._load_rules()

                InfoBar.success(
                    title="导入成功",
                    content=f"成功导入 {imported_count} 条规则，跳过 {len(skipped)} 条，覆盖 {len(overwritten)} 条",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )

        except Exception as e:
            logger.error(f"[RuleEditor] 导入规则失败: {e}")
            InfoBar.error(
                title="导入失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )

    def _on_export_rules(self):
        """导出规则"""
        try:
            # 选择导出范围
            selected_rows = self.table.selectionModel().selectedRows()

            if selected_rows:
                # 导出选中
                reply = QMessageBox.question(
                    self,
                    "选择导出范围",
                    "是否仅导出选中的规则？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                rule_ids = []
                if reply == QMessageBox.Yes:
                    # 仅导出选中
                    for selected_row in selected_rows:
                        row = selected_row.row()
                        name_item = self.table.item(row, 1)
                        rule_id = name_item.data(Qt.UserRole)
                        rule_ids.append(rule_id)
                # 否则导出所有规则（rule_ids 保持为空）
            else:
                # 导出所有规则
                rule_ids = None

            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出规则",
                "rules_export.json",
                "JSON 文件 (*.json);;所有文件 (*.*)",
            )

            if not file_path:
                return

            # 确保扩展名
            if not file_path.endswith(".json"):
                file_path += ".json"

            # 导出
            if self.rule_manager.export_rules(file_path, rule_ids):
                logger.info(f"[RuleEditor] 导出规则到: {file_path}")

                InfoBar.success(
                    title="导出成功",
                    content=f"规则已导出到: {file_path}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                )
            else:
                InfoBar.error(
                    title="导出失败",
                    content="导出规则时出错",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )

        except Exception as e:
            logger.error(f"[RuleEditor] 导出规则失败: {e}")
            InfoBar.error(
                title="导出失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )


class _ImportPreviewDialog(QDialog):
    """导入预览对话框

    用于预览即将导入的规则并选择合并策略
    """

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.merge_strategy = "skip"
        self._init_ui()
        self._load_preview()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("导入规则预览")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 文件路径
        file_label = BodyLabel(f"文件: {self.file_path}")
        file_label.setStyleSheet("color: #666;")
        layout.addWidget(file_label)

        # 预览标签
        preview_title = StrongBodyLabel("预览即将导入的规则:")
        preview_title.setStyleSheet("font-size: 14px;")
        layout.addWidget(preview_title)

        # 预览表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["规则名称", "描述", "状态"])
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

        # 合并策略选择
        strategy_label = BodyLabel("合并策略:")
        strategy_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(strategy_label)

        from PyQt5.QtWidgets import QButtonGroup, QRadioButton

        strategy_layout = QHBoxLayout()

        self.strategy_radio_group = QButtonGroup(self)
        self.skip_radio = QRadioButton("跳过已有规则")
        self.skip_radio.setChecked(True)
        self.skip_radio.toggled.connect(self._on_strategy_changed)
        self.strategy_radio_group.addButton(self.skip_radio, 0)

        self.overwrite_radio = QRadioButton("覆盖已有规则")
        self.overwrite_radio.toggled.connect(self._on_strategy_changed)
        self.strategy_radio_group.addButton(self.overwrite_radio, 1)

        strategy_layout.addWidget(self.skip_radio)
        strategy_layout.addWidget(self.overwrite_radio)
        strategy_layout.addStretch()

        layout.addLayout(strategy_layout)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.import_btn = PrimaryPushButton("导入")
        self.import_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.import_btn)

        layout.addLayout(button_layout)

    def _load_preview(self):
        """加载预览"""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            rules = data.get("rules", [])

            self.table.setRowCount(len(rules))

            for row, rule_data in enumerate(rules):
                name_item = QTableWidgetItem(rule_data.get("rule_name", ""))
                self.table.setItem(row, 0, name_item)

                desc_item = QTableWidgetItem(rule_data.get("description", ""))
                self.table.setItem(row, 1, desc_item)

                # 状态
                rule_id = rule_data.get("rule_id", "")
                is_existing = self._check_rule_exists(rule_id)

                status_text = "已存在" if is_existing else "新建"
                status_item = QTableWidgetItem(status_text)

                if is_existing:
                    status_item.setForeground(QColor("#F5222D"))
                else:
                    status_item.setForeground(QColor("#52C41A"))

                self.table.setItem(row, 2, status_item)

        except Exception as e:
            logger.error(f"[ImportPreview] 加载预览失败: {e}")

    def _check_rule_exists(self, rule_id: str) -> bool:
        """检查规则是否已存在"""
        try:
            rule_manager = RuleManager()
            rule = rule_manager.get_rule(rule_id)
            return rule is not None
        except:
            return False

    def _on_strategy_changed(self):
        """合并策略改变"""
        if self.skip_radio.isChecked():
            self.merge_strategy = "skip"
        elif self.overwrite_radio.isChecked():
            self.merge_strategy = "overwrite"

    def get_merge_strategy(self) -> str:
        """获取选择的合并策略

        Returns:
            合并策略
        """
        return self.merge_strategy


__all__ = ["RuleEditorPage"]
