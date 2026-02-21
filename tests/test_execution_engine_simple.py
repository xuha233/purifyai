"""
Execution Engine Unit Tests - Simplified for reliability

Test coverage:
- SmartCleanupExecutor class
- ExecutionThread class
- ExecutionConfig dataclass
- ExecutionPhase enum
- ErrorType enum
- RetryStrategy enum
- Plan execution workflow
- Direct thread execution (no Qt signal dependency)
"""
import pytest
import sys
import os
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Qt - import after path setup
from PyQt5.QtWidgets import QApplication

# Ensure QApplication exists (qApp is a function call)
from PyQt5.QtWidgets import qApp
if qApp is None:
    QApplication(sys.argv)

from core.execution_engine import (
    ExecutionThread,
    ExecutionConfig,
    ExecutionPhase,
    ErrorType,
    RetryStrategy
)
from core.models_smart import (
    CleanupPlan, CleanupItem, CleanupStatus, ExecutionStatus,
    ExecutionResult, FailureInfo
)
from core.backup_manager import BackupManager, BackupType
from core.rule_engine import RiskLevel


# ============================================================================
# Enums Tests
# ============================================================================

def test_execution_phase_enum():
    """Test ExecutionPhase enum"""
    assert ExecutionPhase.PREPARING.value == "preparing"
    assert ExecutionPhase.BACKING_UP.value == "backing_up"
    assert ExecutionPhase.DELETING.value == "deleting"
    assert ExecutionPhase.RECORDING.value == "recording"
    assert ExecutionPhase.FINALIZING.value == "finalizing"


def test_error_type_enum():
    """Test ErrorType enum"""
    assert ErrorType.PERMISSION_DENIED.value == "permission_denied"
    assert ErrorType.FILE_IN_USE.value == "file_in_use"
    assert ErrorType.FILE_NOT_FOUND.value == "file_not_found"
    assert ErrorType.DISK_FULL.value == "disk_full"
    assert ErrorType.BACKUP_FAILED.value == "backup_failed"
    assert ErrorType.DELETE_FAILED.value == "delete_failed"
    assert ErrorType.UNKNOWN.value == "unknown"


def test_retry_strategy_enum():
    """Test RetryStrategy enum"""
    assert RetryStrategy.NO_RETRY.value == "no_retry"
    assert RetryStrategy.IMMEDIATE_RETRY.value == "immediate_retry"
    assert RetryStrategy.DELAYED_RETRY.value == "delayed_retry"
    assert RetryStrategy.SKIP.value == "skip"


# ============================================================================
# ExecutionConfig Tests
# ============================================================================

def test_execution_config_default():
    """Test default ExecutionConfig"""
    config = ExecutionConfig()
    assert config.max_retries == 3
    assert config.retry_delay == 1.0
    assert config.enable_backup is True
    assert config.log_all_operations is True
    assert config.abort_on_error is False
    assert config.chunk_size == 100


def test_execution_config_custom():
    """Test custom ExecutionConfig"""
    config = ExecutionConfig(
        max_retries=5,
        retry_delay=2.0,
        enable_backup=False,
        log_all_operations=False,
        abort_on_error=True,
        chunk_size=50
    )
    assert config.max_retries == 5
    assert config.retry_delay == 2.0
    assert config.enable_backup is False
    assert config.abort_on_error is True
    assert config.chunk_size == 50


# ============================================================================
# ExecutionThread Tests (Direct Thread Testing)
# ============================================================================

@pytest.fixture
def temp_test_files():
    """Create a temporary test directory with test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        # Create test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(source, f'test_{i}.tmp')
            with open(file_path, 'w') as f:
                f.write('test content' * 100)
            test_files.append((file_path, os.path.getsize(file_path)))

        # Create test directory
        test_dir = os.path.join(source, 'test_dir')
        os.makedirs(test_dir)
        for i in range(2):
            dir_file = os.path.join(test_dir, f'dir_test_{i}.tmp')
            with open(dir_file, 'w') as f:
                f.write('dir content' * 50)
            test_files.append((dir_file, os.path.getsize(dir_file)))

        yield tmpdir, source, test_files


def test_execution_thread_safe_files(temp_test_files):
    """Test ExecutionThread with Safe files (no backup)"""
    tmpdir, source, test_files = temp_test_files

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

    # Create cleanup items
    items = [
        CleanupItem(
            item_id=i,
            path=path,
            size=size,
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        )
        for i, (path, size) in enumerate(test_files[:2])
    ]

    # Create plan
    plan = CleanupPlan(
        plan_id="test_safe",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    # Create and run thread
    thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=False))
    thread.start()
    thread.wait(10000)

    # Verify files deleted
    for path, _ in test_files[:2]:
        assert not os.path.exists(path), f"File should be deleted: {path}"

    # Verify no backups (Safe items)
    stats = backup_mgr.get_stats()
    assert stats.hardlink_backups == 0
    assert stats.full_backups == 0

    # Check thread state
    assert thread.current_phase == ExecutionPhase.FINALIZING


def test_execution_thread_suspicious_files(temp_test_files):
    """Test ExecutionThread with Suspicious files (hardlink backup)"""
    tmpdir, source, test_files = temp_test_files

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

    # Create cleanup items
    items = [
        CleanupItem(
            item_id=0,
            path=test_files[0][0],
            size=test_files[0][1],
            item_type='file',
            original_risk=RiskLevel.SUSPICIOUS,
            ai_risk=RiskLevel.SUSPICIOUS
        )
    ]

    plan = CleanupPlan(
        plan_id="test_suspicious",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=items[0].size,
        estimated_freed=items[0].size
    )

    # Run thread
    thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=True))
    thread.start()
    thread.wait(10000)

    # Verify file deleted and backup created
    assert not os.path.exists(items[0].path)

    stats = backup_mgr.get_stats()
    assert stats.hardlink_backups == 1


def test_execution_thread_dangerous_files(temp_test_files):
    """Test ExecutionThread with Dangerous files (full backup)"""
    tmpdir, source, test_files = temp_test_files

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

    items = [
        CleanupItem(
            item_id=0,
            path=test_files[1][0],
            size=test_files[1][1],
            item_type='file',
            original_risk=RiskLevel.DANGEROUS,
            ai_risk=RiskLevel.DANGEROUS
        )
    ]

    plan = CleanupPlan(
        plan_id="test_dangerous",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=items[0].size,
        estimated_freed=items[0].size
    )

    thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=True))
    thread.start()
    thread.wait(10000)

    assert not os.path.exists(items[0].path)

    stats = backup_mgr.get_stats()
    assert stats.full_backups == 1


def test_execution_thread_nonexistent_files():
    """Test ExecutionThread with nonexistent files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

        items = [
            CleanupItem(
                item_id=i,
                path=os.path.join(tmpdir, f'nonexistent_{i}.dat'),
                size=100,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            )
            for i in range(2)
        ]

        plan = CleanupPlan(
            plan_id="test_nonexistent",
            scan_type="test",
            scan_target=tmpdir,
            items=items,
            total_size=200,
            estimated_freed=200
        )

        thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=False))
        thread.start()
        thread.wait(5000)

        # Should complete without errors, files just skipped
        assert thread.current_phase == ExecutionPhase.FINALIZING


def test_execution_thread_cancel():
    """Test ExecutionThread cancellation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        # Create many small files
        items = []
        for i in range(50):
            file_path = os.path.join(source, f'file_{i}.tmp')
            with open(file_path, 'w') as f:
                f.write('x')
            items.append(CleanupItem(
                item_id=i,
                path=file_path,
                size=1,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            ))

        plan = CleanupPlan(
            plan_id="test_cancel",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=len(items),
            estimated_freed=len(items)
        )

        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=False))

        thread.start()
        time.sleep(0.1)  # Let it start
        thread.cancel()
        thread.wait(5000)

        # Should be cancelled
        assert thread.is_cancelled is True


def test_execution_thread_empty_plan():
    """Test ExecutionThread with empty plan"""
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

        plan = CleanupPlan(
            plan_id="test_empty",
            scan_type="test",
            scan_target=tmpdir,
            items=[],
            total_size=0,
            estimated_freed=0
        )

        thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=False))
        thread.start()
        thread.wait(5000)

        assert thread.current_phase == ExecutionPhase.FINALIZING


def test_execution_thread_directory_deletion(temp_test_files):
    """Test ExecutionThread directory deletion"""
    tmpdir, source, test_files = temp_test_files

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

    # Find the test directory
    test_dir = os.path.join(source, 'test_dir')
    assert os.path.isdir(test_dir)

    items = [
        CleanupItem(
            item_id=0,
            path=test_dir,
            size=sum(size for path, size in test_files if test_dir in path),
            item_type='directory',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        )
    ]

    plan = CleanupPlan(
        plan_id="test_directory",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=items[0].size,
        estimated_freed=items[0].size
    )

    thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=False))
    thread.start()
    thread.wait(5000)

    assert not os.path.exists(test_dir), "Directory should be deleted"


def test_execution_thread_permission_error():
    """Test ExecutionThread with permission errors"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        # Create file and make read-only
        test_file = os.path.join(source, 'readonly.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.chmod(test_file, 0o444)

        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

        items = [
            CleanupItem(
                item_id=0,
                path=test_file,
                size=4,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            )
        ]

        plan = CleanupPlan(
            plan_id="test_permission",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=4,
            estimated_freed=4
        )

        # With no retries, should fail
        thread = ExecutionThread(
            plan, backup_mgr,
            ExecutionConfig(enable_backup=False, max_retries=0)
        )
        thread.start()
        thread.wait(5000)

        # Restore permissions for cleanup
        os.chmod(test_file, 0o644)

        # Verify thread completed (with potential error)
        assert thread.current_phase == ExecutionPhase.FINALIZING


def test_execution_thread_state_tracking():
    """Test ExecutionThread state tracking"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        test_file = os.path.join(source, 'test.tmp')
        with open(test_file, 'w') as f:
            f.write('test')

        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

        items = [
            CleanupItem(
                item_id=0,
                path=test_file,
                size=4,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            )
        ]

        plan = CleanupPlan(
            plan_id="test_state",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=4,
            estimated_freed=4
        )

        thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=False))

        # Check initial state
        assert thread.current_phase == ExecutionPhase.PREPARING
        assert thread.is_cancelled is False
        assert thread.current_item_index == 0
        assert thread.success_count == 0
        assert thread.failed_count == 0
        assert thread.skipped_count == 0
        assert thread.freed_size == 0

        thread.start()
        thread.wait(5000)

        # Check final state
        assert thread.current_phase == ExecutionPhase.FINALIZING
        assert thread.success_count == 1
        assert thread.freed_size == 4


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_execution_backup_integration(temp_test_files):
    """Test full workflow with backup integration"""
    tmpdir, source, test_files = temp_test_files

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

    # Create mixed risk items
    items = [
        CleanupItem(
            item_id=0,
            path=test_files[0][0],
            size=test_files[0][1],
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        ),
        CleanupItem(
            item_id=1,
            path=test_files[1][0],
            size=test_files[1][1],
            item_type='file',
            original_risk=RiskLevel.SUSPICIOUS,
            ai_risk=RiskLevel.SUSPICIOUS
        ),
        CleanupItem(
            item_id=2,
            path=test_files[2][0],
            size=test_files[2][1],
            item_type='file',
            original_risk=RiskLevel.DANGEROUS,
            ai_risk=RiskLevel.DANGEROUS
        ),
    ]

    plan = CleanupPlan(
        plan_id="test_workflow",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    thread = ExecutionThread(plan, backup_mgr, ExecutionConfig(enable_backup=True))
    thread.start()
    thread.wait(10000)

    # Verify all files deleted
    for item in items:
        assert not os.path.exists(item.path)

    # Verify backup stats
    stats = backup_mgr.get_stats()
    # Safe: no backup, Suspicious: hardlink, Dangerous: full
    assert stats.hardlink_backups == 1
    assert stats.full_backups == 1


def test_concurrent_thread_execution_prevention():
    """Test that executor prevents concurrent execution"""
    from core.execution_engine import SmartCleanupExecutor

    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        for i in range(3):
            with open(os.path.join(source, f'file_{i}.tmp'), 'w') as f:
                f.write('x')

        items = [
            CleanupItem(
                item_id=0,
                path=os.path.join(source, 'file_0.tmp'),
                size=1,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            )
        ]

        plan = CleanupPlan(
            plan_id="test_concurrent",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=1,
            estimated_freed=1
        )

        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

        # Start first execution
        result1 = executor.execute_plan(plan)
        assert result1 is True
        assert not executor.is_idle()

        # Try to start second (should fail)
        result2 = executor.execute_plan(plan, ExecutionConfig(enable_backup=False))
        assert result2 is False

        # Cleanup
        executor.cancel_execution()
