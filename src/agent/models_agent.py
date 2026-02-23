# -*- coding: utf-8 -*-
"""
智能体数据模型 (Agent Models)

与 PurifyAI 原有模型兼容，但面向智能通信
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class AgentRole(Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ContentBlockType(Enum):
    """内容块类型"""
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"


@dataclass
class ContentBlock:
    """AI 响应内容块"""
    type: str
    content: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type,
            "content": self.content
        }


@dataclass
class AgentMessage:
    """Agent 消息"""
    role: AgentRole
    content: List[ContentBlock]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role.value,
            "content": [block.to_dict() for block in self.content]
        }


@dataclass
class AgentToolCall:
    """工具调用请求"""
    tool_id: str
    tool_name: str
    input_json: Dict[str, Any]

    def __post_init__(self):
        if not self.tool_id:
            self.tool_id = f"call_{__import__('time').time_ns() % 1000000000}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "input_json": self.input_json
        }


@dataclass
class AgentToolResult:
    """工具执行结果"""
    tool_id: str
    tool_name: str = ""
    content: str = ""
    is_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tool_id": self.tool_id,
            "name": self.tool_name,
            "content": self.content,
            "is_error": self.is_error
        }


@dataclass
class AgentConfig:
    """智能体配置"""
    agent_type: str
    model: str = "claude-opus-4-6"
    max_turns: int = 20
    max_tokens: int = 8192
    tools: List[str] = field(default_factory=list)
    system_prompt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "agent_type": self.agent_type,
            "model": self.model,
            "max_turns": self.max_turns,
            "max_tokens": self.max_tokens,
            "tools": self.tools
        }


@dataclass
class AgentSession:
    """智能体会话"""
    session_id: str
    agent_type: str
    workspace: Optional[str] = None
    messages: List[AgentMessage] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: AgentRole, content: List[ContentBlock]):
        """添加消息到会话"""
        self.messages.append(AgentMessage(role=role, content=content))

    def add_user_message(self, text: str):
        """添加用户消息（简化方法）"""
        self.add_message(
            AgentRole.USER,
            [ContentBlock(type="text", content={"text": text})]
        )

    def add_assistant_message(self, text: str):
        """添加助手消息（简化方法）"""
        self.add_message(
            AgentRole.ASSISTANT,
            [ContentBlock(type="text", content={"text": text})]
        )

    def get_last_message(self) -> Optional[AgentMessage]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def get_all_messages(self) -> List[AgentMessage]:
        """获取所有消息"""
        return self.messages.copy()
