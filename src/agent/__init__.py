# -*- coding: utf-8 -*-
"""
Agent 包 - 智能体核心模块

功能:
- orchestrator: 智能体编排器
- agents: 各类型智能体
- tools: 工具层
- models: 智能体数据模型
"""
from typing import Optional, TYPE_CHECKING

# Export main components (延迟循环依赖导入)
from .orchestrator import AgentOrchestrator, AgentType, AIConfig
from .models_agent import (
    AgentMessage, AgentRole, AgentToolCall, AgentToolResult, AgentSession
)

# 延迟导入循环依赖
if TYPE_CHECKING:
    from .integration import AgentIntegration

__all__ = [
    "AgentOrchestrator", "AgentType", "AIConfig",
    "AgentMessage", "AgentRole", "AgentToolCall", "AgentToolResult", "AgentSession",
    "create_scan_agent", "create_review_agent", "create_cleanup_agent", "create_report_agent",
    "get_orchestrator",
    "get_agent_integration", "AgentIntegration"
]


# 便利函数
def get_orchestrator(ai_config: Optional[AIConfig] = None) -> AgentOrchestrator:
    """获取全局编排器实例

    Args:
        ai_config: AI 配置

    Returns:
        AgentOrchestrator 实例
    """
    return AgentOrchestrator(ai_config)


def create_scan_agent(orchestrator: Optional[AgentOrchestrator] = None):
    """创建扫描智能体

    Args:
        orchestrator: 编排器实例，如果为 None 则创建新实例

    Returns:
        ScanAgent 实例
    """
    from .agents.scan_agent import ScanAgent

    if orchestrator is None:
        orchestrator = get_orchestrator()
    return ScanAgent(orchestrator)


def create_review_agent(orchestrator: Optional[AgentOrchestrator] = None):
    """创建审查智能体

    Args:
        orchestrator: 编排器实例，如果为 None 则创建新实例

    Returns:
        ReviewAgent 实例
    """
    from .agents.review_agent import ReviewAgent

    if orchestrator is None:
        orchestrator = get_orchestrator()
    return ReviewAgent(orchestrator)


def create_cleanup_agent(orchestrator: Optional[AgentOrchestrator] = None):
    """创建清理智能体

    Args:
        orchestrator: 编排器实例，如果为 None 则创建新实例

    Returns:
        CleanupAgent 实例
    """
    from .agents.cleanup_agent import CleanupAgent

    if orchestrator is None:
        orchestrator = get_orchestrator()
    return CleanupAgent(orchestrator)


def create_report_agent(orchestrator: Optional[AgentOrchestrator] = None):
    """创建报告智能体

    Args:
        orchestrator: 编排器实例，如果为 None 则创建新实例

    Returns:
        ReportAgent 实例
    """
    from .agents.report_agent import ReportAgent

    if orchestrator is None:
        orchestrator = get_orchestrator()
    return ReportAgent(orchestrator)


def get_agent_integration(ai_config: Optional[AIConfig] = None):
    """获取 Agent Integration 实例

    Args:
        ai_config: AI 配置

    Returns:
        AgentIntegration 实例
    """
    from .integration import AgentIntegration

    return AgentIntegration(ai_config)


# 延迟导入支持 - 允许 from agent import AgentIntegration
_deferred_imports = {
    "AgentIntegration": ("integration", "AgentIntegration"),
}


def __getattr__(name: str):
    """支持延迟导入

    Args:
        name: 属性名

    Returns:
        导入的对象
    """
    if name in _deferred_imports:
        module_name, attr_name = _deferred_imports[name]
        from importlib import import_module
        module = import_module(f".{module_name}", package=__name__)
        return getattr(module, attr_name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
