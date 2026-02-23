# -*- coding: utf-8 -*-
"""
智能体配置增强 - 智能体系统集成配置

这配置文件定义了智能体系统在 UI 中的选项和默认值
"""

# 智能体系统可用性
AGENT_SYSTEM_AVAILABLE = True

# 智能体模式选项
AGENT_MODE_OPTIONS = {
    "disabled": {
        "name": "禁用",
        "description": "使用传统扫描和分析系统",
        "enabled": False
    },
    "hybrid": {
        "name": "混合模式",
        "description": "智能体辅助，传统系统后备",
        "enabled": True,
        "default": True
    },
    "full": {
        "name": "完全智能体",
        "description": "使用智能体系统处理所有操作",
        "enabled": True
    }
}

# 默认配置
DEFAULT_AGENT_CONFIG = {
    "agent_mode": "hybrid",            # 默认使用混合模式
    "enable_agent_review": True,       # 启用智能体审查
    "ai_model": "claude-opus-4-6",      # 默认AI模型
    "ai_max_tokens": 8192,            # 最大token数
    "ai_temperature": 0.7,             # 温度设置

    # 扫描设置
    "scan_patterns": ["temp_files", "cache_files", "log_files", "system_junk"],
    "max_scan_items": 10000,           # 最大扫描项数

    # 审查设置
    "auto_block_dangerous": True,       # 自动阻止危险项目
    "review_all_items": False,         # 审查所有项目（不仅可疑项）

    # 执行设置
    "enable_backup": True,             # 启用备份
    "backup_retention_days": 7,        # 备份保留天数
    "confirm_before_cleanup": True,     # 清理前确认

    # 批量处理
    "batch_size": 100,                 # 批量处理大小
    "batch_recommended_threshold": 500, # 建议批量处理的阈值

    # 超时设置
    "scan_timeout": 300,                # 扫描超时（秒）
    "analyze_timeout": 300,            # 分析超时（秒）
    "execute_timeout": 600,            # 执行超时（秒）
}

# AI 风险政策
AI_RISK_POLICY = {
    "safe": {
        "name": "安全",
        "color": "#52C41A",  # 绿色
        "auto_clean": True,
        "needs_review": False
    },
    "suspicious": {
        "name": "疑似",
        "color": "#FAAD14",  # 黄色
        "auto_clean": True,
        "needs_review": True
    },
    "dangerous": {
        "name": "危险",
        "color": "#FF4D4F",  # 红色
        "auto_clean": False,
        "needs_review": True
    }
}

# 智能体UI提示文本
AGENT_UI_TEXTS = {
    "mode_label": "智能体模式",
    "mode_help": "选择智能体运行模式",
    "review_label": "启用智能体审查",
    "review_help": "使用智能体系统审查清理计划的安全性",
    "scan_with_agent": "使用智能体扫描",
    "scan_with_agent_tooltip": "使用AI智能体进行智能扫描和风险分析",
    "traditional_scan": "传统扫描",
    "traditional_scan_tooltip": "使用传统规则系统进行扫描",

    "agent_scanning": "智能体正在扫描中...",
    "agent_analyzing": "智能体正在分析扫描结果...",
    "agent_reviewing": "智能体正在审查清理计划...",
    "agent_executing": "智能体正在执行清理...",

    "mode_disabled": "智能体已禁用 - 使用传统系统",
    "mode_hybrid": "混合模式 - 智能体辅助",
    "mode_full": "完全智能体模式",

    "backup_enabled": "智能体执行会自动备份被删除的文件",
    "backup_retention": f"备份将保留 {DEFAULT_AGENT_CONFIG['backup_retention_days']} 天",
    "review_summary": "智能体审查将自动标记危险的文件"
}

# 统计信息格式化模板
STATS_TEMPLATES = {
    "files_scanned": "扫描文件数",
    "space_freed": "释放空间",
    "scan_duration": "扫描耗时",
    "ai_calls": "AI 调用次数",
    "success_rate": "成功率",

    "ai_mode": "智能体模式",
    "agent_turns": "智能体轮次",
    "tool_calls": "工具调用次数"
}

# 获取配置的函数
def get_default_agent_config():
    """获取默认智能体配置"""
    return DEFAULT_AGENT_CONFIG.copy()

def get_agent_mode_info(mode: str) -> dict:
    """获取智能体模式信息

    Args:
        mode: 模式字符串

    Returns:
        模式信息字典
    """
    return AGENT_MODE_OPTIONS.get(mode, AGENT_MODE_OPTIONS["hybrid"])

def get_risk_policy(risk: str) -> dict:
    """获取风险政策

    Args:
        risk: 风险等级

    Returns:
        政策字典
    """
    return AI_RISK_POLICY.get(risk, AI_RISK_POLICY["suspicious"])

def get_ui_text(key: str) -> str:
    """获取UI文本

    Args:
        key: 文本键

    Returns:
        文本内容
    """
    return AGENT_UI_TEXTS.get(key, "")

def get_available_models() -> list:
    """获取可用的AI模型列表

    Returns:
        模型列表
    """
    return [
        {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "description": "最强性能模型"},
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "description": "平衡性能和成本"},
        {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "description": "快速低成本模型"}
    ]

def validate_agent_config(config: dict) -> tuple[bool, list]:
    """验证智能体配置

    Args:
        config: 配置字典

    Returns:
        (是否有效, 错误列表)
    """
    errors = []

    # 验证模式
    if config.get("agent_mode") not in AGENT_MODE_OPTIONS:
        errors.append(f"无效的智能体模式: {config.get('agent_mode')}")

    # 验证模型
    models = [m["id"] for m in get_available_models()]
    if config.get("ai_model") not in models:
        errors.append(f"无效的AI模型: {config.get('ai_model')}")

    # 验证数值
    if config.get("ai_max_tokens", 0) < 1000:
        errors.append("ai_max_tokens 必须至少为 1000")

    if config.get("ai_temperature", 1.0) < 0 or config.get("ai_temperature", 1.0) > 1:
        errors.append("ai_temperature 必须在 0-1 之间")

    return len(errors) == 0, errors

# 导出
__all__ = [
    "AGENT_SYSTEM_AVAILABLE",
    "AGENT_MODE_OPTIONS",
    "DEFAULT_AGENT_CONFIG",
    "AI_RISK_POLICY",
    "AGENT_UI_TEXTS",
    "STATS_TEMPLATES",
    "get_default_agent_config",
    "get_agent_mode_info",
    "get_risk_policy",
    "get_ui_text",
    "get_available_models",
    "validate_agent_config"
]
