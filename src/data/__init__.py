# -*- coding: utf-8 -*-
"""
数据层模块 (Data Layer)

提供数据持久化和历史数据管理功能。
"""

from .health_history import (
    HealthHistoryManager,
    HealthHistoryEntry
)

__all__ = [
    'HealthHistoryManager',
    'HealthHistoryEntry',
]
