# -*- coding: utf-8 -*-
"""
清理调度器测试模块 (Cleanup Scheduler Tests)

测试 CleanupScheduler 类的核心功能

作者: 小午 🦁
创建时间: 2026-02-24
"""

import pytest
from datetime import datetime, timedelta
from src.agent.cleanup_scheduler import (
    CleanupScheduler,
    ScheduleConfig,
    ScheduleType,
    ScheduleStatus
)
from src.agent.cleanup_strategy_manager import CleanupStrategy


class TestScheduleConfig:
    """调度配置测试"""

    def test_schedule_creation(self):
        """测试调度配置创建"""
        schedule = ScheduleConfig(
            schedule_id="test_schedule",
            name="Test Schedule",
            schedule_type="daily",
            time_of_day="18:00"
        )

        assert schedule.schedule_id == "test_schedule"
        assert schedule.name == "Test Schedule"
        assert schedule.schedule_type == "daily"


class TestCleanupScheduler:
    """清理调度器测试"""

    @pytest.fixture
    def scheduler(self):
        """创建调度器实例"""
        return CleanupScheduler()

    def test_create_daily_schedule(self, scheduler):
        """测试创建每日调度"""
        schedule = scheduler.create_schedule(
            name="Test Daily",
            schedule_type=ScheduleType.DAILY,
            time_of_day="18:30"
        )

        assert isinstance(schedule, ScheduleConfig)
        assert schedule.schedule_type == "daily"
        assert schedule.time_of_day == "18:30"

    def test_create_weekly_schedule(self, scheduler):
        """测试创建每周调度"""
        schedule = scheduler.create_schedule(
            name="Test Weekly",
            schedule_type=ScheduleType.WEEKLY,
            day_of_week=5,
            time_of_day="20:00"
        )

        assert isinstance(schedule, ScheduleConfig)
        assert schedule.schedule_type == "weekly"
        assert schedule.day_of_week == 5

    def test_create_monthly_schedule(self, scheduler):
        """测试创建每月调度"""
        schedule = scheduler.create_schedule(
            name="Test Monthly",
            schedule_type=ScheduleType.MONTHLY,
            day_of_month=1,
            time_of_day="21:00"
        )

        assert isinstance(schedule, ScheduleConfig)
        assert schedule.schedule_type == "monthly"
        assert schedule.day_of_month == 1

    def test_get_schedules(self, scheduler):
        """测试获取所有调度"""
        schedules = scheduler.get_schedules()

        assert isinstance(schedules, list)

    def test_get_next_run_time_daily(self, scheduler):
        """测试获取下次执行时间 - 每日"""
        schedule = ScheduleConfig(
            schedule_id="test",
            name="Test",
            schedule_type="daily",
            time_of_day="18:30"
        )

        next_run = scheduler.get_next_run_time(schedule)

        assert isinstance(next_run, datetime)
        assert next_run.date() >= datetime.now().date()

    def test_is_schedule_due(self, scheduler):
        """测试检查是否该执行"""
        # 创建一个已经过去的调度
        past_time = datetime.now() - timedelta(minutes=10)
        schedule = ScheduleConfig(
            schedule_id="test",
            name="Test",
            schedule_type="manual",
            last_run_time=past_time
        )

        is_due = scheduler.is_schedule_due(schedule)

        assert is_due

    def test_calculate_optimal_time(self, scheduler):
        """测试最佳时机计算"""
        schedule = ScheduleConfig(
            schedule_id="test",
            name="Test",
            schedule_type="daily",
            time_of_day="18:00"
        )

        optimal_time = scheduler.calculate_optimal_time(schedule)

        assert isinstance(optimal_time, datetime)

    def test_load_presets(self, scheduler):
        """测试加载预置调度"""
        presets = scheduler.load_presets()

        assert isinstance(presets, dict)
        assert "daily_work" in presets
        assert "weekly_home" in presets
        assert "monthly_deep" in presets
        assert "idle_detect" in presets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
