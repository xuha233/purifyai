# -*- coding: utf-8 -*-
"""
审查智能体 - Review Agent

负责审查清理计划的安全性，防止误删重要文件
"""
import json
from typing import Dict, List, Any, Optional

from ..orchestrator import AgentOrchestrator, AgentType
from utils.logger import get_logger

logger = get_logger(__name__)


class ReviewAgent:
    """审查智能体

    工作流程：
    1. 分析清理计划中的文件路径
    2. 识别敏感路径和危险文件
    3. 评估风险并标记需要用户确认的项目
    4. 生成审查报告
    """

    def __init__(self, orchestrator: AgentOrchestrator):
        """初始化审查智能体

        Args:
            orchestrator: 编排器实例
        """
        self.orchestrator = orchestrator
        self.agent_type = AgentType.REVIEW

        # 危险关键词
        self.dangerous_paths = [
            r"C:\\Windows", r"C:\\Program Files", r"C:\\ProgramData",
            r"/windows/", r"/system/", r"/program/", r"/program files", r"/programdata"
        ]

        self.user_paths = [
            "/users/", "/home/", "/documents", "/downloads", "/desktop",
            "/pictures", "/videos", "/music",
            "C:\\Users\\", "C:\\Documents and Settings\\"
        ]

        self.executable_extensions = [
            ".exe", ".dll", ".sys", ".bin", ".bat", ".cmd", ".ps1", ".vbs"
        ]

        self.data_extensions = [
            ".db", ".sqlite", ".mdb", ".accdb", ".json", ".xml", ".yaml", ".toml",
            "_vsc", ".suo", ".csproj", ".xcodepro"
        ]

        logger.info(f"[REVIEW_AGENT] 初始化审查智能体")

    def review_cleanup_plan(
        self,
        cleanup_items: List[Dict[str, Any]],
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """审查清理计划

        Args:
            cleanup_items: 清理项目列表
            workspace: 工作目录

        Returns:
            审查结果
        """
        # 创建会话
        session = self.orchestrator.create_session(
            AgentType.REVIEW,
            workspace=workspace,
            metadata={"items_count": len(cleanup_items)}
        )

        # 构建审查请求
        review_request = self._build_review_request(cleanup_items)

        logger.info(f"[REVIEW_AGENT] 开始审查: {len(cleanup_items)} 个项目")

        try:
            # 运行智能体循环
            result = self.orchestrator.run_agent_loop(
                AgentType.REVIEW,
                review_request,
                workspace=workspace,
                max_turns=10  # 审查任务通常较快
            )

            # 解析审查结果
            review_result = self._parse_review_result(result, cleanup_items)

            logger.info(f"[REVIEW_AGENT] 审查完成: "
                       f"阻断 {len(review_result.get('blocked_items', []))} 项")
            return review_result

        except Exception as e:
            logger.error(f"[REVIEW_AGENT] 审查失败: {e}")
            return {
                "safe_to_proceed": False,
                "error": str(e),
                "reason": "审查过程出错"
            }

    def _build_review_request(self, cleanup_items: List[Dict[str, Any]]) -> str:
        """构建审查请求

        Args:
            cleanup_items: 清理项目列表

        Returns:
            审查请求文本
        """
        # 限制显示的项目数量
        display_items = cleanup_items[:100]

        request_parts = [
            "# 任务",
            "",
            "请审查以下清理计划的安全性，确定是否可以安全执行。",
            "",
            "## 清理项目",
            "",
            f"总项目数: {len(cleanup_items)} (显示前 {len(display_items)} 项)",
            ""
        ]

        # 添加项目列表
        for i, item in enumerate(display_items, 1):
            path = item.get("path", "")
            size = item.get("size", 0)
            risk_level = item.get("risk", "unknown")

            request_parts.append(f"{i}. {path}")
            request_parts.append(f"   大小: {size:,} 字节, 风险: {risk_level}")

        request_parts.extend([
            "",
            "## 审查要求",
            "1. 检查路径是否在系统关键目录",
            "2. 检查文件扩展名（可执行文件、数据文件）",
            "3. 评估整体风险",
            "4. 返回 JSON 格式的审查结果",
            "",
            "## 输出格式",
            '```json',
            '{',
            '  "safe_to_proceed": true,',
            '  "blocked_items": [',
            '    {"path": "path1", "reason": "原因"},',
            '    {"path": "path2", "reason": "原因"}',
            '  ],',
            '  "warnings": ["警告1", "警告2"],',
            '  "items_to_review": [',
            '    {"path": "path3", "reason": "原因"}',
            '  ],',
            '  "reason": "总体评估说明"',
            '}',
            '```'
        ])

        return "\n".join(request_parts)

    def _parse_review_result(
        self,
        agent_result: Dict[str, Any],
        original_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """解析智能体审查结果

        Args:
            agent_result: 智能体执行结果
            original_items: 原始清理项目列表

        Returns:
            解析后的审查结果
        """
        result = {
            "safe_to_proceed": True,
            "blocked_items": [],
            "warnings": [],
            "items_to_review": [],
            "reason": ""
        }

        full_response = "\n".join(agent_result.get("responses", []))

        try:
            import re

            # 查找 JSON 代码块
            json_match = re.search(r'```json\s*({.*?})\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                review_data = json.loads(json_str)

                result.update(review_data)
            else:
                # 尝试直接解析
                try:
                    review_data = json.loads(full_response.strip())
                    result.update(review_data)
                except json.JSONDecodeError:
                    result["reason"] = "无法解析审查结果，原始响应见 raw_response"
                    result["raw_response"] = full_response

        except Exception as e:
            logger.warning(f"[REVIEW_AGENT] 解析结果失败: {e}")
            result["safe_to_proceed"] = False
            result["reason"] = f"解析失败: {str(e)}"
            result["raw_response"] = full_response

        # 添加原始项目计数
        result["total_items"] = len(original_items)
        result["blocked_count"] = len(result.get("blocked_items", []))
        result["review_count"] = len(result.get("items_to_review", []))

        # 如果有大数量文件，建议分批处理
        if result["safe_to_proceed"] and len(original_items) > 500:
            result["batch_recommended"] = True
            result["batch_size"] = 100
            if not result["warnings"]:
                result["warnings"] = []
            result["warnings"].append(f"项目数量较多 ({len(original_items)})，建议分批处理")

        return result

    def quick_review(self, item_path: str) -> str:
        """快速审查单个项目

        Args:
            item_path: 项目路径

        Returns:
            风险等级: safe/suspicious/dangerous
        """
        path_lower = item_path.lower()

        # 检查危险路径
        for dangerous in self.dangerous_paths:
            if dangerous.lower() in path_lower:
                return "dangerous"

        # 检查用户数据路径
        for user_path in self.user_paths:
            if user_path.lower() in path_lower:
                return "suspicious"

        # 检查可执行文件
        for ext in self.executable_extensions:
            if path_lower.endswith(ext):
                return "suspicious"

        # 检查数据文件
        for ext in self.data_extensions:
            if path_lower.endswith(ext):
                return "suspicious"

        return "safe"
