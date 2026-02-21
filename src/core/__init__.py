"""
Core 模块初始化
"""

# AI 客户端
from .ai_client import AIClient, AIConfig

# 规则引擎
from .rule_engine import RuleEngine, RiskLevel, Rule, get_rule_engine

# 数据模型
from .models import ScanItem

# 扫描器
from .scanner import (
    SystemScanner, BrowserScanner, AppDataScanner,
    ScanEventType, ScanEvent, format_size
)
from .custom_scanner import CustomScanner

# 清理器
from .cleaner import Cleaner, CleanEventType, CleanEvent

# 白名单
from .whitelist import Whitelist, get_whitelist

# 权限
from .permissions import (
    is_admin, request_admin_privilege, ensure_admin_or_fail,
    get_current_user, is_system_path, needs_admin_for_operation
)

# 数据库
from .database import get_database

# AI 增强
from .ai_enhancer import AIEnhancer, get_ai_enhancer

# AI 缓存
from .ai_cache import AICache, get_ai_cache

# 风险评估系统
from .risk_assessment import (
    RiskAssessmentSystem, RuleAssessmentResult, DecisionReport,
    FinalRiskAssessment, get_risk_assessment_system
)

# AI复核模块
from .ai_review_models import (
    AIReviewResult,
    AIReviewStatus,
    AuditRecord,
    ReviewDecision,
    ReviewConfig
)
from .ai_prompt_builder import PromptBuilder
from .ai_response_parser import ResponseParser, get_parser
from .ai_review_task import AIReviewWorker, AIReviewOrchestrator
from .ai_result_store import AIResultStore, AuditLogManager, get_result_store

# AppData 迁移模块
from .appdata_migration import (
    AppDataMigrationTool, MigrationItem, ScanMigrationThread,
    MigrateThread, RollbackThread
)

# 备份管理器
from .backup_manager import BackupManager, BackupStats, get_backup_manager

# 执行引擎
from .execution_engine import (
    SmartCleanupExecutor, ExecutionThread, ExecutionConfig,
    ExecutionPhase, ErrorType, RetryStrategy, get_executor
)

# 智能清理器
from .smart_cleaner import (
    SmartCleaner, SmartCleanConfig, SmartCleanPhase, ScanType,
    get_smart_cleaner
)

# 恢复管理器
from .recovery_manager import (
    RecoveryManager, RecoveryTask, RecoveryStats,
    RestoreStatus, get_recovery_manager
)

__all__ = [
    # AI 客户端
    'AIClient', 'AIConfig',
    # 规则引擎
    'RuleEngine', 'RiskLevel', 'Rule', 'get_rule_engine',
    # 扫描器
    'ScanItem', 'SystemScanner', 'BrowserScanner', 'AppDataScanner',
    'ScanEventType', 'ScanEvent', 'format_size',
    'CustomScanner',
    # 清理器
    'Cleaner', 'CleanEventType', 'CleanEvent',
    # 白名单
    'Whitelist', 'get_whitelist',
    # 权限
    'is_admin', 'request_admin_privilege', 'ensure_admin_or_fail',
    'get_current_user', 'is_system_path', 'needs_admin_for_operation',
    # 数据库
    'get_database',
    # AI 增强
    'AIEnhancer', 'get_ai_enhancer',
    # AI 缓存
    'AICache', 'get_ai_cache',
    # 风险评估系统
    'RiskAssessmentSystem', 'RuleAssessmentResult', 'DecisionReport',
    'FinalRiskAssessment', 'get_risk_assessment_system',
    # AI复核模块
    'AIReviewResult',
    'AIReviewStatus',
    'AuditRecord',
    'ReviewDecision',
    'ReviewConfig',
    'PromptBuilder',
    'ResponseParser',
    'get_parser',
    'AIReviewWorker',
    'AIReviewOrchestrator',
    'AIResultStore',
    'AuditLogManager',
    'get_result_store',
    # AppData 迁移模块
    'AppDataMigrationTool',
    'MigrationItem',
    'ScanMigrationThread',
    'MigrateThread',
    'RollbackThread',
    # 备份管理器
    'BackupManager',
    'BackupStats',
    'get_backup_manager',
    # 执行引擎
    'SmartCleanupExecutor',
    'ExecutionThread',
    'ExecutionConfig',
    'ExecutionPhase',
    'ErrorType',
    'RetryStrategy',
    'get_executor',
    # 智能清理器
    'SmartCleaner',
    'SmartCleanConfig',
    'SmartCleanPhase',
    'ScanType',
    'get_smart_cleaner',
    # 恢复管理器
    'RecoveryManager',
    'RecoveryTask',
    'RecoveryStats',
    'RestoreStatus',
    'get_recovery_manager',
]
