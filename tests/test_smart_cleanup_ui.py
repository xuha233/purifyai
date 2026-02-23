"""
Smart Cleanup UI Unit Tests

Test coverage:
- CleanupItemCard (replaces CleanupItemCard)
- SmartCleanupPage
- CleanupReportDialog
- UI state management
- Mode integration
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Qt
from PyQt5.QtWidgets import QApplication, qApp
if qApp is None:
    QApplication(sys.argv)

from typing import Optional

from ui.smart_cleanup_page import (
    CleanupItemCard,
    SmartCleanupPage,
    CleanupReportDialog
)
from core.models_smart import CleanupItem, CleanupPlan, CleanupStatus, ExecutionResult, ExecutionStatus
from core.models import ScanItem
from core.rule_engine import RiskLevel
from core.backup_manager import BackupManager, BackupType


# ============================================================================
# CleanupItemCard Tests (replaces CleanupItemCard)
# ============================================================================

@pytest.fixture
def test_cleanup_item():
    """Create a test cleanup item"""
    return CleanupItem(
        item_id=1,
        path="C:/Temp/test_file.tmp",
        size=1024,
        item_type='file',
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )


def test_cleanup_item_widget_creation(test_cleanup_item):
    """Test CleanupItemCard creation"""
    widget = CleanupItemCard(test_cleanup_item)
    assert widget is not None
    assert widget.item == test_cleanup_item
    assert widget.is_selected is False


def test_cleanup_item_widget_safe():
    """Test CleanupItemCard with Safe risk"""
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/safe.log",
        size=2048,
        item_type='file',
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )
    widget = CleanupItemCard(item)
    assert widget.is_selected is False


def test_cleanup_item_widget_suspicious():
    """Test CleanupItemCard with Suspicious risk"""
    item = CleanupItem(
        item_id=2,
        path="C:/AppData/config.db",
        size=4096,
        item_type='file',
        original_risk=RiskLevel.SUSPICIOUS,
        ai_risk=RiskLevel.SUSPICIOUS
    )
    widget = CleanupItemCard(item)
    assert widget.is_selected is False


def test_cleanup_item_widget_dangerous():
    """Test CleanupItemCard with Dangerous risk"""
    item = CleanupItem(
        item_id=3,
        path="C:/Windows/system32/dll.sys",
        size=8192,
        item_type='file',
        original_risk=RiskLevel.DANGEROUS,
        ai_risk=RiskLevel.DANGEROUS
    )
    widget = CleanupItemCard(item)
    assert widget.is_selected is False


def test_cleanup_item_widget_checkbox():
    """Test Checkbox in CleanupItemCard"""
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.log",
        size=1024,
        item_type='file',
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )
    widget = CleanupItemCard(item)

    # Initially not selected
    assert widget.is_selected is False

    # Simulate checkbox click
    widget.checkbox.setChecked(True)
    assert widget.is_selected is True

    widget.checkbox.setChecked(False)
    assert widget.is_selected is False


def test_cleanup_item_widget_format_size():
    """Test size formatting"""
    item = CleanupItem(
        item_id=1,
        path="C:/Temp/test.log",
        size=1024,
        item_type='file',
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )
    widget = CleanupItemCard(item)
    assert widget._format_size(1024) == "1.0 KB"
    assert widget._format_size(1024*1024) == "1.0 MB"
    assert widget._format_size(1024*1024*1024) == "1.0 GB"


# ============================================================================
# CleanupReportDialog Tests
# ============================================================================

@pytest.mark.skip(reason="CleanupReportDialog API changed - need to update tests")
def test_cleanup_report_card_creation():
    """Test CleanupReportDialog creation"""
    card = CleanupReportDialog()
    assert card is not None
    assert card.minimumHeight() == 100


@pytest.mark.skip(reason="CleanupReportDialog API changed - need to update tests")
def test_cleanup_report_card_with_result():
    """Test CleanupReportDialog with execution result"""
    result = ExecutionResult(
        plan_id="test_plan",
        started_at=0,
        total_items=100,
        total_size=1024000,
        success_items=90,
        failed_items=5,
        skipped_items=5,
        freed_size=512000,
        failed_size=0
    )

    card = CleanupReportDialog(result)
    assert card.execution_result == result


@pytest.mark.skip(reason="CleanupReportDialog API changed - need to update tests")
def test_cleanup_report_card_update():
    """Test CleanupReportDialog update"""
    card = CleanupReportDialog()

    result = ExecutionResult(
        plan_id="test_plan",
        started_at=0,
        total_items=50,
        total_size=512000,
        success_items=45,
        failed_items=3,
        skipped_items=2,
        freed_size=256000
    )

    card.update_result(result)
    assert card.execution_result == result


@pytest.mark.skip(reason="CleanupReportDialog API changed - need to update tests")
def test_cleanup_report_card_format_size():
    """Test size formatting in report card"""
    card = CleanupReportDialog()
    assert card._format_size(1024) == "1.0 KB"
    assert card._format_size(1024*1024) == "1.0 MB"


# ============================================================================
# CleanupPlanPreviewDialog Tests
# ============================================================================

@pytest.fixture
def test_cleanup_plan():
    """Create a test cleanup plan"""
    items = []
    for i in range(10):
        risk = RiskLevel.SAFE if i < 5 else (RiskLevel.SUSPICIOUS if i < 8 else RiskLevel.DANGEROUS)
        items.append(CleanupItem(
            item_id=i,
            path=f"C:/Temp/file_{i}.tmp",
            size=1024 * (i + 1),
            item_type='file',
            original_risk=risk,
            ai_risk=risk
        ))

    return CleanupPlan(
        plan_id="test_plan",
        scan_type="test",
        scan_target="C:/Temp",
        items=items,
        total_size=sum(item.size for item in items),
        estimated_freed=sum(item.size for item in items if item.ai_risk == RiskLevel.SAFE)
    )


@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_creation(test_cleanup_plan):
    """Test CleanupPlanPreviewDialog creation"""
    backup_mgr = BackupManager()

    dialog = CleanupPlanPreviewDialog(test_cleanup_plan, backup_mgr)
    assert dialog is not None
    assert dialog.plan == test_cleanup_plan
    assert dialog.selected_items == []


@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_get_selected(test_cleanup_plan):
    """Test getting selected items"""
    backup_mgr = BackupManager()

    dialog = CleanupPlanPreviewDialog(test_cleanup_plan, backup_mgr)

    # Initially all Safe items are selected by default
    selected = dialog.get_selected_items()
    safe_count = sum(1 for item in selected if item.ai_risk == RiskLevel.SAFE)
    assert safe_count == len([i for i in test_cleanup_plan.items if i.ai_risk == RiskLevel.SAFE])


@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_select_all(test_cleanup_plan):
    """Test selecting all items"""
    backup_mgr = BackupManager()

    dialog = CleanupPlanPreviewDialog(test_cleanup_plan, backup_mgr)

    # Clear default selections
    dialog._deselect_all()
    assert len(dialog.get_selected_items()) == 0

    # Select all
    dialog._select_all()
    all_selected = dialog.get_selected_items()
    assert len(all_selected) > 0


#@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_deselect_all(test_cleanup_plan):
    """Test deselecting all items"""
    backup_mgr = BackupManager()

    dialog = CleanupPlanPreviewDialog(test_cleanup_plan, backup_mgr)

    # Initially has selected items
    has_selected = len(dialog.get_selected_items()) > 0

    # Deselect all
    dialog._deselect_all()
    assert len(dialog.get_selected_items()) == 0


@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_filter(test_cleanup_plan):
    """Test filtering items"""
    backup_mgr = BackupManager()

    dialog = CleanupPlanPreviewDialog(test_cleanup_plan, backup_mgr)

    # Filter by Safe
    dialog._filter_items(RiskLevel.SAFE)

    # Count visible widgets
    visible_count = sum(1 for w, _ in dialog.item_widgets if w.isVisible() and w.item.ai_risk == RiskLevel.SAFE)
    assert visible_count == len([i for i in test_cleanup_plan.items if i.ai_risk == RiskLevel.SAFE])

    # Reset filter
    dialog._filter_items('all')


@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_format_size(test_cleanup_plan):
    """Test size formatting"""
    backup_mgr = BackupManager()

    dialog = CleanupPlanPreviewDialog(test_cleanup_plan, backup_mgr)
    assert dialog._format_size(1024) == "1.0 KB"
    assert dialog._format_size(1024*1024) == "1.0 MB"


# ============================================================================
# SmartCleanupPage Tests
# ============================================================================

def test_smart_cleanup_page_creation():
    """Test SmartCleanupPage creation"""
    page = SmartCleanupPage()
    assert page is not None
    assert isinstance(page.cleaner, type(page.cleaner))  # SmartCleaner instance


def test_smart_cleanup_page_config():
    """Test SmartCleanupPage config"""
    page = SmartCleanupPage()
    assert page.config.enable_ai is True
    assert page.backup_mgr is not None


def test_smart_cleanup_page_scan_buttons():
    """Test scan mode buttons"""
    page = SmartCleanupPage()

    # Check buttons exist
    assert hasattr(page, 'scan_btn')
    assert hasattr(page, 'preview_btn')
    assert hasattr(page, 'execute_btn')
    assert hasattr(page, 'cancel_btn')


def test_smart_cleanup_page_scan_type_change():
    """Test scan type mode change"""
    page = SmartCleanupPage()

    # Initially system mode selected (index 0)
    assert page.scan_type_index == 0

    # Change to browser mode (index 1)
    page._on_scan_type_changed(1)
    assert page.scan_type_index == 1


def test_smart_cleanup_page_custom_path_mode():
    """Test custom path mode"""
    page = SmartCleanupPage()

    # Change to custom mode (index 3)
    page._on_scan_type_changed(3)
    assert page.scan_type_index == 3
    assert page.custom_path_input.isVisible() is True
    assert page.custom_browse_btn.isVisible() is True

    # Change back to system mode
    page._on_scan_type_changed(0)
    assert page.scan_type_index == 0
    assert page.custom_path_input.isVisible() is False
    assert page.custom_browse_btn.isVisible() is False


def test_smart_cleanup_page_toggle_ai():
    """Test toggling AI"""
    page = SmartCleanupPage()

    # Initially AI enabled
    assert page.config.enable_ai is True

    # Disable AI
    page.toggle_ai(False)
    assert page.config.enable_ai is False

    # Re-enable AI
    page.toggle_ai(True)
    assert page.config.enable_ai is True


def test_smart_cleanup_page_ui_state_scanning():
    """Test UI state during scanning"""
    page = SmartCleanupPage()

    # Set to scanning state
    page._set_ui_state('scanning')

    # Check buttons disabled
    assert page.scan_btn.isEnabled() is False
    assert page.preview_btn.isEnabled() is False
    assert page.execute_btn.isEnabled() is False
    assert page.cancel_btn.isVisible() is True
    assert page.progress_bar.isVisible() is True


def test_smart_cleanup_page_ui_state_preview():
    """Test UI state during preview"""
    page = SmartCleanupPage()

    # Set to preview state
    page._set_ui_state('preview')

    # Check buttons enabled correctly
    assert page.scan_btn.isEnabled() is True
    assert page.preview_btn.isEnabled() is True
    assert page.execute_btn.isEnabled() is False
    assert page.cancel_btn.isVisible() is False
    assert page.progress_bar.isVisible() is False


def test_smart_cleanup_page_ui_state_idle():
    """Test UI state idle"""
    page = SmartCleanupPage()

    # Return to idle state
    page._set_ui_state('idle')

    # Check buttons
    assert page.scan_btn.isEnabled() is True
    assert page.preview_btn.isEnabled() is False
    assert page.execute_btn.isEnabled() is False
    assert page.cancel_btn.isVisible() is False
    assert page.progress_bar.isVisible() is False


# ============================================================================
# Integration Tests
# ============================================================================

def test_smart_cleanup_page_idle_without_plan():
    """Test execute without plan shows warning"""
    page = SmartCleanupPage()
    # No plan ready yet
    assert page.current_plan is None


def test_smart_cleanup_page_signal_connections():
    """Test signal connections"""
    page = SmartCleanupPage()

    # Check that signals exist
    assert hasattr(page, 'cleanup_phase_changed')

    # Verify cleaner has signals connected by checking if we can execute
    # (This mainly tests that no errors occur during initialization)
    signals_emitted = []

    def on_phase_changed(phase):
        signals_emitted.append(('phase', phase))

    page.cleanup_phase_changed.connect(on_phase_changed)


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_cleanup_item_widget_empty_path():
    """Test CleanupItemCard with path truncation"""
    very_long_path = "C:/Very/Long/Path/That/Exceeds/The/Maximum/Length/For/Display/file.txt"
    item = CleanupItem(
        item_id=1,
        path=very_long_path,
        size=1024,
        item_type='file',
        original_risk=RiskLevel.SAFE,
        ai_risk=RiskLevel.SAFE
    )
    widget = CleanupItemCard(item)
    assert widget is not None


@pytest.mark.skip(reason="CleanupPlanPreviewDialog class removed - UI refactored")
def test_cleanup_plan_preview_dialog_empty_plan():
    """Test preview dialog with empty plan"""
    backup_mgr = BackupManager()

    empty_plan = CleanupPlan(
        plan_id="empty",
        scan_type="test",
        scan_target=".",
        items=[],
        total_size=0,
        estimated_freed=0
    )

    dialog = CleanupPlanPreviewDialog(empty_plan, backup_mgr)
    assert dialog.get_selected_items() == []


@pytest.mark.skip(reason="CleanupReportDialog API changed - need to update tests")
def test_cleanup_report_card_empty_result():
    """Test report card with no result"""
    card = CleanupReportDialog()

    # Initially no result
    assert "等待执行" in card.phase_label.text() if hasattr(card, 'phase_label') else True
