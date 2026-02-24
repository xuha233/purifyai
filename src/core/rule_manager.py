# -*- coding: utf-8 -*-
"""
规则管理器 (Rule Manager)

管理规则的增删改查、导入导出、持久化存储

作者: 小午 🦁
创建时间: 2026-02-24
"""

from __future__ import annotations

import json
import uuid
import os
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .cleanup_rule import (
    CleanupRule, RuleType, RuleAction, ConditionType, RuleOperator
)
from .rule_engine import RuleEngine, create_simple_rule

logger = logging.getLogger(__name__)


# ============================================================================
# 规则管理器类
# ============================================================================

class RuleManager:
    """规则管理器类

    负责规则的完整生命周期管理
    """

    def __init__(self, config_dir: str = "src/config"):
        """初始化规则管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 规则文件路径
        self.rules_file = self.config_dir / "cleanup_rules.json"
        self.preset_rules_file = self.config_dir / "preset_rules.json"
        self.backup_dir = self.config_dir / "rules_backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 规则引擎
        self.engine = RuleEngine()

        # 规则列表（已加载的）
        self._rules: Dict[str, CleanupRule] = {}

        # 自动加载
        self.load_all_rules()

    # ------------------------------------------------------------------------
    # CRUD 操作
    # ------------------------------------------------------------------------

    def add_rule(self, rule: CleanupRule) -> str:
        """添加规则

        Args:
            rule: 清理规则对象

        Returns:
            规则 ID

        Raises:
            ValueError: 规则 ID 已存在
        """
        if rule.rule_id in self._rules:
            raise ValueError(f"规则 ID 已存在: {rule.rule_id}")

        # 自动生成 ID（如果没有）
        if not rule.rule_id:
            rule.rule_id = str(uuid.uuid4())

        self._rules[rule.rule_id] = rule
        self._save_rules()

        # 加载到引擎
        self.engine.load_rules([rule])

        logger.info(f"添加规则: {rule.rule_name} ({rule.rule_id})")
        return rule.rule_id

    def update_rule(self, rule_id: str, rule: CleanupRule) -> bool:
        """更新规则

        Args:
            rule_id: 规则 ID
            rule: 新的规则对象

        Returns:
            是否成功
        """
        if rule_id not in self._rules:
            logger.warning(f"规则不存在: {rule_id}")
            return False

        # 备份原规则
        self._backup_rule(rule_id)

        # 更新
        rule.rule_id = rule_id  # 确保一致
        rule.updated_at = datetime.now()
        self._rules[rule_id] = rule

        self._save_rules()

        # 重新加载到引擎
        self._reload_rules_to_engine()

        logger.info(f"更新规则: {rule.rule_name} ({rule_id})")
        return True

    def delete_rule(self, rule_id: str) -> bool:
        """删除规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功
        """
        if rule_id not in self._rules:
            logger.warning(f"规则不存在: {rule_id}")
            return False

        rule = self._rules.pop(rule_id, None)
        if rule:
            logger.info(f"删除规则: {rule.rule_name} ({rule_id})")

        self._save_rules()

        # 重新加载到引擎
        self._reload_rules_to_engine()

        return True

    def get_rule(self, rule_id: str) -> Optional[CleanupRule]:
        """获取规则

        Args:
            rule_id: 规则 ID

        Returns:
            CleanupRule 对象或 None
        """
        return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> List[CleanupRule]:
        """列出所有规则

        Args:
            enabled_only: 是否仅返回启用的规则

        Returns:
            规则列表，按优先级排序
        """
        rules = list(self._rules.values())

        if enabled_only:
            rules = [r for r in rules if r.is_enabled]

        # 按优先级排序
        rules.sort(key=lambda r: r.priority)
        return rules

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功
        """
        return self._set_rule_enabled(rule_id, True)

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功
        """
        return self._set_rule_enabled(rule_id, False)

    def _set_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        """设置规则启用状态（内部方法）

        Args:
            rule_id: 规则 ID
            enabled: 是否启用

        Returns:
            是否成功
        """
        if rule_id not in self._rules:
            logger.warning(f"规则不存在: {rule_id}")
            return False

        self._rules[rule_id].is_enabled = enabled
        self._rules[rule_id].updated_at = datetime.now()
        self._save_rules()
        self._reload_rules_to_engine()

        logger.info(f"{'启用' if enabled else '禁用'}规则: {rule_id}")
        return True

    def reorder_rules(self, rule_ids: List[str]) -> bool:
        """重新排序规则

        Args:
            rule_ids: 按优先级排序的规则 ID 列表

        Returns:
            是否成功
        """
        # 验证所有 ID 都存在
        missing_ids = set(rule_ids) - set(self._rules.keys())
        if missing_ids:
            logger.warning(f"规则不存在: {missing_ids}")
            return False

        # 分配新优先级
        for idx, rule_id in enumerate(rule_ids):
            if rule_id in self._rules:
                self._rules[rule_id].priority = idx
                self._rules[rule_id].updated_at = datetime.now()

        self._save_rules()
        self._reload_rules_to_engine()

        logger.info(f"重新排序了 {len(rule_ids)} 条规则")
        return True

    # ------------------------------------------------------------------------
    # 导入/导出
    # ------------------------------------------------------------------------

    def export_rules(self, file_path: str, rule_ids: Optional[List[str]] = None) -> bool:
        """导出规则到文件

        Args:
            file_path: 导出文件路径
            rule_ids: 可选，仅导出指定规则

        Returns:
            是否成功
        """
        try:
            # 确定要导出的规则
            if rule_ids:
                rules_to_export = [self._rules[rid] for rid in rule_ids if rid in self._rules]
            else:
                rules_to_export = list(self._rules.values())

            # 导出
            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'count': len(rules_to_export),
                'rules': [rule.to_dict() for rule in rules_to_export]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"导出 {len(rules_to_export)} 条规则到 {file_path}")
            return True
        except (OSError, IOError) as e:
            logger.error(f"导出规则失败: {e}")
            return False

    def import_rules(
        self,
        file_path: str,
        merge_strategy: str = "skip"
    ) -> tuple[int, List[str], List[str]]:
        """从文件导入规则

        Args:
            file_path: 导入文件路径
            merge_strategy: 合并策略（skip | overwrite | skip_all | overwrite_all）

        Returns:
            (成功导入数, 跳过列表, 覆盖列表)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'rules' not in data:
                logger.error(f"无效的规则文件: {file_path}")
                return 0, [], []

            imported_count = 0
            skipped = []
            overwritten = []

            for rule_data in data['rules']:
                rule_id = rule_data['rule_id']

                if rule_id in self._rules:
                    if merge_strategy == "skip":
                        skipped.append(rule_id)
                        continue
                    elif merge_strategy == "skip_all":
                        skipped.append(rule_id)
                        continue
                    elif merge_strategy in ("overwrite", "overwrite_all"):
                        # 备份原规则
                        self._backup_rule(rule_id)
                        overwritten.append(rule_id)
                    else:
                        skipped.append(rule_id)
                        continue

                # 反序列化并添加
                rule = CleanupRule.from_dict(rule_data)
                self._rules[rule_id] = rule
                imported_count += 1
                logger.info(f"导入规则: {rule.rule_name} ({rule_id})")

            self._save_rules()
            self._reload_rules_to_engine()

            return imported_count, skipped, overwritten
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"导入规则失败: {e}")
            return 0, [], []

    # ------------------------------------------------------------------------
    # 预置规则
    # ------------------------------------------------------------------------

    def load_preset_rules(self) -> int:
        """加载预置规则库

        Returns:
            加载的规则数
        """
        if not self.preset_rules_file.exists():
            # 创建默认预置规则
            self._create_default_preset_rules()

        try:
            with open(self.preset_rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'rules' not in data:
                return 0

            count = 0
            for rule_data in data['rules']:
                rule = CleanupRule.from_dict(rule_data)
                rule_id = f"preset_{rule.rule_id}"

                if rule_id not in self._rules:
                    self._rules[rule_id] = rule
                    count += 1

            self._reload_rules_to_engine()
            logger.info(f"加载了 {count} 条预置规则")

            return count
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"加载预置规则失败: {e}")
            return 0

    def add_to_presets(self, rule_id: str) -> bool:
        """将规则添加到预置规则库

        Args:
            rule_id: 规则 ID

        Returns:
            是否成功
        """
        if rule_id not in self._rules:
            logger.warning(f"规则不存在: {rule_id}")
            return False

        rule = self._rules[rule_id]

        # 读取现有预置规则
        presets = {'rules': []}
        if self.preset_rules_file.exists():
            with open(self.preset_rules_file, 'r', encoding='utf-8') as f:
                presets = json.load(f)

        # 添加新规则
        rule_data = rule.to_dict()
        rule_data['rule_id'] = rule_data['rule_id'].replace('preset_', '')
        presets['rules'].append(rule_data)

        # 保存
        with open(self.preset_rules_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

        logger.info(f"规则已添加到预置库: {rule.rule_name}")
        return True

    def list_preset_rules(self) -> List[Dict]:
        """列出可用的预置规则（未导入的）

        Returns:
            预置规则列表
        """
        if not self.preset_rules_file.exists():
            return []

        with open(self.preset_rules_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        presets = []
        for rule_data in data.get('rules', []):
            preset_id = f"preset_{rule_data['rule_id']}"
            is_imported = preset_id in self._rules

            presets.append({
                'rule_id': rule_data['rule_id'],
                'rule_name': rule_data['rule_name'],
                'description': rule_data.get('description', ''),
                'is_imported': is_imported
            })

        return presets

    # ------------------------------------------------------------------------
    # 持久化（私有方法）
    # ------------------------------------------------------------------------

    def load_all_rules(self) -> int:
        """从配置文件加载所有规则

        Returns:
            加载的规则数
        """
        if not self.rules_file.exists():
            logger.info("规则文件不存在，创建新文件")
            self._save_rules()
            return 0

        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'rules' not in data:
                logger.warning("规则文件格式无效，重新创建")
                self._save_rules()
                return 0

            count = 0
            for rule_data in data['rules']:
                rule = CleanupRule.from_dict(rule_data)
                self._rules[rule.rule_id] = rule
                count += 1

            # 加载到引擎
            self._reload_rules_to_engine()

            logger.info(f"从文件加载了 {count} 条规则")
            return count
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"加载规则失败: {e}")
            return 0

    def _save_rules(self) -> bool:
        """保存规则到配置文件

        Returns:
            是否成功
        """
        try:
            data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'count': len(self._rules),
                'rules': [rule.to_dict() for rule in self._rules.values()]
            }

            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except (OSError, IOError) as e:
            logger.error(f"保存规则失败: {e}")
            return False

    def _reload_rules_to_engine(self):
        """重新加载规则到引擎（内部方法）"""
        self.engine.load_rules(list(self._rules.values()))

    def _backup_rule(self, rule_id: str):
        """备份规则（内部方法）

        Args:
            rule_id: 规则 ID
        """
        if rule_id not in self._rules:
            return

        rule = self._rules[rule_id]
        backup_file = self.backup_dir / f"{rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(rule.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"备份规则到: {backup_file}")

    def _create_default_preset_rules(self):
        """创建默认预置规则库（内部方法）"""
        from .cleanup_rule import ConditionType

        # 定义 5 条常用规则
        preset_rules = [
            {
                'rule_id': 'temp_files_large',
                'rule_name': '大临时文件清理',
                'description': '删除超过 10MB 的临时文件（.tmp, .temp）',
                'rule_type': RuleType.FILE_SIZE.value,
                'conditions': [
                    {
                        'condition_type': ConditionType.FILE_EXTENSION.value,
                        'operator': 'in',
                        'value': ['tmp', 'temp'],
                        'is_case_sensitive': False
                    },
                    {
                        'condition_type': ConditionType.FILE_SIZE.value,
                        'operator': 'greater_than',
                        'value': 10485760,  # 10 MB
                        'is_case_sensitive': False
                    }
                ],
                'action': RuleAction.DELETE.value,
                'is_enabled': True,
                'priority': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'rule_id': 'log_files_old',
                'rule_name': '旧日志文件清理',
                'description': '删除超过 7 天的日志文件（.log）',
                'rule_type': RuleType.DATE_MODIFIED.value,
                'conditions': [
                    {
                        'condition_type': ConditionType.FILE_EXTENSION.value,
                        'operator': 'equals',
                        'value': 'log',
                        'is_case_sensitive': False
                    },
                    {
                        'condition_type': ConditionType.DATE_MODIFIED.value,
                        'operator': 'before',
                        'value': (datetime.now() - timedelta(days=7)).isoformat(),
                        'is_case_sensitive': False
                    }
                ],
                'action': RuleAction.DELETE.value,
                'is_enabled': True,
                'priority': 1,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]

        data = {'rules': preset_rules}

        with open(self.preset_rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("创建默认预置规则库")


# ============================================================================
# 辅助函数
# ============================================================================

def get_common_rules() -> List[CleanupRule]:
    """获取常用清理规则列表

    Returns:
        常用规则列表
    """
    rules = []
    rules.append(create_simple_rule(
        rule_id="common_temp",
        rule_name="临时文件清理",
        description="临时文件和缓存",
        rule_type=RuleType.FILE_EXTENSION,
        condition_type=ConditionType.FILE_EXTENSION,
        operator=RuleOperator.IN,
        value=["tmp", "temp", "cache", "dmp"],
        action=RuleAction.DELETE
    ))

    rules.append(create_simple_rule(
        rule_id="common_log",
        rule_name="日志文件清理",
        description="应用和系统日志",
        rule_type=RuleType.FILE_EXTENSION,
        condition_type=ConditionType.FILE_EXTENSION,
        operator=RuleOperator.EQUALS,
        value="log",
        action=RuleAction.DELETE
    ))

    return rules


def get_scenario_rules(scenario: str) -> List[CleanupRule]:
    """获取场景化规则

    Args:
        scenario: 场景类型（gamer, office, developer, normal）

    Returns:
        规则列表
    """
    rules = []

    if scenario == "gamer":
        rules.append(create_simple_rule(
            rule_id="gamer_cache",
            rule_name="游戏缓存清理",
            description="游戏缓存文件",
            rule_type=RuleType.PATH_PATTERN,
            condition_type=ConditionType.FILE_PATH,
            operator=RuleOperator.CONTAINS,
            value="cache",
            action=RuleAction.DELETE
        ))
    elif scenario == "office":
        rules.append(create_simple_rule(
            rule_id="office_temp",
            rule_name="办公临时文件",
            description="Office 临时文件",
            rule_type=RuleType.FILE_EXTENSION,
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.EQUALS,
            value="tmp",
            action=RuleAction.DELETE
        ))
    elif scenario == "developer":
        rules.append(create_simple_rule(
            rule_id="dev_build_cache",
            rule_name="构建缓存清理",
            description="生成文件和构建缓存",
            rule_type=RuleType.FILE_EXTENSION,
            condition_type=ConditionType.FILE_EXTENSION,
            operator=RuleOperator.IN,
            value=["pyc", "o", "so", "dll"],
            action=RuleAction.DELETE
        ))
    elif scenario == "normal":
        # 普通用户场景：浏览器缓存、下载文件
        rules.append(create_simple_rule(
            rule_id="normal_browser_cache",
            rule_name="浏览器缓存",
            description="浏览器缓存文件",
            rule_type=RuleType.PATH_PATTERN,
            condition_type=ConditionType.FILE_PATH,
            operator=RuleOperator.CONTAINS,
            value="cache",
            action=RuleAction.DELETE
        ))

    return rules
