# -*- coding: utf-8 -*-
"""
AI 健康评分测试模块 (AI Health Scorer Tests)

测试 AIHealthScorer 类的核心功能

作者: 小午 🦁 (手动补充测试)
创建时间: 2026-02-24
"""

import pytest
from datetime import datetime
from src.agent.ai_health_scorer import (
    AIHealthScorer,
    HealthReport,
    HealthRecommendation,
    HealthPriority,
    HealthCategory
)
from src.core.models import ScanItem


class TestAIHealthScorer:
    """AIHealthScorer 类测试"""

    @pytest.fixture
    def health_scorer(self):
        """创建 AIHealthScorer 实例"""
        return AIHealthScorer()

    def test_disk_usage_score_excellent(self, health_scorer):
        """测试磁盘使用率评分 - 优秀（<30%）"""
        score = health_scorer.calculate_disk_usage_score(25.5)
        assert score == 100

        score = health_scorer.calculate_disk_usage_score(29.9)
        assert score == 100

    def test_disk_usage_score_good(self, health_scorer):
        """测试磁盘使用率评分 - 良好（30-60%）"""
        score = health_scorer.calculate_disk_usage_score(45.0)
        assert 70 <= score < 100

        score = health_scorer.calculate_disk_usage_score(59.9)
        assert 70 <= score < 100

    def test_disk_usage_score_average(self, health_scorer):
        """测试磁盘使用率评分 - 一般（60-80%）"""
        score = health_scorer.calculate_disk_usage_score(70.0)
        assert 20 <= score < 70

        score = health_scorer.calculate_disk_usage_score(79.9)
        assert 0 <= score < 20

    def test_disk_usage_score_poor(self, health_scorer):
        """测试磁盘使用率评分 - 差（>80%）"""
        score = health_scorer.calculate_disk_usage_score(85.0)
        assert score <= 20

        score = health_scorer.calculate_disk_usage_score(95.0)
        assert score < 10

    def test_cleanable_space_score(self, health_scorer):
        """测试可清理空间评分"""
        # <1GB: 优秀
        score = health_scorer.calculate_cleanable_space_score(500)
        assert score < 20

        # 1-3GB: 良好
        score = health_scorer.calculate_cleanable_space_score(2000)
        assert 20 <= score < 60

        # 3-5GB: 一般
        score = health_scorer.calculate_cleanable_space_score(4000)
        assert 60 <= score < 100

        # >5GB: 差
        score = health_scorer.calculate_cleanable_space_score(6000)
        assert score >= 100

    def test_fragmentation_score(self, health_scorer):
        """测试文件碎片度评分"""
        # <5%: 优秀
        score = health_scorer.calculate_fragmentation_score(3)
        assert score >= 90

        # 5-15%: 良好
        score = health_scorer.calculate_fragmentation_score(10)
        assert 70 <= score < 90

        # 15-30%: 一般
        score = health_scorer.calculate_fragmentation_score(20)
        assert 40 <= score < 70

        # >30%: 差
        score = health_scorer.calculate_fragmentation_score(40)
        assert score < 20

    def test_performance_score(self, health_scorer):
        """测试系统性能评分"""
        # <5MB/day: 优秀
        score = health_scorer.calculate_performance_score(3)
        assert score >= 85

        # 5-20MB/day: 良好
        score = health_scorer.calculate_performance_score(10)
        assert 50 <= score < 85

        # 20-50MB/day: 一般
        score = health_scorer.calculate_performance_score(30)
        assert 0 < score < 50

        # >50MB/day: 差
        score = health_scorer.calculate_performance_score(60)
        assert score == 0

    def test_total_health_score(self, health_scorer):
        """测试总分计算"""
        # 优秀情况
        score = health_scorer.calculate_health_score(
            disk_usage_percent=25,
            cleanable_space_mb=500,
            fragmentation_percent=3,
            growth_speed_mb_per_day=3
        )
        assert score >= 85

        # 一般情况
        score = health_scorer.calculate_health_score(
            disk_usage_percent=50,
            cleanable_space_mb=2500,
            fragmentation_percent=15,
            growth_speed_mb_per_day=15
        )
        assert 50 <= score < 85

        # 差的情况
        score = health_scorer.calculate_health_score(
            disk_usage_percent=85,
            cleanable_space_mb=6000,
            fragmentation_percent=40,
            growth_speed_mb_per_day=60
        )
        assert score < 50

    def test_health_report_generation(self, health_scorer):
        """测试健康报告生成"""
        report = health_scorer.generate_health_report(
            disk_usage_percent=75,
            cleanable_space_mb=4000,
            fragmentation_percent=20,
            growth_speed_mb_per_day=25
        )

        assert isinstance(report, HealthReport)
        assert 0 <= report.score <= 100
        assert 0 <= report.disk_usage_score <= 100
        assert 0 <= report.cleanable_space_score <= 100
        assert 0 <= report.fragmentation_score <= 100
        assert 0 <= report.performance_score <= 100
        assert isinstance(report.recommendations, list)
        assert isinstance(report.priority, HealthPriority)

    def test_cleanup_priority_recommendation_high(self, health_scorer):
        """测试高优先级推荐"""
        priority = health_scorer.recommend_cleanup_priority(
            health_score=40,
            cleanable_space_mb=5000
        )
        assert priority == HealthPriority.HIGH

    def test_cleanup_priority_recommendation_medium(self, health_scorer):
        """测试中优先级推荐"""
        priority = health_scorer.recommend_cleanup_priority(
            health_score=60,
            cleanable_space_mb=2000
        )
        assert priority == HealthPriority.MEDIUM

    def test_cleanup_priority_recommendation_low(self, health_scorer):
        """测试低优先级推荐"""
        priority = health_scorer.recommend_cleanup_priority(
            health_score=80,
            cleanable_space_mb=500
        )
        assert priority == HealthPriority.LOW


class TestHealthRecommendation:
    """健康推荐测试"""

    def test_health_recommendation_creation(self):
        """测试健康推荐创建"""
        recommendation = HealthRecommendation(
            category=HealthCategory.DISK_SPACE,
            issue="磁盘使用率 85%",
            solution="执行一键清理",
            potential_save=2000
        )

        assert recommendation.category == HealthCategory.DISK_SPACE
        assert recommendation.issue == "磁盘使用率 85%"
        assert recommendation.solution == "执行一键清理"
        assert recommendation.potential_save == 2000


class TestHealthReport:
    """健康报告测试"""

    def test_health_report_creation(self):
        """测试健康报告创建"""
        report = HealthReport(
            score=75,
            disk_usage_score=70,
            cleanable_space_score=80,
            fragmentation_score=75,
            performance_score=72,
            recommendations=[],
            priority=HealthPriority.MEDIUM
        )

        assert report.score == 75
        assert report.disk_usage_score == 70
        assert report.cleanable_space_score == 80
        assert report.fragmentation_score == 75
        assert report.performance_score == 72
        assert len(report.recommendations) == 0
        assert report.priority == HealthPriority.MEDIUM


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
