"""
规则引擎增强功能单元测试 (Phase 2 Day 5)

测试范围:
- 批量评估方法
- Suspicious 级别识别
- 描述生成
- reason_id 相关功能
"""
import pytest
import sys
import os

# 添加 src 到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.rule_engine import RuleEngine, Rule, RiskLevel, get_rule_engine


# ============================================================================
# 批量评估方法测试
# ============================================================================

def test_classify_batch():
    """测试批量分类"""
    engine = RuleEngine()

    items = [
        ("C:/Temp/test.log", 1024),
        ("C:/Temp/cache.tmp", 2048),
        ("C:/Windows/system32/dll.exe", 4096),
    ]

    results = engine.classify_batch(items)

    assert len(results) == 3
    # Temp 文件应该是 SAFE
    assert results[0] == RiskLevel.SAFE or results[0] == RiskLevel.SUSPICIOUS
    # Cache 文件应该是 SAFE 或 SUSPICIOUS
    assert results[1] in [RiskLevel.SAFE, RiskLevel.SUSPICIOUS]
    # 系统文件应该是 DANGEROUS
    assert results[2] == RiskLevel.DANGEROUS


def test_classify_batch_with_progress():
    """测试带进度回调的批量分类"""
    engine = RuleEngine()

    items = [("C:/Temp/file{}.tmp".format(i), i * 1024) for i in range(10)]

    progress_calls = []

    def progress_callback(current, total):
        progress_calls.append((current, total))

    results = engine.classify_batch(items, progress_callback)

    assert len(results) == 10
    assert len(progress_calls) == 10
    assert progress_calls[-1] == (10, 10)


def test_evaluate_paths_batch():
    """测试批量评估路径"""
    engine = RuleEngine()

    paths = [
        "C:/Temp/test.log",
        "C:/Temp/cache.tmp",
        "C:/Windows/system32/test.dll",
    ]

    results = engine.evaluate_paths_batch(paths)

    assert len(results) == 3
    assert "C:/Temp/test.log" in results
    assert "C:/Windows/system32/test.dll" in results
    assert results["C:/Windows/system32/test.dll"] == RiskLevel.DANGEROUS


def test_filter_by_risk_level():
    """测试按风险等级过滤"""
    engine = RuleEngine()

    items = [
        ("C:/Temp/safe.log", 1024),
        ("C:/Temp/safe2.tmp", 2048),
        ("C:/Windows/system32/danger.exe", 4096),
    ]

    # 过滤 DANGEROUS 级别
    dangerous_items = engine.filter_by_risk_level(items, RiskLevel.DANGEROUS)

    assert len(dangerous_items) == 1
    assert dangerous_items[0][0] == "C:/Windows/system32/danger.exe"


def test_filter_by_risk_level_safe():
    """测试过滤 SAFE 级别"""
    engine = RuleEngine()

    items = [
        ("C:/Temp/file1.log", 1024),
        ("C:/Temp/file2.tmp", 2048),
        ("C:/Windows/system32/danger.exe", 4096),
    ]

    safe_items = engine.filter_by_risk_level(items, RiskLevel.SAFE)

    # 应该找到至少一个安全项（Temp 目录下的文件）
    assert len(safe_items) >= 1


# ============================================================================
# 带描述的分类测试
# ============================================================================

def test_classify_with_description_safe():
    """测试带分类的安全描述"""
    engine = RuleEngine()

    risk_level, description = engine.classify_with_description("C:/Temp/test.log", 1024)

    assert risk_level in [RiskLevel.SAFE, RiskLevel.SUSPICIOUS]
    assert len(description) > 0
    assert "删除" in description or "清理" in description


def test_classify_with_description_dangerous():
    """测试带分类的危险描述"""
    engine = RuleEngine()

    risk_level, description = engine.classify_with_description("C:/Windows/system32/test.dll", 4096)

    assert risk_level == RiskLevel.DANGEROUS
    assert len(description) > 0
    assert "不建议删除" in description or "危险" in description


def test_generate_description_temp():
    """测试生成临时文件描述"""
    engine = RuleEngine()

    desc = engine.generate_description("C:/Temp/test.log", RiskLevel.SAFE)

    assert "temp" in desc.lower() or "临时" in desc


def test_generate_description_cache():
    """测试生成缓存文件描述"""
    engine = RuleEngine()

    desc = engine.generate_description("C:/Temp/cache.tmp", RiskLevel.SAFE)

    # 描述应该包含删除或清理相关词汇
    assert len(desc) > 0
    assert "删除" in desc or "清理" in desc


def test_generate_description_system():
    """测试生成系统文件描述"""
    engine = RuleEngine()

    desc = engine.generate_description("C:/Windows/system32/test.dll", RiskLevel.DANGEROUS)

    assert len(desc) > 0
    assert "不建议删除" in desc or "危险" in desc


# ============================================================================
# Suspicious 级别识别测试
# ============================================================================

def test_suspicious_config_files():
    """测试识别配置文件为可疑"""
    engine = RuleEngine()

    risk_level = engine.classify("C:/AppData/app/config.json", 512)
    assert risk_level == RiskLevel.SUSPICIOUS


def test_suspicious_user_data():
    """测试识别用户数据为可疑"""
    engine = RuleEngine()

    risk_level = engine.classify("C:/UserData/documents.db", 10240)
    assert risk_level == RiskLevel.SUSPICIOUS


def test_suspicious_settings():
    """测试识别设置文件为可疑"""
    engine = RuleEngine()

    risk_level = engine.classify("C:/Settings/prefs.ini", 256)
    assert risk_level == RiskLevel.SUSPICIOUS


def test_safe_cache_files():
    """测试识别缓存文件为安全或可疑"""
    engine = RuleEngine()

    risk_level = engine.classify("C:/Users/test/Chrome/Cache", 1048576)
    # Cache 文件可能被识别为 SAFE 或 SUSPICIOUS，都不是 DANGEROUS
    assert risk_level in [RiskLevel.SAFE, RiskLevel.SUSPICIOUS]
    assert risk_level != RiskLevel.DANGEROUS


def test_safe_temp_files():
    """测试识别临时文件为安全"""
    engine = RuleEngine()

    risk_level = engine.classify("C:/Temp/temp123.tmp", 5120)
    assert risk_level == RiskLevel.SAFE


def test_dangerous_executables():
    """测试识别可执行文件为危险"""
    engine = RuleEngine()

    risk_level = engine.classify("C:/Windows/system32/notepad.exe", 20480)
    assert risk_level == RiskLevel.DANGEROUS


# ============================================================================
# 集成测试
# ============================================================================

def test_batch_evaluation_workflow():
    """测试批量评估完整流程"""
    engine = RuleEngine()

    # 创建测试数据
    paths = [
        "C:/Temp/safe_log.log",
        "C:/Users/test/AppData/suspicious_config.json",
        "C:/Windows/system32/danger_driver.sys",
    ]

    # 批量评估
    results = engine.evaluate_paths_batch(paths)

    # 验证结果
    assert len(results) == 3
    assert "C:/Temp/safe_log.log" in results
    assert "C:/Users/test/AppData/suspicious_config.json" in results
    assert "C:/Windows/system32/danger_driver.sys" in results

    # 验证风险等级
    assert results["C:/Windows/system32/danger_driver.sys"] == RiskLevel.DANGEROUS
    assert results["C:/Temp/safe_log.log"] in [RiskLevel.SAFE, RiskLevel.SUSPICIOUS]


def test_full_classify_with_descriptions():
    """测试获取完整分类结果和描述"""
    engine = RuleEngine()

    items = [
        ("C:/Temp/cache.tmp", 2048),
        ("C:/Users/test/app_data.db", 102400),
    ]

    descriptions = []
    for path, size in items:
        risk_level, desc = engine.classify_with_description(path, size)
        descriptions.append(desc)

    assert len(descriptions) == 2
    for desc in descriptions:
        assert len(desc) > 0


# ============================================================================
# 边界条件测试
# ============================================================================

def test_classify_batch_empty():
    """测试批量分类空列表"""
    engine = RuleEngine()

    results = engine.classify_batch([])

    assert results == []


def test_classify_batch_single():
    """测试批量分类单个项目"""
    engine = RuleEngine()

    results = engine.classify_batch([("C:/Temp/test.log", 1024)])

    assert len(results) == 1


def test_filter_by_risk_level_no_matches():
    """测试过滤无匹配结果"""
    engine = RuleEngine()

    safe_items = [
        ("C:/Temp/safe1.log", 1024),
        ("C:/Temp/safe2.tmp", 2048),
    ]

    # 过滤 DANGEROUS 级别（应该没有匹配）
    dangerous_items = engine.filter_by_risk_level(safe_items, RiskLevel.DANGEROUS)

    assert len(dangerous_items) == 0


def test_get_rule_engine_singleton():
    """测试全局规则引擎单例"""
    engine1 = get_rule_engine()
    engine2 = get_rule_engine()

    # 应该是同一个实例
    assert engine1 is engine2
