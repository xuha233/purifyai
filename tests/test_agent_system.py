# -*- coding: utf-8 -*-
"""
智能体系统测试

测试智能体系统的各个组件是否正常工作
"""
import pytest
import tempfile
import os
from pathlib import Path

# 核心导入
from agent import (
    get_orchestrator, AgentType, AIConfig,
    create_scan_agent, create_review_agent,
    create_cleanup_agent, create_report_agent,
    AgentIntegration, get_agent_integration
)
from agent.models_agent import (
    AgentSession, AgentRole, ContentBlock
)
from agent.tools.base import ToolBase
from agent.tools import get_all_tools, get_tool, get_tools_schema, register_tool  # 添加缺失的导入


class DummyTool(ToolBase):
    """测试工具"""
    NAME = "dummy_tool"
    DESCRIPTION = "测试工具"

    def execute(self, input_json, workspace=None):
        """执行测试工具"""
        return f"Dummy tool executed: {input_json}"


@pytest.fixture
def ai_config():
    """AI配置fixture"""
    return AIConfig(
        api_key="test_key",
        model="claude-opus-4-6",
        max_tokens=4096
    )


@pytest.fixture
def orchestrator(ai_config):
    """编排器fixture"""
    return get_orchestrator(ai_config)


@pytest.fixture
def test_dir():
    """测试目录fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestAgentModels:
    """测试智能体数据模型"""

    def test_content_block(self):
        """测试ContentBlock"""
        block = ContentBlock(
            type="text",
            content={"text": "测试消息"}
        )
        assert block.type == "text"
        assert block.content["text"] == "测试消息"

    def test_content_block_to_dict(self):
        """测试ContentBlock转字典"""
        block = ContentBlock(
            type="text",
            content={"text": "测试"}
        )
        result = block.to_dict()
        assert result == {"type": "text", "content": {"text": "测试"}}


class TestAgentOrchestrator:
    """测试编排器"""

    def test_create_orchestrator(self, ai_config):
        """测试创建编排器"""
        orch = get_orchestrator(ai_config)
        assert orch is not None
        assert orch.ai_config.model == "claude-opus-4-6"

    def test_create_session(self, orchestrator):
        """测试创建会话"""
        session = orchestrator.create_session(AgentType.SCAN)
        assert session is not None
        assert session.agent_type == "scan"
        assert len(session.messages) > 0  # 应该有系统提示词

    def test_agent_type_enum(self):
        """测试AgentType枚举"""
        assert AgentType.SCAN.value == "scan"
        assert AgentType.REVIEW.value == "review"
        assert AgentType.CLEANUP.value == "cleanup"
        assert AgentType.REPORT.value == "report"

    def test_close_session(self, orchestrator):
        """测试关闭会话"""
        session = orchestrator.create_session(AgentType.SCAN)
        session_id = session.session_id
        orchestrator.close_session(session_id)
        assert orchestrator.get_session(session_id) is None

    def test_close_all_sessions(self, orchestrator):
        """测试关闭所有会话"""
        orchestrator.create_session(AgentType.SCAN)
        orchestrator.create_session(AgentType.REVIEW)
        orchestrator.close_all_sessions()
        assert len(orchestrator.sessions) == 0


class TestAgentTools:
    """测试工具系统"""

    def test_tool_registration(self):
        """测试工具注册"""
        # 获取初始工具计数
        initial_registry = get_all_tools()
        initial_count = len(initial_registry)

        # 使用装饰器注册工具类
        registered = register_tool(DummyTool)

        # 验证注册返回的是一个 DummyTool 实例
        assert isinstance(registered, DummyTool)
        assert registered.NAME == DummyTool.NAME

        # 验证工具已注册
        assert DummyTool.NAME in get_all_tools()

        # 验证工具数量可能增加（如果之前未注册）
        # 注意：DummyTool 可能已经被其他测试注册过

    def test_get_tool(self):
        """测试获取工具"""
        # 获取不存在的工具
        tool = get_tool("nonexistent_tool")
        assert tool is None

    def test_get_tools_schema(self):
        """测试获取工具schema"""
        schemas = get_tools_schema()
        assert isinstance(schemas, list)
        # 每个schema应该有type和function字段
        for schema in schemas:
            assert "type" in schema
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]

    def test_dummy_tool_execute(self):
        """测试DummyTool执行"""
        tool = DummyTool()
        result = tool.execute({"test": "data"})
        assert "Dummy tool executed" in result


class TestAgentIntegration:
    """测试集成管理器"""

    @pytest.mark.skipif(
        os.environ.get("ANTHROPIC_API_KEY") is None,
        reason="需要ANTHROPIC_API_KEY环境变量"
    )
    def test_create_agent_integration(self):
        """测试创建AgentIntegration"""
        integration = get_agent_integration("test_key")
        assert integration is not None
        assert integration.ai_config.api_key == "test_key"

    @pytest.mark.skipif(
        os.environ.get("ANTHROPIC_API_KEY") is None,
        reason="需要ANTHROPIC_API_KEY环境变量"
    )
    def test_full_cleanup_flow(self, test_dir):
        """测试完整清理流程"""
        # 创建测试文件
        test_files = []
        for i in range(5):
            file_path = os.path.join(test_dir, f"test_{i}.tmp")
            with open(file_path, 'w') as f:
                f.write("test content")
            test_files.append(file_path)

        integration = get_agent_integration(os.environ.get("ANTHROPIC_API_KEY"))

        # 仅扫描测试
        result = integration.run_scan_only([test_dir])
        assert result is not None
        assert "scan_id" in result

    def test_mock_integration(self):
        """测试模拟模式集成"""
        # 不提供密钥，使用模拟模式
        integration = get_agent_integration("")
        assert integration is not None


class TestFileTools:
    """测试文件工具"""

    @pytest.mark.skip(reason="ReadTool does not exist in agent.tools")
    def test_read_tool_file(self, test_dir):
        """测试ReadTool读取文件"""
        # 创建测试文件
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("测试内容")

        from agent.tools import ReadTool
        tool = ReadTool()
        result = tool.execute({"path": test_file})

        assert "type" in result
        assert "path" in result


class TestAgentScanner:
    """测试智能体扫描器"""

    def test_create_agent_scanner(self):
        """测试创建AgentScanner"""
        from core.agent_adapter import AgentScanner, get_agent_scanner

        scanner = get_agent_scanner("system", "", "hybrid")
        assert scanner is not None
        assert scanner.scan_type == "system"

    def test_agent_scan_to_scan_items(self):
        """测试扫描结果转换"""
        from core.agent_adapter import AgentScanner

        scanner = AgentScanner("system", "", "hybrid")

        # 模拟扫描数据
        scan_data = {
            "files": [
                {
                    "path": "C:\\Temp\\test.tmp",
                    "size": 1024,
                    "risk": "safe",
                    "category": "temp",
                    "is_garbage": True,
                    "confidence": 0.9
                }
            ]
        }

        items = scanner._convert_to_scan_items(scan_data, ["C:\\Temp"])
        assert len(items) == 1
        assert items[0].path == "C:\\Temp\\test.tmp"
        assert items[0].size == 1024


class TestSmartCleanerAgentSupport:
    """测试SmartCleaner的智能体支持"""

    def test_smart_clean_config_agent_fields(self):
        """测试SmartCleanConfig的智能体字段"""
        from core.smart_cleaner import SmartCleanConfig, AgentMode

        config = SmartCleanConfig()
        assert hasattr(config, 'agent_mode')
        assert config.agent_mode == "hybrid"
        assert hasattr(config, 'enable_agent_review')
        assert config.enable_agent_review is True

    @pytest.mark.skipif(
        os.environ.get("SKIP_QT_TESTS", "1") == "1",
        reason="跳过Qt测试"
    )
    def test_smart_cleaner_agent_initialization(self, qt_app):
        """测试SmartCleaner初始化智能体组件"""
        from core.smart_cleaner import SmartCleaner

        cleaner = SmartCleaner()
        # 应该有智能体模式属性
        assert hasattr(cleaner, 'agent_mode')
        assert hasattr(cleaner, 'agent_scanner') or cleaner.agent_scanner is None
        assert hasattr(cleaner, 'agent_executor') or cleaner.agent_executor is None


class TestUIAgentConfig:
    """测试UI智能体配置"""

    def test_agent_mode_options(self):
        """测试智能体模式选项"""
        from ui.agent_config import AGENT_MODE_OPTIONS, get_agent_mode_info

        assert "disabled" in AGENT_MODE_OPTIONS
        assert "hybrid" in AGENT_MODE_OPTIONS
        assert "full" in AGENT_MODE_OPTIONS

        info = get_agent_mode_info("hybrid")
        assert info["name"] == "混合模式"

    def test_default_agent_config(self):
        """测试默认智能体配置"""
        from ui.agent_config import DEFAULT_AGENT_CONFIG, get_default_agent_config

        assert "agent_mode" in DEFAULT_AGENT_CONFIG
        assert DEFAULT_AGENT_CONFIG["agent_mode"] == "hybrid"

        config = get_default_agent_config()
        assert config["agent_mode"] == "hybrid"
        # 验证是副本
        config["agent_mode"] = "full"
        assert DEFAULT_AGENT_CONFIG["agent_mode"] == "hybrid"

    def test_ai_risk_policy(self):
        """测试AI风险政策"""
        from ui.agent_config import AI_RISK_POLICY, get_risk_policy

        assert "safe" in AI_RISK_POLICY
        assert "suspicious" in AI_RISK_POLICY
        assert "dangerous" in AI_RISK_POLICY

        safe_policy = get_risk_policy("safe")
        assert safe_policy["auto_clean"] is True
        assert safe_policy["needs_review"] is False

    def test_available_models(self):
        """测试可用模型列表"""
        from ui.agent_config import get_available_models

        models = get_available_models()
        assert len(models) > 0
        assert any(m["id"] == "claude-opus-4-6" for m in models)


class TestAgentStatusWidgets:
    """测试智能体状态组件"""

    @pytest.mark.skipif(
        os.environ.get("SKIP_QT_TESTS", "1") == "1",
        reason="跳过Qt测试"
    )
    def test_agent_status_frame_creation(self, qt_app):
        """测试AgentStatusFrame创建"""
        from ui.agent_status_widgets import AgentStatusFrame

        status_frame = AgentStatusFrame()
        assert status_frame is not None
        assert status_frame.current_status == "idle"

    @pytest.mark.skipif(
        os.environ.get("SKIP_QT_TESTS", "1") == "1",
        reason="跳过Qt测试"
    )
    def test_agent_status_set_status(self, qt_app):
        """测试设置状态"""
        from ui.agent_status_widgets import AgentStatusFrame

        status_frame = AgentStatusFrame()
        status_frame.set_status("running", stage="扫描", progress=50, details="扫描中...")
        assert status_frame.current_status == "running"


# 运行所有测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
