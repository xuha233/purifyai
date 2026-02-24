# -*- coding: utf-8 -*-
"""
AI 健康评分模块 (AI Health Scorer)

实现磁盘健康评分系统，让用户能够直观地了解磁盘健康状况和清理价值。

作者: Claude Code (dev 团队)
创建时间: 2026-02-24
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..core.models import ScanItem
from ..core.scanner import Scanner
from ..data.health_history import HealthHistoryManager


# ============================================================================
# 枚举定义
# ============================================================================

class HealthPriority(Enum):
    """清理优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            HealthPriority.HIGH: "高",
            HealthPriority.MEDIUM: "中",
            HealthPriority.LOW: "低"
        }
        return names.get(self, self.value)


class HealthCategory(Enum):
    """健康类别"""
    DISK_SPACE = "disk_space"
    CLEANABLE_SPACE = "cleanable_space"
    FRAGMENTATION = "fragmentation"
    PERFORMANCE = "performance"

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            HealthCategory.DISK_SPACE: "磁盘空间",
            HealthCategory.CLEANABLE_SPACE: "可清理空间",
            HealthCategory.FRAGMENTATION: "文件碎片",
            HealthCategory.PERFORMANCE: "系统性能"
        }
        return names.get(self, self.value)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class HealthRecommendation:
    """健康建议"""
    category: str  # 类别（disk_space/cleanable_space/fragmentation/performance）
    issue: str     # 问题描述
    solution: str  # 解决方案
    potential_save: float = 0.0  # 预计节省空间（MB）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'category': self.category,
            'category_display': HealthCategory(self.category).get_display_name() if self.category in [e.value for e in HealthCategory] else self.category,
            'issue': self.issue,
            'solution': self.solution,
            'potential_save': self.potential_save
        }


@dataclass
class HealthReport:
    """健康报告"""
    score: int  # 总分（0-100）
    disk_usage_score: int  # 磁盘空间评分
    cleanable_space_score: int  # 可清理空间评分
    fragmentation_score: int  # 文件碎片度评分
    performance_score: int  # 系统性能评分
    recommendations: List[HealthRecommendation] = field(default_factory=list)
    priority: str = HealthPriority.MEDIUM.value  # 清理优先级（high/medium/low）
    timestamp: datetime = field(default_factory=datetime.now)
    disk_usage_percent: float = 0.0  # 磁盘使用率
    cleanable_space_mb: float = 0.0  # 可清理空间（MB）
    fragmentation_percent: float = 0.0  # 碎片率
    growth_speed_mb_per_day: float = 0.0  # 增长速度（MB/天）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'score': self.score,
            'disk_usage_score': self.disk_usage_score,
            'cleanable_space_score': self.cleanable_space_score,
            'fragmentation_score': self.fragmentation_score,
            'performance_score': self.performance_score,
            'recommendations': [rec.to_dict() for rec in self.recommendations],
            'priority': self.priority,
            'timestamp': self.timestamp.isoformat(),
            'disk_usage_percent': self.disk_usage_percent,
            'cleanable_space_mb': self.cleanable_space_mb,
            'fragmentation_percent': self.fragmentation_percent,
            'growth_speed_mb_per_day': self.growth_speed_mb_per_day
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'HealthReport':
        """从字典创建健康报告"""
        recommendations = [
            HealthRecommendation(
                category=rec['category'],
                issue=rec['issue'],
                solution=rec['solution'],
                potential_save=rec.get('potential_save', 0.0)
            )
            for rec in data.get('recommendations', [])
        ]

        return cls(
            score=data['score'],
            disk_usage_score=data['disk_usage_score'],
            cleanable_space_score=data['cleanable_space_score'],
            fragmentation_score=data['fragmentation_score'],
            performance_score=data['performance_score'],
            recommendations=recommendations,
            priority=data.get('priority', HealthPriority.MEDIUM.value),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            disk_usage_percent=data.get('disk_usage_percent', 0.0),
            cleanable_space_mb=data.get('cleanable_space_mb', 0.0),
            fragmentation_percent=data.get('fragmentation_percent', 0.0),
            growth_speed_mb_per_day=data.get('growth_speed_mb_per_day', 0.0)
        )


# ============================================================================
# AI 健康评分器
# ============================================================================

class AIHealthScorer:
    """AI 健康评分器

    功能：
    1. 分析磁盘健康状况
    2. 计算健康评分（0-100）
    3. 生成健康报告
    4. 推荐清理优先级

    评分维度：
    1. 磁盘空间占用（40%）
    2. 可清理空间（30%）
    3. 文件碎片度（15%）
    4. 系统性能影响（15%）
    """

    # 评分维度权重
    WEIGHTS = {
        'disk_usage': 0.40,
        'cleanable_space': 0.30,
        'fragmentation': 0.15,
        'performance': 0.15
    }

    def __init__(self, health_history_manager: Optional[HealthHistoryManager] = None):
        """初始化健康评分器

        Args:
            health_history_manager: 健康历史管理器（可选）
        """
        self.scanner = Scanner()
        self.health_history_manager = health_history_manager
        self._health_history: Optional[List[HealthReport]] = None

    # ------------------------------------------------------------------------
    # 核心分析方法
    # ------------------------------------------------------------------------

    def analyze_disk_health(self,
                          disk_path: str = None,
                          cleanable_files: List[ScanItem] = None,
                          last_scan_time: Optional[datetime] = None) -> HealthReport:
        """分析磁盘健康状况

        Args:
            disk_path: 要分析的磁盘路径（默认为主磁盘）
            cleanable_files: 可清理文件列表
            last_scan_time: 上次扫描时间（用于计算增长速度）

        Returns:
            HealthReport: 健康报告
        """
        # 获取磁盘路径
        if disk_path is None:
            disk_path = self._get_primary_disk()

        # 计算各项指标
        disk_usage_percent = self._get_disk_usage(disk_path)
        cleanable_space_mb = self._get_cleanable_space(cleanable_files)
        fragmentation_percent = self._calculate_fragmentation(cleanable_files)
        growth_speed_mb_per_day = self._calculate_growth_speed(
            cleanable_space_mb, last_scan_time
        )

        # 计算各项评分
        disk_usage_score = self._calculate_disk_usage_score(disk_usage_percent)
        cleanable_space_score = self._calculate_cleanable_space_score(cleanable_space_mb)
        fragmentation_score = self._calculate_fragmentation_score(fragmentation_percent)
        performance_score = self._calculate_performance_score(growth_speed_mb_per_day)

        # 计算总分
        total_score = self.calculate_health_score(
            disk_usage_percent,
            cleanable_space_mb,
            fragmentation_percent,
            growth_speed_mb_per_day
        )

        # 生成健康报告
        report = HealthReport(
            score=total_score,
            disk_usage_score=disk_usage_score,
            cleanable_space_score=cleanable_space_score,
            fragmentation_score=fragmentation_score,
            performance_score=performance_score,
            disk_usage_percent=disk_usage_percent,
            cleanable_space_mb=cleanable_space_mb,
            fragmentation_percent=fragmentation_percent,
            growth_speed_mb_per_day=growth_speed_mb_per_day
        )

        # 生成改进建议
        report.recommendations = self.generate_recommendations(report)

        # 推荐清理优先级
        report.priority = self.recommend_cleanup_priority(report).value

        return report

    def calculate_health_score(self,
                             disk_usage_percent: float,
                             cleanable_space_mb: float,
                             fragmentation_percent: float,
                             growth_speed_mb_per_day: float) -> int:
        """计算健康评分

        Args:
            disk_usage_percent: 磁盘使用率（0-100）
            cleanable_space_mb: 可清理空间（MB）
            fragmentation_percent: 碎片文件百分比（0-100）
            growth_speed_mb_per_day: 垃圾文件增长速度（MB/天）

        Returns:
            健康评分（0-100）
        """
        # 磁盘空间评分（40%）
        disk_score = self._calculate_disk_usage_score(disk_usage_percent)

        # 可清理空间评分（30%）
        cleanable_score = self._calculate_cleanable_space_score(cleanable_space_mb)

        # 文件碎片评分（15%）
        frag_score = self._calculate_fragmentation_score(fragmentation_percent)

        # 系统性能评分（15%）
        perf_score = self._calculate_performance_score(growth_speed_mb_per_day)

        # 加权总分
        total_score = (
            disk_score * self.WEIGHTS['disk_usage'] +
            cleanable_score * self.WEIGHTS['cleanable_space'] +
            frag_score * self.WEIGHTS['fragmentation'] +
            perf_score * self.WEIGHTS['performance']
        )

        return max(0, min(100, round(total_score)))

    def generate_recommendations(self, report: HealthReport) -> List[HealthRecommendation]:
        """生成改进建议

        Args:
            report: 健康报告

        Returns:
            改进建议列表
        """
        recommendations = []

        # 磁盘空间建议
        if report.disk_usage_score < 70:
            recommendations.append(HealthRecommendation(
                category=HealthCategory.DISK_SPACE.value,
                issue=f"磁盘使用率 {report.disk_usage_percent:.1f}%，建议清理",
                solution="执行一键清理，释放磁盘空间",
                potential_save=report.cleanable_space_mb
            ))

        # 可清理空间建议
        if report.cleanable_space_score < 60:
            recommendations.append(HealthRecommendation(
                category=HealthCategory.CLEANABLE_SPACE.value,
                issue=f"可清理空间 {self._format_size(report.cleanable_space_mb * 1024 * 1024)}",
                solution="增量清理模式可以快速释放空间",
                potential_save=report.cleanable_space_mb * 0.8
            ))

        # 文件碎片建议
        if report.fragmentation_score < 70:
            recommendations.append(HealthRecommendation(
                category=HealthCategory.FRAGMENTATION.value,
                issue=f"文件碎片率 {report.fragmentation_percent:.1f}%，影响系统性能",
                solution="建议运行磁盘碎片整理工具优化性能",
                potential_save=report.cleanable_space_mb * 0.1
            ))

        # 系统性能建议
        if report.performance_score < 60:
            recommendations.append(HealthRecommendation(
                category=HealthCategory.PERFORMANCE.value,
                issue=f"垃圾文件增长速度 {report.growth_speed_mb_per_day:.1f} MB/天",
                solution="建议设置定期自动清理任务，减少垃圾文件积累",
                potential_save=report.growth_speed_mb_per_day * 7  # 预计一周节省
            ))

        # 如果各项都良好,给出鼓励性建议
        if report.score >= 85:
            recommendations.append(HealthRecommendation(
                category=HealthCategory.PERFORMANCE.value,
                issue="系统健康状况良好",
                solution="建议保持每周一次的定期清理习惯",
                potential_save=0.0
            ))

        return recommendations

    def recommend_cleanup_priority(self, report: HealthReport) -> HealthPriority:
        """推荐清理优先级

        Args:
            report: 健康报告

        Returns:
            清理优先级
        """
        # 高优先级：总分 < 60 或任意维度评分 < 50
        if (report.score < 60 or
            report.disk_usage_score < 50 or
            report.cleanable_space_score < 50):
            return HealthPriority.HIGH

        # 中优先级：总分 60-79 或任意维度评分 < 70
        if (report.score < 80 or
            report.disk_usage_score < 70 or
            report.cleanable_space_score < 70 or
            report.fragmentation_score < 60):
            return HealthPriority.MEDIUM

        # 低优先级：总分 >= 80
        return HealthPriority.LOW

    # ------------------------------------------------------------------------
    # 分项评分计算方法（私有）
    # ------------------------------------------------------------------------

    def _calculate_disk_usage_score(self, usage_percent: float) -> int:
        """计算磁盘空间评分

        阈值：<30% (优秀), 30-60% (良好), 60-80% (一般), >80% (差)

        Args:
            usage_percent: 磁盘使用率（0-100）

        Returns:
            磁盘空间评分（0-100）
        """
        # 确保在合理范围内
        usage_percent = max(0, min(100, usage_percent))

        if usage_percent < 30:
            return 100
        elif usage_percent < 60:
            # 100 - (使用率 - 30) × 1.5
            return round(100 - (usage_percent - 30) * 1.5)
        elif usage_percent < 80:
            # 70 - (使用率 - 60) × 2.5
            return round(70 - (usage_percent - 60) * 2.5)
        else:
            # 20 - (使用率 - 80) × 1
            return max(0, round(20 - (usage_percent - 80) * 1))

    def _calculate_cleanable_space_score(self, cleanable_space_mb: float) -> int:
        """计算可清理空间评分

        阈值：<1GB (优秀), 1-3GB (良好), 3-5GB (一般), >5GB (差)

        Args:
            cleanable_space_mb: 可清理空间（MB）

        Returns:
            可清理空间评分（0-100）
        """
        # min(100, 可清理MB / 5000 × 100)
        # 越少越好，所以我们需要反向评分
        cleanable_gb = cleanable_space_mb / 1024

        if cleanable_gb < 1:
            return 100
        elif cleanable_gb < 3:
            # 100 - (GB - 1) × 15
            return round(100 - (cleanable_gb - 1) * 15)
        elif cleanable_gb < 5:
            # 70 - (GB - 3) × 20
            return round(70 - (cleanable_gb - 3) * 20)
        else:
            return max(0, round(30 - (cleanable_gb - 5) * 5))

    def _calculate_fragmentation_score(self, fragmentation_percent: float) -> int:
        """计算文件碎片度评分

        阈值：<5% (优秀), 5-15% (良好), 15-30% (一般), >30% (差)

        Args:
            fragmentation_percent: 碎片文件百分比（0-100）

        Returns:
            文件碎片度评分（0-100）
        """
        # 确保在合理范围内
        fragmentation_percent = max(0, min(100, fragmentation_percent))

        if fragmentation_percent < 5:
            return 100
        elif fragmentation_percent < 15:
            # 100 - (碎片率 - 5) × 7.5
            return round(100 - (fragmentation_percent - 5) * 7.5)
        elif fragmentation_percent < 30:
            # 25 - (碎片率 - 15) × 1.5
            return round(25 - (fragmentation_percent - 15) * 1.5)
        else:
            return max(0, round(5 - (fragmentation_percent - 30) * 0.2))

    def _calculate_performance_score(self, growth_speed_mb_per_day: float) -> int:
        """计算系统性能评分

        阈值：<5MB/天 (优秀), 5-20MB/天 (良好), 20-50MB/天 (一般), >50MB/天 (差)

        Args:
            growth_speed_mb_per_day: 垃圾文件增长速度（MB/天）

        Returns:
            系统性能评分（0-100）
        """
        # 确保在合理范围内
        growth_speed_mb_per_day = max(0, min(200, growth_speed_mb_per_day))

        if growth_speed_mb_per_day < 5:
            return 100
        elif growth_speed_mb_per_day < 20:
            # 100 - (增长速度 - 5) × 2.67
            return round(100 - (growth_speed_mb_per_day - 5) * 2.67)
        elif growth_speed_mb_per_day < 50:
            # 60 - (增长速度 - 20) × 1.33
            return round(60 - (growth_speed_mb_per_day - 20) * 1.33)
        else:
            return max(0, round(20 - (growth_speed_mb_per_day - 50) * 0.3))

    # ------------------------------------------------------------------------
    # 辅助方法（私有）
    # ------------------------------------------------------------------------

    def _get_primary_disk(self) -> str:
        """获取主磁盘路径

        Returns:
            主磁盘路径
        """
        if os.name == 'nt':  # Windows
            return os.path.splitdrive(os.path.expanduser('~'))[0] + '\\'
        else:  # Linux/Mac
            return '/'

    def _get_disk_usage(self, disk_path: str) -> float:
        """获取磁盘使用率

        Args:
            disk_path: 磁盘路径

        Returns:
            磁盘使用率（0-100）
        """
        try:
            if os.name == 'nt':  # Windows
                # Windows 特殊处理
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(disk_path),
                    None,
                    ctypes.byref(total_bytes),
                    ctypes.byref(free_bytes)
                )
                if total_bytes.value > 0:
                    used_bytes = total_bytes.value - free_bytes.value
                    return (used_bytes / total_bytes.value) * 100
            else:  # Linux/Mac
                stat = os.statvfs(disk_path)
                if stat.f_blocks > 0:
                    total = stat.f_blocks * stat.f_frsize
                    free = stat.f_bavail * stat.f_frsize
                    return ((total - free) / total) * 100
        except Exception as e:
            print(f"[AIHealthScorer] 获取磁盘使用率失败: {e}")

        return 0.0

    def _get_cleanable_space(self, cleanable_files: List[ScanItem] = None) -> float:
        """获取可清理空间

        Args:
            cleanable_files: 可清理文件列表

        Returns:
            可清理空间（MB）
        """
        if cleanable_files is None:
            return 0.0

        # 计算总大小（MB）
        total_bytes = sum(item.size for item in cleanable_files)
        return total_bytes / (1024 * 1024)

    def _calculate_fragmentation(self, cleanable_files: List[ScanItem] = None) -> float:
        """计算文件碎片度

        这里使用简化的碎片度计算：小型文件占总文件数量的比例

        Args:
            cleanable_files: 可清理文件列表

        Returns:
            碎片文件百分比（0-100）
        """
        if not cleanable_files:
            return 0.0

        # 统计小型文件（<100KB）的数量
        small_files = sum(1 for item in cleanable_files if item.size < 100 * 1024)
        total_files = len(cleanable_files)

        if total_files == 0:
            return 0.0

        return (small_files / total_files) * 100

    def _calculate_growth_speed(self,
                               cleanable_space_mb: float,
                               last_scan_time: Optional[datetime] = None) -> float:
        """计算垃圾文件增长速度

        如果有历史数据，使用历史数据计算；否则使用估算值

        Args:
            cleanable_space_mb: 当前可清理空间（MB）
            last_scan_time: 上次扫描时间

        Returns:
            增长速度（MB/天）
        """
        if self.health_history_manager:
            # 尝试从历史数据计算
            return self.health_history_manager.calculate_health_trend()

        # 如果没有历史数据，使用估算值
        # 假设每天增长可清理空间的 5%
        return cleanable_space_mb * 0.05

    def _format_size(self, size_bytes: float) -> str:
        """格式化文件大小

        Args:
            size_bytes: 字节数

        Returns:
            格式化后的字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
