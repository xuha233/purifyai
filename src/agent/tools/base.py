# -*- coding: utf-8 -*-
"""
工具基类 - 所有智能体工具的基类
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class ToolBase(ABC):
    """工具基类 - 所有智能体工具都继承此类"""

    NAME: str = ""
    DESCRIPTION: str = ""

    @abstractmethod
    def execute(self, input_json: Dict[str, Any], workspace: Optional[str] = None) -> str:
        """执行工具

        Args:
            input_json: 输入 JSON
            workspace: 工作目录

        Returns:
            工具输出字符串
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的 JSON Schema

        Returns:
            工具 Schema
        """
        return {}
