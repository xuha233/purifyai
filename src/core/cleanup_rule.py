# -*- coding: utf-8 -*-
"""
清理规则类定义 (Cleanup Rule Classes)

定义清理规则的数据结构，包括规则类型、条件、动作等

作者: 小午 🦁
创建时间: 2026-02-24
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import os
import re
import json
import mimetypes

from pathlib import Path


# ============================================================================
# 枚举定义
# ============================================================================


class RuleType(Enum):
    """规则类型"""

    FILE_EXTENSION = "file_extension"  # 文件扩展名匹配
    FILE_PATTERN = "file_pattern"  # 文件名模式匹配（通配符）
    REGEX = "regex"  # 正则表达式匹配
    FILE_SIZE = "file_size"  # 文件大小匹配
    DATE_CREATED = "date_created"  # 创建日期匹配
    DATE_MODIFIED = "date_modified"  # 修改日期匹配
    PATH_PATTERN = "path_pattern"  # 路径模式匹配


class ConditionType(Enum):
    """条件类型"""

    FILE_NAME = "file_name"
    FILE_EXTENSION = "file_extension"
    FILE_SIZE = "file_size"
    FILE_PATH = "file_path"
    DATE_CREATED = "date_created"
    DATE_MODIFIED = "date_modified"
    FILE_CONTENT = "file_content"


class RuleOperator(Enum):
    """规则操作符"""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # 正则匹配
    IN = "in"
    NOT_IN = "not_in"
    BEFORE = "before"
    AFTER = "after"


class RuleAction(Enum):
    """规则动作"""

    DELETE = "delete"
    MOVE_TO = "move_to"
    ARCHIVE = "archive"
    LOG_ONLY = "log_only"


# ============================================================================
# 数据类定义
# ============================================================================


@dataclass
class FileInfo:
    """文件信息类

    表示文件的元数据信息，用于规则匹配
    """

    path: str  # 文件完整路径
    name: str  # 文件名（含扩展名）
    extension: str  # 文件扩展名（不含点）
    size: int  # 文件大小（字节）
    created_at: datetime  # 创建时间
    modified_at: datetime  # 修改时间
    is_directory: bool = False  # 是否为目录

    @classmethod
    def from_path(cls, file_path: str) -> Optional["FileInfo"]:
        """从文件路径创建 FileInfo

        Args:
            file_path: 文件路径

        Returns:
            FileInfo 对象，如果文件不存在或无法访问则返回 None
        """
        try:
            path_obj = Path(file_path)

            if not path_obj.exists():
                return None

            # 获取文件状态
            stat = path_obj.stat()

            # 分离文件名和扩展名
            file_name = path_obj.name
            ext = path_obj.suffix.lstrip(".")

            return cls(
                path=str(path_obj.absolute()),
                name=file_name,
                extension=ext,
                size=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                is_directory=path_obj.is_dir(),
            )
        except (OSError, ValueError) as e:
            print(f"[FileInfo] 无法解析文件 {file_path}: {e}")
            return None

    def to_dict(self) -> Dict:
        """序列化为字典

        Returns:
            字典表示
        """
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size": self.size,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "is_directory": self.is_directory,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FileInfo":
        """从字典反序列化

        Args:
            data: 字典数据

        Returns:
            FileInfo 对象
        """
        return cls(
            path=data["path"],
            name=data["name"],
            extension=data["extension"],
            size=data["size"],
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]),
            is_directory=data["is_directory"],
        )


@dataclass
class RuleCondition:
    """规则条件类

    定义规则的匹配条件
    """

    condition_type: ConditionType  # 条件类型
    operator: RuleOperator  # 操作符
    value: Union[str, int, float, List[str], datetime]  # 条件值
    is_case_sensitive: bool = False  # 是否区分大小写

    def evaluate(self, target_file: FileInfo) -> bool:
        """评估条件是否匹配

        Args:
            target_file: 目标文件信息

        Returns:
            是否匹配条件
        """
        try:
            if self.condition_type == ConditionType.FILE_NAME:
                return self._evaluate_string(target_file.name)
            elif self.condition_type == ConditionType.FILE_EXTENSION:
                return self._evaluate_string(target_file.extension)
            elif self.condition_type == ConditionType.FILE_SIZE:
                return self._evaluate_number(target_file.size)
            elif self.condition_type == ConditionType.FILE_PATH:
                return self._evaluate_string(target_file.path)
            elif self.condition_type == ConditionType.DATE_CREATED:
                return self._evaluate_datetime(target_file.created_at)
            elif self.condition_type == ConditionType.DATE_MODIFIED:
                return self._evaluate_datetime(target_file.modified_at)
            elif self.condition_type == ConditionType.FILE_CONTENT:
                # 文件内容匹配需要特殊处理
                return self._evaluate_file_content(target_file.path)
            else:
                print(f"[RuleCondition] 未知的条件类型: {self.condition_type}")
                return False
        except Exception as e:
            print(f"[RuleCondition] 评估条件时出错: {e}")
            return False

    def _evaluate_string(self, target: str) -> bool:
        """评估字符串条件"""
        if not isinstance(self.value, str):
            return False

        compare_to = self.value if self.is_case_sensitive else self.value.lower()
        compare_target = target if self.is_case_sensitive else target.lower()

        if self.operator == RuleOperator.EQUALS:
            return compare_target == compare_to
        elif self.operator == RuleOperator.NOT_EQUALS:
            return compare_target != compare_to
        elif self.operator == RuleOperator.CONTAINS:
            return compare_to in compare_target
        elif self.operator == RuleOperator.STARTS_WITH:
            return compare_target.startswith(compare_to)
        elif self.operator == RuleOperator.ENDS_WITH:
            return compare_target.endswith(compare_to)
        elif self.operator == RuleOperator.MATCHES:
            try:
                pattern = compare_to
                flags = 0 if self.is_case_sensitive else re.IGNORECASE
                return bool(re.search(pattern, compare_target, flags))
            except re.error:
                return False
        elif self.operator == RuleOperator.IN:
            if not isinstance(self.value, list):
                return False
            return any(v.lower() == compare_target for v in self.value)
        elif self.operator == RuleOperator.NOT_IN:
            if not isinstance(self.value, list):
                return False
            return all(v.lower() != compare_target for v in self.value)
        else:
            return False

    def _evaluate_number(self, target: Union[int, float]) -> bool:
        """评估数值条件"""
        if not isinstance(self.value, (int, float)):
            return False

        if self.operator == RuleOperator.EQUALS:
            return target == self.value
        elif self.operator == RuleOperator.NOT_EQUALS:
            return target != self.value
        elif self.operator == RuleOperator.GREATER_THAN:
            return target > self.value
        elif self.operator == RuleOperator.LESS_THAN:
            return target < self.value
        elif self.operator == RuleOperator.GREATER_EQUAL:
            return target >= self.value
        elif self.operator == RuleOperator.LESS_EQUAL:
            return target <= self.value
        else:
            return False

    def _evaluate_datetime(self, target: datetime) -> bool:
        """评估日期时间条件"""
        if isinstance(self.value, (int, float)):
            # 假设值是秒数（Unix 时间戳）
            compare_value = datetime.fromtimestamp(self.value)
        elif isinstance(self.value, str):
            try:
                compare_value = datetime.fromisoformat(self.value)
            except ValueError:
                return False
        else:
            return False

        if self.operator == RuleOperator.EQUALS:
            return target == compare_value
        elif self.operator == RuleOperator.NOT_EQUALS:
            return target != compare_value
        elif self.operator == RuleOperator.BEFORE:
            return target < compare_value
        elif self.operator == RuleOperator.AFTER:
            return target > compare_value
        elif self.operator == RuleOperator.GREATER_THAN:
            return target > compare_value
        elif self.operator == RuleOperator.LESS_THAN:
            return target < compare_value
        else:
            return False

    def _evaluate_file_content(self, file_path: str) -> bool:
        """评估文件内容条件"""
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return False

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if self.operator == RuleOperator.CONTAINS:
                return str(self.value) in content
            elif self.operator == RuleOperator.MATCHES:
                pattern = str(self.value)
                flags = 0 if self.is_case_sensitive else re.IGNORECASE
                return bool(re.search(pattern, content, flags))
            else:
                return False
        except (OSError, IOError):
            return False

    def to_dict(self) -> Dict:
        """序列化为字典

        Returns:
            字典表示
        """
        value_to_serialize = self.value
        if isinstance(self.value, datetime):
            value_to_serialize = self.value.isoformat()
        elif isinstance(self.value, list):
            value_to_serialize = [
                v.isoformat() if isinstance(v, datetime) else v for v in self.value
            ]

        return {
            "condition_type": self.condition_type.value,
            "operator": self.operator.value,
            "value": value_to_serialize,
            "is_case_sensitive": self.is_case_sensitive,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "RuleCondition":
        """从字典反序列化

        Args:
            data: 字典数据

        Returns:
            RuleCondition 对象
        """
        condition_type = ConditionType(data["condition_type"])
        operator = RuleOperator(data["operator"])
        raw_value = data["value"]
        is_case_sensitive = data.get("is_case_sensitive", False)

        value = raw_value

        if condition_type in (ConditionType.DATE_CREATED, ConditionType.DATE_MODIFIED):
            if isinstance(raw_value, str):
                try:
                    value = datetime.fromisoformat(raw_value)
                except ValueError:
                    value = raw_value
            elif isinstance(raw_value, list):
                value = []
                for v in raw_value:
                    if isinstance(v, str):
                        try:
                            value.append(datetime.fromisoformat(v))
                        except ValueError:
                            value.append(v)
                    else:
                        value.append(v)

        return cls(
            condition_type=condition_type,
            operator=operator,
            value=value,
            is_case_sensitive=is_case_sensitive,
        )


@dataclass
class ActionResult:
    """规则动作执行结果

    表示规则动作执行的结果
    """

    success: bool  # 是否成功
    action: RuleAction  # 执行的动作
    file_path: str  # 文件路径
    message: str = ""  # 结果消息
    error: Optional[str] = None  # 错误信息（如果有）

    def to_dict(self) -> Dict:
        """序列化为字典

        Returns:
            字典表示
        """
        return {
            "success": self.success,
            "action": self.action.value,
            "file_path": self.file_path,
            "message": self.message,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ActionResult":
        """从字典反序列化

        Args:
            data: 字典数据

        Returns:
            ActionResult 对象
        """
        return cls(
            success=data["success"],
            action=RuleAction(data["action"]),
            file_path=data["file_path"],
            message=data.get("message", ""),
            error=data.get("error"),
        )


@dataclass
class CleanupRule:
    """清理规则类

    定义一个完整的清理规则
    """

    rule_id: str  # 规则唯一标识符
    rule_name: str  # 规则名称
    description: str  # 规则描述
    rule_type: RuleType  # 规则类型
    conditions: List[RuleCondition]  # 条件列表
    action: RuleAction  # 执行动作
    is_enabled: bool = True  # 是否启用
    priority: int = 0  # 优先级（数字越小优先级越高）
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间

    def to_dict(self) -> Dict:
        """序列化为字典

        Returns:
            字典表示
        """
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.value,
            "is_enabled": self.is_enabled,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CleanupRule":
        """从字典反序列化

        Args:
            data: 字典数据

        Returns:
            CleanupRule 对象
        """

        def parse_datetime(value):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    return None
            return value

        return cls(
            rule_id=data["rule_id"],
            rule_name=data["rule_name"],
            description=data["description"],
            rule_type=RuleType(data["rule_type"]),
            conditions=[RuleCondition.from_dict(c) for c in data["conditions"]],
            action=RuleAction(data["action"]),
            is_enabled=data.get("is_enabled", True),
            priority=data.get("priority", 0),
            created_at=parse_datetime(data.get("created_at")) or datetime.now(),
            updated_at=parse_datetime(data.get("updated_at")) or datetime.now(),
        )

    def matches(self, file_info: FileInfo) -> bool:
        """检查文件是否匹配规则的所有条件

        Args:
            file_info: 文件信息对象

        Returns:
            bool: 是否匹配
        """
        if not self.is_enabled:
            return False

        return all(condition.evaluate(file_info) for condition in self.conditions)


# ============================================================================
# 辅助函数
# ============================================================================


def convert_size_to_bytes(size: Union[str, int, float]) -> int:
    """将大小字符串转换为字节

    Args:
        size: 大小字符串（如 "10 MB"）或数字（假设为字节）

    Returns:
        字节数
    """
    if isinstance(size, (int, float)):
        return int(size)

    if isinstance(size, str):
        size_str = size.strip().upper()

        # 单位到字节的映射
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

        # 提取数值和单位
        match = re.match(r"^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)$", size_str)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            return int(value * units[unit])
        else:
            # 默认为字节
            try:
                return int(size)
            except ValueError:
                return 0

    return 0


def convert_bytes_to_size(size_bytes: int, unit: str = "MB") -> float:
    """将字节转换为指定单位

    Args:
        size_bytes: 字节数
        unit: 目标单位（B, KB, MB, GB, TB）

    Returns:
        转换后的数值
    """
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

    divisor = units.get(unit.upper(), 1024**2)
    return size_bytes / divisor
