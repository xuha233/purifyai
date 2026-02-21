"""实时日志记录器 - 立即写入磁盘，避免崩溃丢失日志"""

import os
import sys
import threading
import time
import traceback
from datetime import datetime
from typing import Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker


class RealTimeLogger(QObject):
    """实时日志记录器 - 立即写入磁盘文件"""

    log_written = pyqtSignal(str)  # 日志写入成功信号
    log_error = pyqtSignal(str)   # 日志写入错误信号

    _instance: Optional['RealTimeLogger'] = None
    _lock = QMutex()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with QMutexLocker(cls._lock):
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = None):
        """初始化实时日志记录器

        Args:
            log_dir: 日志目录，默认为当前工作目录的 logs 子目录
        """
        # 先调用父类初始化，避免在 hasattr 时出现 RuntimeError
        super().__init__()

        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 日志目录和文件
        self.log_dir = log_dir or os.path.join(os.getcwd(), 'logs')
        self.log_file: Optional[str] = None
        self._file_mutex = QMutex()
        self._enabled = False
        self._write_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 统计信息
        self._log_count = 0
        self._last_error_count = 0

        # 性能数据
        self._perf_data = []

    def enable(self) -> bool:
        """启用实时日志"""
        if self._enabled:
            return True

        try:
            os.makedirs(self.log_dir, exist_ok=True)

            # 创建日志文件（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(self.log_dir, f'realtime_{timestamp}.log')

            # 写入文件头
            header = f"""{"="*80}
PurifyAI 实时日志
启动时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
Python 版本: {sys.version}
工作目录: {os.getcwd()}
{"="*80}

"""
            self._write_raw(header)

            self._enabled = True

            # 启动监控线程
            self._start_monitor_thread()

            return True

        except Exception as e:
            self.log_error.emit(f"启用实时日志失败: {e}")
            return False

    def disable(self):
        """禁用实时日志"""
        if not self._enabled:
            return

        self._stop_event.set()
        self._enabled = False

        # 等待线程结束
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=1.0)

    def clear(self) -> bool:
        """清理实时日志文件"""
        try:
            # 停止当前日志
            self.disable()

            # 删除日志文件
            if self.log_file and os.path.exists(self.log_file):
                os.remove(self.log_file)

            # 删除旧日志文件（保留最近10个）
            self._cleanup_old_logs(keep_count=10)

            return True

        except Exception as e:
            self.log_error.emit(f"清理日志失败: {e}")
            return False

    def write(self, level: str, source: str, message: str, log_time: str = None):
        """写入日志（立即写入磁盘）

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL, STDOUT, STDERR)
            source: 日志来源
            message: 日志消息
            log_time: 日志时间（格式化为 HH:MM:SS.mmm）
        """
        if not self._enabled or not self.log_file:
            return

        if log_time is None:
            log_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # 格式化日志
        log_line = f"[{log_time}] [{level:<8}] [{source}] {message}\n"

        # 立即写入文件
        self._write_raw(log_line)
        self._log_count += 1

    def write_exception(self, exc_type, exc_value, exc_traceback):
        """写入异常堆栈"""
        if not self._enabled or not self.log_file:
            return

        tb_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_list)

        header = f"\n{'='*80}\n"
        header += f"未捕获异常 [{datetime.now().strftime("%H:%M:%S.%f")[:-3]}]\n"
        header += f"类型: {exc_type.__name__}\n"
        header += f"消息: {exc_value}\n"
        header += f"{'='*80}\n"

        self._write_raw(header)
        self._write_raw(tb_text)
        self._write_raw(f"{'='*80}\n\n")

        self._last_error_count += 1

    def write_performance(self, metric_name: str, value: float, unit: str = ""):
        """写入性能指标"""
        if not self._enabled or not self.log_file:
            return

        log_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        perf_line = f"[PERF] {log_time} | {metric_name} = {value} {unit}\n"
        self._write_raw(perf_line)

    def write_system_state(self, cpu_percent: float, memory_mb: float,
                          thread_count: int, queue_size: int = 0):
        """写入系统状态"""
        if not self._enabled or not self.log_file:
            return

        log_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        state_line = (f"[STATE] {log_time} | CPU: {cpu_percent:.1f}% | "
                    f"Memory: {memory_mb:.1f}MB | Threads: {thread_count} | "
                    f"Queue: {queue_size}\n")
        self._write_raw(state_line)

    def _write_raw(self, text: str):
        """立即写入原始文本到文件（线程安全）"""
        try:
            with QMutexLocker(self._file_mutex):
                with open(self.log_file, 'a', encoding='utf-8', buffering=1) as f:
                    f.write(text)
        except Exception as e:
            # 避免死循环，不在这里调用 log_error
            pass

    def _start_monitor_thread(self):
        """启动监控线程"""
        self._stop_event.clear()
        self._write_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._write_thread.start()

    def _monitor_loop(self):
        """监控循环 - 定期检查系统状态（使用异步方式避免阻塞）"""
        import threading

        while not self._stop_event.wait(5.0):  # 每5秒检查一次
            try:
                # 使用单独线程运行 psutil 调用，避免阻塞 UI
                def monitor():
                    try:
                        import psutil
                        process = psutil.Process()

                        cpu = process.cpu_percent(interval=0.1)
                        memory = process.memory_info().rss / (1024 * 1024)
                        threads = process.num_threads()

                        # 异步写入性能数据（避免在监控线程中阻塞）
                        self.write_performance('cpu_percent', cpu, '%')
                        self.write_performance('memory_mb', memory, 'MB')
                        self.write_performance('thread_count', threads, '')

                        # 如果CPU或内存异常，写入警告
                        if cpu > 80:
                            self.write('WARNING', 'SystemMonitor',
                                      f'高CPU使用率警告: {cpu:.1f}%')
                        if memory > 1000:
                            self.write('WARNING', 'SystemMonitor',
                                      f'高内存使用警告: {memory:.1f}MB')
                    except:
                        pass

                # 在独立线程中运行监控
                monitor_thread = threading.Thread(target=monitor, daemon=True)
                monitor_thread.start()

            except:
                pass  # 避免监控线程崩溃

    def _cleanup_old_logs(self, keep_count: int = 10):
        """清理旧的日志文件"""
        try:
            if not os.path.exists(self.log_dir):
                return

            # 获取所有实时日志文件
            log_files = []
            for f in os.listdir(self.log_dir):
                if f.startswith('realtime_') and f.endswith('.log'):
                    filepath = os.path.join(self.log_dir, f)
                    log_files.append((filepath, os.path.getmtime(filepath)))

            # 按修改时间排序，删除超出的旧文件
            log_files.sort(key=lambda x: x[1], reverse=True)
            for filepath, _ in log_files[keep_count:]:
                try:
                    os.remove(filepath)
                except:
                    pass

        except Exception as e:
            pass

    def get_stats(self) -> dict:
        """获取统计信息"""
        file_size = 0
        if self.log_file and os.path.exists(self.log_file):
            file_size = os.path.getsize(self.log_file)

        return {
            'enabled': self._enabled,
            'log_file': self.log_file,
            'log_count': self._log_count,
            'error_count': self._last_error_count,
            'file_size_mb': file_size / (1024 * 1024) if file_size > 0 else 0
        }

    def get_log_content(self, max_lines: int = 1000) -> str:
        """获取日志内容"""
        if not self.log_file or not os.path.exists(self.log_file):
            return ""

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 返回最后N行
                if len(lines) > max_lines:
                    lines = lines[-max_lines:]
                return ''.join(lines)
        except Exception as e:
            return f"读取日志失败: {e}"


class RealTimeRedirector(QObject):
    """实时输出重定向器 - 捕获所有输出并写入实时日志"""

    output_received = pyqtSignal(str)  # 输出信号（用于UI显示）

    def __init__(self, original_stream, stream_name: str, rt_logger: RealTimeLogger):
        """初始化重定向器

        Args:
            original_stream: 原始流对象
            stream_name: 流名称 (stdout/stderr)
            rt_logger: 实时日志记录器
        """
        super().__init__()
        self.original_stream = original_stream
        self.stream_name = stream_name
        self.rt_logger = rt_logger
        self._buffer = ""
        self._mutex = QMutex()

    def write(self, text: str):
        """写入文本"""
        try:
            # 写入实时日志文件
            if self.rt_logger._enabled:
                self.rt_logger.write(
                    'STDERR' if 'stderr' in self.stream_name else 'STDOUT',
                    self.stream_name,
                    text.rstrip()
                )

            # 缓冲并逐行处理
            with QMutexLocker(self._mutex):
                self._buffer += text
                while '\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\n', 1)
                    if line:
                        # 发射信号到UI
                        self.output_received.emit(line)

            # 也写入原始流
            if self.original_stream and hasattr(self.original_stream, 'write'):
                self.original_stream.write(text)

        except Exception as e:
            # 避免中断程序
            pass

    def flush(self):
        """刷新"""
        # 刷新缓冲区
        if self._buffer:
            self.output_received.emit(self._buffer)
            self._buffer = ""

        if self.original_stream and hasattr(self.original_stream, 'flush'):
            self.original_stream.flush()


# 全局异常钩子
_original_excepthook = None
_rt_logger_instance = None


def install_realtime_excepthook():
    """安装实时异常钩子"""
    global _original_excepthook, _rt_logger_instance

    _rt_logger_instance = RealTimeLogger()
    _original_excepthook = sys.excepthook

    def realtime_excepthook(exc_type, exc_value, exc_traceback):
        """实时异常处理钩子"""
        # 写入实时日志
        if isinstance(_rt_logger_instance, RealTimeLogger) and _rt_logger_instance._enabled:
            _rt_logger_instance.write_exception(exc_type, exc_value, exc_traceback)

        # 调用原始钩子
        if _original_excepthook:
            _original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = realtime_excepthook


def uninstall_realtime_excepthook():
    """卸载实时异常钩子"""
    global _original_excepthook

    if _original_excepthook:
        sys.excepthook = _original_excepthook
        _original_excepthook = None
