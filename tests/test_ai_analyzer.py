"""
AI分析器单元测试

测试范围:
- AIAnalyzer 类
- 成本控制逻辑
- 批量评估
- 调用计数器
- 统计功能
"""
import pytest
import sys
import os

# 添加 src 到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.ai_analyzer import (
    AIAnalyzer,
    AIAnalysisStats,
    CostControlConfig,
    CostControlMode,
    get_ai_analyzer
)
from core.ai_client import AIConfig
from core.rule_engine import RiskLevel
from core.models import ScanItem
from core.models_smart import CleanupItem, CleanupPlan


# ============================================================================
# CostControlMode 枚举测试
# ============================================================================

def test_cost_control_mode_values():
    """测试 CostControlMode 枚举的值"""
    assert CostControlMode.UNLIMITED.value == "unlimited"
    assert CostControlMode.BUDGET.value == "budget"
    assert CostControlMode.FALLBACK.value == "fallback"
    assert CostControlMode.RULES_ONLY.value == "rules_only"


# ============================================================================
# CostControlConfig 数据类测试
# ============================================================================

def test_cost_control_config_creation():
    """测试 CostControlConfig 创建"""
    config = CostControlConfig()
    assert config.mode == CostControlMode.FALLBACK
    assert config.max_calls_per_scan == 100
    assert config.batch_size == 50
    assert config.only_analyze_suspicious is True
    assert config.fallback_to_rules is True


def test_cost_control_config_custom():
    """测试自定义 CostControlConfig"""
    config = CostControlConfig(
        mode=CostControlMode.UNLIMITED,
        max_calls_per_scan=500,
        batch_size=100,
        only_analyze_suspicious=False
    )
    assert config.mode == CostControlMode.UNLIMITED
    assert config.max_calls_per_scan == 500
    assert config.batch_size == 100
    assert config.only_analyze_suspicious is False


# ============================================================================
# AIAnalysisStats 数据类测试
# ============================================================================

def test_ai_analysis_stats_creation():
    """测试 AIAnalysisStats 创建"""
    stats = AIAnalysisStats(
        total_items=100,
        items_with_ai=20,
        safe_count=50,
        suspicious_count=30,
        dangerous_count=20
    )
    assert stats.total_items == 100
    assert stats.items_with_ai == 20
    assert stats.ai_coverage == 20.0
    assert stats.safe_count == 50


def test_ai_analysis_stats_coverage():
    """测试 AI覆盖率计算"""
    stats = AIAnalysisStats(total_items=100, items_with_ai=50)
    assert stats.ai_coverage == 50.0

    stats = AIAnalysisStats(total_items=0, items_with_ai=0)
    assert stats.ai_coverage == 0.0


# ============================================================================
# AIAnalyzer 类测试
# ============================================================================

def test_ai_analyzer_creation():
    """测试 AIAnalyzer 创建"""
    analyzer = AIAnalyzer()
    assert analyzer is not None
    assert analyzer.get_call_count() == 0


def test_get_ai_analyzer():
    """测试便利函数"""
    analyzer = get_ai_analyzer()
    assert analyzer is not None


def test_ai_analyzer_with_config():
    """测试带配置的 AIAnalyzer 创建"""
    ai_config = AIConfig(api_key="test_key")
    cost_config = CostControlConfig(mode=CostControlMode.FALLBACK)

    analyzer = AIAnalyzer(ai_config, cost_config)
    assert analyzer.cost_config.mode == CostControlMode.FALLBACK


def test_reset_call_count():
    """测试重置调用计数"""
    analyzer = AIAnalyzer()
    # 模拟调用计数
    analyzer._call_count = 10
    assert analyzer.get_call_count() == 10

    analyzer.reset_call_count()
    assert analyzer.get_call_count() == 0


def test_get_stats():
    """测试获取统计信息"""
    analyzer = AIAnalyzer()
    stats = analyzer.get_stats()
    assert isinstance(stats, AIAnalysisStats)


def test_is_ai_enabled():
    """测试 AI 启用状态"""
    # 没有 API key 时应该禁用
    analyzer = AIAnalyzer()
    assert analyzer.is_ai_enabled() is False

    # 有 API key 时应该启用
    ai_config = AIConfig(api_key="test_key")
    analyzer = AIAnalyzer(ai_config)
    assert analyzer.is_ai_enabled() is True

    # 规则仅模式应该禁用 AI
    cost_config = CostControlConfig(mode=CostControlMode.RULES_ONLY)
    analyzer = AIAnalyzer(None, cost_config)
    assert analyzer.is_ai_enabled() is False


def test_set_cost_config():
    """测试设置成本控制配置"""
    analyzer = AIAnalyzer()
    new_config = CostControlConfig(mode=CostControlMode.UNLIMITED)
    analyzer.set_cost_config(new_config)

    assert analyzer.cost_config.mode == CostControlMode.UNLIMITED


def test_analyze_scan_results_empty():
    """测试分析空扫描结果"""
    analyzer = AIAnalyzer()
    plan = analyzer.analyze_scan_results([])

    assert isinstance(plan, CleanupPlan)
    assert len(plan.items) == 0


def test_analyze_scan_results_with_items():
    """测试分析扫描结果"""
    analyzer = AIAnalyzer()

    # 创建测试扫描项
    items = [
        ScanItem(
            path="C:/Temp/test.log",
            description="日志文件",
            size=1024,
            item_type="file",
            risk_level="safe"
        ),
        ScanItem(
            path="C:/Temp/cache.tmp",
            description="缓存文件",
            size=2048,
            item_type="file",
            risk_level="safe"
        ),
    ]

    plan = analyzer.analyze_scan_results(items)

    assert isinstance(plan, CleanupPlan)
    assert len(plan.items) == 2
    assert plan.total_size == 1024 + 2048  # 3072


def test_analyze_cost_control_rules_only():
    """测试规则仅模式的成本控制"""
    cost_config = CostControlConfig(mode=CostControlMode.RULES_ONLY)
    analyzer = AIAnalyzer(cost_config=cost_config)

    items = [
        ScanItem(
            path="C:/Temp/test.log",
            description="日志文件",
            size=1024,
            item_type="file",
            risk_level="safe"
        ),
    ]

    plan = analyzer.analyze_scan_results(items)

    assert len(plan.items) == 1
    assert analyzer._call_count == 0  # 规则仅模式不应调用 AI


def test_get_stats_report():
    """测试获取统计报告"""
    analyzer = AIAnalyzer()
    report = analyzer.get_stats_report()

    assert "AI分析统计" in report
    assert "总项目" in report
    assert "AI评估" in report


# ============================================================================
# 辅助方法测试
# ============================================================================

def test_to_cleanup_item():
    """测试转换为 CleanupItem"""
    analyzer = AIAnalyzer()

    scan_item = ScanItem(
        path="C:/Temp/test.log",
        description="日志文件",
        size=1024,
        item_type="file",
        risk_level="safe"
    )

    risk_result = {
        'risk_level': "safe",
        'reason': '可安全删除',
        'method': 'rule'
    }

    cleanup_item = analyzer._to_cleanup_item(scan_item, risk_result)

    assert isinstance(cleanup_item, CleanupItem)
    assert cleanup_item.path == "C:/Temp/test.log"
    assert cleanup_item.size == 1024


def test_to_scan_item():
    """测试转换为 ScanItem"""
    analyzer = AIAnalyzer()

    cleanup_item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.log",
        size=1024,
        item_type="file",
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )

    scan_item = analyzer._to_scan_item(cleanup_item)

    assert isinstance(scan_item, ScanItem)
    assert scan_item.path == "C:/Temp/test.log"


# ============================================================================
# 边界条件测试
# ============================================================================

def test_cost_control_max_calls_limit():
    """测试最大调用次数限制"""
    ai_config = AIConfig(api_key="test_key")
    cost_config = CostControlConfig(
        mode=CostControlMode.BUDGET,
        max_calls_per_scan=5  # 限制为5次调用
    )
    analyzer = AIAnalyzer(ai_config, cost_config)

    assert analyzer.cost_config.max_calls_per_scan == 5


def test_analyze_with_progress_callback():
    """测试带进度回调的分析"""
    analyzer = AIAnalyzer()

    callback_calls = []

    def progress_callback(current, total):
        callback_calls.append((current, total))

    items = [
        ScanItem(
            path=f"C:/Temp/file{i}.log",
            description=f"日志文件 {i}",
            size=1024,
            item_type="file",
            risk_level="safe"
        )
        for i in range(10)
    ]

    plan = analyzer.analyze_scan_results(items, progress_callback)

    assert len(plan.items) == 10
    # 进度回调应该被调用（规则引擎评估）
    assert len(callback_calls) > 0


# ============================================================================
# CleanupPlan 测试
# ============================================================================

def test_cleanup_plan_properties():
    """测试 CleanupPlan 的属性"""
    analyzer = AIAnalyzer()

    items = [
        ScanItem(
            path="C:/Temp/safe.log",
            description="安全日志",
            size=1024,
            item_type="file",
            risk_level="safe"
        ),
        ScanItem(
            path="C:/Temp/suspicious.tmp",
            description="可疑临时文件",
            size=2048,
            item_type="file",
            risk_level="suspicious"
        ),
    ]

    plan = analyzer.analyze_scan_results(items)

    # 检查属性
    assert plan.plan_id.startswith("plan_")
    assert plan.scan_type == "custom"
    assert len(plan.items) == 2
    assert plan.total_items == 2
    assert plan.total_size == 1024 + 2048

    # 检查风险分类
    assert len(plan.safe_items) + len(plan.suspicious_items) + len(plan.dangerous_items) == 2
