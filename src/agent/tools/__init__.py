# -*- coding: utf-8 -*-
"""
工具注册表 - 管理智能体工具

职责:
1. 工具注册和发现
2. 工具验证
3. 工具执行
"""
from typing import Dict, Type, Callable, Any, Optional, List
from dataclasses import dataclass

from .base import ToolBase
from utils.logger import get_logger

logger = get_logger(__name__)


_tools_registry: Dict[str, ToolBase] = {}


def register_tool(tool_class: Type[ToolBase]) -> Type[ToolBase]:
    """工具注册装饰器

    用法:
    @register_tool
    class MyTool(ToolBase):
        NAME = "my_tool"
        DESCRIPTION = "..."

        def execute(self, input_json, workspace):
            ...
    """
    tool_instance = tool_class()
    _tools_registry[tool_instance.NAME] = tool_instance
    return tool_instance


def get_tool(name: str) -> Optional[ToolBase]:
    """获取工具实例

    Args:
        name: 工具名称

    Returns:
        工具实例，如果不存在返回 None
    """
    return _tools_registry.get(name)


def get_all_tools() -> Dict[str, ToolBase]:
    """获取所有已注册的工具

    Returns:
        工具字典
    """
    return _tools_registry.copy()


def get_tools_schema() -> List[Dict[str, Any]]:
    """获取所有工具的 Schema 列表

    Returns:
        工具 Schema 列表 (OpenAI 格式)
    """
    tools = []

    for name, tool in _tools_registry.items():
        try:
            schema = tool.get_schema()
            if schema:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.DESCRIPTION,
                        "parameters": schema
                    }
                })
        except Exception as e:
            logger.warning(f"[TOOLS] 获取工具 {name} schema 失败: {e}")

    return tools


def print_tools_info():
    """打印工具信息（调试用）"""
    tools = get_all_tools()
    logger.info(f"[TOOLS] 已注册 {len(tools)} 个工具:")
    for tool_name, tool in tools.items():
        logger.info(f"  - {tool_name}: {tool.DESCRIPTION}")
