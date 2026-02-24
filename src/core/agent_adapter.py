# -*- coding: utf-8 -*-
"""
智能体适配器 (Agent Adapter)

将新型智能体系统集成到 PurifyAI 现有框架中

职责:
1. 提供 SmartCleaner 兼容的接口
2. 管理智能体生命周期
3. 转换数据格式
"""
from typing import List, Dict, Optional, Callable, TYPE_CHECKING
import time
import json

from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex

from .models import ScanItem
from .annotation import RiskLevel
from .models_smart import CleanupPlan, CleanupItem, ExecutionResult, ExecutionStatus, CleanupStatus
from agent import (
    get_orchestrator, AgentType, AIConfig,
    get_agent_integration, AgentIntegration
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _get_app_config() -> Dict:
    """获取应用配置（简化版）"""
    import os
    return {
        "ai": {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": os.environ.get("AI_MODEL", "claude-opus-4-6"),
            "max_tokens": int(os.environ.get("AI_MAX_TOKENS", "8192")),
            "temperature": float(os.environ.get("AI_TEMPERATURE", "0.7")),
        }
    }

# 延迟导入避免循环依赖
if TYPE_CHECKING:
    from .smart_cleaner import AgentMode as SmartCleanerAgentMode


class AgentMode:
    """智能体运行模式 - 使用字符串而非Enum避免冲突"""
    DISABLED = "disabled"       # 禁用，使用传统系统
    HYBRID = "hybrid"          # 混合模式：智能体+规则
    FULL = "full"              # 完全智能体模式


class AgentScanner(QThread):
    """智能体扫描器 - 替代传统扫描器

    使用智能体系统进行扫描，保持与传统 ScanItem 的兼容
    """

    # 兼容信号
    progress = pyqtSignal(int, int)
    item_found = pyqtSignal(object)
    complete = pyqtSignal(list)
    error = pyqtSignal(str)
    scan_progress = pyqtSignal(str, int, int)  # 额外：阶段、当前、总数

    def __init__(self, scan_type: str, scan_target: str = "", agent_mode: str = AgentMode.HYBRID):
        super().__init__()
        self.scan_type = scan_type
        self.scan_target = scan_target
        self.agent_mode = agent_mode

        self.is_running = False
        self.is_cancelled = False
        self.mutex = QMutex()
        self.scan_results = []

        self.logger = logger

        # 智能体集成
        self.agent_integration: Optional[AgentIntegration] = None

    def run(self):
        """执行智能体扫描"""
        start_time = time.time()

        try:
            self.is_running = True
            self.scan_progress.emit("init", 0, 100)

            self.logger.info(f"[AGENT_SCANNER] 开始智能体扫描: {self.scan_type}, "
                           f"模式: {self.agent_mode.value}")

            # 获取扫描路径
            scan_paths = self._get_scan_paths()

            if not scan_paths:
                error_msg = f"未找到扫描路径: {self.scan_type}/{self.scan_target}"
                self.logger.error(f"[AGENT_SCANNER] {error_msg}")
                self.error.emit(error_msg)
                return

            self.scan_progress.emit("scanning", 10, 100)

            # 创建智能体集成
            if not self.agent_integration:
                try:
                    config = _get_app_config()
                    ai_config = AIConfig(
                        api_key=config.get("ai", {}).get("api_key", ""),
                        model=config.get("ai", {}).get("model", "claude-opus-4-6"),
                        max_tokens=config.get("ai", {}).get("max_tokens", 8192)
                    )
                    self.agent_integration = AgentIntegration(ai_config)
                except Exception as e:
                    self.logger.warning(f"[AGENT_SCANNER] 智能体初始化失败: {e}")
                    self._use_fallback_scanning(scan_paths)
                    return

            # 扫描模式
            self.scan_progress.emit("agent_scan", 20, 100)

            if self.agent_mode == AgentMode.HYBRID:
                # 使用智能体快速扫描
                result = self.agent_integration.run_scan_only(scan_paths)
                scan_data = result
            else:
                # 完整智能体扫描
                scan_patterns = self._get_scan_patterns()
                result = self.agent_integration.scan_agent.scan(
                    scan_paths=scan_paths,
                    scan_patterns=scan_patterns
                )
                scan_data = result

            self.scan_progress.emit("converting", 80, 100)

            # 转换为 ScanItem 格式
            self.scan_results = self._convert_to_scan_items(scan_data, scan_paths)

            self.scan_progress.emit("completed", 100, 100)

            elapsed = time.time() - start_time
            self.logger.info(f"[AGENT_SCANNER] 扫描完成: {len(self.scan_results)} 项, "
                           f"耗时: {elapsed:.2f}秒")

            self.is_running = False
            self.complete.emit(self.scan_results)

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"[AGENT_SCANNER] 扫描异常: {e}")
            self.is_running = False
            self.error.emit(f"扫描失败: {str(e)}")

    def _get_scan_paths(self) -> List[str]:
        """获取扫描路径"""
        import os

        if self.scan_type == "custom" and self.scan_target:
            return [self.scan_target]

        paths = []
        if self.scan_type == "system":
            # Windows 系统路径
            paths.extend([
                os.path.expandvars(r"%TEMP%"),
                os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
                r"C:\Windows\Temp"
            ])
        elif self.scan_type == "appdata":
            paths.append(os.path.expandvars(r"%LOCALAPPDATA%"))
        else:
            paths.append(self.scan_target or ".")

        # 过滤有效路径
        valid_paths = [p for p in paths if p and os.path.exists(p)]
        return valid_paths

    def _get_scan_patterns(self) -> List[str]:
        """获取扫描模式"""
        return ["temp_files", "cache_files", "log_files", "system_junk"]

    def _convert_to_scan_items(self, scan_data: Dict, scan_paths: List[str]) -> List[ScanItem]:
        """将智能体扫描结果转换为 ScanItem

        Args:
            scan_data: 智能体扫描数据
            scan_paths: 扫描路径列表

        Returns:
            ScanItem 列表
        """
        items = []
        files = scan_data.get("files", [])

        for i, file_info in enumerate(files):
            path = file_info.get("path", "")
            size = file_info.get("size", 0)
            risk = file_info.get("risk", "suspicious")  # safe, suspicious, dangerous
            category = file_info.get("category", "unknown")

            item = ScanItem(
                path=path,
                size=size,
                item_type='file',  # 扫描的是文件类型
                description=f"{category} - agent_scan",  # 使用 category 作为描述
                risk_level=risk
            )

            # 设置额外字段（ScanItem 有 judgment_method 和 ai_explanation 属性）
            item.judgment_method = 'ai'  # 智能体扫描
            if file_info.get("is_garbage", risk != "dangerous"):
                item.ai_explanation = f"AI判断为垃圾文件，置信度: {file_info.get('confidence', 0.5):.2f}"

            items.append(item)

            # 发射进度信号
            if i % 10 == 0:
                self.progress.emit(i, len(files))
                self.item_found.emit(item)

        return items

    def _use_fallback_scanning(self, scan_paths: List[str]):
        """回退到传统扫描"""
        self.logger.info(f"[AGENT_SCANNER] 使用回退扫描: {len(scan_paths)} 个路径")

        # 导入传统扫描器
        from .scanner import SystemScanner
        from .custom_scanner import CustomScanner

        all_items = []
        for scan_path in scan_paths:
            try:
                if "Temp" in scan_path or scan_path.endswith("Temp"):
                    scanner = SystemScanner()
                else:
                    scanner = CustomScanner(scan_path)

                scanner.scan()
                all_items.extend(scanner.scan_results or [])

                # 发射进度
                for item in scanner.scan_results or []:
                    self.progress.emit(len(all_items), 100)
                    self.item_found.emit(item)

            except Exception as e:
                self.logger.error(f"[AGENT_SCANNER] 回退扫描失败: {scan_path}, {e}")

        self.scan_results = all_items
        self.is_running = False
        self.complete.emit(self.scan_results)

    def cancel(self):
        """取消扫描"""
        self.is_cancelled = True
        self.is_running = False
        self.logger.info("[AGENT_SCANNER] 扫描已取消")

    @property
    def scan_results(self) -> List[ScanItem]:
        """获取扫描结果"""
        return self._scan_results

    @scan_results.setter
    def scan_results(self, value: List[ScanItem]):
        self._scan_results = value


class AgentExecutor(QThread):
    """智能体执行器 - 替代传统执行器

    使用智能体系统执行清理
    """

    execution_completed = pyqtSignal(object)  # ExecutionResult
    execution_failed = pyqtSignal(str, str)   # plan_id, error
    progress = pyqtSignal(int, int)

    def __init__(
        self,
        items: List[CleanupItem],
        is_dry_run: bool = True,
        review_enabled: bool = True
    ):
        super().__init__()
        self.items = items
        self.is_dry_run = is_dry_run
        self.review_enabled = review_enabled

        self.is_running = False
        self.is_cancelled = False
        self.mutex = QMutex()

        self.logger = logger

        # 智能体集成
        self.agent_integration: Optional[AgentIntegration] = None

    def run(self):
        """执行清理"""
        start_time = time.time()

        try:
            self.is_running = True
            self.progress.emit(0, 100)

            self.logger.info(f"[AGENT_EXECUTOR] 开始智能体执行: {len(self.items)} 项, "
                           f"演练模式: {self.is_dry_run}")

            # 转换格式
            cleanup_items = [
                {
                    "path": item.path,
                    "type": "file",
                    "size": item.size
                }
                for item in self.items
            ]

            self.progress.emit(10, 100)

            # 创建智能体集成
            if not self.agent_integration:
                try:
                    config = _get_app_config()
                    ai_config = AIConfig(
                        api_key=config.get("ai", {}).get("api_key", ""),
                        model=config.get("ai", {}).get("model", "claude-opus-4-6")
                    )
                    self.agent_integration = AgentIntegration(ai_config)
                except Exception as e:
                    self.logger.warning(f"[AGENT_EXECUTOR] 智能体初始化失败: {e}")
                    self._use_fallback_execution(cleanup_items)
                    return

            self.progress.emit(30, 100)

            # 执行清理
            result = self.agent_integration.run_cleanup_only(
                cleanup_items=cleanup_items,
                is_dry_run=self.is_dry_run
            )

            self.progress.emit(80, 100)

            # 转换为 ExecutionResult
            execution_result = self._convert_to_execution_result(result)

            self.progress.emit(100, 100)

            elapsed = time.time() - start_time
            self.logger.info(f"[AGENT_EXECUTOR] 执行完成: "
                           f"成功 {result['deleted_count']}, "
                           f"失败 {result['failed_count']}, "
                           f"耗时: {elapsed:.2f}秒")

            self.is_running = False
            self.execution_completed.emit(execution_result)

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"[AGENT_EXECUTOR] 执行异常: {e}")
            self.is_running = False
            self.execution_failed.emit("agent_executor", str(e))

    def _convert_to_execution_result(self, cleanup_result: Dict) -> ExecutionResult:
        """转换为 ExecutionResult

        Args:
            cleanup_result: 清理结果

        Returns:
            ExecutionResult
        """
        plan_id = f"agent_exec_{int(time.time())}"

        # 统计成功/失败
        deleted_list = cleanup_result.get("deleted_files", [])
        failed_list = cleanup_result.get("failed_files", [])

        # 创建 ExecutionResult
        result = ExecutionResult(
            plan_id=plan_id,
            status=ExecutionStatus.COMPLETED,
            start_time=int(time.time()) - 60,
            end_time=int(time.time()),
            total_items=len(self.items),
            deleted_count=len(deleted_list),
            failed_count=len(failed_list),
            freed_bytes=cleanup_result.get("total_freed_bytes", 0),
            errors=[]
        )

        # 添加失败项详情
        for fail in failed_list:
            result.errors.append({
                "path": fail.get("path", ""),
                "error": fail.get("error", "Unknown")
            })

        return result

    def _use_fallback_execution(self, cleanup_items: List[Dict]):
        """回退到传统执行"""
        self.logger.info("[AGENT_EXECUTOR] 使用回退执行")

        from .execution_engine import get_executor

        # 转换回 CleanupItem
        executor = get_executor()

        # 这里需要更多逻辑来完成回退
        # 简化处理
        result = ExecutionResult(
            plan_id="fallback_exec",
            status=ExecutionStatus.FAILED,
            start_time=int(time.time()),
            end_time=int(time.time()),
            total_items=len(self.items),
            deleted_count=0,
            failed_count=len(self.items),
            freed_bytes=0,
            errors=["使用回退执行"]
        )

        self.is_running = False
        self.execution_completed.emit(result)

    def cancel(self):
        """取消执行"""
        self.is_cancelled = True
        self.is_running = False


def get_agent_scanner(
    scan_type: str,
    scan_target: str = "",
    mode: AgentMode = AgentMode.HYBRID
) -> AgentScanner:
    """获取智能体扫描器实例

    Args:
        scan_type: 扫描类型
        scan_target: 扫描目标
        mode: 智能体模式

    Returns:
        AgentScanner 实例
    """
    return AgentScanner(scan_type, scan_target, mode)


def get_agent_executor(
    items: List[CleanupItem],
    is_dry_run: bool = True,
    review_enabled: bool = True
) -> AgentExecutor:
    """获取智能体执行器实例

    Args:
        items: 清理项目列表
        is_dry_run: 是否演练模式
        review_enabled: 是否启用审查

    Returns:
        AgentExecutor 实例
    """
    return AgentExecutor(items, is_dry_run, review_enabled)
