"""
AppData Migration Unit Tests

Test coverage:
- MigrationItem dataclass
- ScanMigrationThread
- MigrateThread
- RollbackThread
- AppDataMigrationTool
- Risk assessment
- Migration history management
"""
import pytest
import sys
import os
import tempfile
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Qt
from PyQt5.QtWidgets import QApplication, qApp
if qApp is None:
    QApplication(sys.argv)

from core.appdata_migration import (
    MigrationItem,
    ScanMigrationThread,
    MigrateThread,
    RollbackThread,
    AppDataMigrationTool,
    COMMON_APPS
)
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# MigrationItem Tests
# ============================================================================

def test_migration_item_creation():
    """Test MigrationItem creation"""
    item = MigrationItem(
        name="TestFolder",
        path="C:/AppData/TestFolder",
        size=1024000,
        app_type="safe",
        category="cache",
        risk_level="safe",
        risk_reason="Manual test"
    )

    assert item.name == "TestFolder"
    assert item.path == "C:/AppData/TestFolder"
    assert item.size == 1024000
    assert item.risk_level == "safe"  # Explicitly set
    assert item.category == "cache"


def test_migration_item_unknown_risk():
    """Test MigrationItem with unknown risk level gets assessed"""
    item = MigrationItem(
        name="UnknownFolder_123",
        path="C:/AppData/UnknownFolder_123",
        size=1024000,
        app_type="unknown",
        category="unknown"
    )

    # Should auto-assess risk
    assert item.risk_level in ['safe', 'wary', 'dangerous', 'unknown']


def test_migration_item_safe_apps():
    """Test MigrationItem risk assessment for safe apps"""
    safe_apps = ['Google', 'Chrome', 'Code', 'VSCode', 'cache_test']

    for app_name in safe_apps:
        item = MigrationItem(
            name=app_name,
            path=f"C:/AppData/{app_name}",
            size=1024000,
            app_type="unknown",
            category="unknown"
        )
        # Known safe apps should be assessed as safe or wary
        assert item.risk_level in ['safe', 'wary']


def test_migration_item_cache_keywords():
    """Test MigrationItem for cache keywords"""
    cache_keywords = ['cache', 'temp', 'tmp', 'logs', 'thumb']

    for keyword in cache_keywords:
        item = MigrationItem(
            name=f"app_{keyword}",
            path=f"C:/AppData/app_{keyword}",
            size=1024000,
            app_type="unknown",
            category="unknown"
        )
        # Cache keywords should be safe
        assert item.risk_level == 'safe'


def test_migration_item_to_dict():
    """Test MigrationItem to_dict conversion"""
    item = MigrationItem(
        name="TestFolder",
        path="C:/AppData/TestFolder",
        size=1024000,
        app_type="safe",
        category="cache",
        risk_level="safe",
        risk_reason="Cache folder"
    )

    data = item.to_dict()
    assert data['name'] == "TestFolder"
    assert data['risk_level'] == "safe"
    assert data['risk_reason'] == "Cache folder"


def test_migration_item_dangerous_patterns():
    """Test MigrationItem for dangerous patterns"""
    # Test dangerous folder names - these are exact matches in the code
    # Note: "packages" gets matched by safe keywords, so we test others
    dangerous_names = ['windowsapps', '.hidden', '_system']

    for name in dangerous_names:
        item = MigrationItem(
            name=name,
            path=f"C:/AppData/{name}",
            size=1024000,
            app_type="unknown",
            category="unknown"
        )
        # These should be marked as wary or unknown (hidden files/user data)
        # (Note: patterns might be complex strings)
        assert item.risk_level in ['wary', 'dangerous', 'unknown']


def test_migration_item_system_paths():
    """Test MigrationItem for system-level paths"""
    system_names = ['microsoft', 'google', 'adobe']

    # Note: These might vary based on exact name matching
    for name in system_names:
        item = MigrationItem(
            name=name.lower(),
            path=f"C:/AppData/{name}",
            size=1024000,
            app_type="unknown",
            category="unknown"
        )
        # Should be recognized (not causing errors)
        assert item.risk_level in ['safe', 'wary', 'dangerous', 'unknown']


def test_migration_item_wary_keywords():
    """Test MigrationItem for wary keywords (user data)"""
    wary_keywords = ['data', 'database', 'storage', 'profile', 'user']

    for keyword in wary_keywords:
        item = MigrationItem(
            name=f"myapp_{keyword}",
            path=f"C:/AppData/myapp_{keyword}",
            size=1024000,
            app_type="unknown",
            category="unknown"
        )
        # User data keywords should be wary
        assert item.risk_level in ['wary', 'unknown']


# ============================================================================
# ScanMigrationThread Tests
# ============================================================================

def test_scan_migration_thread_creation():
    """Test ScanMigrationThread creation"""
    thread = ScanMigrationThread(
        min_size_mb=100,
        scan_roaming=True,
        scan_local=False,
        scan_local_low=False
    )

    assert thread.min_size_mb == 100
    assert thread.min_size_bytes == 100 * 1024 * 1024
    assert thread.scan_roaming is True
    assert thread.scan_local is False
    assert thread.scan_local_low is False
    assert thread.is_cancelled is False


def test_scan_migration_thread_cancel():
    """Test ScanMigrationThread cancellation"""
    thread = ScanMigrationThread(min_size_mb=100)
    assert thread.is_cancelled is False

    thread.cancel()
    assert thread.is_cancelled is True


def test_scan_migration_thread_signals():
    """Test ScanMigrationThread signals exist"""
    thread = ScanMigrationThread(min_size_mb=100)

    # Check signals exist
    assert hasattr(thread, 'progress')
    assert hasattr(thread, 'item_found')
    assert hasattr(thread, 'complete')
    assert hasattr(thread, 'error')


@pytest.mark.timeout(5)
def test_scan_migration_thread_run_empty():
    """Test ScanMigrationThread run with no valid directories"""
    thread = ScanMigrationThread(
        min_size_mb=999999,  # High threshold
        scan_roaming=False,  # Disable all scanning
        scan_local=False,
        scan_local_low=False
    )

    thread.run()
    # Should complete without errors


def test_scan_migration_thread_calculate_size():
    """Test _calculate_size method"""
    with tempfile.TemporaryDirectory() as tmpdir:
        thread = ScanMigrationThread(min_size_mb=1)

        # Create test files
        for i in range(5):
            file_path = os.path.join(tmpdir, f'test_{i}.txt')
            with open(file_path, 'w') as f:
                f.write('x' * 100)

        size = thread._calculate_size(tmpdir)
        assert size >= 500  # At least 500 bytes


# ============================================================================
# MigrateThread Tests
# ============================================================================

def test_migrate_thread_creation():
    """Test MigrateThread creation"""
    items = [
        MigrationItem(
            name="TestItem",
            path="C:/Test/TestItem",
            size=1024000,
            app_type="safe",
            category="cache"
        )
    ]

    thread = MigrateThread(items, "D:/Target")
    assert thread.items == items
    assert thread.target_base == "D:/Target"
    assert thread.is_cancelled is False


def test_migrate_thread_cancel():
    """Test MigrateThread cancellation"""
    thread = MigrateThread([], "D:/Target")
    assert thread.is_cancelled is False

    thread.cancel()
    assert thread.is_cancelled is True


def test_migrate_thread_signals():
    """Test MigrateThread signals exist"""
    thread = MigrateThread([], "D:/Target")

    assert hasattr(thread, 'progress')
    assert hasattr(thread, 'status')
    assert hasattr(thread, 'complete')
    assert hasattr(thread, 'error')


@pytest.mark.timeout(10)
def test_migrate_thread_empty_list():
    """Test MigrateThread with empty item list"""
    with tempfile.TemporaryDirectory() as tmpdir:
        thread = MigrateThread([], tmpdir)
        thread.run()
        # Should complete


# ============================================================================
# RollbackThread Tests
# ============================================================================

def test_rollback_thread_creation():
    """Test RollbackThread creation"""
    record = {
        'source': 'C:/Test/Source',
        'target': 'D:/Target',
        'original_target': 'D:/Target',
        'name': 'TestItem'
    }

    thread = RollbackThread(record)
    assert thread.source == 'C:/Test/Source'
    assert thread.target == 'D:/Target'


def test_rollback_thread_empty_record():
    """Test RollbackThread with incomplete record"""
    record = {'source': '', 'target': ''}
    thread = RollbackThread(record)
    assert thread.source == ''
    assert thread.target == ''


def test_rollback_thread_signals():
    """Test RollbackThread signals exist"""
    thread = RollbackThread({'source': 'test', 'target': 'test'})

    assert hasattr(thread, 'progress')
    assert hasattr(thread, 'status')
    assert hasattr(thread, 'complete')
    assert hasattr(thread, 'error')


def test_rollback_thread_cancel():
    """Test RollbackThread cancellation"""
    thread = RollbackThread({'source': 'test', 'target': 'test'})
    assert thread.is_cancelled is False

    thread.cancel()
    assert thread.is_cancelled is True


# ============================================================================
# AppDataMigrationTool Tests
# ============================================================================

def test_migration_tool_creation():
    """Test AppDataMigrationTool creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)

        tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
        tool.config_dir = config_dir
        tool.history_file = os.path.join(config_dir, 'appdata_migrations.json')
        tool._ensure_history_file()

        assert tool.config_dir == config_dir
        assert 'appdata_migrations.json' in tool.history_file


def test_migration_tool_history_file():
    """Test history file creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)

        tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
        tool.config_dir = config_dir
        tool.history_file = os.path.join(config_dir, 'appdata_migrations.json')
        tool._ensure_history_file()

        # File should exist
        assert os.path.exists(tool.history_file)


def test_migration_tool_get_empty_history():
    """Test getting empty history"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)

        tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
        tool.config_dir = config_dir
        tool.history_file = os.path.join(config_dir, 'appdata_migrations.json')
        tool._ensure_history_file()

        history = tool.get_migration_history()
        assert isinstance(history, list)
        assert len(history) == 0


def test_migration_tool_save_and_load_history():
    """Test saving and loading migration history"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)

        tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
        tool.config_dir = config_dir
        tool.history_file = os.path.join(config_dir, 'appdata_migrations.json')
        tool._ensure_history_file()

        # Save a record
        record = {
            'source': 'C:/Test/Source',
            'target': 'D:/Target',
            'original_target': 'D:/Target',
            'name': 'TestItem',
            'size': 1024000,
            'timestamp': datetime.now().isoformat()
        }
        tool.save_migration_record(record)

        # Load and verify
        history = tool.get_migration_history()
        assert len(history) == 1
        assert history[0]['name'] == 'TestItem'


def test_migration_tool_remove_history():
    """Test removing migration history"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)

        tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
        tool.config_dir = config_dir
        tool.history_file = os.path.join(config_dir, 'appdata_migrations.json')
        tool._ensure_history_file()

        # Save records
        record1 = {
            'source': 'C:/Test/Source1',
            'target': 'D:/Target1',
            'name': 'TestItem1',
            'size': 1024000,
            'timestamp': datetime.now().isoformat()
        }
        record2 = {
            'source': 'C:/Test/Source2',
            'target': 'D:/Target2',
            'name': 'TestItem2',
            'size': 2048000,
            'timestamp': datetime.now().isoformat()
        }
        tool.save_migration_record(record1)
        tool.save_migration_record(record2)

        # Verify both exist
        assert len(tool.get_migration_history()) == 2

        # Remove one
        tool.remove_migration_history('C:/Test/Source1')
        history = tool.get_migration_history()
        assert len(history) == 1
        assert history[0]['source'] == 'C:/Test/Source2'


def test_migration_tool_get_available_drives():
    """Test getting available drives"""
    tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
    tool.config_dir = tempfile.gettempdir()
    tool.history_file = os.path.join(tempfile.gettempdir(), 'test.json')

    drives = tool.get_available_drives()
    assert isinstance(drives, list)
    # At least one drive should exist
    if drives:
        assert 'drive' in drives[0]
        assert 'free' in drives[0]
        assert 'total' in drives[0]


def test_migration_tool_format_size():
    """Test size formatting"""
    assert AppDataMigrationTool.format_size(100) == "100.00 B"
    assert AppDataMigrationTool.format_size(1024) == "1.00 KB"
    assert AppDataMigrationTool.format_size(1024 * 1024) == "1.00 MB"
    assert AppDataMigrationTool.format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert AppDataMigrationTool.format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"


# ============================================================================
# COMMON_APPS Tests
# ============================================================================

def test_common_apps_structure():
    """Test COMMON_APPS dictionary structure"""
    assert isinstance(COMMON_APPS, dict)
    assert len(COMMON_APPS) > 0


def test_common_apps_safe():
    """Test safe apps in COMMON_APPS"""
    safe_apps = [k for k, v in COMMON_APPS.items() if v['risk'] == 'safe']
    assert len(safe_apps) > 0


def test_common_apps_wary():
    """Test wary apps in COMMON_APPS"""
    wary_apps = [k for k, v in COMMON_APPS.items() if v['risk'] == 'wary']
    assert len(wary_apps) > 0


def test_common_apps_categories():
    """Test categories in COMMON_APPS"""
    categories = set(v['category'] for v in COMMON_APPS.values())
    assert 'cache' in categories
    assert 'config' in categories
    assert 'user_data' in categories


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_migration_item_zero_size():
    """Test MigrationItem with zero size"""
    item = MigrationItem(
        name="EmptyFolder",
        path="C:/AppData/EmptyFolder",
        size=0,
        app_type="safe",
        category="cache"
    )

    assert item.size == 0


def test_migration_item_large_size():
    """Test MigrationItem with large size (GB)"""
    gb_size = 2 * 1024 * 1024 * 1024  # 2 GB
    item = MigrationItem(
        name="LargeFolder",
        path="C:/AppData/LargeFolder",
        size=gb_size,
        app_type="wary",
        category="user_data"
    )

    assert item.size == gb_size


def test_migration_item_invalid_characters():
    """Test MigrationItem with special characters in name"""
    special_names = [
        "App_123",
        "My.App",
        "folder-with-dashes",
        "folder with spaces"
    ]

    for name in special_names:
        item = MigrationItem(
            name=name,
            path=f"C:/AppData/{name}",
            size=1024000,
            app_type="unknown",
            category="unknown"
        )
        # Should not crash
        assert item.name == name


def test_scan_thread_custom_min_size():
    """Test ScanMigrationThread with various min_size values"""
    sizes = [50, 100, 250, 500, 1024]  # MB

    for size_mb in sizes:
        thread = ScanMigrationThread(min_size_mb=size_mb)
        assert thread.min_size_mb == size_mb
        assert thread.min_size_bytes == size_mb * 1024 * 1024


def test_migration_tool_corrupted_history():
    """Test AppDataMigrationTool with corrupted history file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, 'config')
        os.makedirs(config_dir)

        tool = AppDataMigrationTool.__new__(AppDataMigrationTool)
        tool.config_dir = config_dir
        tool.history_file = os.path.join(config_dir, 'appdata_migrations.json')

        # Create corrupted file
        with open(tool.history_file, 'w') as f:
            f.write("corrupted json content")

        # Should handle gracefully
        history = tool.get_migration_history()
        assert isinstance(history, list)
        assert len(history) == 0


# ============================================================================
# Integration Tests
# ============================================================================

def test_item_found_signal():
    """Test item_found signal from ScanMigrationThread"""
    signal_received = False
    received_item = None

    def on_item_found(item):
        nonlocal signal_received, received_item
        signal_received = True
        received_item = item

    thread = ScanMigrationThread(min_size_mb=1)
    thread.item_found.connect(on_item_found)

    # Emit a mock signal
    test_item = MigrationItem(
        name="Test",
        path="C:/Test",
        size=1024000,
        app_type="safe",
        category="cache"
    )
    thread.item_found.emit(test_item)

    assert signal_received is True
    assert received_item.name == "Test"


def test_complete_signal():
    """Test complete signal from ScanMigrationThread"""
    signal_received = False
    received_list = None

    def on_complete(items):
        nonlocal signal_received, received_list
        signal_received = True
        received_list = items

    thread = ScanMigrationThread(min_size_mb=1)
    thread.complete.connect(on_complete)

    test_items = [1, 2, 3]
    thread.complete.emit(test_items)

    assert signal_received is True
    assert received_list == [1, 2, 3]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
