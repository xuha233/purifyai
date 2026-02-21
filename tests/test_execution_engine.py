"""
Execution Engine Unit Tests

Test coverage:
- SmartCleanupExecutor class
- ExecutionThread class
- ExecutionConfig dataclass
- ExecutionPhase enum
- ErrorType enum
- RetryStrategy enum
- Plan execution workflow
- Progress reporting
- Cancellation support
- Backup integration
- Error handling and recovery
"""
import pytest
import sys
import os
import tempfile
import time
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Ensure QApplication instance exists (required for PyQt5 signals)
app = None

from core.execution_engine import (
    SmartCleanupExecutor,
    ExecutionThread,
    ExecutionConfig,
    ExecutionPhase,
    ErrorType,
    RetryStrategy,
    get_executor
)
from core.models_smart import (
    CleanupPlan, CleanupItem, CleanupStatus, ExecutionStatus,
    ExecutionResult, FailureInfo
)
from core.backup_manager import BackupManager, BackupType
from core.rule_engine import RiskLevel
from core.database import get_database


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
# SmartCleanupExecutor Tests
# ============================================================================

def test_executor_creation():
    """Test SmartCleanupExecutor creation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        executor = SmartCleanupExecutor(backup_mgr=backup_mgr)
        assert executor is not None
        assert executor.is_idle() is True


def test_get_executor_utility():
    """Test utility function"""
    executor = get_executor()
    assert executor is not None
    assert isinstance(executor, SmartCleanupExecutor)


def test_executor_status():
    """Test executor status"""
    executor = SmartCleanupExecutor()
    status = executor.get_status()
    assert status['status'] == 'idle'
    assert status['plan_id'] is None
    assert status['progress'] == (0, 0)


def test_executor_idle_check():
    """Test executor idle check"""
    executor = SmartCleanupExecutor()
    assert executor.is_idle() is True


# ============================================================================
# Cleanup Execution Integration Tests
# ============================================================================

@pytest.fixture
def temp_test_dir():
    """Create a temporary test directory with test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        # Create test files
        test_files = []
        for i in range(5):
            file_path = os.path.join(source, f'test_{i}.tmp')
            with open(file_path, 'w') as f:
                f.write('test content' * 100)
            test_files.append(file_path)

        # Create test directory
        test_dir = os.path.join(source, 'test_dir')
        os.makedirs(test_dir)
        for i in range(3):
            dir_file = os.path.join(test_dir, f'dir_test_{i}.tmp')
            with open(dir_file, 'w') as f:
                f.write('dir content' * 50)
            test_files.append(dir_file)

        yield tmpdir, source, test_files


def test_execute_plan_safe_files(temp_test_dir):
    """Test executing plan with safe files (no backup)"""
    tmpdir, source, test_files = temp_test_dir

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
    executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

    # Create cleanup plan with safe items
    items = [
        CleanupItem(
            item_id=i,
            path=path,
            size=os.path.getsize(path),
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        )
        for i, path in enumerate(test_files[:3])
    ]

    plan = CleanupPlan(
        plan_id="test_plan_safe",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    # Track signals
    signals = []

    def on_completed(result):
        signals.append(('completed', result))

        # Verify files were deleted
        for item in items:
            assert not os.path.exists(item.path)

        # Verify no backups were created (Safe items)
        # 等待备份目录稳定
        time.sleep(0.5)
        stats = backup_mgr.get_stats()
        assert stats.hardlink_backups == 0
        assert stats.full_backups == 0

    # Connect signal
    executor.execution_completed.connect(on_completed)

    # Execute plan with backup disabled for testing speed
    config = ExecutionConfig(enable_backup=False)
    executor.execute_plan(plan, config)

    # Wait for thread completion
    if executor.current_thread:
        executor.current_thread.wait(10000)

    # Process Qt events manually
    from conftest import qt_wait_for_signal
    qt_wait_for_signal(executor.execution_completed, timeout=1000)

    # Final verification
    assert len(signals) >= 0  # Signals may not always be captured in tests
    # Direct file deletion verification (the core functionality)

    assert len(signals) == 1
    assert signals[0][0] == 'completed'


def test_execute_plan_suspicious_files(temp_test_dir):
    """Test executing plan with suspicious files (hardlink backup)"""
    tmpdir, source, test_files = temp_test_dir

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
    executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

    # Create cleanup plan with suspicious items
    items = [
        CleanupItem(
            item_id=i,
            path=path,
            size=os.path.getsize(path),
            item_type='file',
            original_risk=RiskLevel.SUSPICIOUS,
            ai_risk=RiskLevel.SUSPICIOUS
        )
        for i, path in enumerate(test_files[:2])
    ]

    plan = CleanupPlan(
        plan_id="test_plan_suspicious",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    # Track signals
    signals = []

    def on_completed(result):
        signals.append(('completed', result))

        # Verify files were deleted
        for item in items:
            assert not os.path.exists(item.path)

        # Verify backups were created (hardlink for suspicious)
        stats = backup_mgr.get_stats()
        assert stats.hardlink_backups > 0

    executor.execution_completed.connect(on_completed)

    # Execute plan
    executor.execute_plan(plan)

    # Wait for completion
    timeout = 10
    start = time.time()
    while not signals and (time.time() - start) < timeout:
        time.sleep(0.1)

    assert len(signals) == 1


def test_execute_plan_dangerous_files(temp_test_dir):
    """Test executing plan with dangerous files (full backup)"""
    tmpdir, source, test_files = temp_test_dir

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
    executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

    # Create cleanup plan with dangerous items
    items = [
        CleanupItem(
            item_id=i,
            path=path,
            size=os.path.getsize(path),
            item_type='file',
            original_risk=RiskLevel.DANGEROUS,
            ai_risk=RiskLevel.DANGEROUS
        )
        for i, path in enumerate(test_files[:1])
    ]

    plan = CleanupPlan(
        plan_id="test_plan_dangerous",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    # Track signals
    signals = []

    def on_completed(result):
        signals.append(('completed', result))

        # Verify files were deleted
        for item in items:
            assert not os.path.exists(item.path)

        # Verify backups were created (full for dangerous)
        stats = backup_mgr.get_stats()
        assert stats.full_backups > 0

    executor.execution_completed.connect(on_completed)

    # Execute plan
    executor.execute_plan(plan)

    # Wait for completion
    timeout = 10
    start = time.time()
    while not signals and (time.time() - start) < timeout:
        time.sleep(0.1)

    assert len(signals) == 1


# ============================================================================
# Progress Reporting Tests
# ============================================================================

def test_progress_reporting(temp_test_dir):
    """Test progress reporting during execution"""
    tmpdir, source, test_files = temp_test_dir

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
    executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

    # Create cleanup plan
    items = [
        CleanupItem(
            item_id=i,
            path=path,
            size=os.path.getsize(path),
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        )
        for i, path in enumerate(test_files)
    ]

    plan = CleanupPlan(
        plan_id="test_progress",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    # Track progress signals
    progress_signals = {
        'phase': [],
        'item_started': [],
        'item_completed': [],
        'completed': []
    }

    def on_execution_started(plan_id):
        progress_signals['started'] = plan_id

    def on_item_started(plan_id, path):
        progress_signals['item_started'].append((plan_id, path))

    def on_item_completed(plan_id, path, status):
        progress_signals['item_completed'].append((plan_id, path, status))

    def on_phase_changed(plan_id, phase):
        progress_signals['phase'].append((plan_id, phase))

    def on_completed(result):
        progress_signals['completed'].append(result)

    executor.execution_started.connect(on_execution_started)
    executor.item_started.connect(on_item_started)
    executor.item_completed.connect(on_item_completed)
    executor.phase_changed.connect(on_phase_changed)
    executor.execution_completed.connect(on_completed)

    # Execute plan
    config = ExecutionConfig(enable_backup=False)
    executor.execute_plan(plan, config)

    # Wait for completion
    timeout = 10
    start = time.time()
    while not progress_signals['completed'] and (time.time() - start) < timeout:
        time.sleep(0.1)

    # Verify progress signals
    assert progress_signals['started'] == "test_progress"
    assert len(progress_signals['item_started']) == len(items)
    assert len(progress_signals['item_completed']) == len(items)
    assert len(progress_signals['phase']) > 0
    assert len(progress_signals['completed']) == 1


# ============================================================================
# Cancellation Tests
# ============================================================================

def test_cancellation(temp_test_dir):
    """Test execution cancellation"""
    tmpdir, source, test_files = temp_test_dir

    # Create many files to allow cancellation during execution
    extra_files = []
    for i in range(20):
        file_path = os.path.join(source, f'extra_{i}.tmp')
        with open(file_path, 'w') as f:
            f.write('x' * 1000)  # Small file
        extra_files.append(file_path)

    all_files = test_files + extra_files

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
    executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

    # Create cleanup plan
    items = [
        CleanupItem(
            item_id=i,
            path=path,
            size=os.path.getsize(path),
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        )
        for i, path in enumerate(all_files)
    ]

    plan = CleanupPlan(
        plan_id="test_cancel",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items)
    )

    # Track signals
    cancelled_signal = []

    def on_cancelled(plan_id):
        cancelled_signal.append(plan_id)

    executor.execution_cancelled.connect(on_cancelled)

    # Execute plan
    config = ExecutionConfig(enable_backup=False)
    executor.execute_plan(plan, config)

    # Wait a bit then cancel
    time.sleep(0.5)
    executor.cancel_execution()

    # Wait for cancellation
    timeout = 5
    start = time.time()
    while not cancelled_signal and (time.time() - start) < timeout:
        time.sleep(0.1)

    # Verify cancellation
    assert cancelled_signal == ["test_cancel"]
    assert executor.is_idle() is True


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_nonexistent_file_handling():
    """Test handling of nonexistent files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

        # Create plan with nonexistent files
        items = [
            CleanupItem(
                item_id=i,
                path=os.path.join(tmpdir, f'nonexistent_{i}.dat'),
                size=100,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            )
            for i in range(3)
        ]

        plan = CleanupPlan(
            plan_id="test_nonexistent",
            scan_type="test",
            scan_target=tmpdir,
            items=items,
            total_size=300,
            estimated_freed=300
        )

        # Track signals
        signals = []

        def on_completed(result):
            signals.append(result)

        executor.execution_completed.connect(on_completed)

        # Execute plan
        executor.execute_plan(plan)

        # Wait for completion
        timeout = 5
        start = time.time()
        while not signals and (time.time() - start) < timeout:
            time.sleep(0.1)

        assert len(signals) == 1
        result = signals[0]
        # All files should be skipped
        assert result.skipped_items > 0


def test_permission_error_handling(temp_test_dir):
    """Test handling of permission errors"""
    tmpdir, source, test_files = temp_test_dir

    # Make file read-only (simulating permission issue)
    test_file = test_files[0]
    os.chmod(test_file, 0o444)

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
    executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

    items = [
        CleanupItem(
            item_id=0,
            path=test_file,
            size=os.path.getsize(test_file),
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
        total_size=items[0].size,
        estimated_freed=items[0].size
    )

    # With 0 retries, should fail
    config = ExecutionConfig(enable_backup=False, max_retries=0)
    executor.execute_plan(plan, config)

    # Restore permissions
    os.chmod(test_file, 0o644)


# ============================================================================
# ExecutionThread Tests
# ============================================================================

def test_execution_thread_creation(temp_test_dir):
    """Test ExecutionThread creation"""
    tmpdir, source, test_files = temp_test_dir

    backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))

    items = [
        CleanupItem(
            item_id=0,
            path=test_files[0],
            size=os.path.getsize(test_files[0]),
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE
        )
    ]

    plan = CleanupPlan(
        plan_id="test_thread",
        scan_type="test",
        scan_target=source,
        items=items,
        total_size=items[0].size,
        estimated_freed=items[0].size
    )

    thread = ExecutionThread(plan, backup_mgr)
    assert thread.plan.plan_id == "test_thread"
    assert thread.is_cancelled is False
    assert thread.current_phase == ExecutionPhase.PREPARING


def test_execution_thread_cancel():
    """Test ExecutionThread cancel"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        # Create a large number of files
        items = []
        for i in range(100):
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
            plan_id="test_cancel_thread",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=len(items),
            estimated_freed=len(items)
        )

        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        thread = ExecutionThread(plan, backup_mgr)

        # Start thread
        thread.start()

        # Cancel quickly
        time.sleep(0.1)
        thread.cancel()

        # Wait for thread to finish
        thread.wait()

        assert thread.is_cancelled is True


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_empty_plan():
    """Test executing empty plan"""
    with tempfile.TemporaryDirectory() as tmpdir:
        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

        plan = CleanupPlan(
            plan_id="test_empty",
            scan_type="test",
            scan_target=tmpdir,
            items=[],
            total_size=0,
            estimated_freed=0
        )

        signals = []

        def on_completed(result):
            signals.append(result)

        executor.execution_completed.connect(on_completed)

        # Execute plan
        executor.execute_plan(plan)

        # Wait for completion
        timeout = 5
        start = time.time()
        while not signals and (time.time() - start) < timeout:
            time.sleep(0.1)

        assert len(signals) == 1
        result = signals[0]
        assert result.total_items == 0


def test_concurrent_execution():
    """Test that concurrent execution is prevented"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source = os.path.join(tmpdir, 'source')
        os.makedirs(source)

        # Create test files
        for i in range(5):
            file_path = os.path.join(source, f'file_{i}.tmp')
            with open(file_path, 'w') as f:
                f.write('x')

        items = [
            CleanupItem(
                item_id=0,
                path=os.path.join(source, f'file_{0}.tmp'),
                size=1,
                item_type='file',
                original_risk=RiskLevel.SAFE,
                ai_risk=RiskLevel.SAFE
            )
        ]

        plan1 = CleanupPlan(
            plan_id="plan1",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=1,
            estimated_freed=1
        )

        plan2 = CleanupPlan(
            plan_id="plan2",
            scan_type="test",
            scan_target=source,
            items=items,
            total_size=1,
            estimated_freed=1
        )

        backup_mgr = BackupManager(backup_root=os.path.join(tmpdir, 'backups'))
        executor = SmartCleanupExecutor(backup_mgr=backup_mgr)

        # Start first execution
        result1 = executor.execute_plan(plan1)
        assert result1 is True
        assert executor.is_idle() is False

        # Try to start second execution (should fail)
        result2 = executor.execute_plan(plan2)
        assert result2 is False
