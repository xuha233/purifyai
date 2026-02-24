# -*- coding: utf-8 -*-
"""
清理报告生成器 (Cleanup Report Generator)

Phase A Task 1: 生成清理执行报告

功能:
- 生成清理摘要（统计信息）
- 生成失败项列表
- 生成详细统计数据
- 导出报告为文件（JSON/HTML）
- 恢复记录查询
"""
import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .models_smart import (
    CleanupPlan, ExecutionResult, FailureInfo, RecoveryRecord,
    CleanupItem, RiskLevel, BackupType
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CleanupReport:
    """清理报告

    Attributes:
        plan_id: 清理计划ID
        plan: 清理计划（可选，可能已从数据库移除）
        result: 执行结果
        generated_at: 生成时间
        summary: 摘要信息
        statistics: 统计数据
        failures: 失败项列表
        recovery_records: 恢复记录列表
    """
    plan_id: str
    result: ExecutionResult
    generated_at: datetime = field(default_factory=datetime.now)
    plan: Optional[CleanupPlan] = None
    summary: Dict = field(default_factory=dict)
    statistics: Dict = field(default_factory=dict)
    failures: List[Dict] = field(default_factory=list)
    recovery_records: List[Dict] = field(default_factory=list)


class CleanupReportGenerator:
    """清理报告生成器

    根据清理计划和执行结果生成详细报告
    """

    def __init__(self):
        """初始化报告生成器"""
        self.logger = logger

    def generate_report(
        self,
        plan: Optional[CleanupPlan],
        result: ExecutionResult,
        recovery_records: Optional[List[RecoveryRecord]] = None
    ) -> CleanupReport:
        """
        生成完整的清理报告

        Args:
            plan: 清理计划（可选）
            result: 执行结果
            recovery_records: 恢复记录列表（可选）

        Returns:
            CleanupReport: 清理报告对象
        """
        self.logger.info(f"[REPORT] 生成报告: {result.plan_id}")

        report = CleanupReport(
            plan_id=result.plan_id,
            plan=plan,
            result=result
        )

        # 生成摘要
        report.summary = self.generate_summary(plan, result)

        # 生成统计数据
        report.statistics = self.generate_statistics(result, plan)

        # 生成失败项列表
        report.failures = self.generate_failure_list(result)

        # 添加恢复记录
        if recovery_records:
            report.recovery_records = self._format_recovery_records(recovery_records)

        self.logger.info(f"[REPORT] 报告生成完成: {result.plan_id}")
        return report

    def generate_summary(
        self,
        plan: Optional[CleanupPlan],
        result: ExecutionResult
    ) -> Dict:
        """
        生成报告摘要

        Args:
            plan: 清理计划（可选）
            result: 执行结果

        Returns:
            摘要字典，包含：
            - status: 执行状态
            - duration: 执行时长
            - success_rate: 成功率
            - freed_space: 释放空间（格式化）
            - total_items: 总项目数
            - success_items: 成功项目数
            - failed_items: 失败项目数
            - skipped_items: 跳过项目数
        """
        summary = {
            'plan_id': result.plan_id,
            'status': result.status.get_display_name(),
            'status_value': result.status.value,
            'started_at': result.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': (
                result.completed_at.strftime('%Y-%m-%d %H:%M:%S')
                if result.completed_at
                else '进行中'
            ),
            'duration_seconds': result.duration_seconds,
            'duration_formatted': self._format_duration(result.duration_seconds),
            'success_rate': round(result.success_rate * 100, 2),
            'total_items': result.total_items,
            'success_items': result.success_items,
            'failed_items': result.failed_items,
            'skipped_items': result.skipped_items,
            'total_size': self._format_size(result.total_size),
            'total_size_bytes': result.total_size,
            'freed_size': self._format_size(result.freed_size),
            'freed_size_bytes': result.freed_size,
            'failed_size': self._format_size(result.failed_size),
            'failed_size_bytes': result.failed_size,
        }

        # 如果有计划信息，添加风险分类统计
        if plan:
            summary.update({
                'scan_type': plan.scan_type,
                'scan_target': plan.scan_target,
                'safe_count': plan.safe_count,
                'suspicious_count': plan.suspicious_count,
                'dangerous_count': plan.dangerous_count,
                'ai_model': plan.ai_model,
                'ai_call_count': plan.ai_call_count,
                'used_rule_engine': plan.used_rule_engine,
                'plan_created_at': plan.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        return summary

    def generate_statistics(
        self,
        result: ExecutionResult,
        plan: Optional[CleanupPlan] = None
    ) -> Dict:
        """
        生成详细统计数据

        Args:
            result: 执行结果
            plan: 清理计划（可选）

        Returns:
            统计数据字典
        """
        stats = {
            # 执行统计
            'execution': {
                'status': result.status.value,
                'duration_seconds': result.duration_seconds,
                'items_per_second': (
                    result.total_items / result.duration_seconds
                    if result.duration_seconds > 0
                    else 0
                ),
            },
            # 项目统计
            'items': {
                'total': result.total_items,
                'success': result.success_items,
                'failed': result.failed_items,
                'skipped': result.skipped_items,
                'success_rate': round(result.success_rate * 100, 2),
                'failure_rate': round((1 - result.success_rate) * 100, 2),
            },
            # 空间统计
            'space': {
                'total_bytes': result.total_size,
                'total_formatted': self._format_size(result.total_size),
                'freed_bytes': result.freed_size,
                'freed_formatted': self._format_size(result.freed_size),
                'failed_bytes': result.failed_size,
                'failed_formatted': self._format_size(result.failed_size),
                'recovery_rate': round(result.freed_size / result.total_size * 100, 2)
                if result.total_size > 0
                else 0,
            },
            # 失败统计
            'failures': {
                'total_count': len(result.failures),
                'by_type': self._get_failures_by_type(result.failures),
            },
        }

        # 如果有计划，添加风险统计
        if plan:
            stats['risk'] = {
                'safe_count': plan.safe_count,
                'suspicious_count': plan.suspicious_count,
                'dangerous_count': plan.dangerous_count,
                'ai_summary': plan.ai_summary,
            }
            # AI 统计
            stats['ai'] = {
                'model': plan.ai_model or '规则引擎',
                'call_count': plan.ai_call_count,
                'used_rule_engine': plan.used_rule_engine,
                'analyzed_at': (
                    plan.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')
                    if plan.analyzed_at
                    else None
                ),
            }

        return stats

    def generate_failure_list(self, result: ExecutionResult) -> List[Dict]:
        """
        生成失败项列表

        Args:
            result: 执行结果

        Returns:
            失败项字典列表
        """
        failures = []
        for fail_info in result.failures:
            failure_dict = {
                'item_id': fail_info.item.item_id,
                'path': fail_info.item.path,
                'size': self._format_size(fail_info.item.size),
                'size_bytes': fail_info.item.size,
                'item_type': fail_info.item.item_type,
                'risk_level': fail_info.item.ai_risk.value,
                'risk_display': fail_info.item.ai_risk.get_display_name(),
                'error_type': fail_info.error_type,
                'error_type_display': self._format_error_type(fail_info.error_type),
                'error_message': fail_info.error_message,
                'suggested_action': fail_info.suggested_action,
                'suggested_action_display': self._format_suggested_action(fail_info.suggested_action),
                'timestamp': fail_info.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            }
            failures.append(failure_dict)

        return failures

    def has_failures(self, result: ExecutionResult) -> bool:
        """
        检查是否有失败项

        Args:
            result: 执行结果

        Returns:
            是否有失败项
        """
        return len(result.failures) > 0

    def get_failure_count(self, result: ExecutionResult) -> int:
        """
        获取失败项数量

        Args:
            result: 执行结果

        Returns:
            失败项数量
        """
        return len(result.failures)

    def export_to_json(
        self,
        report: CleanupReport,
        file_path: str
    ) -> bool:
        """
        导出报告为 JSON 文件

        Args:
            report: 清理报告
            file_path: 导出文件路径

        Returns:
            是否成功导出
        """
        try:
            # 准备可序列化的数据
            export_data = {
                'metadata': {
                    'plan_id': report.plan_id,
                    'generated_at': report.generated_at.isoformat(),
                    'report_type': 'cleanup_report',
                },
                'summary': report.summary,
                'statistics': report.statistics,
                'failures': report.failures,
                'recovery_records': report.recovery_records,
            }

            # 如果有计划信息，添加
            if report.plan:
                export_data['plan'] = {
                    'plan_id': report.plan.plan_id,
                    'scan_type': report.plan.scan_type,
                    'scan_target': report.plan.scan_target,
                    'total_items': report.plan.total_items,
                    'total_size': report.plan.total_size,
                    'estimated_freed': report.plan.estimated_freed,
                    'safe_count': report.plan.safe_count,
                    'suspicious_count': report.plan.suspicious_count,
                    'dangerous_count': report.plan.dangerous_count,
                    'ai_summary': report.plan.ai_summary,
                    'ai_model': report.plan.ai_model,
                    'ai_call_count': report.plan.ai_call_count,
                    'used_rule_engine': report.plan.used_rule_engine,
                    'created_at': report.plan.created_at.isoformat(),
                    'analyzed_at': (
                        report.plan.analyzed_at.isoformat()
                        if report.plan.analyzed_at
                        else None
                    ),
                }

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"[REPORT] 导出 JSON 报告: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"[REPORT] 导出 JSON 失败: {e}")
            return False

    def export_to_html(
        self,
        report: CleanupReport,
        file_path: str
    ) -> bool:
        """
        导出报告为 HTML 文件

        Args:
            report: 清理报告
            file_path: 导出文件路径

        Returns:
            是否成功导出
        """
        try:
            html_content = self._generate_html_report(report)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.info(f"[REPORT] 导出 HTML 报告: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"[REPORT] 导出 HTML 失败: {e}")
            return False

    def _generate_html_report(self, report: CleanupReport) -> str:
        """生成 HTML 报告内容"""
        summary = report.summary
        stats = report.statistics
        failures = report.failures

        # HTML 模板
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>清理报告 - {report.plan_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 20px;
            color: #333;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card .label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .summary-card .value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        .summary-card.success .value {{
            color: #28a745;
        }}
        .summary-card.warning .value {{
            color: #ffc107;
        }}
        .summary-card.danger .value {{
            color: #dc3545;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .table th, .table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}
        .table tr:hover {{
            background: #f8f9fa;
        }}
        .status-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .status-badge.success {{
            background: #d4edda;
            color: #155724;
        }}
        .status-badge.warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .status-badge.danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧹 清理报告</h1>
            <p>计划 ID: {report.plan_id} | 生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="content">
            <!-- 摘要 -->
            <div class="section">
                <h2 class="section-title">📊 清理摘要</h2>
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="label">执行状态</div>
                        <div class="value"><span class="status-badge {self._get_status_class(summary.get('status_value', ''))}">{summary.get('status', '未知')}</span></div>
                    </div>
                    <div class="summary-card success">
                        <div class="label">成功项目</div>
                        <div class="value">{summary.get('success_items', 0)}</div>
                    </div>
                    <div class="summary-card danger">
                        <div class="label">失败项目</div>
                        <div class="value">{summary.get('failed_items', 0)}</div>
                    </div>
                    <div class="summary-card warning">
                        <div class="label">跳过项目</div>
                        <div class="value">{summary.get('skipped_items', 0)}</div>
                    </div>
                    <div class="summary-card success">
                        <div class="label">释放空间</div>
                        <div class="value">{summary.get('freed_size', '0 B')}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">执行时长</div>
                        <div class="value">{summary.get('duration_formatted', '0s')}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">成功率</div>
                        <div class="value">{summary.get('success_rate', 0)}%</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">总项目数</div>
                        <div class="value">{summary.get('total_items', 0)}</div>
                    </div>
                </div>
            </div>"""

        # 失败项列表
        if failures:
            html += f"""
            <div class="section">
                <h2 class="section-title">❌ 失败项列表 ({len(failures)})</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>路径</th>
                            <th>大小</th>
                            <th>风险等级</th>
                            <th>错误类型</th>
                            <th>建议操作</th>
                        </tr>
                    </thead>
                    <tbody>"""
            for fail in failures:
                html += f"""
                        <tr>
                            <td>{fail['path']}</td>
                            <td>{fail['size']}</td>
                            <td><span class="status-badge {self._get_risk_class(fail['risk_level'])}">{fail['risk_display']}</span></td>
                            <td>{fail['error_type_display']}</td>
                            <td>{fail['suggested_action_display']}</td>
                        </tr>"""
            html += """
                    </tbody>
                </table>
            </div>"""

        html += f"""
        </div>
        <div class="footer">
            <p>由 PurifyAI 生成 | {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def _format_recovery_records(self, records: List[RecoveryRecord]) -> List[Dict]:
        """格式化恢复记录"""
        return [
            {
                'record_id': r.record_id,
                'plan_id': r.plan_id,
                'item_id': r.item_id,
                'original_path': r.original_path,
                'backup_path': r.backup_path,
                'backup_type': r.backup_type.value,
                'restored': r.restored,
                'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for r in records
        ]

    def _get_failures_by_type(self, failures: List[FailureInfo]) -> Dict[str, int]:
        """按错误类型统计失败项"""
        by_type = {}
        for fail in failures:
            by_type[fail.error_type] = by_type.get(fail.error_type, 0) + 1
        return by_type

    def _format_size(self, size_bytes: int) -> str:
        """格式化字节大小为可读格式"""
        if size_bytes == 0:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} 分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} 小时"

    def _format_error_type(self, error_type: str) -> str:
        """格式化错误类型"""
        error_types = {
            'permission_denied': '权限不足',
            'file_in_use': '文件被占用',
            'file_not_found': '文件不存在',
            'disk_full': '磁盘空间不足',
            'backup_failed': '备份失败',
            'delete_failed': '删除失败',
            'unknown': '未知错误',
        }
        return error_types.get(error_type, error_type)

    def _format_suggested_action(self, action: str) -> str:
        """格式化建议操作"""
        actions = {
            'retry': '重试',
            'skip': '跳过',
            'admin_privilege': '管理员权限',
            'close_app': '关闭占用程序',
        }
        return actions.get(action, action)

    def _get_status_class(self, status: str) -> str:
        """获取状态样式类"""
        status_classes = {
            'completed': 'success',
            'success': 'success',
            'partial_success': 'warning',
            'failed': 'danger',
            'cancelled': 'warning',
        }
        return status_classes.get(status, '')

    def _get_risk_class(self, risk: str) -> str:
        """获取风险等级样式类"""
        risk_classes = {
            'safe': 'success',
            'suspicious': 'warning',
            'dangerous': 'danger',
        }
        return risk_classes.get(risk, '')


# 便利函数
def get_report_generator() -> CleanupReportGenerator:
    """获取报告生成器实例"""
    return CleanupReportGenerator()
