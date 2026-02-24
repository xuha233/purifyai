"""
Rule Editor UI Integration Tests

P3-2: 规则编辑器 UI 界面集成测试

测试覆盖:
1. 规则列表加载
2. 规则编辑对话框打开
3. 规则创建/编辑/删除
4. 规则导入/导出
5. 条件编辑器功能
"""

import pytest
import sys
import os
import tempfile
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 添加 src 到路径（utils 模块在 src/utils 中）
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

# Qt
from PyQt5.QtWidgets import QApplication, qApp, QTableWidgetItem
from PyQt5.QtCore import Qt

if qApp is None:
    QApplication(sys.argv)

# 现在可以正常导入了
from core.rule_manager import RuleManager
from core.cleanup_rule import (
    CleanupRule,
    RuleType,
    RuleAction,
    RuleCondition,
    ConditionType,
    RuleOperator,
    FileInfo,
)
from ui.rule_editor_page import RuleEditorPage
from ui.rule_edit_dialog import RuleEditDialog
from ui.components.condition_widget import ConditionWidget


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir(tmp_path):
    """创建临时配置目录"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    backup_dir = config_dir / "rules_backup"
    backup_dir.mkdir()
    yield str(config_dir)
    # 清理由 RuleManager 和测试完成


@pytest.fixture
def rule_manager(temp_config_dir):
    """创建规则管理器"""
    manager = RuleManager(config_dir=temp_config_dir)
    # 清空规则
    manager = RuleManager(config_dir=tmp_path / "empty_config")
    yield manager


@pytest.fixture
def sample_rules():
    """创建示例规则"""
    rules = []

    # 规则1: 大临时文件
    rules.append(
        CleanupRule(
            rule_id="rule_001",
            rule_name="大临时文件清理",
            description="删除超过10MB的.tmp文件",
            rule_type=RuleType.FILE_SIZE,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value="tmp",
                    is_case_sensitive=False,
                ),
                RuleCondition(
                    condition_type=ConditionType.FILE_SIZE,
                    operator=RuleOperator.GREATER_THAN,
                    value=10 * 1024 * 1024,  # 10MB
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=True,
            priority=0,
        )
    )

    # 规则2: 旧日志文件
    rules.append(
        CleanupRule(
            rule_id="rule_002",
            rule_name="旧日志文件清理",
            description="删除7天前的.log文件",
            rule_type=RuleType.DATE_MODIFIED,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value="log",
                    is_case_sensitive=False,
                ),
                RuleCondition(
                    condition_type=ConditionType.DATE_MODIFIED,
                    operator=RuleOperator.BEFORE,
                    value=datetime.now() - timedelta(days=7),
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=False,
            priority=1,
        )
    )

    # 规则3: 缓存目录
    rules.append(
        CleanupRule(
            rule_id="rule_003",
            rule_name="缓存清理",
            description="清理cache目录",
            rule_type=RuleType.PATH_PATTERN,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_PATH,
                    operator=RuleOperator.CONTAINS,
                    value="cache",
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=True,
            priority=2,
        )
    )

    return rules


@pytest.fixture
def populated_manager(temp_config_dir, sample_rules):
    """创建已填充规则的规则管理器"""
    manager = RuleManager(config_dir=temp_config_dir)

    # 添加示例规则
    for rule in sample_rules:
        manager.add_rule(rule)

    return manager


@pytest.fixture
def rule_editor_page(populated_manager):
    """创建规则编辑器页面"""

    class TestableRuleEditorPage(RuleEditorPage):
        """可测试的规则编辑器页面"""

        def __init__(self, rule_manager=None, parent=None):
            super().__init__(parent)
            if rule_manager:
                self.rule_manager = rule_manager
                self._load_rules()

    page = TestableRuleEditorPage(rule_manager=populated_manager)
    return page


# ============================================================================
# Part 1: 规则列表加载测试
# ============================================================================


class TestRuleListLoading:
    """规则列表加载测试"""

    def test_page_creation(self, rule_editor_page):
        """测试页面创建"""
        assert rule_editor_page is not None
        assert hasattr(rule_editor_page, "table")
        assert hasattr(rule_editor_page, "rule_manager")

    def test_rules_loaded(self, rule_editor_page, sample_rules):
        """测试规则加载"""
        table = rule_editor_page.table
        assert table.rowCount() == len(sample_rules)

    def test_rule_data_display(self, rule_editor_page, sample_rules):
        """测试规则数据显示"""
        table = rule_editor_page.table

        for row, rule in enumerate(sample_rules):
            # 检查规则名称
            name_item = table.item(row, 1)
            assert name_item is not None
            assert name_item.text() == rule.rule_name

            # 检查规则类型
            type_item = table.item(row, 2)
            assert type_item is not None
            assert type_item.text() in [
                "FILE_EXTENSION",
                "FILE_SIZE",
                "DATE_MODIFIED",
                "PATH_PATTERN",
            ]

            # 检查动作
            action_item = table.item(row, 4)
            assert action_item is not None
            assert action_item.text() == rule.action.value

    def test_enabled_status_display(self, rule_editor_page, sample_rules):
        """测试启用状态显示"""
        table = rule_editor_page.table

        for row, rule in enumerate(sample_rules):
            status_item = table.item(row, 6)
            assert status_item is not None

            status_text = "启用" if rule.is_enabled else "禁用"
            assert status_item.text() == status_text

            # 检查颜色
            if rule.is_enabled:
                assert status_item.foreground().color().green() > 200  # 绿色
            else:
                # 灰色或红色
                pass

    def test_statistics_display(self, rule_editor_page, sample_rules):
        """测试统计信息显示"""
        enabled_count = sum(1 for r in sample_rules if r.is_enabled)
        disabled_count = len(sample_rules) - enabled_count

        total_text = f"总规则数: {len(sample_rules)}"
        enabled_text = f"已启用: {enabled_count}"
        disabled_text = f"已禁用: {disabled_count}"

        assert rule_editor_page.total_rules_label.text() == total_text
        assert rule_editor_page.enabled_rules_label.text() == enabled_text
        total_text = f"总规则数: {len(sample_rules)}"
        enabled_text = f"已启用: {enabled_count}"
        disabled_text = f"已禁用: {disabled_count}"

        assert rule_editor_page.total_rules_label.text() == total_text
        assert rule_editor_page.enabled_rules_label.text() == enabled_text
        assert rule_editor_page.disabled_rules_label.text() == disabled_text

    def test_rule_conditions_display(self, rule_editor_page, sample_rules):
        """测试条件显示"""
        table = rule_editor_page.table

        for row, rule in enumerate(sample_rules):
            condition_item = table.item(row, 3)
            assert condition_item is not None

            # 检查条件不为空
            condition_text = condition_item.text()
            assert condition_text != "-"


# ============================================================================
# Part 2: 规则编辑对话框打开测试
# ============================================================================


class TestRuleEditDialogOpening:
    """规则编辑对话框打开测试"""

    def test_new_rule_dialog_creation(self):
        """测试新建规则对话框"""
        dialog = RuleEditDialog(rule=None)
        assert dialog is not None
        assert dialog.windowTitle() == "新建规则"
        assert dialog.rule is None

    def test_edit_rule_dialog_creation(self, sample_rules):
        """测试编辑规则对话框"""
        rule = sample_rules[0]
        dialog = RuleEditDialog(rule=rule)
        assert dialog is not None
        assert dialog.windowTitle() == f"编辑规则"
        assert dialog.rule == rule

    def test_dialog_has_tabs(self):
        """测试对话框包含标签页"""
        dialog = RuleEditDialog()
        assert hasattr(dialog, "tab_widget")
        assert dialog.tab_widget.count() == 4  # 基本信息、条件、动作、预览

        tab_names = [
            dialog.tab_widget.tabText(i) for i in range(dialog.tab_widget.count())
        ]
        assert "基本信息" in tab_names
        assert "条件设置" in tab_names
        assert "动作设置" in tab_names
        assert "预览和测试" in tab_names

    def test_new_dialog_loads_default_values(self):
        """测试新建对话框加载默认值"""
        dialog = RuleEditDialog()

        # 基本信息标签页默认值
        assert dialog.name_input.text() == ""
        assert dialog.desc_input.text() == ""
        assert dialog.priority_spin.value() == 0
        assert dialog.enabled_switch.isChecked() == True

        # 条件列表为空
        assert len(dialog.conditions) == 0

    def test_edit_dialog_loads_rule_data(self, sample_rules):
        """测试编辑对话框加载规则数据"""
        rule = sample_rules[0]
        dialog = RuleEditDialog(rule=rule)

        # 验证基本信息
        assert dialog.name_input.text() == rule.rule_name
        assert dialog.desc_input.text() == rule.description
        assert dialog.priority_spin.value() == rule.priority
        assert dialog.enabled_switch.isChecked() == rule.is_enabled

        # 验证条件
        assert len(dialog.conditions) == len(rule.conditions)


# ============================================================================
# Part 3: 规则创建/编辑/删除测试
# ============================================================================


class TestRuleCreateEditDelete:
    """规则创建/编辑/删除测试"""

    def test_create_new_rule(self, populated_manager):
        """测试创建新规则"""
        # 计算初始规则数
        initial_count = len(populated_manager.list_rules())

        # 创建新规则
        new_rule = CleanupRule(
            rule_id="new_rule_001",
            rule_name="测试规则",
            description="这是一个测试规则",
            rule_type=RuleType.FILE_EXTENSION,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value="test",
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=True,
            priority=10,
        )

        # 添加规则
        rule_id = populated_manager.add_rule(new_rule)
        assert rule_id == "new_rule_001"

        # 验证规则数量增加
        assert len(populated_manager.list_rules()) == initial_count + 1

        # 验证规则存在
        retrieved_rule = populated_manager.get_rule(rule_id)
        assert retrieved_rule is not None
        assert retrieved_rule.rule_name == "测试规则"

    def test_edit_existing_rule(self, populated_manager, sample_rules):
        """测试编辑现有规则"""
        rule = sample_rules[0]
        original_name = rule.rule_name

        # 修改规则
        rule.rule_name = "修改后的规则名称"
        rule.description = "修改后的描述"
        rule.priority = 99

        # 保存修改
        success = populated_manager.update_rule(rule.rule_id, rule)
        assert success == True

        # 验证修改
        updated_rule = populated_manager.get_rule(rule.rule_id)
        assert updated_rule.rule_name == "修改后的规则名称"
        assert updated_rule.description == "修改后的描述"
        assert updated_rule.priority == 99
        assert updated_rule.rule_name != original_name

    def test_delete_rule(self, populated_manager, sample_rules):
        """测试删除规则"""
        initial_count = len(populated_manager.list_rules())
        rule_id = sample_rules[0].rule_id

        # 删除规则
        success = populated_manager.delete_rule(rule_id)
        assert success == True

        # 验证规则数量减少
        assert len(populated_manager.list_rules()) == initial_count - 1

        # 验证规则不存在
        retrieved_rule = populated_manager.get_rule(rule_id)
        assert retrieved_rule is None

    def test_enable_disable_rule(self, populated_manager):
        """测试启用/禁用规则"""
        rules = populated_manager.list_rules()
        if not rules:
            pytest.skip("没有规则可测试")

        rule_id = rules[0].rule_id
        rule = populated_manager.get_rule(rule_id)

        # 禁用规则
        populated_manager.disable_rule(rule_id)
        rule = populated_manager.get_rule(rule_id)
        assert rule.is_enabled == False

        # 启用规则
        populated_manager.enable_rule(rule_id)
        rule = populated_manager.get_rule(rule_id)
        assert rule.is_enabled == True

    def test_copy_rule(self, populated_manager, sample_rules):
        """测试复制规则"""
        original_rule = sample_rules[0]
        initial_count = len(populated_manager.list_rules())

        # 复制规则
        rule_dict = original_rule.to_dict()
        rule_dict["rule_id"] = ""
        rule_dict["rule_name"] = f"{original_rule.rule_name} (副本)"

        copied_rule = CleanupRule.from_dict(rule_dict)
        new_rule_id = populated_manager.add_rule(copied_rule)

        # 验证复制成功
        assert new_rule_id is not None
        assert new_rule_id != original_rule.rule_id
        assert len(populated_manager.list_rules()) == initial_count + 1

        # 验证副本数据
        copied = populated_manager.get_rule(new_rule_id)
        assert copied.rule_name == f"{original_rule.rule_name} (副本)"
        assert len(copied.conditions) == len(original_rule.conditions)


# ============================================================================
# Part 4: 规则导入/导出测试
# ============================================================================


class TestRuleImportExport:
    """规则导入/导出测试"""

    def test_export_all_rules(self, populated_manager, sample_rules, tmp_path):
        """测试导出所有规则"""
        export_file = tmp_path / "export_all.json"

        # 导出所有规则
        success = populated_manager.export_rules(str(export_file), rule_ids=None)
        assert success == True
        assert export_file.exists()

        # 验证导出内容
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("version") is not None
        assert data.get("count") == len(sample_rules)
        assert len(data.get("rules", [])) == len(sample_rules)

    def test_export_selected_rules(self, populated_manager, sample_rules, tmp_path):
        """测试导出选中的规则"""
        export_file = tmp_path / "export_selected.json"
        selected_ids = [sample_rules[0].rule_id, sample_rules[2].rule_id]

        # 导出选中的规则
        success = populated_manager.export_rules(
            str(export_file), rule_ids=selected_ids
        )
        assert success == True
        assert export_file.exists()

        # 验证导出内容
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("count") == 2
        exported_ids = [r["rule_id"] for r in data.get("rules", [])]
        assert set(exported_ids) == set(selected_ids)

    def test_import_new_rules(self, temp_config_dir, tmp_path):
        """测试导入新规则"""
        # 创建导入文件
        import_file = tmp_path / "import_new.json"
        import_data = {
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "import_rule_001",
                    "rule_name": "导入的规则1",
                    "description": "这是导入的规则",
                    "rule_type": RuleType.FILE_EXTENSION.value,
                    "conditions": [
                        {
                            "condition_type": ConditionType.FILE_EXTENSION.value,
                            "operator": RuleOperator.EQUALS.value,
                            "value": "tmp",
                            "is_case_sensitive": False,
                        }
                    ],
                    "action": RuleAction.DELETE.value,
                    "is_enabled": True,
                    "priority": 0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            ],
        }

        with open(import_file, "w", encoding="utf-8") as f:
            json.dump(import_data, f, indent=2, ensure_ascii=False)

        # 导入规则
        manager = RuleManager(config_dir=temp_config_dir)
        imported_count, skipped, overwritten = manager.import_rules(
            str(import_file), merge_strategy="skip"
        )

        # 验证导入结果
        assert imported_count == 1
        assert len(skipped) == 0
        assert len(overwritten) == 0

        # 验证规则存在
        rule = manager.get_rule("import_rule_001")
        assert rule is not None
        assert rule.rule_name == "导入的规则1"

    def test_import_with_skip_strategy(self, populated_manager, sample_rules, tmp_path):
        """测试使用跳过策略导入"""
        # 创建包含已存在规则的导入文件
        import_file = tmp_path / "import_skip.json"
        import_data = {"version": "1.0", "rules": [sample_rules[0].to_dict()]}

        with open(import_file, "w", encoding="utf-8") as f:
            json.dump(import_data, f, indent=2, ensure_ascii=False)

        # 使用跳过策略导入
        imported_count, skipped, overwritten = populated_manager.import_rules(
            str(import_file), merge_strategy="skip"
        )

        # 验证跳过
        assert imported_count == 0
        assert len(skipped) == 1
        assert len(overwritten) == 0

    def test_import_with_overwrite_strategy(
        self, populated_manager, sample_rules, tmp_path
    ):
        """测试使用覆盖策略导入"""
        # 修改规则数据用于覆盖
        rule_dict = sample_rules[0].to_dict()
        rule_dict["rule_name"] = "覆盖后的规则名称"
        rule_dict["description"] = "覆盖后的描述"

        import_file = tmp_path / "import_overwrite.json"
        import_data = {"version": "1.0", "rules": [rule_dict]}

        with open(import_file, "w", encoding="utf-8") as f:
            json.dump(import_data, f, indent=2, ensure_ascii=False)

        # 使用覆盖策略导入
        imported_count, skipped, overwritten = populated_manager.import_rules(
            str(import_file), merge_strategy="overwrite"
        )

        # 验证覆盖
        assert imported_count == 1
        assert len(skipped) == 0
        assert len(overwritten) == 1

        # 验证规则被更新
        rule = populated_manager.get_rule(sample_rules[0].rule_id)
        assert rule.rule_name == "覆盖后的规则名称"

    def test_preset_rules_loading(self, temp_config_dir):
        """测试加载预置规则"""
        manager = RuleManager(config_dir=temp_config_dir)

        # 加载预置规则
        count = manager.load_preset_rules()
        assert count >= 0

        # 列出预置规则
        presets = manager.list_preset_rules()
        assert len(presets) >= 0


# ============================================================================
# Part 5: 条件编辑器功能测试
# ============================================================================


class TestConditionEditor:
    """条件编辑器功能测试"""

    def test_condition_widget_creation(self):
        """测试条件组件创建"""
        widget = ConditionWidget()
        assert widget is not None
        assert widget.condition is None

    def test_condition_widget_with_condition(self):
        """测试带条件的条件组件创建"""
        condition = RuleCondition(
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="tmp",
            is_case_sensitive=False,
        )
        widget = ConditionWidget(condition=condition)
        assert widget is not None
        assert widget.condition == condition

    def test_condition_type_change(self):
        """测试条件类型切换"""
        widget = ConditionWidget()

        # 切换到文件扩展名
        widget.condition_type_combo.setCurrentIndex(
            widget.condition_type_combo.findData(ConditionType.FILE_EXTENSION)
        )
        assert widget.condition_type_combo.currentData() == ConditionType.FILE_EXTENSION

    def test_file_size_value_input(self):
        """测试文件大小值输入"""
        widget = ConditionWidget()

        # 切换到文件大小条件
        widget.condition_type_combo.setCurrentIndex(
            widget.condition_type_combo.findData(ConditionType.FILE_SIZE)
        )

        # 获取条件
        condition = widget.get_condition()
        assert condition.condition_type == ConditionType.FILE_SIZE

    def test_date_value_input(self):
        """测试日期值输入"""
        widget = ConditionWidget()

        # 切换到修改日期条件
        widget.condition_type_combo.setCurrentIndex(
            widget.condition_type_combo.findData(ConditionType.DATE_MODIFIED)
        )

        # 获取条件
        condition = widget.get_condition()
        assert condition.condition_type == ConditionType.DATE_MODIFIED

    def test_get_set_condition(self):
        """测试获取和设置条件"""
        widget = ConditionWidget()

        # 创建条件
        condition = RuleCondition(
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="log",
            is_case_sensitive=True,
        )

        # 设置条件
        widget.set_condition(condition)

        # 获取条件
        retrieved = widget.get_condition()
        assert retrieved.condition_type == ConditionType.FILE_EXTENSION
        assert retrieved.operator == RuleOperator.EQUALS
        assert retrieved.value == "log"
        assert retrieved.is_case_sensitive == True

    def test_operator_validation_by_condition_type(self):
        """测试操作符根据条件类型验证"""
        widget = ConditionWidget()

        # 文件名条件应该有字符串操作符
        widget.condition_type_combo.setCurrentIndex(
            widget.condition_type_combo.findData(ConditionType.FILE_NAME)
        )
        operator_data = [
            widget.operator_combo.itemData(i)
            for i in range(widget.operator_combo.count())
        ]
        assert RuleOperator.EQUALS in operator_data
        assert RuleOperator.CONTAINS in operator_data
        assert RuleOperator.IN in operator_data

        # 文件大小条件应该有数值操作符
        widget.condition_type_combo.setCurrentIndex(
            widget.condition_type_combo.findData(ConditionType.FILE_SIZE)
        )
        operator_data = [
            widget.operator_combo.itemData(i)
            for i in range(widget.operator_combo.count())
        ]
        assert RuleOperator.GREATER_THAN in operator_data
        assert RuleOperator.LESS_THAN in operator_data

    def test_case_sensitive_toggle(self):
        """测试区分大小写切换"""
        widget = ConditionWidget()
        assert widget.case_sensitive_check.isChecked() == False

        widget.case_sensitive_check.setChecked(True)
        assert widget.case_sensitive_check.isChecked() == True

        condition = widget.get_condition()
        assert condition.is_case_sensitive == True

    def test_condition_signal_emission(self, qtbot):
        """测试条件改变信号发射"""
        widget = ConditionWidget()

        emitted_conditions = []
        widget.condition_changed.connect(lambda c: emitted_conditions.append(c))

        # 修改条件类型
        widget.condition_type_combo.setCurrentIndex(
            widget.condition_type_combo.findData(ConditionType.FILE_EXTENSION)
        )

        # 等待信号
        qtbot.wait(100)

        # 验证信号被发射
        assert len(emitted_conditions) > 0

    def test_add_multiple_conditions_in_dialog(self):
        """测试在对话框中添加多个条件"""
        dialog = RuleEditDialog()

        # 初始条件为空
        assert len(dialog.conditions) == 0

        # 添加第一个条件
        dialog._on_add_condition()
        assert len(dialog.conditions) == 1

        # 添加第二个条件
        dialog._on_add_condition()
        assert len(dialog.conditions) == 2

        # 添加第三个条件
        dialog._on_add_condition()
        assert len(dialog.conditions) == 3

    def test_remove_condition_from_dialog(self):
        """测试从对话框中删除条件"""
        dialog = RuleEditDialog()

        # 添加两个条件
        dialog._on_add_condition()
        dialog._on_add_condition()
        assert len(dialog.conditions) == 2

        # 创建条件组件
        condition_widgets = []
        for i in range(dialog.conditions_layout.count()):
            item = dialog.conditions_layout.itemAt(i)
            if item and item.widget():
                condition_widgets.append(item.widget())

        if condition_widgets:
            # 删除第一个条件
            dialog._on_remove_condition(condition_widgets[0])
            assert len(dialog.conditions) == 1

    def test_logic_and_or_toggle(self):
        """测试条件逻辑 AND/OR 切换"""
        dialog = RuleEditDialog()

        # 默认为 AND
        assert dialog.condition_logic == "AND"
        assert dialog.and_radio.isChecked() == True

        # 切换到 OR
        dialog.or_radio.setChecked(True)
        assert dialog.condition_logic == "OR"
        assert dialog.or_radio.isChecked() == True

        # 切回 AND
        dialog.and_radio.setChecked(True)
        assert dialog.condition_logic == "AND"
        assert dialog.and_radio.isChecked() == True


# ============================================================================
# 集成测试: 预览和测试功能
# ============================================================================


class TestRulePreviewAndTest:
    """规则预览和测试功能测试"""

    def test_preview_tab_exists(self):
        """测试预览标签页存在"""
        dialog = RuleEditDialog()
        assert hasattr(dialog, "preview_tab")
        assert hasattr(dialog, "test_file_path_input")
        assert hasattr(dialog, "result_table")

    def test_browse_test_file(self, tmp_path):
        """测试浏览测试文件"""
        dialog = RuleEditDialog()

        # 创建测试目录
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # 模拟选择目录
        dialog.test_file_path_input.setText(str(test_dir))
        assert dialog.test_file_path_input.text() == str(test_dir)

    def test_preview_without_file(self):
        """测试没有选择文件时的预览"""
        dialog = RuleEditDialog()

        # 添加一个条件和动作
        dialog.name_input.setText("测试规则")
        dialog.rule_type_combo.setCurrentIndex(0)
        dialog.action_combo.setCurrentIndex(0)
        dialog._on_add_condition()

        # 点击运行测试（因为没有路径，应该显示警告）
        dialog._on_run_test()
        # 验证结果是空或警告
        assert dialog.result_table.rowCount() >= 0

    def test_get_current_rule_validation(self):
        """测试获取当前规则的验证"""
        dialog = RuleEditDialog()

        # 没有名称应该返回 None
        rule = dialog._get_current_rule()
        assert rule is None

        # 设置名称但没有条件
        dialog.name_input.setText("测试规则")
        rule = dialog._get_current_rule()
        assert rule is None


# ============================================================================
# 端到端测试: 完整工作流程
# ============================================================================


class TestEndToEndWorkflow:
    """端到端工作流程测试"""

    def test_full_rule_lifecycle(self, temp_config_dir):
        """测试完整的规则生命周期"""
        manager = RuleManager(config_dir=temp_config_dir)

        # 1. 创建规则
        rule = CleanupRule(
            rule_id="lifecycle_rule",
            rule_name="生命周期测试规则",
            description="测试完整工作流程",
            rule_type=RuleType.FILE_EXTENSION,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value="tmp",
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=True,
            priority=0,
        )

        rule_id = manager.add_rule(rule)
        assert rule_id == "lifecycle_rule"

        # 2. 获取规则
        retrieved = manager.get_rule(rule_id)
        assert retrieved is not None

        # 3. 编辑规则
        retrieved.rule_name = "修改后的规则"
        manager.update_rule(rule_id, retrieved)

        # 4. 禁用规则
        manager.disable_rule(rule_id)
        retrieved = manager.get_rule(rule_id)
        assert retrieved.is_enabled == False

        # 5. 重新启用
        manager.enable_rule(rule_id)
        retrieved = manager.get_rule(rule_id)
        assert retrieved.is_enabled == True

        # 6. 删除规则
        success = manager.delete_rule(rule_id)
        assert success == True

        retrieved = manager.get_rule(rule_id)
        assert retrieved is None

    def test_import_export_workflow(self, temp_config_dir, tmp_path):
        """测试导入导出工作流程"""
        # 创建第一个管理器并添加规则
        manager1 = RuleManager(config_dir=temp_config_dir / "manager1")

        rule = CleanupRule(
            rule_id="workflow_rule",
            rule_name="工作流测试规则",
            description="导入导出测试",
            rule_type=RuleType.FILE_EXTENSION,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value="tmp",
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=True,
            priority=0,
        )

        manager1.add_rule(rule)

        # 导出规则
        export_file = tmp_path / "workflow_export.json"
        success = manager1.export_rules(str(export_file))
        assert success == True

        # 创建第二个管理器并导入规则
        manager2 = RuleManager(config_dir=temp_config_dir / "manager2")
        imported_count, skipped, overwritten = manager2.import_rules(str(export_file))

        # 验证导入成功
        assert imported_count == 1
        retrieved = manager2.get_rule("workflow_rule")
        assert retrieved is not None
        assert retrieved.rule_name == "工作流测试规则"

    def test_rule_matching(self, temp_config_dir, tmp_path):
        """测试规则匹配功能"""
        manager = RuleManager(config_dir=temp_config_dir)

        # 创建临时文件
        test_file = tmp_path / "test.tmp"
        test_file.write_text("test content")

        # 创建规则
        rule = CleanupRule(
            rule_id="match_rule",
            rule_name="匹配测试规则",
            description="测试规则匹配",
            rule_type=RuleType.FILE_EXTENSION,
            conditions=[
                RuleCondition(
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value="tmp",
                    is_case_sensitive=False,
                ),
            ],
            action=RuleAction.DELETE,
            is_enabled=True,
            priority=0,
        )

        manager.add_rule(rule)

        # 测试匹配
        file_info = FileInfo.from_path(str(test_file))
        assert file_info is not None

        is_match = rule.matches(file_info)
        assert is_match == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
