# -*- coding: utf-8 -*-
import pytest
from unittest.mock import Mock
from src.agent.agents.scan_agent import ScanAgent
from src.agent.orchestrator import AgentType

class TestScanAgentInit:
    def test_init_with_orchestrator(self):
        mock_orchestrator = Mock()
        agent = ScanAgent(mock_orchestrator)
        assert agent.orchestrator == mock_orchestrator
        assert agent.agent_type == AgentType.SCAN
        assert len(agent.known_patterns) > 0
    
    def test_init_known_patterns(self):
        mock_orchestrator = Mock()
        agent = ScanAgent(mock_orchestrator)
        assert "temp_files" in agent.known_patterns
        assert "cache_files" in agent.known_patterns
        assert "log_files" in agent.known_patterns
        assert "system_junk" in agent.known_patterns

class TestScanAgentScan:
    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = Mock()
        mock_session = Mock()
        mock_session.session_id = "test-session-123"
        orchestrator.create_session.return_value = mock_session
        orchestrator.run_agent_loop.return_value = {
            "is_complete": True,
            "session_id": "test-session-123",
            "responses": ["```json\n{\"files\": [{\"path\": \"/tmp/test.log\", \"size\": 1024, \"is_garbage\": true}], \"summary\": {\"total_files\": 1}}\n```"]
        }
        return orchestrator
    
    def test_scan_basic(self, mock_orchestrator):
        agent = ScanAgent(mock_orchestrator)
        result = agent.scan(scan_paths=["/tmp"], scan_patterns=["temp_files"])
        mock_orchestrator.create_session.assert_called_once()
        mock_orchestrator.run_agent_loop.assert_called_once()
        assert result["success"] == True
        assert "files" in result
    
    def test_quick_scan(self, mock_orchestrator):
        agent = ScanAgent(mock_orchestrator)
        result = agent.quick_scan("/tmp")
        mock_orchestrator.create_session.assert_called_once()
        assert result["scan_id"] == "test-session-123"

class TestScanAgentErrorHandling:
    def test_scan_with_orchestrator_error(self):
        mock_orchestrator = Mock()
        mock_session = Mock()
        mock_session.session_id = "test-123"
        mock_orchestrator.create_session.return_value = mock_session
        mock_orchestrator.run_agent_loop.side_effect = Exception("AI service error")
        agent = ScanAgent(mock_orchestrator)
        result = agent.scan(scan_paths=["/tmp"])
        assert result["success"] == False
        assert "error" in result
