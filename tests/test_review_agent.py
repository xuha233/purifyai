# -*- coding: utf-8 -*-
import pytest
from unittest.mock import Mock
from src.agent.agents.review_agent import ReviewAgent
from src.agent.orchestrator import AgentType

class TestReviewAgentInit:
    def test_init_with_orchestrator(self):
        mock_orchestrator = Mock()
        agent = ReviewAgent(mock_orchestrator)
        assert agent.orchestrator == mock_orchestrator
        assert agent.agent_type == AgentType.REVIEW
    
    def test_init_dangerous_paths(self):
        mock_orchestrator = Mock()
        agent = ReviewAgent(mock_orchestrator)
        assert len(agent.dangerous_paths) > 0
        assert "C:\\Windows" in agent.dangerous_paths
    
    def test_init_executable_extensions(self):
        mock_orchestrator = Mock()
        agent = ReviewAgent(mock_orchestrator)
        assert len(agent.executable_extensions) > 0
        assert ".exe" in agent.executable_extensions

class TestReviewAgentQuickReview:
    @pytest.fixture
    def agent(self):
        return ReviewAgent(Mock())
    
    def test_quick_review_dangerous_path(self, agent):
        risk = agent.quick_review("C:\\Windows\\System32\\test.dll")
        assert risk == "dangerous"
    
    def test_quick_review_executable_file(self, agent):
        risk = agent.quick_review("/tmp/test.exe")
        assert risk == "suspicious"
    
    def test_quick_review_safe_file(self, agent):
        risk = agent.quick_review("/tmp/test.log")
        assert risk == "safe"

class TestReviewAgentReview:
    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = Mock()
        mock_session = Mock()
        mock_session.session_id = "test-review-123"
        orchestrator.create_session.return_value = mock_session
        orchestrator.run_agent_loop.return_value = {
            "is_complete": True,
            "session_id": "test-review-123",
            "responses": ["```json\n{\"safe_to_proceed\": true, \"blocked_items\": []}\n```"]
        }
        return orchestrator
    
    def test_review_cleanup_plan_basic(self, mock_orchestrator):
        agent = ReviewAgent(mock_orchestrator)
        cleanup_items = [{"path": "/tmp/test.log", "size": 1024}]
        result = agent.review_cleanup_plan(cleanup_items)
        mock_orchestrator.create_session.assert_called_once()
        assert "safe_to_proceed" in result
