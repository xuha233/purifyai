"""
错误处理模块 - 提供统一的异常捕获和日志记录功能
"""
import functools
import logging
import traceback
from typing import Callable, Any
from PyQt5.QtCore import QObject, pyqtSignal


# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('purifyai_errors.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def safe_execute(default_return=None, log_prefix: str = ""):
    """
    安全执行装饰器：捕获所有异常并记录日志

    Args:
        default_return: 发生异常时返回的默认值
        log_prefix: 日志前缀
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{log_prefix or func.__name__} 发生异常: {str(e)}")
                logger.debug(traceback.format_exc())
                return default_return
        return wrapper
    return decorator


def catch_errors(func: Callable) -> Callable:
    """简化的错误捕获装饰器，适用于大多数方法"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[{func.__name__}] {str(e)}")
            logger.debug(traceback.format_exc())
            # 对于 None 返回的方法，静默返回 None
            # 如果有 Qt 信号，可以选择发送错误信号
            return None
    return wrapper


class ErrorHandler(QObject):
    """错误处理器 - 集中管理应用中的错误"""

    # 信号：当发生错误时发送
    error_occurred = pyqtSignal(str, str)  # (error_title, error_message)

    def __init__(self, parent=None):
        super().__init__(parent)

    def log_error(self, error: Exception, context: str = ""):
        """记录错误并发送信号

        Args:
            error: 异常对象
            context: 错误发生的上下文信息
        """
        error_type = type(error).__name__
        error_msg = str(error)
        full_msg = f"{context}: {error_type} - {error_msg}" if context else error_msg

        logger.error(full_msg)
        logger.debug(traceback.format_exc())

        # 发送错误信号
        self.error_occurred.emit(error_type, full_msg)

    def log_warning(self, message: str, context: str = ""):
        """记录警告"""
        full_msg = f"{context}: {message}" if context else message
        logger.warning(full_msg)

    def log_info(self, message: str, context: str = ""):
        """记录信息"""
        full_msg = f"{context}: {message}" if context else message
        logger.info(full_msg)


# 全局错误处理器实例
error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    return error_handler


class SafeSignal(QObject):
    """安全的信号发送器 - 捕获信号发送中的异常"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def emit_safe(self, signal, *args, **kwargs):
        """安全发送信号"""
        try:
            signal.emit(*args, **kwargs)
        except Exception as e:
            error_handler.log_error(e, f"信号发送失败")
