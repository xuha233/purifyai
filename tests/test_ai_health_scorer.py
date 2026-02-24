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
        score = health_scorer._calculate_disk_usage_score(25.5)
        assert score == 100

        score = health_scorer._calculate_disk_usage_score(29.9)
        assert score == 100

    def test_disk_usage_score_good(self, health_scorer):
        """测试磁盘使用率评分 - 良好（30-60%）"""
        score = health_scorer._calculate_disk_usage_score(45.0)
        # 100 - (45-30)*1.5 = 77.5 → 78
        assert 70 <= score < 100

        score = health_scorer._calculate_disk_usage_score(40.0)
        # 100 - (40-30)*1.5 = 85
        assert 80 <= score <= 90

    def test_disk_usage_score_average(self, health_scorer):
        """测试磁盘使用率评分 - 一般（60-80%）"""
        score = health_scorer._calculate_disk_usage_score(70.0)
        # 70 - (70-60)*2.5 = 45
        assert 20 <= score < 70

        score = health_scorer._calculate_disk_usage_score(75.0)
        # 70 - (75-60)*2.5 = 32.5 → 33
        assert 30 <= score < 40

    def test_disk_usage_score_poor(self, health_scorer):
        """测试磁盘使用率评分 - 差（>80%）"""
        score = health_scorer._calculate_disk_usage_score(85.0)
        # 20 - (85-80)*1 = 15
        assert score <= 20

        score = health_scorer._calculate_disk_usage_score(95.0)
        # 20 - (95-80)*1 = 5
        assert score <= 10

    def test_cleanable_space_score(self, health_scorer):
        """测试可清理空间评分（空间少=高分，空间多=低分）"""
        # <1GB: 优秀（高分）
        score = health_scorer._calculate_cleanable_space_score(500)
        assert score == 100

        # 1-3GB: 良好
        score = health_scorer._calculate_cleanable_space_score(2000)
        # 2000MB = 1.95GB, 100 - (1.95-1)*15 = 85.75 → 86
        assert 80 <= score < 90

        # 3-5GB: 一般
        score = health_scorer._calculate_cleanable_space_score(4000)
        # 4000MB = 3.9GB, 70 - (3.9-3)*20 = 52
        assert 50 <= score < 60

        # >5GB: 差（低分）
        score = health_scorer._calculate_cleanable_space_score(6000)
        # 6000MB = 5.86GB, 30 - (5.86-5)*5 = 25.7 → 26
        assert score < 30

    def test_fragmentation_score(self, health_scorer):
        """测试文件碎片度评分"""
        # <5%: 优秀
        score = health_scorer._calculate_fragmentation_score(3)
        assert score == 100

        # 5-15%: 良好
        score = health_scorer._calculate_fragmentation_score(10)
        # 100 - (10-5)*7.5 = 62.5 → 63
        assert 60 <= score < 65

        # 15-30%: 一般
        score = health_scorer._calculate_fragmentation_score(20)
        # 25 - (20-15)*1.5 = 17.5 → 18
        assert 15 <= score < 20

        # >30%: 差
        score = health_scorer._calculate_fragmentation_score(40)
        # 5 - (40-30)*0.2 = 3
        assert score < 5

    def test_performance_score(self, health_scorer):
        """测试系统性能评分"""
        # <5MB/day: 优秀
        score = health_scorer._calculate_performance_score(3)
        # < 5 → 100
        assert score == 100

        # 5-20MB/day: 良好
        score = health_scorer._calculate_performance_score(10)
        # 100 - (10-5)*2.67 = 100 - 13.35 = 86.65 → 87
        assert 80 <= score < 90

        # 20-50MB/day: 一般
        score = health_scorer._calculate_performance_score(30)
        # 60 - (30-20)*1.33 = 60 - 13.3 = 46.7 → 47
        assert 40 <= score < 50

        # >50MB/day: 差
        score = health_scorer._calculate_performance_score(60)
        # 20 - (60-50)*0.3 = 20 - 3 = 17
        assert 10 <= score < 20

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
        """测试健康报告生成（通过analyze_disk_health方法）"""
        # 测试是否能生成报告（不需要真实的磁盘数据）
        # 这里我们只测试 calculate_health_score 公共方法
        total_score = health_scorer.calculate_health_score(
            disk_usage_percent=75,
            cleanable_space_mb=4000,
            fragmentation_percent=20,
            growth_speed_mb_per_day=25
        )
        assert 0 <= total_score <= 100

    def test_cleanup_priority_recommendation_high(self, health_scorer):
        """测试高优先级推荐"""
        from src.agent.ai_health_scorer import HealthReport
        report = HealthReport(
            score=40,
            disk_usage_score=50,
            cleanable_space_score=30,
            fragmentation_score=40,
            performance_score=45,
            cleanable_space_mb=5000
        )
        priority = health_scorer.recommend_cleanup_priority(report)
        assert priority == HealthPriority.HIGH

    def test_cleanup_priority_recommendation_medium(self, health_scorer):
        """测试中优先级推荐"""
        from src.agent.ai_health_scorer import HealthReport
        report = HealthReport(
            score=60,
            disk_usage_score=70,
            cleanable_space_score=60,
            fragmentation_score=65,
            performance_score=55,
            cleanable_space_mb=2000
        )
        priority = health_scorer.recommend_cleanup_priority(report)
        assert priority == HealthPriority.MEDIUM

    def test_cleanup_priority_recommendation_low(self, health_scorer):
        """测试低优先级推荐"""
        from src.agent.ai_health_scorer import HealthReport
        report = HealthReport(
            score=80,
            disk_usage_score=85,
            cleanable_space_score=80,
            fragmentation_score=82,
            performance_score=78,
            cleanable_space_mb=500
        )
        priority = health_scorer.recommend_cleanup_priority(report)
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
