# -*- coding: utf-8 -*-
"""
规则引擎单元测试

作者: 小午 🦁
创建时间: 2026-02-24
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from core.cleanup_rule import (
    CleanupRule, RuleCondition, FileInfo, ActionResult,
    RuleType, ConditionType, RuleOperator, RuleAction,
    convert_size_to_bytes, convert_bytes_to_size
)
from core.rule_engine import RuleEngine, create_simple_rule
from core.rule_manager import RuleManager, get_common_rules, get_scenario_rules


# ============================================================================
# CleanupRule 测试
# ============================================================================

class TestCleanupRule:
    """清理规则测试"""

    def test_rule_creation(self):
        """测试规则创建"""
        rule = CleanupRule(
            rule_id="test_001",
            rule_name="测试规则",
            description="测试用例",
            rule_type=RuleType.FILE_EXTENSION,
            conditions=[],
            action=RuleAction.DELETE
        )

        assert rule.rule_id == "test_001"
        assert rule.rule_name == "测试规则"
        assert rule.is_enabled == True
        assert rule.priority == 0

    def test_rule_serialization(self):
        """测试规则序列化"""
        condition = RuleCondition(
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="tmp"
        )

        rule = CleanupRule(
            rule_id="test_002",
            rule_name="测试规则",
            description="测试序列化",
            rule_type=RuleType.FILE_EXTENSION,
            conditions=[condition],
            action=RuleAction.DELETE
        )

        # 序列化
        data = rule.to_dict()

        assert data['rule_id'] == "test_002"
        assert len(data['conditions']) == 1
        assert data['conditions'][0]['operator'] == "equals"

        # 反序列化
        restored = CleanupRule.from_dict(data)

        assert restored.rule_id == rule.rule_id
        assert restored.rule_name == rule.rule_name
        assert len(restored.conditions) == 1

    def test_rule_with_conditions(self):
        """测试包含条件的规则"""
        condition1 = RuleCondition(
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.IN,
            value=["tmp", "temp"]
        )

        condition2 = RuleCondition(
            condition_type=ConditionType.FILE_SIZE,
            operator=RuleOperator.GREATER_THAN,
            value=10485760  # 10 MB
        )

        rule = CleanupRule(
            rule_id="test_003",
            rule_name="大临时文件清理",
            description="删除大于 10MB 的临时文件",
            rule_type=RuleType.FILE_SIZE,
            conditions=[condition1, condition2],
            action=RuleAction.DELETE
        )

        assert len(rule.conditions) == 2
        assert rule.conditions[0].operator == RuleOperator.IN
        assert rule.conditions[1].operator == RuleOperator.GREATER_THAN


# ============================================================================
# RuleCondition 测试
# ============================================================================

class TestRuleCondition:
    """规则条件测试"""

    def test_string_evaluate_equals(self):
        """测试字符串条件评估 - 相等"""
        condition = RuleCondition(
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="tmp"
        )

        # 测试用例
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            tmp_path = f.name

        try:
            file_info = FileInfo.from_path(tmp_path)
            assert file_info is not None
            assert condition.evaluate(file_info) == True
        finally:
            os.remove(tmp_path)

    def test_string_evaluate_contains(self):
        """测试字符串条件评估 - 包含"""
        condition = RuleCondition(
            condition_type=ConditionType.FILE_PATH,
            operator=RuleOperator.CONTAINS,
            value="temp"
        )

        # 测试用例
        tmp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(tmp_dir, "test_temp.txt")
            with open(test_file, 'w') as f:
                f.write("test")

            file_info = FileInfo.from_path(test_file)
            assert file_info is not None
            assert condition.evaluate(file_info) == True
        finally:
            # 清理
            if os.path.exists(test_file):
                os.remove(test_file)
            os.rmdir(tmp_dir)

    def test_number_evaluate(self):
        """测试数值条件评估"""
        # 创建一个小文件
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            tmp_path = f.name

        try:
            condition = RuleCondition(
                condition_type=ConditionType.FILE_SIZE,
                operator=RuleOperator.LESS_THAN,
                value=1048576  # 1 MB
            )

            file_info = FileInfo.from_path(tmp_path)
            assert file_info is not None
            assert condition.evaluate(file_info) == True
        finally:
            os.remove(tmp_path)


# ============================================================================
# FileInfo 测试
# ============================================================================

class TestFileInfo:
    """文件信息测试"""

    def test_file_info_creation(self):
        """测试文件信息创建"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            file_info = FileInfo.from_path(tmp_path)

            assert file_info is not None
            assert os.path.basename(tmp_path) == file_info.name
            assert file_info.is_directory == False
            assert file_info.size > 0
            assert file_info.created_at is not None
            assert file_info.modified_at is not None
        finally:
            os.remove(tmp_path)

    def test_file_info_non_existent(self):
        """测试不存在文件的信息"""
        file_info = FileInfo.from_path("/non/existent/path/file.txt")

        assert file_info is None

    def test_file_info_serialization(self):
        """测试文件信息序列化"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            file_info = FileInfo.from_path(tmp_path)
            data = file_info.to_dict()

            restored = FileInfo.from_dict(data)

            assert restored.path == file_info.path
            assert restored.name == file_info.name
            assert restored.size == file_info.size
        finally:
            os.remove(tmp_path)


# ============================================================================
# RuleEngine 测试
# ============================================================================

class TestRuleEngine:
    """规则引擎测试"""

    def test_engine_load_rules(self):
        """测试加载规则"""
        engine = RuleEngine()

        rule = create_simple_rule(
            rule_id="test_001",
            rule_name="测试规则",
            description="测试",
            rule_type=RuleType.FILE_EXTENSION,
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="tmp",
            action=RuleAction.DELETE
        )

        count = engine.load_rules([rule])

        assert count == 1
        assert engine.get_rule("test_001") is not None

    def test_engine_match_file(self):
        """测试文件匹配"""
        engine = RuleEngine()

        # 创建测试文件
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            tmp_path = f.name

        try:
            rule = create_simple_rule(
                rule_id="test_002",
                rule_name="临时文件清理",
                description="测试",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="tmp",
                action=RuleAction.DELETE
            )

            engine.load_rules([rule])

            # 测试匹配
            matched = engine.match_file(tmp_path)

            assert len(matched) == 1
            assert matched[0].rule_id == "test_002"
        finally:
            os.remove(tmp_path)

    def test_engine_no_match(self):
        """测试不匹配"""
        engine = RuleEngine()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name

        try:
            rule = create_simple_rule(
                rule_id="test_003",
                rule_name="临时文件清理",
                description="测试",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="tmp",
                action=RuleAction.DELETE
            )

            engine.load_rules([rule])

            # 测试不匹配
            matched = engine.match_file(tmp_path)

            assert len(matched) == 0
        finally:
            os.remove(tmp_path)

    def test_engine_execute_log_only(self):
        """测试 LOG_ONLY 动作"""
        engine = RuleEngine()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            result = engine.execute_action(tmp_path, RuleAction.LOG_ONLY)

            assert result.success == True
            assert result.action == RuleAction.LOG_ONLY
            assert "已记录" in result.message
            assert os.path.exists(tmp_path)  # 文件仍然存在
        finally:
            os.remove(tmp_path)

    def test_engine_execute_delete(self):
        """测试 DELETE 动作"""
        engine = RuleEngine()

        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            result = engine.execute_action(tmp_path, RuleAction.DELETE)

            assert result.success == True
            assert result.action == RuleAction.DELETE
            assert not os.path.exists(tmp_path)  # 文件已删除
        except Exception as e:
            # 测试失败时手动清理
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


# ============================================================================
# RuleManager 测试
# ============================================================================

class TestRuleManager:
    """规则管理器测试"""

    def test_manager_add_rule(self):
        """测试添加规则"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuleManager(config_dir=tmpdir)

            rule = create_simple_rule(
                rule_id="test_001",
                rule_name="测试规则",
                description="测试",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="tmp",
                action=RuleAction.DELETE
            )

            rule_id = manager.add_rule(rule)

            assert rule_id == "test_001"
            assert manager.get_rule("test_001") is not None

    def test_manager_delete_rule(self):
        """测试删除规则"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuleManager(config_dir=tmpdir)

            rule = create_simple_rule(
                rule_id="test_002",
                rule_name="测试规则",
                description="测试",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="tmp",
                action=RuleAction.DELETE
            )

            manager.add_rule(rule)
            result = manager.delete_rule("test_002")

            assert result == True
            assert manager.get_rule("test_002") is None

    def test_manager_export_import_rules(self):
        """测试导出和导入规则"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuleManager(config_dir=tmpdir)

            # 添加规则
            rule1 = create_simple_rule(
                rule_id="test_003",
                rule_name="测试规则 1",
                description="测试 1",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="tmp",
                action=RuleAction.DELETE
            )

            rule2 = create_simple_rule(
                rule_id="test_004",
                rule_name="测试规则 2",
                description="测试 2",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="log",
                action=RuleAction.DELETE
            )

            manager.add_rule(rule1)
            manager.add_rule(rule2)

            # 导出规则
            export_file = os.path.join(tmpdir, "export.json")
            result = manager.export_rules(export_file)

            assert result == True
            assert os.path.exists(export_file)

            # 导入规则到新管理器
            manager2 = RuleManager(config_dir=tmpdir + "_new")
            imported, skipped, overwritten = manager2.import_rules(export_file)

            assert imported == 2
            assert len(skipped) == 0
            assert len(overwritten) == 0

    def test_manager_list_rules(self):
        """测试列出规则"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuleManager(config_dir=tmpdir)

            # 添加几个规则
            for i in range(3):
                rule = create_simple_rule(
                    rule_id=f"test_{i}",
                    rule_name=f"测试规则 {i}",
                    description=f"测试 {i}",
                    rule_type=RuleType.FILE_EXTENSION,
                    condition_type=ConditionType.FILE_EXTENSION,
                    operator=RuleOperator.EQUALS,
                    value=f"ext{i}",
                    action=RuleAction.DELETE,
                )
                rule.priority = i
                manager.add_rule(rule)

            # 列出所有规则
            rules = manager.list_rules()

            assert len(rules) == 3
            # 应该按优先级排序
            assert rules[0].priority < rules[1].priority
            assert rules[1].priority < rules[2].priority

    def test_manager_enable_disable_rule(self):
        """测试启用/禁用规则"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuleManager(config_dir=tmpdir)

            rule = create_simple_rule(
                rule_id="test_005",
                rule_name="测试规则",
                description="测试",
                rule_type=RuleType.FILE_EXTENSION,
                condition_type=ConditionType.FILE_EXTENSION,
                operator=RuleOperator.EQUALS,
                value="tmp",
                action=RuleAction.DELETE
            )

            manager.add_rule(rule)
            assert manager.get_rule("test_005").is_enabled == True

            manager.disable_rule("test_005")
            assert manager.get_rule("test_005").is_enabled == False

            manager.enable_rule("test_005")
            assert manager.get_rule("test_005").is_enabled == True


# ============================================================================
# 辅助函数测试
# ============================================================================

class TestHelperFunctions:
    """辅助函数测试"""

    def test_convert_size_to_bytes(self):
        """测试转换为字节"""
        assert convert_size_to_bytes(1024) == 1024
        assert convert_size_to_bytes("1 KB") == 1024
        assert convert_size_to_bytes("1 MB") == 1048576
        assert convert_size_to_bytes("1 GB") == 1073741824

    def test_convert_bytes_to_size(self):
        """测试字节转换为大小"""
        assert convert_bytes_to_size(1024, 'KB') == 1.0
        assert convert_bytes_to_size(1048576, 'MB') == 1.0
        assert convert_bytes_to_size(1073741824, 'GB') == 1.0

    def test_get_common_rules(self):
        """测试获取常用规则"""
        rules = get_common_rules()

        assert len(rules) >= 2
        assert all(isinstance(rule, CleanupRule) for rule in rules)

    def test_get_scenario_rules(self):
        """测试获取场景化规则"""
        scenarios = ['gamer', 'office', 'developer', 'normal']

        for scenario in scenarios:
            rules = get_scenario_rules(scenario)
            assert all(isinstance(rule, CleanupRule) for rule in rules)
