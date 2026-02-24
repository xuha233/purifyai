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
import zipfile
import uuid
import fnmatch
from typing import List, Optional, Dict
from dataclasses import dataclass, field, asdict
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


@dataclass
class BackupFileInfo:
    """备份文件信息

    Attributes:
        original_path: 原始文件路径
        backup_path: 备份文件路径
        size: 文件大小（字节）
        compressed_size: 压缩后大小（字节）
        checksum: SHA256 校验和
        permissions: 文件权限
        modified_time: 最后修改时间（时间戳）
        is_directory: 是否为目录
    """
    original_path: str
    backup_path: str
    size: int
    compressed_size: int = 0
    checksum: str = ""
    permissions: int = 0o644
    modified_time: float = 0.0
    is_directory: bool = False

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'BackupFileInfo':
        """从字典创建"""
        return cls(**data)


@dataclass
class BackupManifest:
    """备份清单

    Attributes:
        manifest_id: 清单ID
        backup_id: 备份ID
        files: 文件信息列表
        total_size: 总大小（字节）
        compressed_size: 压缩后大小（字节）
        zip_path: 压缩包路径
        created_at: 创建时间
        profile_id: 关联的备份配置ID（可选）
    """
    manifest_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    backup_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    files: List[BackupFileInfo] = field(default_factory=list)
    total_size: int = 0
    compressed_size: int = 0
    zip_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    profile_id: Optional[str] = None

    def add_file_info(self, file_info: BackupFileInfo):
        """添加文件信息并更新统计"""
        self.files.append(file_info)
        self.total_size += file_info.size
        self.compressed_size += file_info.compressed_size

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'manifest_id': self.manifest_id,
            'backup_id': self.backup_id,
            'files': [f.to_dict() for f in self.files],
            'total_size': self.total_size,
            'compressed_size': self.compressed_size,
            'zip_path': self.zip_path,
            'created_at': self.created_at.isoformat(),
            'profile_id': self.profile_id
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BackupManifest':
        """从字典创建"""
        files_data = data.get('files', [])
        files = [BackupFileInfo.from_dict(f) for f in files_data]

        return cls(
            manifest_id=data.get('manifest_id', ''),
            backup_id=data.get('backup_id', ''),
            files=files,
            total_size=data.get('total_size', 0),
            compressed_size=data.get('compressed_size', 0),
            zip_path=data.get('zip_path', ''),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            profile_id=data.get('profile_id')
        )

    def save(self, filepath: str):
        """保存清单到文件"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> 'BackupManifest':
        """从文件加载清单"""
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class BackupProfile:
    """备份配置

    Attributes:
        profile_id: 配置ID
        name: 备份配置名称
        backup_paths: 备份路径列表
        exclude_patterns: 排除模式（支持 glob 通配符）
        compression_level: 压缩级别 (0-9)
        retention_days: 保留天数
        max_versions: 最大版本数
        schedule: 备份计划 (简单格式: "daily", "weekly", 或 cron 表达式)
        enabled: 是否启用
        created_at: 创建时间
        updated_at: 更新时间
    """
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "default"
    backup_paths: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    compression_level: int = 6
    retention_days: int = 30
    max_versions: int = 10
    schedule: str = "daily"
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'BackupProfile':
        """从字典创建"""
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            profile_id=data.get('profile_id', ''),
            name=data.get('name', 'default'),
            backup_paths=data.get('backup_paths', []),
            exclude_patterns=data.get('exclude_patterns', []),
            compression_level=data.get('compression_level', 6),
            retention_days=data.get('retention_days', 30),
            max_versions=data.get('max_versions', 10),
            schedule=data.get('schedule', 'daily'),
            enabled=data.get('enabled', True),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now()
        )

    def save(self, filepath: str):
        """保存配置到文件"""
        import json
        self.updated_at = datetime.now()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> 'BackupProfile':
        """从文件加载配置"""
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


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

    # ========================================================================
    # 新增方法 - Part 1: BackupManager Enhancement
    # ========================================================================

    @staticmethod
    def _calculate_checksum(file_path: str) -> str:
        """计算文件的 SHA256 校验和

        Args:
            file_path: 文件路径

        Returns:
            SHA256 十六进制字符串
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                # 分块读取以支持大文件
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ""

    @staticmethod
    def _get_file_metadata(file_path: str) -> Dict:
        """获取文件元数据

        Args:
            file_path: 文件路径

        Returns:
            包含权限、修改时间等元数据的字典
        """
        try:
            stat_info = os.stat(file_path)
            return {
                'permissions': stat_info.st_mode,
                'modified_time': stat_info.st_mtime,
                'is_directory': os.path.isdir(file_path),
                'size': stat_info.st_size if os.path.isfile(file_path) else 0
            }
        except Exception:
            return {
                'permissions': 0o644,
                'modified_time': 0.0,
                'is_directory': False,
                'size': 0
            }

    def _generate_backup_id(self, prefix: str = "backup") -> str:
        """生成唯一备份ID

        Args:
            prefix: ID前缀

        Returns:
            备份ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{unique_suffix}"

    def _matches_exclude_pattern(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """检查文件是否匹配排除模式

        Args:
            file_path: 文件路径
            exclude_patterns: 排除模式列表

        Returns:
            是否匹配
        """
        filename = os.path.basename(file_path)

        for pattern in exclude_patterns:
            # 支持通配符匹配
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True

        return False

    def backup_profile(self, profile: BackupProfile, files: Optional[List[str]] = None) -> BackupManifest:
        """根据配置创建备份

        Args:
            profile: 备份配置
            files: 要备份的文件列表，None则使用profile中的backup_paths

        Returns:
            BackupManifest 备份清单
        """
        self.logger.info(f"[BACKUP] 开始配置备份: {profile.name}")

        # 确定要备份的文件列表
        if files is None:
            files = profile.backup_paths

        # 创建备份清单
        manifest = BackupManifest(
            backup_id=self._generate_backup_id(f"profile_{profile.name}"),
            profile_id=profile.profile_id
        )

        # 创建临时目录用于备份
        temp_backup_dir = os.path.join(self.backup_root, f".temp_{manifest.backup_id}")
        os.makedirs(temp_backup_dir, exist_ok=True)

        try:
            # 收集所有文件信息并复制到临时目录
            file_infos = []
            for file_path in files:
                self._backup_file_recursive(
                    file_path=file_path,
                    temp_backup_dir=temp_backup_dir,
                    exclude_patterns=profile.exclude_patterns,
                    file_infos=file_infos,
                    manifest=manifest
                )

            if not file_infos:
                self.logger.warning(f"[BACKUP] 没有文件需要备份: {profile.name}")
                return manifest

            # 创建压缩包
            manifest.zip_path = self._create_backup_zip(
                backup_id=manifest.backup_id,
                temp_backup_dir=temp_backup_dir,
                compression_level=profile.compression_level
            )

            self.logger.info(
                f"[BACKUP] 配份备份完成: {profile.name} - "
                f"{len(file_infos)} 个文件, {self._format_size(manifest.compressed_size)}"
            )

        except Exception as e:
            self.logger.error(f"[BACKUP] 配份备份失败: {profile.name}: {e}")
            # 清理临时文件
            if os.path.exists(temp_backup_dir):
                shutil.rmtree(temp_backup_dir)
            raise
        finally:
            # 清理临时目录
            if os.path.exists(temp_backup_dir):
                shutil.rmtree(temp_backup_dir)

        return manifest

    def _backup_file_recursive(self, file_path: str, temp_backup_dir: str,
                                 exclude_patterns: List[str],
                                 file_infos: List[BackupFileInfo],
                                 manifest: BackupManifest):
        """递归备份文件

        Args:
            file_path: 文件/目录路径
            temp_backup_dir: 临时备份目录
            exclude_patterns: 排除模式列表
            file_infos: 文件信息列表（会更新）
            manifest: 备份清单（会更新）
        """
        if not os.path.exists(file_path):
            self.logger.warning(f"[BACKUP] 文件不存在，跳过: {file_path}")
            return

        # 检查排除模式
        if self._matches_exclude_pattern(file_path, exclude_patterns):
            self.logger.debug(f"[BACKUP] 匹配排除模式，跳过: {file_path}")
            return

        if os.path.isfile(file_path):
            # 备份单个文件
            file_info = self._backup_single_file(file_path, temp_backup_dir)
            if file_info:
                file_infos.append(file_info)
                manifest.add_file_info(file_info)
        elif os.path.isdir(file_path):
            # 递归备份目录
            for root, dirs, files in os.walk(file_path):
                # 过滤排除的子目录
                dirs[:] = [d for d in dirs if not self._matches_exclude_pattern(
                    os.path.join(root, d), exclude_patterns)]

                for filename in files:
                    full_path = os.path.join(root, filename)
                    if self._matches_exclude_pattern(full_path, exclude_patterns):
                        continue

                    file_info = self._backup_single_file(full_path, temp_backup_dir)
                    if file_info:
                        file_infos.append(file_info)
                        manifest.add_file_info(file_info)

    def _backup_single_file(self, file_path: str, temp_backup_dir: str) -> Optional[BackupFileInfo]:
        """备份单个文件

        Args:
            file_path: 源文件路径
            temp_backup_dir: 临时备份目录

        Returns:
            BackupFileInfo 备份成功，None 失败
        """
        try:
            # 获取文件元数据
            metadata = self._get_file_metadata(file_path)

            # 创建相对路径用于备份
            # 对于 Windows 驱动器，需要处理驱动器号
            relative_path = file_path
            if os.name == 'nt' and len(file_path) > 2 and file_path[1] == ':':
                relative_path = file_path[2:].lstrip('\\/')

            # 确保相对路径不以 / 或 \ 开头
            relative_path = relative_path.lstrip('\\/')

            # 在临时目录创建文件
            backup_file_path = os.path.join(temp_backup_dir, relative_path)
            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)

            # 复制文件
            shutil.copy2(file_path, backup_file_path)

            # 获取压缩后大小（预先估算：假设压缩率50%用于初步计数）
            compressed_size = os.path.getsize(backup_file_path)

            # 计算校验和
            checksum = self._calculate_checksum(file_path)

            return BackupFileInfo(
                original_path=file_path,
                backup_path=backup_file_path,
                size=metadata['size'],
                compressed_size=compressed_size,
                checksum=checksum,
                permissions=metadata['permissions'],
                modified_time=metadata['modified_time'],
                is_directory=metadata['is_directory']
            )

        except Exception as e:
            self.logger.error(f"[BACKUP] 备份文件失败 {file_path}: {e}")
            return None

    def _create_backup_zip(self, backup_id: str, temp_backup_dir: str,
                            compression_level: int = 6) -> str:
        """创建压缩备份

        Args:
            backup_id: 备份ID
            temp_backup_dir: 临时备份目录
            compression_level: 压缩级别 (0-9)

        Returns:
            压缩包路径
        """
        # 创建 manifest 目录
        manifest_dir = os.path.join(self.backup_root, 'manifests')
        os.makedirs(manifest_dir, exist_ok=True)

        # 创建压缩包路径
        zip_path = os.path.join(self.backup_root, f"{backup_id}.zip")

        # 映射：原始路径 -> BackupFileInfo
        file_info_map = {}
        for root, dirs, files in os.walk(temp_backup_dir):
            for filename in files:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, temp_backup_dir)
                file_info_map[rel_path] = abs_path

        # 创建 ZIP 文件
        with zipfile.ZipFile(
            zip_path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compression_level
        ) as zf:
            for rel_path, abs_path in file_info_map.items():
                zf.write(abs_path, arcname=rel_path)

        self.logger.info(f"[BACKUP] 压缩包创建完成: {zip_path}")
        return zip_path

    def backup_system(self, paths: List[str], exclude: List[str] = None,
                       name: str = "system") -> BackupManifest:
        """系统级备份

        Args:
            paths: 要备份的路径列表
            exclude: 排除模式列表
            name: 备份名称

        Returns:
            BackupManifest 备份清单
        """
        if exclude is None:
            exclude = []

        self.logger.info(f"[BACKUP] 开始系统备份: {name}, 路径数量: {len(paths)}")

        # 创建临时配置
        profile = BackupProfile(
            name=name,
            backup_paths=paths,
            exclude_patterns=exclude,
            compression_level=6
        )

        return self.backup_profile(profile)

    def restore_from_manifest(self, manifest: BackupManifest,
                               files: Optional[List[str]] = None,
                               restore_to_root: Optional[str] = None) -> Dict[str, bool]:
        """从清单恢复文件

        Args:
            manifest: 备份清单
            files: 要恢复的文件列表，None表示恢复所有
            restore_to_root: 恢复目标根目录，None表示恢复到原路径

        Returns:
            字典 {original_path: success} 表示恢复结果
        """
        self.logger.info(f"[BACKUP] 开始从清单恢复: {manifest.manifest_id}")

        if not os.path.exists(manifest.zip_path):
            self.logger.error(f"[BACKUP] 压缩包不存在: {manifest.zip_path}")
            return {}

        results = {}

        # 过滤要恢复的文件
        files_to_restore = files if files else [f.original_path for f in manifest.files]

        # 查找要恢复的文件信息
        file_map = {f.original_path: f for f in manifest.files}

        # 创建临时目录
        temp_restore_dir = os.path.join(self.backup_root, f".temp_restore_{manifest.manifest_id}")
        os.makedirs(temp_restore_dir, exist_ok=True)

        try:
            # 解压到临时目录
            with zipfile.ZipFile(manifest.zip_path, 'r') as zf:
                zf.extractall(temp_restore_dir)

            # 恢复文件
            for original_path in files_to_restore:
                file_info = file_map.get(original_path)

                if not file_info:
                    self.logger.warning(f"[BACKUP] 文件不在清单中: {original_path}")
                    results[original_path] = False
                    continue

                try:
                    # 确定目标路径
                    if restore_to_root:
                        # 使用相对路径恢复到指定根目录
                        # 需要从备份路径中提取相对路径
                        rel_path = os.path.basename(file_info.backup_path)
                        # 这里的逻辑可能需要根据实际情况调整
                        target_path = os.path.join(restore_to_root, os.path.basename(original_path))
                    else:
                        # 恢复到原路径
                        target_path = original_path

                    # 在临时目录找到对应的备份文件
                    # 压缩包内的路径应该是相对路径
                    rel_backup_path = os.path.relpath(file_info.backup_path)

                    # 从临时目录解压的内容中查找文件
                    temp_file_path = os.path.join(temp_restore_dir, rel_backup_path)

                    if not os.path.exists(temp_file_path):
                        # 尝试另一种路径映射方式
                        # 在压缩包中，文件是按相对路径存储的
                        for file_info_entry in manifest.files:
                            temp_file_path = os.path.join(
                                temp_restore_dir,
                                os.path.basename(file_info_entry.backup_path)
                            )
                            if os.path.exists(temp_file_path):
                                break

                    if not os.path.exists(temp_file_path):
                        self.logger.error(f"[BACKUP] 临时文件不存在: {temp_file_path}")
                        results[original_path] = False
                        continue

                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    # 恢复文件
                    shutil.copy2(temp_file_path, target_path)

                    # 尝试设置权限
                    try:
                        os.chmod(target_path, file_info.permissions)
                    except Exception:
                        pass

                    self.logger.info(f"[BACKUP] 文件恢复成功: {original_path}")
                    results[original_path] = True

                except Exception as e:
                    self.logger.error(f"[BACKUP] 恢复文件失败 {original_path}: {e}")
                    results[original_path] = False

        except Exception as e:
            self.logger.error(f"[BACKUP] 从清单恢复失败: {e}")
        finally:
            # 清理临时目录
            if os.path.exists(temp_restore_dir):
                shutil.rmtree(temp_restore_dir)

        success_count = sum(1 for success in results.values() if success)
        self.logger.info(f"[BACKUP] 恢复完成: {success_count}/{len(results)} 个文件成功")

        return results

    def save_manifest(self, manifest: BackupManifest) -> str:
        """保存清单到文件

        Args:
            manifest: 备份清单

        Returns:
            清单文件路径
        """
        manifest_dir = os.path.join(self.backup_root, 'manifests')
        os.makedirs(manifest_dir, exist_ok=True)

        manifest_path = os.path.join(manifest_dir, f"{manifest.manifest_id}.json")
        manifest.save(manifest_path)

        return manifest_path

    def load_manifest(self, manifest_id: str) -> Optional[BackupManifest]:
        """从文件加载清单

        Args:
            manifest_id: 清单ID

        Returns:
            BackupManifest
        """
        manifest_dir = os.path.join(self.backup_root, 'manifests')
        manifest_path = os.path.join(manifest_dir, f"{manifest_id}.json")

        if not os.path.exists(manifest_path):
            return None

        try:
            return BackupManifest.load(manifest_path)
        except Exception as e:
            self.logger.error(f"[BACKUP] 加载清单失败: {e}")
            return None

    def get_backup_history(self, days: int = 30) -> List[BackupManifest]:
        """获取备份历史

        Args:
            days: 获取最近多少天的备份

        Returns:
            备份清单列表
        """
        cutoff = datetime.now() - timedelta(days=days)
        manifests = []

        manifest_dir = os.path.join(self.backup_root, 'manifests')

        if not os.path.exists(manifest_dir):
            return []

        for filename in os.listdir(manifest_dir):
            if not filename.endswith('.json'):
                continue

            manifest_path = os.path.join(manifest_dir, filename)

            try:
                # 检查文件修改时间
                file_stat = os.stat(manifest_path)
                file_time = datetime.fromtimestamp(file_stat.st_mtime)

                if file_time < cutoff:
                    continue

                # 加载清单
                manifest = BackupManifest.load(manifest_path)
                if manifest:
                    manifests.append(manifest)

            except Exception as e:
                self.logger.warning(f"[BACKUP] 加载清单失败 {filename}: {e}")

        # 按创建时间降序排序
        manifests.sort(key=lambda m: m.created_at, reverse=True)

        self.logger.info(f"[BACKUP] 找到 {len(manifests)} 个最近的备份 (最近 {days} 天)")

        return manifests

    def cleanup_old_backups(self, retention_days: int = 7,
                             max_versions: Optional[int] = None) -> Dict[str, int]:
        """清理旧备份

        增强版本，保留天数和最大版本数双重策略

        Args:
            retention_days: 保留天数
            max_versions: 每个配置保留的最大版本数，None表示不限

        Returns:
            清理统计: {
                'manifests_deleted': 删除的清单数,
                'zips_deleted': 删除的压缩包数,
                'legacy_files_deleted': 删除的旧格式文件数
            }
        """
        self.logger.info(f"[BACKUP] 清理旧备份: 保留{retention_days}天, 最大版本{max_versions or '不限'}")

        cutoff = datetime.now() - timedelta(days=retention_days)
        stats = {
            'manifests_deleted': 0,
            'zips_deleted': 0,
            'legacy_files_deleted': 0
        }

        # 1. 清理清单文件
        manifest_dir = os.path.join(self.backup_root, 'manifests')
        if os.path.exists(manifest_dir):
            # 按profile_id分组
            profile_backups = {}
            for filename in os.listdir(manifest_dir):
                if not filename.endswith('.json'):
                    continue

                manifest_path = os.path.join(manifest_dir, filename)
                try:
                    manifest = BackupManifest.load(manifest_path)
                    if manifest:
                        profile_id = manifest.profile_id or 'default'
                        if profile_id not in profile_backups:
                            profile_backups[profile_id] = []
                        profile_backups[profile_id].append((manifest, manifest_path))
                except Exception:
                    pass

            # 按策略清理
            for profile_id, backups in profile_backups.items():
                # 按创建时间排序（新的在前）
                backups.sort(key=lambda x: x[0].created_at, reverse=True)

                # 处理 max_versions 策略
                to_delete_by_version = []
                if max_versions:
                    to_delete_by_version = backups[max_versions:]

                # 处理 retention_days 策略
                to_delete_by_age = [b for b in backups if b[0].created_at < cutoff]

                # 合并并去重
                to_delete = set(to_delete_by_version) | set(to_delete_by_age)

                for manifest, manifest_path in to_delete:
                    try:
                        # 删除清单
                        os.remove(manifest_path)
                        stats['manifests_deleted'] += 1

                        # 删除对应的压缩包
                        if manifest.zip_path and os.path.exists(manifest.zip_path):
                            os.remove(manifest.zip_path)
                            stats['zips_deleted'] += 1

                        self.logger.debug(f"[BACKUP] 删除过期备份: {manifest.manifest_id}")

                    except Exception as e:
                        self.logger.warning(f"[BACKUP] 删除备份失败: {e}")

        # 2. 清理旧格式备份（保持向后兼容）
        legacy_files = self._cleanup_legacy_backups(days=retention_days)
        stats['legacy_files_deleted'] = legacy_files

        # 发出清理完成信号
        total_deleted = stats['manifests_deleted'] + stats['legacy_files_deleted']
        if total_deleted > 0:
            self.cleanup_completed.emit(total_deleted)

        self.logger.info(
            f"[BACKUP] 清理完成: 清单{stats['manifests_deleted']}个, "
            f"压缩包{stats['zips_deleted']}个, 旧格式{stats['legacy_files_deleted']}个"
        )

        return stats

    def _cleanup_legacy_backups(self, days: int = 7) -> int:
        """清理旧格式备份（向后兼容）

        Args:
            days: 保留天数

        Returns:
            清理的文件数量
        """
        cutoff = datetime.now() - timedelta(days=days)
        count = 0

        # 扫描硬链接备份目录
        hardlink_dir = os.path.join(self.backup_root, 'hardlinks')
        if os.path.exists(hardlink_dir):
            for filename in os.listdir(hardlink_dir):
                file_path = os.path.join(hardlink_dir, filename)
                try:
                    file_stat = os.stat(file_path)
                    file_time = datetime.fromtimestamp(file_stat.st_mtime)

                    if file_time < cutoff:
                        os.remove(file_path)
                        count += 1
                        self.logger.debug(f"[BACKUP] 清理旧硬链接备份: {filename}")
                except Exception as e:
                    self.logger.warning(f"[BACKUP] 清理失败 {filename}: {e}")

        # 扫描完整备份目录
        full_dir = os.path.join(self.backup_root, 'full')
        if os.path.exists(full_dir):
            for filename in os.listdir(full_dir):
                file_path = os.path.join(full_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        file_time = datetime.fromtimestamp(file_stat.st_mtime)

                        if file_time < cutoff:
                            os.remove(file_path)
                            count += 1
                            self.logger.debug(f"[BACKUP] 清理旧完整备份: {filename}")
                    elif os.path.isdir(file_path):
                        dir_stat = os.stat(file_path)
                        dir_time = datetime.fromtimestamp(dir_stat.st_mtime)

                        if dir_time < cutoff:
                            shutil.rmtree(file_path)
                            count += 1
                            self.logger.debug(f"[BACKUP] 清理旧备份目录: {filename}")
                except Exception as e:
                    self.logger.warning(f"[BACKUP] 清理失败 {filename}: {e}")

        return count


# 便利函数
def get_backup_manager(backup_root: Optional[str] = None) -> BackupManager:
    """获取备份管理器实例

    Args:
        backup_root: 备份根目录

    Returns:
        BackupManager 实例
    """
    return BackupManager(backup_root)
