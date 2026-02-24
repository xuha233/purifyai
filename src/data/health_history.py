# -*- coding: utf-8 -*-
"""
健康历史管理模块 (Health History Manager)

管理健康报告的历史记录，支持健康趋势计算。

作者: Claude Code (dev 团队)
创建时间: 2026-02-24
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

from ..agent.ai_health_scorer import HealthReport


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class HealthHistoryEntry:
    """健康历史记录"""
    timestamp: int  # Unix 时间戳（毫秒）
    score: int
    disk_usage_score: int
    cleanable_space_score: int
    fragmentation_score: int
    performance_score: int

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'score': self.score,
            'disk_usage_score': self.disk_usage_score,
            'cleanable_space_score': self.cleanable_space_score,
            'fragmentation_score': self.fragmentation_score,
            'performance_score': self.performance_score
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'HealthHistoryEntry':
        """从字典创建记录"""
        return cls(
            timestamp=data['timestamp'],
            score=data['score'],
            disk_usage_score=data['disk_usage_score'],
            cleanable_space_score=data['cleanable_space_score'],
            fragmentation_score=data['fragmentation_score'],
            performance_score=data['performance_score']
        )


# ============================================================================
# 健康历史管理器
# ============================================================================

class HealthHistoryManager:
    """健康历史管理器

    功能：
    1. 保存健康报告
    2. 获取健康历史
    3. 计算健康趋势
    4. 获取对比数据
    """

    # 默认配置
    DEFAULT_DATA_DIR = 'data'
    DEFAULT_FILE_NAME = 'health_history.json'
    MAX_HISTORY_ENTRIES = 100  # 最大历史记录条数

    def __init__(self, data_dir: Optional[str] = None, file_name: Optional[str] = None):
        """初始化健康历史管理器

        Args:
            data_dir: 数据目录路径
            file_name: 文件名
        """
        self.data_dir = data_dir or self.DEFAULT_DATA_DIR
        self.file_name = file_name or self.DEFAULT_FILE_NAME
        self.file_path = os.path.join(self.data_dir, self.file_name)
        self._cache: Optional[List[HealthHistoryEntry]] = None

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

    def save_health_report(self, report: HealthReport) -> bool:
        """保存健康报告

        Args:
            report: 健康报告

        Returns:
            是否保存成功
        """
        try:
            # 加载现有历史
            history = self._load_history_from_file()

            # 创建新的历史记录
            entry = HealthHistoryEntry(
                timestamp=int(report.timestamp.timestamp() * 1000),  # 毫秒时间戳
                score=report.score,
                disk_usage_score=report.disk_usage_score,
                cleanable_space_score=report.cleanable_space_score,
                fragmentation_score=report.fragmentation_score,
                performance_score=report.performance_score
            )

            # 添加到历史记录
            history.append(entry)

            # 按时间戳排序
            history.sort(key=lambda x: x.timestamp)

            # 限制历史记录数量
            if len(history) > self.MAX_HISTORY_ENTRIES:
                history = history[-self.MAX_HISTORY_ENTRIES:]

            # 保存到文件
            self._save_history_to_file(history)

            # 清除缓存
            self._cache = None

            return True
        except Exception as e:
            print(f"[HealthHistoryManager] 保存健康报告失败: {e}")
            return False

    def get_health_history(self, limit: int = 30) -> List[HealthHistoryEntry]:
        """获取健康历史

        Args:
            limit: 最大返回条数

        Returns:
            健康历史记录列表
        """
        history = self._load_history_from_file()

        # 返回最近的记录
        return history[-limit:] if history else []

    def calculate_health_trend(self, days: int = 7) -> float:
        """计算健康趋势

        Args:
            days: 计算趋势的天数

        Returns:
            健康趋势变化（正值表示改善，负值表示恶化）
        """
        history = self.get_health_history(days * 2)  # 获取更多记录以确保有足够数据

        if len(history) < 2:
            return 0.0

        # 获取当前和之前的数据
        current = history[-1]
        # 查找最早符合条件的记录
        target_timestamp = current.timestamp - (days * 24 * 60 * 60 * 1000)
        previous = None
        for entry in reversed(history[:-1]):
            if entry.timestamp <= target_timestamp:
                previous = entry
                break

        if previous is None and len(history) > 1:
            previous = history[0]

        if previous is None:
            return 0.0

        # 计算评分变化
        score_change = current.score - previous.score

        # 归一化为每天的变化
        time_diff_days = (current.timestamp - previous.timestamp) / (24 * 60 * 60 * 1000)
        if time_diff_days > 0:
            return score_change / time_diff_days

        return float(score_change)

    def get_health_comparison(self) -> Dict[str, any]:
        """获取健康对比数据

        Returns:
            对比数据字典，包含：
            - current: 当前评分
            - previous: 上次评分
            - best: 最佳评分
            - worst: 最差评分
            - average: 平均评分
            - trend: 趋势（上升/稳定/下降）
            - trend_value: 趋势值
            - comparison_vs_previous: 与上次对比
        """
        history = self.get_health_history()

        if not history:
            return {
                'current': 0,
                'previous': 0,
                'best': 0,
                'worst': 0,
                'average': 0,
                'trend': 'stable',
                'trend_value': 0.0,
                'comparison_vs_previous': 0
            }

        scores = [entry.score for entry in history]
        current = history[-1]
        previous = history[-2] if len(history) > 1 else current

        # 计算趋势
        trend_value = self.calculate_health_trend()
        if trend_value > 1:
            trend = 'improving'  # 改善
        elif trend_value < -1:
            trend = 'declining'  # 恶化
        else:
            trend = 'stable'  # 稳定

        return {
            'current': current.score,
            'previous': previous.score,
            'best': max(scores),
            'worst': min(scores),
            'average': round(sum(scores) / len(scores)),
            'trend': trend,
            'trend_value': round(trend_value, 2),
            'comparison_vs_previous': current.score - previous.score
        }

    # ------------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------------

    def _load_history_from_file(self) -> List[HealthHistoryEntry]:
        """从文件加载历史记录

        Returns:
            历史记录列表
        """
        # 使用缓存
        if self._cache is not None:
            return self._cache.copy()

        entries = []

        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    reports = data.get('reports', [])
                    for report_data in reports:
                        entry = HealthHistoryEntry.from_dict(report_data)
                        entries.append(entry)
            except Exception as e:
                print(f"[HealthHistoryManager] 加载历史记录失败: {e}")

        # 缓存结果
        self._cache = entries

        return entries.copy()

    def _save_history_to_file(self, history: List[HealthHistoryEntry]) -> bool:
        """保存历史记录到文件

        Args:
            history: 历史记录列表

        Returns:
            是否保存成功
        """
        try:
            data = {
                'reports': [entry.to_dict() for entry in history],
                'updated_at': int(datetime.now().timestamp() * 1000)
            }

            # 原子写入：先写临时文件，再重命名
            temp_path = self.file_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 原子操作
            if os.path.exists(self.file_path):
                os.replace(temp_path, self.file_path)
            else:
                os.rename(temp_path, self.file_path)

            return True
        except Exception as e:
            print(f"[HealthHistoryManager] 保存历史记录失败: {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            return False

    def clear_history(self) -> bool:
        """清除健康历史记录

        Returns:
            是否清除成功
        """
        try:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            self._cache = None
            return True
        except Exception as e:
            print(f"[HealthHistoryManager] 清除历史记录失败: {e}")
            return False

    def health_trend_to_display(self, trend_value: float) -> Tuple[str, str]:
        """将趋势值转换为显示文本

        Args:
            trend_value: 趋势值

        Returns:
            (显示文本, 状态) - 状态为 'good'/'neutral'/'bad'
        """
        if trend_value > 2:
            return f"改善 (+{trend_value:.1f}/天)", 'good'
        elif trend_value > 0:
            return f"轻微改善 (+{trend_value:.1f}/天)", 'good'
        elif trend_value < -2:
            return f"恶化 ({trend_value:.1f}/天)", 'bad'
        elif trend_value < 0:
            return f"轻微恶化 ({trend_value:.1f}/天)", 'bad'
        else:
            return "保持稳定", 'neutral'
