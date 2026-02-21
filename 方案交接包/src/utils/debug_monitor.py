"""
高级调试监控模块 - 提供更灵活的错误追踪和性能监控（增强版）

功能：
1. 结构化日志追踪
2. 错误上下文捕获
3. 函数调用链追踪
4. 性能监控
5. 内存使用监控
6. 线程状态监控
7. 网络活动监控
8. 实时统计和仪表板
"""
import os
import logging
import sys
import traceback
import threading
import time
import inspect
import gc
import psutil
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, ContextManager
from functools import wraps
from collections import defaultdict, deque
from contextlib import contextmanager
import platform

# 配置
MAX_ERROR_LOGS = 1000
_MAX_STACK_DEPTH = 20
_MAX_PERFORMANCE_LOGS = 500
_MAX_MEMORY_SAMPLES = 200
_MAX_THREAD_SAMPLES = 200
_MAX_NETWORK_SAMPLES = 100


class ErrorContext:
    """错误上下文信息"""
    def __init__(self, error_type: str, message: str, traceback_str: str,
                 timestamp: datetime, context_info: Dict[str, Any]):
        self.error_type = error_type
        self.message = message
        self.traceback_str = traceback_str
        self.timestamp = timestamp
        self.context_info = context_info


class CallStack:
    """函数调用栈追踪器"""
    def __init__(self):
        self.stack: List[Dict[str, Any]] = []
        self.start_time: float = time.time()

    def push(self, func_name: str, args: tuple = None, kwargs: dict = None,
            module: str = None, file: str = None, line: int = None):
        """压入调用栈"""
        self.stack.append({
            'function': func_name,
            'args': args if args else (),
            'kwargs': kwargs if kwargs else {},
            'module': module,
            'file': file,
            'line': line,
            'timestamp': time.time()
        })

    def pop(self) -> Optional[Dict[str, Any]]:
        """弹出调用栈"""
        return self.stack.pop() if self.stack else None

    def get_call_chain(self) -> str:
        """获取调用链字符串"""
        if not self.stack:
            return "无"
        return " -> ".join(frame['function'] for frame in self.stack)

    def get_context_dict(self) -> Dict[str, Any]:
        """获取当前上下文字典"""
        return {
            'current_function': self.stack[-1]['function'] if self.stack else None,
            'module': self.stack[-1]['module'] if self.stack else None,
            'file': self.stack[-1]['file'] if self.stack else None,
            'line': self.stack[-1]['line'] if self.stack else None,
            'call_depth': len(self.stack),
            'call_chain': self.get_call_chain()
        }


class MemoryMonitor:
    """内存使用监控器"""
    def __init__(self):
        self.samples: deque = deque(maxlen=_MAX_MEMORY_SAMPLES)
        self._process = psutil.Process()
        self._start_memory_mb = 0

        try:
            self._start_memory_mb = self._process.memory_info().rss / (1024 * 1024)
        except:
            pass

    def sample(self) -> Dict[str, Any]:
        """采样内存状态"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            # 系统内存
            sys_memory = psutil.virtual_memory()

            # GC 统计
            gc_stats = gc.get_stats() if hasattr(gc, 'get_stats') else []
            gc_counts = gc.get_count()

            sample = {
                'timestamp': datetime.now(),
                'rss_mb': memory_info.rss / (1024 * 1024),  # 驻留集大小
                'vms_mb': memory_info.vms / (1024 * 1024),  # 虚拟内存大小
                'peak_mb': memory_info.rss / (1024 * 1024),  # 当前峰值（简化）
                'percent': sys_memory.percent,
                'available_mb': sys_memory.available / (1024 * 1024),
                'total_mb': sys_memory.total / (1024 * 1024),
                'gc_objects': len(gc.get_objects()) if hasattr(gc, 'get_objects') else 0,
                'gc_counts': gc_counts,
                'gc_collections': sum(stat.get('collections', 0) for stat in gc_stats) if gc_stats else 0,
                'delta_mb': 0  # 与上次采样的差值
            }

            # 计算增量
            if self.samples:
                last_sample = self.samples[-1]
                sample['delta_mb'] = sample['rss_mb'] - last_sample['rss_mb']

            self.samples.append(sample)
            return sample

        except Exception as e:
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'rss_mb': 0,
                'delta_mb': 0
            }

    def get_memory_growth(self) -> float:
        """获取内存增长率 (MB/分钟)"""
        if len(self.samples) < 2:
            return 0.0

        start = self.samples[0]
        end = self.samples[-1]

        if start.get('error') or end.get('error'):
            return 0.0

        time_diff = (end['timestamp'] - start['timestamp']).total_seconds()
        if time_diff < 1:
            return 0.0

        memory_diff = end['rss_mb'] - start['rss_mb']
        return (memory_diff / time_diff) * 60  # MB/分钟

    def get_stats(self) -> Dict[str, Any]:
        """获取内存统计"""
        if not self.samples:
            return {}

        recent = list(self.samples)[-60:]  # 最近60个样本

        rss_values = [s.get('rss_mb', 0) for s in recent if not s.get('error')]
        delta_values = [s.get('delta_mb', 0) for s in recent if not s.get('error')]

        return {
            'current_mb': rss_values[-1] if rss_values else 0,
            'peak_mb': max(rss_values) if rss_values else 0,
            'min_mb': min(rss_values) if rss_values else 0,
            'avg_mb': sum(rss_values) / len(rss_values) if rss_values else 0,
            'growth_mb_per_min': self.get_memory_growth(),
            'trend': 'increasing' if delta_values and sum(delta_values[-10:]) > 0 else 'stable',
            'gc_objects': recent[-1].get('gc_objects', 0) if recent else 0,
            'gc_collections': recent[-1].get('gc_collections', 0) if recent else 0,
            'system_percent': recent[-1].get('percent', 0) if recent else 0,
            'samples_count': len(self.samples)
        }

    def check_memory_warnings(self) -> List[Dict[str, Any]]:
        """检查内存警告"""
        warnings = []

        if not self.samples:
            return warnings

        stats = self.get_stats()
        current = stats.get('current_mb', 0)

        # 高内存使用警告 (>1GB)
        if current > 1024:
            warnings.append({
                'level': 'warning',
                'type': 'high_memory',
                'message': f'内存使用较高: {current:.1f} MB',
                'value': current
            })

        # 内存泄漏警告
        growth = stats.get('growth_mb_per_min', 0)
        if growth > 10:  # 每分钟增长超过10MB
            warnings.append({
                'level': 'warning',
                'type': 'memory_leak',
                'message': f'可能存在内存泄漏: 增长率 {growth:.1f} MB/分钟',
                'value': growth
            })

        # 系统内存低警告
        sys_percent = stats.get('system_percent', 0)
        if sys_percent > 90:  # 系统内存使用超过90%
            warnings.append({
                'level': 'critical',
                'type': 'low_system_memory',
                'message': f'系统内存不足: 使用率 {sys_percent:.1f}%',
                'value': sys_percent
            })

        return warnings


class ThreadMonitor:
    """线程监控器"""
    def __init__(self):
        self.samples: deque = deque(maxlen=_MAX_THREAD_SAMPLES)
        self.thread_counts: deque = deque(maxlen=500)
        self.active_threads = set()

    def sample(self) -> Dict[str, Any]:
        """采样线程状态"""
        try:
            current_threads = set(threading.enumerate())
            active_count = threading.active_count()

            # 统计线程序列
            main_thread = threading.main_thread() if threading.main_thread() in current_threads else None

            # 分类线程
            daemon_threads = [t for t in current_threads if t.daemon and t is not main_thread]
            non_daemon_threads = [t for t in current_threads if not t.daemon and t is not main_thread]

            sample = {
                'timestamp': datetime.now(),
                'total_count': active_count,
                'active_count': active_count,
                'daemon_count': len(daemon_threads),
                'non_daemon_count': len(non_daemon_threads),
                'main_thread_alive': main_thread.is_alive() if main_thread else False,
                'threads': [
                    {
                        'name': t.name,
                        'daemon': t.daemon,
                        'alive': t.is_alive(),
                        'ident': t.ident
                    }
                    for t in current_threads[:20]  # 只记录前20个
                ],
                'thread_count_delta': active_count - (self.thread_counts[-1] if self.thread_counts else 0)
            }

            self.samples.append(sample)
            self.thread_counts.append(active_count)
            return sample

        except Exception as e:
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'total_count': 0
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取线程统计"""
        if not self.samples:
            return {}

        recent = list(self.samples)[-30:]
        counts = [s.get('total_count', 0) for s in recent if not s.get('error')]

        if not counts:
            return {}

        # 检测线程泄漏
        is_leaking = len(counts) > 5 and counts[-1] > max(counts[:-5]) + 5

        return {
            'current_count': counts[-1],
            'max_count': max(counts),
            'min_count': min(counts),
            'avg_count': sum(counts) / len(counts),
            'trend': 'increasing' if len(counts) >= 5 and counts[-1] > counts[-5] else 'stable',
            'is_leaking': is_leaking,
            'samples_count': len(self.samples)
        }

    def check_thread_warnings(self) -> List[Dict[str, Any]]:
        """检查线程警告"""
        warnings = []

        if not self.samples:
            return warnings

        stats = self.get_stats()

        # 线程泄漏检测
        if stats.get('is_leaking'):
            warnings.append({
                'level': 'warning',
                'type': 'thread_leak',
                'message': f'可能存在线程泄漏: 线程数持续增长',
                'value': stats.get('current_count', 0)
            })

        # 高线程数警告
        if stats.get('current_count', 0) > 50:
            warnings.append({
                'level': 'warning',
                'type': 'high_thread_count',
                'message': f'线程数较高: {stats.get("current_count", 0)}',
                'value': stats.get('current_count', 0)
            })

        return warnings


class NetworkMonitor:
    """网络活动监控器"""
    def __init__(self):
        self.samples: deque = deque(maxlen=_MAX_NETWORK_SAMPLES)
        self.api_calls: deque = deque(maxlen=100)
        self._start_counters = None

    def initialize(self):
        """初始化网络计数器"""
        try:
            self._start_counters = psutil.net_io_counters()
        except:
            self._start_counters = None

    def sample(self) -> Dict[str, Any]:
        """采样网络状态"""
        try:
            counters = psutil.net_io_counters()

            sample = {
                'timestamp': datetime.now(),
                'bytes_sent': counters.bytes_sent,
                'bytes_recv': counters.bytes_recv,
                'packets_sent': counters.packets_sent,
                'packets_recv': counters.packets_recv,
                'errin': counters.errin,
                'errout': counters.errout,
                'dropin': counters.dropin,
                'dropout': counters.dropout
            }

            # 计算增量
            if self.samples:
                last_sample = self.samples[-1]
                sample['delta_sent'] = sample['bytes_sent'] - last_sample['bytes_sent']
                sample['delta_recv'] = sample['bytes_recv'] - last_sample['bytes_recv']
            else:
                sample['delta_sent'] = 0
                sample['delta_recv'] = 0

            self.samples.append(sample)
            return sample

        except Exception as e:
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'bytes_sent': 0,
                'bytes_recv': 0
            }

    def record_api_call(self, method: str, url: str, status: int = None,
                       duration_ms: float = None):
        """记录API调用"""
        self.api_calls.append({
            'timestamp': datetime.now(),
            'method': method,
            'url': url,
            'status': status,
            'duration_ms': duration_ms
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取网络统计"""
        if not self._start_counters:
            return {}

        try:
            counters = psutil.net_io_counters()

            total_sent_mb = (counters.bytes_sent - self._start_counters.bytes_sent) / (1024 * 1024)
            total_recv_mb = (counters.bytes_recv - self._start_counters.bytes_recv) / (1024 * 1024)

            # 计算平均吞吐量
            if len(self.samples) >= 2:
                first_sample = self.samples[0]
                last_sample = self.samples[-1]
                time_diff = (last_sample['timestamp'] - first_sample['timestamp']).total_seconds()

                if time_diff > 0:
                    sent_mb = last_sample['bytes_sent'] - first_sample['bytes_sent']
                    recv_mb = last_sample['bytes_recv'] - first_sample['bytes_recv']
                    avg_mbps = (sent_mb + recv_mb) / time_diff if time_diff > 0 else 0
                else:
                    avg_mbps = 0
            else:
                avg_mbps = 0

            # 统计API调用
            api_stats = {}
            for call in list(self.api_calls)[-50:]:
                key = f"{call.get('method', 'UNKNOWN')}"
                if key not in api_stats:
                    api_stats[key] = {'count': 0, 'errors': 0}
                api_stats[key]['count'] += 1
                if call.get('status', 200) >= 400:
                    api_stats[key]['errors'] += 1

            return {
                'total_sent_mb': total_sent_mb,
                'total_recv_mb': total_recv_mb,
                'current_sent_mb': counters.bytes_sent / (1024 * 1024),
                'current_recv_mb': counters.bytes_recv / (1024 * 1024),
                'avg_throughput_mbps': avg_mbps,
                'error_in': counters.errin,
                'error_out': counters.errout,
                'api_calls': api_stats,
                'total_api_calls': len(self.api_calls)
            }

        except Exception as e:
            return {'error': str(e)}


class SystemStats:
    """系统统计"""
    def __init__(self):
        self.start_time = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        try:
            process = psutil.Process()

            # CPU 统计
            cpu_percent = process.cpu_percent(interval=0.1)
            cpu_affinity = len(process.cpu_affinity()) if hasattr(process, 'cpu_affinity') else 0
            cpu_count = psutil.cpu_count()

            # 内存统计（最近一次）
            memory = process.memory_info()

            # 系统信息
            system_info = {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
            }

            # 磁盘统计
            disk_usage = psutil.disk_usage(os.getcwd())

            # 运行时间
            uptime = time.time() - self.start_time
            uptime_str = str(timedelta(seconds=int(uptime)))

            return {
                'uptime': uptime_str,
                'uptime_seconds': uptime,

                # CPU
                'cpu_percent': cpu_percent,
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'cpu_count_physical': psutil.cpu_count(logical=False),
                'cpu_affinity': cpu_affinity,
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},

                # 内存
                'memory_rss_mb': memory.rss / (1024 * 1024),
                'memory_vms_mb': memory.vms / (1024 * 1024),
                'memory_percent': process.memory_percent(),

                # 系统内存
                'system_memory_percent': psutil.virtual_memory().percent,
                'system_memory_total_gb': psutil.virtual_memory().total / (1024 ** 3),
                'system_memory_available_gb': psutil.virtual_memory().available / (1024 ** 3),

                # 磁盘
                'disk_usage_percent': disk_usage.percent,
                'disk_used_gb': disk_usage.used / (1024 ** 3),
                'disk_total_gb': disk_usage.total / (1024 ** 3),
                'disk_free_gb': disk_usage.free / (1024 ** 3),

                # 系统信息
                'system': system_info,

                # 进程
                'thread_count': process.num_threads(),
                'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
                'connections': len(process.connections()) if hasattr(process, 'connections') else 0,
            }

        except Exception as e:
            return {'error': str(e)}


class PerformanceTracker:
    """性能追踪器"""
    def __init__(self):
        self.recordings: deque = deque(maxlen=_MAX_PERFORMANCE_LOGS)
        self.current_operations: Dict[str, float] = {}

    def start_operation(self, name: str, context: Dict[str, Any] = None):
        """开始追踪操作"""
        operation_id = f"{name}_{time.time()}"
        self.current_operations[operation_id] = {
            'name': name,
            'start_time': time.perf_counter(),
            'context': context or {}
        }
        return operation_id

    def end_operation(self, operation_id: str) -> Optional[float]:
        """结束追踪操作，返回耗时（毫秒）"""
        if operation_id not in self.current_operations:
            return None

        op = self.current_operations.pop(operation_id)
        duration_ms = (time.perf_counter() - op['start_time']) * 1000

        self.recordings.append({
            'operation': op['name'],
            'duration_ms': duration_ms,
            'context': op['context'],
            'timestamp': datetime.now()
        })

        return duration_ms

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict]:
        """获取慢操作列表"""
        return [r for r in self.recordings if r['duration_ms'] >= threshold_ms]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.recordings:
            return {}

        durations = [r['duration_ms'] for r in self.recordings]
        return {
            'total_operations': len(self.recordings),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'slow_count': len(self.get_slow_operations()),
            'total_duration_ms': sum(durations)
        }

    def start_operation(self, name: str, context: Dict[str, Any] = None):
        """开始追踪操作"""
        operation_id = f"{name}_{time.time()}"
        self.current_operations[operation_id] = {
            'name': name,
            'start_time': time.perf_counter(),
            'context': context or {}
        }
        return operation_id

    def end_operation(self, operation_id: str) -> Optional[float]:
        """结束追踪操作，返回耗时（毫秒）"""
        if operation_id not in self.current_operations:
            return None

        op = self.current_operations.pop(operation_id)
        duration_ms = (time.perf_counter() - op['start_time']) * 1000

        self.recordings.append({
            'operation': op['name'],
            'duration_ms': duration_ms,
            'context': op['context'],
            'timestamp': datetime.now()
        })

        return duration_ms

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict]:
        """获取慢操作列表"""
        return [r for r in self.recordings if r['duration_ms'] >= threshold_ms]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.recordings:
            return {}

        durations = [r['duration_ms'] for r in self.recordings]
        return {
            'total_operations': len(self.recordings),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'slow_count': len(self.get_slow_operations())
        }


class DebugMonitor:
    """调试监控器 - 单例（增强版）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = logging.getLogger('DebugMonitor')
            self.errors: deque = deque(maxlen=MAX_ERROR_LOGS)
            self.current_call_stack: Optional[CallStack] = None
            self.call_stacks: deque = deque(maxlen=100)  # 存储历史调用栈
            self.performance_tracker = PerformanceTracker()

            # 新增监控器
            self.memory_monitor = MemoryMonitor()
            self.thread_monitor = ThreadMonitor()
            self.network_monitor = NetworkMonitor()
            self.system_stats = SystemStats()

            # 错误统计
            self.error_counts = defaultdict(int)
            self.error_by_module = defaultdict(int)

            # 监控回调
            self.on_error_callbacks = []
            self.on_slow_operation_callbacks = []
            self.on_warning_callbacks = []

            # 启动定时器（可选）
            self._monitoring_active = False
            self._monitor_thread = None

    @contextmanager
    def track_call(self, func_name: str, **context):
        """追踪函数调用上下文"""
        caller_frame = inspect.currentframe().f_back

        try:
            module = inspect.getmodule(caller_frame).__name__
        except:
            module = None

        file = caller_frame.f_code.co_filename
        line = caller_frame.f_lineno

        self.current_call_stack = CallStack()
        self.current_call_stack.push(
            func_name=func_name,
            args=None,
            kwargs=context,
            module=module,
            file=file,
            line=line
        )

        try:
            yield
        finally:
            # 保存调用栈用于调试
            self.call_stacks.append(self.current_call_stack)
            self.current_call_stack = None

    def capture_error(self, exc: Exception, context: Dict[str, Any] = None) -> ErrorContext:
        """捕获错误及上下文信息"""
        exc_type = type(exc).__name__
        error_msg = str(exc)
        traceback_str = traceback.format_exc()

        # 获取调用上下文
        call_context = self.current_call_stack.get_context_dict() if self.current_call_stack else {}
        if context:
            call_context.update(context)

        # 添加函数信息
        caller_frame = inspect.currentframe()
        call_context.update({
            'caller_function': inspect.stack()[2].function if len(inspect.stack()) > 2 else None,
            'caller_file': inspect.stack()[2].filename if len(inspect.stack()) > 2 else None,
            'caller_line': inspect.stack()[2].lineno if len(inspect.stack()) > 2 else None,
        })

        error_context = ErrorContext(
            error_type=exc_type,
            message=error_msg,
            traceback_str=traceback_str,
            timestamp=datetime.now(),
            context_info=call_context
        )

        # 存储错误
        self.errors.append(error_context)
        self.error_counts[exc_type] += 1

        if 'module' in call_context:
            self.error_by_module[call_context['module']] += 1

        # 调用回调
        for callback in self.on_error_callbacks:
            try:
                callback(error_context)
            except Exception as e:
                self.logger.error(f"Error callback failed: {e}")

        # 记录到日志
        self.logger.error(f"[ERROR:{exc_type}] {error_msg} | Context: {call_context}")

        return error_context

    def track_function(self, **tracker_context):
        """函数追踪装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                operation_id = self.performance_tracker.start_operation(
                    func.__name__,
                    {'module': func.__module__}
                )

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.capture_error(e, {'function': func.__name__, 'tracker_context': tracker_context})
                    raise
                finally:
                    duration = self.performance_tracker.end_operation(operation_id)

                    if duration and duration > 1000:  # 超过1秒算慢操作
                        for callback in self.on_slow_operation_callbacks:
                            try:
                                callback(func.__name__, duration, tracker_context)
                            except:
                                pass
            return wrapper
        return decorator

    def track_operation(self, name: str):
        """操作追踪上下文管理器"""
        @contextmanager
        def _tracker():
            operation_id = self.performance_tracker.start_operation(name)
            try:
                yield
            finally:
                self.performance_tracker.end_operation(operation_id)
        return _tracker()

    def get_recent_errors(self, count: int = 10) -> List[ErrorContext]:
        """获取最近的错误"""
        return list(self.errors)[-count:]

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            'total_errors': len(self.errors),
            'by_type': dict(self.error_counts),
            'by_module': dict(self.error_by_module),
            'recent_errors': self.get_recent_errors(5)
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_tracker.get_stats()

    def get_slow_operations(self, threshold_ms: float = 1000) -> List[Dict]:
        """获取慢操作"""
        return self.performance_tracker.get_slow_operations(threshold_ms)

    def add_error_callback(self, callback: Callable[[ErrorContext], None]):
        """添加错误回调"""
        self.on_error_callbacks.append(callback)

    def add_slow_operation_callback(self, callback: Callable[[str, float, Dict], None]):
        """添加慢操作回调"""
        self.on_slow_operation_callbacks.append(callback)

    def add_warning_callback(self, callback: Callable[[Dict], None]):
        """添加警告回调"""
        self.on_warning_callbacks.append(callback)

    def clear_errors(self):
        """清空错误日志"""
        self.errors.clear()
        self.error_counts.clear()
        self.error_by_module.clear()

    # =========== 增强监控方法 ==========

    def sample_all_monitors(self) -> Dict[str, Any]:
        """采样所有监控器"""
        warnings = []

        # 内存监控
        memory_sample = self.memory_monitor.sample()
        memory_warnings = self.memory_monitor.check_memory_warnings()
        warnings.extend(memory_warnings)

        # 线程监控
        thread_sample = self.thread_monitor.sample()
        thread_warnings = self.thread_monitor.check_thread_warnings()
        warnings.extend(thread_warnings)

        # 网络监控
        if not self.network_monitor._start_counters:
            self.network_monitor.initialize()
        network_sample = self.network_monitor.sample()

        # 触发警告回调
        for warning in warnings:
            for callback in self.on_warning_callbacks:
                try:
                    callback(warning)
                except:
                    pass

        return {
            'memory': memory_sample,
            'threads': thread_sample,
            'network': network_sample,
            'warnings': warnings,
            'timestamp': datetime.now()
        }

    def get_full_stats(self) -> Dict[str, Any]:
        """获取完整统计信息"""
        return {
            'errors': self.get_error_stats(),
            'performance': self.get_performance_stats(),
            'memory': self.memory_monitor.get_stats(),
            'threads': self.thread_monitor.get_stats(),
            'network': self.network_monitor.get_stats(),
            'system': self.system_stats.get_stats(),
            'slow_operations': self.get_slow_operations(500),  # 慢操作阈值500ms
        }

    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告（系统整体状态）"""
        stats = self.get_full_stats()

        # 计算健康评分 (0-100)
        health_score = 100

        issues = []

        # 错误扣分
        error_count = stats['errors'].get('total_errors', 0)
        if error_count > 0:
            health_score -= min(error_count * 2, 30)
            issues.append(f"{error_count} 个错误")

        # 慢操作扣分
        slow_count = len(stats.get('slow_operations', []))
        if slow_count > 0:
            health_score -= min(slow_count * 1, 20)
            issues.append(f"{slow_count} 个慢操作")

        # 内存扣分
        memory_stats = stats.get('memory', {})
        system_percent = memory_stats.get('system_percent', 0)
        if system_percent > 90:
            health_score -= 20
            issues.append(f"系统内存使用率 {system_percent}%")
        elif system_percent > 80:
            health_score -= 10
        elif system_percent > 70:
            health_score -= 5

        # 线程扣分
        thread_stats = stats.get('threads', {})
        if thread_stats.get('is_leaking'):
            health_score -= 15
            issues.append("可能存在线程泄漏")

        # 网络错误扣分
        net_stats = stats.get('network', {})
        net_errors = net_stats.get('error_in', 0) + net_stats.get('error_out', 0)
        if net_errors > 10:
            health_score -= 10
            issues.append(f"{net_errors} 个网络错误")

        health_score = max(0, health_score)

        # 确定健康等级
        if health_score >= 90:
            health_level = 'excellent'
        elif health_score >= 75:
            health_level = 'good'
        elif health_score >= 60:
            health_level = 'fair'
        elif health_score >= 40:
            health_level = 'poor'
        else:
            health_level = 'critical'

        return {
            'score': health_score,
            'level': health_level,
            'issues': issues,
            'stats': stats,
            'recommendations': self._get_recommendations(stats)
        }

    def _get_recommendations(self, stats: Dict) -> List[str]:
        """获取改进建议"""
        recommendations = []

        # 错误建议
        error_count = stats['errors'].get('total_errors', 0)
        if error_count > 10:
            recommendations.append("错误数量较多，建议检查日志和错误处理逻辑")

        # 性能建议
        perf_stats = stats.get('performance', {})
        avg_duration = perf_stats.get('avg_duration_ms', 0)
        if avg_duration > 100:
            recommendations.append("平均操作耗时较高，建议优化性能瓶颈")

        slow_ops = stats.get('slow_operations', [])
        if len(slow_ops) > 5:
            recommendations.append("存在多个慢操作，建议分析并优化")

        # 内存建议
        memory_stats = stats.get('memory', {})
        growth = memory_stats.get('growth_mb_per_min', 0)
        if growth > 5:
            recommendations.append("内存持续增长，可能存在内存泄漏，建议检查对象生命周期")

        # 线程建议
        thread_stats = stats.get('threads', {})
        if thread_stats.get('is_leaking'):
            recommendations.append("疑似线程泄漏，建议检查线程创建和销毁逻辑")

        return recommendations

    def start_background_monitoring(self, interval: float = 5.0):
        """启动后台监控"""
        if self._monitoring_active:
            return

        self._monitoring_active = True

        def monitor_loop():
            while self._monitoring_active:
                try:
                    self.sample_all_monitors()
                except Exception as e:
                    self.logger.error(f"监控采样失败: {e}")
                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("后台监控已启动")

    def stop_background_monitoring(self):
        """停止后台监控"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("后台监控已停止")

    def record_api_call(self, method: str, url: str, status: int = None,
                       duration_ms: float = None):
        """记录API调用"""
        self.network_monitor.record_api_call(method, url, status, duration_ms)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据（用于UI显示）"""
        stats = self.get_full_stats()
        health = self.get_health_report()

        # 构建实时数据
        recent_errors = [
            {
                'type': e.error_type,
                'message': e.message[:100],
                'timestamp': e.timestamp.strftime("%H:%M:%S"),
                'time_ago': str(datetime.now() - e.timestamp).split('.')[0]
            }
            for e in list(self.errors)[-10:]
        ]

        # 性能趋势
        perf_recordings = list(self.performance_tracker.recordings)[-20:]
        perf_trend = [r['duration_ms'] for r in perf_recordings] if perf_recordings else []

        # 内存趋势
        memory_trend = [
            {
                'time': s['timestamp'].strftime("%H:%M:%S"),
                'value': s['rss_mb']
            }
            for s in list(self.memory_monitor.samples)[-20:]
        ]

        return {
            'health': {
                'score': health['score'],
                'level': health['level'],
                'issues': health['issues']
            },
            'errors': {
                'total': stats['errors'].get('total_errors', 0),
                'recent': recent_errors,
                'by_type': stats['errors'].get('by_type', {})
            },
            'performance': {
                'total_ops': stats['performance'].get('total_operations', 0),
                'avg_ms': stats['performance'].get('avg_duration_ms', 0),
                'max_ms': stats['performance'].get('max_duration_ms', 0),
                'slow_count': stats['performance'].get('slow_count', 0),
                'trend': perf_trend
            },
            'memory': {
                'current_mb': stats['memory'].get('current_mb', 0),
                'peak_mb': stats['memory'].get('peak_mb', 0),
                'growth': stats['memory'].get('growth_mb_per_min', 0),
                'trend': memory_trend,
                'system_percent': stats['memory'].get('system_percent', 0)
            },
            'threads': {
                'current': stats['threads'].get('current_count', 0),
                'max': stats['threads'].get('max_count', 0),
                'is_leaking': stats['threads'].get('is_leaking', False)
            },
            'network': {
                'sent_mb': stats['network'].get('total_sent_mb', 0),
                'recv_mb': stats['network'].get('total_recv_mb', 0),
                'api_calls': stats['network'].get('total_api_calls', 0)
            },
            'system': {
                'uptime': stats['system'].get('uptime', '0:00:00'),
                'cpu_percent': stats['system'].get('cpu_percent', 0),
                'disk_percent': stats['system'].get('disk_usage_percent', 0)
            },
            'timestamp': datetime.now().isoformat()
        }


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.monitor = get_debug_monitor()

    def log_api_call(self, method: str, url: str, status: int = None,
                     duration_ms: float = None, **kwargs):
        """记录 API 调用"""
        parts = [f"[API:{method}]"]
        if url:
            parts.append(f"{url}")
        if status:
            parts.append(f"status={status}")
        if duration_ms:
            parts.append(f"{duration_ms}ms")

        extra = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        if extra:
            parts.append(extra)

        msg = " ".join(parts)

        if status and status >= 400:
            self.logger.error(msg)
        elif duration_ms and duration_ms > 5000:
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def log_ui_event(self, event_type: str, page: str, element: str = None, **kwargs):
        """记录 UI 事件"""
        parts = [f"[UI:{event_type}]", f"page={page}"]
        if element:
            parts.append(f"element={element}")

        extra = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        if extra:
            parts.append(extra)

        self.logger.debug(" ".join(parts))

    def log_scan_event(self, action: str, target: str, count: int = None, **kwargs):
        """记录扫描事件"""
        parts = [f"[SCAN:{action}]", f"target={target}"]
        if count is not None:
            parts.append(f"count={count}")

        extra = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        if extra:
            parts.append(extra)

        self.logger.info(" ".join(parts))

    def log_ai_event(self, event_type: str, model: str = None,
                    prompt_tokens: int = None, response_tokens: int = None,
                    duration_ms: float = None, error: str = None, **kwargs):
        """记录 AI 事件"""
        parts = [f"[AI:{event_type}]"]
        if model:
            parts.append(f"model={model}")
        if prompt_tokens:
            parts.append(f"prompt={prompt_tokens}")
        if response_tokens:
            parts.append(f"response={response_tokens}")
        if duration_ms:
            parts.append(f"{duration_ms}ms")
        if error:
            parts.append(f"error={error}")

        extra = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        if extra:
            parts.append(extra)

        if error or event_type == 'ERROR':
            self.logger.error(" ".join(parts))
        else:
            self.logger.info(" ".join(parts))

    def log_database_error(self, operation: str, table: str, sql: str = None,
                           error: str = None, **kwargs):
        """记录数据库错误"""
        parts = [f"[DB:ERROR]", f"operation={operation}", f"table={table}"]
        if sql:
            parts.append(f"sql={sql[:100]}...")  # 限制 SQL 长度
        if error:
            parts.append(f"error={error}")

        extra = ", ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        if extra:
            parts.append(extra)

        self.logger.error(" ".join(parts))

    def log_config_change(self, key: str, old_value: Any = None,
                           new_value: Any = None, **kwargs):
        """记录配置变更"""
        parts = [f"[CONFIG:CHANGE]", f"key={key}"]
        if old_value is not None:
            parts.append(f"old={old_value}")
        if new_value is not None:
            parts.append(f"new={new_value}")

        self.logger.info(" ".join(parts))


def get_debug_monitor() -> DebugMonitor:
    """获取调试监控器实例"""
    return DebugMonitor()


def get_structured_logger(logger: logging.Logger) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(logger)


def track_performance(operation_name: str):
    """性能追踪装饰器 - 监控函数执行时间"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_debug_monitor()
            with monitor.track_operation(operation_name):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    monitor.capture_error(e, {
                        'function': func.__name__,
                        'module': func.__module__,
                        'operation': operation_name
                    })
                    raise
        return wrapper
    return decorator


def debug_function(enable: bool = True, **context):
    """调试装饰器 - 是否在调试模式下打印信息"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if enable:
                logger = logging.getLogger(func.__module__)
                caller_frame = inspect.currentframe().f_back
                logger.debug(
                    f"[DEBUG] {func.__module__}.{func.__name__}() | "
                    f"args={args}, kwargs={kwargs} | "
                    f"caller={caller_frame.f_code.co_name}:{caller_frame.f_lineno}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 全局调试日志
debug_logger = logging.getLogger('Debug')
debug_handler = logging.StreamHandler()
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
))
# debug_logger.addHandler(debug_handler)  # 初始化时不添加，由主程序控制
