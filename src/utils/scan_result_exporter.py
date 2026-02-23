# -*- coding: utf-8 -*-
"""
扫描结果导出器 (Scan Result Exporter)

Phase B Task 4: 扫描结果导出

功能:
- 导出清理项为 CSV
- 导出清理项为 JSON
- 导出执行结果为 JSON
- 获取导出统计
"""
import os
import csv
import json
from typing import List, Dict, Optional
from datetime import datetime

from core.models_smart import (
    CleanupItem, CleanupPlan, ExecutionResult, FailureInfo,
    ItemDetail, RiskLevel
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ScanResultExporter:
    """扫描结果导出器

    支持将清理项目和执行结果导出为 CSV 或 JSON 格式
    """

    def __init__(self):
        """初始化导出器"""
        self.logger = logger

    def export_items_to_csv(
        self,
        items: List[CleanupItem],
        file_path: str,
        details: Optional[Dict[int, ItemDetail]] = None
    ) -> bool:
        """
        导出清理项为 CSV 文件

        Args:
            items: 清理项列表
            file_path: 导出文件路径
            details: 清理项详细信息字典（可选）

        Returns:
            是否成功导出
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)

            # 写入 CSV
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)

                # 写入表头
                headers = [
                    'item_id', 'path', 'size', 'size_mb', 'item_type',
                    'original_risk', 'ai_risk', 'risk_display'
                ]

                # 如果有详细信息，添加额外列
                if details:
                    headers.extend([
                        'ai_reason', 'confidence', 'cleanup_suggestion',
                        'software_name', 'function_description'
                    ])

                writer.writerow(headers)

                # 写入数据行
                for item in items:
                    row = [
                        item.item_id,
                        item.path,
                        item.size,
                        round(item.size / (1024 * 1024), 2),
                        item.item_type,
                        item.original_risk.value,
                        item.ai_risk.value,
                        item.ai_risk.get_display_name()
                    ]

                    # 如果有详细信息，添加额外数据
                    if details and item.item_id in details:
                        detail = details[item.item_id]
                        row.extend([
                            detail.ai_reason,
                            detail.confidence,
                            detail.cleanup_suggestion,
                            detail.software_name,
                            detail.function_description
                        ])
                    elif details:
                        row.extend(['', '', '', '', ''])

                    writer.writerow(row)

            self.logger.info(f"[EXPORT] 导出 CSV 成功: {file_path}, {len(items)} 项")
            return True

        except Exception as e:
            self.logger.error(f"[EXPORT] 导出 CSV 失败: {e}")
            return False

    def export_items_to_json(
        self,
        items: List[CleanupItem],
        file_path: str,
        details: Optional[Dict[int, ItemDetail]] = None
    ) -> bool:
        """
        导出清理项为 JSON 文件

        Args:
            items: 清理项列表
            file_path: 导出文件路径
            details: 清理项详细信息字典（可选）

        Returns:
            是否成功导出
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)

            # 构建导出数据
            export_data = {
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'total_items': len(items),
                    'format_version': '1.0'
                },
                'items': []
            }

            for item in items:
                item_data = {
                    'item_id': item.item_id,
                    'path': item.path,
                    'size': item.size,
                    'size_mb': round(item.size / (1024 * 1024), 2),
                    'item_type': item.item_type,
                    'original_risk': item.original_risk.value,
                    'ai_risk': item.ai_risk.value,
                    'risk_display': item.ai_risk.get_display_name(),
                }

                # 添加详细信息
                if details and item.item_id in details:
                    detail = details[item.item_id]
                    item_data.update({
                        'ai_reason': detail.ai_reason,
                        'confidence': detail.confidence,
                        'cleanup_suggestion': detail.cleanup_suggestion,
                        'software_name': detail.software_name,
                        'function_description': detail.function_description,
                        'last_modified': (
                            detail.last_modified.isoformat()
                            if detail.last_modified
                            else None
                        ),
                        'error_message': detail.error_message,
                    })

                export_data['items'].append(item_data)

            # 写入 JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"[EXPORT] 导出 JSON 成功: {file_path}, {len(items)} 项")
            return True

        except Exception as e:
            self.logger.error(f"[EXPORT] 导出 JSON 失败: {e}")
            return False

    def export_plan_to_json(
        self,
        plan: CleanupPlan,
        file_path: str,
        include_items: bool = True
    ) -> bool:
        """
        导出清理计划为 JSON 文件

        Args:
            plan: 清理计划
            file_path: 导出文件路径
            include_items: 是否包含所有清理项

        Returns:
            是否成功导出
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)

            # 构建导出数据
            export_data = {
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'plan_id': plan.plan_id,
                    'format_version': '1.0'
                },
                'plan': {
                    'plan_id': plan.plan_id,
                    'scan_type': plan.scan_type,
                    'scan_target': plan.scan_target,
                    'total_items': plan.total_items,
                    'total_size': plan.total_size,
                    'estimated_freed': plan.estimated_freed,
                    'safe_count': plan.safe_count,
                    'suspicious_count': plan.suspicious_count,
                    'dangerous_count': plan.dangerous_count,
                    'ai_summary': plan.ai_summary,
                    'ai_model': plan.ai_model,
                    'ai_call_count': plan.ai_call_count,
                    'used_rule_engine': plan.used_rule_engine,
                    'created_at': plan.created_at.isoformat(),
                    'analyzed_at': (
                        plan.analyzed_at.isoformat()
                        if plan.analyzed_at
                        else None
                    ),
                }
            }

            # 添加清理项
            if include_items:
                export_data['items'] = [
                    {
                        'item_id': item.item_id,
                        'path': item.path,
                        'size': item.size,
                        'item_type': item.item_type,
                        'original_risk': item.original_risk.value,
                        'ai_risk': item.ai_risk.value,
                    }
                    for item in plan.items
                ]

            # 写入 JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"[EXPORT] 导出计划 JSON 成功: {file_path}, "
                f"{plan.total_items} 项"
            )
            return True

        except Exception as e:
            self.logger.error(f"[EXPORT] 导出计划 JSON 失败: {e}")
            return False

    def export_result_to_json(
        self,
        result: ExecutionResult,
        file_path: str,
        include_failures: bool = True
    ) -> bool:
        """
        导出执行结果为 JSON 文件

        Args:
            result: 执行结果
            file_path: 导出文件路径
            include_failures: 是否包含失败项详情

        Returns:
            是否成功导出
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)

            # 构建导出数据
            export_data = {
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'plan_id': result.plan_id,
                    'format_version': '1.0'
                },
                'result': {
                    'plan_id': result.plan_id,
                    'started_at': result.started_at.isoformat(),
                    'completed_at': (
                        result.completed_at.isoformat()
                        if result.completed_at
                        else None
                    ),
                    'duration_seconds': result.duration_seconds,
                    'total_items': result.total_items,
                    'success_items': result.success_items,
                    'failed_items': result.failed_items,
                    'skipped_items': result.skipped_items,
                    'success_rate': result.success_rate,
                    'total_size': result.total_size,
                    'freed_size': result.freed_size,
                    'failed_size': result.failed_size,
                    'status': result.status.value,
                    'error_message': result.error_message,
                }
            }

            # 添加失败项
            if include_failures:
                export_data['failures'] = [
                    {
                        'item_id': fail.item.item_id,
                        'path': fail.item.path,
                        'error_type': fail.error_type,
                        'error_message': fail.error_message,
                        'suggested_action': fail.suggested_action,
                        'timestamp': fail.timestamp.isoformat(),
                    }
                    for fail in result.failures
                ]

            # 写入 JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"[EXPORT] 导出结果 JSON 成功: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"[EXPORT] 导出结果 JSON 失败: {e}")
            return False

    def get_export_stats(self, items: List[CleanupItem]) -> Dict:
        """
        获取导出统计信息

        Args:
            items: 清理项列表

        Returns:
            统计信息字典
        """
        if not items:
            return {
                'total_items': 0,
                'total_size': 0,
                'total_size_mb': 0,
                'safe_count': 0,
                'suspicious_count': 0,
                'dangerous_count': 0,
            }

        total_size = sum(item.size for item in items)
        safe_count = sum(1 for item in items if item.ai_risk == RiskLevel.SAFE)
        suspicious_count = sum(1 for item in items if item.ai_risk == RiskLevel.SUSPICIOUS)
        dangerous_count = sum(1 for item in items if item.ai_risk == RiskLevel.DANGEROUS)

        return {
            'total_items': len(items),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'safe_count': safe_count,
            'suspicious_count': suspicious_count,
            'dangerous_count': dangerous_count,
        }


# 便利函数
def get_exporter() -> ScanResultExporter:
    """获取导出器实例"""
    return ScanResultExporter()
