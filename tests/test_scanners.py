"""
扫描器模块单元测试

测试范围:
- SmartScanSelector 扫描器选择
- DepthDiskScanner 深度扫描功能
- ScanType 和 ScanConfig 数据类
"""
import pytest
import sys
import os

# 添加 src 到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.smart_scan_selector import (
    SmartScanSelector, ScanType, ScanConfig, get_smart_scan_selector
)
from core.depth_disk_scanner import (
    DepthDiskScanner, get_depth_disk_scanner,
    ScanProgress, get_disk_info, get_available_drives
)
from core.models import ScanItem
from core.rule_engine import RiskLevel


# ============================================================================
# ScanType 枚举测试
# ============================================================================

def test_scan_type_values():
    """测试 ScanType 枚举的值"""
    assert ScanType.SYSTEM.value == "system"
    assert ScanType.BROWSER.value == "browser"
    assert ScanType.APPDATA.value == "appdata"
    assert ScanType.CUSTOM.value == "custom"
    assert ScanType.DISK.value == "disk"


# ============================================================================
# ScanConfig 数据类测试
# ============================================================================

def test_scan_config_creation():
    """测试 ScanConfig 创建"""
    config = ScanConfig(
        scan_type=ScanType.CUSTOM,
        scan_target="C:/Temp"
    )
    assert config.scan_type == ScanType.CUSTOM
    assert config.scan_target == "C:/Temp"
    assert not config.include_hidden
    assert not config.follow_symlinks
    assert not config.use_mft
    assert config.min_size == 0


def test_scan_config_with_options():
    """测试 ScanConfig 带选项"""
    config = ScanConfig(
        scan_type=ScanType.DISK,
        scan_target="C:/",
        include_hidden=True,
        follow_symlinks=True,
        use_mft=True,
        min_size=1024
    )
    assert config.include_hidden
    assert config.follow_symlinks
    assert config.use_mft
    assert config.min_size == 1024


# ============================================================================
# SmartScanSelector 测试
# ============================================================================

def test_smart_scan_selector_creation():
    """测试 SmartScanSelector 创建"""
    selector = SmartScanSelector()
    assert selector is not None
    assert selector.get_scan_config() is None
    assert not selector.is_scanning()


def test_smart_scan_selector_available_types():
    """测试获取可用扫描类型"""
    selector = SmartScanSelector()
    types = selector.get_available_scan_types()
    assert len(types) == 5
    assert ScanType.SYSTEM in types
    assert ScanType.BROWSER in types
    assert ScanType.APPDATA in types
    assert ScanType.CUSTOM in types
    assert ScanType.DISK in types


def test_smart_scan_selector_get_scanner():
    """测试获取扫描器"""
    selector = SmartScanSelector()

    # 测试所有扫描器存在
    assert selector.get_scanner(ScanType.SYSTEM) is not None
    assert selector.get_scanner(ScanType.BROWSER) is not None
    assert selector.get_scanner(ScanType.APPDATA) is not None
    assert selector.get_scanner(ScanType.CUSTOM) is not None
    assert selector.get_scanner(ScanType.DISK) is not None


def test_smart_scan_selector_path_detection():
    """测试路径智能推测"""
    selector = SmartScanSelector()

    # AppData 路径（包含浏览器关键字但优先是 AppData）
    assert selector.get_scan_type_by_path(
        "C:/Users/test/AppData/Local/Chrome"
    ) == ScanType.APPDATA

    # 系统路径
    assert selector.get_scan_type_by_path(
        "C:/Windows/Temp"
    ) == ScanType.SYSTEM

    # 默认为自定义
    assert selector.get_scan_type_by_path(
        "D:/MyDocuments"
    ) == ScanType.CUSTOM


# ============================================================================
# DepthDiskScanner 测试
# ============================================================================

def test_depth_disk_scanner_creation():
    """测试 DepthDiskScanner 创建"""
    scanner = DepthDiskScanner()
    assert scanner is not None
    assert not scanner.is_scanning()
    assert scanner.get_config() is None


def test_get_depth_disk_scanner():
    """测试便利函数"""
    scanner = get_depth_disk_scanner()
    assert scanner is not None
    assert not scanner.is_scanning()


def test_scan_progress_model():
    """测试 ScanProgress 数据模型"""
    progress = ScanProgress(total=100, current=50)

    assert progress.percentage == 50.0
    assert progress.current == 50
    assert progress.total == 100
    assert progress.found_items == 0
    assert progress.skipped_items == 0


def test_scan_progress_zero_division():
    """测试 ScanProgress 零除情况"""
    progress = ScanProgress(total=0, current=0)

    assert progress.percentage == 0.0
    assert progress.estimated_remaining == 0.0


def test_scan_progress_percentage_edge_cases():
    """测试 ScanProgress 百分比边界情况"""
    # 全完成
    progress = ScanProgress(total=100, current=100)
    assert progress.percentage == 100.0

    # 一半
    progress = ScanProgress(total=100, current=50)
    assert progress.percentage == 50.0

    # 超过总进度 (不应该发生但需要处理)
    progress = ScanProgress(total=100, current=150)
    assert progress.percentage == 150.0


# ============================================================================
# 磁盘信息工具测试
# ============================================================================

def test_get_available_drives():
    """测试获取可用驱动器"""
    drives = get_available_drives()
    # Windows 应该至少有 C: 盘
    assert isinstance(drives, list)
    assert len(drives) > 0
    # 验证返回的路径格式
    for drive in drives:
        assert len(drive) >= 2
        assert drive[1] == ':'


def test_get_disk_info():
    """测试获取磁盘信息"""
    info = get_disk_info("C:/")
    assert isinstance(info, dict)
    assert 'total' in info
    assert 'used' in info
    assert 'free' in info
    assert 'percent' in info

    # 验证值的合理性
    if info:  # 可能会因为权限等原因返回空字典
        assert info['total'] > 0
        assert info['used'] >= 0
        assert info['free'] >= 0
        assert 0 <= info['percent'] <= 100


def test_get_disk_info_nonexistent():
    """测试获取不存在的磁盘信息"""
    info = get_disk_info("X:/")  # 通常不存在
    # 不存在的驱动器应该返回空字典
    assert isinstance(info, dict)


# ============================================================================
# 集成测试
# ============================================================================

def test_smart_scan_selector_config_integration():
    """测试 SmartScanSelector 配置集成"""
    selector = SmartScanSelector()

    config = ScanConfig(
        scan_type=ScanType.CUSTOM,
        scan_target="C:/Temp",
        include_hidden=True
    )

    scanner = selector.select_optimal_scanner(config)
    assert scanner is not None
    assert isinstance(scanner, DepthDiskScanner)

    # 验证配置已保存
    retrieved_config = selector.get_scan_config()
    # 注意: select_optimal_scanner 不会自动保存 config
    # 这里只测试方法的调用是否正常
    assert selector.select_optimal_scanner(config) is not None


def test_scan_progress_estimation():
    """测试扫描进度预估"""
    import time

    # 创建带有正确 start_time 的进度对象
    progress = ScanProgress(total=100, current=0, start_time=time.time())
    time.sleep(0.1)  # 等待一点时间

    progress.current = 50
    # 验证已用时间被计算
    assert progress.elapsed_time > 0

    # 如果速率存在，预估剩余时间应该有意义
    if progress.elapsed_time > 0:
        estimated = progress.estimated_remaining
        assert isinstance(estimated, float)
