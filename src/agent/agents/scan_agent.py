# -*- coding: utf-8 -*-
"""
扫描智能体 - Scan Agent

负责扫描文件系统，识别垃圾文件并生成清理计划
"""
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..orchestrator import AgentOrchestrator, AgentType
from ..models_agent import AgentSession
from utils.logger import get_logger

logger = get_logger(__name__)


class ScanAgent:
    """扫描智能体

    工作流程：
    1. 使用 Glob 工具搜索已知垃圾文件模式
    2. 使用 Read/Ls 工具验证发现的文件
    3. 使用 Grep 工具分析文件内容（如需要）
    4. AI 分析并生成清理计划
    """

    def __init__(self, orchestrator: AgentOrchestrator):
        """初始化扫描智能体

        Args:
            orchestrator: 编排器实例
        """
        self.orchestrator = orchestrator
        self.agent_type = AgentType.SCAN

        # 已知的垃圾文件模式
        self.known_patterns = {
            "temp_files": [
                "*.tmp", "*.temp", "*~", "*.bak", "*.old", "*.swp"
            ],
            "cache_files": [
                "*cache*", "GPUCache", "Code Cache", "*Cache*"
            ],
            "log_files": [
                "*.log", "*.trace", "*.out", "*.dmp"
            ],
            "system_junk": [
                "Thumbs.db", "desktop.ini", ".DS_Store"
            ]
        }

        logger.info(f"[SCAN_AGENT] 初始化扫描智能体")

    def scan(
        self,
        scan_paths: List[str],
        scan_patterns: Optional[List[str]] = None,
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行扫描任务

        Args:
            scan_paths: 扫描路径列表
            scan_patterns: 扫描模式（如 ["temp_files", "cache_files"]）
            workspace: 工作目录

        Returns:
            扫描结果
        """
        # 创建会话
        session_id = self.orchestrator.create_session(
            AgentType.SCAN,
            workspace=workspace,
            metadata={"scan_paths": scan_paths}
        )

        # 构建扫描请求
        scan_request = self._build_scan_request(scan_paths, scan_patterns)

        logger.info(f"[SCAN_AGENT] 开始扫描: {scan_paths}")

        # 运行智能体循环
        try:
            result = self.orchestrator.run_agent_loop(
                AgentType.SCAN,
                scan_request,
                workspace=workspace,
                max_turns=30  # 扫描任务可能需要更多轮次
            )

            # 解析结果
            scan_result = self._parse_scan_result(result)

            logger.info(f"[SCAN_AGENT] 扫描完成: 发现 {len(scan_result.get('files', []))} 个文件")
            return scan_result

        except Exception as e:
            logger.error(f"[SCAN_AGENT] 扫描失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": session_id.session_id
            }

    def _build_scan_request(
        self,
        scan_paths: List[str],
        scan_patterns: Optional[List[str]]
    ) -> str:
        """构建扫描请求消息

        Args:
            scan_paths: 扫描路径
            scan_patterns: 扫描模式

        Returns:
            扫描请求文本
        """
        # 默认使用全部模式
        if not scan_patterns:
            scan_patterns = list(self.known_patterns.keys())

        request_parts = [
            "# 扫描任务",
            "",
            f"## 扫描路径",
            ", ".join(scan_paths),
            "",
            f"## 扫描模式",
        ]

        for pattern_type in scan_patterns:
            patterns = self.known_patterns.get(pattern_type, [])
            request_parts.append(f"- {pattern_type}: {', '.join(patterns)}")

        request_parts.extend([
            "",
            "## 任务要求",
            "1. 使用 Glob 工具按模式搜索文件",
            "2. 使用 Read/Ls 工具验证发现的文件",
            "3. 对每个文件进行风险评估 (safe/suspicious/dangerous)",
            "4. 生成清理计划（JSON 格式）",
        ])

        return "\n".join(request_parts)

    def _parse_scan_result(self, agent_result: Dict[str, Any]) -> Dict[str, Any]:
        """解析智能体扫描结果

        Args:
            agent_result: 智能体执行结果

        Returns:
            解析后的扫描结果
        """
        result = {
            "success": agent_result.get("is_complete", False),
            "scan_id": agent_result.get("session_id"),
            "files": [],
            "summary": {
                "total_files": 0,
                "garbage_files": 0,
                "total_size": 0,
                "scan_duration": 0
            }
        }

        # 解析响应内容，查找 JSON 格式的扫描结果
        full_response = "\n".join(agent_result.get("responses", []))

        try:
            # 尝试提取 JSON 结果
            import re

            # 查找 JSON 代码块
            json_match = re.search(r'```json\s*({.*?})\s*```', full_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                scan_data = json.loads(json_str)

                if "files" in scan_data:
                    result["files"] = scan_data["files"]
                    result["summary"] = scan_data.get("summary", result["summary"])
                else:
                    result["success"] = False
                    result["error"] = "未找到 files 字段"

            else:
                # 尝试直接解析整个响应为 JSON
                try:
                    scan_data = json.loads(full_response.strip())
                    if "files" in scan_data:
                        result["files"] = scan_data["files"]
                        result["summary"] = scan_data.get("summary", result["summary"])
                except json.JSONDecodeError:
                    # 无法解析 JSON，记录原始响应
                    result["raw_response"] = full_response
                    result["error"] = "无法解析 JSON 格式的扫描结果"

        except Exception as e:
            logger.warning(f"[SCAN_AGENT] 解析结果失败: {e}")
            result["error"] = str(e)
            result["raw_response"] = full_response

        # 统计摘要
        files = result.get("files", [])
        result["summary"]["total_files"] = len(files)
        result["summary"]["garbage_files"] = sum(
            1 for f in files if f.get("is_garbage", False)
        )
        result["summary"]["total_size"] = sum(
            f.get("size", 0) for f in files
        )

        return result

    def quick_scan(self, path: str) -> Dict[str, Any]:
        """快速扫描单个路径

        Args:
            path: 扫描路径

        Returns:
            扫描结果
        """
        return self.scan(
            scan_paths=[path],
            scan_patterns=["temp_files", "system_junk"],
            workspace=None
        )
