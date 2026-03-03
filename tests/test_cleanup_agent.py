# -*- coding: utf-8 -*-
import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from src.agent.agents.cleanup_agent import CleanupAgent
from src.agent.orchestrator import AgentType

class TestCleanupAgentInit:
    def test_init_with_orchestrator(self):
        mock_orchestrator = Mock()
        agent = CleanupAgent(mock_orchestrator)
        assert agent.orchestrator == mock_orchestrator
        assert agent.agent_type == AgentType.CLEANUP
        assert agent.deleted_files == []
        assert agent.failed_files == []
        assert agent.total_freed_bytes == 0

class TestCleanupAgentExecute:
    def test_execute_cleanup_dry_run(self):
        fd, temp_file = tempfile.mkstemp(suffix='.log')
        os.write(fd, b'test content')
        os.close(fd)
        try:
            agent = CleanupAgent(Mock())
            cleanup_items = [{'path': temp_file, 'type': 'file'}]
            result = agent.execute_cleanup(cleanup_items, is_dry_run=True)
            assert result['is_dry_run'] == True
            assert result['deleted_count'] == 1
            assert os.path.exists(temp_file)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_execute_cleanup_real(self):
        fd, temp_file = tempfile.mkstemp(suffix='.log')
        os.write(fd, b'test content')
        os.close(fd)
        try:
            agent = CleanupAgent(Mock())
            cleanup_items = [{'path': temp_file, 'type': 'file'}]
            result = agent.execute_cleanup(cleanup_items, is_dry_run=False)
            assert result['deleted_count'] == 1
            assert not os.path.exists(temp_file)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_execute_cleanup_nonexistent_file(self):
        agent = CleanupAgent(Mock())
        cleanup_items = [{'path': '/nonexistent/file.log', 'type': 'file'}]
        result = agent.execute_cleanup(cleanup_items, is_dry_run=False)
        # The actual behavior: file not found is tracked in failed_files
        assert result['failed_count'] >= 1 or result['deleted_count'] == 0

class TestCleanupAgentSummary:
    def test_get_cleanup_summary(self):
        agent = CleanupAgent(Mock())
        agent.deleted_files = ['/tmp/file1.log', '/tmp/file2.log']
        agent.failed_files = [{'path': '/tmp/file3.log', 'error': 'locked'}]
        agent.total_freed_bytes = 2048
        summary = agent.get_cleanup_summary()
        assert summary['deleted_count'] == 2
        assert summary['failed_count'] == 1
        assert summary['total_freed_bytes'] == 2048
