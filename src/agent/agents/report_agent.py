# -*- coding: utf-8 -*-
"""
报告智能体 - Report Agent

负责生成清理操作报告
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..orchestrator import AgentOrchestrator, AgentType
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportAgent:
    """报告智能体

    工作流程：
    1. 收集清理操作数据
    2. 分析统计数据
    3. 生成结构化报告
    4. 格式化输出
    """

    def __init__(self, orchestrator: AgentOrchestrator):
        """初始化报告智能体

        Args:
            orchestrator: 编排器实例
        """
        self.orchestrator = orchestrator
        self.agent_type = AgentType.REPORT

        logger.info(f"[REPORT_AGENT] 初始化报告智能体")

    def generate_report(
        self,
        scan_result: Dict[str, Any],
        cleanup_result: Dict[str, Any],
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成清理报告

        Args:
            scan_result: 扫描结果
            cleanup_result: 清理结果

        Returns:
            生成的报告
        """
        logger.info(f"[REPORT_AGENT] 生成报告")

        # 基础报告数据
        report = {
            "report_id": f"report_{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "scan_type": scan_result.get("scan_type", "system"),
            "status": "completed",
        }

        # 执行摘要
        report["summary"] = self._generate_summary(scan_result, cleanup_result)

        # 统计信息
        report["statistics"] = self._generate_statistics(scan_result, cleanup_result)

        # 失败分析
        report["failures"] = self._analyze_failures(cleanup_result)

        # 优化建议
        report["recommendations"] = self._generate_recommendations(
            scan_result, cleanup_result
        )

        return report

    def _generate_summary(
        self,
        scan_result: Dict[str, Any],
        cleanup_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成执行摘要

        Args:
            scan_result: 扫描结果
            cleanup_result: 清理结果

        Returns:
            执行摘要
        """
        scan_summary = scan_result.get("summary", {})
        total_planned = cleanup_result.get("total_planned", 0)
        deleted_count = cleanup_result.get("deleted_count", 0)
        failed_count = cleanup_result.get("failed_count", 0)
        success_rate = cleanup_result.get("success_rate", 0.0)

        return {
            "scan_type": scan_result.get("scan_type", "unknown"),
            "total_scanned": scan_summary.get("total_files", 0),
            "total_planned": total_planned,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "success_rate": round(success_rate * 100, 2),
            "total_freed_bytes": cleanup_result.get("total_freed_bytes", 0),
            "is_dry_run": cleanup_result.get("is_dry_run", False)
        }

    def _generate_statistics(
        self,
        scan_result: Dict[str, Any],
        cleanup_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成统计信息

        Args:
            scan_result: 扫描结果
            cleanup_result: 清理结果

        Returns:
            统计信息
        """
        # 按类型统计
        files = scan_result.get("files", [])
        type_stats = {}
        size_stats = {}

        for file_info in files:
            category = file_info.get("category", "unknown")
            size = file_info.get("size", 0)
            risk = file_info.get("risk", "unknown")

            # 类型统计
            type_stats[category] = type_stats.get(category, 0) + 1

            # 大小统计
            if category not in size_stats:
                size_stats[category] = 0
            size_stats[category] += size

        # 文件大小分布
        size_distribution = {
            "< 100 KB": 0,
            "100 KB - 1 MB": 0,
            "1 MB - 10 MB": 0,
            "> 10 MB": 0
        }

        for file_info in files:
            size = file_info.get("size", 0)
            if size < 100 * 1024:
                size_distribution["< 100 KB"] += 1
            elif size < 1 * 1024 * 1024:
                size_distribution["100 KB - 1 MB"] += 1
            elif size < 10 * 1024 * 1024:
                size_distribution["1 MB - 10 MB"] += 1
            else:
                size_distribution["> 10 MB"] += 1

        # 风险等级分布
        risk_distribution = {"safe": 0, "suspicious": 0, "dangerous": 0}
        for file_info in files:
            risk = file_info.get("risk", "unknown").lower()
            if risk in risk_distribution:
                risk_distribution[risk] += 1

        # 目录分布（提取父目录）
        dir_distribution = {}
        for file_info in files[:100]:  # 限制数量
            path = file_info.get("path", "")
            parent = str(Path(path).parent)
            dir_distribution[parent] = dir_distribution.get(parent, 0) + 1

        # 取前 10 个目录
        top_dirs = sorted(
            dir_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "files_by_type": type_stats,
            "space_by_type": size_stats,
            "size_distribution": size_distribution,
            "risk_distribution": risk_distribution,
            "top_directories": [{"path": d[0], "count": d[1]} for d in top_dirs]
        }

    def _analyze_failures(self, cleanup_result: Dict[str, Any]) -> Dict[str, Any]:
        """分析失败项

        Args:
            cleanup_result: 清理结果

        Returns:
            失败分析
        """
        failed_files = cleanup_result.get("failed_files", [])

        # 按错误类型分类
        error_types = {}
        for fail in failed_files:
            error_type = fail.get("error_type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # 前 10 个失败项
        top_failures = failed_files[:10]

        return {
            "total_failures": len(failed_files),
            "error_types": error_types,
            "top_failures": top_failures
        }

    def _generate_recommendations(
        self,
        scan_result: Dict[str, Any],
        cleanup_result: Dict[str, Any]
    ) -> List[str]:
        """生成优化建议

        Args:
            scan_result: 扫描结果
            cleanup_result: 清理结果

        Returns:
            建议列表
        """
        recommendations = []

        # 检查失败率
        success_rate = cleanup_result.get("success_rate", 0)
        if success_rate < 0.8:
            recommendations.append(
                f"成功率较低 ({success_rate*100:.1f}%)，建议检查失败的项是否为系统关键文件"
            )

        # 检查 locked 文件
        failed_files = cleanup_result.get("failed_files", [])
        locked_count = sum(
            1 for f in failed_files
            if f.get("error_type") == "file_in_use"
        )
        if locked_count > 0:
            recommendations.append(
                f"发现 {locked_count} 个文件被占用，建议关闭相关程序后重试"
            )

        # 检查权限问题
        permission_count = sum(
            1 for f in failed_files
            if f.get("error_type") == "permission_denied"
        )
        if permission_count > 0:
            recommendations.append(
                f"发现 {permission_count} 个权限不足项，可能需要管理员权限"
            )

        # 检查大量小文件
        files = scan_result.get("files", [])
        small_files = sum(1 for f in files if f.get("size", 0) < 10 * 1024)
        if small_files > len(files) * 0.7:
            recommendations.append(
                "大量小文件，建议考虑批量清理策略"
            )

        # 检查大文件
        large_files = [f for f in files if f.get("size", 0) > 100 * 1024 * 1024]
        if large_files:
            size_str = self._format_bytes(large_files[0].get("size", 0))
            recommendations.append(
                f"发现大于100MB的文件 ({len(large_files)} 个)，建议特别确认"
            )

        if not recommendations:
            recommendations.append("清理操作完成，未发现需要特别注意的问题")

        return recommendations

    def _format_bytes(self, bytes_size: int) -> str:
        """格式化字节数

        Args:
            bytes_size: 字节数

        Returns:
            格式化字符串
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.2f} PB"

    def format_report_as_markdown(self, report: Dict[str, Any]) -> str:
        """将报告格式化为 Markdown

        Args:
            report: 报告数据

        Returns:
            Markdown 格式字符串
        """
        lines = []

        lines.append("# 清理操作报告\n")

        # 摘要
        summary = report.get("summary", {})
        lines.append("## 执行摘要\n")
        lines.append(f"- 扫描类型: **{summary.get('scan_type', 'unknown')}**")
        lines.append(f"- 总扫描数: **{summary.get('total_scanned', 0)}**")
        lines.append(f"- 计划清理: **{summary.get('total_planned', 0)}**")
        lines.append(f"- 实际清理: **{summary.get('deleted_count', 0)}**")
        lines.append(f"- 失败项: **{summary.get('failed_count', 0)}**")
        lines.append(f"- 成功率: **{summary.get('success_rate', 0)}%**")
        lines.append(f"- 释放空间: **{self._format_bytes(summary.get('total_freed_bytes', 0))}**\n")

        # 统计
        stats = report.get("statistics", {})
        lines.append("## 统计信息\n")

        type_stats = stats.get("files_by_type", {})
        if type_stats:
            lines.append("### 按类型统计\n")
            lines.append("| 类型 | 数量 |")
            lines.append("|------|------|")
            for category, count in type_stats.items():
                lines.append(f"| {category} | {count} |")
            lines.append("")

        # 失败分析
        failures = report.get("failures", {})
        if failures.get("total_failures", 0) > 0:
            lines.append("## 失败分析\n")
            lines.append(f"总失败数: **{failures['total_failures']}**\n")

            error_types = failures.get("error_types", {})
            if error_types:
                lines.append("### 错误类型分布\n")
                lines.append("| 错误类型 | 数量 |")
                lines.append("|---------|------|")
                for error_type, count in error_types.items():
                    lines.append(f"| {error_type} | {count} |")
                lines.append("")

            top_failures = failures.get("top_failures", [])
            if top_failures:
                lines.append("### 前 10 个失败项\n")
                lines.append("| 路径 | 错误 |")
                lines.append("|------|------|")
                for fail in top_failures[:10]:
                    lines.append(f"| {fail.get('path', '')[:50]} | {fail.get('error', '')[:50]} |")
                lines.append("")

        # 建议
        recommendations = report.get("recommendations", [])
        if recommendations:
            lines.append("## 优化建议\n")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # 元数据
        lines.append("---\n")
        lines.append(f"生成时间: {report.get('generated_at', '')}\n")

        return "\n".join(lines)
