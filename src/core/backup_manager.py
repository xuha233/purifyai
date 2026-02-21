"""
备份管理器 (Backup Manager)

Phase 3 Day 5.5 MVP功能:
- 等级差异化备份（Safe不备份、Suspicious硬链接、Dangerous完整）
- 备份记录管理
- 自动清理（7天）
- 恢复功能

问题4修复 - 完整BackupManager设计
"""
import os
import shutil
import sqlite3
import hashlib
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from PyQt5.QtCore import QObject, pyqtSignal

from .rule_engine import RiskLevel
from .models_smart import CleanupItem, BackupInfo, BackupType, RecoveryRecord
from .database import Database, get_database
from utils.logger import get_logger

logger = get_logger(__name__)


class BackupError(Exception):
    """备份错误"""
    pass


@dataclass
class BackupStats:
    """备份统计"""
    total_backups: int = 0
    hardlink_backups: int = 0
    full_backups: int = 0
    total_size: int = 0
    restored_count: int = 0


class BackupManager(QObject):
    """备份管理器

    提供差异化的备份策略：
    - Safe: 不备份（可以直接删除）
    - Suspicious: 硬链接备份（节省空间，几KB）
    - Dangerous: 完整备份（确保可恢复）

    支持自动清理旧备份（默认7天）

    Signals:
        backup_created: BackupInfo - 备份创建成功
        backup_failed: (str, str) - (item_path, error_message)
        backup_restored: BackupInfo - 备份恢复成功
        backup_deleted: str - backup_id deleted
        cleanup_completed: int - number of backups cleaned
    """

    backup_created = pyqtSignal(object)      # BackupInfo
    backup_failed = pyqtSignal(str, str)     # path, error
    backup_restored = pyqtSignal(object)    # BackupInfo
    backup_deleted = pyqtSignal(str)        # backup_id
    cleanup_completed = pyqtSignal(int)      # count

    def __init__(self, backup_root: Optional[str] = None, db: Optional[Database] = None):
        """初始化备份管理器

        Args:
            backup_root: 备份根目录
            db: 数据库实例
        """
        super().__init__()

        if backup_root is None:
            # 默认使用 %APPDATA%/Local/PurifyAI/Backups
            app_path = os.environ.get('LOCALAPPDATA', '')
            if app_path:
                backup_root = os.path.join(app_path, 'PurifyAI', 'Backups')
            else:
                backup_root = os.path.expanduser('~/PurifyAI/Backups')

        self.backup_root = backup_root
        self.db = db or get_database()

        self.logger = logger
        self._stats = BackupStats()

        # 内存缓存备份信息（用于 restore/delete 操作，不依赖数据库）
        self._backup_cache: Dict[str, BackupInfo] = {}

        # 确保备份目录存在
        os.makedirs(self.backup_root, exist_ok=True)
        os.makedirs(os.path.join(self.backup_root, 'hardlinks'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_root, 'full'), exist_ok=True)

        self.logger.info(f"[BACKUP] 备份管理器初始化完成: {self.backup_root}")

    def create_backup(self, item: CleanupItem) -> Optional[BackupInfo]:
        """创建备份（差异化策略）

        Args:
            item: 清理项

        Returns:
            BackupInfo 备份成功，None 不需要备份或失败
        """
        # 根据风险等级选择备份策略
        backup_type = BackupType.from_risk(item.ai_risk)

        if backup_type == BackupType.NONE:
            # Safe 项不备份
            self.logger.debug(f"[BACKUP] Safe项跳过备份: {item.path}")
            return None

        elif backup_type == BackupType.HARDLINK:
            # Suspicious: 创建硬链接
            return self._create_hardlink(item)

        else:  # BackupType.FULL
            # Dangerous: 完整备份
            return self._create_full_backup(item)

    def _create_hardlink(self, item: CleanupItem) -> Optional[BackupInfo]:
        """创建硬链接备份

        Args:
            item: 清理项

        Returns:
            BackupInfo 备份信息，失败返回 None
        """
        if not os.path.exists(item.path):
            self.logger.warning(f"[BACKUP] 源文件不存在，无法创建硬链接: {item.path}")
            return None

        try:
            # 创建唯一备份路径
            backup_name = self._generate_backup_name(item)
            backup_path = os.path.join(self.backup_root, 'hardlinks', backup_name)

            # 尝试创建硬链接
            os.link(item.path, backup_path)

            # 创建备份记录
            backup_info = BackupInfo.create(item, backup_path, BackupType.HARDLINK)

            # 保存到缓存和数据库
            self._backup_cache[backup_info.backup_id] = backup_info
            self._save_backup_to_db(backup_info)

            self._stats.hardlink_backups += 1
            self._stats.total_backups += 1

            # 获取文件大小
            backup_size = os.path.getsize(backup_path)
            self._stats.total_size += backup_size

            self.logger.info(f"[BACKUP] 硬链接备份创建成功: {item.path} -> {backup_name}")
            self.backup_created.emit(backup_info)

            return backup_info

        except OSError as e:
            error_msg = f"硬链接备份失败: {str(e)}"
            self.logger.error(f"[BACKUP] {error_msg}: {item.path}")
            self.backup_failed.emit(item.path, error_msg)

            # 回退到完整备份
            self.logger.info(f"[BACKUP] 回退到完整备份: {item.path}")
            return self._create_full_backup(item)

        except Exception as e:
            error_msg = f"备份失败: {str(e)}"
            self.logger.error(f"[BACKUP] {error_msg}: {item.path}")
            self.backup_failed.emit(item.path, error_msg)
            return None

    def _create_full_backup(self, item: CleanupItem) -> Optional[BackupInfo]:
        """创建完整备份

        Args:
            item: 清理项

        Returns:
            BackupInfo 备份信息，失败返回 None
        """
        if not os.path.exists(item.path):
            self.logger.warning(f"[BACKUP] 源文件不存在，无法创建完整备份: {item.path}")
            return None

        try:
            # 创建唯一备份路径
            backup_name = self._generate_backup_name(item)
            backup_path = os.path.join(self.backup_root, 'full', backup_name)

            # 复制文件
            if os.path.isfile(item.path):
                shutil.copy2(item.path, backup_path)
            else:  # 目录
                shutil.copytree(item.path, backup_path)

            # 创建备份记录
            backup_info = BackupInfo.create(item, backup_path, BackupType.FULL)

            # 保存到缓存和数据库
            self._backup_cache[backup_info.backup_id] = backup_info
            self._save_backup_to_db(backup_info)

            self._stats.full_backups += 1
            self._stats.total_backups += 1

            # 获取备份大小
            backup_size = os.path.getsize(backup_path) if os.path.isfile(backup_path) else 0
            if os.path.isdir(backup_path):
                backup_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(backup_path)
                    for filename in filenames
                )

            self._stats.total_size += backup_size

            self.logger.info(f"[BACKUP] 完整备份创建成功: {item.path} -> {backup_name}")
            self.backup_created.emit(backup_info)

            return backup_info

        except Exception as e:
            error_msg = f"完整备份失败: {str(e)}"
            self.logger.error(f"[BACKUP] {error_msg}: {item.path}")
            self.backup_failed.emit(item.path, error_msg)
            return None

    def _generate_backup_name(self, item: CleanupItem) -> str:
        """生成备份文件名

        Args:
            item: 清理项

        Returns:
            备份文件名
        """
        # 使用 item_id 和路径生成唯一名称
        path_hash = hashlib.md5(item.path.encode('utf-8')).hexdigest()[:8]
        filename = os.path.basename(item.path)
        base, ext = os.path.splitext(filename)

        return f"{base}_{path_hash}{ext}"

    def _save_backup_to_db(self, backup_info: BackupInfo):
        """保存备份信息到数据库

        Args:
            backup_info: 备份信息
        """
        try:
            self.db.add_recovery_log(
                plan_id="unknown",  # 将由调用方设置
                item_id=backup_info.item_id,
                original_path="",  # 将由调用方设置
                backup_path=backup_info.backup_path,
                backup_type=backup_info.backup_type.value
            )
        except Exception as e:
            self.logger.warning(f"[BACKUP] 保存备份记录失败 (非致命): {e}")

    def restore_backup(self, backup_id: str, destination: Optional[str] = None) -> bool:
        """恢复备份

        Args:
            backup_id: 备份ID
            destination: 恢复目标路径，None 恢复到原路径

        Returns:
            是否成功
        """
        # 优先从缓存获取备份信息
        backup_info = self._backup_cache.get(backup_id)
        if not backup_info:
            # 回退到数据库查询
            backup_info = self._get_backup_info(backup_id)

        if not backup_info:
            self.logger.error(f"[BACKUP] 备份不存在: {backup_id}")
            return False

        try:
            if not os.path.exists(backup_info.backup_path):
                self.logger.error(f"[BACKUP] 备份文件不存在: {backup_info.backup_path}")
                return False

            # 确定目标路径（优先使用 BackupInfo 中的 original_path）
            if destination:
                target_path = destination
            elif backup_info.original_path:
                target_path = backup_info.original_path
            else:
                # 回退到数据库查询
                target_path = self._get_original_path(backup_id)
                if not target_path:
                    self.logger.error(f"[BACKUP] 无法确定恢复路径: {backup_id}")
                    return False

            parent_dir = os.path.dirname(target_path)
            os.makedirs(parent_dir, exist_ok=True)

            # 恢复文件
            if os.path.isfile(backup_info.backup_path):
                shutil.copy2(backup_info.backup_path, target_path)
            else:  # 目录
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                shutil.copytree(backup_info.backup_path, target_path)

            # 更新恢复状态
            backup_info.restored = True
            backup_info.restored_at = datetime.now()
            self._stats.restored_count += 1

            self.logger.info(f"[BACKUP] 备份恢复成功: {backup_id} -> {target_path}")
            self.backup_restored.emit(backup_info)

            return True

        except Exception as e:
            error_msg = f"恢复备份失败: {str(e)}"
            self.logger.error(f"[BACKUP] {error_msg}: {backup_id}")
            return False

    def delete_backup(self, backup_id: str) -> bool:
        """删除备份

        Args:
            backup_id: 备份ID

        Returns:
            是否成功
        """
        backup_info = self._get_backup_info(backup_id)
        if not backup_info:
            return False

        try:
            if os.path.exists(backup_info.backup_path):
                if os.path.isfile(backup_info.backup_path):
                    os.remove(backup_info.backup_path)
                else:
                    shutil.rmtree(backup_info.backup_path)

            # 从缓存中移除
            if backup_id in self._backup_cache:
                del self._backup_cache[backup_id]

            self.logger.info(f"[BACKUP] 备份已删除: {backup_id}")
            self.backup_deleted.emit(backup_id)

            return True

        except Exception as e:
            self.logger.error(f"[BACKUP] 删除备份失败 {backup_id}: {e}")
            return False

    def cleanup_old_backups(self, days: int = 7) -> int:
        """清理旧备份

        Args:
            days: 保留天数

        Returns:
            清理的备份数量
        """
        cutoff = datetime.now() - timedelta(days=days)
        count = 0

        # 扫描硬链接备份目录
        for filename in os.listdir(os.path.join(self.backup_root, 'hardlinks')):
            file_path = os.path.join(self.backup_root, 'hardlinks', filename)
            try:
                file_stat = os.stat(file_path)
                file_time = datetime.fromtimestamp(file_stat.st_mtime)

                if file_time < cutoff:
                    os.remove(file_path)
                    count += 1
                    self.logger.debug(f"[BACKUP] 清理旧备份: {filename}")
            except Exception as e:
                self.logger.warning(f"[BACKUP] 清理失败 {filename}: {e}")

        # 扫描完整备份目录
        for filename in os.listdir(os.path.join(self.backup_root, 'full')):
            file_path = os.path.join(self.backup_root, 'full', filename)
            try:
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    file_time = datetime.fromtimestamp(file_stat.st_mtime)

                    if file_time < cutoff:
                        os.remove(file_path)
                        count += 1
                        self.logger.debug(f"[BACKUP] 清理旧备份: {filename}")
                elif os.path.isdir(file_path):
                    # 对于目录，检查目录的修改时间
                    dir_stat = os.stat(file_path)
                    dir_time = datetime.fromtimestamp(dir_stat.st_mtime)

                    if dir_time < cutoff:
                        shutil.rmtree(file_path)
                        count += 1
                        self.logger.debug(f"[BACKUP] 清理旧备份目录: {filename}")
            except Exception as e:
                self.logger.warning(f"[BACKUP] 清理失败 {filename}: {e}")

        self.cleanup_completed.emit(count)
        self.logger.info(f"[BACKUP] 清理旧备份完成: {count} 个文件")

        return count

    def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """获取备份信息

        Args:
            backup_id: 备份ID

        Returns:
            BackupInfo
        """
        return self._get_backup_info(backup_id)

    def _get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """从数据库获取备份信息

        Args:
            backup_id: 备份ID

        Returns:
            BackupInfo
        """
        # 优先从缓存中查询
        if backup_id in self._backup_cache:
            return self._backup_cache[backup_id]

        # 从 recovery_log 表查询
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM recovery_log WHERE id = ?
            ''', (backup_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                backup_info = BackupInfo(
                    backup_id=row['id'],
                    item_id=row['item_id'],
                    backup_path=row['backup_path'],
                    backup_type=BackupType.from_value(row['backup_type']),
                    created_at=datetime.fromisoformat(row['timestamp']),
                    restored=bool(row['restored'])
                )
                # 也添加到缓存
                self._backup_cache[backup_id] = backup_info
                return backup_info
        except Exception as e:
            self.logger.error(f"[BACKUP] 查询备份信息失败: {e}")

        return None

    def _get_original_path(self, backup_id: str) -> Optional[str]:
        """获取原始路径

        Args:
            backup_id: 备份ID

        Returns:
            原始路径
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT original_path FROM recovery_log WHERE id = ?
            ''', (backup_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return row['original_path']
        except Exception as e:
            self.logger.error(f"[BACKUP] 查询原始路径失败: {e}")

        return None

    def get_backup_list(self) -> List[BackupInfo]:
        """获取所有备份列表

        Returns:
            备份列表
        """
        backups = []

        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM recovery_log ORDER BY timestamp DESC
            ''')

            for row in cursor.fetchall():
                backups.append(BackupInfo(
                    backup_id=row['id'],
                    item_id=row['item_id'],
                    backup_path=row['backup_path'],
                    backup_type=BackupType.from_value(row['backup_type']),
                    created_at=datetime.fromisoformat(row['timestamp']),
                    restored=bool(row['restored'])
                ))

            conn.close()

        except Exception as e:
            self.logger.error(f"[BACKUP] 获取备份列表失败: {e}")

        return backups

    def get_stats(self) -> BackupStats:
        """获取备份统计

        Returns:
            BackupStats
        """
        # 更新统计信息
        self._update_stats()
        return self._stats

    def _update_stats(self):
        """更新统计信息"""
        try:
            hardlink_dir = os.path.join(self.backup_root, 'hardlinks')
            full_dir = os.path.join(self.backup_root, 'full')

            self._stats.hardlink_backups = len(os.listdir(hardlink_dir)) if os.path.exists(hardlink_dir) else 0
            self._stats.full_backups = len(os.listdir(full_dir)) if os.path.exists(full_dir) else 0
            self._stats.total_backups = self._stats.hardlink_backups + self._stats.full_backups

            # 计算总大小
            self._stats.total_size = 0
            if os.path.exists(hardlink_dir):
                for filename in os.listdir(hardlink_dir):
                    file_path = os.path.join(hardlink_dir, filename)
                    if os.path.isfile(file_path):
                        self._stats.total_size += os.path.getsize(file_path)

            if os.path.exists(full_dir):
                for filename in os.listdir(full_dir):
                    file_path = os.path.join(full_dir, filename)
                    if os.path.isfile(file_path):
                        self._stats.total_size += os.path.getsize(file_path)

            # 从数据库获取恢复数量
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM recovery_log WHERE restored = 1')
            row = cursor.fetchone()
            if row:
                self._stats.restored_count = row['count']
            conn.close()

        except Exception as e:
            self.logger.warning(f"[BACKUP] 更新统计信息失败: {e}")

    def get_stats_report(self) -> str:
        """获取统计报告

        Returns:
            报告文本
        """
        stats = self.get_stats()

        return (
            f"备份统计:\n"
            f"  总备份数: {stats.total_backups}\n"
            f"  硬链接备份: {stats.hardlink_backups}\n"
            f"  完整备份: {stats.full_backups}\n"
            f"  总大小: {self._format_size(stats.total_size)}\n"
            f"  已恢复: {stats.restored_count}"
        )

    def _format_size(self, size: int) -> str:
        """格式化大小

        Args:
            size: 大小（字节）

        Returns:
            格式化字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


# 便利函数
def get_backup_manager(backup_root: Optional[str] = None) -> BackupManager:
    """获取备份管理器实例

    Args:
        backup_root: 备份根目录

    Returns:
        BackupManager 实例
    """
    return BackupManager(backup_root)
