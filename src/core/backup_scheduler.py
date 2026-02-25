"""
备份调度器 (Backup Scheduler)

P0-2 自动备份系统核心组件:
- 定时自动备份（支持多种调度策略）
- 手动触发备份
- 备份配置管理
- 备份任务状态监控
"""
import os
import json
import threading
import time
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

from .backup_manager import (
    BackupManager,
    BackupProfile,
    BackupManifest,
    BackupError
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ScheduleType(Enum):
    """调度类型"""
    ONCE = "once"           # 一次性
    DAILY = "daily"         # 每天
    WEEKLY = "weekly"       # 每周
    MONTHLY = "monthly"     # 每月
    INTERVAL = "interval"   # 间隔（小时/分钟）
    CRON = "cron"           # Cron 表达式


class SchedulerState(Enum):
    """调度器状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class ScheduledTask:
    """调度任务"""
    task_id: str
    profile_id: str
    profile: BackupProfile
    schedule_type: ScheduleType
    schedule_value: str           # 具体值（时间、间隔等）
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    last_result: Optional[str] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'profile_id': self.profile_id,
            'profile': self.profile.to_dict(),
            'schedule_type': self.schedule_type.value,
            'schedule_value': self.schedule_value,
            'next_run_time': self.next_run_time.isoformat() if self.next_run_time else None,
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'last_result': self.last_result,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduledTask':
        """从字典创建"""
        return cls(
            task_id=data['task_id'],
            profile_id=data['profile_id'],
            profile=BackupProfile.from_dict(data['profile']),
            schedule_type=ScheduleType(data['schedule_type']),
            schedule_value=data['schedule_value'],
            next_run_time=datetime.fromisoformat(data['next_run_time']) if data.get('next_run_time') else None,
            last_run_time=datetime.fromisoformat(data['last_run_time']) if data.get('last_run_time') else None,
            last_result=data.get('last_result'),
            enabled=data.get('enabled', True),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class SchedulerStats:
    """调度器统计"""
    total_tasks: int = 0
    active_tasks: int = 0
    completed_backups: int = 0
    failed_backups: int = 0
    last_backup_time: Optional[datetime] = None


class BackupScheduler(QObject):
    """备份调度器

    支持多种备份调度策略：
    - 定时备份（每天/每周/每月）
    - 间隔备份（每隔N小时/分钟）
    - Cron 表达式（高级用户）
    - 手动触发

    Signals:
        scheduler_started: 调度器启动
        scheduler_stopped: 调度器停止
        task_added: ScheduledTask - 任务添加
        task_removed: str - task_id removed
        backup_started: str - task_id
        backup_completed: (str, BackupManifest) - (task_id, manifest)
        backup_failed: (str, str) - (task_id, error_message)
    """

    scheduler_started = pyqtSignal()
    scheduler_stopped = pyqtSignal()
    task_added = pyqtSignal(object)       # ScheduledTask
    task_removed = pyqtSignal(str)        # task_id
    backup_started = pyqtSignal(str)      # task_id
    backup_completed = pyqtSignal(str, object)  # task_id, BackupManifest
    backup_failed = pyqtSignal(str, str)  # task_id, error

    def __init__(self, backup_manager: Optional[BackupManager] = None,
                 config_path: Optional[str] = None):
        """初始化调度器

        Args:
            backup_manager: 备份管理器实例
            config_path: 配置文件路径
        """
        super().__init__()

        self.backup_manager = backup_manager or BackupManager()
        self.config_path = config_path

        if config_path is None:
            # 默认配置路径
            app_path = os.environ.get('LOCALAPPDATA', '')
            if app_path:
                config_path = os.path.join(app_path, 'PurifyAI', 'scheduler_config.json')
            else:
                config_path = os.path.expanduser('~/.purifyai/scheduler_config.json')
            self.config_path = config_path

        self.logger = logger
        self._state = SchedulerState.STOPPED
        self._tasks: Dict[str, ScheduledTask] = {}
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._stats = SchedulerStats()

        # 加载配置
        self._load_config()

        self.logger.info(f"[SCHEDULER] 备份调度器初始化完成")

    @property
    def state(self) -> SchedulerState:
        """获取调度器状态"""
        return self._state

    @property
    def is_running(self) -> bool:
        """调度器是否运行中"""
        return self._state == SchedulerState.RUNNING

    # ========================================================================
    # 任务管理
    # ========================================================================

    def add_profile(self, profile: BackupProfile,
                    schedule_type: ScheduleType = ScheduleType.DAILY,
                    schedule_value: str = "03:00") -> ScheduledTask:
        """添加备份配置

        Args:
            profile: 备份配置
            schedule_type: 调度类型
            schedule_value: 调度值（时间字符串如 "03:00" 或间隔如 "2h"）

        Returns:
            ScheduledTask 创建的任务
        """
        import uuid

        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task = ScheduledTask(
            task_id=task_id,
            profile_id=profile.profile_id,
            profile=profile,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            enabled=profile.enabled
        )

        # 计算下次运行时间
        task.next_run_time = self._calculate_next_run(task)

        self._tasks[task_id] = task
        self._update_stats()
        self._save_config()

        self.logger.info(f"[SCHEDULER] 添加备份任务: {task_id} - {profile.name}")
        self.task_added.emit(task)

        return task

    def remove_profile(self, task_id: str) -> bool:
        """移除备份任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功
        """
        if task_id not in self._tasks:
            return False

        del self._tasks[task_id]
        self._update_stats()
        self._save_config()

        self.logger.info(f"[SCHEDULER] 移除备份任务: {task_id}")
        self.task_removed.emit(task_id)

        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            ScheduledTask
        """
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务

        Returns:
            任务列表
        """
        return list(self._tasks.values())

    def enable_task(self, task_id: str, enabled: bool = True) -> bool:
        """启用/禁用任务

        Args:
            task_id: 任务ID
            enabled: 是否启用

        Returns:
            是否成功
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.enabled = enabled
        self._update_stats()
        self._save_config()

        self.logger.info(f"[SCHEDULER] {'启用' if enabled else '禁用'}任务: {task_id}")
        return True

    def update_task_schedule(self, task_id: str,
                             schedule_type: ScheduleType,
                             schedule_value: str) -> bool:
        """更新任务调度配置

        Args:
            task_id: 任务ID
            schedule_type: 调度类型
            schedule_value: 调度值

        Returns:
            是否成功
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.schedule_type = schedule_type
        task.schedule_value = schedule_value
        task.next_run_time = self._calculate_next_run(task)
        self._save_config()

        self.logger.info(f"[SCHEDULER] 更新任务调度: {task_id} -> {schedule_type.value} {schedule_value}")
        return True

    # ========================================================================
    # 调度控制
    # ========================================================================

    def start(self):
        """启动调度器"""
        if self._state == SchedulerState.RUNNING:
            self.logger.warning("[SCHEDULER] 调度器已在运行中")
            return

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="BackupScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        self._state = SchedulerState.RUNNING

        self.logger.info("[SCHEDULER] 调度器已启动")
        self.scheduler_started.emit()

    def stop(self):
        """停止调度器"""
        if self._state == SchedulerState.STOPPED:
            return

        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None

        self._state = SchedulerState.STOPPED

        self.logger.info("[SCHEDULER] 调度器已停止")
        self.scheduler_stopped.emit()

    def pause(self):
        """暂停调度器"""
        if self._state == SchedulerState.RUNNING:
            self._state = SchedulerState.PAUSED
            self.logger.info("[SCHEDULER] 调度器已暂停")

    def resume(self):
        """恢复调度器"""
        if self._state == SchedulerState.PAUSED:
            self._state = SchedulerState.RUNNING
            self.logger.info("[SCHEDULER] 调度器已恢复")

    # ========================================================================
    # 手动触发
    # ========================================================================

    def trigger_manual_backup(self, task_id: str) -> Optional[BackupManifest]:
        """手动触发备份

        Args:
            task_id: 任务ID

        Returns:
            BackupManifest 备份清单
        """
        task = self._tasks.get(task_id)
        if not task:
            self.logger.error(f"[SCHEDULER] 任务不存在: {task_id}")
            return None

        return self._execute_backup(task)

    def trigger_manual_backup_by_profile(self, profile_id: str) -> Optional[BackupManifest]:
        """通过配置ID手动触发备份

        Args:
            profile_id: 配置ID

        Returns:
            BackupManifest 备份清单
        """
        for task in self._tasks.values():
            if task.profile_id == profile_id:
                return self._execute_backup(task)

        self.logger.error(f"[SCHEDULER] 配置不存在: {profile_id}")
        return None

    def trigger_backup_all(self) -> Dict[str, BackupManifest]:
        """触发所有启用的备份任务

        Returns:
            字典 {task_id: BackupManifest}
        """
        results = {}

        for task_id, task in self._tasks.items():
            if task.enabled:
                manifest = self._execute_backup(task)
                if manifest:
                    results[task_id] = manifest

        return results

    # ========================================================================
    # 调度计算
    # ========================================================================

    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """计算下次运行时间

        Args:
            task: 调度任务

        Returns:
            下次运行时间
        """
        now = datetime.now()

        if task.schedule_type == ScheduleType.ONCE:
            # 一次性：解析时间字符串
            try:
                run_time = datetime.strptime(task.schedule_value, "%Y-%m-%d %H:%M")
                return run_time if run_time > now else now + timedelta(days=1)
            except ValueError:
                return now + timedelta(hours=1)

        elif task.schedule_type == ScheduleType.DAILY:
            # 每天：解析时间如 "03:00"
            try:
                hour, minute = map(int, task.schedule_value.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            except (ValueError, AttributeError):
                return now + timedelta(days=1)

        elif task.schedule_type == ScheduleType.WEEKLY:
            # 每周：格式 "3,03:00" 表示周三 3:00
            try:
                parts = task.schedule_value.split(',')
                weekday = int(parts[0])
                hour, minute = map(int, parts[1].split(':'))

                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # 计算到目标星期几的天数
                days_ahead = weekday - next_run.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0 and next_run <= now:
                    days_ahead = 7

                next_run += timedelta(days=days_ahead)
                return next_run
            except (ValueError, IndexError):
                return now + timedelta(weeks=1)

        elif task.schedule_type == ScheduleType.MONTHLY:
            # 每月：格式 "15,03:00" 表示每月15日 3:00
            try:
                parts = task.schedule_value.split(',')
                day = int(parts[0])
                hour, minute = map(int, parts[1].split(':'))

                next_run = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)

                if next_run <= now:
                    # 移到下个月
                    if now.month == 12:
                        next_run = next_run.replace(year=now.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=now.month + 1)

                return next_run
            except (ValueError, IndexError):
                return now + timedelta(days=30)

        elif task.schedule_type == ScheduleType.INTERVAL:
            # 间隔：格式 "2h" 或 "30m"
            try:
                value = task.schedule_value.lower()
                if value.endswith('h'):
                    hours = int(value[:-1])
                    return now + timedelta(hours=hours)
                elif value.endswith('m'):
                    minutes = int(value[:-1])
                    return now + timedelta(minutes=minutes)
                else:
                    return now + timedelta(hours=1)
            except ValueError:
                return now + timedelta(hours=1)

        elif task.schedule_type == ScheduleType.CRON:
            # Cron 表达式：简单解析（仅支持基本格式）
            return self._parse_cron_next_run(task.schedule_value, now)

        # 默认：1小时后
        return now + timedelta(hours=1)

    def _parse_cron_next_run(self, cron_expr: str, now: datetime) -> datetime:
        """解析 Cron 表达式获取下次运行时间

        支持简单格式：分 时 日 月 周
        例如: "0 3 * * *" 表示每天凌晨3点

        Args:
            cron_expr: Cron 表达式
            now: 当前时间

        Returns:
            下次运行时间
        """
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                return now + timedelta(hours=1)

            minute, hour, day, month, weekday = parts

            # 简化处理：只解析小时和分钟
            target_hour = int(hour) if hour != '*' else now.hour
            target_minute = int(minute) if minute != '*' else 0

            next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

            if next_run <= now:
                next_run += timedelta(days=1)

            return next_run

        except (ValueError, IndexError):
            return now + timedelta(hours=1)

    def get_next_run_time(self, task_id: str) -> Optional[datetime]:
        """获取任务下次运行时间

        Args:
            task_id: 任务ID

        Returns:
            下次运行时间
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        return task.next_run_time

    def get_next_run_times(self) -> Dict[str, datetime]:
        """获取所有任务的下次运行时间

        Returns:
            字典 {task_id: next_run_time}
        """
        return {
            task_id: task.next_run_time
            for task_id, task in self._tasks.items()
            if task.enabled and task.next_run_time
        }

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _scheduler_loop(self):
        """调度器主循环"""
        self.logger.info("[SCHEDULER] 调度循环启动")

        while not self._stop_event.is_set():
            if self._state == SchedulerState.RUNNING:
                self._check_and_execute_tasks()

            # 每60秒检查一次
            self._stop_event.wait(60)

        self.logger.info("[SCHEDULER] 调度循环结束")

    def _check_and_execute_tasks(self):
        """检查并执行到期的任务"""
        now = datetime.now()

        for task_id, task in list(self._tasks.items()):
            if not task.enabled:
                continue

            if task.next_run_time and task.next_run_time <= now:
                self.logger.info(f"[SCHEDULER] 执行定时任务: {task_id}")

                # 执行备份
                self._execute_backup(task)

                # 更新下次运行时间
                task.next_run_time = self._calculate_next_run(task)
                task.last_run_time = now

                self._save_config()

    def _execute_backup(self, task: ScheduledTask) -> Optional[BackupManifest]:
        """执行备份任务

        Args:
            task: 调度任务

        Returns:
            BackupManifest 备份清单
        """
        self.logger.info(f"[SCHEDULER] 开始备份: {task.profile.name}")
        self.backup_started.emit(task.task_id)

        try:
            # 使用 BackupManager 执行备份
            manifest = self.backup_manager.backup_profile(task.profile)

            # 保存清单
            self.backup_manager.save_manifest(manifest)

            # 更新任务状态
            task.last_run_time = datetime.now()
            task.last_result = "success"

            # 更新统计
            self._stats.completed_backups += 1
            self._stats.last_backup_time = datetime.now()

            self.logger.info(
                f"[SCHEDULER] 备份完成: {task.profile.name} - "
                f"{len(manifest.files)} 个文件"
            )
            self.backup_completed.emit(task.task_id, manifest)

            return manifest

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"[SCHEDULER] 备份失败: {task.profile.name} - {error_msg}")

            task.last_result = f"failed: {error_msg}"
            self._stats.failed_backups += 1

            self.backup_failed.emit(task.task_id, error_msg)

            return None

    def _update_stats(self):
        """更新统计信息"""
        self._stats.total_tasks = len(self._tasks)
        self._stats.active_tasks = sum(1 for t in self._tasks.values() if t.enabled)

    def get_stats(self) -> SchedulerStats:
        """获取调度器统计

        Returns:
            SchedulerStats
        """
        return self._stats

    def get_stats_report(self) -> str:
        """获取统计报告

        Returns:
            报告文本
        """
        return (
            f"备份调度器统计:\n"
            f"  状态: {self._state.value}\n"
            f"  总任务数: {self._stats.total_tasks}\n"
            f"  活动任务: {self._stats.active_tasks}\n"
            f"  完成备份: {self._stats.completed_backups}\n"
            f"  失败备份: {self._stats.failed_backups}\n"
            f"  最近备份: {self._stats.last_backup_time or '无'}"
        )

    # ========================================================================
    # 配置持久化
    # ========================================================================

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载任务
            tasks_data = config.get('tasks', [])
            for task_data in tasks_data:
                try:
                    task = ScheduledTask.from_dict(task_data)
                    self._tasks[task.task_id] = task
                except Exception as e:
                    self.logger.warning(f"[SCHEDULER] 加载任务失败: {e}")

            self._update_stats()
            self.logger.info(f"[SCHEDULER] 加载配置: {len(self._tasks)} 个任务")

        except Exception as e:
            self.logger.error(f"[SCHEDULER] 加载配置失败: {e}")

    def _save_config(self):
        """保存配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            config = {
                'version': '1.0',
                'tasks': [task.to_dict() for task in self._tasks.values()],
                'updated_at': datetime.now().isoformat()
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"[SCHEDULER] 配置已保存")

        except Exception as e:
            self.logger.error(f"[SCHEDULER] 保存配置失败: {e}")

    def export_config(self, filepath: str) -> bool:
        """导出配置到文件

        Args:
            filepath: 目标文件路径

        Returns:
            是否成功
        """
        try:
            config = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'tasks': [task.to_dict() for task in self._tasks.values()]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.logger.info(f"[SCHEDULER] 配置已导出: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"[SCHEDULER] 导出配置失败: {e}")
            return False

    def import_config(self, filepath: str, merge: bool = True) -> bool:
        """从文件导入配置

        Args:
            filepath: 源文件路径
            merge: 是否与现有配置合并

        Returns:
            是否成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not merge:
                self._tasks.clear()

            tasks_data = config.get('tasks', [])
            imported_count = 0

            for task_data in tasks_data:
                try:
                    task = ScheduledTask.from_dict(task_data)
                    self._tasks[task.task_id] = task
                    imported_count += 1
                except Exception as e:
                    self.logger.warning(f"[SCHEDULER] 导入任务失败: {e}")

            self._update_stats()
            self._save_config()

            self.logger.info(f"[SCHEDULER] 导入配置: {imported_count} 个任务")
            return True

        except Exception as e:
            self.logger.error(f"[SCHEDULER] 导入配置失败: {e}")
            return False


# ============================================================================
# 便捷函数
# ============================================================================

def create_default_scheduler(backup_dir: Optional[str] = None) -> BackupScheduler:
    """创建默认配置的调度器

    Args:
        backup_dir: 备份目录

    Returns:
        BackupScheduler 实例
    """
    backup_manager = BackupManager(backup_root=backup_dir)
    return BackupScheduler(backup_manager=backup_manager)


def create_simple_daily_backup(name: str, paths: List[str],
                               time_str: str = "03:00",
                               backup_dir: Optional[str] = None) -> BackupScheduler:
    """创建简单的每日备份

    Args:
        name: 备份名称
        paths: 备份路径列表
        time_str: 备份时间（格式：HH:MM）
        backup_dir: 备份目录

    Returns:
        BackupScheduler 实例
    """
    scheduler = create_default_scheduler(backup_dir)

    profile = BackupProfile(
        name=name,
        backup_paths=paths
    )

    scheduler.add_profile(profile, ScheduleType.DAILY, time_str)

    return scheduler
