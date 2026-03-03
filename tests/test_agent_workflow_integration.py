# -*- coding: utf-8 -*-
"""
智能体工作流集成测试 - Agent Workflow Integration Tests
"""
import pytest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Mock PyQt5
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()
sys.modules['qfluentwidgets'] = MagicMock()

mock_logger = MagicMock()
mock_logger.get_logger = lambda name: MagicMock()
sys.modules['utils.logger'] = mock_logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.agent.agents.scan_agent import ScanAgent
from src.agent.agents.review_agent import ReviewAgent
from src.agent.agents.cleanup_agent import CleanupAgent
from src.agent.agents.report_agent import ReportAgent
from src.agent.orchestrator import AgentOrchestrator, AgentType, AIConfig


@pytest.fixture
def mock_orchestrator():
    orchestrator = Mock(spec=AgentOrchestrator)
    orchestrator.ai_config = AIConfig(api_key="test-key", model="test-model")
    orchestrator.sessions = {}
    orchestrator.current_session_id = None
    orchestrator.active_agent_type = None
    
    def create_session(agent_type, workspace=None, metadata=None):
        session_id = f"{agent_type.value}_test_{int(datetime.now().timestamp())}"
        mock_session = Mock()
        mock_session.session_id = session_id
        mock_session.agent_type = agent_type.value
        mock_session.workspace = workspace
        mock_session.metadata = metadata or {}
        orchestrator.sessions[session_id] = mock_session
        orchestrator.current_session_id = session_id
        return mock_session
    
    orchestrator.create_session = Mock(side_effect=create_session)
    orchestrator.get_session = Mock(side_effect=lambda sid: orchestrator.sessions.get(sid))
    orchestrator.close_session = Mock(side_effect=lambda sid: orchestrator.sessions.pop(sid, None))
    
    return orchestrator


@pytest.fixture
def scan_agent(mock_orchestrator):
    return ScanAgent(mock_orchestrator)


@pytest.fixture
def review_agent(mock_orchestrator):
    return ReviewAgent(mock_orchestrator)


@pytest.fixture
def cleanup_agent(mock_orchestrator):
    return CleanupAgent(mock_orchestrator)


@pytest.fixture
def report_agent(mock_orchestrator):
    return ReportAgent(mock_orchestrator)


@pytest.fixture
def sample_scan_result():
    return {
        "success": True,
        "scan_id": "scan_test_123",
        "files": [
            {"path": "/tmp/test1.log", "size": 1024, "is_garbage": True, "category": "temp", "risk": "safe"},
            {"path": "/tmp/test2.log", "size": 2048, "is_garbage": True, "category": "temp", "risk": "safe"},
            {"path": "/tmp/cache/test.cache", "size": 4096, "is_garbage": True, "category": "cache", "risk": "safe"},
        ],
        "summary": {"total_files": 3, "garbage_files": 3, "total_size": 7168, "scan_duration": 1.5}
    }


@pytest.fixture
def sample_cleanup_result():
    return {
        "total_planned": 3, "deleted_count": 3, "failed_count": 0,
        "deleted_files": [
            {"path": "/tmp/test1.log", "size": 1024},
            {"path": "/tmp/test2.log", "size": 2048},
            {"path": "/tmp/cache/test.cache", "size": 4096}
        ],
        "failed_files": [], "total_freed_bytes": 7168, "is_dry_run": False, "success_rate": 1.0
    }


class TestScanAgentIntegration:
    def test_scan_agent_initialization(self, scan_agent):
        assert scan_agent.agent_type == AgentType.SCAN
        assert len(scan_agent.known_patterns) >= 4
        assert "temp_files" in scan_agent.known_patterns

    def test_build_scan_request(self, scan_agent):
        request = scan_agent._build_scan_request(["/tmp", "/var"], ["temp_files", "log_files"])
        assert "# 扫描任务" in request
        assert "/tmp" in request

    def test_parse_scan_result_with_json(self, scan_agent):
        # Use actual newlines, not escaped \n
        json_data = {"files": [{"path": "/tmp/test.log", "size": 1024, "is_garbage": True}], "summary": {"total_files": 1}}
        json_str = json.dumps(json_data)
        response = "```json\n" + json_str + "\n```"
        
        agent_result = {
            "is_complete": True, 
            "session_id": "scan_test_123",
            "responses": [response]
        }
        result = scan_agent._parse_scan_result(agent_result)
        assert result["success"] == True
        assert len(result["files"]) == 1


class TestReviewAgentIntegration:
    def test_review_agent_initialization(self, review_agent):
        assert review_agent.agent_type == AgentType.REVIEW
        assert len(review_agent.dangerous_paths) > 0

    def test_quick_review_dangerous_path(self, review_agent):
        risk = review_agent.quick_review("C:\\Windows\\System32\\test.dll")
        assert risk == "dangerous"

    def test_quick_review_safe_file(self, review_agent):
        risk = review_agent.quick_review("/tmp/test.log")
        assert risk == "safe"


class TestCleanupAgentIntegration:
    def test_cleanup_agent_initialization(self, cleanup_agent):
        assert cleanup_agent.agent_type == AgentType.CLEANUP
        assert cleanup_agent.deleted_files == []

    def test_execute_cleanup_dry_run(self, cleanup_agent):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("test content")
            temp_path = f.name
        try:
            result = cleanup_agent.execute_cleanup([{"path": temp_path, "type": "file"}], is_dry_run=True)
            assert result["is_dry_run"] == True
            assert result["deleted_count"] == 1
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_execute_cleanup_real(self, cleanup_agent):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("test content")
            temp_path = f.name
        try:
            result = cleanup_agent.execute_cleanup([{"path": temp_path, "type": "file"}], is_dry_run=False)
            assert result["deleted_count"] == 1
            assert not os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestReportAgentIntegration:
    def test_report_agent_initialization(self, report_agent):
        assert report_agent.agent_type == AgentType.REPORT

    def test_generate_report(self, report_agent, sample_scan_result, sample_cleanup_result):
        report = report_agent.generate_report(sample_scan_result, sample_cleanup_result)
        assert "report_id" in report
        assert "summary" in report
        assert "statistics" in report


class TestEndToEndWorkflow:
    def test_complete_workflow(self, mock_orchestrator):
        scan_agent = ScanAgent(mock_orchestrator)
        review_agent = ReviewAgent(mock_orchestrator)
        cleanup_agent = CleanupAgent(mock_orchestrator)
        report_agent = ReportAgent(mock_orchestrator)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("test log content")
            temp_file = f.name

        try:
            # Mock scan result with actual newlines
            json_data = {"files": [{"path": temp_file, "size": 16, "is_garbage": True, "category": "temp", "risk": "safe"}], "summary": {"total_files": 1}}
            scan_response = "```json\n" + json.dumps(json_data) + "\n```"
            
            mock_orchestrator.run_agent_loop.return_value = {
                "is_complete": True, 
                "session_id": "scan_test",
                "responses": [scan_response]
            }

            scan_result = scan_agent.scan(scan_paths=[os.path.dirname(temp_file)])
            assert scan_result["success"] == True
            assert len(scan_result["files"]) == 1

            # Mock review result
            review_json = {"safe_to_proceed": True, "blocked_items": []}
            review_response = "```json\n" + json.dumps(review_json) + "\n```"
            mock_orchestrator.run_agent_loop.return_value = {
                "is_complete": True, 
                "responses": [review_response]
            }
            review_result = review_agent.review_cleanup_plan(scan_result["files"])
            assert review_result["safe_to_proceed"] == True

            cleanup_result = cleanup_agent.execute_cleanup(scan_result["files"], is_dry_run=False)
            assert cleanup_result["deleted_count"] == 1

            report = report_agent.generate_report(scan_result, cleanup_result)
            assert "report_id" in report
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


class TestUIAgentIntegration:
    def test_pipeline_stage_transitions(self):
        from src.ui.agent_theme import AgentStage, AgentStatus
        assert AgentStage.SCAN == "scan"
        assert AgentStage.get_name("scan") == "扫描"
        assert AgentStage.get_all_stages() == ["scan", "review", "cleanup", "report"]

    def test_status_colors_mapping(self):
        from src.ui.agent_theme import AgentTheme
        assert AgentTheme.get_status_color("idle") == "#999999"
        assert AgentTheme.get_status_color("running") == "#0078D4"
        assert AgentTheme.get_stage_color("scan") == "#0078D4"
        assert AgentTheme.get_risk_color("safe") == "#52C41A"


class TestErrorHandling:
    def test_scan_agent_handles_ai_error(self, scan_agent, mock_orchestrator):
        mock_orchestrator.run_agent_loop.side_effect = Exception("AI error")
        result = scan_agent.scan(scan_paths=["/tmp"])
        assert result["success"] == False
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
