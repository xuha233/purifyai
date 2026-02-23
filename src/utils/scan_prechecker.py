# -*- coding: utf-8 -*-
"""
扫描预检查器 (Scan Pre-Checker)

Phase B Task 3: 扫描前检查

功能:
- 检查执行权限
- 检查磁盘空间
- 检查路径有效性
- 提供预检查结果和修复建议
"""
import os
import shutil
import stat
from typing import List, Optional
from pathlib import Path

from core.models_smart import CheckResult
from core.permissions import PermissionManager
from utils.logger import get_logger

logger = get_logger(__name__)


class ScanPreChecker:
    """扫描预检查器

    在开始扫描前检查系统状态，确保操作安全
    """

    def __init__(self):
        """初始化预检查器"""
        self.logger = logger
        self.permission_mgr = PermissionManager()

    def check_scan_path(self, path: str) -> CheckResult:
        """
        检查扫描路径是否有效

        Args:
            path: 扫描路径

        Returns:
            CheckResult: 检查结果
        """
        result = CheckResult(scan_path=path)

        # 检查路径是否存在
        if not os.path.exists(path):
            result.add_issue(f"路径不存在: {path}")
            self.logger.warning(f"[PRECHECK] 路径不存在: {path}")
            return result

        # 检查路径类型
        if not os.path.isdir(path):
            result.add_issue(f"路径不是目录: {path}")
            self.logger.warning(f"[PRECHECK] 路径不是目录: {path}")
            return result

        # 检查路径可读性
        if not os.access(path, os.R_OK):
            result.add_issue(f"无读取权限: {path}")
            self.logger.warning(f"[PRECHECK] 无读取权限: {path}")
        else:
            self.logger.debug(f"[PRECHECK] 路径可读: {path}")

        # 检查路径可写性（用于创建临时文件等）
        # 注意：某些系统目录可能不可写，但这不应阻止扫描
        if not os.access(path, os.W_OK):
            result.add_warning(f"路径不可写（可能无法创建临时文件）: {path}")
            self.logger.debug(f"[PRECHECK] 路径不可写: {path}")

        self.logger.info(f"[PRECHECK] 路径检查完成: {path}")
        return result

    def check_permissions(self, paths: List[str]) -> CheckResult:
        """
        检查执行权限

        Args:
            paths: 需要检查的路径列表

        Returns:
            CheckResult: 检查结果
        """
        result = CheckResult()

        if not paths:
            result.add_warning("没有指定扫描路径")
            return result

        # 检查每个路径的权限
        for path in paths:
            path_result = self.permission_mgr.check_read_permission(path)
            if not path_result:
                result.add_issue(f"无权限访问路径: {path}")
            else:
                self.logger.debug(f"[PRECHECK] 有权限访问: {path}")

        # 检查是否需要管理员权限
        needs_admin = False
        for path in paths:
            if self._requires_admin(path):
                if not self.permission_mgr.is_admin():
                    result.add_issue(f"路径 {path} 需要管理员权限，但当前未以管理员身份运行")
                    needs_admin = True
                else:
                    result.add_warning(f"路径 {path} 需要管理员权限，已确认拥有管理员权限")

        if not needs_admin:
            self.logger.info("[PRECHECK] 权限检查通过")

        return result

    def check_disk_space(self, scan_paths: List[str], required_space_mb: int = 100) -> CheckResult:
        """
        检查磁盘空间

        Args:
            scan_paths: 扫描路径列表
            required_space_mb: 所需的磁盘空间（MB），默认100MB用于临时文件

        Returns:
            CheckResult: 检查结果
        """
        result = CheckResult()

        if not scan_paths:
            return result

        # 获取所有磁盘路径
        disk_drives = set()
        for path in scan_paths:
            try:
                drive = os.path.splitdrive(path)[0]
                disk_drives.add(drive)
            except Exception as e:
                self.logger.warning(f"[PRECHECK] 无法解析驱动器: {path}, 错误: {e}")

        # 检查每个磁盘
        for drive in disk_drives:
            try:
                usage = shutil.disk_usage(drive)
                free_gb = usage.free / (1024 ** 3)
                required_gb = required_space_mb / 1024

                if free_gb < required_gb:
                    result.add_issue(
                        f"磁盘 {drive} 空间不足: 仅剩 {free_gb:.2f} GB, "
                        f"需要至少 {required_gb:.2f} GB"
                    )
                    self.logger.warning(f"[PRECHECK] 磁盘 {drive} 空间不足")
                else:
                    self.logger.info(f"[PRECHECK] 磁盘 {drive} 空间充足: {free_gb:.2f} GB")

            except Exception as e:
                result.add_warning(f"无法检查磁盘 {drive} 的空间: {e}")
                self.logger.warning(f"[PRECHECK] 检查磁盘空间失败: {drive}, {e}")

        return result

    def check_path_safety(self, path: str) -> CheckResult:
        """
        检查路径安全性

        Args:
            path: 待检查的路径

        Returns:
            CheckResult: 检查结果
        """
        result = CheckResult(scan_path=path)

        # 检查是否是系统关键路径
        critical_paths = [
            r"C:\Windows\System32",
            r"C:\Windows\SysWOW64",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            "/System",  # macOS/Linux
            "/usr/bin",  # Linux
            "/usr/sbin",  # Linux
        ]

        normalized_path = os.path.normpath(path).lower()

        for critical in critical_paths:
            if normalized_path.startswith(critical.lower()):
                result.add_warning(
                    f"路径包含系统关键目录: {path}。请谨慎操作，避免删除系统文件。"
                )
                self.logger.warning(f"[PRECHECK] 路径涉及系统关键目录: {path}")
                break

        # 检查是否是用户关键数据目录
        user_critical = [
            "desktop",
            "documents",
            "downloads",
            "pictures",
            "videos",
            "music",
        ]

        for folder in user_critical:
            if folder.lower() in normalized_path.lower():
                result.add_warning(
                    f"路径涉及用户数据目录: {path}。建议仔细检查后再清理。"
                )
                self.logger.debug(f"[PRECHECK] 路径涉及用户数据: {path}")
                break

        return result

    def full_precheck(
        self,
        scan_paths: List[str],
        required_space_mb: int = 100,
        check_permissions: bool = True,
        check_disk_space: bool = True,
        check_path_safety: bool = True
    ) -> CheckResult:
        """
        执行完整的预检查

        Args:
            scan_paths: 扫描路径列表
            required_space_mb: 所需磁盘空间（MB）
            check_permissions: 是否检查权限
            check_disk_space: 是否检查磁盘空间
            check_path_safety: 是否检查路径安全性

        Returns:
            CheckResult: 完整的检查结果
        """
        result = CheckResult()

        self.logger.info(f"[PRECHECK] 开始完整预检查: {len(scan_paths)} 个路径")

        # 检查每个路径
        for path in scan_paths:
            path_result = self.check_scan_path(path)
            if path_result.has_issues:
                result.issues.extend(path_result.issues)
            if path_result.warnings:
                result.warnings.extend(path_result.warnings)

        # 检查权限
        if check_permissions:
            perm_result = self.check_permissions(scan_paths)
            if perm_result.has_issues:
                result.issues.extend(perm_result.issues)
            if perm_result.warnings:
                result.warnings.extend(perm_result.warnings)

        # 检查磁盘空间
        if check_disk_space and result.can_scan:  # 只在可以扫描时检查磁盘
            space_result = self.check_disk_space(scan_paths, required_space_mb)
            if space_result.has_issues:
                result.issues.extend(space_result.issues)
            if space_result.warnings:
                result.warnings.extend(space_result.warnings)

        # 检查路径安全性
        if check_path_safety:
            for path in scan_paths:
                safety_result = self.check_path_safety(path)
                if safety_result.warnings:
                    result.warnings.extend(safety_result.warnings)

        # 汇总
        total_issues = len(result.issues)
        total_warnings = len(result.warnings)

        if result.can_scan:
            self.logger.info(f"[PRECHECK] 预检查通过: {total_warnings} 个警告")
        else:
            self.logger.warning(f"[PRECHECK] 预检查未通过: {total_issues} 个问题, {total_warnings} 个警告")

        return result

    def _requires_admin(self, path: str) -> bool:
        """
        判断路径是否需要管理员权限

        Args:
            path: 路径

        Returns:
            是否需要管理员权限
        """
        # Windows 系统目录
        windows_critical = [
            "C:\\Windows\\System32",
            "C:\\Windows\\SysWOW64",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
        ]

        normalized_path = os.path.normpath(path).lower()

        for critical in windows_critical:
            if normalized_path.startswith(critical.lower()):
                return True

        return False


# 便利函数
def get_pre_checker() -> ScanPreChecker:
    """获取预检查器实例"""
    return ScanPreChecker()