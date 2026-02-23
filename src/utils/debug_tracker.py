"""
调试追踪器 - 增强的错误和性能监控

用于捕获和分析智能清理工作中的所有异常和性能瓶颈。
提供完整的堆栈跟踪、信号追踪和时间分析。
"""
import sys
import time
import traceback
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class DebugEvent:
    """调试事件数据类"""
    timestamp: float
    level: str  # 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    module: str  # 模块名称
    component: str  # 组件名称
    action: str  # 动作描述
    message: str  # 消息
    traceback_str: Optional[str] = None  # 堆栈跟踪
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文数据


@dataclass
class SignalTrack:
    """信号追踪记录"""
    signal_name: str
    source: str
    destination: str
    timestamp: float
    emitted: bool = True
    received: bool = False
    receive_timestamp: Optional[float] = None
    delay_ms: Optional[float] = None  # 信号延迟


@dataclass
class TimingTrack:
    """时间追踪记录"""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    category: str = "general"  # 'scan', 'analyze', 'ui', 'db', etc.


class DebugTracker:
    """调试追踪器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._events: List[DebugEvent] = []
        self._signal_tracks: Dict[str, List[SignalTrack]] = defaultdict(list)
        self._timing_tracks: Dict[str, TimingTrack] = {}
        self._error_count = 0
        self._warning_count = 0
        self._max_events = 1000  # 最多保留1000个事件
        self._lock = threading.RLock()
        self._session_start = time.time()

        # 性能统计
        self._performance_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'min_time': float('inf'),
            'max_time': 0
        })

        self._initialized = True
        self._log_to_console = True

    def set_console_logging(self, enabled: bool):
        """设置是否输出到控制台"""
        self._lock.acquire()
        try:
            self._log_to_console = enabled
        finally:
            self._lock.release()

    def log_event(self, level: str, module: str, component: str,
                  action: str, message: str, **context):
        """记录调试事件

        Args:
            level: 日志级别
            module: 模块名称
            component: 组件名称
            action: 动作描述
            message: 消息
            **context: 上下文数据
        """
        event = DebugEvent(
            timestamp=time.time(),
            level=level,
            module=module,
            component=component,
            action=action,
            message=message,
            context=context
        )

        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events.pop(0)

            if level == 'ERROR':
                self._error_count += 1
            elif level == 'WARNING':
                self._warning_count += 1

        if self._log_to_console:
            timestamp_str = datetime.fromtimestamp(event.timestamp).strftime('%H:%M:%S.%f')[:-3]
            console_msg = f"[{timestamp_str}] [{level}] [{module}:{component}] {action} - {message}"
            if context:
                console_msg += f" | Context: {context}"
            print(console_msg, file=sys.stderr if level in ('ERROR', 'CRITICAL') else sys.stdout)

    def log_exception(self, level: str, module: str, component: str,
                     action: str, message: str, exc_info=None, **context):
        """记录异常事件（包含堆栈跟踪）

        Args:
            level: 日志级别
            module: 模块名称
            component: 组件名称
            action: 动作描述
            message: 消息
            exc_info: 异常信息（可选，默认使用当前异常）
            **context: 上下文数据
        """
        if exc_info is None:
            exc_info = sys.exc_info()

        traceback_str = None
        if exc_info and exc_info[0] is not None:
            traceback_str = ''.join(traceback.format_exception(*exc_info))

        event = DebugEvent(
            timestamp=time.time(),
            level=level,
            module=module,
            component=component,
            action=action,
            message=message,
            traceback_str=traceback_str,
            context=context
        )

        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events.pop(0)
            self._error_count += 1

        if self._log_to_console:
            timestamp_str = datetime.fromtimestamp(event.timestamp).strftime('%H:%M:%S.%f')[:-3]
            console_msg = f"[{timestamp_str}] [{level}] [{module}:{component}] {action} - {message}"
            if context:
                console_msg += f" | Context: {context}"
            print(console_msg, file=sys.stderr)
            if traceback_str:
                print("堆栈跟踪:", file=sys.stderr)
                print(traceback_str, file=sys.stderr)

    def track_signal(self, signal_name: str, source: str, destination: str,
                    emitted: bool = True, received: bool = False):
        """追踪信号

        Args:
            signal_name: 信号名称
            source: 信号源
            destination: 信号目标
            emitted: 是否已发送
            received: 是否已接收
        """
        track = SignalTrack(
            signal_name=signal_name,
            source=source,
            destination=destination,
            timestamp=time.time(),
            emitted=emitted,
            received=received
        )
        with self._lock:
            self._signal_tracks[signal_name].append(track)
            # 只保留最近的100条
            if len(self._signal_tracks[signal_name]) > 100:
                self._signal_tracks[signal_name].pop(0)

        if self._log_to_console:
            status = "EMITTED" if emitted else "RECEIVED"
            timestamp_str = datetime.fromtimestamp(track.timestamp).strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp_str}] [SIGNAL:TRACK] {signal_name} {status} {source} -> {destination}", file=sys.stdout)

    def start_timing(self, operation: str, category: str = "general"):
        """开始计时

        Args:
            operation: 操作名称
            category: 操作类别
        """
        track = TimingTrack(
            operation=operation,
            start_time=time.time(),
            category=category
        )
        with self._lock:
            key = f"{category}:{operation}"
            self._timing_tracks[key] = track

    def end_timing(self, operation: str, category: str = "general") -> Optional[float]:
        """结束计时

        Args:
            operation: 操作名称
            category: 操作类别

        Returns:
            持续时间（毫秒），如果未找到开始记录则返回 None
        """
        key = f"{category}:{operation}"
        with self._lock:
            track = self._timing_tracks.get(key)
            if track is None or track.end_time is not None:
                return None

            track.end_time = time.time()
            track.duration_ms = (track.end_time - track.start_time) * 1000

            # 更新性能统计
            stats = self._performance_stats[key]
            stats['count'] += 1
            stats['total_time'] += track.duration_ms
            stats['min_time'] = min(stats['min_time'], track.duration_ms)
            stats['max_time'] = max(stats['max_time'], track.duration_ms)

            if self._log_to_console:
                timestamp_str = datetime.fromtimestamp(track.end_time).strftime('%H:%M:%S.%f')[:-3]
                print(f"[{timestamp_str}] [TIMING] {operation} ({category}): {track.duration_ms:.2f}ms", file=sys.stdout)

            return track.duration_ms

    def get_events(self, level: Optional[str] = None,
                   module: Optional[str] = None,
                   limit: int = 100) -> List[DebugEvent]:
        """获取事件

        Args:
            level: 过滤日志级别
            module: 过滤模块
            limit: 最多返回数量

        Returns:
            事件列表
        """
        with self._lock:
            events = list(self._events)

        if level:
            events = [e for e in events if e.level == level]
        if module:
            events = [e for e in events if e.module == module]

        return events[-limit:]

    def get_errors(self, limit: int = 50) -> List[DebugEvent]:
        """获取所有错误事件"""
        return self.get_events(level='ERROR', limit=limit)

    def get_signal_tracks(self, signal_name: Optional[str] = None) -> List[SignalTrack]:
        """获取信号追踪记录"""
        with self._lock:
            if signal_name:
                return list(self._signal_tracks.get(signal_name, []))
            # 返回所有信号追踪
            all_tracks = []
            for tracks in self._signal_tracks.values():
                all_tracks.extend(tracks)
            return all_tracks[-100:]  # 最近100条

    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计"""
        with self._lock:
            result = {}
            for key, stats in self._performance_stats.items():
                if stats['count'] > 0:
                    result[key] = {
                        'count': stats['count'],
                        'total_ms': stats['total_time'],
                        'avg_ms': stats['total_time'] / stats['count'],
                        'min_ms': stats['min_time'],
                        'max_ms': stats['max_time']
                    }
            return result

    def get_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        with self._lock:
            session_duration = time.time() - self._session_start

            return {
                'session_duration_seconds': session_duration,
                'total_events': len(self._events),
                'error_count': self._error_count,
                'warning_count': self._warning_count,
                'signal_tracked_signals': len(self._signal_tracks),
                'tracked_operations': len(self._performance_stats),
                'recent_errors': [
                    {
                        'timestamp': e.timestamp,
                        'level': e.level,
                        'module': e.module,
                        'component': e.component,
                        'action': e.action,
                        'message': e.message
                    }
                    for e in self._events[-20:] if e.level in ('ERROR', 'CRITICAL')
                ]
            }

    def clear(self):
        """清除所有追踪数据"""
        with self._lock:
            self._events.clear()
            self._signal_tracks.clear()
            self._timing_tracks.clear()
            self._error_count = 0
            self._warning_count = 0
            self._session_start = time.time()
            self._performance_stats.clear()


# 便捷函数
def get_debug_tracker() -> DebugTracker:
    """获取调试追踪器实例"""
    return DebugTracker()


def debug_event(level: str, module: str, component: str,
                action: str, message: Optional[str] = None, **context):
    """便捷函数：记录调试事件"""
    tracker = get_debug_tracker()
    # 如果message为None，使用action作为message
    if message is None:
        message = action
    tracker.log_event(level, module, component, action, message, **context)


def debug_exception(module: str, component: str, action: str,
                    message: Optional[str] = None, exc_info=None, **context):
    """便捷函数：记录异常"""
    tracker = get_debug_tracker()
    # 如果message为None，使用action作为message
    if message is None:
        message = action
    tracker.log_exception('ERROR', module, component, action, message, exc_info, **context)


def track_signal(signal_name: str, source: str, destination: str,
                emitted: bool = True, received: bool = False):
    """便捷函数：追踪信号"""
    tracker = get_debug_tracker()
    tracker.track_signal(signal_name, source, destination, emitted, received)


def timing_context(operation: str, category: str = "general"):
    """计时上下文管理器

    用法:
        with timing_context('scan_directory', 'scan'):
            # 执行扫描
            pass
    """
    class TimingContext:
        def __init__(self, operation, category):
            self.operation = operation
            self.category = category
            self.tracker = get_debug_tracker()

        def __enter__(self):
            self.tracker.start_timing(self.operation, self.category)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = self.tracker.end_timing(self.operation, self.category)
            if exc_type:
                # 如果有异常，记录
                self.tracker.log_exception(
                    'ERROR',
                    self.category,
                    self.operation,
                    'Exception in timing context',
                    exc_info=(exc_type, exc_val, exc_tb)
                )
            return False  # 不抑制异常

    return TimingContext(operation, category)


def get_debug_summary() -> Dict[str, Any]:
    """获取调试摘要"""
    tracker = get_debug_tracker()
    return tracker.get_summary()


def get_debug_errors(limit: int = 50) -> List[DebugEvent]:
    """获取调试错误"""
    tracker = get_debug_tracker()
    return tracker.get_errors(limit)


def get_performance_stats() -> Dict[str, Dict[str, Any]]:
    """获取性能统计"""
    tracker = get_debug_tracker()
    return tracker.get_performance_stats()


def clear_debug():
    """清除调试数据"""
    tracker = get_debug_tracker()
    tracker.clear()
