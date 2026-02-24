# -*- coding: utf-8 -*-
"""
智能体系统异常处理模块

提供统一的异常类型定义和错误处理框架
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback


class ErrorCode(Enum):
    """错误代码枚举"""
    # 通用错误
    UNKNOWN_ERROR = "E0000"
    INTERNAL_ERROR = "E0001"

    # 智能体错误
    AGENT_NOT_INITIALIZED = "E1000"
    AGENT_EXECUTION_FAILED = "E1001"
    AGENT_TIMEOUT = "E1002"
    AGENT_STATE_INVALID = "E1003"
    AGENT_SESSION_NOT_FOUND = "E1004"
    AGENT_LOOP_MAX_TURNS = "E1005"

    # AI API 错误
    AI_API_ERROR = "E2000"
    AI_AUTHENTICATION_FAILED = "E2001"
    AI_RATE_LIMIT_EXCEEDED = "E2002"
    AI_INVALID_RESPONSE = "E2003"
    AI_CONNECTION_ERROR = "E2004"
    AI_QUOTA_EXCEEDED = "E2005"

    # 工具执行错误
    TOOL_NOT_FOUND = "E3000"
    TOOL_EXECUTION_FAILED = "E3001"
    TOOL_TIMEOUT = "E3002"
    TOOL_INVALID_INPUT = "E3003"
    TOOL_PERMISSION_DENIED = "E3004"

    # 恢复相关
    RECOVERY_FAILED = "E9000"
    MAX_RETRIES_EXCEEDED = "E9001"
    CANNOT_RECOVER = "E9002"


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """恢复策略"""
    NONE = "none"                    # 无法恢复
    RETRY = "retry"                  # 重试
    FALLBACK = "fallback"            # 降级处理
    RESTART_SESSION = "restart"      # 重启会话
    CONTINUE = "continue"            # 继续执行 (跳过错误)


@dataclass
class ErrorContext:
    """错误上下文信息"""
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    workspace: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    stack_trace: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def add_data(self, key: str, value: Any):
        """添加额外数据"""
        self.additional_data[key] = value


@dataclass
class RecoveryAttempt:
    """恢复尝试记录"""
    attempt_number: int
    strategy: RecoveryStrategy
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = False
    error_message: str = ""
    duration_ms: int = 0


@dataclass
class AgentException(Exception):
    """智能体系统基础异常类"""
    code: ErrorCode
    message: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recoverable: bool = False
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE
    max_retries: int = 0
    context: ErrorContext = field(default_factory=ErrorContext)
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于日志记录）"""
        return {
            "code": self.code.value,
            "message": self.message,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "recovery_strategy": self.recovery_strategy.value,
            "context": {
                "session_id": self.context.session_id,
                "agent_type": self.context.agent_type,
                "workspace": self.context.workspace,
                "timestamp": self.context.timestamp,
                "stack_trace": self.context.stack_trace,
                "additional_data": self.context.additional_data
            },
            "recovery_attempts": [
                {
                    "attempt_number": ra.attempt_number,
                    "strategy": ra.strategy.value,
                    "timestamp": ra.timestamp,
                    "success": ra.success,
                    "error_message": ra.error_message,
                    "duration_ms": ra.duration_ms
                }
                for ra in self.recovery_attempts
            ]
        }

    def add_recovery_attempt(
        self,
        attempt_number: int,
        strategy: RecoveryStrategy,
        success: bool,
        error_message: str = "",
        duration_ms: int = 0
    ):
        """添加恢复尝试记录"""
        attempt = RecoveryAttempt(
            attempt_number=attempt_number,
            strategy=strategy,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        self.recovery_attempts.append(attempt)

    def update_context(self, **kwargs):
        """更新错误上下文"""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                self.context.add_data(key, value)
        return self

    def capture_stack(self):
        """捕获调用栈"""
        self.context.stack_trace = traceback.format_exc()
        return self


# ========== 具体的异常类 ==========

class AgentStateException(AgentException):
    """智能体状态异常"""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AGENT_STATE_INVALID,
            message=message,
            severity=ErrorSeverity.ERROR,
            recoverable=True,
            recovery_strategy=RecoveryStrategy.RESTART_SESSION,
            max_retries=3
        )
        self.update_context(session_id=session_id, **kwargs)


class AgentExecutionException(AgentException):
    """智能体执行异常"""

    def __init__(
        self,
        message: str,
        agent_type: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AGENT_EXECUTION_FAILED,
            message=message,
            severity=ErrorSeverity.ERROR,
            recoverable=True,
            recovery_strategy=RecoveryStrategy.RETRY,
            max_retries=2
        )
        self.update_context(agent_type=agent_type, session_id=session_id, **kwargs)


class AgentTimeoutException(AgentException):
    """智能体超时异常"""

    def __init__(
        self,
        message: str,
        timeout_seconds: int,
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AGENT_TIMEOUT,
            message=message,
            severity=ErrorSeverity.WARNING,
            recoverable=True,
            recovery_strategy=RecoveryStrategy.RESTART_SESSION,
            max_retries=1
        )
        self.update_context(timeout_seconds=timeout_seconds, **kwargs)


class ToolExecutionException(AgentException):
    """工具执行异常"""

    def __init__(
        self,
        message: str,
        tool_name: str,
        inputs: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.TOOL_EXECUTION_FAILED,
            message=message,
            severity=ErrorSeverity.WARNING,
            recoverable=True,
            recovery_strategy=RecoveryStrategy.CONTINUE,
            max_retries=1
        )
        self.update_context(
            tool_name=tool_name,
            inputs=inputs,
            session_id=session_id,
            **kwargs
        )


class ToolNotFoundException(AgentException):
    """工具不存在异常"""

    def __init__(
        self,
        tool_name: str,
        available_tools: Optional[List[str]] = None,
        **kwargs
    ):
        message = f"工具 '{tool_name}' 未找到"
        if available_tools:
            message += f", 可用工具: {', '.join(available_tools[:5])}"
        super().__init__(
            code=ErrorCode.TOOL_NOT_FOUND,
            message=message,
            severity=ErrorSeverity.ERROR,
            recoverable=False,
            recovery_strategy=RecoveryStrategy.NONE
        )
        self.update_context(tool_name=tool_name, available_tools=available_tools, **kwargs)


class AIAuthenticationException(AgentException):
    """AI 认证失败异常"""

    def __init__(
        self,
        message: str = "AI API 认证失败，请检查 API Key",
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AI_AUTHENTICATION_FAILED,
            message=message,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            recovery_strategy=RecoveryStrategy.NONE
        )
        self.update_context(**kwargs)


class AIRateLimitException(AgentException):
    """AI API 速率限制异常"""

    def __init__(
        self,
        message: str = "AI API 请求过于频繁，请稍后再试",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AI_RATE_LIMIT_EXCEEDED,
            message=message,
            severity=ErrorSeverity.WARNING,
            recoverable=True,
            recovery_strategy=RecoveryStrategy.RETRY,
            max_retries=3
        )
        if retry_after:
            self.update_context(retry_after_seconds=retry_after, **kwargs)
        else:
            self.update_context(**kwargs)


class AIConnectionException(AgentException):
    """AI 连接异常"""

    def __init__(
        self,
        message: str = "AI API 连接失败",
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AI_CONNECTION_ERROR,
            message=message,
            severity=ErrorSeverity.ERROR,
            recoverable=True,
            recovery_strategy=RecoveryStrategy.RETRY,
            max_retries=3
        )
        self.update_context(**kwargs)


class AIQuotaExceededException(AgentException):
    """AI 配额超限异常"""

    def __init__(
        self,
        message: str = "AI API 配额已用尽",
        **kwargs
    ):
        super().__init__(
            code=ErrorCode.AI_QUOTA_EXCEEDED,
            message=message,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            recovery_strategy=RecoveryStrategy.NONE
        )
        self.update_context(**kwargs)


class MaxRetriesExceededError(AgentException):
    """最大重试次数超限异常"""

    def __init__(
        self,
        original_error: AgentException,
        **kwargs
    ):
        message = f"重试次数已超限: {original_error.message}"
        super().__init__(
            code=ErrorCode.MAX_RETRIES_EXCEEDED,
            message=message,
            severity=ErrorSeverity.ERROR,
            recoverable=False,
            recovery_strategy=RecoveryStrategy.NONE
        )
        self.update_context(original_error_code=original_error.code.value, **kwargs)


# ========== 辅助函数 ==========

def unwrap_agent_exception(exc: Exception) -> Optional[AgentException]:
    """提取异常链中的 AgentException"""
    current = exc
    seen = set()

    while current is not None:
        if isinstance(current, AgentException):
            return current
        if id(current) in seen:
            break
        seen.add(id(current))

        # 获取 __cause__ 或 __context__
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)

    return None


def is_recoverable(exc: Exception) -> bool:
    """检查异常是否可恢复"""
    agent_exc = unwrap_agent_exception(exc)
    if agent_exc:
        return agent_exc.recoverable
    return False


def get_recovery_strategy(exc: Exception) -> RecoveryStrategy:
    """获取异常的恢复策略"""
    agent_exc = unwrap_agent_exception(exc)
    if agent_exc:
        return agent_exc.recovery_strategy
    return RecoveryStrategy.NONE


def format_error_for_user(exc: Exception, include_details: bool = False) -> str:
    """格式化异常信息供用户查看

    Args:
        exc: 异常对象
        include_details: 是否包含详细信息

    Returns:
        格式化后的错误消息
    """
    agent_exc = unwrap_agent_exception(exc)

    if agent_exc:
        # 使用 AgentException 的结构化信息
        user_msg = f"错误: {agent_exc.message}"

        if agent_exc.severity == ErrorSeverity.CRITICAL:
            user_msg = f"严重错误: {agent_exc.message}"
        elif agent_exc.severity == ErrorSeverity.WARNING:
            user_msg = f"警告: {agent_exc.message}"

        if include_details:
            details = []
            if agent_exc.context.session_id:
                details.append(f"会话ID: {agent_exc.context.session_id}")
            if agent_exc.context.agent_type:
                details.append(f"智能体类型: {agent_exc.context.agent_type}")
            if details:
                user_msg += f"\n详情: {', '.join(details)}"

        return user_msg

    # 普通异常
    if isinstance(exc, ConnectionError):
        return f"网络连接错误: {str(exc)}"
    elif isinstance(exc, TimeoutError):
        return f"操作超时: {str(exc)}"
    elif isinstance(exc, PermissionError):
        return f"权限不足: {str(exc)}"
    elif isinstance(exc, FileNotFoundError):
        return f"文件未找到: {str(exc)}"

    return f"发生错误: {str(exc)}"
