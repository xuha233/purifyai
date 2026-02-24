# -*- coding: utf-8 -*-
"""
结构化异常日志记录模块

提供统一的异常日志记录和查询功能
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import threading
import os

from .exceptions import AgentException, ErrorCode, ErrorSeverity


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorLogEntry:
    """错误日志条目"""
    log_id: str
    session_id: Optional[str]
    agent_type: Optional[str]
    error_code: str
    error_type: str
    error_message: str
    severity: str
    timestamp: str
    duration_ms: int = 0

    # 上下文信息
    workspace: Optional[str] = None
    tool_name: Optional[str] = None
    stack_trace: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)

    # 恢复信息
    recoverable: bool = False
    recovery_strategy: Optional[str] = None
    retry_count: int = 0
    recovery_success: bool = False

    # 用户相关信息
    user_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "log_id": self.log_id,
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "error_code": self.error_code,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "workspace": self.workspace,
            "tool_name": self.tool_name,
            "stack_trace": self.stack_trace,
            "additional_data": self.additional_data,
            "recoverable": self.recoverable,
            "recovery_strategy": self.recovery_strategy,
            "retry_count": self.retry_count,
            "recovery_success": self.recovery_success,
            "user_message": self.user_message
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ErrorLogger:
    """错误日志记录器

    提供线程安全的错误日志记录功能
    """

    def __init__(self, log_file: Optional[str] = None, max_entries: int = 10000):
        self.log_file = log_file
        self.max_entries = max_entries
        self._entries: List[ErrorLogEntry] = []
        self._lock = threading.RLock()
        self._log_counter = 0

        # 确保日志目录存在
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # 加载已有日志
            self._load_from_file()

    def _generate_log_id(self) -> str:
        """生成日志 ID"""
        self._log_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"ERR-{timestamp}-{self._log_counter:06d}"

    def log_exception(
        self,
        exception: Exception,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        workspace: Optional[str] = None,
        tool_name: Optional[str] = None,
        duration_ms: int = 0,
        additional_data: Optional[Dict[str, Any]] = None,
        include_stack: bool = True
    ) -> ErrorLogEntry:
        """记录异常

        Args:
            exception: 异常对象
            session_id: 会话 ID
            agent_type: 智能体类型
            workspace: 工作目录
            tool_name: 工具名称
            duration_ms: 持续时间（毫秒）
            additional_data: 额外数据
            include_stack: 是否包含堆栈信息

        Returns:
            日志条目
        """
        import traceback

        # 提取 AgentException 信息
        if isinstance(exception, AgentException):
            error_code = exception.code.value
            error_type = exception.code.name
            error_message = exception.message
            severity = exception.severity.value
            recoverable = exception.recoverable
            recovery_strategy = exception.recovery_strategy.value if exception.recovery_strategy else None
            retry_count = len(exception.recovery_attempts)
            recovery_success = any(ra.success for ra in exception.recovery_attempts)

            # 从上下文获取信息
            if exception.context.session_id:
                session_id = exception.context.session_id
            if exception.context.agent_type:
                agent_type = exception.context.agent_type
            if exception.context.workspace:
                workspace = exception.context.workspace

            stack_trace = exception.context.stack_trace
            if include_stack and not stack_trace:
                stack_trace = traceback.format_exc()

            additional_data = additional_data or {}
            additional_data.update(exception.context.additional_data)

        else:
            # 处理普通异常
            error_code = "E0000"
            error_type = type(exception).__name__
            error_message = str(exception)
            severity = self._determine_severity(exception)
            recoverable = False
            recovery_strategy = None
            retry_count = 0
            recovery_success = False
            stack_trace = traceback.format_exc() if include_stack else ""

        # 创建日志条目
        entry = ErrorLogEntry(
            log_id=self._generate_log_id(),
            session_id=session_id,
            agent_type=agent_type,
            error_code=error_code,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms,
            workspace=workspace,
            tool_name=tool_name,
            stack_trace=stack_trace,
            additional_data=additional_data or {},
            recoverable=recoverable,
            recovery_strategy=recovery_strategy,
            retry_count=retry_count,
            recovery_success=recovery_success
        )

        # 添加到内存
        with self._lock:
            self._entries.append(entry)
            # 限制条目数量
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]

        # 写入文件
        self._write_to_file(entry)

        # 输出到标准日志
        self._log_to_standard_logger(entry)

        return entry

    def _determine_severity(self, exception: Exception) -> str:
        """根据异常类型确定严重程度"""
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return ErrorSeverity.WARNING.value
        if isinstance(exception, PermissionError):
            return ErrorSeverity.ERROR.value
        if isinstance(exception, FileNotFoundError):
            return ErrorSeverity.WARNING.value
        if isinstance(exception, (ValueError, TypeError)):
            return ErrorSeverity.ERROR.value
        return ErrorSeverity.ERROR.value

    def _write_to_file(self, entry: ErrorLogEntry):
        """写入日志文件"""
        if not self.log_file:
            return

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            # 避免递归错误
            print(f"写入错误日志失败: {e}")

    def _load_from_file(self):
        """从文件加载日志"""
        if not self.log_file or not os.path.exists(self.log_file):
            return

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        entry = ErrorLogEntry(
                            log_id=data.get("log_id", ""),
                            session_id=data.get("session_id"),
                            agent_type=data.get("agent_type"),
                            error_code=data.get("error_code", ""),
                            error_type=data.get("error_type", ""),
                            error_message=data.get("error_message", ""),
                            severity=data.get("severity", "error"),
                            timestamp=data.get("timestamp", ""),
                            duration_ms=data.get("duration_ms", 0),
                            workspace=data.get("workspace"),
                            tool_name=data.get("tool_name"),
                            stack_trace=data.get("stack_trace", ""),
                            additional_data=data.get("additional_data", {}),
                            recoverable=data.get("recoverable", False),
                            recovery_strategy=data.get("recovery_strategy"),
                            retry_count=data.get("retry_count", 0),
                            recovery_success=data.get("recovery_success", False),
                            user_message=data.get("user_message", "")
                        )
                        with self._lock:
                            self._entries.append(entry)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            pass

    def _log_to_standard_logger(self, entry: ErrorLogEntry):
        """输出到标准日志"""
        from utils.logger import get_logger
        logger = get_logger(__name__)

        log_method = {
            "debug": logger.debug,
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
            "critical": logger.critical
        }.get(entry.severity, logger.error)

        log_msg = (
            f"[ERROR_LOG] {entry.log_id} | {entry.error_code}:{entry.error_type} | "
            f"{entry.error_message}"
        )

        if entry.agent_type:
            log_msg += f" | Agent: {entry.agent_type}"
        if entry.tool_name:
            log_msg += f" | Tool: {entry.tool_name}"

        log_method(log_msg)

    def get_errors(
        self,
        session_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        tool_name: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[ErrorLogEntry]:
        """查询错误日志

        Args:
            session_id: 会话 ID 过滤
            agent_type: 智能体类型过滤
            tool_name: 工具名称过滤
            severity: 严重程度过滤
            limit: 最大返回数量

        Returns:
            错误日志条目列表
        """
        with self._lock:
            results = self._entries.copy()

        # 应用过滤
        if session_id:
            results = [e for e in results if e.session_id == session_id]
        if agent_type:
            results = [e for e in results if e.agent_type == agent_type]
        if tool_name:
            results = [e for e in results if e.tool_name == tool_name]
        if severity:
            results = [e for e in results if e.severity == severity]

        # 按时间倒序
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # 限制数量
        return results[:limit]

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        with self._lock:
            entries = self._entries.copy()

        if not entries:
            return {
                "total_errors": 0,
                "by_severity": {},
                "by_error_code": {},
                "by_agent_type": {},
                "by_tool_name": {},
                "recoverable_count": 0,
                "recovery_success_rate": 0.0
            }

        stats = {
            "total_errors": len(entries)
        }

        # 按严重程度统计
        stats["by_severity"] = {}
        for entry in entries:
            stats["by_severity"][entry.severity] = stats["by_severity"].get(entry.severity, 0) + 1

        # 按错误代码统计
        stats["by_error_code"] = {}
        for entry in entries:
            code = f"{entry.error_code}:{entry.error_type}"
            stats["by_error_code"][code] = stats["by_error_code"].get(code, 0) + 1

        # 按智能体类型统计
        stats["by_agent_type"] = {}
        for entry in entries:
            if entry.agent_type:
                stats["by_agent_type"][entry.agent_type] = stats["by_agent_type"].get(entry.agent_type, 0) + 1

        # 按工具名称统计
        stats["by_tool_name"] = {}
        for entry in entries:
            if entry.tool_name:
                stats["by_tool_name"][entry.tool_name] = stats["by_tool_name"].get(entry.tool_name, 0) + 1

        # 可恢复性统计
        recoverable_entries = [e for e in entries if e.recoverable]
        stats["recoverable_count"] = len(recoverable_entries)
        recovered_entries = [e for e in recoverable_entries if e.recovery_success]
        stats["recovery_success_rate"] = (
            len(recovered_entries) / len(recoverable_entries) * 100
            if recoverable_entries else 0
        )

        return stats

    def clear(self):
        """清空所有日志"""
        with self._lock:
            self._entries.clear()

    def get_recent_errors(self, limit: int = 10) -> List[ErrorLogEntry]:
        """获取最近的错误"""
        with self._lock:
            sorted_entries = sorted(self._entries, key=lambda e: e.timestamp, reverse=True)
            return sorted_entries[:limit]


# 全局错误日志记录器
_global_error_logger: Optional[ErrorLogger] = None


def get_error_logger(log_file: Optional[str] = None, max_entries: int = 10000) -> ErrorLogger:
    """获取全局错误日志记录器"""
    global _global_error_logger
    if _global_error_logger is None or log_file is not None:
        _global_error_logger = ErrorLogger(log_file=log_file, max_entries=max_entries)
    return _global_error_logger


def log_exception(
    exception: Exception,
    session_id: Optional[str] = None,
    agent_type: Optional[str] = None,
    workspace: Optional[str] = None,
    tool_name: Optional[str] = None,
    duration_ms: int = 0,
    additional_data: Optional[Dict[str, Any]] = None
) -> ErrorLogEntry:
    """记录异常（便捷函数）"""
    logger = get_error_logger()
    return logger.log_exception(
        exception=exception,
        session_id=session_id,
        agent_type=agent_type,
        workspace=workspace,
        tool_name=tool_name,
        duration_ms=duration_ms,
        additional_data=additional_data
    )
