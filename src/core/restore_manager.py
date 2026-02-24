# -*- coding: utf-8 -*-
"""
恢复管理器 (Restore Manager)

实现一键撤销功能，允许用户在清理后 30 天内撤销清理操作，将文件从备份恢复到原位置。

作者: 小午 🦁
创建时间: 2026-02-24
"""

import os
import uuid
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import shutil

from PyQt5.QtCore import QObject, pyqtSignal

from .backup_manager import BackupManager, BackupInfo, BackupType
from .models_smart import CleanupItem, RecoveryRecord
from .restore_signal import RestoreSignal
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class RestoreSession:
    """文件恢复会话"""

    session_id: str                      # 会话 ID
    backup_id: str                       # 备份 ID（来自 CleanupReport）
    restore_mode: str                    # 恢复模式：all, selected
    files: List[str]                     # 选中的文件列表
    total_files: int                     # 总文件数
    restored_files: int                  # 已恢复文件数
    failed_files: int                    # 恢复失败数
    status: str                          # 状态：pending, restoring, completed, failed
    created_at: datetime                 # 创建时间
    completed_at: Optional[datetime] = None  # 完成时间

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'backup_id': self.backup_id,
            'restore_mode': self.restore_mode,
            'files': self.files,
            'total_files': self.total_files,
            'restored_files': self.restored_files,
            'failed_files': self.failed_files,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RestoreSession':
        """从字典创建"""
        created_at = datetime.fromisoformat(data['created_at'])
        completed_at = None
        if data.get('completed_at'):
            completed_at = datetime.fromisoformat(data['completed_at'])

        return cls(
            session_id=data['session_id'],
            backup_id=data['backup_id'],
            restore_mode=data['restore_mode'],
            files=data.get('files', []),
            total_files=data.get('total_files', 0),
            restored_files=data.get('restored_files', 0),
            failed_files=data.get('failed_files', 0),
            status=data['status'],
            created_at=created_at,
            completed_at=completed_at
        )


@dataclass
class UndoHistory:
    """撤销历史记录

    Attributes:
        cleanup_report_id: 清理报告 ID
        backup_id: 备份 ID
        cleanup_time: 清理时间
        undo_time: 撤销时间（None 表示未撤销）
        can_undo: 是否可撤销（30 天内）
        status: 状态：available, undone, expired
    """
    cleanup_report_id: str
    backup_id: str
    cleanup_time: datetime
    undo_time: Optional[datetime] = None
    can_undo: bool = True
    status: str = "available"  # available, undone, expired

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'cleanup_report_id': self.cleanup_report_id,
            'backup_id': self.backup_id,
            'cleanup_time': self.cleanup_time.isoformat(),
            'undo_time': self.undo_time.isoformat() if self.undo_time else None,
            'can_undo': self.can_undo,
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UndoHistory':
        """从字典创建"""
        cleanup_time = datetime.fromisoformat(data['cleanup_time'])
        undo_time = None
        if data.get('undo_time'):
            undo_time = datetime.fromisoformat(data['undo_time'])

        return cls(
            cleanup_report_id=data['cleanup_report_id'],
            backup_id=data['backup_id'],
            cleanup_time=cleanup_time,
            undo_time=undo_time,
            can_undo=data.get('can_undo', True),
            status=data.get('status', 'available')
        )


# 恢复管理器
# ============================================================================

class RestoreManager(QObject):
    """恢复管理器

    功能：
    1. 创建恢复会话（选择性恢复）
    2. 执行恢复操作（批量或选择）
    3. 获取撤销历史
    4. 检查撤销有效性（30 天）
    """

    def __init__(self, backup_manager: Optional[BackupManager] = None):
        """初始化恢复管理器

        Args:
            backup_manager: 备份管理器（可选）
        """
        super().__init__()

        self.backup_manager = backup_manager or BackupManager()
        self.logger = logger

        # 恢复会话存储
        self._sessions: Dict[str, RestoreSession] = {}

        # 撤销历史存储
        self._undo_history: List[UndoHistory] = []

        # 加载持久化数据
        self._load_sessions()
        self._load_undo_history()

        self.logger.info("[RESTORE] 恢复管理器初始化完成")

    def _get_sessions_file(self) -> str:
        """获取会话文件路径"""
        return os.path.join(self.backup_manager.backup_root, 'restore_sessions.json')

    def _get_undo_history_file(self) -> str:
        """获取撤销历史文件路径"""
        return os.path.join(self.backup_manager.backup_root, 'undo_history.json')

    def _load_sessions(self):
        """从文件加载恢复会话"""
        filepath = self._get_sessions_file()
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for session_data in data.get('sessions', []):
                    session = RestoreSession.from_dict(session_data)
                    self._sessions[session.session_id] = session
            self.logger.info(f"[RESTORE] 加载恢复会话: {len(self._sessions)} 个")
        except Exception as e:
            self.logger.error(f"[RESTORE] 加载恢复会话失败: {e}")

    def _save_sessions(self):
        """保存恢复会话到文件"""
        filepath = self._get_sessions_file()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            data = {
                'version': '1.0',
                'sessions': [s.to_dict() for s in self._sessions.values()]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"[RESTORE] 保存恢复会话失败: {e}")

    def _load_undo_history(self):
        """从文件加载撤销历史"""
        filepath = self._get_undo_history_file()
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for history_data in data.get('history', []):
                    history = UndoHistory.from_dict(history_data)
                    self._undo_history.append(history)
            self.logger.info(f"[RESTORE] 加载撤销历史: {len(self._undo_history)} 条")
        except Exception as e:
            self.logger.error(f"[RESTORE] 加载撤销历史失败: {e}")

    def _save_undo_history(self):
        """保存撤销历史到文件"""
        filepath = self._get_undo_history_file()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            data = {
                'version': '1.0',
                'history': [h.to_dict() for h in self._undo_history]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"[RESTORE] 保存撤销历史失败: {e}")

    def create_restore_session(
        self,
        backup_id: str,
        files: Optional[List[str]] = None
    ) -> RestoreSession:
        """创建恢复会话

        Args:
            backup_id: 备份 ID
            files: 可选，指定的文件列表（None 表示全部恢复）

        Returns:
            RestoreSession 恢复会话

        Raises:
            ValueError: 备份无效
        """
        # 验证备份有效性
        backup_info = self._get_backup_info(backup_id)
        if not backup_info:
            raise ValueError(f"备份不存在: {backup_id}")

        if not os.path.exists(backup_info.backup_path):
            raise ValueError(f"备份文件不存在: {backup_info.backup_path}")

        # 确定文件列表
        if files is None or len(files) == 0:
            # 全部恢复模式
            restore_mode = "all"
            # 如果是 ZIP 压缩包，从manifest读取文件列表
            # 这里简化为1个文件
            the_files = [backup_info.original_path or "unknown"]
        else:
            # 选择性恢复模式
            restore_mode = "selected"
            the_files = files

        # 创建恢复会话
        session_id = str(uuid.uuid4())
        session = RestoreSession(
            session_id=session_id,
            backup_id=backup_id,
            restore_mode=restore_mode,
            files=the_files,
            total_files=len(the_files),
            restored_files=0,
            failed_files=0,
            status="pending",
            created_at=datetime.now()
        )

        # 保存会话
        self._sessions[session_id] = session
        self._save_sessions()

        self.logger.info(f"[RESTORE] 创建恢复会话: {session_id} (模式: {restore_mode})")

        return session

    def execute_restore(
        self,
        session_id: str,
        signal: Optional[RestoreSignal] = None
    ) -> bool:
        """执行恢复操作

        Args:
            session_id: 会话 ID
            signal: 恢复信号（可选）

        Returns:
            bool 是否成功
        """
        # 加载会话
        session = self._sessions.get(session_id)
        if not session:
            self.logger.error(f"[RESTORE] 会话不存在: {session_id}")
            if signal:
                signal.restore_failed.emit("会话不存在")
            return False

        try:
            # 更新状态为恢复中
            session.status = "restoring"
            self._save_sessions()

            # 获取备份信息
            backup_info = self._get_backup_info(session.backup_id)
            if not backup_info:
                raise ValueError(f"备份不存在: {session.backup_id}")

            # 执行恢复
            total = session.total_files
            for idx, file_path in enumerate(session.files):
                percent = int((idx / total) * 100) if total > 0 else 0
                status = f"正在恢复 ({idx + 1}/{total}): {os.path.basename(file_path)}"

                if signal:
                    signal.progress_updated.emit(percent, status)

                success = self.backup_manager.restore_backup(session.backup_id)

                if success:
                    session.restored_files += 1
                    if signal:
                        signal.file_restored.emit(file_path, True)
                else:
                    session.failed_files += 1
                    if signal:
                        signal.file_restored.emit(file_path, False)

            # 更新状态为完成
            session.status = "completed"
            session.completed_at = datetime.now()
            self._save_sessions()

            if signal:
                signal.progress_updated.emit(100, "恢复完成")
                signal.restore_completed.emit(session)

            self.logger.info(f"[RESTORE] 恢复会话完成: {session_id}")

            return True

        except Exception as e:
            self.logger.error(f"[RESTORE] 恢复会话失败: {e}")
            session.status = "failed"
            session.completed_at = datetime.now()
            self._save_sessions()

            if signal:
                signal.restore_failed.emit(str(e))

            return False

    def add_undo_history(
        self,
        cleanup_report_id: str,
        backup_id: str,
        cleanup_time: datetime
    ):
        """添加撤销历史记录

        Args:
            cleanup_report_id: 清理报告 ID
            backup_id: 备份 ID
            cleanup_time: 清理时间
        """
        # 检查是否有效（30天内）
        time_diff = datetime.now() - cleanup_time
        can_undo = time_diff.days < 30

        history = UndoHistory(
            cleanup_report_id=cleanup_report_id,
            backup_id=backup_id,
            cleanup_time=cleanup_time,
            can_undo=can_undo
        )

        self._undo_history.append(history)
        self._save_undo_history()

        self.logger.info(f"[RESTORE] 添加撤销历史: {cleanup_report_id}")

    def get_undo_history(
        self,
        cleanup_report_id: Optional[str] = None
    ) -> List[UndoHistory]:
        """获取撤销历史

        Args:
            cleanup_report_id: 可选，指定的清理报告 ID

        Returns:
            撤销历史列表
        """
        if cleanup_report_id:
            # 返回指定的清理报告
            filtered = [h for h in self._undo_history if h.cleanup_report_id == cleanup_report_id]
            return filtered
        else:
            # 返回全部历史（倒序）
            return reversed(self._undo_history)

    def check_undo_validity(cleanup_report: Any) -> bool:
        """检查清理报告是否可撤销

        Args:
            cleanup_report: 清理报告（CleanupReport 对象）

        Returns:
            bool 是否可撤销
        """
        # 检查 completed_at 是否存在
        if not hasattr(cleanup_report, 'completed_at') or not cleanup_report.completed_at:
            return False

        # 检查是否在 30 天内
        time_since_cleanup = datetime.now() - cleanup_report.completed_at
        return time_since_cleanup.days < 30

    def _get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """获取备份信息（从 BackupManager）

        Args:
            backup_id: 备份 ID

        Returns:
            BackupInfo 备份信息
        """
        # 优先从缓存获取
        backup_info = self.backup_manager._backup_cache.get(backup_id)
        if not backup_info:
            # 从数据库查询
            backup_info = self.backup_manager._get_backup_info(backup_id)
        return backup_info
