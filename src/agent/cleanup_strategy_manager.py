# -*- coding: utf-8 -*-
"""
清理策略管理器模块 (Cleanup Strategy Manager)

实现智能策略推荐系统，根据用户场景和使用习惯推荐最优的清理策略。

功能：
1. 用户行为分析 - 分析用户的清理频率、时机、内容和系统使用模式
2. 策略画像生成 - 基于用户行为生成策略画像
3. 智能策略推荐 - 根据场景或行为历史推荐最优策略
4. 策略历史管理 - 保存和管理用户的策略历史

作者: 小午 🦁
创建时间: 2026-02-24
"""

import os
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod


# ============================================================================
# 枚举定义
# ============================================================================

class UserScenario(Enum):
    """用户场景枚举"""
    GAMER = "gamer"           # 游戏玩家
    OFFICE = "office"         # 办公电脑
    DEVELOPER = "developer"   # 开发环境
    NORMAL = "normal"         # 普通用户

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            UserScenario.GAMER: "游戏玩家",
            UserScenario.OFFICE: "办公电脑",
            UserScenario.DEVELOPER: "开发环境",
            UserScenario.NORMAL: "普通用户"
        }
        return names.get(self, self.value)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class CleanupStrategy:
    """清理策略数据类

    定义清理策略的核心属性，包括清理规则、时间策略和性能偏好。
    """

    strategy_id: str  # 策略唯一标识
    name: str  # 策略名称
    description: str  # 策略描述

    # 清理规则
    mode: str  # 清理模式（conservative/balanced/aggressive）
    risk_threshold: int  # 风险阈值（0-100）
    priority_categories: List[str] = field(default_factory=list)  # 优先清理的类别

    # 时间策略
    schedule: Optional[str] = None  # 调度计划（daily/weekly/manual）
    preferred_time: Optional[str] = None  # 偏好时间

    # 性能偏好
    prioritize_size: bool = False  # 优先处理大文件
    prioritize_recency: bool = False  # 优先处理最近文件

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    is_preset: bool = False  # 是否为预置策略

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'strategy_id': self.strategy_id,
            'name': self.name,
            'description': self.description,
            'mode': self.mode,
            'risk_threshold': self.risk_threshold,
            'priority_categories': self.priority_categories,
            'schedule': self.schedule,
            'preferred_time': self.preferred_time,
            'prioritize_size': self.prioritize_size,
            'prioritize_recency': self.prioritize_recency,
            'created_at': self.created_at.isoformat(),
            'is_preset': self.is_preset
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CleanupStrategy':
        """从字典创建实例"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class UserBehaviorProfile:
    """用户行为画像

    存储用户的行为模式分析结果。
    """

    profiling_timestamp: datetime  # 分析时间戳

    # 清理频率分析
    cleanup_frequency: str = "unknown"  # daily/weekly/monthly/unknown
    avg_interval_days: float = 0.0  # 平均清理间隔（天）

    # 清理时机偏好
    timing_preference: str = "unknown"  # weekday/weekend/unknown
    time_of_day_preference: str = "unknown"  # morning/afternoon/evening/unknown

    # 清理内容分析
    content_preference: str = "unknown"  # 最常清理的类别
    category_frequency: Dict[str, int] = field(default_factory=dict)

    # 风险容忍度
    risk_tolerance: str = "medium"  # low/medium/high

    # 系统使用模式
    disk_growth_rate: float = 0.0  # 磁盘增长率（MB/天）
    avg_cleanup_size: float = 0.0  # 平均清理大小（MB）

    # 清理历史统计
    total_cleanups: int = 0  # 总清理次数
    last_cleanup_time: Optional[datetime] = None  # 最后一次清理时间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'profiling_timestamp': self.profiling_timestamp.isoformat(),
            'cleanup_frequency': self.cleanup_frequency,
            'avg_interval_days': self.avg_interval_days,
            'timing_preference': self.timing_preference,
            'time_of_day_preference': self.time_of_day_preference,
            'content_preference': self.content_preference,
            'category_frequency': self.category_frequency,
            'risk_tolerance': self.risk_tolerance,
            'disk_growth_rate': self.disk_growth_rate,
            'avg_cleanup_size': self.avg_cleanup_size,
            'total_cleanups': self.total_cleanups,
            'last_cleanup_time': self.last_cleanup_time.isoformat() if self.last_cleanup_time else None
        }


@dataclass
class StrategyHistory:
    """策略历史记录

    记录用户采用策略的历史。
    """

    history_id: str  # 历史记录ID
    strategy_id: str  # 策略ID
    strategy_name: str  # 策略名称
    applied_at: datetime  # 应用时间
    success_rate: float = 0.0  # 成功率
    acceptedrecommendations: bool = False  # 是否接受了推荐
    feedback_score: Optional[int] = None  # 用户反馈评分（1-5）
    notes: str = ""  # 备注

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'history_id': self.history_id,
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'applied_at': self.applied_at.isoformat(),
            'success_rate': self.success_rate,
            'accepted_recommendations': self.acceptedrecommendations,
            'feedback_score': self.feedback_score,
            'notes': self.notes
        }


# ============================================================================
# 策略推荐器接口
# ============================================================================

class StrategyRecommender(ABC):
    """策略推荐器抽象基类"""

    @abstractmethod
    def recommend(self, context: Dict[str, Any]) -> CleanupStrategy:
        """推荐策略

        Args:
            context: 推荐上下文

        Returns:
            推荐的清理策略
        """
        pass


# ============================================================================
# 清理策略管理器
# ============================================================================

class CleanupStrategyManager:
    """清理策略管理器

    负责智能策略推荐的核心功能：
    1. 分析用户行为模式
    2. 生成策略画像
    3. 推荐最优策略
    4. 管理策略历史

    数据存储位置：
    - ~/.purifyai/strategy_history.json - 策略历史
    - ~/.purifyai/user_behavior.json - 用户行为画像
    """

    # 默认策略配置（当配置文件不存在时的后备方案）
    DEFAULT_PRESETS = {
        "gamer": {
            "strategy_id": "gamer_preferred",
            "name": "游戏玩家优化",
            "description": "为游戏玩家优化的清理策略",
            "mode": "aggressive",
            "risk_threshold": 50,
            "priority_categories": ["game_cache", "temp_files", "downloads"],
            "schedule": "weekly",
            "prioritize_size": True,
            "prioritize_recency": False,
            "is_preset": True
        },
        "office": {
            "strategy_id": "office_standard",
            "name": "办公电脑标准",
            "description": "适合办公环境的标准清理策略",
            "mode": "balanced",
            "risk_threshold": 30,
            "priority_categories": ["browser_cache", "temp_files", "logs"],
            "schedule": "daily",
            "prioritize_size": False,
            "prioritize_recency": False,
            "is_preset": True
        },
        "developer": {
            "strategy_id": "dev_conservative",
            "name": "开发者保守",
            "description": "保护开发文件的保守清理策略",
            "mode": "conservative",
            "risk_threshold": 20,
            "priority_categories": ["build_cache", "temp_files", "logs"],
            "schedule": "manual",
            "prioritize_size": False,
            "prioritize_recency": False,
            "is_preset": True
        },
        "normal": {
            "strategy_id": "normal_balanced",
            "name": "普通用户平衡",
            "description": "适合普通用户的平衡清理策略",
            "mode": "balanced",
            "risk_threshold": 30,
            "priority_categories": ["browser_cache", "temp_files"],
            "schedule": "weekly",
            "prioritize_size": False,
            "prioritize_recency": False,
            "is_preset": True
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """初始化清理策略管理器

        Args:
            config_path: 策略配置文件路径（可选）
        """
        # 设置数据目录
        self.data_dir = Path.home() / '.purifyai'
        self.data_dir.mkdir(exist_ok=True)

        # 配置文件路径
        self.config_path = config_path or str(
            Path(__file__).parent.parent / 'config' / 'strategy_presets.json'
        )

        # 历史文件路径
        self.history_file = self.data_dir / 'strategy_history.json'
        self.behavior_file = self.data_dir / 'user_behavior.json'

        # 缓存
        self._presets: Optional[Dict[str, Dict[str, Any]]] = None
        self._behaviors: Optional[Dict[str, Any]] = None

    # ========================================================================
    # 策略管理
    # ========================================================================

    def load_presets(self) -> Dict[str, Dict[str, Any]]:
        """加载预置策略配置

        Returns:
            预置策略字典
        """
        if self._presets is not None:
            return self._presets

        # 尝试从配置文件加载
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._presets = data.get('presets', {})
                    print(f"[CleanupStrategyManager] 加载策略配置: {self.config_path}")
                    return self._presets
            except Exception as e:
                print(f"[CleanupStrategyManager] 加载配置失败，使用默认配置: {e}")

        # 使用默认配置
        self._presets = self.DEFAULT_PRESETS
        print("[CleanupStrategyManager] 使用默认策略配置")
        return self._presets

    def get_preset_strategy(self, scenario: UserScenario) -> Optional[CleanupStrategy]:
        """获取场景对应的预置策略

        Args:
            scenario: 用户场景

        Returns:
            对应的清理策略，不存在时返回 None
        """
        presets = self.load_presets()
        preset_key = scenario.value

        if preset_key not in presets:
            return None

        return CleanupStrategy.from_dict(presets[preset_key])

    def list_preset_strategies(self) -> List[CleanupStrategy]:
        """列出所有预置策略

        Returns:
            预置策略列表
        """
        presets = self.load_presets()
        return [CleanupStrategy.from_dict(p) for p in presets.values()]

    # ========================================================================
    # 用户行为分析
    # ========================================================================

    def analyze_user_behavior(self, cleanup_reports: List[Any]) -> UserBehaviorProfile:
        """分析用户行为模式

        分析维度：
        1. 清理频率 - 用户多久清理一次
        2. 清理时好 - 工作日/周末，上午/下午/晚上
        3. 清理内容 - 最常清理的类别
        4. 系统使用模式 - 磁盘增长速度、清理大小等

        Args:
            cleanup_reports: 清理历史记录列表

        Returns:
            用户行为画像
        """
        profile = UserBehaviorProfile(
            profiling_timestamp=datetime.now()
        )

        if not cleanup_reports:
            return profile

        # 统计总清理次数
        profile.total_cleanups = len(cleanup_reports)

        # 提取清理时间（兼容 CleanupReport 的 created_at 和 started_at）
        times = []
        for report in cleanup_reports:
            cleanup_time = getattr(report, 'created_at', None)
            if cleanup_time is None:
                cleanup_time = getattr(report, 'started_at', None)
            if cleanup_time is not None:
                times.append(cleanup_time)

        if not times:
            return profile

        # 更新最后清理时间
        profile.last_cleanup_time = max(times)

        # 分析清理频率
        profile.cleanup_frequency, profile.avg_interval_days = self._analyze_frequency(times)

        # 分析清理时机偏好
        profile.timing_preference = self._analyze_timing_weekday(times)
        profile.time_of_day_preference = self._analyze_timing_hour(times)

        # 分析清理内容偏好
        profile.content_preference, profile.category_frequency = self._analyze_content(cleanup_reports)

        # 分析风险容忍度
        profile.risk_tolerance = self._analyze_risk_tolerance(profile.avg_interval_days)

        # 分析系统使用模式
        profile.disk_growth_rate, profile.avg_cleanup_size = self._analyze_system_usage(cleanup_reports, profile.total_cleanups)

        return profile

    def _analyze_frequency(self, times: List[datetime]) -> tuple:
        """分析清理频率

        Args:
            times: 清理时间列表

        Returns:
            (频率类别, 平均间隔天数)
        """
        if len(times) < 2:
            return "unknown", 7.0

        times_sorted = sorted(times)
        intervals = []
        for i in range(1, len(times_sorted)):
            interval_days = (times_sorted[i] - times_sorted[i-1]).total_seconds() / 86400
            intervals.append(interval_days)

        if not intervals:
            return "unknown", 7.0

        avg_interval = sum(intervals) / len(intervals)

        # 分类
        if avg_interval < 2:
            frequency = "daily"
        elif avg_interval < 7:
            frequency = "weekly"
        elif avg_interval < 30:
            frequency = "monthly"
        else:
            frequency = "infrequent"

        return frequency, avg_interval

    def _analyze_timing_weekday(self, times: List[datetime]) -> str:
        """分析工作日/周末偏好

        Args:
            times: 清理时间列表

        Returns:
            "weekday" 或 "weekend" 或 "unknown"
        """
        if not times:
            return "unknown"

        weekday_count = sum(1 for t in times if t.weekday() < 5)
        weekend_count = len(times) - weekday_count

        if weekday_count > weekend_count:
            return "weekday"
        elif weekend_count > weekday_count:
            return "weekend"
        else:
            return "unknown"

    def _analyze_timing_hour(self, times: List[datetime]) -> str:
        """分析时段偏好

        Args:
            times: 清理时间列表

        Returns:
            "morning" / "afternoon" / "evening" / "unknown"
        """
        if not times:
            return "unknown"

        morning = sum(1 for t in times if 5 <= t.hour < 12)  # 5-11点
        afternoon = sum(1 for t in times if 12 <= t.hour < 18)  # 12-17点
        evening = sum(1 for t in times if 18 <= t.hour or t.hour < 5)  # 18-5点

        if morning >= afternoon and morning >= evening:
            return "morning"
        elif afternoon >= morning and afternoon >= evening:
            return "afternoon"
        elif evening >= morning and evening >= afternoon:
            return "evening"
        else:
            return "unknown"

    def _analyze_content(self, reports: List[Any]) -> tuple:
        """分析清理内容偏好

        Args:
            reports: 清理报告列表

        Returns:
            (最常清理的类别, 类别频率统计)
        """
        category_counts = {}

        for report in reports:
            # 从 details 中提取类别信息
            details = getattr(report, 'details', [])
            if not details:
                details = report.get('details', [])

            for detail in details:
                if isinstance(detail, dict):
                    category = detail.get('category', 'unknown')
                    category_counts[category] = category_counts.get(category, 0) + 1

        if not category_counts:
            return "unknown", {}

        top_category = max(category_counts.items(), key=lambda x: x[1])[0]
        return top_category, category_counts

    def _analyze_risk_tolerance(self, avg_interval_days: float) -> str:
        """分析风险容忍度

        Args:
            avg_interval_days: 平均清理间隔天数

        Returns:
            "low" / "medium" / "high"
        """
        # 清理频率越高，风险容忍度越高（经常清理意味着更谨慎地选择要删除的文件）
        if avg_interval_days < 2:
            return "high"
        elif avg_interval_days < 7:
            return "medium"
        else:
            return "low"

    def _analyze_system_usage(self, reports: List[Any], total_count: int) -> tuple:
        """分析系统使用模式

        Args:
            reports: 清理报告列表
            total_count: 清理总次数

        Returns:
            (磁盘增长率, 平均清理大小)
        """
        if not reports:
            return 0.0, 0.0

        total_size = 0
        for report in reports:
            freed_size = getattr(report, 'freed_size', 0)
            if freed_size == 0:
                freed_size = report.get('freed_size', 0)
            total_size += freed_size

        avg_size = total_size / total_count if total_count > 0 else 0

        # 磁盘增长率 = 平均清理大小 / 平均间隔天数
        # 这里使用一个简化模型
        growth_rate = avg_size / 7  # 假设一周清理一次

        return growth_rate, avg_size

    def generate_strategy_profile(self, behavior: UserBehaviorProfile) -> Dict[str, Any]:
        """生成策略画像

        基于用户行为画像，生成可用于策略推荐的画像数据。

        Args:
            behavior: 用户行为画像

        Returns:
            策略画像字典
        """
        return {
            'profiling_timestamp': behavior.profiling_timestamp.isoformat(),
            'cleanup_frequency': behavior.cleanup_frequency,
            'avg_interval_days': behavior.avg_interval_days,
            'timing_preference': behavior.timing_preference,
            'time_of_day_preference': behavior.time_of_day_preference,
            'content_preference': behavior.content_preference,
            'risk_tolerance': behavior.risk_tolerance,
            'disk_growth_rate': behavior.disk_growth_rate,
            'avg_cleanup_size': behavior.avg_cleanup_size,
            'total_cleanups': behavior.total_cleanups,
            'last_cleanup_time': behavior.last_cleanup_time.isoformat() if behavior.last_cleanup_time else None,
            # 策略推荐建议
            'strategy_recommendations': self._generate_strategy_recommendations(behavior)
        }

    def _generate_strategy_recommendations(self, behavior: UserBehaviorProfile) -> Dict[str, Any]:
        """生成策略推荐建议（内部方法）

        Args:
            behavior: 用户行为画像

        Returns:
            策略推荐建议
        """
        recommendations = {
            'mode': 'balanced',  # 默认平衡模式
            'schedule': 'weekly',  # 默认每周
            'risk_threshold': 30,  # 默认风险阈值
            'prioritize_size': False,
            'prioritize_recency': False
        }

        # 基于风险容忍度
        if behavior.risk_tolerance == 'low':
            recommendations['mode'] = 'conservative'
            recommendations['risk_threshold'] = 20
            recommendations['schedule'] = 'manual'
        elif behavior.risk_tolerance == 'high':
            recommendations['mode'] = 'aggressive'
            recommendations['risk_threshold'] = 50
            recommendations['schedule'] = 'daily'

        # 基于清理频率
        if behavior.cleanup_frequency == 'daily':
            recommendations['schedule'] = 'daily'
        elif behavior.cleanup_frequency == 'weekly':
            recommendations['schedule'] = 'weekly'
        elif behavior.cleanup_frequency == 'infrequent':
            recommendations['schedule'] = 'manual'

        # 基于清理大小（偏好大文件）
        if behavior.avg_cleanup_size > 500 * 1024 * 1024:  # 大于500MB
            recommendations['prioritize_size'] = True

        # 基于内容偏好设置优先类别
        recommendations['priority_categories'] = []
        if behavior.content_preference in ['game_cache', 'temp_files', 'downloads', 'browser_cache', 'logs', 'build_cache']:
            recommendations['priority_categories'].append(behavior.content_preference)

        return recommendations

    # ========================================================================
    # 策略推荐（基于场景）
    # ========================================================================

    def recommend_based_on_scenario(self, scenario: UserScenario) -> CleanupStrategy:
        """根据用户场景推荐策略

        场景策略映射：
        1. 游戏玩家 - 激进模式，优先清理游戏缓存、临时文件、下载文件夹
        2. 办公电脑 - 平衡模式，优先清理浏览器缓存、临时文件、日志
        3. 开发环境 - 保守模式，保护开发文件，手动调度
        4. 普通用户 - 平衡模式，中等风险

        Args:
            scenario: 用户场景

        Returns:
            推荐的清理策略
        """
        presets = self.load_presets()
        scenario_key = scenario.value

        if scenario_key in presets:
            return CleanupStrategy.from_dict(presets[scenario_key])

        # 如果没有找到预置策略，返回默认策略
        return CleanupStrategy.from_dict(presets.get('normal', self.DEFAULT_PRESETS['normal']))

    # ========================================================================
    # 策略推荐（基于行为）
    # ========================================================================

    def recommend_based_on_behavior(self, cleanup_reports: List[Any]) -> CleanupStrategy:
        """根据用户行为历史推荐策略

        推荐逻辑：
        1. 分析用户清理频率 → 推荐调度计划
        2. 分析用户清理时机 → 推荐偏好时间
        3. 分析用户清理内容 → 推荐优先类别
        4. 分析用户接受的风险 → 推荐风险阈值

        Args:
            cleanup_reports: 清理历史记录列表

        Returns:
            推荐的清理策略
        """
        # 分析用户行为
        behavior = self.analyze_user_behavior(cleanup_reports)

        # 生成策略推荐建议
        recommendations = self._generate_strategy_recommendations(behavior)

        # 创建策略ID
        strategy_id = f"behavior_{uuid.uuid4().hex[:8]}"

        # 转换时间段为具体时间
        preferred_time_map = {
            'morning': '09:00',
            'afternoon': '14:00',
            'evening': '20:00',
            'unknown': None
        }

        # 确定优先类别
        priority_categories = recommendations.get('priority_categories', [])
        if behavior.content_preference != 'unknown' and behavior.content_preference not in priority_categories:
            priority_categories.append(behavior.content_preference)

        # 创建策略
        strategy = CleanupStrategy(
            strategy_id=strategy_id,
            name=f"行为优化策略 ({behavior.cleanup_frequency})",
            description=f"基于用户行为历史生成的策略，风险容忍度：{behavior.risk_tolerance}",
            mode=recommendations['mode'],
            risk_threshold=recommendations['risk_threshold'],
            priority_categories=priority_categories,
            schedule=recommendations['schedule'],
            preferred_time=preferred_time_map.get(behavior.time_of_day_preference),
            prioritize_size=recommendations['prioritize_size'],
            prioritize_recency=False,
            is_preset=False
        )

        return strategy

    # ========================================================================
    # 通用策略推荐
    # ========================================================================

    def recommend_strategy(
        self,
        scenario: Optional[UserScenario] = None,
        cleanup_reports: Optional[List[Any]] = None
    ) -> CleanupStrategy:
        """推荐最优策略

        优先级：
        1. 如果有行为历史，优先基于行为推荐
        2. 如果有场景配置，基于场景推荐
        3. 否则返回默认平衡策略

        Args:
            scenario: 用户场景（可选）
            cleanup_reports: 清理历史记录（可选）

        Returns:
            推荐的清理策略
        """
        # 优先基于行为推荐
        if cleanup_reports and len(cleanup_reports) >= 2:
            try:
                return self.recommend_based_on_behavior(cleanup_reports)
            except Exception as e:
                print(f"[CleanupStrategyManager] 基于行为推荐失败: {e}")

        # 基于场景推荐
        if scenario:
            return self.recommend_based_on_scenario(scenario)

        # 默认策略
        return self.get_preset_strategy(UserScenario.NORMAL)

    # ========================================================================
    # 策略历史管理
    # ========================================================================

    def save_user_strategy(
        self,
        strategy: CleanupStrategy,
        success_rate: float = 0.0,
        accepted_recommendations: bool = False,
        feedback_score: Optional[int] = None,
        notes: str = ""
    ) -> StrategyHistory:
        """保存用户采用的策略

        Args:
            strategy: 清理策略
            success_rate: 成功率
            accepted_recommendations: 是否接受了推荐
            feedback_score: 用户反馈评分（1-5）
            notes: 备注

        Returns:
            策略历史记录
        """
        history_id = str(uuid.uuid4())

        history = StrategyHistory(
            history_id=history_id,
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            applied_at=datetime.now(),
            success_rate=success_rate,
            acceptedrecommendations=accepted_recommendations,
            feedback_score=feedback_score,
            notes=notes
        )

        # 加载现有历史
        histories = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    histories = data.get('histories', [])
            except Exception as e:
                print(f"[CleanupStrategyManager] 加载历史失败: {e}")

        # 添加新历史
        histories.append(history.to_dict())

        # 只保留最近 100 条记录
        if len(histories) > 100:
            histories = histories[-100:]

        # 保存
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({'histories': histories}, f, ensure_ascii=False, indent=2)
            print(f"[CleanupStrategyManager] 保存策略历史: {strategy.name}")
        except Exception as e:
            print(f"[CleanupStrategyManager] 保存历史失败: {e}")

        return history

    def get_strategy_history(self, limit: int = 50) -> List[StrategyHistory]:
        """获取策略历史

        Args:
            limit: 最大返回数量

        Returns:
            策略历史列表
        """
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                histories_data = data.get('histories', [])
        except Exception as e:
            print(f"[CleanupStrategyManager] 加载历史失败: {e}")
            return []

        # 转换为 StrategyHistory 对象
        histories = []
        for h_data in histories_data[-limit:]:
            if 'applied_at' in h_data and isinstance(h_data['applied_at'], str):
                h_data['applied_at'] = datetime.fromisoformat(h_data['applied_at'])
            histories.append(StrategyHistory(**h_data))

        # 按时间倒序
        histories.sort(key=lambda h: h.applied_at, reverse=True)

        return histories

    # ========================================================================
    # 策略评分与优化
    # ========================================================================

    def evaluate_strategy_effectiveness(
        self,
        strategy: CleanupStrategy,
        recent_reports: List[Any]
    ) -> Dict[str, float]:
        """评估策略效果

        评估维度：
        1. 清理成功率
        2. 清理效率（释放空间 / 时间）
        3. 用户满意度（基于反馈评分）

        Args:
            strategy: 清理策略
            recent_reports: 最近的清理报告

        Returns:
            评估结果字典
        """
        if not recent_reports:
            return {
                'success_rate': 0.0,
                'efficiency': 0.0,
                'satisfaction': 0.0,
                'overall_score': 0.0
            }

        # 获取使用该策略的历史记录
        histories = [
            h for h in self.get_strategy_history()
            if h.strategy_id == strategy.strategy_id
        ]

        if not histories:
            return {
                'success_rate': 0.0,
                'efficiency': 0.0,
                'satisfaction': 0.0,
                'overall_score': 0.0
            }

        # 计算成功率
        success_rates = [h.success_rate for h in histories if h.success_rate > 0]
        success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0

        # 计算满意度
        feedback_scores = [h.feedback_score for h in histories if h.feedback_score is not None]
        satisfaction = sum(feedback_scores) / len(feedback_scores) / 5 if feedback_scores else 0.0

        # 计算效率（简化：假设每天清理）
        avg_size = sum(r.freed_size for r in recent_reports) / len(recent_reports)
        efficiency = min(avg_size / (1024 * 1024 * 100), 1.0)  # 标准化到 0-1

        # 综合评分
        overall_score = (success_rate * 0.4 + satisfaction * 0.4 + efficiency * 0.2)

        return {
            'success_rate': success_rate,
            'efficiency': efficiency,
            'satisfaction': satisfaction,
            'overall_score': overall_score
        }

    # ========================================================================
    # 自定义策略创建
    # ========================================================================

    def create_custom_strategy(
        self,
        name: str,
        description: str,
        mode: str,
        risk_threshold: int,
        priority_categories: List[str],
        schedule: Optional[str] = None,
        preferred_time: Optional[str] = None,
        prioritize_size: bool = False,
        prioritize_recency: bool = False
    ) -> CleanupStrategy:
        """创建自定义策略

        Args:
            name: 策略名称
            description: 策略描述
            mode: 清理模式
            risk_threshold: 风险阈值
            priority_categories: 优先清理的类别
            schedule: 调度计划
            preferred_time: 偏好时间
            prioritize_size: 优先处理大文件
            prioritize_recency: 优先处理最近文件

        Returns:
            自定义清理策略
        """
        strategy_id = f"custom_{uuid.uuid4().hex[:8]}"

        strategy = CleanupStrategy(
            strategy_id=strategy_id,
            name=name,
            description=description,
            mode=mode,
            risk_threshold=risk_threshold,
            priority_categories=priority_categories,
            schedule=schedule,
            preferred_time=preferred_time,
            prioritize_size=prioritize_size,
            prioritize_recency=prioritize_recency,
            is_preset=False
        )

        return strategy


# ============================================================================
# 便利函数
# ============================================================================

def get_strategy_manager(config_path: Optional[str] = None) -> CleanupStrategyManager:
    """获取策略管理器实例

    Args:
        config_path: 策略配置文件路径（可选）

    Returns:
        CleanupStrategyManager 实例
    """
    return CleanupStrategyManager(config_path)
