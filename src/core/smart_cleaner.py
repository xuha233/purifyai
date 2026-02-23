"""
智能清理器 (Smart Cleaner) - 整合模块

Phase 3 Day 3 MVP功能:
- 整合扫描器 (Scanner)
- 整合AI分析器 (AIAnalyzer)
- 整合执行器 (SmartCleanupExecutor)
- 整合备份管理器 (BackupManager)
- 完整清理工作流编排

工作流：
1. Scan Phase: 扫描目标路径，生成ScanItems
2. Analyze Phase: AI/规则引擎评估，生成CleanupPlan
3. Preview Phase: 用户确认清理项
4. Execute Phase: 异步执行清理，带备份
5. Report Phase: 生成清理报告

Features:
- 支持多种扫描类型 (system, browser, appdata, custom, disk)
- 异步扫描和分析（不阻塞UI）
- 进度报告和取消支持
- 自动备份策略
- 错误处理和重试
- 统计和报告
"""
import os
import sys
import time
from enum import Enum
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker, Qt

from .scanner import SystemScanner, BrowserScanner, AppDataScanner
from .custom_scanner import CustomScanner
from .models import ScanItem
from .models_smart import (
    CleanupPlan, CleanupItem, ExecutionResult, ExecutionStatus,
    ScanProgress, CleanupStatus
)
from .ai_analyzer import AIAnalyzer, CostControlConfig, CostControlMode
from .backup_manager import BackupManager, get_backup_manager
from .execution_engine import (
    SmartCleanupExecutor, ExecutionConfig, get_executor
)
from .database import Database, get_database
from utils.logger import get_logger
from utils.debug_tracker import debug_event, debug_exception, track_signal, timing_context

logger = get_logger(__name__)


class ScannerAdapter(QThread):
    """扫描器适配器 - 统一不同扫描器的接口"""

    scan_progress = pyqtSignal(int, int)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    def __init__(self, scanner):
        super().__init__()
        self.scanner = scanner
        self._is_running = False
        self._results = []
        self.logger = logger
        self._connect_scanner_signals()

    def _connect_scanner_signals(self):
        debug_event('DEBUG', 'ScannerAdapter', '_connect_scanner_signals',
                   '连接扫描器信号',
                   scanner_type=type(self.scanner).__name__)

        # 使用 QueuedConnection 确保从 threading.Thread 发射的信号在 QThread 中被处理
        if hasattr(self.scanner, 'item_found'):
            self.scanner.item_found.connect(self.item_found.emit, Qt.QueuedConnection)
            debug_event('DEBUG', 'ScannerAdapter', '_connect_scanner_signals',
                       '已连接 item_found 信号')

        if hasattr(self.scanner, 'complete'):
            self.scanner.complete.connect(self._on_complete, Qt.QueuedConnection)
            debug_event('DEBUG', 'ScannerAdapter', '_connect_scanner_signals',
                       '已连接 complete 信号')

        if hasattr(self.scanner, 'error'):
            self.scanner.error.connect(self.error.emit, Qt.QueuedConnection)
            debug_event('DEBUG', 'ScannerAdapter', '_connect_scanner_signals',
                       '已连接 error 信号')

        if hasattr(self.scanner, 'progress'):
            self.scanner.progress.connect(self._translate_progress, Qt.QueuedConnection)
            debug_event('DEBUG', 'ScannerAdapter', '_connect_scanner_signals',
                       '已连接 progress 信号')

    def _translate_progress(self, progress):
        debug_event('DEBUG', 'ScannerAdapter', '_translate_progress',
                   '接收进度信号',
                   progress_type=type(progress).__name__,
                   progress_value=str(progress)[:100])

        if isinstance(progress, tuple) and len(progress) == 2:
            self.scan_progress.emit(*progress)
        elif isinstance(progress, str):
            try:
                if '(' in progress and ')' in progress:
                    parts = progress.split('(')[1].split(')')[0].split('/')
                    if len(parts) == 2:
                        self.scan_progress.emit(int(parts[0]), int(parts[1]))
            except Exception as e:
                debug_event('WARNING', 'ScannerAdapter', '_translate_progress',
                           '进度解析失败',
                           error=str(e))

    def _on_complete(self, results):
        try:
            if not hasattr(self, 'logger'):
                from utils.logger import get_logger
                self.logger = get_logger(__name__)

            track_signal('complete', type(self.scanner).__name__, 'ScannerAdapter', emitted=False, received=True)

            results_list = results if isinstance(results, list) else ([results] if results else [])
            self._results = results_list
            self._is_running = False

            debug_event('INFO', 'ScannerAdapter', '_on_complete',
                       '扫描完成，准备发送 complete 信号',
                       results_count=len(results_list))

            self.logger.info(f"[ScannerAdapter] 扫描完成: {len(self._results)} 项，准备发送 complete 信号")

            self.complete.emit(self._results)
            track_signal('complete', 'ScannerAdapter', 'ScanThread', emitted=True, received=False)

            debug_event('INFO', 'ScannerAdapter', '_on_complete',
                       'complete 信号已发送')

            self.logger.info(f"[ScannerAdapter] complete 信号已发送")
        except Exception as e:
            debug_exception('ScannerAdapter', '_on_complete', '处理完成信号异常', exc_info=sys.exc_info())
            self.error.emit(f'扫描完成处理异常: {str(e)}')
            raise

    def run(self):
        pass

    def start_scan(self):
        try:
            if not hasattr(self, 'logger'):
                from utils.logger import get_logger
                self.logger = get_logger(__name__)

            scanner_type = type(self.scanner).__name__
            self._is_running = True
            self.logger.info(f"[ScannerAdapter] start_scan 被调用, scanner类型: {scanner_type}")

            if hasattr(self.scanner, 'start_scan'):
                self.logger.debug("[ScannerAdapter] 调用 scanner.start_scan()")
                self.scanner.start_scan()
            elif hasattr(self.scanner, 'start') and callable(getattr(self.scanner, 'start')):
                self.logger.debug("[ScannerAdapter] 调用 scanner.start()")
                self.scanner.start()
            elif hasattr(self.scanner, 'scan') and callable(getattr(self.scanner, 'scan')):
                self.logger.debug("[ScannerAdapter] 调用 scanner.scan()")
                self.scanner.scan()
            else:
                self.logger.warning(f"[ScannerAdapter] scanner 没有 start 方法: {type(self.scanner)}")

            self.logger.info(f"[ScannerAdapter] start_scan 完成, is_running={self._is_running}")
        except Exception as e:
            self.logger.error(f"[ScannerAdapter] 启动扫描异常: {str(e)}")
            self.error.emit(f'启动扫描失败: {str(e)}')
            self._is_running = False

    def cancel(self):
        if hasattr(self.scanner, 'cancel'):
            self.scanner.cancel()
        elif hasattr(self.scanner, 'cancel_scan'):
            self.scanner.cancel_scan()
        self._is_running = False

    @property
    def is_running(self):
        # 返回内部状态，而不是scanner的is_running
        # 这样可以确保ScanThread能正确检测完成状态
        return self._is_running

    @property
    def results(self):
        # 优先返回内部结果，备用scanner的results
        if self._results:
            return self._results
        return getattr(self.scanner, 'results', [])


class AnalyzeThread(QThread):
    """分析线程 - 在后台执行 AI 分析"""
    progress = pyqtSignal(int, int)
    completed = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, ai_analyzer, items, config):
        super().__init__()
        self.ai_analyzer = ai_analyzer
        self.items = items
        self.config = config

    def run(self):
        try:
            def progress_callback(current, total):
                self.progress.emit(current, total)
            plan = self.ai_analyzer.analyze_scan_results(self.items, progress_callback)
            self.completed.emit(plan)
        except Exception as e:
            self.error.emit(f"分析失败: {str(e)}")


class SmartCleanPhase(Enum):
    """智能清理阶段"""
    IDLE = "idle"                       # 空闲
    SCANNING = "scanning"               # 扫描中
    ANALYZING = "analyzing"             # 分析中
    PREVIEW = "preview"                 # 预览中
    EXECUTING = "executing"             # 执行中
    COMPLETED = "completed"             # 完成
    ERROR = "error"                     # 错误


class ScanType(Enum):
    """扫描类型"""
    SYSTEM = "system"                   # 系统垃圾
    BROWSER = "browser"                 # 浏览器缓存
    APPDATA = "appdata"                 # AppData 文件夹
    CUSTOM = "custom"                   # 自定义路径
    DISK = "disk"                       # 深度磁盘扫描


@dataclass
class SmartCleanConfig:
    """智能清理配置"""
    # AI 配置
    enable_ai: bool = True               # 启用AI评估
    max_ai_calls: int = 100             # 最大AI调用次数
    cost_mode: CostControlMode = CostControlMode.FALLBACK

    # 备份配置
    enable_backup: bool = True           # 启用备份
    backup_retention_days: int = 7       # 备份保留天数

    # 执行配置
    max_retries: int = 3                 # 最大重试次数
    abort_on_error: bool = False         # 出错时中止

    # 过滤配置
    min_size_mb: int = 0                 # 最小文件大小 (MB)
    exclude_patterns: List[str] = None   # 排除模式

    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = []


class ScanThread(QThread):
    """扫描线程 - 在后台执行扫描"""

    progress = pyqtSignal(str, int, int)      # phase, current, total
    item_found = pyqtSignal(object)           # ScanItem
    completed = pyqtSignal(list, str)         # items, scan_type
    error = pyqtSignal(str)

    def __init__(self, scan_type: str, scan_target: str = ""):
        super().__init__()
        self.scan_type = scan_type
        self.scan_target = scan_target
        self.is_cancelled = False
        self.mutex = QMutex()
        self._temp_results = []  # 临时保存结果

        self.logger = logger

    def run(self):
        """执行扫描"""
        start_time = time.time()

        try:
            debug_event('INFO', 'ScanThread', 'run',
                       '扫描线程启动',
                       scan_type=self.scan_type,
                       scan_target=self.scan_target)

            self.logger.info(f"[SMART_CLEAN] 开始扫描: {self.scan_type}, 目标: {self.scan_target}")

            items = []
            scanner = None

            # 根据扫描类型选择扫描器
            if self.scan_type == ScanType.SYSTEM.value:
                scanner = SystemScanner()
            elif self.scan_type == ScanType.BROWSER.value:
                scanner = BrowserScanner()
            elif self.scan_type == ScanType.APPDATA.value:
                scanner = AppDataScanner()
            elif self.scan_type == ScanType.CUSTOM.value:
                scanner = CustomScanner(self.scan_target)
            else:
                error_msg = f"不支持的扫描类型: {self.scan_type}"
                debug_event('ERROR', 'ScanThread', 'run',
                           f"不支持的扫描类型: {self.scan_type}")
                self.error.emit(error_msg)
                return

            debug_event('INFO', 'ScanThread', 'run',
                       '扫描器创建',
                       scanner_type=type(scanner).__name__)

            # 使用适配器包装扫描器
            scanner_adapter = ScannerAdapter(scanner)
            self.logger.debug(f"[SMART_CLEAN] ScannerAdapter created, connecting signals")
            self._connect_scanner_signals(scanner_adapter)

            self.logger.info(f"[SMART_CLEAN] 开始扫描, 适配器状态: is_running={scanner_adapter.is_running}")

            # 执行扫描
            scanner_adapter.start_scan()

            # 等待扫描完成（但保持响应取消）
            loop_count = 0
            timeout_seconds = 300  # 5分钟超时
            self.logger.info(f"[SMART_CLEAN] 等待扫描完成...")

            while scanner_adapter.is_running and not self._is_cancelled():
                elapsed = time.time() - start_time

                # 超时检测
                if elapsed > timeout_seconds:
                    error_msg = f"扫描超时（{timeout_seconds}秒），请检查系统状态或重试"
                    self.logger.error(f"[SMART_CLEAN] {error_msg}")
                    debug_event('ERROR', 'ScanThread', 'run',
                               '扫描超时',
                               elapsed_seconds=elapsed,
                               timeout_seconds=timeout_seconds)
                    scanner_adapter.cancel()
                    self.error.emit(error_msg)
                    return

                # 每秒一次详细日志
                if loop_count % 10 == 0:
                    self.logger.debug(f"[SMART_CLEAN] 等待中... 循环: {loop_count}, adapter_running: {scanner_adapter.is_running}, 已等待: {elapsed:.1f}秒")

                    # 每5秒输出一次调试事件
                    if loop_count % 50 == 0:
                        debug_event('DEBUG', 'ScanThread', 'run',
                                   '扫描等待中',
                                   elapsed_seconds=elapsed,
                                   loop_count=loop_count,
                                   adapter_is_running=scanner_adapter.is_running)

                self.msleep(100)
                loop_count += 1

            elapsed = time.time() - start_time
            self.logger.info(f"[SMART_CLEAN] 扫描循环结束: 迭行次数={loop_count}, is_cancelled={self._is_cancelled()}, adapter_is_running={scanner_adapter.is_running}, 耗时: {elapsed:.2f}秒")

            debug_event('INFO', 'ScanThread', 'run',
                       '扫描循环结束',
                       loop_count=loop_count,
                       is_cancelled=self._is_cancelled(),
                       adapter_is_running=scanner_adapter.is_running,
                       elapsed_seconds=elapsed)

            self.msleep(200)  # 等待最后的信号

            if self._is_cancelled():
                scanner_adapter.cancel()
                self.logger.info("[SMART_CLEAN] 扫描已取消")
                debug_event('INFO', 'ScanThread', 'run', '扫描已取消')
                return

            # 获取扫描结果
            items = scanner_adapter.results
            self.logger.info(f"[SMART_CLEAN] 从适配器获取结果: {len(items)} 项")

            debug_event('INFO', 'ScanThread', 'run',
                       '获取扫描结果',
                       results_count=len(items))

            self.completed.emit(items, self.scan_type)
            track_signal('completed', 'ScanThread', 'SmartCleaner', emitted=True, received=False)
            self.logger.info(f"[SMART_CLEAN] 完成信号已发射, 类型={self.scan_type}")

        except Exception as e:
            elapsed = time.time() - start_time
            import traceback
            tb_str = traceback.format_exc()

            self.logger.error(f"[SMART_CLEAN] 扫描异常: {str(e)}\n{tb_str}")

            debug_exception('ScanThread', 'run',
                          '扫描异常',
                          exc_info=sys.exc_info(),
                          scan_type=self.scan_type,
                            elapsed_seconds=elapsed)

            error_msg = f"扫描失败: {str(e)}"
            self.error.emit(error_msg)

    def _connect_scanner_signals(self, scanner):
        """连接扫描器信号"""
        debug_event('DEBUG', 'ScanThread', '_connect_scanner_signals',
                   '连接适配器信号',
                   scanner_type=type(scanner).__name__)

        # 连接 scan_progress - 注意类型匹配
        if hasattr(scanner, 'scan_progress'):
            # ScannerAdapter 发送 (int, int)，直接传递
            scanner.scan_progress.connect(
                lambda current, total: self.progress.emit("scanning", current, total)
            )
            debug_event('DEBUG', 'ScanThread', '_connect_scanner_signals',
                       '已连接 scan_progress 信号')

        if hasattr(scanner, 'item_found'):
            scanner.item_found.connect(self.item_found)
            debug_event('DEBUG', 'ScanThread', '_connect_scanner_signals',
                       '已连接 item_found 信号')

        if hasattr(scanner, 'complete'):
            track_signal('complete', 'ScannerAdapter', 'ScanThread._save_results')
            scanner.complete.connect(self._save_results)
            debug_event('DEBUG', 'ScanThread', '_connect_scanner_signals',
                       '已连接 complete 信号')

        if hasattr(scanner, 'error'):
            track_signal('error', 'ScannerAdapter', 'ScanThread.error')
            scanner.error.connect(self.error.emit)
            debug_event('DEBUG', 'ScanThread', '_connect_scanner_signals',
                       '已连接 error 信号')

    def _save_results(self, results):
        """保存扫描结果"""
        debug_event('INFO', 'ScanThread', '_save_results',
                   '接收扫描结果',
                   results_count=len(results) if results else 0)
        self._temp_results = results

    def cancel(self):
        """取消扫描"""
        locker = QMutexLocker(self.mutex)
        self.is_cancelled = True

    def _is_cancelled(self) -> bool:
        """检查是否已取消"""
        locker = QMutexLocker(self.mutex)
        return self.is_cancelled


class SmartCleaner(QObject):
    """智能清理器 - 完整工作流编排

    提供扫描 → 分析 → 预览 → 扽数 → 报告的完整清理工作流

    Signals:
        phase_changed: SmartCleanPhase - 阶段发生变化
        scan_progress: int, int - 扫描进度 (current, total)
        analyze_progress: int, int - 分析进度 (current, total)
        execute_progress: int, int - 执行进度 (current, total)
        item_found: ScanItem - 发现新项
        plan_ready: CleanupPlan - 清理计划就绪
        execution_completed: ExecutionResult - 执行完成
        error: str - 错误发生
    """

    # 阶段信号
    phase_changed = pyqtSignal(str)           # phase_name
    scan_progress = pyqtSignal(int, int)      # current, total
    analyze_progress = pyqtSignal(int, int)   # current, total
    execute_progress = pyqtSignal(int, int)   # current, total

    # 数据信号
    item_found = pyqtSignal(object)           # ScanItem
    plan_ready = pyqtSignal(object)           # CleanupPlan
    execution_completed = pyqtSignal(object) # ExecutionResult

    # 错误信号
    error = pyqtSignal(str)                   # error_message

    def __init__(
        self,
        config: SmartCleanConfig = None,
        backup_mgr: BackupManager = None,
        db: Database = None
    ):
        """
        初始化智能清理器

        Args:
            config: 智能清理配置
            backup_mgr: 备份管理器
            db: 数据库实例
        """
        super().__init__()

        self.config = config or SmartCleanConfig()
        self.backup_mgr = backup_mgr or get_backup_manager()
        self.db = db or get_database()

        # 组件初始化
        self.ai_analyzer = AIAnalyzer(cost_config=self._get_ai_cost_config())
        self.executor = get_executor(backup_mgr=self.backup_mgr, db=self.db)

        # 状态管理
        self.current_phase = SmartCleanPhase.IDLE
        self.scan_thread: Optional[ScanThread] = None
        self.scan_items: List[ScanItem] = []
        self.current_plan: Optional[CleanupPlan] = None

        self.mutex = QMutex()
        self.logger = logger

    def _get_ai_cost_config(self) -> CostControlConfig:
        """获取AI成本控制配置

        Returns:
            成本控制配置
        """
        return CostControlConfig(
            mode=self.config.cost_mode,
            max_calls_per_scan=self.config.max_ai_calls,
            only_analyze_suspicious=True,  # 只分析可疑项
            fallback_to_rules=True
        )

    def start_scan(
        self,
        scan_type: str,
        scan_target: str = ""
    ) -> bool:
        """
        开始扫描

        Args:
            scan_type: 扫描类型 (system/browser/appdata/custom/disk)
            scan_target: 扫描目标（自定义路径）

        Returns:
            是否成功启动
        """
        if not self._is_idle():
            self.logger.warning("[SMART_CLEAN] 正在运行中，无法启动新的扫描")
            return False

        self._set_phase(SmartCleanPhase.SCANNING)
        self.logger.info(f"[SMART_CLEAN] 启动扫描: {scan_type}")

        self.scan_thread = ScanThread(scan_type, scan_target)

        # 连接信号
        self.scan_thread.progress.connect(self._on_scan_progress)
        self.scan_thread.item_found.connect(self.item_found.emit)
        self.scan_thread.completed.connect(self._on_scan_completed)
        self.scan_thread.error.connect(self.error.emit)

        # 启动线程
        self.scan_thread.start()
        return True

    def _on_scan_progress(self, phase: str, current: int, total: int):
        """扫描进度回调

        Args:
            phase: 阶段名称
            current: 当前进度
            total: 总数
        """
        self.scan_progress.emit(current, total)

    def _on_scan_completed(self, items: List[ScanItem], scan_type: str):
        """扫描完成回调

        Args:
            items: 扫描项列表
            scan_type: 扫描类型
        """
        debug_event('INFO', 'SmartCleaner', '_on_scan_completed',
                   '接收扫描完成信号',
                   scan_type=scan_type,
                   items_count=len(items))

        self.scan_items = items
        self.logger.info(f"[SMART_CLEAN] 扫描完成: {len(items)} 项")

        # 进入分析阶段
        self._set_phase(SmartCleanPhase.ANALYZING)

        debug_event('INFO', 'SmartCleaner', '_on_scan_completed',
                   '启动分析线程',
                   items_count=len(items))

        # 在新线程中分析
        self.analyze_thread = AnalyzeThread(self.ai_analyzer, items, self.config)
        self.analyze_thread.progress.connect(self.analyze_progress.emit)
        self.analyze_thread.completed.connect(lambda plan: self._on_analyze_completed(plan, scan_type))
        self.analyze_thread.error.connect(self.error.emit)
        self.analyze_thread.start()

    def _on_analyze_completed(self, plan: CleanupPlan, scan_type: str):
        """分析完成回调

        Args:
            plan: 清理计划
            scan_type: 扫描类型
        """
        self.current_plan = plan
        self.current_plan.scan_type = scan_type
        self.current_plan.scan_target = self.scan_thread.scan_target if self.scan_thread else ""

        self.logger.info(f"[SMART_CLEAN] 分析完成: Safe={plan.safe_count}, "
                        f"Suspicious={plan.suspicious_count}, "
                        f"Dangerous={plan.dangerous_count}")

        # 预览阶段
        self._set_phase(SmartCleanPhase.PREVIEW)
        self.plan_ready.emit(plan)

    def execute_cleanup(self, selected_items: Optional[List[CleanupItem]] = None) -> bool:
        """
        执行清理

        Args:
            selected_items: 选中的清理项，None 表示全部

        Returns:
            是否成功启动
        """
        if not self.current_plan:
            self.logger.error("[SMART_CLEAN] 没有可执行的清理计划")
            return False

        self._set_phase(SmartCleanPhase.EXECUTING)
        self.logger.info("[SMART_CLEAN] 开始执行清理")

        # 准备要清理的项目
        items_to_clean = selected_items or self.current_plan.items

        # 创建新的计划（只包含选中的项）
        execution_plan = CleanupPlan(
            plan_id=f"exec_{int(time.time())}",
            scan_type=self.current_plan.scan_type,
            scan_target=self.current_plan.scan_target,
            items=items_to_clean,
            total_size=sum(item.size for item in items_to_clean),
            estimated_freed=sum(item.size for item in items_to_clean if item.is_safe)
        )

        # 准备执行配置
        execution_config = ExecutionConfig(
            max_retries=self.config.max_retries,
            enable_backup=self.config.enable_backup
        )

        # 启动执行
        success = self.executor.execute_plan(execution_plan, execution_config)

        if not success:
            self._set_phase(SmartCleanPhase.ERROR)
            return False

        return True

    def cancel(self):
        """取消当前操作"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.logger.info("[SMART_CLEAN] 取消扫描")
            self.scan_thread.cancel()
            self.scan_thread.wait(5000)

        if not self.executor.is_idle():
            self.logger.info("[SMART_CLEAN] 取消执行")
            self.executor.cancel_execution()

    def get_current_phase(self) -> SmartCleanPhase:
        """获取当前阶段

        Returns:
            当前阶段
        """
        return self.current_phase

    def get_scan_results(self) -> List[ScanItem]:
        """获取扫描结果

        Returns:
            扫描项列表
        """
        return self.scan_items

    def get_cleanup_plan(self) -> Optional[CleanupPlan]:
        """获取清理计划

        Returns:
            清理计划
        """
        return self.current_plan

    def get_plan_summary(self) -> Dict:
        """获取计划摘要

        Returns:
            计划摘要字典
        """
        if not self.current_plan:
            return {}

        return {
            'total_items': self.current_plan.total_items,
            'safe_count': self.current_plan.safe_count,
            'suspicious_count': self.current_plan.suspicious_count,
            'dangerous_count': self.current_plan.dangerous_count,
            'total_size': self.current_plan.total_size,
            'estimated_freed': self.current_plan.estimated_freed,
            'ai_calls': self.current_plan.ai_call_count
        }

    def _set_phase(self, phase: SmartCleanPhase):
        """设置当前阶段

        Args:
            phase: 阶段
        """
        self.current_phase = phase
        self.phase_changed.emit(phase.value)
        self.logger.debug(f"[SMART_CLEAN] 阶段变更: {phase.value}")

    def _is_idle(self) -> bool:
        """检查是否空闲

        Returns:
            是否空闲
        """
        return (
            self.current_phase == SmartCleanPhase.IDLE or
            self.current_phase == SmartCleanPhase.PREVIEW or
            self.current_phase == SmartCleanPhase.COMPLETED or
            self.current_phase == SmartCleanPhase.ERROR
        )

    def reset(self):
        """重置清理器状态"""
        self._set_phase(SmartCleanPhase.IDLE)
        self.scan_items = []
        self.current_plan = None


# 便利函数
def get_smart_cleaner(
    config: SmartCleanConfig = None,
    backup_mgr: BackupManager = None,
    db: Database = None
) -> SmartCleaner:
    """获取智能清理器实例

    Args:
        config: 智能清理配置
        backup_mgr: 备份管理器
        db: 数据库实例

    Returns:
        SmartCleaner 实例
    """
    return SmartCleaner(
        config=config,
        backup_mgr=backup_mgr,
        db=db
    )
