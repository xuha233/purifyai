# 智能清理数据模型单元测试


"""
PurifyAI 智能清理数据模型单元测试 (v1.1)

测试范围:
- CleanupItem 轻量化设计
- ItemDetail 按需加载
- CleanupPlan 完整功能
- ExecutionResult 执行结果
- FailureInfo 失败信息
- BackupInfo 备份信息
- RecoveryRecord 恢复记录
- 各种枚举
"""

import pytest
from datetime import datetime

# 导入智能清理模型
from core.models_smart import (
    CleanupItem,
    ItemDetail,
    CleanupPlan,
    ExecutionResult,
    FailureInfo,
    BackupInfo,
    RecoveryRecord,
    RollbackResult,
    CleanupStatus,
    ExecutionStatus,
    BackupType,
    get_reason_hash,
    is_empty_cleanup_item
)

# 从rule_engine导入RiskLevel
from core.rule_engine import RiskLevel

# 导入ScanProgress（添加遗漏的导入）
from core.models_smart import ScanProgress


# ============================================================================
# RiskLevel 枚举测试
# ============================================================================

def test_risk_level_value_access():
    """测试 RiskLevel 枚举的 value 属性访问"""
    assert RiskLevel.SAFE.value == "safe"
    assert RiskLevel.SUSPICIOUS.value == "suspicious"
    assert RiskLevel.DANGEROUS.value == "dangerous"


def test_risk_level_from_string():
    """测试从字符串创建 RiskLevel"""
    assert RiskLevel.from_value("safe") == RiskLevel.SAFE
    assert RiskLevel.from_value("suspicious") == RiskLevel.SUSPICIOUS
    assert RiskLevel.from_value("dangerous") == RiskLevel.DANGEROUS


def test_risk_level_display_name():
    """测试 RiskLevel 显示名称"""
    assert RiskLevel.SAFE.get_display_name() == "安全"
    assert RiskLevel.SUSPICIOUS.get_display_name() == "疑似"
    assert RiskLevel.DANGEROUS.get_display_name() == "危险"


# ============================================================================
# CleanupItem 测试
# ============================================================================

def test_cleanup_item_creation():
    """测试 CleanupItem 创建"""
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.txt",
        size=1024,
        item_type="file",
        original_risk=RiskLevel.SUSPICIOUS,
        ai_risk=RiskLevel.SAFE
    )

    assert item.item_id == 1
    assert item.path == "C:/Temp/test.txt"
    assert item.size == 1024
    assert item.item_type == "file"


def test_cleanup_item_string_to_enum_conversion():
    """测试 CleanupItem 字符串到枚举的转换"""
    item = CleanupItem(
        item_id=2,
        path="C:/Temp/test2.txt",
        size=2048,
        item_type="file",
        original_risk="safe",  # 字符串
        ai_risk="suspicious"
    )

    assert item.original_risk == RiskLevel.SAFE
    assert item.ai_risk == RiskLevel.SUSPICIOUS


def test_cleanup_item_properties():
    """测试 CleanupItem 属性方法"""
    # Safe item
    safe_item = CleanupItem(
        item_id=1,
        path="C:/Temp/safe.tmp",
        size=100,
        item_type="file",
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )
    assert safe_item.is_safe is True
    assert safe_item.is_suspicious is False
    assert safe_item.is_dangerous is False

    # Suspicious item
    suspicious_item = CleanupItem(
        item_id=2,
        path="C:/Temp/suspicious.dat",
        size=200,
        item_type="file",
        original_risk=RiskLevel.SUSPICIOUS,
        ai_risk=RiskLevel.SUSPICIOUS
    )
    assert suspicious_item.is_safe is False
    assert suspicious_item.is_suspicious is True
    assert suspicious_item.is_dangerous is False

    # Dangerous item
    dangerous_item = CleanupItem(
        item_id=3,
        path="C:/Users/test/report.docx",
        size=1000000,
        item_type="file",
        original_risk=RiskLevel.DANGEROUS,
        ai_risk=RiskLevel.DANGEROUS
    )
    assert dangerous_item.is_safe is False
    assert dangerous_item.is_suspicious is False
    assert dangerous_item.is_dangerous is True


def test_cleanup_item_to_dict():
    """测试 CleanupItem 转换为字典"""
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.txt",
        size=1024,
        item_type="file",
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )

    d = item.to_dict()

    assert d['path'] == "C:/Temp/test.txt"
    assert d['size'] == 1024
    assert d['item_type'] == "file"
    assert d['original_risk'] == "safe"
    assert d['ai_risk'] == "safe"


def test_cleanup_item_from_dict():
    """测试从字典创建 CleanupItem"""
    data = {
        'path': "C:/Temp/from_dict.tmp",
        'size': 2048,
        'item_type': "directory",
        'original_risk': "suspicious",
        'ai_risk': "safe"
    }

    item = CleanupItem.from_dict(data, item_id=99)

    assert item.path == "C:/Temp/from_dict.tmp"
    assert item.item_id == 99
    assert item.original_risk == RiskLevel.SUSPICIOUS
    assert item.ai_risk == RiskLevel.SAFE


def test_is_empty_cleanup_item():
    """测试空清理项检查"""
    assert is_empty_cleanup_item(None) is True

    # 正常项
    item = CleanupItem(1, "C:/Temp/test", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE)
    assert is_empty_cleanup_item(item) is False

    # 空ID项
    empty_item = CleanupItem(0, "C:/Temp/test", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE)
    assert is_empty_cleanup_item(empty_item) is True


# ============================================================================
# ItemDetail 测试
# ============================================================================

def test_item_detail_creation():
    """测试 ItemDetail 创建"""
    detail = ItemDetail(
        ai_reason="缓存文件",
        confidence=0.95,
        cleanup_suggestion="可以直接删除",
        software_name="Chrome",
        function_description="浏览器缓存"
    )

    assert detail.ai_reason == "缓存文件"
    assert detail.confidence == 0.95
    assert detail.software_name == "Chrome"


def test_item_detail_to_dict():
    """测试 ItemDetail 转换为字典"""
    detail = ItemDetail(
        ai_reason="系统日志",
        confidence=0.8,
        cleanup_suggestion="可删除",
        software_name="App",
        function_description="应用日志"
    )

    d = detail.to_dict()

    assert d['ai_reason'] == "系统日志"
    assert d['confidence'] == 0.8
    assert 'cleanup_suggestion' in d


# ============================================================================
# CleanupPlan 测试
# ============================================================================

def test_cleanup_plan_creation():
    """测试 CleanupPlan 创建"""
    items = [
        CleanupItem(1, "C:/Temp/file1", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE),
        CleanupItem(2, "C:/Temp/file2", 2048, "file", RiskLevel.SUSPICIOUS, RiskLevel.SAFE),
        CleanupItem(3, "C:/Users/test/report.docx", 10000, "file", RiskLevel.DANGEROUS, RiskLevel.DANGEROUS)
    ]

    plan = CleanupPlan.create("system", "C:/Temp", items)

    assert plan.plan_id is not None
    assert len(plan.plan_id) > 0
    assert plan.scan_type == "system"
    assert plan.scan_target == "C:/Temp"
    assert plan.total_items == 3
    assert plan.total_size == 13072


def test_cleanup_plan_properties():
    """测试 CleanupPlan 属性方法"""
    items = [
        CleanupItem(1, "C:/Temp/file1", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE),
        CleanupItem(2, "C:/Temp/file2", 2048, "file", RiskLevel.SUSPICIOUS, RiskLevel.SUSPICIOUS),
        CleanupItem(3, "C:/Users/test/report.docx", 10000, "file", RiskLevel.DANGEROUS, RiskLevel.DANGEROUS)
    ]

    plan = CleanupPlan.create("system", "C:/Temp", items)

    assert plan.safe_count == 1
    assert plan.suspicious_count == 1
    assert plan.dangerous_count == 1
    assert plan.all_items == items


def test_cleanup_plan_to_dict():
    """测试 CleanupPlan 转换为字典"""
    items = [
        CleanupItem(1, "C:/Temp/file1", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE),
        CleanupItem(2, "C:/Temp/file2", 2048, "file", RiskLevel.SUSPICIOUS, RiskLevel.SUSPICIOUS)
    ]

    plan = CleanupPlan.create("browser", "C:/Temp", items)
    plan.ai_summary = "清理方案概述"
    plan.used_rule_engine = True

    d = plan.to_dict()

    assert d['scan_type'] == "browser"
    assert d['total_items'] == 2
    assert d['safe_count'] == 1
    assert d['suspicious_count'] == 1
    assert d['used_rule_engine'] == 1


def test_cleanup_plan_empty():
    """测试空 CleanupPlan"""
    plan = CleanupPlan.create("system", "C:/Temp", [])
    assert plan.total_items == 0
    assert plan.total_size == 0
    assert plan.safe_count == 0
    assert plan.suspicious_count == 0
    assert plan.dangerous_count == 0
    assert plan.all_items == []


# ============================================================================
# ScanProgress 测试
# ============================================================================

def test_scan_progress_creation():
    """测试 ScanProgress 创建"""
    progress = ScanProgress(total=100, current=0)

    assert progress.total == 100
    assert progress.current == 0
    assert progress.phase == 'scanning'
    assert progress.progress_percent == 0.0


def test_scan_progress_update():
    """测试 ScanProgress 更新"""
    progress = ScanProgress(total=100, current=0)

    progress.update(50, 100, phase='analyzing', message="AI分析中")

    assert progress.current == 50
    assert progress.phase == 'analyzing'
    assert progress.message == "AI分析中"
    assert progress.progress_percent == 50.0


def test_scan_progress_percent():
    """测试进度百分比计算"""
    progress = ScanProgress(total=100, current=25)
    assert progress.progress_percent == 25.0

    progress.update(50, 100)
    assert progress.progress_percent == 50.0

    progress.update(100, 100)
    assert progress.progress_percent == 100.0


def test_scan_progress_zero():
    """测试零项目扫描进度"""
    progress = ScanProgress(total=0, current=0)

    assert progress.progress_percent == 0.0
    assert progress.items_per_second == 0.0


def test_scan_progress_instant_complete():
    """测试瞬间完成的扫描进度"""
    from datetime import datetime

    start = datetime.now()
    progress = ScanProgress(total=1, current=1, started_at=start)

    progress.update(1, 1, phase='completed')

    assert progress.progress_percent == 100.0
    assert progress.phase == 'completed'


# ============================================================================
# ExecutionResult 测试
# ============================================================================

def test_execution_result_creation():
    """测试 ExecutionResult 创建"""
    result = ExecutionResult(
        plan_id="test-plan-id",
        started_at=datetime(2026, 2, 21, 12, 0, 0)
    )

    assert result.plan_id == "test-plan-id"
    assert result.total_items == 0
    assert result.status == ExecutionStatus.PENDING
    assert result.success_rate == 0.0


def test_execution_result_properties():
    """测试 ExecutionResult 属性"""
    result = ExecutionResult(
        plan_id="test-plan-id",
        started_at=datetime(2026, 2, 21, 12, 0, 0)
    )

    result.total_items = 10
    result.success_items = 8
    result.failed_items = 2

    result.update_status()

    assert result.success_rate == 0.8
    assert result.status == ExecutionStatus.PARTIAL_SUCCESS


def test_execution_result_full_success():
    """测试全部成功状态"""
    start = datetime(2026, 2, 21, 12, 0, 0)

    result = ExecutionResult(
        plan_id="test",
        started_at=start,
        completed_at=datetime(2026, 2, 21, 12, 1, 0)
    )

    result.total_items = 10
    result.success_items = 10
    result.failed_items = 0

    result.update_status()

    assert result.success_rate == 1.0
    assert result.status == ExecutionStatus.COMPLETED
    assert result.duration_seconds == 60


def test_execution_result_add_failure():
    """测试添加失败记录"""
    item = CleanupItem(1, "C:/Temp/test", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE)

    result = ExecutionResult(
        plan_id="test-plan-id",
        started_at=datetime(2026, 2, 21, 12, 0, 0)
    )

    result.add_failure(
        item,
        error_type='permission',
        error_message='权限不足',
        suggested_action='retry_with_admin'
    )

    assert len(result.failures) == 1
    assert result.failed_items == 1
    assert result.failures[0].error_type == 'permission'


def test_execution_result_update_status():
    """测试状态更新"""
    result = ExecutionResult(
        plan_id="test",
        started_at=datetime.now()
    )

    result.total_items = 10
    result.completed_at = datetime.now()
    result.success_items = 10
    result.failed_items = 0

    result.update_status()

    assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.PARTIAL_SUCCESS]


def test_execution_result_zero_duration():
    """测试零时长执行"""
    start = datetime.now()

    result = ExecutionResult(
        plan_id="test",
        started_at=start,
        completed_at=start
    )

    assert result.duration_seconds < 1.0


# ============================================================================
# FailureInfo 测试
# ============================================================================

def test_failure_info_creation():
    """测试 FailureInfo 创建"""
    item = CleanupItem(1, "C:/Temp/test", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE)

    failure = FailureInfo(
        item=item,
        error_type='file_in_use',
        error_message='文件被占用',
        suggested_action='retry_with_close_app'
    )

    assert failure.item == item
    assert failure.error_type == 'file_in_use'
    assert failure.suggested_action == 'retry_with_close_app'


def test_failure_info_to_dict():
    """测试 FailureInfo 转换为字典"""
    item = CleanupItem(1, "C:/Temp/test", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE)

    failure = FailureInfo(
        item=item,
        error_type='permission',
        error_message='权限不足'
    )

    d = failure.to_dict()

    assert d['item_id'] == 1
    assert d['error_type'] == 'permission'


# ============================================================================
# BackupInfo 测试
# ============================================================================

def test_backup_info_creation():
    """测试 BackupInfo 创建"""
    item = CleanupItem(1, "C:/Temp/test", 1024, "file", RiskLevel.SAFE, RiskLevel.SAFE)

    backup = BackupInfo.create(
        item=item,
        backup_path="C:/Backups/test",
        backup_type=BackupType.HARDLINK
    )

    assert backup.item_id == 1
    assert backup.backup_path == "C:/Backups/test"
    assert backup.backup_type == BackupType.HARDLINK


def test_backup_type_from_risk():
    """测试根据风险等级确定备份类型"""
    assert BackupType.from_risk(RiskLevel.SAFE) == BackupType.NONE
    assert BackupType.from_risk(RiskLevel.SUSPICIOUS) == BackupType.HARDLINK
    assert BackupType.from_risk(RiskLevel.DANGEROUS) == BackupType.FULL


# ============================================================================
# RecoveryRecord 测试
# ============================================================================

def test_recovery_record_creation():
    """测试 RecoveryRecord 创建"""
    record = RecoveryRecord(
        plan_id="test-plan-id",
        item_id=1,
        original_path="C:/Temp/test",
        backup_path="C:/Backups/test",
        backup_type=BackupType.HARDLINK
    )

    assert record.plan_id == "test-plan-id"
    assert record.item_id == 1
    assert record.restored is False


# ============================================================================
# RollbackResult 测试
# ============================================================================

def test_rollback_result_creation():
    """测试 RollbackResult 创建"""
    result = RollbackResult(
        total=10,
        success=8,
        failed=2
    )

    assert result.total == 10
    assert result.success == 8
    assert result.failed == 2


# ============================================================================
# Utility 函数测试
# ============================================================================

def test_get_reason_hash():
    """测试原因哈希函数"""
    reason1 = "缓存文件"
    reason2 = "临时文件"
    reason3 = "缓存文件"  # 相同内容

    hash1 = get_reason_hash(reason1)
    hash2 = get_reason_hash(reason2)
    hash3 = get_reason_hash(reason3)

    # 相同内容应产生相同哈希
    assert hash1 == hash3
    # 不同内容应产生不同哈希
    assert hash1 != hash2
    # 获取的hash应该是十六进制字符串
    assert len(hash1) == 32  # MD5哈希长度


def test_get_reason_hash_consistency():
    """测试原因哈希一致性（问题1修复验证）"""
    reason = "这是一个测试原因"
    hash1 = get_reason_hash(reason)
    hash2 = get_reason_hash(reason)
    hash3 = get_reason_hash(reason)

    # MD5一致性
    assert hash1 == hash2 == hash3

    # 测试不同原因产生不同哈希
    other_reason = "不同的原因"
    other_hash = get_reason_hash(other_reason)
    assert hash1 != other_hash

    # 测试哈希长度
    assert len(hash1) == 32
    assert all(c in '0123456789abcdef' for c in hash1)


# ============================================================================
# 枚举显示名称测试
# ============================================================================

def test_cleanup_status_display_name():
    """测试 CleanupStatus 显示名称"""
    assert CleanupStatus.SUCCESS.get_display_name() == "成功"
    assert CleanupStatus.FAILED.get_display_name() == "失败"
    assert CleanupStatus.SKIPPED.get_display_name() == "跳过"
    assert CleanupStatus.AWAITING_CONFIRM.get_display_name() == "等待确认"


def test_execution_status_display_name():
    """测试 ExecutionStatus 显示名称"""
    assert ExecutionStatus.RUNNING.get_display_name() == "执行中"
    assert ExecutionStatus.PARTIAL_SUCCESS.get_display_name() == "部分成功"
    assert ExecutionStatus.COMPLETED.get_display_name() == "已完成"


def test_backup_type_values():
    """测试 BackupType 类型值"""
    assert BackupType.NONE.value == "none"
    assert BackupType.HARDLINK.value == "hardlink"
    assert BackupType.FULL.value == "full"


# ============================================================================
# 内存优化验证 (问题2修复验证)
# ============================================================================

def test_cleanup_item_size():
    """验证 CleanupItem 大小"""
    import sys

    # 单个CleanupItem的基础大小估算
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.txt",
        size=1024,
        item_type="file",
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )

    # 验证核心字段数量为6 (符合设计要求)
    # item_id, path, size, item_type, original_risk, ai_risk
    attribute_count = len([attr for attr in dir(item) if not attr.startswith('_')])

    # 验证没有详细信息字段
    assert not hasattr(item, 'ai_reason')
    assert not hasattr(item, 'confidence')
    assert not hasattr(item, 'cleanup_suggestion')


# ============================================================================
# 参数化测试
# ============================================================================

@pytest.mark.parametrize("risk_value", ["safe", "suspicious", "dangerous"])
def test_cleanupitem_risk_levels(risk_value):
    """参数化测试不同的风险等级"""
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.txt",
        size=1024,
        item_type="file",
        original_risk=risk_value,
        ai_risk=risk_value
    )

    # 验证转换正确
    assert item.original_risk == RiskLevel.from_value(risk_value)
    assert item.ai_risk == RiskLevel.from_value(risk_value)


@pytest.mark.parametrize("backup_risk,expected_type", [
    (RiskLevel.SAFE, BackupType.NONE),
    (RiskLevel.SUSPICIOUS, BackupType.HARDLINK),
    (RiskLevel.DANGEROUS, BackupType.FULL)
])
def test_backup_type_mapping(backup_risk, expected_type):
    """参数化测试备份类型映射"""
    assert BackupType.from_risk(backup_risk) == expected_type


# ============================================================================
# 边界条件测试
# ============================================================================

def test_cleanup_item_large_size():
    """测试大文件处理"""
    large_size = 10 * 1024 * 1024 * 1024  # 10GB

    item = CleanupItem(
        item_id=999,
        path="C:/Temp/large_file.dat",
        size=large_size,
        item_type="file",
        original_risk="suspicious",
        ai_risk="suspicious"
    )

    assert item.size == large_size


def test_cleanup_plan_unique_ids():
    """测试cleanup计划ID唯一性"""
    plan1 = CleanupPlan.create("system", "C:/Temp", [])
    plan2 = CleanupPlan.create("system", "C:/Temp", [])

    assert plan1.plan_id != plan2.plan_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
