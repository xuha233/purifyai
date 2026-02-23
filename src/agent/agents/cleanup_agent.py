# -*- coding: utf-8 -*-
"""
清理智能体 - Cleanup Agent

负责执行文件清理操作
"""
import json
import os
from typing import Dict, List, Any, Optional
import shutil

from ..orchestrator import AgentOrchestrator, AgentType
from utils.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)


class CleanupAgent:
    """清理智能体

    工作流程：
    1. 验证文件是否存在
    2. 检查文件是否被占用
    3. 执行删除操作
    4. 记录操作日志
    """

    def __init__(self, orchestrator: AgentOrchestrator):
        """初始化清理智能体

        Args:
            orchestrator: 编排器实例
        """
        self.orchestrator = orchestrator
        self.agent_type = AgentType.CLEANUP

        # 操作日志
        self.deleted_files: List[str] = []
        self.failed_files: List[Dict[str, Any]] = []
        self.total_freed_bytes: int = 0

        logger.info(f"[CLEANUP_AGENT] 初始化清理智能体")

    def execute_cleanup(
        self,
        cleanup_items: List[Dict[str, Any]],
        is_dry_run: bool = False,
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行清理任务

        Args:
            cleanup_items: 清理项目列表
            is_dry_run: 是否为演练模式（只显示不执行）
            workspace: 工作目录

        Returns:
            清理结果
        """
        logger.info(f"[CLEANUP_AGENT] 开始清理: {len(cleanup_items)} 个项目, "
                   f"演练模式: {is_dry_run}")

        # 重置统计
        self.deleted_files = []
        self.failed_files = []
        self.total_freed_bytes = 0

        results = {
            "total_planned": len(cleanup_items),
            "deleted_count": 0,
            "failed_count": 0,
            "deleted_files": [],
            "failed_files": [],
            "total_freed_bytes": 0,
            "is_dry_run": is_dry_run,
            "success_rate": 0.0
        }

        for i, item in enumerate(cleanup_items, 1):
            path = item.get("path", "")
            file_type = item.get("type", "file")

            logger.debug(f"[CLEANUP_AGENT] 处理 {i}/{len(cleanup_items)}: {path}")

            # 检查是否存在
            if not os.path.exists(path):
                self.failed_files.append({
                    "path": path,
                    "error": "文件不存在",
                    "error_type": "file_not_found"
                })
                continue

            # 执行删除
            if is_dry_run:
                # 演练模式：只记录不实际删除
                size = os.path.getsize(path) if os.path.isfile(path) else 0
                self.deleted_files.append(path)
                self.total_freed_bytes += size
                results["deleted_count"] += 1
                results["deleted_files"].append({
                    "path": path,
                    "size": size
                })
            else:
                # 实际删除
                success, freed_size, error_info = self._delete_item(path, file_type)

                if success:
                    self.deleted_files.append(path)
                    self.total_freed_bytes += freed_size
                    results["deleted_count"] += 1
                    results["deleted_files"].append({
                        "path": path,
                        "size": freed_size
                    })
                else:
                    self.failed_files.append(error_info)
                    results["failed_count"] += 1
                    results["failed_files"].append(error_info)

        # 计算成功率
        if results["total_planned"] > 0:
            results["success_rate"] = results["deleted_count"] / results["total_planned"]

        results["total_freed_bytes"] = self.total_freed_bytes

        logger.info(f"[CLEANUP_AGENT] 清理完成: 成功 {results['deleted_count']}, "
                   f"失败 {results['failed_count']}, "
                   f"释放 {self._format_bytes(self.total_freed_bytes)}")

        return results

    def _delete_item(
        self,
        path: str,
        file_type: str
    ) -> tuple[bool, int, Dict[str, Any]]:
        """删除单个项目

        Args:
            path: 项目路径
            file_type: 类型 (file/directory)

        Returns:
            (是否成功, 释放字节数, 错误信息)
        """
        error_info = {
            "path": path,
            "error": "",
            "error_type": ""
        }

        try:
            # 获取文件大小
            size = os.path.getsize(path) if os.path.isfile(path) else 0

            if file_type == "directory":
                # 递归删除目录
                shutil.rmtree(path, ignore_errors=True)
                # 检查是否真的删除成功
                if os.path.exists(path):
                    # 逐个删除
                    self._delete_directory_recursive(path)
            else:
                # 删除文件
                os.remove(path)

            # 验证删除成功
            if not os.path.exists(path):
                return True, 0, {}  # 不计算目录大小
            else:
                error_info["error"] = "文件仍存在，可能被锁定"
                error_info["error_type"] = "file_in_use"
                return False, 0, error_info

        except PermissionError as e:
            error_info["error"] = f"权限拒绝: {str(e)}"
            error_info["error_type"] = "permission_denied"
            return False, 0, error_info
        except OSError as e:
            error_info["error"] = f"系统错误: {str(e)}"
            error_info["error_type"] = "os_error"
            return False, 0, error_info
        except Exception as e:
            error_info["error"] = f"未知错误: {str(e)}"
            error_info["error_type"] = "unknown"
            return False, 0, error_info

    def _delete_directory_recursive(self, dir_path: str):
        """递归删除目录内容（备选方法）

        Args:
            dir_path: 目录路径
        """
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)

                if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                    except Exception:
                        pass
                elif os.path.isdir(item_path):
                    self._delete_directory_recursive(item_path)

            # 尝试删除目录
            try:
                os.rmdir(dir_path)
            except Exception:
                pass

        except Exception:
            pass

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

    def retry_failed_items(
        self,
        failed_items: List[Dict[str, Any]],
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """重试失败的清理项

        Args:
            failed_items: 失败的项目列表
            workspace: 工作目录

        Returns:
            重试结果
        """
        logger.info(f"[CLEANUP_AGENT] 重试失败项: {len(failed_items)} 个")

        # 提取路径
        retry_paths = [item.get("path", "") for item in failed_items]

        # 重新构建清理项格式
        retry_items = [
            {"path": path, "type": "file"} for path in retry_paths
        ]

        return self.execute_cleanup(retry_items, is_dry_run=False, workspace=workspace)

    def get_cleanup_summary(self) -> Dict[str, Any]:
        """获取清理摘要

        Returns:
            清理摘要
        """
        return {
            "deleted_count": len(self.deleted_files),
            "failed_count": len(self.failed_files),
            "total_freed_bytes": self.total_freed_bytes,
            "total_freed_formatted": self._format_bytes(self.total_freed_bytes),
            "deleted_files_sample": self.deleted_files[:10],
            "failed_files_summary": [
                f"{f.get('path')}: {f.get('error')}"
                for f in self.failed_files[:10]
            ]
        }
