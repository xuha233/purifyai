# -*- coding: utf-8 -*-
"""
规则引擎 (Rule Engine)

实现规则的加载、匹配和执行逻辑

作者: 小午 🦁
创建时间: 2026-02-24
"""

from __future__ import annotations

from typing import List, Optional, Dict, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import os
import shutil
import logging
from pathlib import Path

from .cleanup_rule import (
    CleanupRule, RuleCondition, FileInfo, ActionResult,
    RuleAction, RuleOperator, RuleType, ConditionType,
    convert_size_to_bytes
)

logger = logging.getLogger(__name__)


# ============================================================================
# 风险评估规则兼容类（向后兼容）
# ============================================================================

class RiskLevel(Enum):
    """风险等级枚举（用于风险评估系统）"""
    SAFE = "safe"           # 安全
    LOW = "low"             # 低风险
    MEDIUM = "medium"       # 中风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"   # 危险
    DANGEROUS = "dangerous" # 危险（别名）
    SUSPICIOUS = "suspicious"  # 可疑


@dataclass
class Rule:
    """风险评估规则（用于风险评估系统）"""
    rule_id: str
    name: str
    risk_level: RiskLevel
    condition: str  # 条件表达式
    pattern: Optional[str] = None  # 匹配模式
    priority: int = 0

    def match(self, path: str, size: int = 0, last_accessed: Optional[datetime] = None) -> bool:
        """检查是否匹配规则"""
        # 简单的前缀匹配实现
        if self.pattern:
            return path.startswith(self.pattern)
        return False


# ============================================================================
# 规则引擎类
# ============================================================================

class RuleEngine:
    """规则引擎类

    负责加载规则、评估文件匹配、执行规则动作
    """

    def __init__(self):
        """初始化规则引擎"""
        self._rules: Dict[str, CleanupRule] = {}
        self._actions_handlers: Dict[RuleAction, Callable] = {
            RuleAction.DELETE: self._delete_file,
            RuleAction.MOVE_TO: self._move_file,
            RuleAction.ARCHIVE: self._archive_file,
            RuleAction.LOG_ONLY: self._log_file
        }

    def load_rules(self, rules: List[CleanupRule]) -> int:
        """加载规则到引擎

        Args:
            rules: 规则列表

        Returns:
            成功加载的规则数
        """
        count = 0
        for rule in rules:
            if rule.rule_id not in self._rules:
                self._rules[rule.rule_id] = rule
                count += 1
            else:
                logger.warning(f"规则 ID 重复，已跳过: {rule.rule_id}")

        logger.info(f"加载了 {count} 条规则")
        return count

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

    def match_file(self, file_path: str, rule_ids: Optional[List[str]] = None) -> List[CleanupRule]:
        """查找匹配文件的规则

        Args:
            file_path: 文件路径
            rule_ids: 可选，仅在指定规则中查找

        Returns:
            匹配的规则列表，按优先级排序
        """
        # 创建文件信息
        file_info = FileInfo.from_path(file_path)
        if file_info is None:
            return []

        # 确定要检查的规则
        rules_to_check = []
        if rule_ids:
            for rule_id in rule_ids:
                rule = self.get_rule(rule_id)
                if rule and rule.is_enabled:
                    rules_to_check.append(rule)
        else:
            rules_to_check = self.list_rules(enabled_only=True)

        # 评估匹配
        matched_rules = []
        for rule in rules_to_check:
            if self._evaluate_rule(file_info, rule):
                matched_rules.append(rule)

        # 按优先级排序
        matched_rules.sort(key=lambda r: r.priority)
        return matched_rules

    def _evaluate_rule(self, file_info: FileInfo, rule: CleanupRule) -> bool:
        """评估规则是否匹配文件

        Args:
            file_info: 文件信息
            rule: 清理规则

        Returns:
            是否匹配
        """
        try:
            # 空条件列表视为不匹配
            if not rule.conditions:
                return False

            # 评估所有条件（默认为 AND 逻辑，所有条件都必须满足）
            for condition in rule.conditions:
                if not condition.evaluate(file_info):
                    return False

            return True
        except Exception as e:
            logger.error(f"评估规则 {rule.rule_id} 时出错: {e}")
            return False

    def evaluate_condition(self, file_info: FileInfo, condition: RuleCondition) -> bool:
        """评估单个条件

        Args:
            file_info: 文件信息
            condition: 规则条件

        Returns:
            是否匹配条件
        """
        return condition.evaluate(file_info)

    def execute_action(self, file_path: str, action: RuleAction, **action_params) -> ActionResult:
        """执行规则动作

        Args:
            file_path: 文件路径
            action: 规则动作
            **action_params: 动作参数（如目标路径、压缩格式等）

        Returns:
            ActionResult 对象
        """
        handler = self._actions_handlers.get(action)
        if handler is None:
            return ActionResult(
                success=False,
                action=action,
                file_path=file_path,
                message=f"未知的动作类型: {action.value}",
                error="UNKNOWN_ACTION"
            )

        try:
            result = handler(file_path, **action_params)
            return result
        except Exception as e:
            return ActionResult(
                success=False,
                action=action,
                file_path=file_path,
                message=f"执行动作失败: {e}",
                error=str(e)
            )

    def execute_rule(self, file_path: str, rule: CleanupRule) -> ActionResult:
        """执行规则（匹配 + 执行动作）

        Args:
            file_path: 文件路径
            rule: 清理规则

        Returns:
            ActionResult 对象
        """
        # 检查规则是否启用
        if not rule.is_enabled:
            return ActionResult(
                success=False,
                action=rule.action,
                file_path=file_path,
                message="规则未启用",
                error="RULE_DISABLED"
            )

        # 评估匹配
        if not self.match_file(file_path, [rule.rule_id]):
            return ActionResult(
                success=False,
                action=rule.action,
                file_path=file_path,
                message="文件不匹配规则条件",
                error="NOT_MATCHED"
            )

        # 执行动作
        return self.execute_action(file_path, rule.action)

    def batch_execute(self, file_paths: List[str], rule_ids: Optional[List[str]] = None) -> Dict[str, ActionResult]:
        """批量执行规则

        Args:
            file_paths: 文件路径列表
            rule_ids: 可选，仅使用指定规则

        Returns:
            文件路径到 ActionResult 的映射
        """
        results = {}

        for file_path in file_paths:
            # 查找匹配的规则
            matched_rules = self.match_file(file_path, rule_ids)

            if not matched_rules:
                # 没有匹配的规则，记录
                results[file_path] = ActionResult(
                    success=False,
                    action=RuleAction.LOG_ONLY,
                    file_path=file_path,
                    message="没有匹配的规则"
                )
                continue

            # 执行第一个匹配的规则
            rule = matched_rules[0]
            result = self.execute_rule(file_path, rule)
            results[file_path] = result

        return results

    # ------------------------------------------------------------------------
    # 动作处理器（私有方法）
    # ------------------------------------------------------------------------

    def _delete_file(self, file_path: str, **kwargs) -> ActionResult:
        """删除文件

        Args:
            file_path: 文件路径
            **kwargs: 未使用的参数

        Returns:
            ActionResult 对象
        """
        try:
            if not os.path.exists(file_path):
                return ActionResult(
                    success=False,
                    action=RuleAction.DELETE,
                    file_path=file_path,
                    message="文件不存在",
                    error="FILE_NOT_FOUND"
                )

            os.remove(file_path)
            logger.info(f"已删除文件: {file_path}")

            return ActionResult(
                success=True,
                action=RuleAction.DELETE,
                file_path=file_path,
                message=f"已删除文件"
            )
        except OSError as e:
            return ActionResult(
                success=False,
                action=RuleAction.DELETE,
                file_path=file_path,
                message=f"删除失败: {e}",
                error=str(e)
            )

    def _move_file(self, file_path: str, target_path: str = "", **kwargs) -> ActionResult:
        """移动文件到目标路径

        Args:
            file_path: 文件路径
            target_path: 目标路径
            **kwargs: 未使用的参数

        Returns:
            ActionResult 对象
        """
        try:
            if not os.path.exists(file_path):
                return ActionResult(
                    success=False,
                    action=RuleAction.MOVE_TO,
                    file_path=file_path,
                    message="文件不存在",
                    error="FILE_NOT_FOUND"
                )

            # 使用 kwargs 中的 target_path 或默认值
            if not target_path:
                target_path = kwargs.get('target_path', "")

            if not target_path:
                return ActionResult(
                    success=False,
                    action=RuleAction.MOVE_TO,
                    file_path=file_path,
                    message="未指定目标路径",
                    error="NO_TARGET_PATH"
                )

            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # 移动文件
            shutil.move(file_path, target_path)
            logger.info(f"已移动文件 {file_path} -> {target_path}")

            return ActionResult(
                success=True,
                action=RuleAction.MOVE_TO,
                file_path=file_path,
                message=f"已移动到 {target_path}"
            )
        except OSError as e:
            return ActionResult(
                success=False,
                action=RuleAction.MOVE_TO,
                file_path=file_path,
                message=f"移动失败: {e}",
                error=str(e)
            )

    def _archive_file(self, file_path: str, archive_path: Optional[str] = None, **kwargs) -> ActionResult:
        """归档文件（压缩）

        Args:
            file_path: 文件路径
            archive_path: 归档文件路径（默认：file_path.zip）
            **kwargs: 未使用的参数

        Returns:
            ActionResult 对象
        """
        try:
            if not os.path.exists(file_path):
                return ActionResult(
                    success=False,
                    action=RuleAction.ARCHIVE,
                    file_path=file_path,
                    message="文件不存在",
                    error="FILE_NOT_FOUND"
                )

            # 使用 kwargs 中的 archive_path 或生成默认路径
            if archive_path is None:
                archive_path = kwargs.get('archive_path', "")
                if not archive_path:
                    archive_path = f"{file_path}.zip"

            # 创建归档
            shutil.make_archive(
                archive_path.replace('.zip', ''),
                'zip',
                os.path.dirname(file_path),
                os.path.basename(file_path)
            )

            logger.info(f"已归档文件 {file_path} -> {archive_path}")

            return ActionResult(
                success=True,
                action=RuleAction.ARCHIVE,
                file_path=file_path,
                message=f"已归档到 {archive_path}"
            )
        except OSError as e:
            return ActionResult(
                success=False,
                action=RuleAction.ARCHIVE,
                file_path=file_path,
                message=f"归档失败: {e}",
                error=str(e)
            )

    def _log_file(self, file_path: str, **kwargs) -> ActionResult:
        """仅记录文件信息（不删除）

        Args:
            file_path: 文件路径
            **kwargs: 未使用的参数

        Returns:
            ActionResult 对象
        """
        logger.info(f"[LOG_ONLY] 文件: {file_path}")

        return ActionResult(
            success=True,
            action=RuleAction.LOG_ONLY,
            file_path=file_path,
            message="已记录文件信息"
        )


# ============================================================================

def get_rule_engine() -> RiskLevel:
    """获取默认风险评估等级（向后兼容）"""
    return RiskLevel.SAFE

# ============================================================================
# 辅助函数
# ============================================================================

def create_simple_rule(
    rule_id: str,
    rule_name: str,
    description: str,
    rule_type: RuleType,
    condition_type: ConditionType,
    operator: RuleOperator,
    value: Union[str, int, float],
    action: RuleAction
) -> CleanupRule:
    """创建简单规则（单条件）

    Args:
        rule_id: 规则 ID
        rule_name: 规则名称
        description: 规则描述
        rule_type: 规则类型
        condition_type: 条件类型
        operator: 操作符
        value: 条件值
        action: 动作

    Returns:
        CleanupRule 对象
    """
    condition = RuleCondition(
        condition_type=condition_type,
        operator=operator,
        value=value
    )

    return CleanupRule(
        rule_id=rule_id,
        rule_name=rule_name,
        description=description,
        rule_type=rule_type,
        conditions=[condition],
        action=action
    )
