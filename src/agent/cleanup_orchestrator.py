# -*- coding: utf-8 -*-
"""
清理流程编排模块 (Cleanup Orchestrator)

实现一键清理流程的编排、预览、执行和报告生成

作者: 小午 🦁
创建时间: 2026-02-24
"""

import uuid
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from pathlib import Path
import time

from PyQt5.QtCore import QObject, pyqtSignal

from .smart_recommender import SmartRecommender, UserProfile, CleanupPlan, CleanupMode
from ..core.models import ScanItem
from ..core.backup_manager import BackupManager
from ..core.cleaner import Cleaner


# ============================================================================
# 枚举定义
# ============================================================================

class CleanupPhase(Enum):
    """清理阶段"""
    SCANNING = "scanning"           # 扫描中
    ANALYZING = "analyzing"         # 分析中
    BACKING_UP = "backing_up"       # 备份中
    CLEANING = "cleaning"           # 清理中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"               # 失败

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            CleanupPhase.SCANNING: "扫描中",
            CleanupPhase.ANALYZING: "分析中",
            CleanupPhase.BACKING_UP: "备份中",
            CleanupPhase.CLEANING: "清理中",
            CleanupPhase.COMPLETED: "已完成",
            CleanupPhase.FAILED: "失败"
        }
        return names.get(self, self.value)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class CleanupReport:
    """清理报告"""
    report_id: str
    plan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    total_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    freed_size: int = 0
    success_rate: float = 0.0
    details: List[Dict[str, Any]] = field(default_factory=list)
    phase: CleanupPhase = CleanupPhase.SCANNING
    is_incremental: bool = False  # 是否为增量清理

    def calculate_stats(self):
        """计算统计数据"""
        self.total_items = len(self.details)
        self.success_items = sum(1 for d in self.details if d.get('success', False))
        self.failed_items = sum(1 for d in self.details if not d.get('success', False))
        self.freed_size = sum(d.get('freed_size', 0) for d in self.details if d.get('success', False))

        if self.total_items > 0:
            self.success_rate = (self.success_items / self.total_items) * 100

        if self.completed_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'report_id': self.report_id,
            'plan_id': self.plan_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'total_items': self.total_items,
            'success_items': self.success_items,
            'failed_items': self.failed_items,
            'freed_size': self.freed_size,
            'success_rate': self.success_rate,
            'phase': self.phase.value,
            'details': self.details
        }


@dataclass
class BackupInfo:
    """备份信息"""
    backup_id: str
    items_count: int
    total_size: int
    backup_path: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'backup_id': self.backup_id,
            'items_count': self.items_count,
            'total_size': self.total_size,
            'backup_path': self.backup_path,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


# ============================================================================
# 清理信号
# ============================================================================

class CleanupSignal(QObject):
    """清理信号（用于更新 UI）"""

    # 进度更新：(百分比, 当前状态描述)
    progress_updated = pyqtSignal(int, str)

    # 阶段变化：'scanning', 'analyzing', 'backing_up', 'cleaning', 'completed', 'failed'
    phase_changed = pyqtSignal(str)

    # 清理完成：清理报告
    cleanup_completed = pyqtSignal(CleanupReport)

    # 清理失败：错误消息
    cleanup_failed = pyqtSignal(str)

    # 备份进度：(当前项目数, 总项目数)
    backup_progress = pyqtSignal(int, int)

    # 清理状态：（项目路径, 成功/失败）
    cleanup_status = pyqtSignal(str, bool)


# ============================================================================
# 清理流程编排器
# ============================================================================

class CleanupOrchestrator:
    """清理流程编排器

    功能：
    1. 执行一键清理完整流程
    2. 生成清理计划预览
    3. 清理前自动备份
    4. 执行清理并生成报告
    5. 支持增量清理
    """

    def __init__(self, profile: UserProfile, signal: Optional[CleanupSignal] = None):
        """初始化清理编排器

        Args:
            profile: 用户画像
            signal: 清理信号（用于 UI 更新）
        """
        self.profile = profile
        self.recommender = SmartRecommender()
        self.backup_manager = BackupManager()
        self.cleaner = Cleaner()
        self.signal = signal

    def execute_one_click_cleanup(self, mode: str = CleanupMode.BALANCED.value) -> CleanupReport:
        """执行一键清理

        步骤：
        1. 生成清理计划
        2. 显示预览
        3. 自动备份
        4. 执行清理
        5. 生成报告
        """
        report_id = str(uuid.uuid4())
        report = CleanupReport(
            report_id=report_id,
            plan_id="",
            started_at=datetime.now(),
            phase=CleanupPhase.SCANNING
        )

        try:
            # 阶段 1：扫描和分析
            self._update_phase(CleanupPhase.SCANNING, 10, "正在扫描系统...")
            plan = self.generate_cleanup_plan(mode)
            report.plan_id = plan.plan_id
            report.is_incremental = plan.is_incremental

            self._update_phase(CleanupPhase.ANALYZING, 20, "正在分析文件风险...")
            # 计划已在 recommend 中生成

            # 阶段 2：备份
            self._update_phase(CleanupPhase.BACKING_UP, 30, "正在备份文件...")
            backup_info = self.backup_before_cleanup(plan.items)
            report.details.append({
                'type': 'backup',
                'backup_id': backup_info.backup_id,
                'items_count': backup_info.items_count,
                'total_size': backup_info.total_size
            })

            # 阶段 3：执行清理
            self._update_phase(CleanupPhase.CLEANING, 50, "正在清理文件...")
            report = self.execute_cleanup(plan, backup_info.backup_id)

            # 阶段 4：生成报告
            self._update_phase(CleanupPhase.COMPLETED, 100, "清理完成！")
            report.phase = CleanupPhase.COMPLETED
            report.calculate_stats()

            # 保存清理历史
            self._save_cleanup_history(report)

            return report

        except Exception as e:
            report.phase = CleanupPhase.FAILED
            report.details.append({
                'type': 'error',
                'error': str(e)
            })

            if self.signal:
                self.signal.cleanup_failed.emit(str(e))

            raise e

    def generate_cleanup_plan(self, mode: str = CleanupMode.BALANCED.value) -> CleanupPlan:
        """生成清理计划（预览用）"""
        plan = self.recommender.recommend(self.profile, mode)
        return plan

    def preview_cleanup(self, plan: CleanupPlan) -> Dict[str, Any]:
        """生成清理预览"""
        return {
            'plan_id': plan.plan_id,
            'total_items': len(plan.items),
            'estimated_space': self._format_size(plan.estimated_space),
            'high_risk_count': plan.high_risk_count,
            'medium_risk_count': plan.medium_risk_count,
            'low_risk_count': plan.low_risk_count,
            'risk_percentage': plan.risk_percentage,
            'recommended': plan.recommended,
            'mode': CleanupMode(plan.mode).get_display_name()
        }

    def backup_before_cleanup(self, items: List[ScanItem]) -> BackupInfo:
        """清理前自动备份"""
        backup_id = str(uuid.uuid4())
        backup_path = os.path.join(os.path.expanduser('~'), '.purifyai', 'backups', backup_id)

        os.makedirs(backup_path, exist_ok=True)

        total_count = len(items)
        total_size = sum(item.size for item in items)

        started_at = datetime.now()

        for i, item in enumerate(items):
            try:
                # 使用备份管理器创建备份
                backup_file = self.backup_manager.backup_file(
                    item.path,
                    backup_path=backup_path
                )

                if self.signal:
                    self.signal.backup_progress.emit(i + 1, total_count)

            except Exception as e:
                print(f"[CleanupOrchestrator] 备份失败: {item.path}, 错误: {e}")

        completed_at = datetime.now()

        backup_info = BackupInfo(
            backup_id=backup_id,
            items_count=total_count,
            total_size=total_size,
            backup_path=backup_path,
            started_at=started_at,
            completed_at=completed_at
        )

        return backup_info

    def execute_cleanup(self, plan: CleanupPlan, backup_id: str) -> CleanupReport:
        """执行清理"""
        report_id = str(uuid.uuid4())
        report = CleanupReport(
            report_id=report_id,
            plan_id=plan.plan_id,
            started_at=datetime.now(),
            phase=CleanupPhase.CLEANING
        )

        total_items = len(plan.items)

        for i, item in enumerate(plan.items):
            try:
                # 使用清理器安全删除
                result = self.cleaner.delete_secure(item.path, backup_id=backup_id)

                success = bool(result and result.get('success', False))
                freed_size = result.get('freed_size', 0) if success else 0

                report.details.append({
                    'type': 'cleanup',
                    'path': item.path,
                    'success': success,
                    'freed_size': freed_size,
                    'error': None if success else result.get('error', 'Unknown error')
                })

                if self.signal:
                    self.signal.cleanup_status.emit(item.path, success)

                # 更新进度
                progress = 50 + int((i + 1) / total_items * 50)
                percent = min(progress, 95)
                status = f"正在清理 ({i + 1}/{total_items}): {os.path.basename(item.path)}"
                self._update_progress(percent, status)

            except Exception as e:
                report.details.append({
                    'type': 'cleanup',
                    'path': item.path,
                    'success': False,
                    'freed_size': 0,
                    'error': str(e)
                })

                if self.signal:
                    self.signal.cleanup_status.emit(item.path, False)

        report.calculate_stats()
        report.completed_at = datetime.now()

        return report

    def _update_phase(self, phase: CleanupPhase, progress: int, status: str):
        """更新清理阶段"""
        if self.signal:
            self.signal.phase_changed.emit(phase.value)
            self._update_progress(progress, status)

    def _update_progress(self, percent: int, status: str):
        """更新进度"""
        if self.signal:
            self.signal.progress_updated.emit(percent, status)

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _save_cleanup_history(self, report: CleanupReport):
        """保存清理历史"""
        history_file = os.path.join(os.path.expanduser('~'), '.purifyai', 'cleanup_history.json')
        history_dir = os.path.dirname(history_file)
        os.makedirs(history_dir, exist_ok=True)

        try:
            data = {}
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            if 'history' not in data:
                data['history'] = []

            data['history'].append(report.to_dict())
            data['last_cleanup'] = datetime.now().isoformat()

            # 只保留最近 100 条记录
            if len(data['history']) > 100:
                data['history'] = data['history'][-100:]

            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[CleanupOrchestrator] 保存历史失败: {e}")


# 导入 os 模块
import os
