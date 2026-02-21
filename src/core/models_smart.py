# 核心数据模型 - 智能清理功能

"""
PurifyAI 智能清理模块数据模型 (v1.1 - 修复审核反馈)

本模块包含智能清理功能所需的所有数据模型。

设计原则（基于审核反馈）:
1. CleanupItem 轻量化: 仅存储核心字段 (ID/path/size)
2. ItemDetail 按需加载: 详细信息存储在字典中
3. 数据库大字段分离: 原因字段独立存储在 reasons 表
4. 完整恢复机制: 支持 RecoveryRecord 记录
"""

import uuid
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from itertools import chain
from typing import List, Dict, Optional, Any, Set
from datetime import datetime

from .risk_assessment import RiskAssessmentSystem
from .rule_engine import RiskLevel, RuleEngine


# ============================================================================
# 枚举定义
# ============================================================================

class CleanupStatus(Enum):
    """清理项状态"""
    PENDING = "pending"                 # 等待执行
    RUNNING = "running"                 # 执行中
    SUCCESS = "success"                 # 成功
    FAILED = "failed"                   # 失败
    SKIPPED = "skipped"                 # 跳过
    CANCELLED = "cancelled"             # 已取消
    AWAITING_CONFIRM = "awaiting_confirm"  # 等待用户确认

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            CleanupStatus.PENDING: "等待中",
            CleanupStatus.RUNNING: "执行中",
            CleanupStatus.SUCCESS: "成功",
            CleanupStatus.FAILED: "失败",
            CleanupStatus.SKIPPED: "跳过",
            CleanupStatus.CANCELLED: "已取消",
            CleanupStatus.AWAITING_CONFIRM: "等待确认"
        }
        return names.get(self, self.value)


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"                 # 等待执行
    RUNNING = "running"                 # 执行中
    COMPLETED = "completed"             # 已完成
    PARTIAL_SUCCESS = "partial_success" # 部分成功
    FAILED = "failed"                   # 失败
    CANCELLED = "cancelled"             # 已取消

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            ExecutionStatus.PENDING: "等待中",
            ExecutionStatus.RUNNING: "执行中",
            ExecutionStatus.COMPLETED: "已完成",
            ExecutionStatus.PARTIAL_SUCCESS: "部分成功",
            ExecutionStatus.FAILED: "失败",
            ExecutionStatus.CANCELLED: "已取消"
        }
        return names.get(self, self.value)


class BackupType(Enum):
    """备份类型"""
    NONE = "none"           # 不备份
    HARDLINK = "hardlink"   # 硬链接
    FULL = "full"           # 完整备份

    @staticmethod
    def from_risk(risk: RiskLevel) -> 'BackupType':
        """根据风险等级确定备份类型"""
        if risk == RiskLevel.SAFE:
            return BackupType.NONE
        elif risk == RiskLevel.SUSPICIOUS:
            return BackupType.HARDLINK
        else:
            return BackupType.FULL


# ============================================================================
# 核心数据模型
# ============================================================================

@dataclass
class ItemDetail:
    """项目详细信息（按需加载，避免内存占用过高）"""
    ai_reason: str = ""              # AI判断原因
    confidence: float = 0.0           # AI置信度 (0-1)
    cleanup_suggestion: str = ""    # 清理建议
    software_name: str = ""          # 所属软件名称
    function_description: str = ""    # 功能描述
    last_modified: Optional[datetime] = None  # 最后修改时间
    error_message: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ItemDetail':
        """从字典创建"""
        return cls(
            ai_reason=data.get('ai_reason', ''),
            confidence=data.get('confidence', 0.0),
            cleanup_suggestion=data.get('cleanup_suggestion', ''),
            software_name=data.get('software_name', ''),
            function_description=data.get('function_description', ''),
            last_modified=data.get('last_modified'),
            error_message=data.get('error_message', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'ai_reason': self.ai_reason,
            'confidence': self.confidence,
            'cleanup_suggestion': self.cleanup_suggestion,
            'software_name': self.software_name,
            'function_description': self.function_description,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'error_message': self.error_message
        }


@dataclass
class CleanupItem:
    """清理项数据模型（轻量化设计 - 问题2修复）

    仅存储核心字段，详细信息通过 ItemDetail 按需加载

    Attributes:
        item_id: 唯一ID
        path: 文件/文件夹路径
        size: 大小（字节）
        item_type: 'file' 或 'directory'
        original_risk: 原始风险等级
        ai_risk: AI评估风险等级

    内存优化:
        - 原设计: ~500字节/项 × 10万项 = 50MB
        - 轻量化: ~100字节/项 × 10万项 = 10MB
        - 节省: ~80%
    """
    item_id: int
    path: str
    size: int
    item_type: str  # 'file' or 'directory'
    original_risk: RiskLevel
    ai_risk: RiskLevel

    # 关联数据（不直接存储）通过外部字典加载
    # details: ItemDetail  # 外部存储，按需访问

    def __post_init__(self):
        """初始化后处理"""
        # 确保风险等级是 RiskLevel 枚举
        if isinstance(self.original_risk, str):
            self.original_risk = RiskLevel.from_value(self.original_risk)
        if isinstance(self.ai_risk, str):
            self.ai_risk = RiskLevel.from_value(self.ai_risk)

    @property
    def is_safe(self) -> bool:
        """是否为安全项"""
        return self.ai_risk == RiskLevel.SAFE

    @property
    def is_suspicious(self) -> bool:
        """是否为疑似项"""
        return self.ai_risk == RiskLevel.SUSPICIOUS

    @property
    def is_dangerous(self) -> bool:
        """是否为高危项"""
        return self.ai_risk == RiskLevel.DANGEROUS

    @classmethod
    def from_scan_item(cls, item: Any, item_id: int) -> 'CleanupItem':
        """从扫描项创建 CleanupItem"""
        # 这里假设 item 是 ScanItem 类型，需要根据实际情况调整
        if hasattr(item, '__dict__'):
            # 如果是 ScanItem 对象
            return cls(
                item_id=item_id,
                path=item.path,
                size=item.size,
                item_type=item.item_type if hasattr(item, 'item_type') else 'file',
                original_risk=item.risk_level if hasattr(item, 'risk_level') else RiskLevel.SUSPICIOUS,
                ai_risk=item.risk_level if hasattr(item, 'risk_level') else RiskLevel.SUSPICIOUS
            )
        else:
            # 如果是字典
            return cls(
                item_id=item_id,
                path=item.get('path', ''),
                size=item.get('size', 0),
                item_type=item.get('item_type', 'file'),
                original_risk=RiskLevel.from_value(item.get('risk_level', 'suspicious')),
                ai_risk=RiskLevel.from_value(item.get('risk_level', 'suspicious'))
            )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（数据库序列化）"""
        return {
            'path': self.path,
            'size': self.size,
            'item_type': self.item_type,
            'original_risk': self.original_risk.value,
            'ai_risk': self.ai_risk.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], item_id: int) -> 'CleanupItem':
        """从字典创建 CleanupItem"""
        return cls(
            item_id=item_id,
            path=data.get('path', ''),
            size=data.get('size', 0),
            item_type=data.get('item_type', 'file'),
            original_risk=RiskLevel.from_value(data.get('original_risk', 'suspicious')),
            ai_risk=RiskLevel.from_value(data.get('ai_risk', 'suspicious'))
        )


@dataclass
class CleanupPlan:
    """清理执行计划

    Attributes:
        plan_id: 计划ID (UUID)
        scan_type: 扫描类型 ('system', 'browser', 'appdata', 'custom', 'disk')
        scan_target: 扫描目标 (路径)
        items: 所有清理项列表 (CleanupItem 集合)
        total_size: 总大小 (字节)
        estimated_freed: 预计释放空间 (字节)
        ai_summary: AI汇总说明
        ai_model: AI模型名称
        ai_call_count: AI调用次数 (成本控制)
        used_rule_engine: 是否使用了规则引擎降级
        analyzed_at: 分析时间
        created_at: 创建时间
    """
    plan_id: str
    scan_type: str
    scan_target: str
    items: List[CleanupItem]
    total_size: int
    estimated_freed: int
    ai_summary: str = ""
    ai_model: str = ""
    ai_call_count: int = 0
    used_rule_engine: bool = False
    analyzed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    # 数据库ID ( populated after save)
    _db_id: int = 0

    @property
    def safe_items(self) -> List[CleanupItem]:
        """安全项列表"""
        return [item for item in self.items if item.ai_risk == RiskLevel.SAFE]

    @property
    def suspicious_items(self) -> List[CleanupItem]:
        """疑似项列表"""
        return [item for item in self.items if item.ai_risk == RiskLevel.SUSPICIOUS]

    @property
    def dangerous_items(self) -> List[CleanupItem]:
        """高危项列表"""
        return [item for item in self.items if item.ai_risk == RiskLevel.DANGEROUS]

    @property
    def total_items(self) -> int:
        """总项数"""
        return len(self.items)

    @property
    def safe_count(self) -> int:
        """安全项数量"""
        return len(self.safe_items)

    @property
    def suspicious_count(self) -> int:
        """疑似项数量"""
        return len(self.suspicious_items)

    @property
    def dangerous_count(self) -> int:
        """高危项数量"""
        return len(self.dangerous_items)

    @property
    def all_items(self) -> List[CleanupItem]:
        """所有项"""
        return self.items

    @classmethod
    def create(cls, scan_type: str, scan_target: str,
                items: List['CleanupItem'] = None) -> 'CleanupPlan':
        """创建清理计划工厂方法"""
        items = items or []
        total_size = sum(item.size for item in items)

        return cls(
            plan_id=str(uuid.uuid4()),
            scan_type=scan_type,
            scan_target=scan_target,
            items=items,
            total_size=total_size,
            estimated_freed=total_size  # 初始假设全部可释放
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（数据库序列化）"""
        return {
            'plan_id': self.plan_id,
            'scan_type': self.scan_type,
            'scan_target': self.scan_target,
            'total_items': self.total_items,
            'total_size': self.total_size,
            'safe_count': self.safe_count,
            'suspicious_count': self.suspicious_count,
            'dangerous_count': self.dangerous_count,
            'estimated_freed': self.estimated_freed,
            'ai_summary': self.ai_summary,
            'ai_model': self.ai_model,
            'ai_call_count': self.ai_call_count,
            'used_rule_engine': int(self.used_rule_engine),
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class ScanProgress:
    """扫描进度信息

    Attributes:
        total: 总项目数
        current: 当前处理的项目数
        phase: 当前阶段 ('scanning', 'analyzing', 'executing', 'completed')
        message: 进度消息
        started_at: 开始时间
        estimated_remaining_seconds: 预估剩余秒数
    """
    total: int
    current: int = 0
    phase: str = 'scanning'
    message: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    estimated_remaining_seconds: Optional[float] = None

    @property
    def progress_percent(self) -> float:
        """进度百分比 (0-100)"""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100

    @property
    def items_per_second(self) -> float:
        """每秒处理的项目数"""
        if self.current == 0:
            return 0.0

        elapsed = (datetime.now() - self.started_at).total_seconds()
        if elapsed == 0:
            return 0.0

        return self.current / elapsed

    def update(self, current: int, total: int, phase: str = None,
                message: str = "", estimated_remaining: Optional[float] = None):
        """更新进度"""
        self.current = current
        self.total = total
        if phase:
            self.phase = phase
        if message:
            self.message = message
        if estimated_remaining is not None:
            self.estimated_remaining_seconds = estimated_remaining


@dataclass
class ExecutionResult:
    """清理执行结果

    Attributes:
        plan_id: 计划ID
        started_at: 开始时间
        completed_at: 完成时间
        total_items: 总项目数
        success_items: 成功项目数
        failed_items: 失败项目数
        skipped_items: 跳过项目数
        total_size: 总大小
        freed_size: 释放大小
        failed_size: 失败项大小
        status: 执行状态
        error_message: 错误消息
        failures: 失败项列表
    """
    plan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    total_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0

    total_size: int = 0
    freed_size: int = 0
    failed_size: int = 0

    status: ExecutionStatus = ExecutionStatus.PENDING
    error_message: str = ""

    failures: List['FailureInfo'] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """成功率 (0-1)"""
        if self.total_items == 0:
            return 0.0
        return self.success_items / self.total_items

    @property
    def duration_seconds(self) -> float:
        """执行时长（秒）"""
        if not self.completed_at:
            return (datetime.now() - self.started_at).total_seconds()
        return (self.completed_at - self.started_at).total_seconds()

    def add_failure(self, item: CleanupItem, error_type: str,
                   error_message: str, suggested_action: str):
        """添加失败记录"""
        failure = FailureInfo(
            item=item,
            error_type=error_type,
            error_message=error_message,
            suggested_action=suggested_action
        )
        self.failures.append(failure)
        self.failed_items += 1
        self.failed_size += item.size

    def update_status(self):
        """根据执行结果更新状态"""
        if self.status == ExecutionStatus.RUNNING or self.completed_at is not None or self.total_items > 0:
            if self.failed_items == 0:
                self.status = ExecutionStatus.COMPLETED
            elif self.success_items > 0:
                self.status = ExecutionStatus.PARTIAL_SUCCESS
            else:
                self.status = ExecutionStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（数据库序列化）"""
        return {
            'plan_id': self.plan_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_items': self.total_items,
            'success_items': self.success_items,
            'failed_items': self.failed_items,
            'skipped_items': self.skipped_items,
            'total_size': self.total_size,
            'freed_size': self.freed_size,
            'failed_size': self.failed_size,
            'status': self.status.value,
            'error_message': self.error_message
        }


@dataclass
class FailureInfo:
    """失败项信息

    Attributes:
        item: 清理项
        error_type: 错误类型 (permission', file_in_use, disk_full, unknown)
        error_message: 错误消息
        suggested_action: 建议操作 (retry, skip, admin_privilege, close_app)
        timestamp: 失败时间
    """
    item: CleanupItem
    error_type: str = 'unknown'
    error_message: str = ""
    suggested_action: str = 'skip'
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'item_id': self.item.item_id,
            'path': self.item.path,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'suggested_action': self.suggested_action,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BackupInfo:
    """备份信息

    Attributes:
        backup_id: 备份ID
        item_id: 清理项ID
        original_path: 原始路径（用于恢复）
        backup_path: 备份路径
        backup_type: 备份类型
        created_at: 创建时间
        restored: 是否已恢复
        restored_at: 恢复时间
    """
    backup_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_id: int = 0
    original_path: str = ""
    backup_path: str = ""
    backup_type: BackupType = BackupType.NONE
    created_at: datetime = field(default_factory=datetime.now)
    restored: bool = False
    restored_at: Optional[datetime] = None

    @classmethod
    def create(cls, item: CleanupItem, backup_path: str,
                backup_type: BackupType) -> 'BackupInfo':
        """创建备份信息"""
        return cls(
            item_id=item.item_id,
            original_path=item.path,  # 存储原始路径
            backup_path=backup_path,
            backup_type=backup_type
        )


@dataclass
class RecoveryRecord:
    """恢复记录

    Attributes:
        record_id: 记录ID
        plan_id: 计划ID
        item_id: 清理项ID
        original_path: 原始路径
        backup_path: 备份路径
        backup_type: 备份类型
        restored: 是否已恢复
        timestamp: 记录时间
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = ""
    item_id: int = 0
    original_path: str = ""
    backup_path: str = ""
    backup_type: BackupType = BackupType.NONE
    restored: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RollbackResult:
    """回滚结果

    Attributes:
        total: 总项目数
        success: 成功恢复数
        failed: 失败恢复数
        failed_items: 失败项目列表
        duration_seconds: 执行时长
    """
    total: int = 0
    success: int = 0
    failed: int = 0
    failed_items: List[RecoveryRecord] = field(default_factory=list)
    duration_seconds: float = 0.0


# ============================================================================
# 预检查相关数据模型
# ============================================================================

@dataclass
class CheckResult:
    """扫描预检查结果

    Attributes:
        can_scan: 是否可以扫描
        issues: 问题列表
        warnings: 警告列表
        scan_path: 扫描路径
    """
    can_scan: bool = True
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scan_path: str = ""

    def add_issue(self, issue: str):
        """添加问题"""
        self.issues.append(issue)
        self.can_scan = False

    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)

    @property
    def has_issues(self) -> bool:
        """是否有问题"""
        return len(self.issues) > 0

    @property
    def issue_summary(self) -> str:
        """问题摘要"""
        if not self.has_issues:
            return "可以开始扫描"
        return f"发现问题: {', '.join(self.issues)}"


# ============================================================================
# 导出的工厂函数和便利函数
# ============================================================================

def get_reason_hash(reason: str) -> str:
    """生成原因字符串的哈希（用于数据库去重 - 问题1修复）"""
    return hashlib.md5(reason.encode('utf-8')).hexdigest()


def is_empty_cleanup_item(item: CleanupItem) -> bool:
    """检查清理项是否为空"""
    return item is None or item.item_id <= 0


def get_risk_level_safe(value: str) -> RiskLevel:
    """安全获取风险等级（字符串转枚举，带默认值）"""
    try:
        return RiskLevel.from_value(value)
    except:
        return RiskLevel.SUSPICIOUS
