"""
定时清理调度器模块
使用 QTimer 实现后台调度
支持每日定时清理和磁盘空间阈值触发
"""
from datetime import datetime, time
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

from .disk_monitor import get_disk_monitor
from .models import ScanItem
from .config_manager import get_config_manager


class SchedulerType:
    """调度类型常量"""
    DISABLED = 'disabled'  # 禁用
    DAILY = 'daily'  # 每日定时
    DISK_SPACE = 'disk_space'  # 磁盘空间阈值


class Scheduler(QObject):
    """定时清理调度器

    支持每日定时清理和磁盘空间阈值触发
    使用 QTimer 实现主线程安全的调度
    """
    # Signals
    clean_system = pyqtSignal(list)  # 清理系统，传递扫描项列表
    clean_browser = pyqtSignal(list)  # 清理浏览器，传递扫描项列表
    auto_clean_completed = pyqtSignal(dict)  # 自动清理完成
    scheduler_started = pyqtSignal()  # 调度器启动
    scheduler_stopped = pyqtSignal()  # 调度器停止
    next_run_time = pyqtSignal(str)  # 下次运行时间

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = get_config_manager()
        self.disk_monitor = get_disk_monitor()

        self.enabled = False
        self.scheduler_type = SchedulerType.DISABLED
        self.daily_time = time(2, 0)  # 默认凌晨 2:00
        self.disk_threshold = 10  # 默认 10GB

        # 计时器
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._on_check_timer)

        # 防止重复触发的冷却时间（秒）
        self._cooldown = 30  # 30秒冷却时间
        self._last_trigger_time = None  # 上次触发时间

        # 磁盘检查间隔（分钟）
        self.disk_check_interval = 30

        self._load_settings()

    def _load_settings(self):
        """加载设置"""
        self.enabled = self.config_mgr.get('scheduler/enabled', False)

        scheduler_type = self.config_mgr.get('scheduler/type', SchedulerType.DISABLED)
        self.scheduler_type = scheduler_type if scheduler_type in [
            SchedulerType.DISABLED, SchedulerType.DAILY, SchedulerType.DISK_SPACE
        ] else SchedulerType.DISABLED

        # 加载每日时间
        daily_time_str = self.config_mgr.get('scheduler/daily_time', '02:00')
        try:
            hour, minute = map(int, daily_time_str.split(':'))
            self.daily_time = time(hour, minute)
        except Exception:
            self.daily_time = time(2, 0)

        # 加载磁盘阈值
        self.disk_threshold = self.config_mgr.get('scheduler/disk_threshold', 10)

    def _save_settings(self):
        """保存设置"""
        self.config_mgr.set('scheduler/enabled', self.enabled)
        self.config_mgr.set('scheduler/type', self.scheduler_type)
        self.config_mgr.set('scheduler/daily_time', f"{self.daily_time.hour:02d}:{self.daily_time.minute:02d}")

    def start(self):
        """启动调度器"""
        if not self.enabled or self.scheduler_type == SchedulerType.DISABLED:
            return

        self.check_timer.start(60000)  # 每分钟检查一次
        self.scheduler_started.emit()
        self._emit_next_run_time()

    def stop(self):
        """停止调度器"""
        self.check_timer.stop()
        self._last_trigger_time = None  # 重置触发时间
        self.scheduler_stopped.emit()

    def is_running(self) -> bool:
        """检查调度器是否运行"""
        return self.check_timer.isActive()

    def set_enabled(self, enabled: bool):
        """
        设置是否启用

        Args:
            enabled: 是否启用
        """
        self.enabled = enabled
        self._save_settings()

        if enabled:
            self.start()
        else:
            self.stop()

    def set_scheduler_type(self, scheduler_type: str):
        """
        设置调度类型

        Args:
            scheduler_type: 调度类型
        """
        if scheduler_type in [SchedulerType.DISABLED, SchedulerType.DAILY, SchedulerType.DISK_SPACE]:
            self.scheduler_type = scheduler_type
            self._save_settings()

            # 重启调度器
            if self.is_running():
                self.stop()
                self.start()

    def set_daily_time(self, hour: int, minute: int):
        """
        设置每日清理时间

        Args:
            hour: 小时（0-23）
            minute: 分钟（0-59）
        """
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            self.daily_time = time(hour, minute)
            self._save_settings()

    def set_disk_threshold(self, threshold_gb: int):
        """
        设置磁盘空间阈值

        Args:
            threshold_gb: 阈值（GB）
        """
        self.disk_threshold = threshold_gb
        self.config_mgr.set('scheduler/disk_threshold', threshold_gb)

    def _on_check_timer(self):
        """
        定时检查器回调
        每分钟检查是否需要触发清理
        """
        now = datetime.now()

        if self.scheduler_type == SchedulerType.DAILY:
            # 检查是否到了每日清理时间
            if now.time().hour == self.daily_time.hour and now.time().minute == self.daily_time.minute:
                self._trigger_daily_clean()

        elif self.scheduler_type == SchedulerType.DISK_SPACE:
            # 检查磁盘空间是否低于阈值
            disk_info = self.disk_monitor.check_disk_space(emit_signal=False)
            if disk_info and disk_info['free_gb'] < self.disk_threshold:
                self._trigger_disk_space_clean(disk_info)

    def _trigger_daily_clean(self):
        """触发每日清理"""
        # 检查冷却时间，防止重复触发
        if self._last_trigger_time:
            elapsed = (datetime.now() - self._last_trigger_time).total_seconds()
            if elapsed < self._cooldown:
                return  # 在冷却时间内，跳过触发

        # 更新最后触发时间
        self._last_trigger_time = datetime.now()

        # 发送清理信号，由主窗口处理
        # 这里不直接执行清理，因为需要在主线程中展示 UI
        self.clean_system.emit([])

        # 可以在设置中配置清理类型
        clean_type = self.config_mgr.get('scheduler/daily_clean_type', 'system')
        if clean_type == 'browser':
            self.clean_browser.emit([])

        # 发送完成信号
        self.auto_clean_completed.emit({
            'type': 'daily',
            'triggered_at': datetime.now().isoformat()
        })

    def _trigger_disk_space_clean(self, disk_info: dict):
        """触发磁盘空间清理"""
        # 发送清理信号
        self.clean_system.emit([])

        # 发送完成信号
        self.auto_clean_completed.emit({
            'type': 'disk_space',
            'disk_path': disk_info['device'],
            'free_space_gb': disk_info['free_gb'],
            'threshold_gb': self.disk_threshold,
            'triggered_at': datetime.now().isoformat()
        })

    def _emit_next_run_time(self):
        """发送下次运行时间信号"""
        if self.scheduler_type == SchedulerType.DAILY:
            now = datetime.now()
            next_run = datetime.combine(now.date(), self.daily_time)
            if next_run <= now:
                # 如果今天的时间已过，计算明天的
                from datetime import timedelta
                next_run += timedelta(days=1)
            self.next_run_time.emit(next_run.strftime('%Y-%m-%d %H:%M:%S'))

        elif self.scheduler_type == SchedulerType.DISK_SPACE:
            self.next_run_time.emit('当磁盘空间低于 {}GB 时'.format(self.disk_threshold))
        else:
            self.next_run_time.emit('未启用')

    def get_next_run_time(self) -> str:
        """
        获取下次运行时间

        Returns:
            str: 下次运行时间字符串
        """
        if self.scheduler_type == SchedulerType.DAILY:
            now = datetime.now()
            next_run = datetime.combine(now.date(), self.daily_time)
            if next_run <= now:
                from datetime import timedelta
                next_run += timedelta(days=1)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        elif self.scheduler_type == SchedulerType.DISK_SPACE:
            return f'当磁盘空间低于 {self.disk_threshold}GB 时'
        else:
            return '未启用'

    def get_status(self) -> dict:
        """
        获取调度器状态

        Returns:
            dict: 状态信息
        """
        return {
            'enabled': self.enabled,
            'type': self.scheduler_type,
            'is_running': self.is_running(),
            'daily_time': f"{self.daily_time.hour:02d}:{self.daily_time.minute:02d}",
            'disk_threshold': self.disk_threshold,
            'next_run': self.get_next_run_time()
        }


# 全局调度器实例（单例模式）
_global_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """
    获取全局调度器实例（单例）

    Returns:
        Scheduler: 调度器实例
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = Scheduler()
    return _global_scheduler
