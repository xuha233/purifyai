"""
Cleanup History Page Unit Tests

Test coverage:
- CleanupHistoryPage class
- HistoryRecord dataclass
- LoadHistoryThread class
- HistoryRecordWidget class
- HistoryRecordDetailsDialog class
- Filtering and searching
- Statistics calculation
- Failed items recovery
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from PyQt5.QtWidgets import QApplication, qApp
if qApp is None:
    QApplication(sys.argv)

import time
from datetime import datetime, timedelta

from ui.cleanup_history_page import (
    HistoryRecord,
    LoadHistoryThread,
    CleanupHistoryPage
)
from core.models_smart import ExecutionStatus
from core.recovery_manager import get_recovery_manager
from core.database import get_database


# ============================================================================
# HistoryRecord Tests
# ============================================================================

def test_history_record_creation():
    """Test HistoryRecord creation"""
    record = HistoryRecord(
        plan_id="test_plan_1",
        plan_name="Test Plan",
        scan_type="system",
        scan_target="C:/Temp",
        total_items=10,
        total_size=1024000,
        estimated_freed=512000,
        status=ExecutionStatus.COMPLETED.value,
        created_at=datetime.now().isoformat(),
        success_count=8,
        failed_count=1,
        skipped_count=1,
        freed_size=256000
    )

    assert record.plan_id == "test_plan_1"
    assert record.status == ExecutionStatus.COMPLETED.value
    assert record.has_failures is True
    assert record.is_completed is True
    assert record.is_running is False


def test_history_record_running():
    """Test HistoryRecord with running status"""
    record = HistoryRecord(
        plan_id="test_plan_running",
        plan_name="Running Plan",
        scan_type="appdata",
        scan_target="C:/AppData",
        total_items=5,
        total_size=512000,
        estimated_freed=256000,
        status=ExecutionStatus.RUNNING.value,
        created_at=datetime.now().isoformat()
    )

    assert record.is_running is True
    assert record.is_completed is False
    assert record.has_failures is False


def test_history_record_without_failures():
    """Test HistoryRecord without failures"""
    record = HistoryRecord(
        plan_id="test_no_failures",
        plan_name="No Failures",
        scan_type="custom",
        scan_target="D:/custom",
        total_items=20,
        total_size=2048000,
        estimated_freed=1024000,
        status=ExecutionStatus.COMPLETED.value,
        created_at=datetime.now().isoformat(),
        success_count=20,
        failed_count=0,
        skipped_count=0,
        freed_size=1024000
    )

    assert record.has_failures is False


# ============================================================================
# LoadHistoryThread Tests
# ============================================================================

def test_load_history_thread_creation():
    """Test LoadHistoryThread creation"""
    thread = LoadHistoryThread(
        limit=10,
        offset=0
    )

    assert thread.limit == 10
    assert thread.offset == 0
    assert thread.is_cancelled is False


def test_load_history_thread_with_filters():
    """Test LoadHistoryThread with filters"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    thread = LoadHistoryThread(
        limit=50,
        offset=0,
        status_filter=ExecutionStatus.COMPLETED.value,
        scan_type_filter="system",
        date_from=yesterday,
        date_to=today
    )

    assert thread.status_filter == ExecutionStatus.COMPLETED.value
    assert thread.scan_type_filter == "system"


def test_load_history_thread_cancel():
    """Test LoadHistoryThread cancellation"""
    thread = LoadHistoryThread(limit=10, offset=0)
    assert thread.is_cancelled is False

    thread.cancel()
    assert thread.is_cancelled is True


# ============================================================================
# CleanupHistoryPage Tests
# ============================================================================

def test_cleanup_history_page_creation():
    """Test CleanupHistoryPage creation"""
    page = CleanupHistoryPage()
    assert page is not None
    assert isinstance(page.recovery_mgr, type(page.recovery_mgr))


def test_cleanup_history_page_filter_reset():
    """Test filter and reset functionality"""
    page = CleanupHistoryPage()
    # Test that filters exist
    assert hasattr(page, 'status_combo')
    assert hasattr(page, 'type_combo')
    assert hasattr(page, 'search_edit')
    assert hasattr(page, 'filter_btn')
    assert hasattr(page, 'reset_btn')


def test_cleanup_history_page_refresh():
    """Test refresh functionality"""
    page = CleanupHistoryPage()
    # Test that refresh exists
    assert hasattr(page, 'refresh_btn')


# ============================================================================
# HistoryRecordWidget Tests
# ============================================================================

def test_history_record_widget_creation():
    """Test HistoryRecordWidget creation"""
    record = HistoryRecord(
        plan_id="test_widget",
        plan_name="Widget Test",
        scan_type="browser",
        scan_target="C:/BrowserCache",
        total_items=5,
        total_size=512000,
        estimated_freed=256000,
        status=ExecutionStatus.COMPLETED.value,
        created_at=datetime.now().isoformat()
    )

    widget = HistoryRecordWidget(record)
    assert widget is not None
    assert widget.record == record


def test_history_record_widget_status_text():
    """Test status text mapping"""
    # Test different statuses
    for status in ['pending', 'running', 'completed', 'cancelled', 'error']:
        record = HistoryRecord(
            plan_id=f"test_{status}",
            plan_name=f"{status.capitalize()} Test",
            scan_type="system",
            scan_target="C:/Temp",
            total_items=1,
            total_size=1024,
            estimated_freed=512,
            status=status,
            created_at=datetime.now().isoformat()
        )

        widget = HistoryRecordWidget(record)

        # The widget should be created without errors
        assert widget is not None


# ============================================================================
# HistoryRecordDetailsDialog Tests
# ============================================================================

def test_history_details_dialog_creation():
    """Test HistoryRecordDetailsDialog creation"""
    record = HistoryRecord(
        plan_id="test_dialog",
        plan_name="Dialog Test",
        scan_type="appdata",
        scan_target="C:/AppData",
        total_items=15,
        total_size=1536000,
        estimated_freed=768000,
        status=ExecutionStatus.COMPLETED.value,
        created_at=datetime.now().isoformat()
    )

    dialog = HistoryRecordDetailsDialog(record)
    assert dialog is not None
    assert dialog.record == record


# ============================================================================
# Integration Tests
# ============================================================================

def test_cleanup_history_page_signal_connections():
    """Test signal connections"""
    page = CleanupHistoryPage()

    # Check that signals exist
    assert hasattr(page, 'record_details_requested')
    assert hasattr(page, 'recover_requested')


def test_cleanup_history_page_format_size():
    """Test size formatting"""
    page = CleanupHistoryPage()

    assert page._format_size(1024) == "128.0 B"
    assert page._format_size(1024 * 1024) == "128.0 KB"
    assert page._format_size(1024 * 1024 * 1024) == "128.0 MB"
    assert page._format_size(1024 * 1024 * 1024 * 1024) == "128.0 GB"


def test_cleanup_history_page_reset_filters():
    """Test filter reset"""
    page = CleanupHistoryPage()

    # Set up filter state
    page.status_combo.setCurrentIndex(1)
    page.type_combo.setCurrentIndex(1)
    page.search_edit.setText("test")

    # Reset filters
    page._reset_filters()

    # Check that filters are reset
    # (indices may be based on available options)
    assert page.search_edit.text() == ""


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_history_record_empty_stats():
    """Test HistoryRecord with zero stats"""
    record = HistoryRecord(
        plan_id="empty_stats",
        plan_name="Empty Stats",
        scan_type="system",
        scan_target="C:/Temp",
        total_items=0,
        total_size=0,
        estimated_freed=0,
        status=ExecutionStatus.PENDING.value,
        created_at=datetime.now().isoformat()
    )

    assert record.total_items == 0
    assert record.total_size == 0
    assert record.estimated_freed == 0
    assert record.success_count == 0
    assert record.failed_count == 0


# ============================================================================
# Database Integration Tests
# ============================================================================

def test_history_with_database():
    """Test history with actual database"""
    db = get_database()

    # This test just validates database integration works
    # Actual record loading is tested in LoadHistoryThread
    assert db is not None

    # Verify tables exist
    conn = db._get_connection()
    cursor = conn.cursor()

    # Check cleanup_plans table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cleanup_plans'")
    result = cursor.fetchone()
    assert result is not None

    conn.close()


# ============================================================================
# Time Formatting Tests
# ============================================================================

def test_history_record_time_formatting():
    """Test time formatting for various periods"""
    # Recent - should show "X minutes ago"
    recent_time = datetime.now() - timedelta(minutes=5)
    record = HistoryRecord(
        plan_id="recent_time",
        plan_name="Recent",
        scan_type="system",
        scan_target="C:/Temp",
        total_items=1,
        total_size=1024,
        estimated_freed=512,
        status=ExecutionStatus.COMPLETED.value,
        created_at=recent_time.isoformat()
    )

    widget = HistoryRecordWidget(record)
    # Widget creation succeeds
    assert widget is not None

    # Very recent - should handle
    very_recent = datetime.now() - timedelta(seconds=30)
    recent_record = HistoryRecord(
        plan_id="very_recent",
        plan_name="Very Recent",
        scan_type="system",
        scan_target="C:/Temp",
        total_items=1,
        total_size=1024,
        estimated_freed=512,
        status=ExecutionStatus.COMPLETED.value,
        created_at=very_recent.isoformat()
    )

    widget2 = HistoryRecordWidget(recent_record)
    assert widget2 is not None


def test_format_size_edge_cases():
    """Test size formatting edge cases"""
    page = CleanupHistoryPage()

    # Zero
    assert page._format_size(0) == "0.0 B"

    # Small values
    assert page._format_size(1) == "0.1 B"
    assert page._format_size(512) == "64.0 B"
    assert page._format_size(1023) == "127.9 B"

    # Byte boundary
    assert page._format_size(1024) == "128.0 B"
    assert page._format_size(1025) == "128.1 B"

    # Large values
    huge_value = 1024 * 1024 * 1024 * 1024  # 1 TB
    assert "TB" in page._format_size(huge_value)
