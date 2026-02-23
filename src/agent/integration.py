# -*- coding: utf-8 -*-
"""
Agent 集成辅助模块

提供智能体与 PurifyAI 现有系统的集成接口
"""
from typing import Dict, List, Any, Optional
import json
import os

from . import (
    get_orchestrator, AgentType,
    create_scan_agent, create_review_agent,
    create_cleanup_agent, create_report_agent,
    AIConfig
)
from .orchestrator import AIConfig as OrchestratorAIConfig
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_app_config() -> Dict[str, Any]:
    """获取应用配置

    Returns:
        配置字典
    """
    # 首先尝试从环境变量获取
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = os.environ.get("AI_MODEL", "claude-opus-4-6")
    max_tokens = int(os.environ.get("AI_MAX_TOKENS", "8192"))
    temperature = float(os.environ.get("AI_TEMPERATURE", "0.7"))

    # 尝试读取配置文件（如果存在）
    config_paths = [
        "config.json",
        "./config/config.json",
        "~/.purifyai/config.json",
    ]

    for config_path in config_paths:
        expanded = os.path.expanduser(config_path)
        if os.path.exists(expanded):
            try:
                with open(expanded, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    return {
                        "ai": {
                            "api_key": file_config.get("ai", {}).get("api_key", api_key),
                            "model": file_config.get("ai", {}).get("model", model),
                            "max_tokens": file_config.get("ai", {}).get("max_tokens", max_tokens),
                            "temperature": file_config.get("ai", {}).get("temperature", temperature),
                        }
                    }
            except Exception as e:
                logger.warning(f"[AGENT_INTEGRATION] 读取配置文件失败 {expanded}: {e}")

    # 返回默认配置
    return {
        "ai": {
            "api_key": api_key,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    }


class AgentIntegration:
    """Agent 集成管理器

    协调各个智能体完成完整的清理流程：
    1. Scan Agent 扫描垃圾文件
    2. Review Agent 审查清理计划安全性
    3. Cleanup Agent 执行清理
    4. Report Agent 生成报告
    """

    def __init__(self, api_key: Optional[str] = None):
        """初始化集成管理器

        Args:
            api_key: AI API 密钥
        """
        # 从配置加载 API 密钥
        config = _get_app_config()
        ai_key = api_key or config.get("ai", {}).get("api_key", "")

        self.ai_config: AIConfig = OrchestratorAIConfig(
            api_key=ai_key,
            model=config.get("ai", {}).get("model", "claude-opus-4-6"),
            max_tokens=config.get("ai", {}).get("max_tokens", 8192),
            temperature=config.get("ai", {}).get("temperature", 0.7)
        )

        self.orchestrator = get_orchestrator(self.ai_config)
        self.scan_agent = create_scan_agent(self.orchestrator)
        self.review_agent = create_review_agent(self.orchestrator)
        self.cleanup_agent = create_cleanup_agent(self.orchestrator)
        self.report_agent = create_report_agent(self.orchestrator)

        logger.info("[AGENT_INTEGRATION] 集成管理器初始化完成")

    def run_full_cleanup(
        self,
        scan_paths: List[str],
        scan_patterns: Optional[List[str]] = None,
        is_dry_run: bool = True,
        skip_review: bool = False
    ) -> Dict[str, Any]:
        """运行完整清理流程

        Args:
            scan_paths: 扫描路径列表
            scan_patterns: 扫描模式
            is_dry_run: 是否为演练模式
            skip_review: 是否跳过审查

        Returns:
            完整流程结果
        """
        result = {
            "success": False,
            "stage": "init",
            "scan_result": None,
            "review_result": None,
            "cleanup_result": None,
            "report": None,
            "error": None
        }

        try:
            logger.info(f"[AGENT_INTEGRATION] 开始完整清理流程: {scan_paths}")

            # 阶段 1: 扫描
            result["stage"] = "scan"
            logger.info("[AGENT_INTEGRATION] 阶段 1/4: 扫描")
            scan_result = self.scan_agent.scan(
                scan_paths=scan_paths,
                scan_patterns=scan_patterns
            )
            result["scan_result"] = scan_result

            if not scan_result.get("success", False):
                result["error"] = "扫描阶段失败"
                return result

            # 提取要清理的项目
            cleanup_items = [
                {"path": f.get("path"), "type": "file", "size": f.get("size", 0)}
                for f in scan_result.get("files", [])
                if f.get("is_garbage", False)
            ]

            # 过滤掉 dangerous 级别的文件
            cleanup_items = [
                item for item in cleanup_items
                if any(f.get("path") == item["path"] and f.get("risk") != "dangerous"
                       for f in scan_result.get("files", []))
            ]

            if not cleanup_items:
                result["error"] = "没有找到可清理的文件"
                return result

            logger.info(f"[AGENT_INTEGRATION] 发现 {len(cleanup_items)} 个可清理项目")

            # 阶段 2: 审查
            result["stage"] = "review"
            if not skip_review:
                logger.info("[AGENT_INTEGRATION] 阶段 2/4: 审查")
                review_result = self.review_agent.review_cleanup_plan(cleanup_items)
                result["review_result"] = review_result

                if not review_result.get("safe_to_proceed", True):
                    result["error"] = f"审查未通过: {review_result.get('reason')}"
                    return result

                # 移除被阻断的项目
                blocked_paths = {f.get("path") for f in review_result.get("blocked_items", [])}
                cleanup_items = [item for item in cleanup_items if item["path"] not in blocked_paths]
                logger.info(f"[AGENT_INTEGRATION] 审查通过，可清理 {len(cleanup_items)} 个项目")
            else:
                logger.info("[AGENT_INTEGRATION] 跳过审查")

            # 阶段 3: 清理
            result["stage"] = "cleanup"
            logger.info("[AGENT_INTEGRATION] 阶段 3/4: 清理")
            cleanup_result = self.cleanup_agent.execute_cleanup(
                cleanup_items=cleanup_items,
                is_dry_run=is_dry_run
            )
            result["cleanup_result"] = cleanup_result

            # 阶段 4: 报告
            result["stage"] = "report"
            logger.info("[AGENT_INTEGRATION] 阶段 4/4: 生成报告")
            report = self.report_agent.generate_report(
                scan_result=scan_result,
                cleanup_result=cleanup_result
            )
            result["report"] = report

            result["success"] = True
            result["stage"] = "completed"
            logger.info("[AGENT_INTEGRATION] 清理流程完成")

            return result

        except Exception as e:
            logger.error(f"[AGENT_INTEGRATION] 清理流程出错: {e}")
            result["error"] = str(e)
            result["stage"] = "error"
            return result

    def run_scan_only(self, scan_paths: List[str]) -> Dict[str, Any]:
        """仅运行扫描

        Args:
            scan_paths: 扫描路径列表

        Returns:
            扫描结果
        """
        logger.info(f"[AGENT_INTEGRATION] 仅扫描: {scan_paths}")
        return self.scan_agent.scan(scan_paths=scan_paths)

    def run_cleanup_only(
        self,
        cleanup_items: List[Dict[str, Any]],
        is_dry_run: bool = True
    ) -> Dict[str, Any]:
        """仅运行清理

        Args:
            cleanup_items: 清理项目列表
            is_dry_run: 是否为演练模式

        Returns:
            清理结果
        """
        logger.info(f"[AGENT_INTEGRATION] 仅清理: {len(cleanup_items)} 个项目")
        return self.cleanup_agent.execute_cleanup(
            cleanup_items=cleanup_items,
            is_dry_run=is_dry_run
        )

    def generate_report(
        self,
        scan_result: Dict[str, Any],
        cleanup_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成报告

        Args:
            scan_result: 扫描结果
            cleanup_result: 清理结果（可选）

        Returns:
            Markdown 格式报告
        """
        if cleanup_result:
            report = self.report_agent.generate_report(
                scan_result=scan_result,
                cleanup_result=cleanup_result
            )
        else:
            # 创建模拟清理结果
            cleanup_result = {
                "total_planned": scan_result.get("summary", {}).get("total_files", 0),
                "deleted_count": 0,
                "failed_count": 0,
                "failed_files": [],
                "total_freed_bytes": 0,
                "success_rate": 0.0,
                "is_dry_run": True
            }
            report = self.report_agent.generate_report(
                scan_result=scan_result,
                cleanup_result=cleanup_result
            )

        return self.report_agent.format_report_as_markdown(report)


def get_agent_integration(api_key: Optional[str] = None) -> AgentIntegration:
    """获取 Agent 集成管理器实例

    Args:
        api_key: AI API 密钥

    Returns:
        AgentIntegration 实例
    """
    return AgentIntegration(api_key)


# 导出
__all__ = [
    "AgentIntegration",
    "get_agent_integration"
]
