# -*- coding: utf-8 -*-
"""
Agent Orchestrator - 智能体编排器

职责:
1. 管理不同类型的智能体
2. 协调智能体之间的通信
3. 处理工具调用和结果返回
4. 管理会话状态
"""
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import json
import time
from dataclasses import dataclass

from .models_agent import (
    AgentSession, AgentMessage, AgentRole, AgentToolCall,
    AgentToolResult, ContentBlock, AgentConfig
)
from .tools import get_tool, get_tools_schema, print_tools_info
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentType(Enum):
    """智能体类型枚举"""
    SCAN = "scan"           # 扫描智能体
    REVIEW = "review"       # 审查智能体
    CLEANUP = "cleanup"     # 清理智能体
    REPORT = "report"       # 报告智能体


class AgentStateException(Exception):
    """智能体状态异常"""
    pass


class ToolExecutionException(Exception):
    """工具执行异常"""
    pass


@dataclass
class AIConfig:
    """AI 配置"""
    api_key: str
    model: str = "claude-opus-4-6"
    base_url: str = "https://api.anthropic.com"
    max_tokens: int = 8192
    temperature: float = 0.7


class AgentOrchestrator:
    """智能体编排器

    负责协调不同类型的智能体，管理会话状态，处理工具调用。
    """

    def __init__(self, ai_config: Optional[AIConfig] = None):
        """初始化编排器

        Args:
            ai_config: AI 配置对象
        """
        self.ai_config = ai_config or AIConfig(
            api_key="",  # 将从配置加载
            model="claude-opus-4-6"
        )
        self.sessions: Dict[str, AgentSession] = {}
        self.active_agent_type: Optional[AgentType] = None
        self.current_session_id: Optional[str] = None

        # 注册的工具
        print_tools_info()

        logger.info(f"[ORCHESTRATOR] 初始化完成, AI模型: {self.ai_config.model}")

    def create_session(
        self,
        agent_type: AgentType,
        workspace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentSession:
        """创建新的智能体会话

        Args:
            agent_type: 智能体类型
            workspace: 工作目录
            metadata: 元数据

        Returns:
            AgentSession: 创建的会话
        """
        session_id = f"{agent_type.value}_{int(time.time())}"

        session = AgentSession(
            session_id=session_id,
            agent_type=agent_type.value,
            workspace=workspace,
            metadata=metadata or {}
        )

        # 添加系统提示词
        system_prompt = self._get_system_prompt(agent_type)
        if system_prompt:
            session.add_message(
                AgentRole.SYSTEM,
                [ContentBlock(type="text", content={"text": system_prompt})]
            )

        self.sessions[session_id] = session
        self.current_session_id = session_id
        self.active_agent_type = agent_type

        logger.info(f"[ORCHESTRATOR] 创建会话: {session_id}, 类型: {agent_type.value}")
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """获取会话

        Args:
            session_id: 会话ID

        Returns:
            AgentSession 或 None
        """
        return self.sessions.get(session_id)

    def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        tools_enabled: bool = True
    ) -> Dict[str, Any]:
        """处理用户消息

        Args:
            message: 用户消息
            session_id: 会话ID，如果为 None 使用当前会话
            tools_enabled: 是否启用工具调用

        Returns:
            处理结果字典
        """
        session_id = session_id or self.current_session_id
        if not session_id:
            raise AgentStateException("没有活动会话")

        session = self.sessions[session_id]

        # 添加用户消息
        session.add_user_message(message)

        # 获取工具列表
        available_tools = []
        if tools_enabled:
            available_tools = get_tools_schema()

        # 调用 AI 获取响应
        response = self._call_ai(
            messages=session.get_all_messages(),
            system_prompt=self._get_system_prompt(AgentType(session.agent_type)),
            tools=available_tools
        )

        # 处理响应
        result = {
            "session_id": session_id,
            "response_text": "",
            "tool_calls": [],
            "tool_results": [],
            "is_complete": False
        }

        # 解析响应内容
        for content in response.get("content", []):
            content_type = content.get("type")

            if content_type == "text":
                result["response_text"] = content.get("text", "")
                session.add_assistant_message(result["response_text"])

            elif content_type == "tool_use":
                tool_call = content
                call_id = tool_call.get("id", f"call_{int(time.time())}")
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("input", {})

                result["tool_calls"].append({
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "input": tool_input
                })

                # 执行工具
                if tools_enabled:
                    tool_result = self._execute_tool(tool_name, tool_input, session.workspace)
                    result["tool_results"].append(tool_result)

                    # 添加工具结果到会话
                    session.add_message(
                        AgentRole.USER,
                        [ContentBlock(type="tool_result", content={
                            "tool_use_id": call_id,
                            "tool_name": tool_name,
                            "content": tool_result.get("output", ""),
                            "is_error": tool_result.get("is_error", False)
                        })]
                    )

        result["is_complete"] = response.get("stop_reason") == "end_turn"

        return result

    def _execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行工具

        Args:
            tool_name: 工具名称
            tool_input: 工具输入
            workspace: 工作目录

        Returns:
            工具执行结果
        """
        tool = get_tool(tool_name)
        if not tool:
            return {
                "output": f"工具 '{tool_name}' 未找到",
                "is_error": True
            }

        try:
            # 执行工具
            result = tool.execute(tool_input, workspace)
            logger.debug(f"[ORCHESTRATOR] 工具执行: {tool_name}，结果长度: {len(result)}")
            return {
                "output": result,
                "is_error": False
            }
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] 工具执行失败 {tool_name}: {e}")
            return {
                "output": str(e),
                "is_error": True
            }

    def _call_ai(
        self,
        messages: List[AgentMessage],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """调用 AI API

        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            tools: 工具列表

        Returns:
            AI 响应
        """
        try:
            # 这里使用 anthropic SDK
            from anthropic import Anthropic

            client = Anthropic(api_key=self.ai_config.api_key)

            # 转换消息格式
            api_messages = []
            for msg in messages:
                role = msg.role.value
                content_blocks = []

                for block in msg.content:
                    block_type = block.type
                    block_data = block.content

                    if block_type == "text":
                        content_blocks.append({
                            "type": "text",
                            "text": block_data.get("text", "")
                        })
                    elif block_type == "tool_use":
                        content_blocks.append({
                            "type": "tool_use",
                            "id": block_data.get("tool_id"),
                            "name": block_data.get("tool_name"),
                            "input": block_data.get("input_json", {})
                        })
                    elif block_type == "tool_result":
                        content_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": block_data.get("tool_id"),
                            "content": block_data.get("content", ""),
                            "is_error": block_data.get("is_error", False)
                        })

                api_messages.append({
                    "role": role,
                    "content": content_blocks
                })

            # 调用 API
            response = client.messages.create(
                model=self.ai_config.model,
                max_tokens=self.ai_config.max_tokens,
                temperature=self.ai_config.temperature,
                system=system_prompt,
                messages=api_messages,
                tools=tools or []
            )

            # 转换响应格式
            result = {
                "id": response.id,
                "model": response.model,
                "stop_reason": response.stop_reason,
                "content": []
            }

            for content in response.content:
                content_type = getattr(content, "type", None)

                if content_type == "text":
                    result["content"].append({
                        "type": "text",
                        "text": content.text
                    })
                elif content_type == "tool_use":
                    result["content"].append({
                        "type": "tool_use",
                        "id": content.id,
                        "name": content.name,
                        "input": content.input
                    })

            logger.debug(f"[ORCHESTRATOR] AI 调用完成, stop_reason: {response.stop_reason}")
            return result

        except ImportError:
            # 如果没有 anthropic SDK，返回模拟响应
            logger.warning("[ORCHESTRATOR] anthropic SDK 未安装，使用模拟模式")

            # 检查是否有最后一个用户消息
            last_user_message = None
            for msg in reversed(messages):
                if msg.role == AgentRole.USER:
                    content_text = ""
                    for block in msg.content:
                        if block.type == "text":
                            content_text = block.content.get("text", "")
                            break
                    if content_text:
                        last_user_message = content_text
                    break

            return {
                "id": "mock_response",
                "model": "mock",
                "stop_reason": "end_turn",
                "content": [
                    {
                        "type": "text",
                        "text": f"[模拟响应] 收到消息: {last_user_message or '空消息'}\n"
                                f"可用工具: {[t.get('function', {}).get('name') for t in tools or []]}"
                    }
                ]
            }
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] AI 调用失败: {e}")
            return {
                "id": "error_response",
                "model": "error",
                "stop_reason": "error",
                "content": [
                    {
                        "type": "text",
                        "text": f"AI 调用失败: {str(e)}"
                    }
                ]
            }

    def _get_system_prompt(self, agent_type: AgentType) -> Optional[str]:
        """获取智能体的系统提示词

        Args:
            agent_type: 智能体类型

        Returns:
            系统提示词
        """
        from .prompts import (
            get_scan_prompt, get_review_prompt,
            get_cleanup_prompt, get_report_prompt
        )

        prompts = {
            AgentType.SCAN: get_scan_prompt(),
            AgentType.REVIEW: get_review_prompt(),
            AgentType.CLEANUP: get_cleanup_prompt(),
            AgentType.REPORT: get_report_prompt()
        }

        return prompts.get(agent_type)

    def run_agent_loop(
        self,
        agent_type: AgentType,
        initial_message: str,
        workspace: Optional[str] = None,
        max_turns: int = 20,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """运行智能体循环

        Args:
            agent_type: 智能体类型
            initial_message: 初始消息
            workspace: 工作目录
            max_turns: 最大轮次
            metadata: 元数据

        Returns:
            执行结果
        """
        # 创建会话
        session = self.create_session(agent_type, workspace, metadata)

        logger.info(f"[ORCHESTRATOR] 开始智能体循环: {agent_type.value}, 最大轮次: {max_turns}")

        results = {
            "session_id": session.session_id,
            "agent_type": agent_type.value,
            "turns": 0,
            "responses": [],
            "tool_calls": [],
            "is_complete": False,
            "error": None
        }

        # 处理初始消息
        try:
            result = self.process_message(initial_message, session.session_id)
            results["responses"].append(result["response_text"])
            results["tool_calls"].extend(result["tool_calls"])
            results["is_complete"] = result["is_complete"]
            results["turns"] = 1

            # 继续循环直到完成或达到最大轮次
            while not results["is_complete"] and results["turns"] < max_turns:
                result = self.process_message("请继续", session.session_id)
                results["responses"].append(result["response_text"])
                results["tool_calls"].extend(result["tool_calls"])
                results["is_complete"] = result["is_complete"]
                results["turns"] += 1

                logger.debug(f"[ORCHESTRATOR] 轮次 {results['turns']}/{max_turns}")

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] 智能体循环出错: {e}")
            results["error"] = str(e)

        logger.info(f"[ORCHESTRATOR] 智能体循环完成: {results['turns']} 轮次, 完成: {results['is_complete']}")
        return results

    def close_session(self, session_id: str):
        """关闭会话

        Args:
            session_id: 会话ID
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"[ORCHESTRATOR] 关闭会话: {session_id}")

            if session_id == self.current_session_id:
                self.current_session_id = None
                self.active_agent_type = None

    def close_all_sessions(self):
        """关闭所有会话"""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            self.close_session(session_id)

        logger.info(f"[ORCHESTRATOR] 关闭所有会话，共 {len(session_ids)} 个")


def get_orchestrator(ai_config: Optional[AIConfig] = None) -> AgentOrchestrator:
    """获取全局编排器实例

    Args:
        ai_config: AI 配置

    Returns:
        AgentOrchestrator 实例
    """
    # 这里可以缓存全局实例
    return AgentOrchestrator(ai_config)
