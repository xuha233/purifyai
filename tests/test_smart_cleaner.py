"""
Smart Cleaner Unit Tests

Test coverage:
- SmartCleaner class
- ScanThread class
- SmartCleanConfig dataclass
- SmartCleanPhase enum
- ScanType enum
- Complete workflow integration
- Progress reporting
- Cancellation support
- Error handling
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

from core.smart_cleaner import (
    SmartCleaner,
    SmartCleanConfig,
    SmartCleanPhase,
    ScanType,
    ScanThread,
    get_smart_cleaner
)
from core.ai_analyzer import CostControlMode
from core.models_smart import CleanupPlan, CleanupStatus, CleanupItem
from core.models import ScanItem
from core.rule_engine import RiskLevel


# ============================================================================
# Enums Tests
# ============================================================================

def test_smart_clean_phase_enum():
    """Test SmartCleanPhase enum"""
    assert SmartCleanPhase.IDLE.value == "idle"
    assert SmartCleanPhase.SCANNING.value == "scanning"
    assert SmartCleanPhase.ANALYZING.value == "analyzing"
    assert SmartCleanPhase.PREVIEW.value == "preview"
    assert SmartCleanPhase.EXECUTING.value == "executing"
    assert SmartCleanPhase.COMPLETED.value == "completed"
    assert SmartCleanPhase.ERROR.value == "error"


def test_scan_type_enum():
    """Test ScanType enum"""
    assert ScanType.SYSTEM.value == "system"
    assert ScanType.BROWSER.value == "browser"
    assert ScanType.APPDATA.value == "appdata"
    assert ScanType.CUSTOM.value == "custom"
    assert ScanType.DISK.value == "disk"


# ============================================================================
# SmartCleanConfig Tests
# ============================================================================

def test_smart_clean_config_default():
    """Test default SmartCleanConfig"""
    config = SmartCleanConfig()
    assert config.enable_ai is True
    assert config.max_ai_calls == 100
    assert config.cost_mode == CostControlMode.FALLBACK
    assert config.enable_backup is True
    assert config.backup_retention_days == 7
    assert config.max_retries == 3
    assert config.abort_on_error is False
    assert config.min_size_mb == 0
    assert config.exclude_patterns == []


def test_smart_clean_config_custom():
    """Test custom SmartCleanConfig"""
    config = SmartCleanConfig(
        enable_ai=False,
        max_ai_calls=50,
        enable_backup=False,
        max_retries=5,
        min_size_mb=10
    )
    assert config.enable_ai is False
    assert config.max_ai_calls == 50
    assert config.enable_backup is False
    assert config.max_retries == 5
    assert config.min_size_mb == 10


# ============================================================================
# SmartCleaner Tests
# ============================================================================

def test_smart_cleaner_creation():
    """Test SmartCleaner creation"""
    from core.backup_manager import BackupManager

    with tempfile.TemporaryDirectory() as tmpdir:
        backup_root = os.path.join(tmpdir, 'backups')
        backup_mgr = BackupManager(backup_root=backup_root)
        cleaner = SmartCleaner(backup_mgr=backup_mgr)
        assert cleaner is not None
        assert cleaner.current_phase == SmartCleanPhase.IDLE


def test_get_smart_cleaner_utility():
    """Test utility function"""
    cleaner = get_smart_cleaner()
    assert cleaner is not None
    assert isinstance(cleaner, SmartCleaner)


def test_cleaner_initial_phase():
    """Test cleaner initial phase"""
    cleaner = SmartCleaner()
    assert cleaner.get_current_phase() == SmartCleanPhase.IDLE


def test_cleaner_idle_check():
    """Test cleaner idle check"""
    cleaner = SmartCleaner()
    assert cleaner._is_idle()


def test_cleaner_reset():
    """Test cleaner reset"""
    cleaner = SmartCleaner()
    cleaner._set_phase(SmartCleanPhase.EXECUTING)
    assert cleaner.get_current_phase() == SmartCleanPhase.EXECUTING
    cleaner.reset()
    assert cleaner.get_current_phase() == SmartCleanPhase.IDLE


def test_cleaner_get_scan_results():
    """Test get_scan_results"""
    cleaner = SmartCleaner()
    results = cleaner.get_scan_results()
    assert results == []


def test_cleaner_get_cleanup_plan():
    """Test get_cleanup_plan"""
    cleaner = SmartCleaner()
    plan = cleaner.get_cleanup_plan()
    assert plan is None


def test_concurrent_scan_prevention():
    """Test concurrent scan prevention"""
    cleaner = SmartCleaner()
    cleaner._set_phase(SmartCleanPhase.SCANNING)

    result = cleaner.start_scan("system")
    assert result is False


# ============================================================================
# ScanThread Tests
# ============================================================================

def test_scan_thread_creation():
    """Test ScanThread creation"""
    thread = ScanThread("system", "")
    assert thread.scan_type == "system"
    assert thread.scan_target == ""
    assert thread.is_cancelled is False


def test_scan_thread_cancel():
    """Test ScanThread cancel"""
    thread = ScanThread("browser", "")
    assert thread.is_cancelled is False
    thread.cancel()
    assert thread.is_cancelled is True


# ============================================================================
# Workflow Integration Tests
# ============================================================================

def test_plan_summary():
    """Test plan summary generation"""
    cleaner = SmartCleaner()

    # Create a mock plan
    items = []
    for i in range(10):
        items.append(CleanupItem(
            item_id=i,
            path=f"/test/file_{i}.tmp",
            size=1024,
            item_type='file',
            original_risk=RiskLevel.SAFE,
            ai_risk=RiskLevel.SAFE if i < 5 else RiskLevel.SUSPICIOUS
        ))

    plan = CleanupPlan(
        plan_id="test_plan",
        scan_type="test",
        scan_target="/test",
        items=items,
        total_size=len(items) * 1024,
        estimated_freed=5 * 1024  # Only safe items
    )

    cleaner.current_plan = plan
    summary = cleaner.get_plan_summary()

    assert summary['total_items'] == 10
    assert summary['safe_count'] == 5
    assert summary['suspicious_count'] == 5
    assert summary['total_size'] == 10240
    assert summary['estimated_freed'] == 5120


def test_signal_emission_phase_change():
    """Test phase change signal emission"""
    cleaner = SmartCleaner()

    phases = []

    def on_phase_changed(phase):
        phases.append(phase)

    cleaner.phase_changed.connect(on_phase_changed)

    cleaner._set_phase(SmartCleanPhase.SCANNING)
    cleaner._set_phase(SmartCleanPhase.ANALYZING)
    cleaner._set_phase(SmartCleanPhase.PREVIEW)

    assert len(phases) == 3
    assert phases[0] == "scanning"
    assert phases[1] == "analyzing"
    assert phases[2] == "preview"


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_empty_scan_type():
    """Test handling of empty scan type"""
    cleaner = SmartCleaner()
    # Empty scan type starts the thread but scanner won't find anything
    # The behavior is that scanning starts but completes with no results
    result = cleaner.start_scan("")
    # Thread starts but has no meaningful scan
    assert result is True


def test_unsupported_scan_type():
    """Test handling of unsupported scan type"""
    cleaner = SmartCleaner()
    # Unsupported types are handled in the thread by emitting an error
    result = cleaner.start_scan("unsupported_type")
    # Thread starts but will emit error
    assert result is True


def test_execute_without_plan():
    """Test execute_cleanup without plan"""
    cleaner = SmartCleaner()
    result = cleaner.execute_cleanup()
    assert result is False


def test_cancel_when_idle():
    """Test cancel when idle (should be safe)"""
    cleaner = SmartCleaner()
    # Should not crash
    cleaner.cancel()
    assert cleaner.get_current_phase() == SmartCleanPhase.IDLE


# ============================================================================
# Configuration Tests
# ============================================================================

def test_ai_cost_config():
    """Test AI cost config generation"""
    config = SmartCleanConfig(
        max_ai_calls=50,
        cost_mode=CostControlMode.BUDGET
    )

    cleaner = SmartCleaner(config=config)
    cost_config = cleaner._get_ai_cost_config()

    assert cost_config.max_calls_per_scan == 50
    assert cost_config.mode == CostControlMode.BUDGET
    assert cost_config.only_analyze_suspicious is True
    assert cost_config.fallback_to_rules is True


def test_disable_ai_config():
    """Test disabled AI config"""
    config = SmartCleanConfig(
        enable_ai=False,
        cost_mode=CostControlMode.RULES_ONLY
    )

    cleaner = SmartCleaner(config=config)
    cost_config = cleaner._get_ai_cost_config()

    assert cost_config.mode == CostControlMode.RULES_ONLY


# ============================================================================
# Mock Workflow Tests
# ============================================================================

def test_mock_scan_analyze_flow():
    """Test scan and analyze flow with mock data"""
    cleaner = SmartCleaner()

    # Simulate scan items
    mock_items = [
        ScanItem(
            path="/temp/test1.tmp",
            description="Temp file 1",
            size=1024,
            item_type='file',
            risk_level='safe'
        ),
        ScanItem(
            path="/temp/test2.tmp",
            description="Temp file 2",
            size=2048,
            item_type='file',
            risk_level='suspicious'
        ),
    ]

    cleaner.scan_items = mock_items

    # Should transition to analyze phase
    cleaner._set_phase(SmartCleanPhase.ANALYZING)
    cleaner._analyze_items(mock_items, "test")

    # Verify plan was created
    assert cleaner.get_cleanup_plan() is not None


def test_component_integration():
    """Test that all components are properly initialized"""
    cleaner = SmartCleaner()

    # Verify components exist
    assert cleaner.ai_analyzer is not None
    assert cleaner.executor is not None
    assert cleaner.backup_mgr is not None
    assert cleaner.db is not None
    assert cleaner.config is not None
