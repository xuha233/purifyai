# -*- coding: utf-8 -*-
"""
清理策略管理器测试模块 (Cleanup Strategy Manager Tests)

测试 CleanupStrategyManager 类的核心功能

作者: 小午 🦁
创建时间: 2026-02-24
"""

import pytest
from datetime import datetime
from src.agent.cleanup_strategy_manager import (
    CleanupStrategy,
    CleanupStrategyManager,
    UserScenario,
    StrategyProfile
)
from src.agent.smart_recommender import CleanupReport


class TestCleanupStrategy:
    """清理策略测试"""

    def test_strategy_creation(self):
        """测试策略创建"""
        strategy = CleanupStrategy(
            strategy_id="test_strategy",
            name="Test Strategy",
            description="Test description",
            mode="balanced",
            risk_threshold=30,
            priority_categories=["browser_cache", "temp_files"]
        )

        assert strategy.strategy_id == "test_strategy"
        assert strategy.name == "Test Strategy"
        assert strategy.mode == "balanced"
        assert strategy.risk_threshold == 30


class TestCleanupStrategyManager:
    """清理策略管理器测试"""

    @pytest.fixture
    def strategy_manager(self):
        """创建管理器实例"""
        return CleanupStrategyManager()

    def test_load_preset_strategies(self, strategy_manager):
        """测试加载预置策略"""
        presets = strategy_manager.load_preset_strategies()

        assert isinstance(presets, dict)
        assert "gamer" in presets
        assert "office" in presets
        assert "developer" in presets
        assert "normal" in presets

    def test_recommend_gamer_strategy(self, strategy_manager):
        """测试游戏玩家策略推荐"""
        strategy = strategy_manager.recommend_based_on_scenario(UserScenario.GAMER)

        assert strategy.strategy_id == "gamer_preferred"
        assert strategy.mode == "aggressive"
        assert strategy.risk_threshold == 50
        assert "game_cache" in strategy.priority_categories

    def test_recommend_office_strategy(self, strategy_manager):
        """测试办公电脑策略推荐"""
        strategy = strategy_manager.recommend_based_on_scenario(UserScenario.OFFICE)

        assert strategy.strategy_id == "office_standard"
        assert strategy.mode == "balanced"
        assert strategy.risk_threshold == 30
        assert "browser_cache" in strategy.priority_categories

    def test_recommend_developer_strategy(self, strategy_manager):
        """测试开发者策略推荐"""
        strategy = strategy_manager.recommend_based_on_scenario(UserScenario.DEVELOPER)

        assert strategy.strategy_id == "dev_conservative"
        assert strategy.mode == "conservative"
        assert strategy.risk_threshold == 20
        assert "build_cache" in strategy.priority_categories

    def test_recommend_normal_strategy(self, strategy_manager):
        """测试普通用户策略推荐"""
        strategy = strategy_manager.recommend_based_on_scenario(UserScenario.NORMAL)

        assert strategy.strategy_id == "normal_balanced"
        assert strategy.mode == "balanced"
        assert strategy.risk_threshold == 30

    def test_analyze_user_behavior_empty_history(self, strategy_manager):
        """测试用户行为分析 - 空历史"""
        behavior = strategy_manager.analyze_user_behavior([])

        assert behavior["frequency"] == "unknown"
        assert behavior["timing_preference"] == "unknown"

    def test_analyze_user_behavior_with_history(self, strategy_manager):
        """测试用户行为分析 - 有历史"""
        # 创建模拟清理报告
        now = datetime.now()
        reports = [
            CleanupReport(
                report_id="r1",
                plan_id="p1",
                started_at=now - timedelta(days=7),
                completed_at=now - timedelta(days=7),
                duration_seconds=60,
                total_items=100,
                success_count=100,
                failed_count=0,
                space_freed=1024,
                details=[]
            ),
            CleanupReport(
                report_id="r2",
                plan_id="p2",
                started_at=now - timedelta(days=3),
                completed_at=now - timedelta(days=3),
                duration_seconds=60,
                total_items=100,
                success_count=100,
                failed_count=0,
                space_freed=1024,
                details=[]
            )
        ]

        behavior = strategy_manager.analyze_user_behavior(reports)

        assert behavior["frequency"] in ["daily", "weekly"]
        assert behavior["timing_preference"] in ["weekday", "weekend"]

    def test_generate_strategy_profile(self, strategy_manager):
        """测试策略画像生成"""
        behavior = {
            "frequency": "weekly",
            "timing_preference": "weekend",
            "content_preference": "browser_cache",
            "risk_tolerance": "medium"
        }

        profile = strategy_manager.generate_strategy_profile(behavior)

        assert isinstance(profile, StrategyProfile)
        assert profile.frequency == "weekly"
        assert profile.timing_preference == "weekend"

    def test_save_user_strategy(self, strategy_manager):
        """测试保存用户策略"""
        strategy = strategy_manager.recommend_based_on_scenario(UserScenario.GAMER)

        success = strategy_manager.save_user_strategy(strategy)

        assert success

    def test_get_strategy_history(self, strategy_manager):
        """测试获取策略历史"""
        strategy = strategy_manager.recommend_based_on_scenario(UserScenario.GAMER)
        strategy_manager.save_user_strategy(strategy)

        history = strategy_manager.get_strategy_history()

        assert isinstance(history, list)
        assert len(history) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
