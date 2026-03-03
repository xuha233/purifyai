# -*- coding: utf-8 -*-
import pytest
from unittest.mock import Mock
from src.agent.agents.report_agent import ReportAgent
from src.agent.orchestrator import AgentType

class TestReportAgentInit:
    def test_init_with_orchestrator(self):
        mock_orchestrator = Mock()
        agent = ReportAgent(mock_orchestrator)
        assert agent.orchestrator == mock_orchestrator
        assert agent.agent_type == AgentType.REPORT

class TestReportAgentGenerate:
    @pytest.fixture
    def agent(self):
        return ReportAgent(Mock())
    
    @pytest.fixture
    def sample_scan_result(self):
        return {
            "scan_type": "system",
            "files": [
                {"path": "/tmp/file1.log", "size": 1024, "category": "temp", "risk": "safe"},
                {"path": "/tmp/file2.log", "size": 2048, "category": "temp", "risk": "safe"}
            ],
            "summary": {"total_files": 2}
        }
    
    @pytest.fixture
    def sample_cleanup_result(self):
        return {
            "total_planned": 2,
            "deleted_count": 2,
            "failed_count": 0,
            "deleted_files": [{"path": "/tmp/file1.log", "size": 1024}],
            "failed_files": [],
            "total_freed_bytes": 3072,
            "success_rate": 1.0,
            "is_dry_run": False
        }
    
    def test_generate_report_basic(self, agent, sample_scan_result, sample_cleanup_result):
        report = agent.generate_report(sample_scan_result, sample_cleanup_result)
        assert "report_id" in report
        assert "summary" in report
        assert "statistics" in report
        assert "recommendations" in report
    
    def test_generate_report_summary(self, agent, sample_scan_result, sample_cleanup_result):
        report = agent.generate_report(sample_scan_result, sample_cleanup_result)
        summary = report["summary"]
        assert summary["total_scanned"] == 2
        assert summary["deleted_count"] == 2

class TestReportAgentFormatting:
    @pytest.fixture
    def agent(self):
        return ReportAgent(Mock())
    
    def test_format_bytes(self, agent):
        assert agent._format_bytes(512) == "512.00 B"
        assert agent._format_bytes(1024) == "1.00 KB"
        assert agent._format_bytes(1024 * 1024) == "1.00 MB"
    
    def test_format_report_as_markdown(self, agent):
        report = {
            "report_id": "test-report",
            "generated_at": "2024-01-01T00:00:00",
            "summary": {
                "scan_type": "system",
                "total_scanned": 10,
                "total_planned": 5,
                "deleted_count": 4,
                "failed_count": 1,
                "success_rate": 80.0,
                "total_freed_bytes": 4096
            },
            "statistics": {"files_by_type": {"temp": 5}, "space_by_type": {"temp": 4096}},
            "failures": {"total_failures": 0, "error_types": {}, "top_failures": []},
            "recommendations": ["Test recommendation"]
        }
        markdown = agent.format_report_as_markdown(report)
        assert "# 清理操作报告" in markdown
        assert "## 执行摘要" in markdown
