"""
日志配置模块
提供统一的日志记录功能，输出到文件和控制台
支持开发者控制台的实时监控
"""
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal


class ConsoleLogHandler(logging.Handler, QObject):
    """向控制台发送日志信号的处理器，用于实时UI更新
    同时将 ERROR/CRITICAL 级别日志传递到调试监控器
    """

    # 禁用 shutdown 时的 flush，避免 QObject 被删除时的 RuntimeError
    flushOnClose = False

    log_signal = pyqtSignal(str, str, str, str)  # level, logger_name, timestamp, message

    def __init__(self, parent=None):
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)
        self.setFormatter(logging.Formatter('%(message)s'))
        self._closed = False

    def emit(self, record):
        """发射日志记录作为信号，并捕获错误到调试监控器"""
        if self._closed:
            return

        try:
            msg = self.format(record)
            # 直接使用 record.created 生成时间戳
            timestamp = self._format_timestamp(record)
            self.log_signal.emit(record.levelname, record.name, timestamp, msg)

            # 将 ERROR 和 CRITICAL 级别的日志传递到调试监控器
            if record.levelno >= logging.ERROR:
                self._forward_to_debug_monitor(record, msg, timestamp)

        except (RuntimeError, Exception):
            # RuntimeObjectError - QObject 已被删除，或其他异常
            self.handleError(record)

    def close(self):
        """安全关闭处理器"""
        self._closed = True
        try:
            # 先断开信号连接
            self.log_signal.disconnect()
        except (RuntimeError, Exception):
            pass
        super().close()

    def _forward_to_debug_monitor(self, record, msg: str, timestamp: str):
        """将错误日志转发到调试监控器"""
        try:
            from .debug_monitor import get_debug_monitor
            monitor = get_debug_monitor()

            # 创建一个虚构的异常用于记录
            class LoggedError(Exception):
                pass

            error = LoggedError(msg)

            # 提取上下文信息
            context = {
                'logger_name': record.name,
                'level': record.levelname,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'file': record.pathname,
                'timestamp': timestamp
            }

            # 尝试从消息中提取更多上下文
            if ' | Context: ' in msg:
                try:
                    import re
                    match = re.search(r'Context: ({[^}]+})', msg)
                    if match:
                        import json
                        extracted = json.loads(match.group(1))
                        context.update(extracted)
                except:
                    pass

            monitor.capture_error(error, context)
        except Exception:
            # 静默失败，避免日志循环
            pass

    def _format_timestamp(self, record):
        """格式化时间戳为 HH:MM:SS.mmm 格式"""
        try:
            # record.created 是 Unix 时间戳
            dt = datetime.fromtimestamp(record.created)
            return dt.strftime('%H:%M:%S.%f')[:-3]
        except Exception:
            # 如果出错，使用当前时间
            return datetime.now().strftime('%H:%M:%S.%f')[:-3]



# ========== 开发者控制台增强功能 ==========

def setup_root_logger_for_console(level: int = logging.DEBUG):
    """配置根日志器，确保所有模块的日志都能被开发者控制台捕获

    Args:
        level: 最低日志级别，默认为 DEBUG
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除可能存在的控制台处理器（避免重复）
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(console_handler)


def get_module_logger(module_name: str) -> logging.Logger:
    """获取指定模块的日志记录器

    Args:
        module_name: 模块名称，如 'core.scanner', 'ui.system_cleaner'

    Returns:
        配置好的 Logger 实例
    """
    return logging.getLogger(module_name)


def log_scan_event(logger: logging.Logger, action: str, target: str,
                   count: Optional[int] = None, size: Optional[str] = None,
                   **kwargs):
    """记录扫描事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'START', 'PROGRESS', 'COMPLETE', 'ITEM_FOUND'
        target: 扫描目标
        count: 项目数量
        size: 大小信息
        **kwargs: 其他附加信息
    """
    message_parts = [f"[扫描:{action}]", f"目标: {target}"]

    if count is not None:
        message_parts.append(f"项目数: {count}")

    if size is not None:
        message_parts.append(f"大小: {size}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    logger.info(" ".join(message_parts))


def log_clean_event(logger: logging.Logger, action: str, target: str,
                   items: Optional[List[str]] = None, deleted: Optional[int] = None,
                   freed: Optional[str] = None, **kwargs):
    """记录清理事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'START', 'ITEM_DELETED', 'COMPLETE'
        target: 清理目标
        items: 清理的项目列表
        deleted: 删除的数量
        freed: 释放的空间
        **kwargs: 其他附加信息
    """
    message_parts = [f"[清理:{action}]", f"目标: {target}"]

    if deleted is not None:
        message_parts.append(f"删除: {deleted} 项")

    if freed is not None:
        message_parts.append(f"释放: {freed}")

    if items:
        sample = ", ".join(items[:3])  # 只显示前3个
        if len(items) > 3:
            sample += f"... (共 {len(items)} 项)"
        message_parts.append(f"项目: [{sample}]")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    logger.info(" ".join(message_parts))


def log_api_event(logger: logging.Logger, action: str, endpoint: str,
                 status: Optional[str] = None, duration_ms: Optional[int] = None,
                 request_size: Optional[int] = None, response_size: Optional[int] = None,
                 error: Optional[str] = None, **kwargs):
    """记录 API 事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'REQUEST', 'RESPONSE', 'ERROR'
        endpoint: API 端点
        status: HTTP 状态码
        duration_ms: 请求耗时（毫秒）
        request_size: 请求大小
        response_size: 响应大小
        error: 错误信息
        **kwargs: 其他附加信息
    """
    message_parts = [f"[API:{action}]", f"端点: {endpoint}"]

    if status is not None:
        message_parts.append(f"状态: {status}")

    if duration_ms is not None:
        message_parts.append(f"耗时: {duration_ms}ms")

    if request_size is not None:
        message_parts.append(f"请求大小: {request_size} 字符")

    if response_size is not None:
        message_parts.append(f"响应大小: {response_size} 字符")

    if error:
        message_parts.append(f"错误: {error}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    if action == 'ERROR' or error:
        logger.error(" ".join(message_parts))
    else:
        logger.info(" ".join(message_parts))


def log_ui_event(logger: logging.Logger, action: str, page: str,
                 element: Optional[str] = None, **kwargs):
    """记录 UI 事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'CLICK', 'NAVIGATE', 'SCAN', 'CLEAN'
        page: 页面名称
        element: UI 元素名称
        **kwargs: 其他附加信息
    """
    message_parts = [f"[UI:{action}]", f"页面: {page}"]

    if element:
        message_parts.append(f"元素: {element}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    logger.debug(" ".join(message_parts))


def log_performance(logger: logging.Logger, operation: str, duration_ms: int,
                    **kwargs):
    """记录性能数据的专用函数

    Args:
        logger: 日志记录器
        operation: 操作名称
        duration_ms: 耗时（毫秒）
        **kwargs: 其他附加信息
    """
    message_parts = [f"[性能]", f"操作: {operation}", f"耗时: {duration_ms}ms"]

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    duration_category = (
        "快速" if duration_ms < 100 else
        "正常" if duration_ms < 1000 else
        "较慢" if duration_ms < 5000 else
        "慢"
    )
    message_parts.append(f"评级: {duration_category}")

    logger.info(" ".join(message_parts))


def log_database_event(logger: logging.Logger, action: str, table: str,
                       rows: Optional[int] = None, error: Optional[str] = None,
                       **kwargs):
    """记录数据库事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'QUERY', 'INSERT', 'UPDATE', 'DELETE'
        table: 表名
        rows: 影响行数
        error: 错误信息
        **kwargs: 其他附加信息
    """
    message_parts = [f"[数据库:{action}]", f"表: {table}"]

    if rows is not None:
        message_parts.append(f"影响行数: {rows}")

    if error:
        message_parts.append(f"错误: {error}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    if action == 'ERROR' or error:
        logger.error(" ".join(message_parts))
    else:
        logger.debug(" ".join(message_parts))


def log_config_event(logger: logging.Logger, action: str, key: str,
                     value: Optional[Any] = None, **kwargs):
    """记录配置事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'READ', 'WRITE', 'CHANGE'
        key: 配置键
        value: 配置值
        **kwargs: 其他附加信息
    """
    message_parts = [f"[配置:{action}]", f"键: {key}"]

    if value is not None:
        # 限制值长度，避免过长
        str_value = str(value)
        if len(str_value) > 100:
            str_value = str_value[:100] + "..."
        message_parts.append(f"值: {str_value}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    logger.debug(" ".join(message_parts))


def log_scheduler_event(logger: logging.Logger, action: str, task_type: str,
                       next_run: Optional[str] = None, **kwargs):
    """记录调度器事件的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'SCHEDULED', 'TRIGGERED', 'SKIPPED'
        task_type: 任务类型
        next_run: 下次运行时间
        **kwargs: 其他附加信息
    """
    message_parts = [f"[调度器:{action}]", f"任务: {task_type}"]

    if next_run:
        message_parts.append(f"下次运行: {next_run}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    logger.info(" ".join(message_parts))


def log_file_operation(logger: logging.Logger, action: str, path: str,
                       size: Optional[int] = None, error: Optional[str] = None,
                       **kwargs):
    """记录文件操作的专用函数

    Args:
        logger: 日志记录器
        action: 动作类型，如 'READ', 'WRITE', 'DELETE', 'SCAN'
        path: 文件路径
        size: 文件大小
        error: 错误信息
        **kwargs: 其他附加信息
    """
    # 限制路径长度
    display_path = path
    if len(display_path) > 150:
        display_path = "..." + display_path[-150:]

    message_parts = [f"[文件:{action}]", f"路径: {display_path}"]

    if size is not None:
        message_parts.append(f"大小: {size} 字节")

    if error:
        message_parts.append(f"错误: {error}")

    if kwargs:
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        message_parts.append(extra_info)

    if action == 'ERROR' or error:
        logger.debug(" ".join(message_parts))  # 文件操作较多，使用 DEBUG

    logger.debug(" ".join(message_parts))


# ========== 原有函数 ==========

def setup_logger(
    name: str = 'PurifyAI',
    log_file: str = None,
    level: int = logging.INFO,
    console_level: int = logging.INFO
) -> logging.Logger:
    """配置日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径，如果为 None 则只输出到控制台
        level: 文件日志级别
        console_level: 控制台日志级别

    Returns:
        configured Logger instance
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # 清除已有的处理器

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定了文件路径）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_default_log_path() -> str:
    """获取默认日志文件路径

    Returns:
        日志文件路径
    """
    # 使用 AppData 目录作为日志存储位置
    app_data_dir = os.path.join(
        os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
        'PurifyAI',
        'logs'
    )

    # 确保目录存在
    os.makedirs(app_data_dir, exist_ok=True)

    # 按日期创建日志文件
    today = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(app_data_dir, f'purifyai_{today}.log')


def get_logger(name: str = 'PurifyAI') -> logging.Logger:
    """获取日志记录器（使用默认配置）

    Args:
        name: 日志记录器名称

    Returns:
        configured Logger instance
    """
    logger = logging.getLogger(name)

    # 如果还没有配置处理器，则进行配置
    if not logger.handlers:
        setup_logger(
            name=name,
            log_file=get_default_log_path(),
            level=logging.INFO,
            console_level=logging.DEBUG
        )

    return logger


# 默认日志记录器实例
default_logger = get_logger()


def debug(message: str):
    """记录调试日志"""
    default_logger.debug(message)


def info(message: str):
    """记录信息日志"""
    default_logger.info(message)


def warning(message: str):
    """记录警告日志"""
    default_logger.warning(message)


def error(message: str):
    """记录错误日志"""
    default_logger.error(message)


def critical(message: str):
    """记录严重错误日志"""
    default_logger.critical(message)


def exception(message: str):
    """记录异常日志（包含堆栈跟踪）"""
    default_logger.exception(message)
