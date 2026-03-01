# -*- coding: utf-8 -*-
"""
UI 错误处理助手

提供用户友好的错误提示和处理
"""
from typing import Optional, Callable, Any
from functools import wraps

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

from qfluentwidgets import InfoBar, InfoBarPosition, MessageBox

from src.agent.exceptions import AgentException, ErrorCode
from utils.logger import get_logger

logger = get_logger(__name__)


class UIErrorHandler:
    """UI 错误处理器
    
    提供统一的错误提示和处理
    """
    
    # 错误消息映射
    ERROR_MESSAGES = {
        ErrorCode.UNKNOWN_ERROR: "发生未知错误，请重试",
        ErrorCode.INTERNAL_ERROR: "程序内部错误，请联系开发者",
        
        ErrorCode.AGENT_NOT_INITIALIZED: "智能体未初始化，请检查配置",
        ErrorCode.AGENT_EXECUTION_FAILED: "智能体执行失败，请重试",
        ErrorCode.AGENT_TIMEOUT: "操作超时，请检查网络连接",
        ErrorCode.AGENT_STATE_INVALID: "智能体状态异常，正在恢复...",
        
        ErrorCode.AI_API_ERROR: "AI 服务暂时不可用",
        ErrorCode.AI_AUTHENTICATION_FAILED: "AI 认证失败，请检查 API Key",
        ErrorCode.AI_RATE_LIMIT_EXCEEDED: "请求过于频繁，请稍后再试",
        ErrorCode.AI_CONNECTION_ERROR: "网络连接失败，请检查网络",
        ErrorCode.AI_QUOTA_EXCEEDED: "AI 配额已用完，请升级套餐",
        
        ErrorCode.TOOL_NOT_FOUND: "工具未找到",
        ErrorCode.TOOL_EXECUTION_FAILED: "工具执行失败",
        ErrorCode.TOOL_TIMEOUT: "工具执行超时",
    }
    
    def __init__(self, parent: Optional[QWidget] = None):
        self.parent = parent
    
    def show_error(
        self,
        error: Exception,
        title: str = "错误",
        show_details: bool = False
    ) -> None:
        """显示错误提示
        
        Args:
            error: 异常对象
            title: 标题
            show_details: 是否显示详细信息
        """
        # 获取用户友好的错误消息
        if isinstance(error, AgentException):
            msg = self.ERROR_MESSAGES.get(error.code, error.message)
            code = f" [{error.code.value}]"
        else:
            msg = str(error)
            code = ""
        
        # 记录日志
        logger.error(f"{title}: {msg}{code}", exc_info=error)
        
        # 显示提示
        if self.parent:
            InfoBar.error(
                title=title,
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self.parent
            )
    
    def show_warning(
        self,
        message: str,
        title: str = "警告"
    ) -> None:
        """显示警告提示"""
        if self.parent:
            InfoBar.warning(
                title=title,
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self.parent
            )
    
    def show_success(
        self,
        message: str,
        title: str = "成功"
    ) -> None:
        """显示成功提示"""
        if self.parent:
            InfoBar.success(
                title=title,
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.parent
            )


def safe_ui_operation(error_handler: Optional[UIErrorHandler] = None):
    """UI 操作安全装饰器
    
    自动捕获异常并显示友好提示
    
    Usage:
        @safe_ui_operation(error_handler)
        def on_button_clicked(self):
            # 可能抛出异常的代码
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except AgentException as e:
                if error_handler:
                    error_handler.show_error(e)
                else:
                    logger.error(f"Agent error in {func.__name__}: {e}")
            except Exception as e:
                if error_handler:
                    error_handler.show_error(e, title="操作失败")
                else:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=e)
        return wrapper
    return decorator


# 全局错误处理器实例
_global_handler: Optional[UIErrorHandler] = None


def get_error_handler(parent: Optional[QWidget] = None) -> UIErrorHandler:
    """获取全局错误处理器"""
    global _global_handler
    if _global_handler is None or parent:
        _global_handler = UIErrorHandler(parent)
    return _global_handler