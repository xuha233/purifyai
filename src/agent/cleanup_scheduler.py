# -*- coding: utf-8 -*-
"""
清理调度器模块 (Cleanup Scheduler)

实现定时清理任务调度功能，支持灵活的调度策略、智能时机选择和后台静默执行。

功能：
1. ScheduleConfig - 调度配置数据结构
2. CleanupScheduler - 调度管理核心类
3. 支持每日、每周、每月、手动四种调度类型
4. 支持智能时机计算
5. 支持后台静默执行

作者: 小午 🦁
创建时间: 2026-02-24
"""

import os
import uuid
import json
import math
import platform
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, time
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod

from ..core.models import ScanItem
from .cleanup_strategy_manager import CleanupStrategy
from .cleanup_orchestrator import CleanupOrchestrator, CleanupReport
from .smart_recommender import UserProfile, CleanupPlan, CleanupMode


# ============================================================================
# 枚举定义
# ============================================================================

class ScheduleType(Enum):
    """调度类型"""
    DAILY = "daily"           # 每日
    WEEKLY = "weekly"         # 每周
    MONTHLY = "monthly"       # 每月
    MANUAL = "manual"         # 手动/基于条件

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            ScheduleType.DAILY: "每日",
            ScheduleType.WEEKLY: "每周",
            ScheduleType.MONTHLY: "每月",
            ScheduleType.MANUAL: "手动"
        }
        return names.get(self, self.value)


class ScheduleStatus(Enum):
    """调度状态"""
    ACTIVE = "active"         # 激活
    PAUSED = "paused"         # 暂停
    DISALBED = "disabled"     # 禁用

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            ScheduleStatus.ACTIVE: "激活",
            ScheduleStatus.PAUSED: "暂停",
            ScheduleStatus.DISALBED: "禁用"
        }
        return names.get(self, self.value)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class ScheduleConfig:
    """调度配置

    定义定时清理任务的核心属性和执行配置。
    """

    schedule_id: str  # 调度 ID
    name: str  # 调度名称

    # 调度类型
    schedule_type: str  # "daily"/"weekly"/"monthly"/"manual"
    interval_days: Optional[int] = None  # 间隔天数

    # 时间设置
    time_of_day: Optional[str] = None  # 每天执行时间（HH:MM 格式）
    day_of_week: Optional[int] = None  # 每周执行日期（0-6，0=周一）
    day_of_month: Optional[int] = None  # 每月执行日期（1-31）

    # 执行条件
    min_space_threshold: int = 5  # 最小磁盘空间阈值（GB）
    max_age_days: int = 30  # 最大文件年龄（天）

    # 用户策略
    strategy_id: Optional[str] = None  # 关联的清理策略 ID

    # 执行选项
    skip_on_battery: bool = True  # 电池模式下跳过
    skip_on_fullscreen: bool = False  # 全屏模式下跳过
    allow_background: bool = True  # 允许后台静默执行

    # 状态管理
    status: str = ScheduleStatus.ACTIVE.value
    last_run_time: Optional[datetime] = None  # 最后执行时间
    next_run_time: Optional[datetime] = None  # 下次执行时间
    total_runs: int = 0  # 总执行次数

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_preset: bool = False  # 是否为预置任务

    # 统计
    success_count: int = 0  # 成功次数
    failed_count: int = 0  # 失败次数
    last_result: Optional[Dict[str, Any]] = None  # 最后执行结果

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 转换 datetime 对象
        if self.last_run_time:
            data['last_run_time'] = self.last_run_time.isoformat()
        if self.next_run_time:
            data['next_runs_time'] = self.next_run_time.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleConfig':
        """从字典创建实例"""
        datetime_fields = ['last_run_time', 'next_run_time', 'created_at', 'updated_at']
        for field_name in datetime_fields:
            if field_name in data and isinstance(data[field_name], str):
                try:
                    data[field_name] = datetime.fromisoformat(data[field_name])
                except (ValueError, TypeError):
                    data[field_name] = None

        # 处理可能的字段名差异
        if 'next_runs_time' in data:
            data['next_run_time'] = data.pop('next_runs_time')

        return cls(**data)

    def is_active(self) -> bool:
        """检查调度是否激活"""
        return self.status == ScheduleStatus.ACTIVE.value

    def should_skip_battery(self) -> bool:
        """检查电池模式下是否应该跳过"""
        return self.skip_on_battery and self._is_on_battery()

    def should_skip_fullscreen(self) -> bool:
        """检查全屏模式下是否应该跳过"""
        return self.skip_on_fullscreen and self._is_fullscreen_active()

    def _is_on_battery(self) -> bool:
        """检查是否在电池模式下"""
        try:
            if platform.system() == 'Windows':
                # Windows: 使用 pywin32 或 WMI
                try:
                    import psutil
                    battery = psutil.sensors_battery()
                    return battery is not None and not battery.power_plugged
                except ImportError:
                    # 降级方案
                    return False
            elif platform.system() == 'Darwin':  # macOS
                import subprocess
                result = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True)
                return 'Battery Power' in result.stdout
            elif platform.system() == 'Linux':
                # Linux: 检查 /sys/class/power_supply
                power_supply_path = '/sys/class/power_supply'
                if os.path.exists(power_supply_path):
                    for supply in os.listdir(power_supply_path):
                        status_file = os.path.join(power_supply_path, supply, 'status')
                        if os.path.exists(status_file):
                            with open(status_file, 'r') as f:
                                return 'Discharging' in f.read()
            return False
        except Exception:
            return False

    def _is_fullscreen_active(self) -> bool:
        """检查是否有全屏应用活动"""
        try:
            if platform.system() == 'Windows':
                # Windows: 需要额外的库检测全屏窗口
                # 这里使用简化版本：检查特定进程
                try:
                    import psutil
                    fullscreen_processes = ['vlc.exe', 'mpc-hc64.exe', 'potplayermini64.exe',
                                            'steamwebhelper.exe', 'epicgameslauncher.exe']
                    for p in psutil.process_iter(['name']):
                        if p.info['name'] and any(fp in p.info['name'].lower() for fp in fullscreen_processes):
                            return True
                except ImportError:
                    pass
            return False
        except Exception:
            return False


@dataclass
class ScheduleExecutionLog:
    """调度执行日志"""
    log_id: str
    schedule_id: str
    schedule_name: str
    executed_at: datetime
    success: bool
    duration_seconds: float
    freed_size: int
    items_cleaned: int
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'log_id': self.log_id,
            'schedule_id': self.schedule_id,
            'schedule_name': self.schedule_name,
            'executed_at': self.executed_at.isoformat(),
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'freed_size': self.freed_size,
            'items_cleaned': self.items_cleaned,
            'error_message': self.error_message
        }


# ============================================================================
# 清理调度器
# ============================================================================

class CleanupScheduler:
    """清理调度器

    核心功能：
    1. 创建、更新、删除定时清理任务
    2. 计算下次执行时间
    3. 检查是否该执行清理
    4. 执行后台静默清理

    数据存储位置：
    - ~/.purifyai/schedules.json - 调度配置
    - ~/.purifyai/scheduler_log.json - 执行日志
    """

    def __init__(self, data_dir: Optional[str] = None):
        """初始化清理调度器

        Args:
            data_dir: 数据目录路径（可选）
        """
        self.data_dir = Path(data_dir) if data_dir else Path.home() / '.purifyai'
        self.data_dir.mkdir(exist_ok=True)

        # 配置文件路径
        self.schedules_file = self.data_dir / 'schedules.json'
        self.log_file = self.data_dir / 'scheduler_log.json'

        # 内存缓存
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._loaded = False

    # ========================================================================
    # 调度管理 (CRUD)
    # ========================================================================

    def create_schedule(self, config: ScheduleConfig) -> ScheduleConfig:
        """创建定时清理任务

        Args:
            config: 调度配置

        Returns:
            创建的调度配置（包含生成的 ID）

        Raises:
            ValueError: 当配置无效时
        """
        # 验证配置
        self._validate_schedule_config(config)

        # 生成 ID（如果未提供）
        if not config.schedule_id:
            config.schedule_id = f"schedule_{uuid.uuid4().hex[:8]}"

        # 计算下次执行时间
        config.next_run_time = self._calculate_next_run_time(config)

        # 设置创建和更新时间
        now = datetime.now()
        config.created_at = now
        config.updated_at = now

        # 保存到缓存和文件
        self._schedules[config.schedule_id] = config
        self._save_schedules()

        print(f"[CleanupScheduler] 创建调度任务: {config.name} ({config.schedule_id})")
        return config

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> Optional[ScheduleConfig]:
        """更新定时清理配置

        Args:
            schedule_id: 调度 ID
            updates: 更新的字段

        Returns:
            更新后的调度配置，不存在时返回 None
        """
        if not self._loaded:
            self._load_schedules()

        if schedule_id not in self._schedules:
            print(f"[CleanupScheduler] 调度任务不存在: {schedule_id}")
            return None

        config = self._schedules[schedule_id]

        # 更新字段
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # 重新计算下次执行时间
        config.next_run_time = self._calculate_next_run_time(config)
        config.updated_at = datetime.now()

        # 保存
        self._save_schedules()

        print(f"[CleanupScheduler] 更新调度任务: {config.name} ({schedule_id})")
        return config

    def delete_schedule(self, schedule_id: str) -> bool:
        """删除定时清理任务

        Args:
            schedule_id: 调度 ID

        Returns:
            是否删除成功
        """
        if not self._loaded:
            self._load_schedules()

        if schedule_id not in self._schedules:
            return False

        config = self._schedules.pop(schedule_id)
        self._save_schedules()

        print(f"[CleanupScheduler] 删除调度任务: {config.name} ({schedule_id})")
        return True

    def get_schedules(self, status: Optional[str] = None) -> List[ScheduleConfig]:
        """获取所有定时清理任务

        Args:
            status: 按状态过滤（可选）

        Returns:
            调度配置列表
        """
        if not self._loaded:
            self._load_schedules()

        schedules = list(self._schedules.values())

        if status:
            schedules = [s for s in schedules if s.status == status]

        # 按 created_at 排序
        schedules.sort(key=lambda s: s.created_at, reverse=True)

        return schedules

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """获取指定的定时清理任务

        Args:
            schedule_id: 调度 ID

        Returns:
            调度配置，不存在时返回 None
        """
        if not self._loaded:
            self._load_schedules()

        return self._schedules.get(schedule_id)

    # ========================================================================
    # 时间计算
    # ========================================================================

    def get_next_run_time(self, schedule_id: str) -> Optional[datetime]:
        """获取下次执行时间

        Args:
            schedule_id: 调度 ID

        Returns:
            下次执行时间，任务不存在或停用时返回 None
        """
        config = self.get_schedule(schedule_id)
        if not config or not config.is_active():
            return None

        return config.next_run_time

    def is_schedule_due(self, schedule_id: str, now: Optional[datetime] = None) -> bool:
        """检查是否该执行清理

        Args:
            schedule_id: 调度 ID
            now: 当前时间（可选，默认使用当前系统时间）

        Returns:
            是否该执行
        """
        config = self.get_schedule(schedule_id)
        if not config or not config.is_active():
            return False

        if not config.next_run_time:
            return False

        now = now or datetime.now()

        # 检查跳过条件
        if config.skip_on_battery and config._is_on_battery():
            print(f"[CleanupScheduler] 跳过执行（电池模式）: {config.name}")
            return False

        if config.skip_on_fullscreen and config._is_fullscreen_active():
            print(f"[CleanupScheduler] 跳过执行（全屏模式）: {config.name}")
            return False

        return now >= config.next_run_time

    def get_due_schedules(self, now: Optional[datetime] = None) -> List[ScheduleConfig]:
        """获取所有到期的调度任务

        Args:
            now: 当前时间（可选）

        Returns:
            到期的调度配置列表
        """
        now = now or datetime.now()
        return [
            config for config in self.get_schedules()
            if config.is_active() and config.next_run_time and now >= config.next_run_time
        ]

    # ========================================================================
    # 验证与辅助方法
    # ========================================================================

    def _validate_schedule_config(self, config: ScheduleConfig) -> None:
        """验证调度配置

        Args:
            config: 调度配置

        Raises:
            ValueError: 当配置无效时
        """
        # 验证调度类型
        valid_types = [st.value for st in ScheduleType]
        if config.schedule_type not in valid_types:
            raise ValueError(f"Invalid schedule_type: {config.schedule_type}. Must be one of {valid_types}")

        # 根据调度类型验证必需字段
        if config.schedule_type == ScheduleType.DAILY.value:
            if config.interval_days is not None and config.interval_days < 1:
                raise ValueError("interval_days must be at least 1 for daily schedule")

        elif config.schedule_type == ScheduleType.WEEKLY.value:
            if config.day_of_week is not None and (config.day_of_week < 0 or config.day_of_week > 6):
                raise ValueError("day_of_week must be between 0 and 6")

        elif config.schedule_type == ScheduleType.MONTHLY.value:
            if config.day_of_month is not None and (config.day_of_month < 1 or config.day_of_month > 31):
                raise ValueError("day_of_month must be between 1 and 31")

        # 验证时间格式
        if config.time_of_day:
            try:
                datetime.strptime(config.time_of_day, "%H:%M")
            except ValueError:
                raise ValueError("time_of_day must be in HH:MM format")

        # 验证阈值
        if config.min_space_threshold < 0:
            raise ValueError("min_space_threshold must be >= 0")

        if config.max_age_days < 0:
            raise ValueError("max_age_days must be >= 0")

    def _calculate_next_run_time(self, config: ScheduleConfig) -> Optional[datetime]:
        """计算下次执行时间

        Args:
            config: 调度配置

        Returns:
            下次执行时间
        """
        now = datetime.now()
        schedule_type = ScheduleType(config.schedule_type)

        if schedule_type == ScheduleType.MANUAL:
            # 手动模式：由条件触发，不需要下次执行时间
            return None

        # 解析时间
        target_time = self._parse_time(config.time_of_day, default_hour=18, default_minute=0)

        if schedule_type == ScheduleType.DAILY:
            # 每日调度
            interval = config.interval_days or 1
            if config.last_run_time:
                next_run = config.last_run_time + timedelta(days=interval)
                # 设置为执行时间
                next_run = next_run.replace(
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0
                )
                if next_run <= now:
                    next_run += timedelta(days=interval)
            else:
                # 首次执行，今天或明天
                next_run = now.replace(
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0
                )
                if next_run <= now:
                    next_run = next_run + timedelta(days=1)

            return next_run

        elif schedule_type == ScheduleType.WEEKLY:
            # 每周调度
            target_day = config.day_of_week if config.day_of_week is not None else 5  # 默认周五
            current_day = now.weekday()

            if config.last_run_time:
                # 基于上次执行时间计算
                next_run = config.last_run_time + timedelta(weeks=1)
            else:
                # 首次执行，找到下一个目标日期
                days_until = (target_day - current_day) % 7
                if days_until == 0:
                    # 今天的这个时刻已过，推到下周
                    next_run_date = (now + timedelta(days=7)).date()
                else:
                    next_run_date = (now + timedelta(days=days_until)).date()

                next_run = datetime.combine(
                    next_run_date,
                    time(hour=target_time.hour, minute=target_time.minute)
                )

            return next_run

        elif schedule_type == ScheduleType.MONTHLY:
            # 每月调度
            target_day = config.day_of_month if config.day_of_month is not None else 1

            if config.last_run_time:
                # 基于上次执行时间计算
                next_run_month = config.last_run_time.month + 1
                next_run_year = config.last_run_time.year
                if next_run_month > 12:
                    next_run_month = 1
                    next_run_year += 1

                # 处理月份日数不足
                max_day = self._days_in_month(next_run_year, next_run_month)
                actual_day = min(target_day, max_day)

                next_run = datetime(next_run_year, next_run_month, actual_day,
                                  hour=target_time.hour, minute=target_time.minute)
            else:
                # 首次执行，找到下个月或本月
                current_day = now.day
                if target_day < current_day or (target_day == current_day and now.time() >= time(target_time.hour, target_time.minute)):
                    # 本月的日子已过，下个月
                    next_month = now.month + 1
                    next_year = now.year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1

                    max_day = self._days_in_month(next_year, next_month)
                    actual_day = min(target_day, max_day)

                    next_run = datetime(next_year, next_month, actual_day,
                                       hour=target_time.hour, minute=target_time.minute)
                else:
                    # 本月
                    max_day = self._days_in_month(now.year, now.month)
                    actual_day = min(target_day, max_day)

                    next_run = datetime(now.year, now.month, actual_day,
                                       hour=target_time.hour, minute=target_time.minute)

            return next_run

        return None

    def _parse_time(self, time_str: Optional[str], default_hour: int = 18, default_minute: int = 0) -> time:
        """解析时间字符串

        Args:
            time_str: 时间字符串（HH:MM 格式）
            default_hour: 默认小时
            default_minute: 默认分钟

        Returns:
            time 对象
        """
        if not time_str:
            return time(default_hour, default_minute)

        try:
            hour, minute = map(int, time_str.split(':'))
            hour = max(0, min(23, hour))
            minute = max(0, min(59, minute))
            return time(hour, minute)
        except (ValueError, AttributeError):
            return time(default_hour, default_minute)

    def _days_in_month(self, year: int, month: int) -> int:
        """获取某个月的天数

        Args:
            year: 年份
            month: 月份（1-12）

        Returns:
            当月天数
        """
        if month == 2:
            # 闰年二月有 29 天
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                return 29
            return 28
        elif month in [4, 6, 9, 11]:
            return 30
        else:
            return 31

    # ========================================================================
    # 数据持久化
    # ========================================================================

    def _load_schedules(self) -> None:
        """从文件加载调度配置"""
        if not self.schedules_file.exists():
            self._schedules = {}
            self._loaded = True
            return

        try:
            with open(self.schedules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            schedules_data = data.get('schedules', [])
            self._schedules = {
                s['schedule_id']: ScheduleConfig.from_dict(s)
                for s in schedules_data
            }

            print(f"[CleanupScheduler] 加载了 {len(self._schedules)} 个调度任务")
        except Exception as e:
            print(f"[CleanupScheduler] 加载调度配置失败: {e}")
            self._schedules = {}

        self._loaded = True

    def _save_schedules(self) -> None:
        """保存调度配置到文件"""
        try:
            data = {
                'schedules': [config.to_dict() for config in self._schedules.values()],
                'last_updated': datetime.now().isoformat()
            }

            with open(self.schedules_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[CleanupScheduler] 保存调度配置失败: {e}")

    # ========================================================================
    # 执行日志
    # ========================================================================

    def log_execution(self, log: ScheduleExecutionLog) -> None:
        """记录执行日志

        Args:
            log: 执行日志
        """
        if not self.log_file.exists():
            data = {'logs': []}
        else:
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[CleanupScheduler] 加载日志失败: {e}")
                data = {'logs': []}

        # 添加新日志
        data['logs'].append(log.to_dict())

        # 只保留最近 500 条记录
        if len(data['logs']) > 500:
            data['logs'] = data['logs'][-500:]

        # 保存
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[CleanupScheduler] 保存日志失败: {e}")

        # 更新调度任务的统计
        self._update_schedule_stats(log.schedule_id, log.success)

    def get_execution_logs(self, schedule_id: Optional[str] = None, limit: int = 50) -> List[ScheduleExecutionLog]:
        """获取执行日志

        Args:
            schedule_id: 调度 ID（可选，为 None 时返回所有日志）
            limit: 最大返回数量

        Returns:
            执行日志列表
        """
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[CleanupScheduler] 加载日志失败: {e}")
            return []

        logs_data = data.get('logs', [])

        # 过滤
        if schedule_id:
            logs_data = [l for l in logs_data if l.get('schedule_id') == schedule_id]

        # 限制数量并按时间倒序
        logs_data = logs_data[-limit:]
        logs_data.reverse()

        # 转换为对象
        logs = []
        for log_data in logs_data:
            if 'executed_at' in log_data and isinstance(log_data['executed_at'], str):
                log_data['executed_at'] = datetime.fromisoformat(log_data['executed_at'])
            logs.append(ScheduleExecutionLog(**log_data))

        return logs

    def _update_schedule_stats(self, schedule_id: str, success: bool) -> None:
        """更新调度任务统计

        Args:
            schedule_id: 调度 ID
            success: 是否成功
        """
        config = self.get_schedule(schedule_id)
        if not config:
            return

        config.total_runs += 1
        if success:
            config.success_count += 1
        else:
            config.failed_count += 1

        self._save_schedules()


# ============================================================================
# 便利函数
# ============================================================================

def get_cleanup_scheduler(data_dir: Optional[str] = None) -> CleanupScheduler:
    """获取清理调度器实例

    Args:
        data_dir: 数据目录路径（可选）

    Returns:
        CleanupScheduler 实例
    """
    return CleanupScheduler(data_dir)
