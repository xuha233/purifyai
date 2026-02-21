"""
恢复管理器 (Recovery Manager) - 备份历史和恢复

Phase 5 MVP功能:
- 备份历史查看 (分页、搜索、过滤)
- 备份恢复 (单条/批量)
- 清理失败项目恢复
- 备份统计信息
- 备份自动清理过期

Features:
- 从数据库读取备份记录
- 按时间、风险等级、备份类型过滤
- 恢复到原路径或指定路径
- 显示备份详情
- 批量操作支持
- 一键恢复所有失败项
"""
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtCore import QMutex, QMutexLocker

from .models_smart import (
    BackupInfo, BackupType, RecoveryRecord,
    CleanupStatus, ExecutionStatus
)
from .database import Database, get_database
from .backup_manager import BackupManager, get_backup_manager
from .rule_engine import RiskLevel
from utils.logger import get_logger

logger = get_logger(__name__)


class RestoreStatus(Enum):
    """恢复状态"""
    PENDING = "pending"           # 等待恢复
    IN_PROGRESS = "in_progress"   # 恢复中
    SUCCESS = "success"           # 恢复成功
    FAILED = "failed"             # 恢复失败
    CANCELLED = "cancelled"       # 已取消


@dataclass
class RecoveryTask:
    """恢复任务"""
    task_id: str
    backup_id: str
    backup_info: BackupInfo
    status: RestoreStatus = RestoreStatus.PENDING
    error_message: str = ""
    target_path: str = ""
    progress: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'backup_id': self.backup_id,
            'backup_info': self.backup_info,
            'status': self.status.value,
            'error_message': self.error_message,
            'target_path': self.target_path,
            'progress': self.progress
        }


@dataclass
class RecoveryStats:
    """恢复统计"""
    total_backups: int = 0
    ready_to_restore: int = 0
    already_restored: int = 0
    failed_backups: int = 0
    total_backup_size: int = 0
    failed_size: int = 0
    restored_size: int = 0


class RecoveryThread(QThread):
    """恢复线程 - 在后台执行恢复"""

    progress = pyqtSignal(str, int)        # task_id, progress (0-100)
    completed = pyqtSignal(str, bool, str) # task_id, success, message


class RecoveryManager(QObject):
    """恢复管理器

    提供备份历史查看和恢复功能：
    - 获取备份历史列表
    - 查看备份详情
    - 恢复单个备份
    - 批量恢复
    - 恢复失败项目
    - 清理过期备份

    Signals:
        backup_loaded: BackupInfo - 加载备份信息
        restore_started: str - task_id
        restore_progress: str, int - task_id, progress
        restore_completed: str, bool, str - task_id, success, message
        error: str - error_message
        stats_updated: RecoveryStats - 统计更新
        cleanup_completed: int - 清理的备份数量
    """

    # 信号
    backup_loaded = pyqtSignal(object)                # BackupInfo
    restore_started = pyqtSignal(str)                # task_id
    restore_progress = pyqtSignal(str, int)            # task_id, progress
    restore_completed = pyqtSignal(str, bool, str)     # task_id, success, message
    error = pyqtSignal(str)                            # error_message
    stats_updated = pyqtSignal(object)                # RecoveryStats
    cleanup_completed = pyqtSignal(int)                  # count

    def __init__(
        self,
        backup_mgr: Optional[BackupManager] = None,
        db: Optional[Database] = None
    ):
        """
        初始化恢复管理器

        Args:
            backup_mgr: 备份管理器
            db: 数据库实例
        """
        super().__init__()

        self.backup_mgr = backup_mgr or get_backup_manager()
        self.db = db or get_database()

        # 恢复任务管理
        self.recovery_tasks: Dict[str, RecoveryTask] = {}
        self.mutex = QMutex()

        self.logger = logger

    def get_backup_history(
        self,
        limit: int = 100,
        offset: int = 0,
        risk_filter: Optional[RiskLevel] = None,
        backup_type: Optional[BackupType] = None,
        restored_only: bool = False,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[BackupInfo]:
        """
        获取备份历史列表

        Args:
            limit: 返回数量限制
            offset: 偏移量
            risk_filter: 风险等级过滤
            backup_type: 备份类型过滤
            restored_only: 是否只返回已恢复的
            date_from: 日期范围起始
            date_to: 日期范围结束

        Returns:
            备份信息列表
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if risk_filter:
                # 需要从备份信息关联的风险等级
                conditions.append("cp.ai_risk = ?")
                params.append(risk_filter.value)

            if backup_type:
                conditions.append("backup_type = ?")
                params.append(backup_type.value)

            if restored_only:
                conditions.append("r.restored = 1")
            else:
                conditions.append("r.restored = 0")

            if date_from:
                conditions.append("timestamp >= ?")
                params.append(date_from.isoformat())

            if date_to:
                conditions.append("timestamp <= ?")
                params.append(date_to.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 构建查询
            base_query = f'''
                SELECT r.*, cp.path as original_path, cp.size as item_size, cp.ai_risk as risk_level
                FROM recovery_log r
                JOIN cleanup_plan_items cp ON r.item_id = cp.item_id
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([limit, offset])

            cursor.execute(base_query, params)

            backups = []
            for row in cursor.fetchall():
                # 处理 null original_path
                original_path = row.get('original_path') or self._get_original_path_from_backup(row['backup_path'])

                backup_info = BackupInfo(
                    backup_id=row['id'],
                    item_id=row['item_id'],
                    original_path=original_path,
                    backup_path=row['backup_path'],
                    backup_type=BackupType.from_value(row['backup_type']),
                    created_at=datetime.fromisoformat(row['timestamp']),
                    restored=bool(row['restored'])
                )

                # 添加风险等级信息
                backup_info.risk_level = RiskLevel.from_value(row['risk_level'])

                backups.append(backup_info)

            conn.close()

            self.logger.info(f"[RECOVERY] 获取备份历史: {len(backups)} 条记录")
            return backups

        except Exception as e:
            self.logger.error(f"[RECOVERY] 获取备份历史失败: {e}")
            return []

    def get_backup_details(self, backup_id: str) -> Optional[BackupInfo]:
        """获取备份详情

        Args:
            backup_id: 备份 ID

        Returns:
            备份信息，不存在返回 None
        """
        return self.backup_mgr._get_backup_info(backup_id)

    def restore_backup(
        self,
        backup_id: str,
        destination: Optional[str] = None
    ) -> bool:
        """
        恢复备份

        Args:
            backup_id: 备份 ID
            destination: 目标路径，None 恢复到原路径

        Returns:
            是否成功
        """
        # 从 BackupManager 恢复
        success = self.backup_mgr.restore_backup(backup_id, destination)

        if success:
            self.logger.info(f"[RECOVERY] 备份恢复成功: {backup_id}")
        else:
            self.logger.error(f"[RECOVERY] 备份恢复失败: {backup_id}")

        return success

    def batch_restore(
        self,
        backup_ids: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[int, int, int]:
        """
        批量恢复备份

        Args:
            backup_ids: 备份 ID 列表
            progress_callback: 进度回调 (current, total)

        Returns:
            (成功数, 失败数, 跳过数)
        """
        success_count = 0
        failed_count = 0
        skipped_count = 0
        total = len(backup_ids)

        self.logger.info(f"[RECOVERY] 开始批量恢复: {total} 个备份")

        for i, backup_id in enumerate(backup_ids):
            progress_callback(i, total)

            backup_info = self.get_backup_details(backup_id)
            if not backup_info:
                self.logger.warning(f"[RECOVERY] 备份不存在: {backup_id}")
                failed_count += 1
                continue

            if backup_info.restored:
                self.logger.info(f"[RECOVERY] 备份已恢复: {backup_id}")
                skipped_count += 1
                continue

            try:
                success = self.restore_backup(backup_id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                self.logger.error(f"[RECOVERY] 恢复失败: {backup_id}, {e}")
                failed_count += 1

        self.logger.info(f"[RECOVERY] 批量恢复完成: 成功 {success_count}, 失败 {failed_count}, 跳过 {skipped_count}")

        return success_count, failed_count, skipped_count

    def restore_failed_items(self, plan_id: Optional[str] = None) -> int:
        """
        恢复所有失败项的备份

        Args:
            plan_id: 清理计划 ID，None 表示所有失败项

        Returns:
            成功恢复的数量
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 查询失败的清理项及其备份
            if plan_id:
                query = '''
                    SELECT r.*
                    FROM recovery_log r
                    JOIN cleanup_plan_items cp ON r.item_id =.cp.item_id
                    WHERE cp.plan_id = ? AND cp.status = ?
                '''
                params = [plan_id, CleanupStatus.FAILED.value]
            else:
                query = '''
                    SELECT r.*
                    FROM recovery_log r
                    JOIN cleanup_plan_items cp ON r.item_id = cp.item_id
                    WHERE cp.status = ?
                '''
                params = [CleanupStatus.FAILED.value]

            cursor.execute(query, params)

            backup_ids = [row['id'] for row in cursor.fetchall()]
            conn.close()

            # 批量恢复
            success, failed, skipped = self.batch_restore(backup_ids)

            return success

        except Exception as e:
            self.logger.error(f"[RECOVERY] 恢复失败项失败: {e}")
            return 0

    def get_stats(self) -> RecoveryStats:
        """获取恢复统计

        Returns:
            恢复统计
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 总备份数
            cursor.execute('SELECT COUNT(*) as count FROM recovery_log')
            total_backups = cursor.fetchone()['count']

            # 未恢复数
            cursor.execute('SELECT COUNT(*) as count FROM recovery_log WHERE restored = 0')
            ready_to_restore = cursor.fetchone()['count']

            # 已恢复数
            cursor.execute('SELECT COUNT(*) as count FROM recovery_log WHERE restored = 1')
            already_restored = cursor.fetchone()['count']

            # 失败数 ( CleanupStatus = FAILED )
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM recovery_log r
                JOIN cleanup_plan_items cp ON r.item_id = cp.item_id
                WHERE cp.status = ?
            ''', (CleanupStatus.FAILED.value,))
            failed_backups = cursor.fetchone()['count']

            # 总大小
            cursor.execute('''
                SELECT SUM(COALESCE(cp.size, 0)) as total_size
                FROM recovery_log r
                JOIN cleanup_plan_items cp ON r.item_id = cp.item_id
            ''')
            total_size = cursor.fetchone()['total_size'] or 0

            conn.close()

            stats = RecoveryStats(
                total_backups=total_backups,
                ready_to_restore=ready_to_restore,
                already_restored=already_restored,
                failed_backups=failed_backups,
                total_backup_size=total_size
            )

            self.stats_updated.emit(stats)
            return stats

        except Exception as e:
            self.logger.error(f"[RECOVERY] 获取统计失败: {e}")
            return RecoveryStats()

    def cleanup_old_backups(self, days: int = 30) -> int:
        """
        清理过期备份

        Args:
            days: 保留天数

        Returns:
            清理的备份数量
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 查找过期备份（假设已恢复的）
            cursor.execute('''
                UPDATE recovery_log
                SET backup_path = NULL
                WHERE restored = 1 AND timestamp < ?
                AND backup_path IS NOT NULL
            ''', (cutoff.isoformat(),))

            deleted = cursor.rowcount

            # 删除文件系统中的备份文件
            # 这里需要遍历备份目录并删除过期文件
            deleted_file_count = self._cleanup_orphaned_files(days)

            conn.commit()
            conn.close()

            self.logger.info(f"[RECOVERY] 清理过期备份: 删除 {deleted} 数据记录, {deleted_file_count} 文件")
            self.cleanup_completed.emit(deleted + deleted_file_count)

            return deleted + deleted_file_count

        except Exception as e:
            self.logger.error(f"[RECOVERY] 清理过期备份失败: {e}")
            return 0

    def _cleanup_orphaned_files(self, days: int) -> int:
        """清理孤立备份文件（记录中已不存在或过期）

        Args:
            days: 文件保留天数

        Returns:
            清理的文件数量
        """
        try:
            backup_root = self.backup_mgr.backup_root
            now = time.time()
            cutoff = now - (days * 24 * 3600)
            count = 0

            # 清理硬链接目录
            hardlink_dir = os.path.join(backup_root, 'hardlinks')
            if os.path.exists(hardlink_dir):
                for filename in os.listdir(hardlink_dir):
                    file_path = os.path.join(hardlink_dir, filename)
                    file_stat = os.stat(file_path)
                    if file_stat.st_mtime < cutoff:
                        # 删除文件（实际上是减少引用计数）
                        try:
                            os.remove(file_path)
                            count += 1
                        except Exception as e:
                            self.logger.debug(f"[RECOVERY] 清理文件失败: {file_path}, {e}")

            # 清理完整备份目录
            full_dir = os.path.join(backup_root, 'full')
            if os.path.exists(full_dir):
                for filename in os.listdir(full_dir):
                    file_path = os.path.join(full_dir, filename)
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        if file_stat.st_mtime < cutoff:
                            try:
                                os.remove(file_path)
                                count += 1
                            except Exception as e:
                                self.logger.debug(f"[RECOVERY] 清理文件失败: {file_path}, {e}")
                    elif os.path.isdir(file_path):
                        dir_stat = os.stat(file_path)
                        if dir_stat.st_mtime < cutoff:
                            try:
                                shutil.rmtree(file_path)
                                count += 1
                            except Exception as e:
                                self.logger.debug(f"[RECOVERY] 清理目录失败: {file_path}, {e}")

            return count

        except Exception as e:
            self.logger.error(f"[RECOVERY] 清理孤立文件失败: {e}")
            return 0

    def _get_original_path_from_backup(self, backup_path: str) -> Optional[str]:
        """从备份路径推断原始路径

        Args:
            backup_path: 备份路径

        Returns:
            原始路径，无法推断返回 None
        """
        # 备份路径格式: backup_root/{type}/app_name_hash.ext
        # 很难准确还原，尝试从数据库查询
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT cp.path
                FROM recovery_log r
                JOIN cleanup_plan_items cp ON r.item_id = cp.item_id
                WHERE r.backup_path = ?
                LIMIT 1
            ''', (backup_path,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return row['path']

        except Exception as e:
            self.logger.debug(f"[RECOVERY] 无法推断原始路径: {backup_path}, {e}")

        return None

    def delete_backup(self, backup_id: str) -> bool:
        """删除备份

        Args:
            backup_id: 备份 ID

        Returns:
            是否成功
        """
        return self.backup_mgr.delete_backup(backup_id)

    def get_backup_stats_by_risk(self) -> Dict[str, int]:
        """按风险等级统计备份

        Returns:
            风险等级统计字典 {risk: count}
        """
        stats = {
            RiskLevel.SAFE.value: 0,
            RiskLevel.SUSPICIOUS.value: 0,
            RiskLevel.DANGEROUS.value: 0
        }

        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT cp.ai_risk, COUNT(*) as count
                FROM recovery_log r
                JOIN cleanup_plan_items cp ON r.item_id = cp.item_id
                GROUP BY cp.ai_risk
            ''')

            for row in cursor.fetchall():
                stats[row['ai_risk']] = stats.get(row['ai_risk'], 0) + row['count']

            conn.close()

        except Exception as e:
            self.logger.error(f"[RECOVERY] 获取风险统计失败: {e}")

        return stats

    def get_backup_stats_by_type(self) -> Dict[str, int]:
        """按备份类型统计备份

        Returns:
            备份类型统计字典 {type: count}
        """
        stats = {
            BackupType.HARDLINK.value: 0,
            BackupType.FULL.value: 0,
            BackupType.NONE.value: 0
        }

        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT backup_type, COUNT(*) as count
                FROM recovery_log
                GROUP BY backup_type
            ''')

            for row in cursor.fetchall():
                stats[row['backup_type']] = stats.get(row['backup_type'], 0) + row['count']

            conn.close()

        except Exception as e:
            self.logger.error(f"[RECOVERY] 获取类型统计失败: {e}")

        return stats

    def search_backups(
        self,
        keyword: str,
        limit: int = 50
    ) -> List[BackupInfo]:
        """搜索备份

        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            匹配的备份列表
        """
        keyword_lower = keyword.lower()

        # 先尝试精确匹配文件名
        backups = self.get_backup_history(limit=limit, offset=0)

        # 筛选
        filtered = []
        for backup in backups:
            if backup.original_path and keyword_lower in backup.original_path.lower():
                filtered.append(backup)
            elif keyword_lower in backup.backup_path.lower():
                filtered.append(backup)

        return filtered


# 便利函数
def get_recovery_manager(
    backup_mgr: Optional[BackupManager] = None,
    db: Optional[Database] = None
) -> RecoveryManager:
    """获取恢复管理器实例

    Args:
        backup_mgr: 备份管理器
        db: 数据库实例

    Returns:
        RecoveryManager 实例
    """
    return RecoveryManager(backup_mgr=backup_mgr, db=db)
