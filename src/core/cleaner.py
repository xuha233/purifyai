"""
清理器模块
用于安全删除文件/文件夹到系统回收站
支持详细的清理操作日志记录
"""
import os
import threading
import time
from typing import List, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal
from ..utils.debug_monitor import get_debug_monitor
import send2trash

from .database import get_database
from .scanner import ScanItem
from .whitelist import get_whitelist
from .permissions import is_admin, request_admin_privilege, needs_admin_for_operation
from .config_manager import get_config_manager
from .safety.custom_recycle_bin import (
    get_custom_recycle_bin,
    is_custom_recycle_enabled,
    get_custom_recycle_path
)
from ..utils.logger import get_logger, log_clean_event, log_file_operation, log_performance


logger = get_logger(__name__)


class CleanEventType:
    """Clean event types"""
    PROGRESS = 'progress'
    ITEM_DELETED = 'item_deleted'
    ERROR = 'error'
    COMPLETE = 'complete'


class CleanEvent:
    """Clean event data"""
    def __init__(self, event_type: str, data: Any = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = time.time()


class Cleaner(QObject):
    """File cleaner - 使用 send2trash 安全删除到回收站"""
    # Signals
    progress = pyqtSignal(str)  # Progress message
    item_deleted = pyqtSignal(str, int)  # Path, size
    error = pyqtSignal(str)  # Error message
    complete = pyqtSignal(dict)  # Result summary

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.clean_thread = None
        self.db = get_database()
        self.whitelist = get_whitelist()  # 初始化白名单

        # 初始化配置管理器
        self.config_mgr = get_config_manager()

        # 初始化自定义回收站（如果启用）
        self._use_custom_recycle = is_custom_recycle_enabled(self.config_mgr)
        if self._use_custom_recycle:
            recycle_path = get_custom_recycle_path(self.config_mgr)
            self.custom_recycle_bin = get_custom_recycle_bin(recycle_path)
            logger.info(f"[Cleaner] 已启用自定义回收站: {recycle_path}")
        else:
            self.custom_recycle_bin = None
            logger.debug("[Cleaner] 使用系统回收站")

        logger.debug("[Cleaner] 清理器初始化完成")

    def start_clean(self, items: List[ScanItem], clean_type: str = 'system'):
        """
        开始清理选中的项目

        Args:
            items: 要清理的 ScanItem 列表
            clean_type: 清理操作类型
        """
        if self.is_running:
            logger.warning("[Cleaner] 清理操作已在运行，忽略新请求")
            return

        total_size = sum(item.size for item in items)
        logger.info(f"[清理:START] 开始清理 - 类型: {clean_type}, 项目数: {len(items)}, 大小: {self.format_size(total_size)}")

        self.is_running = True
        self.is_cancelled = False

        # 在单独线程中执行清理
        self.clean_thread = threading.Thread(
            target=self._clean_thread,
            args=(items, clean_type),
            daemon=True
        )
        self.clean_thread.start()

    def cancel_clean(self):
        """取消当前清理操作"""
        logger.info("[清理:CANCEL] 用户取消清理操作")
        self.is_cancelled = True

    def _clean_thread(self, items: List[ScanItem], clean_type: str):
        """清理线程函数"""
        logger.debug(f"[清理:THREAD] 清理线程启动 - 类型: {clean_type}")

        # 检查权限
        if needs_admin_for_operation('clean', items):
            if not is_admin():
                logger.warning("[清理:ERROR] 需要管理员权限但未获得")
                self.error.emit('需要管理员权限来清理系统文件')
                self.complete.emit({
                    'success': False,
                    'deleted_count': 0,
                    'total_size': 0,
                    'errors': ['需要管理员权限'],
                    'cancelled': False,
                    'needs_admin': True
                })
                self.is_running = False
                return

        start_time = time.time()
        deleted_count = 0
        deleted_size = 0
        errors = []

        try:
            total = len(items)
            logger.debug(f"[清理:THREAD] 准备清理 {total} 个项目")

            for i, item in enumerate(items):
                if self.is_cancelled:
                    logger.info("[清理:CANCELLED] 清理被用户取消")
                    break

                self.progress.emit(f'Cleaning {item.description} ({i+1}/{total})...')
                logger.debug(f"[清理:PROGRESS] 处理项目 {i+1}/{total}: {item.description}")

                try:
                    # 检查白名单
                    if self.whitelist.is_safe(item.path):
                        logger.debug(f"[清理:WHITELIST] 跳过白名单保护项: {item.path}")
                        continue

                    size_deleted = self._delete_item(item)
                    if size_deleted > 0:
                        deleted_count += 1
                        deleted_size += size_deleted
                        self.item_deleted.emit(item.path, size_deleted)

                        log_file_operation(logger, 'DELETE', item.path, size=size_deleted)

                        # 更新数据库
                        if clean_type == 'system':
                            self.db.delete_system_scan(clean_type, item.path)
                except Exception as e:
                    error_msg = f'Failed to delete {item.description}: {str(e)}'
                    errors.append(error_msg)
                    logger.error(f"[清理:ERROR] {error_msg}")
                    self.error.emit(error_msg)

            duration_ms = int((time.time() - start_time) * 1000)

            log_performance(logger, f"清理完成({clean_type})", duration_ms, items=deleted_count)
            logger.info(f"[清理:COMPLETE] 清理完成 - 删除: {deleted_count}/{total} 项, 释放: {self.format_size(deleted_size)}, 耗时: {duration_ms}ms, 错误: {len(errors)}")

            # 记录清理历史
            if deleted_count > 0:
                self.db.add_clean_history(
                    clean_type=clean_type,
                    items_count=deleted_count,
                    total_size=deleted_size,
                    duration_ms=duration_ms,
                    details={'errors': errors}
                )

            # 发送完成信号
            result = {
                'success': True,
                'deleted_count': deleted_count,
                'total_size': deleted_size,
                'duration_ms': duration_ms,
                'errors': errors,
                'cancelled': self.is_cancelled
            }

            if not self.is_cancelled:
                self.progress.emit(f'Clean complete! Deleted {deleted_count} items, {self.format_size(deleted_size)}')
            else:
                self.progress.emit(f'Clean cancelled. Deleted {deleted_count} items.')

            self.complete.emit(result)

        except Exception as e:
            logger.error(f"[清理:THREAD] 清理线程异常: {str(e)}")
            self.error.emit(f'Clean error: {str(e)}')
            self.complete.emit({
                'success': False,
                'deleted_count': deleted_count,
                'total_size': deleted_size,
                'errors': [str(e)],
                'cancelled': False
            })
        finally:
            self.is_running = False
            logger.debug("[清理:THREAD] 清理线程结束")

    def _delete_item(self, item: ScanItem) -> int:
        """
        删除文件或文件夹（安全删除到回收站）

        Args:
            item: 要删除的 ScanItem

        Returns:
            删除的项目大小
        """
        path = item.path
        original_size = item.size

        # 规范化路径为系统原生格式（Windows 下自动转为反斜杠）
        normalized_path = os.path.normpath(path)

        logger.debug(f"[清理:DELETE] 删除项目 - 路径: {path}, 规范化: {normalized_path}, 大小: {original_size}")
        logger.debug(f"[清理:DELETE] 使用自定义回收站: {self._use_custom_recycle}")

        try:
            # 检查文件/目录是否存在
            if not os.path.exists(normalized_path):
                logger.warning(f"[清理:SKIP] 文件不存在 - {path}")
                return 0

            # 检查是否使用自定义回收站
            if self._use_custom_recycle and self.custom_recycle_bin:
                # 使用自定义回收站（压缩后保存）
                success = self.custom_recycle_bin.recycle_item(
                    item_path=normalized_path,
                    original_size=original_size,
                    description=item.description,
                    risk_level=self._normalize_risk_level(item.risk_level)
                )
                if success:
                    logger.info(f"[清理:RECYCLE] 已添加到自定义回收站 - {item.description}")
                    return original_size
                else:
                    # 如果自定义回收站失败，回退到系统回收站
                    logger.warning(f"[清理:RECYCLE] 自定义回收站失败，使用系统回收站 - {item.description}")

            # 使用 send2trash 安全删除到系统回收站
            send2trash.send2trash(normalized_path)
            return original_size

        except Exception as e:
            error_msg = f'Failed to delete {item.description}: {str(e)}'
            logger.error(f"[清理:ERROR] 删除失败 - {path}: {str(e)}")

            # 记录到调试监控器
            monitor = get_debug_monitor()
            monitor.capture_error(e, {
                'path': path,
                'normalized_path': normalized_path,
                'item_description': item.description,
                'item_size': original_size,
                'operation': 'delete_to_recycle',
                'caller_function': '_delete_item'
            })

            raise Exception(error_msg)

    def _normalize_risk_level(self, risk_level) -> str:
        """规范化风险等级为字符串"""
        if hasattr(risk_level, 'value'):
            return risk_level.value
        elif isinstance(risk_level, str):
            return risk_level
        else:
            return str(risk_level).lower()

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """
        格式化大小为人类可读格式

        Args:
            size_bytes: 大小（字节）

        Returns:
            格式化后的字符串
        """
        if size_bytes == 0:
            return '0 B'

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f'{size:.2f} {units[unit_index]}'
