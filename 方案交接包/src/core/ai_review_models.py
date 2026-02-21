"""
AI复核功能模块 - 数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from core.rule_engine import RiskLevel


class ReviewDecision(Enum):
    """人工审核决策"""
    KEEP = "keep"           # 保留
    DELETE = "delete"       # 删除
    SKIP = "skip"           # 跳过

    @classmethod
    def from_str(cls, value: str):
        """从字符串转换

        Args:
            value: 字符串值

        Returns:
            ReviewDecision
        """
        value_map = {
            'keep': cls.KEEP,
            'delete': cls.DELETE,
            'skip': cls.SKIP
        }
        return value_map.get(value.lower(), cls.SKIP)


@dataclass
class AIReviewResult:
    """AI复核结果"""
    item_path: str                      # 项目路径
    original_risk: RiskLevel           # 原始风险等级
    ai_risk: RiskLevel                 # AI评估后的风险等级
    confidence: float                  # 置信度 0.0-1.0
    function_description: str          # 功能描述
    software_name: str                 # 所属软件名称
    risk_reason: str                   # 风险原因
    cleanup_suggestion: str            # 清理建议
    ai_reasoning: Optional[str] = None # AI推理过程（完整）
    review_timestamp: Optional[datetime] = None # 复核时间
    retry_count: int = 0               # 重试次数
    is_valid: bool = True              # 结果是否有效（格式正确）
    parse_method: Optional[str] = None # 使用的解析方法

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'item_path': self.item_path,
            'original_risk': self.original_risk.value if self.original_risk else None,
            'ai_risk': self.ai_risk.value if self.ai_risk else None,
            'confidence': self.confidence,
            'function_description': self.function_description,
            'software_name': self.software_name,
            'risk_reason': self.risk_reason,
            'cleanup_suggestion': self.cleanup_suggestion,
            'ai_reasoning': self.ai_reasoning,
            'review_timestamp': self.review_timestamp.isoformat() if self.review_timestamp else None,
            'retry_count': self.retry_count,
            'is_valid': self.is_valid,
            'parse_method': self.parse_method
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AIReviewResult':
        """从字典创建"""
        risk_map = {'safe': RiskLevel.SAFE, 'suspicious': RiskLevel.SUSPICIOUS, 'dangerous': RiskLevel.DANGEROUS}
        return cls(
            item_path=data.get('item_path', ''),
            original_risk=risk_map.get(data.get('original_risk')),
            ai_risk=risk_map.get(data.get('ai_risk')),
            confidence=data.get('confidence', 0.0),
            function_description=data.get('function_description', ''),
            software_name=data.get('software_name', ''),
            risk_reason=data.get('risk_reason', ''),
            cleanup_suggestion=data.get('cleanup_suggestion', ''),
            ai_reasoning=data.get('ai_reasoning'),
            review_timestamp=datetime.fromisoformat(data['review_timestamp']) if data.get('review_timestamp') else None,
            retry_count=data.get('retry_count', 0),
            is_valid=data.get('is_valid', True),
            parse_method=data.get('parse_method')
        )


@dataclass
class AIReviewStatus:
    """AI复核状态"""
    total_items: int = 0             # 总项数
    reviewed_items: int = 0          # 已评估项数
    success_count: int = 0           # 成功数
    safe_count: int = 0              # 安全都数
    dangerous_count: int = 0         # 危险数
    suspicious_count: int = 0        # 疑似数
    failed_count: int = 0            # 失败数
    is_in_progress: bool = False    # 是否进行中
    current_item: str = ""          # 当前评估项
    start_time: Optional[datetime] = None  # 开始时间
    end_time: Optional[datetime] = None      # 结束时间
    error_messages: list = None      # 错误消息列表

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

    @property
    def progress_percent(self) -> int:
        """进度百分比"""
        if self.total_items == 0:
            return 0
        return int((self.reviewed_items / self.total_items) * 100)

    @property
    def is_complete(self) -> bool:
        """是否完成"""
        return self.reviewed_items >= self.total_items and not self.is_in_progress

    @property
    def elapsed_seconds(self) -> float:
        """已用时间（秒）"""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def estimated_remaining_seconds(self) -> float:
        """预估剩余时间（秒）"""
        if self.reviewed_items == 0:
            return 0.0
        avg_time = self.elapsed_seconds / self.reviewed_items
        remaining = self.total_items - self.reviewed_items
        return avg_time * remaining

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'total_items': self.total_items,
            'reviewed_items': self.reviewed_items,
            'success_count': self.success_count,
            'safe_count': self.safe_count,
            'dangerous_count': self.dangerous_count,
            'suspicious_count': self.suspicious_count,
            'failed_count': self.failed_count,
            'is_in_progress': self.is_in_progress,
            'current_item': self.current_item,
            'progress_percent': self.progress_percent,
            'is_complete': self.is_complete,
            'elapsed_seconds': self.elapsed_seconds,
            'estimated_remaining_seconds': self.estimated_remaining_seconds,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_messages': self.error_messages
        }


@dataclass
class AuditRecord:
    """人工审核记录"""
    item_path: str                      # 项目路径
    user_decision: ReviewDecision       # 用户决策
    original_ai_risk: RiskLevel         # AI原始评估
    final_risk: RiskLevel              # 最终风险等级
    audit_timestamp: datetime           # 审核时间
    audit_reason: Optional[str] = None # 审核原因
    changed_risk: bool = False          # 是否更改AI建议

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'item_path': self.item_path,
            'user_decision': self.user_decision.value,
            'original_ai_risk': self.original_ai_risk.value if self.original_ai_risk else None,
            'final_risk': self.final_risk.value if self.final_risk else None,
            'audit_timestamp': self.audit_timestamp.isoformat(),
            'audit_reason': self.audit_reason,
            'changed_risk': self.changed_risk
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AuditRecord':
        """从字典创建"""
        risk_map = {'safe': RiskLevel.SAFE, 'suspicious': RiskLevel.SUSPICIOUS, 'dangerous': RiskLevel.DANGEROUS}
        decision_map = {'keep': ReviewDecision.KEEP, 'delete': ReviewDecision.DELETE, 'skip': ReviewDecision.SKIP}
        return cls(
            item_path=data.get('item_path', ''),
            user_decision=decision_map.get(data.get('user_decision')),
            original_ai_risk=risk_map.get(data.get('original_ai_risk')),
            final_risk=risk_map.get(data.get('final_risk')),
            audit_timestamp=datetime.fromisoformat(data['audit_timestamp']),
            audit_reason=data.get('audit_reason'),
            changed_risk=data.get('changed_risk', False)
        )


@dataclass
class ReviewConfig:
    """复核配置"""
    max_concurrent: int = 3            # 最大并发数
    max_retries: int = 3               # 最大重试次数
    retry_delay: float = 1.0          # 重试延迟（秒）
    timeout: float = 30.0              # 请求超时（秒）
    enable_caching: bool = True       # 启用缓存
    cache_ttl: int = 86400            # 缓存有效期（秒，24小时）
    strict_parse: bool = True         # 严格解析模式

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'max_concurrent': self.max_concurrent,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'timeout': self.timeout,
            'enable_caching': self.enable_caching,
            'cache_ttl': self.cache_ttl,
            'strict_parse': self.strict_parse
        }
