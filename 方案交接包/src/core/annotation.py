"""
AI批注数据模型
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AssessmentMethod(Enum):
    """评估方法枚举"""
    WHITELIST = "whitelist"
    RULE = "rule"
    AI = "ai"
    UNCERTAIN = "uncertain"


class RiskLevel(Enum):
    """风险等级枚举"""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"

    @classmethod
    def from_value(cls, value: str) -> 'RiskLevel':
        """从字符串值转换为 RiskLevel"""
        for level in cls:
            if level.value == value:
                return level
        return RiskLevel.SUSPICIOUS

    @classmethod
    def from_string(cls, value: str) -> 'RiskLevel':
        """从字符串转换为 RiskLevel（兼容调用）"""
        return cls.from_value(value)


@dataclass
class AnnotationNote:
    """批注备注"""
    text: str = ""
    author: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_user_note: bool = False


@dataclass
class ScanAnnotation:
    """扫描结果批注"""
    # 基础信息
    id: str
    item_path: str
    item_type: str  # 'file' | 'folder'
    scan_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 文件信息
    file_size: int = 0
    file_name: str = ""
    file_extension: str = ""

    # 风险评估
    risk_level: str = RiskLevel.SUSPICIOUS.value  # safe, suspicious, dangerous
    risk_score: int = 50  # 0-100
    confidence: float = 0.5  # 0-1

    # 评估来源
    assessment_method: str = AssessmentMethod.UNCERTAIN.value  # whitelist, rule, ai
    assessment_source: str = ""
    assessment_details: str = ""

    # 批注核心
    annotation_note: str = ""
    annotation_tags: List[str] = field(default_factory=list)
    recommendation: str = "需确认"  # 安全清理、建议保留、需确认

    # 置信度相关
    ai_confidence: float = 0.5
    rule_match_count: int = 0

    # 缓存
    cache_hit: bool = False
    cache_key: Optional[str] = None
    cache_ttl: Optional[int] = None

    # 元数据
    last_modified: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 用户标记
    user_reviewed: bool = False
    user_safe_confirmed: Optional[bool] = None
    user_notes: List[AnnotationNote] = field(default_factory=list)

    # 关联
    scan_source: Optional[str] = None  # system, browser, custom
    parent_scan_id: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'item_path': self.item_path,
            'item_type': self.item_type,
            'scan_timestamp': self.scan_timestamp,
            'file_size': self.file_size,
            'file_name': self.file_name,
            'file_extension': self.file_extension,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'confidence': self.confidence,
            'assessment_method': self.assessment_method,
            'assessment_source': self.assessment_source,
            'assessment_details': self.assessment_details,
            'annotation_note': self.annotation_note,
            'annotation_tags': self.annotation_tags,
            'recommendation': self.recommendation,
            'ai_confidence': self.ai_confidence,
            'rule_match_count': self.rule_match_count,
            'cache_hit': self.cache_hit,
            'cache_key': self.cache_key,
            'cache_ttl': self.cache_ttl,
            'last_modified': self.last_modified,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'user_reviewed': self.user_reviewed,
            'user_safe_confirmed': self.user_safe_confirmed,
            'scan_source': self.scan_source,
            'parent_scan_id': self.parent_scan_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScanAnnotation':
        """从字典创建"""
        return cls(
            id=data['id'],
            item_path=data['item_path'],
            item_type=data.get('item_type', 'file'),
            scan_timestamp=data.get('scan_timestamp'),
            file_size=data.get('file_size', 0),
            file_name=data.get('file_name', ''),
            file_extension=data.get('file_extension', ''),
            risk_level=data.get('risk_level', 'suspicious'),
            risk_score=data.get('risk_score', 50),
            confidence=data.get('confidence', 0.5),
            assessment_method=data.get('assessment_method', 'uncertain'),
            assessment_source=data.get('assessment_source', ''),
            assessment_details=data.get('assessment_details', ''),
            annotation_note=data.get('annotation_note', ''),
            annotation_tags=data.get('annotation_tags', []),
            recommendation=data.get('recommendation', '需确认'),
            ai_confidence=data.get('ai_confidence', 0.5),
            rule_match_count=data.get('rule_match_count', 0),
            cache_hit=data.get('cache_hit', False),
            cache_key=data.get('cache_key'),
            cache_ttl=data.get('cache_ttl'),
            last_modified=data.get('last_modified'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            user_reviewed=data.get('user_reviewed', False),
            user_safe_confirmed=data.get('user_safe_confirmed'),
            scan_source=data.get('scan_source'),
            parent_scan_id=data.get('parent_scan_id'),
        )


def generate_annotation_id(item_path: str) -> str:
    """根据路径生成唯一ID"""
    import hashlib
    path_bytes = item_path.encode('utf-8', errors='ignore')
    hash_obj = hashlib.md5(path_bytes)
    return f"anno_{hash_obj.hexdigest()[:16]}"


def get_default_recommendation(risk_level: str, assessment_method: str) -> str:
    """获取默认推荐操作"""
    if assessment_method == 'whitelist':
        return '保留'  # 白名单一定保留
    elif risk_level == 'safe':
        return '可以清理'
    elif risk_level == 'dangerous':
        return '建议保留'
    elif assessment_method == 'rule':
        return '需人工确认'
    else:  # AI
        return '需确认'


def format_annotation_note(risk_context: dict, assessment_method: str, details: str = "") -> str:
    """格式化批注说明"""
    notes = []

    if assessment_method == 'whitelist':
        notes.append("[白名单保护] 此文件在白名单中，建议保留")
    elif assessment_method == 'rule':
        notes.append(f"[规则评估] {details or '根据路径特征判断'}")
        if risk_context.get('match_type'):
            notes.append(f"匹配: {risk_context['match_type']}")
    elif assessment_method == 'ai':
        if risk_context.get('ai_confidence'):
            conf = risk_context['ai_confidence']
            if conf > 0.8:
                notes.append(f"[AI高置信度:{int(conf*100)}%]")
            elif conf > 0.5:
                notes.append(f"[AI中置信度:{int(conf*100)}%]")
            else:
                notes.append(f"[AI低置信度:{int(conf*100)}%]")
        if risk_context.get('ai_reason'):
            notes.append(f"理由: {risk_context['ai_reason']}")
    else:
        notes.append("[不确定] 需要进一步评估")

    return " ".join(notes)
