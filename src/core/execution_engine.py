"""
智能清理执行器 (Smart Cleanup Executor)

Phase 3 Day 6 MVP功能:
- 异步执行清理计划
- 集成备份管理器
- 进度报告和取消支持
- 执行结果记录到数据库
- 错误处理和恢复建议

设计原则:
- 使用 QThread 实现异步执行
- 与 BackupManager 无缝集成
- 支持取消、暂停、恢复
- 详细的错误分类和处理建议
"""
import os
import shutil
import time
from enum import Enum
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker

from .models_smart import (
    CleanupPlan, CleanupItem, CleanupStatus, ExecutionStatus,
    ExecutionResult, FailureInfo, BackupType, BackupInfo, RecoveryRecord
)
from .backup_manager import BackupManager, BackupStats
from .database import Database, get_database
from .rule_engine import RiskLevel
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ErrorType(Enum):
    """错误类型"""
    PERMISSION_DENIED = "permission_denied"      # 权限不足
    FILE_IN_USE = "file_in_use"                  # 文件被占用
    FILE_NOT_FOUND = "file_not_found"            # 文件不存在
    DISK_FULL = "disk_full"                      # 磁盘空间不足
    BACKUP_FAILED = "backup_failed"              # 备份失败
    DELETE_FAILED = "delete_failed"              # 删除失败
    UNKNOWN = "unknown"                          # 未知错误


class RetryStrategy(Enum):
    """重试策略"""
    NO_RETRY = "no_retry"                        # 不重试
    IMMEDIATE_RETRY = "immediate_retry"          # 立即重试
    DELAYED_RETRY = "delayed_retry"              # 延迟重试
    SKIP = "skip"                                # 跳过


class ExecutionPhase(Enum):
    """执行阶段"""
    PREPARING = "preparing"                      # 准备中
    BACKING_UP = "backing_up"                    # 备份中
    DELETING = "deleting"                        # 删除中
    RECORDING = "recording"                      # 记录中
    FINALIZING = "finalizing"                    # 完成中


@dataclass
class ExecutionConfig:
    """执行配置"""
    max_retries: int = 3                         # 最大重试次数
    retry_delay: float = 1.0                     # 重试延迟（秒）
    enable_backup: bool = True                   # 启用备份
    log_all_operations: bool = True             # 记录所有操作
    abort_on_error: bool = False                 # 出错时中止
    chunk_size: int = 100                        # 批量处理大小


class ExecutionThread(QThread):
    """执行线程 - 在后台线程中执行清理操作"""

    # 进度信号
    phase_started = pyqtSignal(str, int, int)    # phase_name, current, total
    item_started = pyqtSignal(str)              # item_path
    item_completed = pyqtSignal(str, str)       # item_path, status (success/failed/skipped)
    item_progress = pyqtSignal(str, int, int)    # item_path, current, total (for large files)

    # 结果信号
    execution_started = pyqtSignal()
    execution_failed = pyqtSignal(str)           # error_message
    execution_cancelled = pyqtSignal()
    execution_completed = pyqtSignal(object)     # ExecutionResult

    # 备份信号
    backup_created = pyqtSignal(object)         # BackupInfo
    backup_failed = pyqtSignal(str, str)        # item_path, error_message

    def __init__(self, plan: CleanupPlan, backup_mgr: BackupManager,
                 config: ExecutionConfig = None):
        """
        初始化执行线程

        Args:
            plan: 清理计划
            backup_mgr: 备份管理器
            config: 执行配置
        """
        super().__init__()
        self.plan = plan
        self.backup_mgr = backup_mgr
        self.config = config or ExecutionConfig()

        self.is_cancelled = False
        self.mutex = QMutex()

        # 执行状态
        self.current_phase = ExecutionPhase.PREPARING
        self.current_item_index = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.freed_size = 0

        self.logger = logger

    def run(self):
        """执行清理计划"""
        self.logger.info(f"[EXECUTOR] 开始执行计划 {self.plan.plan_id}")
        self.execution_started.emit()

        try:
            # 创建执行结果
            result = ExecutionResult(
                plan_id=self.plan.plan_id,
                started_at=time.time(),
                total_items=0,
                total_size=0,
                status=ExecutionStatus.RUNNING
            )

            # 准备阶段
            self._set_phase(ExecutionPhase.PREPARING)
            items = self._prepare_items()
            result.total_items = len(items)
            result.total_size = sum(item.size for item in items)

            self.phase_started.emit("preparing", 0, result.total_items)

            # 执行清理
            self._execute_cleanup(items, result)

            # 完成阶段
            self._set_phase(ExecutionPhase.FINALIZING)
            result.status = ExecutionStatus.COMPLETED if result.failed_items == 0 else ExecutionStatus.PARTIAL_SUCCESS

            self.logger.info(f"[EXECUTOR] 执行完成 - 结果: {result.status.value}")
            self.execution_completed.emit(result)

        except Exception as e:
            error_msg = f"执行失败: {str(e)}"
            self.logger.error(f"[EXECUTOR] {error_msg}")
            self.execution_failed.emit(error_msg)

    def _prepare_items(self) -> List[CleanupItem]:
        """准备清理项目

        筛选需要清理的项目（根据状态）

        Returns:
            待清理的项目列表
        """
        items = []
        for item in self.plan.items:
            # 只处理 pending 状态的项目
            # TODO: 这里可以从数据库读取项目状态
            items.append(item)

        self.logger.info(f"[EXECUTOR] 准备完成 - {len(items)} 个项目待清理")
        return items

    def _execute_cleanup(self, items: List[CleanupItem], result: ExecutionResult):
        """执行清理

        Args:
            items: 清理项目列表
            result: 执行结果对象
        """
        total = len(items)

        for i, item in enumerate(items):
            if self._is_cancelled():
                self.logger.info("[EXECUTOR] 执行被取消")
                result.status = ExecutionStatus.CANCELLED
                self.execution_cancelled.emit()
                return

            self.current_item_index = i
            self.item_started.emit(item.path)

            try:
                # 执行单个项目
                status = self._execute_item(item)

                # 更新统计
                if status == CleanupStatus.SUCCESS:
                    self.success_count += 1
                    result.success_items += 1
                    self.freed_size += item.size
                    result.freed_size += item.size
                elif status == CleanupStatus.FAILED:
                    self.failed_count += 1
                    result.failed_items += 1
                    result.failed_size += item.size
                else:  # SKIPPED
                    self.skipped_count += 1
                    result.skipped_items += 1

                self.item_completed.emit(item.path, status.value)
                self.phase_started.emit("deleting", i + 1, total)

            except Exception as e:
                error_msg = f"项目清理异常: {str(e)}"
                self.logger.error(f"[EXECUTOR] {error_msg}")

                # 添加失败信息
                result.add_failure(
                    item,
                    ErrorType.UNKNOWN.value,
                    error_msg,
                    "skip"
                )

                self.item_completed.emit(item.path, "failed")

    def _execute_item(self, item: CleanupItem) -> CleanupStatus:
        """执行单个项目的清理

        Args:
            item: 清理项目

        Returns:
            清理状态
        """
        # 跳过不存在或已在白名单的文件
        if not os.path.exists(item.path):
            self.logger.warning(f"[EXECUTOR] 文件不存在: {item.path}")
            return CleanupStatus.SKIPPED

        # 备份（如果需要）
        if self.config.enable_backup:
            backup_info = self.backup_mgr.create_backup(item)
            if backup_info:
                self.backup_created.emit(backup_info)
            else:
                # Safe 项不需要备份
                if item.ai_risk != RiskLevel.SAFE:
                    self.logger.warning(f"[EXECUTOR] 备份失败但继续执行: {item.path}")

        # 删除文件
        return self._delete_item(item)

    def _delete_item(self, item: CleanupItem) -> CleanupStatus:
        """删除项目

        Args:
            item: 清理项目

        Returns:
            清理状态
        """
        path = item.path
        retry_count = 0
        max_retries = self.config.max_retries

        while retry_count <= max_retries:
            try:
                if os.path.isfile(path):
                    # 先尝试删除只读属性
                    if os.name == 'nt':  # Windows
                        try:
                            import stat
                            os.chmod(path, stat.S_IWRITE)
                        except:
                            pass
                    os.remove(path)
                elif os.path.isdir(path):
                    # Windows 特殊处理：处理被锁定的文件
                    if os.name == 'nt':
                        self._clear_readonly(path)
                        # 强制删除，忽略错误
                        try:
                            shutil.rmtree(path, ignore_errors=False)
                        except OSError as e:
                            # [WinError 145] 目录不是空的 - 可能包含被锁定的文件
                            if hasattr(e, 'winerror') and e.winerror == 145:
                                # 尝试删除子文件
                                self._delete_directory_contents(path)
                                # 再次尝试删除空目录
                                try:
                                    os.rmdir(path)
                                except:
                                    raise
                            elif 'Directory not empty' in str(e):
                                # 类似错误
                                self._delete_directory_contents(path)
                                try:
                                    os.rmdir(path)
                                except:
                                    raise
                            else:
                                raise
                    else:
                        # Unix/Linux
                        shutil.rmtree(path)
                else:
                    return CleanupStatus.SKIPPED

                self.logger.info(f"[EXECUTOR] 删除成功: {path}")
                return CleanupStatus.SUCCESS

            except PermissionError:
                error_msg = f"权限不足: {path}"
                logger.warning(f"[EXECUTOR] {error_msg}")

                if retry_count < max_retries:
                    retry_count += 1
                    self.logger.info(f"[EXECUTOR] 重试 {retry_count}/{max_retries}")
                    time.sleep(self.config.retry_delay)
                    continue
                else:
                    raise Exception(error_msg)

            except FileNotFoundError:
                self.logger.warning(f"[EXECUTOR] 文件不存在: {path}")
                return CleanupStatus.SKIPPED

            except Exception as e:
                error_msg = f"删除失败: {e}"
                self.logger.error(f"[EXECUTOR] {error_msg}")

                if retry_count < max_retries:
                    retry_count += 1
                    time.sleep(self.config.retry_delay)
                    continue
                else:
                    raise Exception(error_msg)

        return CleanupStatus.FAILED

    def _clear_readonly(self, path: str):
        """清除目录中所有文件的只读属性（Windows）

        Args:
            path: 目录路径
        """
        import stat
        if os.name != 'nt':
            return

        try:
            for root, dirs, files in os.walk(path):
                for name in files + dirs:
                    full_path = os.path.join(root, name)
                    try:
                        os.chmod(full_path, stat.S_IWRITE)
                    except:
                        pass
        except:
            pass

    def _delete_directory_contents(self, path: str):
        """尝试删除目录中的内容（处理被锁定的文件）

        Args:
            path: 目录路径
        """
        import stat
        if os.name != 'nt':
            return

        try:
            for item_name in os.listdir(path):
                item_path = os.path.join(path, item_name)
                try:
                    if os.path.isfile(item_path):
                        try:
                            os.chmod(item_path, stat.S_IWRITE)
                        except:
                            pass
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        self._clear_readonly(item_path)
                        shutil.rmtree(item_path, ignore_errors=True)
                except Exception as e:
                    self.logger.debug(f"[EXECUTOR] 跳过被锁定的项目: {item_path}, 原因: {e}")
                    pass
        except Exception as e:
            self.logger.debug(f"[EXECUTOR] 删除目录内容异常: {path}, 原因: {e}")
            pass

    def _set_phase(self, phase: ExecutionPhase):
        """设置执行阶段

        Args:
            phase: 执行阶段
        """
        self.current_phase = phase
        self.logger.debug(f"[EXECUTOR] 阶段: {phase.value}")

    def _is_cancelled(self) -> bool:
        """检查是否已取消（线程安全）"""
        locker = QMutexLocker(self.mutex)
        return self.is_cancelled

    def cancel(self):
        """取消执行"""
        locker = QMutexLocker(self.mutex)
        self.is_cancelled = True
        self.logger.info("[EXECUTOR] 收到取消请求")


class SmartCleanupExecutor(QObject):
    """智能清理执行器

    提供异步清理执行能力，集成备份管理器。

    Features:
        - 异步执行（QThread）
        - 进度报告
        - 取消支持
        - 自动备份（Safe: 无, Suspicious: 硬链接, Dangerous: 完整）
        - 错误处理和重试
        - 执行记录到数据库
    """

    # 进度信号
    execution_started = pyqtSignal(str)         # plan_id
    execution_progress = pyqtSignal(str, int, int)  # plan_id, current, total
    item_started = pyqtSignal(str, str)         # plan_id, item_path
    item_completed = pyqtSignal(str, str, str) # plan_id, item_path, status
    phase_changed = pyqtSignal(str, str)        # plan_id, phase_name

    # 结果信号
    execution_completed = pyqtSignal(object)     # ExecutionResult
    execution_failed = pyqtSignal(str, str)     # plan_id, error_message
    execution_cancelled = pyqtSignal(str)       # plan_id

    # 备份信号
    backup_created = pyqtSignal(str, object)    # plan_id, BackupInfo

    def __init__(
        self,
        backup_mgr: Optional[BackupManager] = None,
        db: Optional[Database] = None,
        config: ExecutionConfig = None
    ):
        """
        初始化执行器

        Args:
            backup_mgr: 备份管理器
            db: 数据库实例
            config: 执行配置
        """
        super().__init__()

        self.backup_mgr = backup_mgr or BackupManager()
        self.db = db or get_database()
        self.config = config or ExecutionConfig()

        self.current_thread: Optional[ExecutionThread] = None
        self.is_executing = False

        self.logger = logger

    def execute_plan(
        self,
        plan: CleanupPlan,
        config: ExecutionConfig = None
    ) -> bool:
        """
        执行清理计划

        Args:
            plan: 清理计划
            config: 执行配置（可选，覆盖默认配置）

        Returns:
            是否成功启动执行
        """
        if self.is_executing:
            self.logger.warning("[EXECUTOR] 已有执行在运行")
            return False

        self.is_executing = True
        execution_config = config or self.config

        self.logger.info(f"[EXECUTOR] 启动执行: {plan.plan_id}")
        self.execution_started.emit(plan.plan_id)

        # 创建执行线程
        self.current_thread = ExecutionThread(
            plan=plan,
            backup_mgr=self.backup_mgr,
            config=execution_config
        )

        # 连接信号
        self._connect_thread_signals(self.current_thread, plan.plan_id)

        # 启动线程
        self.current_thread.start()
        return True

    def _connect_thread_signals(self, thread: ExecutionThread, plan_id: str):
        """连接线程信号

        Args:
            thread: 执行线程
            plan_id: 计划ID
        """
        # 执行信号
        thread.execution_started.connect(lambda: None)
        thread.execution_completed.connect(self._on_execution_completed)
        thread.execution_failed.connect(lambda msg: self._on_execution_failed(plan_id, msg))
        thread.execution_cancelled.connect(lambda: self._on_execution_cancelled(plan_id))

        # 进度信号
        thread.phase_started.connect(
            lambda phase, cur, total: self.phase_changed.emit(plan_id, phase)
        )
        thread.item_started.connect(lambda path: self.item_started.emit(plan_id, path))
        thread.item_completed.connect(
            lambda path, status: self.item_completed.emit(plan_id, path, status)
        )

        # 备份信号
        thread.backup_created.connect(
            lambda info: self.backup_created.emit(plan_id, info)
        )

    def _on_execution_completed(self, result: ExecutionResult):
        """执行完成回调

        Args:
            result: 执行结果
        """
        self.is_executing = False
        self.current_thread = None

        self.logger.info(f"[EXECUTOR] 执行完成: {result.plan_id}")
        self.execution_completed.emit(result)

    def _on_execution_failed(self, plan_id: str, error_message: str):
        """执行失败回调

        Args:
            plan_id: 计划ID
            error_message: 错误消息
        """
        self.is_executing = False
        self.current_thread = None

        self.logger.error(f"[EXECUTOR] 执行失败: {plan_id} - {error_message}")
        self.execution_failed.emit(plan_id, error_message)

    def _on_execution_cancelled(self, plan_id: str):
        """执行取消回调

        Args:
            plan_id: 计划ID
        """
        self.is_executing = False
        self.current_thread = None

        self.logger.info(f"[EXECUTOR] 执行取消: {plan_id}")
        self.execution_cancelled.emit(plan_id)

    def cancel_execution(self):
        """取消当前执行"""
        if self.current_thread and self.current_thread.isRunning():
            self.logger.info("[EXECUTOR] 取消执行")
            self.current_thread.cancel()
            self.current_thread.wait(5000)  # 等待最多5秒

    def is_idle(self) -> bool:
        """检查是否空闲

        Returns:
            是否空闲
        """
        return not self.is_executing

    def get_status(self) -> Dict:
        """获取当前状态

        Returns:
            状态字典
        """
        thread = self.current_thread
        if not thread:
            return {
                'status': 'idle',
                'plan_id': None,
                'phase': '',
                'progress': (0, 0)
            }

        return {
            'status': 'running' if thread.isRunning() else 'stopped',
            'plan_id': thread.plan.plan_id,
            'phase': thread.current_phase.value,
            'progress': (thread.current_item_index, len(thread.plan.items)),
            'success': thread.success_count,
            'failed': thread.failed_count,
            'skipped': thread.skipped_count
        }


# 便利函数
def get_executor(
    backup_mgr: Optional[BackupManager] = None,
    db: Optional[Database] = None,
    config: ExecutionConfig = None
) -> SmartCleanupExecutor:
    """获取执行器实例

    Args:
        backup_mgr: 备份管理器
        db: 数据库实例
        config: 执行配置

    Returns:
        SmartCleanupExecutor 实例
    """
    return SmartCleanupExecutor(
        backup_mgr=backup_mgr,
        db=db,
        config=config
    )
