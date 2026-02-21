"""
进度预估模块单元测试

测试范围:
- PreCheckResult 数据类
- ScanProgress 数据类
- ProgressEstimator 类
- 预检查功能
- 剩余时间估算
"""
import pytest
import sys
import os
import time

# 添加 src 到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.progress_estimator import (
    ProgressEstimator,
    ScanProgress,
    PreCheckResult,
    PreCheckStatus,
    get_progress_estimator,
    format_time
)


# ============================================================================
# PreCheckStatus 枚举测试
# ============================================================================

def test_pre_check_status_values():
    """测试 PreCheckStatus 枚举的值"""
    assert PreCheckStatus.PASSED.value == "passed"
    assert PreCheckStatus.WARNING.value == "warning"
    assert PreCheckStatus.FAILED.value == "failed"


# ============================================================================
# PreCheckResult 数据类测试
# ============================================================================

def test_pre_check_result_creation():
    """测试 PreCheckResult 创建"""
    result = PreCheckResult(
        status=PreCheckStatus.PASSED,
        message="检查通过"
    )
    assert result.status == PreCheckStatus.PASSED
    assert result.message == "检查通过"
    assert result.details == {}


def test_pre_check_result_with_details():
    """测试 PreCheckResult 带详细信息"""
    details = {'path': 'C:/Temp', 'free_mb': 1024}
    result = PreCheckResult(
        status=PreCheckStatus.WARNING,
        message="空间不足",
        details=details
    )
    assert result.status == PreCheckStatus.WARNING
    assert result.details == details


# ============================================================================
# ScanProgress 数据类测试
# ============================================================================

def test_scan_progress_creation():
    """测试 ScanProgress 创建"""
    progress = ScanProgress(total=100)
    assert progress.current == 0
    assert progress.total == 100
    assert progress.found_items == 0
    assert progress.skipped_items == 0


def test_scan_progress_percentage():
    """测试进度百分比计算"""
    progress = ScanProgress(total=100, current=50)
    assert progress.percentage == 50.0

    progress = ScanProgress(total=100, current=100)
    assert progress.percentage == 100.0

    progress = ScanProgress(total=200, current=50)
    assert progress.percentage == 25.0


def test_scan_progress_percentage_zero_total():
    """测试零总数的百分比"""
    progress = ScanProgress(total=0, current=0)
    assert progress.percentage == 0.0


def test_scan_progress_elapsed_time():
    """测试已用时间"""
    progress = ScanProgress(total=100, start_time=time.time() - 10)
    elapsed = progress.elapsed_time
    assert elapsed > 0
    assert elapsed < 15  # 允许一些误差


def test_scan_progress_elapsed_time_no_start():
    """测试无开始时间的已用时间"""
    progress = ScanProgress(total=100)
    assert progress.elapsed_time == 0.0


def test_scan_progress_estimated_remaining():
    """测试剩余时间估算"""
    progress = ScanProgress(
        total=100,
        current=50,
        start_time=time.time() - 10  # 10秒前开始
    )
    remaining = progress.estimated_remaining
    assert remaining > 0
    # 大约 10 秒剩余（因为 50/50% 已完成）
    assert remaining < 20  # 允许一些波动


def test_scan_progress_estimated_remaining_zero():
    """测试零进度的剩余时间"""
    progress = ScanProgress(total=100, current=0)
    assert progress.estimated_remaining == 0.0


def test_scan_progress_current_rate():
    """测试当前速率"""
    progress = ScanProgress(
        total=100,
        current=50,
        start_time=time.time() - 10  # 10秒前开始
    )
    rate = progress.current_rate
    assert rate > 0  # 每秒大约 5 个项目


def test_scan_progress_current_rate_zero():
    """测试零进度的速率"""
    progress = ScanProgress(total=100, current=0)
    assert progress.current_rate == 0.0


def test_scan_progress_update():
    """测试进度更新"""
    progress = ScanProgress(total=100)
    progress.update(50, "C:/Temp")
    assert progress.current == 50
    assert progress.current_path == "C:/Temp"


def test_scan_progress_to_dict():
    """测试转换为字典"""
    progress = ScanProgress(
        total=100,
        current=50,
        found_items=10,
        skipped_items=5
    )
    d = progress.to_dict()
    assert d['current'] == 50
    assert d['total'] == 100
    assert d['percentage'] == 50.0
    assert d['found_items'] == 10
    assert d['skipped_items'] == 5
    assert 'elapsed_time' in d


# ============================================================================
# ProgressEstimator 测试
# ============================================================================

def test_progress_estimator_creation():
    """测试 ProgressEstimator 创建"""
    estimator = ProgressEstimator()
    assert estimator is not None
    progress = estimator.get_progress()
    assert progress.current == 0
    assert progress.total == 0


def test_get_progress_estimator():
    """测试便利函数"""
    estimator = get_progress_estimator()
    assert estimator is not None


def test_start_scan():
    """测试开始扫描"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)

    progress = estimator.get_progress()
    assert progress.total == 100
    assert progress.start_time > 0
    assert progress.current == 0


def test_update_progress():
    """测试更新进度"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)
    estimator.update_progress(50, "C:/Temp")

    progress = estimator.get_progress()
    assert progress.current == 50
    assert progress.current_path == "C:/Temp"


def test_add_found_item():
    """测试增加发现的项目"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)
    estimator.add_found_item()
    estimator.add_found_item()

    progress = estimator.get_progress()
    assert progress.found_items == 2


def test_add_skipped_item():
    """测试增加跳过的项目"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)
    estimator.add_skipped_item()

    progress = estimator.get_progress()
    assert progress.skipped_items == 1


def test_is_scan_completed():
    """测试扫描完成检查"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)

    assert not estimator.is_scan_completed()

    estimator.update_progress(100)
    assert estimator.is_scan_completed()


def test_get_estimated_remaining_time():
    """测试预估剩余时间"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)
    estimator.update_progress(10)

    # 需要等待一点时间
    time.sleep(0.1)
    estimator.update_progress(20)

    remaining = estimator.get_estimated_remaining_time()
    assert remaining >= 0


def test_get_estimated_remaining_time_zero_progress():
    """测试零进度的剩余时间估算"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)

    remaining = estimator.get_estimated_remaining_time()
    assert remaining == 0.0


def test_get_progress_report():
    """测试获取进度报告"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)
    estimator.update_progress(50, "C:/Temp")

    report = estimator.get_progress_report()
    assert 'progress' in report
    assert 'estimated_remaining' in report
    assert 'summary' in report
    assert report['progress']['current'] == 50


# ============================================================================
# 预检查测试
# ============================================================================

def test_precheck_valid_path():
    """测试有效路径的预检查"""
    estimator = ProgressEstimator()
    passed, results = estimator.precheck_scan(
        "C:/",
        check_permissions=False,
        check_disk_space=False
    )
    assert passed is True
    assert len(results) > 0


def test_precheck_nonexistent_path():
    """测试不存在路径的预检查"""
    estimator = ProgressEstimator()
    passed, results = estimator.precheck_scan(
        "C:/this/path/does/not/exist",
        check_permissions=False,
        check_disk_space=False
    )

    # 应该失败，至少有一个检查失败
    has_failed = any(r.status == PreCheckStatus.FAILED for r in results)
    assert has_failed is True


def test_precheck_disk_space():
    """测试磁盘空间检查"""
    estimator = ProgressEstimator()
    passed, results = estimator.precheck_scan(
        "C:/",
        check_path_exists=False,
        check_permissions=False,
        check_disk_space=True
    )
    # 磁盘空间检查应该至少有结果
    assert len(results) > 0


# ============================================================================
# 便利函数测试
# ============================================================================

def test_format_time_seconds():
    """测试格式化秒"""
    assert format_time(0) == "0 秒"
    assert format_time(30) == "30 秒"
    assert format_time(59) == "59 秒"


def test_format_time_minutes():
    """测试格式化分钟"""
    assert format_time(60) == "1 分 0 秒"
    assert format_time(90) == "1 分 30 秒"
    assert format_time(300) == "5 分 0 秒"


def test_format_time_hours():
    """测试格式化小时"""
    assert format_time(3600) == "1 小时 0 分钟"
    assert format_time(3661) == "1 小时 1 分钟"
    assert format_time(7200) == "2 小时 0 分钟"


# ============================================================================
# 边界条件测试
# ============================================================================

def test_scan_progress_total_zero():
    """测试总数为零的进度"""
    progress = ScanProgress(total=0)
    assert progress.percentage == 0.0
    assert progress.current_rate == 0.0
    assert progress.estimated_remaining == 0.0


def test_scan_progress_current_greater_than_total():
    """测试当前数超过总数的进度"""
    progress = ScanProgress(total=100, current=150)
    assert progress.percentage == 150.0  # 允许超过 100%


def test_progress_estimator_summary():
    """测试生成摘要"""
    estimator = ProgressEstimator()
    estimator.start_scan(100)
    estimator.update_progress(50)

    report = estimator.get_progress_report()
    summary = report['summary']
    assert '进度' in summary
    assert '%' in summary
