import os
import sys
import shutil
import threading
import time
from typing import Callable, Optional, List, Dict, Any, Tuple
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal
import psutil
from PyQt5.QtCore import QSettings

from .database import get_database
from .rule_engine import RuleEngine, RiskLevel, get_rule_engine
from ..utils.logger import get_logger, log_scan_event, log_file_operation, log_performance
from ..utils.debug_tracker import debug_event, debug_exception, timing_context, get_debug_summary, get_performance_stats


logger = get_logger(__name__)

# 扫描器风险评估模式
RISK_MODE_RULE_ONLY = False    # 规则评估：用于系统缓存、浏览器等安全维度
RISK_MODE_AI_ENHANCED = True   # AI评估：用于AppData、自定义扫描等危险场景
from .whitelist import get_whitelist
from .ai_enhancer import AIEnhancer, get_ai_enhancer
from .risk_assessment import get_risk_assessment_system, FinalRiskAssessment
from .models import ScanItem


class ScanRiskAssessor:
    """Shared risk assessment logic for all scanners

    This class provides consistent risk assessment across SystemScanner,
    BrowserScanner, and AppDataScanner following DRY principle.

    Uses the integrated RiskAssessmentSystem that combines:
    1. Whitelist protection
    2. Rule engine assessment
    3. AI enhancement (if enabled)

    Risk Assessment Strategy:
    - Safe scenarios (System, Browser): Use rule-based evaluation only
    - Dangerous scenarios (AppData, Custom): Use AI-enhanced evaluation
    """

    def __init__(self, use_ai_evaluation: bool = False):
        """Initialize the risk assessor with required dependencies

        Args:
            use_ai_evaluation: If True, use AI evaluation for dangerous scenarios.
                             If False, use rule-only evaluation for safe scenarios.
        """
        self.whitelist = get_whitelist()
        self.use_ai_evaluation = use_ai_evaluation

        try:
            self.risk_assessment_system = get_risk_assessment_system()
        except Exception as e:
            print(f"风险评估系统初始化失败: {e}")
            self.risk_assessment_system = None

    def set_ai_enabled(self, enabled: bool):
        """Enable or disable AI assessment"""
        if self.risk_assessment_system:
            self.risk_assessment_system.enable_ai(enabled)

    def assess(self, path: str, description: str, size: int,
              item_type: str = 'directory') -> Tuple[str, str]:
        """Assess risk level and get AI-enhanced description

        Args:
            path: The file or directory path to assess
            description: Description of the item
            size: Size in bytes
            item_type: Type of item ('file' or 'directory')

        Returns:
            Tuple of (risk_level, description) where risk_level is one of:
            'safe', 'suspicious', 'dangerous'
        """
        # 1. Check whitelist first - protected items are dangerous
        if self.whitelist.is_protected(path):
            return RiskLevel.DANGEROUS.value, f'{description} (白名单保护)'

        # 2. Use integrated risk assessment system
        try:
            if not self.risk_assessment_system:
                # Fallback to rule engine only
                from .rule_engine import get_rule_engine
                rule_engine = get_rule_engine()
                risk_level = rule_engine.classify(path, size, None, item_type == 'file')
                return risk_level.value, description

            scan_item = ScanItem(path, size, item_type, description, RiskLevel.SUSPICIOUS.value)

            # 根据使用场景选择评估策略
            if self.use_ai_evaluation:
                # 危险场景（AppData、自定义扫描）：强制使用 AI 或增强评估
                assessment = self.risk_assessment_system.assess_item(scan_item)
            else:
                # 安全场景（系统缓存、浏览器缓存）：优先使用规则引擎
                # 创建一个只使用规则的临时评估
                from .rule_engine import get_rule_engine
                rule_engine = get_rule_engine()
                risk_level = rule_engine.classify(path, size, None, item_type == 'file')
                assessment = type('obj', (object,), {
                    'risk_level': RiskLevel.from_string(risk_level.value) if isinstance(risk_level, RiskLevel) else RiskLevel.SAFE,
                    'reason': '规则评估',
                    'method': 'rule_only',
                    'rule_assessment': None,
                    'ai_response': None
                })()

            # 3. Return the final assessment result
            risk_level = assessment.risk_level.value

            # 4. Build enhanced description
            if assessment.method == "ai_enhanced":
                enhanced_desc = f'{description} (AI: {assessment.reason})'
            elif assessment.method == "whitelist":
                enhanced_desc = f'{description} (白名单)'
            else:  # rule_only
                enhanced_desc = f'{description} (规则评估)'

            return risk_level, enhanced_desc

        except Exception as e:
            print(f"风险评估失败: {e}")
            return RiskLevel.SUSPICIOUS.value, description

    def reload_ai_config(self):
        """Reload AI configuration from settings"""
        from .config_manager import get_config_manager
        config_mgr = get_config_manager()
        ai_config = config_mgr.get_ai_config()
        ai_enabled = ai_config['enabled']

        if ai_enabled:
            from .ai_client import AIConfig
            api_url = ai_config['api_url']
            api_key = ai_config['api_key']
            ai_model = ai_config['api_model']

            if api_url and api_key:
                config = AIConfig(api_url=api_url, api_key=api_key, model=ai_model)
                self.risk_assessment_system.set_ai_config(config)

        self.risk_assessment_system.enable_ai(ai_enabled)


class ScanEventType:
    """Scan event types"""
    PROGRESS = 'progress'
    ITEM_FOUND = 'item_found'
    ERROR = 'error'
    COMPLETE = 'complete'
    CANCELLED = 'cancelled'


class ScanEvent:
    """Scan event data"""
    def __init__(self, event_type: str, data: Any = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = time.time()


class SystemScanner(QObject):
    """System directory scanner"""
    # Signals
    progress = pyqtSignal(str)  # Progress message
    item_found = pyqtSignal(object)  # ScanItem found
    error = pyqtSignal(str)  # Error message
    complete = pyqtSignal(list)  # List of ScanItems

    # 静态方法：获取目录大小（支持取消标志）
    @staticmethod
    def _get_directory_size(path: str, cancel_flag=None, timeout_seconds=30, max_files=10000) -> int:
        """Get directory size with optional cancel support and progress reporting

        Args:
            path: Directory path
            cancel_flag: Optional function that returns True if cancelled
            timeout_seconds: Timeout in seconds to prevent hanging

        Returns:
            Total size in bytes
        """
        start_time = time.time()

        debug_event('DEBUG', 'SystemScanner', '_get_directory_size',
                   f'开始计算目录大小: {path}',
                   path=path)

        try:
            # 检查目录是否存在和是否可访问
            dir_path = Path(path)
            if not dir_path.exists() or not dir_path.is_dir():
                return 0

            total = 0
            count = 0
            last_report_time = time.time()
            last_progress_files = 0

            # 使用递归但设置超时保护
            def walk_with_timeout(d):
                nonlocal total, count, last_report_time, last_progress_files
                try:
                    # 使用 os.scandir 比 Path.glob 更快
                    with os.scandir(d) as scandir_it:
                        for entry in scandir_it:
                            if cancel_flag and cancel_flag():
                                return
                            # 超时检查
                            if time.time() - start_time > timeout_seconds:
                                logger.warning(f"[扫描:SIZE] 计算目录大小超时: {path} (已过 {timeout_seconds}秒)")
                                return
                            # 最大文件数检查
                            if count >= max_files:
                                logger.warning(f"[扫描:SIZE] 计算目录大小已达到最大文件数限制: {path} ({max_files})")
                                return

                            try:
                                if entry.is_file():
                                    try:
                                        total += entry.stat().st_size
                                    except (OSError, PermissionError):
                                        pass
                                    count += 1
                                elif entry.is_dir():
                                    # 递归进入子目录
                                    try:
                                        walk_with_timeout(Path(entry.path))
                                    except (PermissionError, OSError):
                                        pass
                            except (PermissionError, OSError):
                                pass

                            # 进度报告
                            current_time = time.time()
                            if count - last_progress_files >= 100 or (current_time - last_report_time) >= 2.0:
                                logger.debug(f"[扫描:SIZE] 扫描中: {path} - 已处理 {count} 个文件, 大小: {total/1024/1024:.2f}MB, 耗时: {current_time - start_time:.1f}秒")
                                last_report_time = current_time
                                last_progress_files = count
                except (PermissionError, OSError) as e:
                    # 对于根目录级别的权限错误，记录日志但不抛出
                    logger.debug(f"[扫描:SIZE] 无法访问目录: {d}, 错误: {e}")

            walk_with_timeout(dir_path)

            duration = time.time() - start_time
            logger.info(f"[扫描:SIZE] 完成计算 {path}: {count} 个文件, {total/1024/1024:.2f}MB, 耗时: {duration:.2f}秒")
            debug_event('INFO', 'SystemScanner', '_get_directory_size',
                       '计算完成',
                       path=path,
                       file_count=count,
                       size_bytes=total,
                       size_mb=total/1024/1024,
                       duration_seconds=duration)

            return total
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[扫描:ERROR] 计算目录大小失败 {path}: {str(e)}, 耗时: {duration:.2f}秒")
            debug_exception('SystemScanner', '_get_directory_size',
                          '计算目录大小异常', exc_info=sys.exc_info(), path=path)
            return 0

    @staticmethod
    def _can_access_directory(path: str) -> bool:
        """Check if directory can be accessed"""
        try:
            test_file = os.path.join(path, '.__access_test__')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except Exception:
            try:
                os.listdir(path)
                return True
            except Exception:
                return False

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.scan_thread = None
        self.scan_results: List[ScanItem] = []
        self.db = get_database()
        # 系统缓存是安全场景，使用规则引擎评估
        self.risk_assessor = ScanRiskAssessor(use_ai_evaluation=False)
        logger.debug("[SystemScanner] 系统扫描器初始化完成")

    def reload_ai_config(self):
        """Reload AI configuration from settings"""
        self.risk_assessor.reload_ai_config()

    def start_scan(self, scan_types: List[str] = None):
        """Start scanning system directories (async)

        Args:
            scan_types: List of scan types to perform. If None, scan all.
                      Types: 'temp', 'prefetch', 'logs', 'update_cache'
        """
        if self.is_running:
            logger.warning("[SystemScanner] 扫描已经在运行中，忽略新的扫描请求")
            return

        logger.info("[扫描:START] 开始系统扫描")

        self.is_running = True
        self.is_cancelled = False
        self.scan_results = []

        if scan_types is None:
            scan_types = ['temp', 'prefetch', 'logs', 'update_cache']

        logger.debug(f"[扫描:CONFIG] 扫描类型: {', '.join(scan_types)}")

        # Start scan in separate thread
        self.scan_thread = threading.Thread(
            target=self._scan_thread,
            args=(scan_types,),
            daemon=True
        )
        self.scan_thread.start()

    def scan_sync(self, scan_types: List[str] = None) -> list:
        """扫描系统目录（同步版本，直接在调用线程中执行）

        Args:
            scan_types: List of scan types to perform. If None, scan all.
                      Types: 'temp', 'prefetch', 'logs', 'update_cache'

        Returns:
            List of ScanItems
        """
        if scan_types is None:
            scan_types = ['temp', 'prefetch', 'logs', 'update_cache']

        logger.info(f"[扫描:SYNC] 开始同步系统扫描: {', '.join(scan_types)}")

        self.is_running = True
        self.is_cancelled = False
        self.scan_results = []

        try:
            # 直接执行扫描逻辑（在新线程中）
            self._scan_thread(scan_types)
            return self.scan_results
        finally:
            self.is_running = False

    def cancel_scan(self):
        """Cancel current scan"""
        logger.info("[扫描:CANCEL] 用户取消系统扫描")
        self.is_cancelled = True

    def _scan_thread(self, scan_types: List[str]):
        """Scan thread function"""
        scan_start_time = time.time()
        logger.debug("[扫描:THREAD] 扫描线程启动")

        try:
            total_types = len(scan_types)
            logger.info(f"[扫描:PROGRESS] 准备扫描 {total_types} 个类型目录")

            for i, scan_type in enumerate(scan_types):
                if self.is_cancelled:
                    logger.info("[扫描:CANCEL] 扫描被用户取消")
                    break

                type_start = time.time()
                logger.info(f"[扫描:PROGRESS] 开始扫描 {scan_type} ({i+1}/{total_types})")
                self.progress.emit(f'Scanning {scan_type}... ({i+1}/{total_types})')
                logger.debug(f"[扫描:PROGRESS] 开始扫描 {scan_type} ({i+1}/{total_types})")

                if scan_type == 'temp':
                    items_before = len(self.scan_results)
                    logger.debug(f"[扫描:TEMP] 开始扫描 temp 目录")
                    self._scan_temp_directories()
                    items_found = len(self.scan_results) - items_before
                    duration = int((time.time() - type_start) * 1000)
                    logger.info(f"[扫描:INFO] 扫描 temp 耗时: {duration}ms items={items_found} 发现: {items_found > 0}")
                    log_performance(logger, f"扫描 temp", duration, items=items_found)
                elif scan_type == 'prefetch':
                    items_before = len(self.scan_results)
                    logger.debug(f"[扫描:PREFETCH] 开始扫描 prefetch 目录")
                    self._scan_prefetch()
                    items_found = len(self.scan_results) - items_before
                    duration = int((time.time() - type_start) * 1000)
                    logger.info(f"[扫描:INFO] 扫描 prefetch 耗时: {duration}ms items={items_found}")
                    log_performance(logger, f"扫描 prefetch", duration, items=items_found)
                elif scan_type == 'logs':
                    items_before = len(self.scan_results)
                    logger.debug(f"[扫描:LOGS] 开始扫描 logs 目录")
                    self._scan_logs()
                    items_found = len(self.scan_results) - items_before
                    duration = int((time.time() - type_start) * 1000)
                    logger.info(f"[扫描:INFO] 扫描 logs 耗时: {duration}ms items={items_found}")
                    log_performance(logger, f"扫描 logs", duration, items=items_found)
                elif scan_type == 'update_cache':
                    items_before = len(self.scan_results)
                    logger.debug(f"[扫描:UPDATE_CACHE] 开始扫描 update_cache 目录")
                    self._scan_update_cache()
                    items_found = len(self.scan_results) - items_before
                    duration = int((time.time() - type_start) * 1000)
                    logger.info(f"[扫描:INFO] 扫描 update_cache 耗时: {duration}ms items={items_found}")
                    log_performance(logger, f"扫描 update_cache", duration, items=items_found)

            if not self.is_cancelled:
                total_duration = (time.time() - scan_start_time) * 1000
                total_size = sum(item.size for item in self.scan_results)
                log_scan_event(logger, 'COMPLETE', "system", count=len(self.scan_results), size=f"{total_size/1024/1024:.2f}MB")
                self.progress.emit('Scan complete!')
                self.complete.emit(self.scan_results)
            else:
                logger.info("[扫描:CANCELLED] 扫描已取消")
                self.progress.emit('Scan cancelled')
                self.complete.emit([])
        except Exception as e:
            logger.error(f"[扫描:ERROR] 扫描线程异常: {str(e)}")
            self.error.emit(f'Scan error: {str(e)}')
            self.complete.emit([])
        finally:
            self.is_running = False
            logger.debug("[扫描:THREAD] 扫描线程结束")

    def _assess_item_risk(self, path: str, description: str, size: int) -> tuple[str, str]:
        """Assess risk level and get AI-enhanced description
        Returns: (risk_level, description)"""
        return self.risk_assessor.assess(path, description, size, 'directory')

    def _scan_temp_directories(self):
        """Scan Windows temporary directories"""
        logger.debug("[扫描:TEMP] 开始扫描临时目录")
        temp_dirs = [
            (r'C:\Windows\Temp', 'Windows Temp'),
            (os.environ.get('TEMP', ''), 'User Temp'),
            (os.environ.get('TMP', ''), 'User TMP'),
        ]

        for temp_path, desc in temp_dirs:
            if self.is_cancelled:
                logger.debug("[扫描:TEMP] 扫描被取消")
                break
            if not temp_path or not os.path.exists(temp_path):
                logger.debug(f"[扫描:TEMP] 跳过不存在的目录: {desc}")
                continue

            try:
                logger.debug(f"[扫描:TEMP] 检查目录访问: {temp_path}")
                if not self._can_access_directory(temp_path):
                    logger.debug(f"[扫描:TEMP] 无访问权限: {desc}")
                    continue

                logger.debug(f"[扫描:TEMP] 计算目录大小: {desc}")
                size = self._get_directory_size(temp_path, lambda: self.is_cancelled)
                if size == -1:
                    logger.debug("[扫描:TEMP] 计算目录大小被取消")
                    break
                if size > 0:
                    logger.debug(f"[扫描:TEMP] 发现项目: {desc}, 大小: {size} 字节")
                    log_file_operation(logger, 'SCAN', temp_path, size=size)

                    risk_level, description = self._assess_item_risk(temp_path, desc, size)
                    logger.debug(f"[扫描:TEMP] 风险评估: {desc} -> {risk_level}")

                    item = ScanItem(
                        path=temp_path,
                        size=size,
                        item_type='directory',
                        description=description,
                        risk_level=risk_level
                    )
                    self.scan_results.append(item)
                    self.item_found.emit(item)

                    self.db.upsert_system_scan(
                        scan_type='temp',
                        path=temp_path,
                        size=size,
                        description=description,
                        risk_level=risk_level
                    )
            except PermissionError as e:
                logger.debug(f"[扫描:TEMP] 权限错误: {desc} - {str(e)}")
                continue
            except Exception as e:
                logger.error(f"[扫描:ERROR] 扫描临时目录失败 {desc}: {str(e)}")
                self.error.emit(f'Error scanning {desc}: {str(e)}')

        logger.debug(f"[扫描:TEMP] 临时目录扫描完成，发现 {len([i for i in self.scan_results if 'temp' in i.path.lower()])} 个项目")

    def _scan_prefetch(self):
        """Scan Windows Prefetch directory"""
        if self.is_cancelled:
            return

        prefetch_path = r'C:\Windows\Prefetch'
        if not os.path.exists(prefetch_path):
            return

        try:
            if not self._can_access_directory(prefetch_path):
                return

            size = self._get_directory_size(prefetch_path, lambda: self.is_cancelled)
            if size == -1:
                return
            if size > 0:
                desc = 'Windows Prefetch (can be regenerated)'
                risk_level, description = self._assess_item_risk(prefetch_path, desc, size)
                item = ScanItem(
                    path=prefetch_path,
                    size=size,
                    item_type='directory',
                    description=description,
                    risk_level=risk_level
                )
                self.scan_results.append(item)
                self.item_found.emit(item)

                self.db.upsert_system_scan(
                    scan_type='prefetch',
                    path=prefetch_path,
                    size=size,
                    description=description,
                    risk_level=risk_level
                )
        except Exception as e:
            self.error.emit(f'Error scanning Prefetch: {str(e)}')

    def _scan_logs(self):
        """Scan Windows Logs directory"""
        log_dirs = [
            (r'C:\Windows\Logs', 'Windows Logs'),
            (r'C:\Windows\System32\LogFiles', 'System Log Files'),
        ]

        for log_path, desc in log_dirs:
            if self.is_cancelled:
                break
            if not log_path or not os.path.exists(log_path):
                continue

            try:
                if not self._can_access_directory(log_path):
                    continue

                size = self._get_directory_size(log_path, lambda: self.is_cancelled)
                if size == -1:
                    break
                if size > 0:
                    risk_level, description = self._assess_item_risk(log_path, desc, size)
                    item = ScanItem(
                        path=log_path,
                        size=size,
                        item_type='directory',
                        description=description,
                        risk_level=risk_level
                    )
                    self.scan_results.append(item)
                    self.item_found.emit(item)

                    self.db.upsert_system_scan(
                        scan_type='logs',
                        path=log_path,
                        size=size,
                        description=description,
                        risk_level=risk_level
                    )
            except Exception as e:
                self.error.emit(f'Error scanning {desc}: {str(e)}')

    def _scan_update_cache(self):
        """Scan Windows Update cache"""
        if self.is_cancelled:
            return

        update_cache_path = r'C:\Windows\SoftwareDistribution\Download'
        if not os.path.exists(update_cache_path):
            return

        try:
            if not self._can_access_directory(update_cache_path):
                return

            size = self._get_directory_size(update_cache_path, lambda: self.is_cancelled)
            if size == -1:
                return
            if size > 0:
                desc = 'Windows Update Download Cache'
                risk_level, description = self._assess_item_risk(update_cache_path, desc, size)
                item = ScanItem(
                    path=update_cache_path,
                    size=size,
                    item_type='directory',
                    description=description,
                    risk_level=risk_level
                )
                self.scan_results.append(item)
                self.item_found.emit(item)

                self.db.upsert_system_scan(
                    scan_type='update_cache',
                    path=update_cache_path,
                    size=size,
                    description=description,
                    risk_level=risk_level
                )
        except Exception as e:
            self.error.emit(f'Error scanning Update Cache: {str(e)}')


class BrowserScanner(QObject):
    """Browser cache scanner"""
    # Signals
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    # 支持的浏览器配置
    BROWSER_CONFIGS = {
        'chrome': {
            'name': 'Google Chrome',
            'local_paths': [
                r'Google\Chrome\User Data\Default\Cache',
                r'Google\Chrome\User Data\Default\Code Cache',
                r'Google\Chrome\User Data\Default\GPUCache',
            ],
            'roaming_paths': [],
        },
        'edge': {
            'name': 'Microsoft Edge',
            'local_paths': [
                r'Microsoft\Edge\User Data\Default\Cache',
                r'Microsoft\Edge\User Data\Default\Code Cache',
                r'Microsoft\Edge\User Data\Default\GPUCache',
            ],
            'roaming_paths': [],
        },
        'firefox': {
            'name': 'Mozilla Firefox',
            'local_paths': [],
            'roaming_paths': [
                r'Mozilla\Firefox\Profiles',
            ],
        },
        'opera': {
            'name': 'Opera',
            'local_paths': [
                r'Opera Software\Opera Stable\Cache',
                r'Opera Software\Opera Stable\Code Cache',
                r'Opera Software\Opera Stable\GPUCache',
            ],
            'roaming_paths': [],
        },
    }

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.scan_thread = None
        self.scan_results: List[ScanItem] = []
        # 浏览器缓存是安全场景，使用规则引擎评估
        self.risk_assessor = ScanRiskAssessor(use_ai_evaluation=False)
        self.detected_browsers = []
        logger.debug("[BrowserScanner] 浏览器扫描器初始化完成")

    def reload_ai_config(self):
        """Reload AI configuration from settings"""
        logger.debug("[BrowserScanner] 重载 AI 配置")
        self.risk_assessor.reload_ai_config()

    def detect_installed_browsers(self) -> List[str]:
        """检测已安装的浏览器"""
        logger.debug("[BrowserScanner] 开始检测已安装的浏览器")
        detected = []

        for browser_id, config in self.BROWSER_CONFIGS.items():
            if self._check_browser_installed(browser_id, config):
                detected.append(browser_id)
                logger.debug(f"[BrowserScanner] 检测到浏览器: {browser_id}")

        logger.info(f"[BrowserScanner] 检测完成，发现 {len(detected)} 个浏览器: {', '.join(detected) or '无'}")
        return detected

    def _check_browser_installed(self, browser_id: str, config: Dict) -> bool:
        """检查浏览器是否已安装"""
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        app_data = os.environ.get('APPDATA', '')

        # 检查 LocalAppData 路径
        if local_app_data:
            for path in config['local_paths']:
                full_path = os.path.join(local_app_data, path)
                if os.path.exists(full_path):
                    return True

        # 检查 AppData 路径
        if app_data:
            for path in config['roaming_paths']:
                full_path = os.path.join(app_data, path)
                if os.path.exists(full_path):
                    return True

        return False

    def start_scan(self, browsers: List[str] = None):
        """Start scanning browser caches

        Args:
            browsers: List of browsers to scan ['chrome', 'edge', 'firefox']
                     If None, auto-detect installed browsers
        """
        if self.is_running:
            logger.warning("[BrowserScanner] 扫描已在运行，忽略新的请求")
            return

        logger.info("[扫描:START] 开始浏览器缓存扫描")

        self.is_running = True
        self.is_cancelled = False
        self.scan_results = []

        # 自动检测浏览器
        if browsers is None:
            browsers = self.detect_installed_browsers()

        if not browsers:
            logger.warning("[BrowserScanner] 未检测到已安装的浏览器")
            self.progress.emit('No browsers detected')
            self.complete.emit([])
            return

        logger.info(f"[BrowserScanner] 将扫描浏览器: {', '.join(browsers)}")

        self.scan_thread = threading.Thread(
            target=self._scan_thread,
            args=(browsers,),
            daemon=True
        )
        self.scan_thread.start()

    def cancel_scan(self):
        """Cancel current scan"""
        logger.info("[扫描:CANCEL] 用户取消浏览器扫描")
        self.is_cancelled = True

    def _scan_thread(self, browsers: List[str]):
        """Scan thread function"""
        scan_start_time = time.time()
        logger.debug("[扫描:THREAD] 浏览器扫描线程启动")

        try:
            total = len(browsers)
            logger.info(f"[扫描:PROGRESS] 准备扫描 {total} 个浏览器")

            for i, browser in enumerate(browsers):
                if self.is_cancelled:
                    logger.info("[扫描:CANCEL] 浏览器扫描被取消")
                    break

                self.progress.emit(f'Scanning {browser}... ({i+1}/{total})')
                logger.debug(f"[扫描:PROGRESS] 开始扫描 {browser} ({i+1}/{total})")

                type_start = time.time()
                if browser == 'chrome':
                    items_before = len(self.scan_results)
                    self._scan_chrome()
                    items_found = len(self.scan_results) - items_before
                    log_performance(logger, f"扫描 Chrome", int((time.time() - type_start) * 1000), items=items_found)
                elif browser == 'edge':
                    items_before = len(self.scan_results)
                    self._scan_edge()
                    items_found = len(self.scan_results) - items_before
                    log_performance(logger, f"扫描 Edge", int((time.time() - type_start) * 1000), items=items_found)
                elif browser == 'firefox':
                    items_before = len(self.scan_results)
                    self._scan_firefox()
                    items_found = len(self.scan_results) - items_before
                    log_performance(logger, f"扫描 Firefox", int((time.time() - type_start) * 1000), items=items_found)
                elif browser == 'opera':
                    items_before = len(self.scan_results)
                    self._scan_opera()
                    items_found = len(self.scan_results) - items_before
                    log_performance(logger, f"扫描 Opera", int((time.time() - type_start) * 1000), items=items_found)

            if not self.is_cancelled:
                total_duration = (time.time() - scan_start_time) * 1000
                total_size = sum(item.size for item in self.scan_results)
                log_scan_event(logger, 'COMPLETE', "browser", count=len(self.scan_results), size=f"{total_size/1024/1024:.2f}MB")
                self.progress.emit('Browser scan complete!')
                self.complete.emit(self.scan_results)
            else:
                logger.info("[扫描:CANCELLED] 浏览器扫描已取消")
                self.progress.emit('Scan cancelled')
                self.complete.emit([])
        except Exception as e:
            logger.error(f"[扫描:ERROR] 浏览器扫描线程异常: {str(e)}")
            self.error.emit(f'Scan error: {str(e)}')
            self.complete.emit([])
        finally:
            self.is_running = False
            logger.debug("[扫描:THREAD] 浏览器扫描线程结束")

    def _assess_item_risk(self, path: str, description: str, size: int) -> tuple[str, str]:
        """Assess risk level and get AI-enhanced description
        Returns: (risk_level, description)"""
        return self.risk_assessor.assess(path, description, size, 'directory')

    def _scan_chrome(self):
        """Scan Google Chrome cache"""
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if not local_app_data:
            return

        # 尝试找到 Chrome 的实际缓存目录
        chrome_user_data = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data')
        if not os.path.exists(chrome_user_data):
            return

        # 查找 Default 配置文件中的缓存路径
        cache_paths_found = []

        # 方法1: 检查常见的缓存目录名
        possible_cache_dirs = ['Cache', 'Code Cache', 'GPUCache', 'Service Worker', 'Cache2']

        # 直接搜索 Default 目录下的缓存相关目录
        default_path = os.path.join(chrome_user_data, 'Default')
        if os.path.exists(default_path):
            for item in os.listdir(default_path):
                item_path = os.path.join(default_path, item)
                if os.path.isdir(item_path) and 'Cache' in item:
                    cache_paths_found.append(item_path)

        # 方法2: 检查 Default/Network 目录
        network_dir = os.path.join(default_path, 'Network')
        if os.path.exists(network_dir):
            for item in os.listdir(network_dir):
                item_path = os.path.join(network_dir, item)
                if os.path.isdir(item_path):
                    cache_paths_found.append(item_path)

        # 扫描找到的缓存路径
        for cache_path in cache_paths_found[:10]:  # 最多扫描10个
            try:
                size = SystemScanner._get_directory_size(cache_path)
                if size > 0:
                    desc = f'Google Chrome 缓存 ({os.path.basename(cache_path)})'
                    risk_level, description = self._assess_item_risk(cache_path, desc, size)
                    item = ScanItem(
                        path=cache_path,
                        size=size,
                        item_type='directory',
                        description=description,
                        risk_level=risk_level
                    )
                    self.scan_results.append(item)
                    self.item_found.emit(item)
            except Exception as e:
                self.debug_log(f'Error scanning Chrome cache {cache_path}: {e}')

    def _scan_edge(self):
        """Scan Microsoft Edge cache"""
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if not local_app_data:
            return

        # 查找 Edge 的实际缓存目录
        edge_user_data = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
        if not os.path.exists(edge_user_data):
            return

        cache_paths_found = []

        default_path = os.path.join(edge_user_data, 'Default')
        if os.path.exists(default_path):
            for item in os.listdir(default_path):
                item_path = os.path.join(default_path, item)
                if os.path.isdir(item_path) and 'Cache' in item:
                    cache_paths_found.append(item_path)

        network_dir = os.path.join(default_path, 'Network')
        if os.path.exists(network_dir):
            for item in os.listdir(network_dir):
                item_path = os.path.join(network_dir, item)
                if os.path.isdir(item_path):
                    cache_paths_found.append(item_path)

        # 扫描找到的缓存路径
        for cache_path in cache_paths_found[:10]:
            try:
                size = SystemScanner._get_directory_size(cache_path)
                if size > 0:
                    desc = f'Microsoft Edge 缓存 ({os.path.basename(cache_path)})'
                    risk_level, description = self._assess_item_risk(cache_path, desc, size)
                    item = ScanItem(
                        path=cache_path,
                        size=size,
                        item_type='directory',
                        description=description,
                        risk_level=risk_level
                    )
                    self.scan_results.append(item)
                    self.item_found.emit(item)
            except Exception as e:
                self.debug_log(f'Error scanning Edge cache {cache_path}: {e}')

    def _scan_firefox(self):
        """Scan Firefox cache"""
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if not local_app_data:
            return

        firefox_profile_path = os.path.join(local_app_data, r'Mozilla\Firefox\Profiles')
        if not os.path.exists(firefox_profile_path):
            return

        try:
            # 扫描所有配置文件
            for profile_dir in os.listdir(firefox_profile_path):
                if self.is_cancelled:
                    break

                # 只扫描默认配置文件
                if not (profile_dir.endswith('.default') or 'default-release' in profile_dir):
                    continue

                profile_path = os.path.join(firefox_profile_path, profile_dir)
                if not os.path.isdir(profile_path):
                    continue

                # 扫描多个 Firefox 缓存目录
                cache_dirs = ['cache2', 'startupCache', 'thumbnails']
                for cache_dir in cache_dirs:
                    cache_path = os.path.join(profile_path, cache_dir)
                    if os.path.exists(cache_path) and os.path.isdir(cache_path):
                        try:
                            size = SystemScanner._get_directory_size(cache_path)
                            if size > 0:
                                desc = f'Mozilla Firefox {cache_dir} ({profile_dir})'
                                risk_level, description = self._assess_item_risk(cache_path, desc, size)
                                item = ScanItem(
                                    path=cache_path,
                                    size=size,
                                    item_type='directory',
                                    description=description,
                                    risk_level=risk_level
                                )
                                self.scan_results.append(item)
                                self.item_found.emit(item)
                        except Exception as e:
                            self.debug_log(f'Error scanning Firefox cache {cache_dir}: {e}')

        except Exception as e:
            self.error.emit(f'Error scanning Firefox: {str(e)}')

    def _scan_opera(self):
        """Scan Opera cache"""
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        if not local_app_data:
            return

        paths_to_scan = [
            r'Opera Software\Opera Stable\Cache',
            r'Opera Software\Opera Stable\Code Cache',
            r'Opera Software\Opera Stable\GPUCache',
        ]

        for cache_rel_path in paths_to_scan:
            cache_path = os.path.join(local_app_data, cache_rel_path)
            if os.path.exists(cache_path) and os.path.isdir(cache_path):
                try:
                    size = SystemScanner._get_directory_size(cache_path)
                    if size > 0:
                        desc = f'Opera {os.path.basename(cache_rel_path)}'
                        risk_level, description = self._assess_item_risk(cache_path, desc, size)
                        item = ScanItem(
                            path=cache_path,
                            size=size,
                            item_type='directory',
                            description=description,
                            risk_level=risk_level
                        )
                        self.scan_results.append(item)
                        self.item_found.emit(item)
                except Exception as e:
                    self.debug_log(f'Error scanning Opera cache {cache_rel_path}: {e}')

    @staticmethod
    def debug_log(message: str):
        """Debug logging"""
        print(f'[BrowserScanner] {message}')


class AppDataScanner(QObject):
    """AppData directory scanner - 简化稳定版，仅使用规则引擎评估"""
    # Signals
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    error = pyqtSignal(str)
    complete = pyqtSignal(list)

    # 缓存关键词 - 优先扫描包含这些词的文件夹
    CACHE_KEYWORDS = ['cache', 'Cache', 'CACHE', 'temp', 'Temp', 'tmp', 'Tmp', 'log', 'Log',
                       'thumbnail', 'Thumbnail', 'cache2', 'Code Cache', 'GPUCache',
                       'CodeCache', 'Service Worker', 'Blob Storage', 'Cookies',
                       'IndexedDB', 'Session Storage', 'Web Storage',
                       'MediaCache', 'ShaderCache', 'gpucache', 'mediacache']

    # 常见应用目录 - 参考 AppDataCleaner
    COMMON_APPS = {
        # 浏览器
        'Google Chrome': 'safe',
        'Mozilla Firefox': 'safe',
        'Microsoft Edge': 'safe',
        'Brave': 'safe',
        'Opera': 'safe',
        'Vivaldi': 'safe',
        # 生产力
        'Microsoft Office': 'suspicious',
        'Adobe': 'suspicious',
        'Autodesk': 'suspicious',
        'Blizzard': 'suspicious',
        'Epic Games': 'suspicious',
        'Steam': 'suspicious',
        # 开发工具
        'JetBrains': 'suspicious',
        'Visual Studio Code': 'safe',
        'VSCode': 'safe',
        'Git': 'safe',
        'Node.js': 'suspicious',
        'Python': 'suspicious',
        # 通讯软件
        'WeChat': 'suspicious',
        'Tencent': 'suspicious',
        'QQ': 'suspicious',
        'Telegram': 'suspicious',
        'WeChat Files': 'suspicious',
        # 媒体播放器
        'VLC': 'suspicious',
        'Spotify': 'suspicious',
        'KuGou': 'safe',
        'Netease': 'suspicious',
    }

    # 最大扫描数量 - 增加以扫描更多项目
    MAX_ITEMS = 100  # 每类型最多扫描 100 个文件夹

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_cancelled = False
        self.scan_thread = None
        self.scan_results: List[ScanItem] = []

    def reload_ai_config(self):
        """AppData 扫描器不需要 AI 配置"""
        pass

    def start_scan(self, scan_types: List[str] = None):
        """开始扫描 AppData 目录"""
        if self.is_running:
            return

        self.is_running = True
        self.is_cancelled = False
        self.scan_results = []

        if scan_types is None:
            scan_types = ['roaming', 'local', 'local_low']

        self.scan_thread = threading.Thread(
            target=self._scan_thread,
            args=(scan_types,),
            daemon=True
        )
        self.scan_thread.start()

    def cancel_scan(self):
        """取消扫描"""
        self.is_cancelled = True

    def _assess_risk_simple(self, folder_name: str, size: int, folder_type: str = '') -> Tuple[str, str]:
        """改进风险评估 - 参考 AppDataCleaner 的应用评估

        Args:
            folder_name: 文件夹名称
            size: 大小(字节)
            folder_type:文件夹类型（roaming/local/local_low）

        Returns:
            (risk_level, description)
        """
        try:
            lower_name = folder_name.lower()

            # 检查已知应用 - 参考 AppDataCleaner 设计
            for app_name in self.COMMON_APPS:
                if app_name.lower() in lower_name:
                    app_eval = self.COMMON_APPS[app_name]
                    if app_eval == 'safe':
                        return RiskLevel.SAFE.value, f'{folder_name} (可清理缓存)'
                    else:
                        return RiskLevel.SUSPICIOUS.value, f'{folder_name} (应用数据-需审)'

            # 缓存类别检查
            if any(kw in lower_name for kw in self.CACHE_KEYWORDS):
                # 进一步检查是否包含重要应用
                important_apps = ['microsoft', 'google', 'adobe', 'autodesk', 'blizzard', 'epic',
                                'weixin', 'wechat', 'tencent', 'qq', 'telegram', 'spotify']
                if any(app in lower_name for app in important_apps):
                    return RiskLevel.SUSPICIOUS.value, f'{folder_name} (应用缓存需确认)'
                return RiskLevel.SAFE.value, f'{folder_name} (缓存目录)'

            # 普通文件夹风险评估
            if 'temp' in lower_name or 'tmp' in lower_name:
                return RiskLevel.SAFE.value, f'{folder_name} (临时文件)'

            # 小文件夹（可能是无用文件）
            if size < 500 * 1024:  # 小于 500KB
                return RiskLevel.SAFE.value, f'{folder_name} (小文件)'

            # 中等大小文件夹（1MB - 10MB）
            if size < 10 * 1024 * 1024:
                return RiskLevel.SUSPICIOUS.value, f'{folder_name} (需确认)'

            # 大文件夹可能包含重要数据
            if size < 100 * 1024 * 1024:  # 小于 100MB
                return RiskLevel.SUSPICIOUS.value, f'{folder_name} (待AI评估)'

            # 超大文件夹（可能是用户数据）
            return RiskLevel.SUSPICIOUS.value, f'{folder_name} (大型文件夹需审)'

        except Exception as e:
            return RiskLevel.SUSPICIOUS.value, folder_name

    def _get_dir_size_fast(self, path: str) -> int:
        """快速获取目录大小（仅统计前两级）"""
        try:
            total = 0
            for item in Path(path).iterdir():
                if self.is_cancelled:
                    return -1
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except (OSError, PermissionError):
                        pass
                elif item.is_dir():
                    # 只统计子目录的第一层
                    try:
                        for sub_item in item.iterdir():
                            if self.is_cancelled:
                                return -1
                            if sub_item.is_file():
                                try:
                                    total += sub_item.stat().st_size
                                except (OSError, PermissionError):
                                    pass
                    except (OSError, PermissionError):
                        pass
            return total
        except Exception:
            return 0

    def _scan_directory(self, appdata_path: str, folder_type: str):
        """扫描指定 AppData 目录"""
        if not appdata_path or not os.path.exists(appdata_path):
            return

        try:
            entries = sorted(os.listdir(appdata_path), key=str.lower)
            scanned = 0

            # 收集所有目录（缓存目录优先）
            cache_folders = []
            other_folders = []

            for folder_name in entries:
                if self.is_cancelled:
                    break
                folder_path = os.path.join(appdata_path, folder_name)
                if os.path.isdir(folder_path):
                    if any(kw in folder_name.lower() for kw in self.CACHE_KEYWORDS):
                        cache_folders.append((folder_name, folder_path))
                    else:
                        other_folders.append((folder_name, folder_path))

            # 扫描缓存文件夹（更安全）
            for folder_name, folder_path in cache_folders:
                if self.is_cancelled:
                    break

                try:
                    size = self._get_dir_size_fast(folder_path)
                    if size == -1:
                        self.debug_log(f"扫描已取消: {folder_path}")
                        break
                    if size > 0:
                        risk_level, description = self._assess_risk_simple(folder_name, size, 'cache')
                        item = ScanItem(folder_path, size, 'directory', description, risk_level)
                        self.scan_results.append(item)
                        self.item_found.emit(item)
                        scanned += 1
                except Exception as e:
                    print(f"扫描缓存文件夹失败 {folder_path}: {e}")

            # 扫描部分其他文件夹（增加扫描数量）
            max_other = self.MAX_ITEMS - len(cache_folders)
            for folder_name, folder_path in other_folders[:max_other]:
                if self.is_cancelled:
                    break

                try:
                    size = self._get_dir_size_fast(folder_path)
                    if size == -1:
                        self.debug_log(f"扫描已取消: {folder_path}")
                        break
                    if size > 51200:  # 降低阈值到至少 50KB
                        risk_level, description = self._assess_risk_simple(folder_name, size, 'other')
                        item = ScanItem(folder_path, size, 'directory', description, risk_level)
                        self.scan_results.append(item)
                        self.item_found.emit(item)
                        scanned += 1
                except Exception as e:
                    print(f"扫描其他文件夹失败 {folder_path}: {e}")

            self.debug_log(f"{folder_type}: 扫描完成 {scanned} 个文件夹")

        except Exception as e:
            self.error.emit(f'扫描 {folder_type} 失败: {str(e)}')

    def _scan_thread(self, scan_types: List[str]):
        """扫描线程函数"""
        try:
            total = len(scan_types)
            for i, scan_type in enumerate(scan_types):
                if self.is_cancelled:
                    break

                self.progress.emit(f'扫描中 {scan_type}... ({i+1}/{total})')

                # 获取 AppData 路径
                try:
                    local_appdata = os.environ.get('LOCALAPPDATA', '')
                    roaming_appdata = os.environ.get('APPDATA', '')

                    if scan_type.lower() == 'roaming':
                        base_path = roaming_appdata
                    elif scan_type.lower() == 'local':
                        base_path = local_appdata
                    elif scan_type.lower() == 'local_low':
                        base_path = local_appdata + '\\Low' if local_appdata else ''
                    else:
                        continue

                    if base_path:
                        self._scan_directory(base_path, scan_type)
                except Exception as e:
                    print(f"扫描 {scan_type} 路径失败: {e}")
                    self.debug_log(f"扫描 {scan_type} 路径失败: {e}")

            if not self.is_cancelled:
                self.progress.emit('AppData 扫描完成')
                self.complete.emit(self.scan_results)
            else:
                self.progress.emit('扫描已取消')
                self.complete.emit([])
        except Exception as e:
            self.error.emit(f'扫描错误: {str(e)}')
            self.debug_log(f"扫描线程异常: {e}")
            self.complete.emit([])
        finally:
            self.is_running = False

    @staticmethod
    def debug_log(message: str):
        """调试日志"""
        print(f'[AppDataScanner] {message}')


def format_size(size_bytes: int) -> str:
    """Format size in human readable format"""
    if size_bytes == 0:
        return '0 B'

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f'{size:.2f} {units[unit_index]}'
