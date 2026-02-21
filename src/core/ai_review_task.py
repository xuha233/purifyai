"""
AI复核功能模块 - AI复核任务
实现带重试机制的异步AI评估任务
"""
import asyncio
import logging
from typing import List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from core.models import ScanItem
from core.rule_engine import RiskLevel
from core.ai_review_models import (
    AIReviewResult,
    AIReviewStatus,
    ReviewConfig,
    AuditRecord
)
from core.ai_prompt_builder import PromptBuilder
from core.ai_response_parser import ResponseParser


logger = logging.getLogger(__name__)


class AIReviewError(Exception):
    """AI复核异常"""
    def __init__(self, message: str, error_type: str = "unknown"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class RateLimitError(AIReviewError):
    """速率限制异常"""
    pass


class TimeoutError(AIReviewError):
    """超时异常"""
    pass


@dataclass
class AIReviewBatch:
    """AI复核批次"""
    items: List[ScanItem]
    results: dict = None  # path -> AIReviewResult
    status: AIReviewStatus = None

    def __post_init__(self):
        if self.results is None:
            self.results = {}
        if self.status is None:
            self.status = AIReviewStatus(total_items=len(self.items))


class AIReviewWorker(QThread):
    """AI复核工作线程 - UI友好版本"""

    # 信号定义
    progress_updated = pyqtSignal(AIReviewStatus)  # 进度更新
    item_completed = pyqtSignal(str, AIReviewResult)  # 项目完成
    item_failed = pyqtSignal(str, str)  # 项目失败 (path, error)
    batch_completed = pyqtSignal(dict)  # 批次完成 (results)
    batch_failed = pyqtSignal(str)  # 批次失败 (error)

    def __init__(
        self,
        items: List[ScanItem],
        config: Optional[ReviewConfig] = None,
        ai_client=None,
        parent=None
    ):
        """初始化工作线程

        Args:
            items: 待评估的项目列表
            config: 复核配置
            ai_client: AI客户端实例
            parent: 父对象
        """
        super().__init__(parent)
        self.items = items
        self.config = config or ReviewConfig()
        self.ai_client = ai_client
        self.results = {}
        self.is_cancelled = False

        # 创建组件
        self.prompt_builder = PromptBuilder(self.config)
        self.response_parser = ResponseParser(self.config.strict_parse)
        self.batch = AIReviewBatch(items)

    def run(self):
        """运行复核任务"""
        try:
            logger.info(f"开始AI复核，共{len(self.items)}项")
            self._execute_batch()
        except Exception as e:
            logger.exception(f"AI复核批次执行失败: {e}")
            self.batch_failed.emit(str(e))

    def cancel(self):
        """取消复核任务"""
        self.is_cancelled = True

    def _execute_batch(self):
        """执行批次复核"""
        # 更新初始状态
        self.batch.status.start_time = datetime.now()
        self.batch.status.is_in_progress = True
        self.progress_updated.emit(self.batch.status)

        # 按照并发控制执行
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent) as executor:
            futures = [
                executor.submit(self._review_item, item)
                for item in self.items
            ]

            for future, item in zip(futures, self.items):
                if self.is_cancelled:
                    logger.info("任务已取消")
                    break

                try:
                    result = future.result(timeout=self.config.timeout)

                    if result:
                        self.results[item.path] = result
                        self._update_status(result)
                        self.item_completed.emit(item.path, result)
                    else:
                        self.batch.status.failed_count += 1
                        error_msg = f"解析失败，已重试{self.config.max_retries}次"
                        self.item_failed.emit(item.path, error_msg)

                    # 更新进度
                    self.progress_updated.emit(self.batch.status)

                except Exception as e:
                    logger.error(f"评估项 {item.path} 失败: {e}")
                    self.batch.status.failed_count += 1
                    self.item_failed.emit(item.path, str(e))
                    self.progress_updated.emit(self.batch.status)

        # 完成批次
        self.batch.status.is_in_progress = False
        self.batch.status.end_time = datetime.now()
        self.progress_updated.emit(self.batch.status)
        self.batch_completed.emit(self.results)

        logger.info(f"AI复核完成: 成功{self.batch.status.success_count}，"
                   f"失败{self.batch.status.failed_count}")

    def _review_item(self, item: ScanItem) -> Optional[AIReviewResult]:
        """评估单个项目

        Args:
            item: 扫描项

        Returns:
            AIReviewResult或None
        """
        original_risk = item.risk_level if hasattr(item, 'risk_level') else None

        for attempt in range(self.config.max_retries):
            if self.is_cancelled:
                return None

            # 更新当前项
            self.batch.status.current_item = item.path

            try:
                # 构建提示词
                if attempt == 0:
                    prompt = self.prompt_builder.build_assessment_prompt(item)
                else:
                    # 重试使用简化提示词
                    prompt = self.prompt_builder.build_retry_prompt(
                        item,
                        "format" if attempt < 2 else "timeout"
                    )

                # 调用AI
                success, response = self._call_ai(prompt)

                if not success:
                    raise AIReviewError(response, "api_error")

                # 解析响应
                result = self.response_parser.parse(
                    response,
                    item.path,
                    original_risk
                )

                if result:
                    result.retry_count = attempt
                    return result
                else:
                    # 首次解析失败，重试
                    logger.debug(f"解析失败，重试 {attempt + 1}/{self.config.max_retries}")
                    continue

            except RateLimitError:
                # 限流错误，指数退避
                delay = self.config.retry_delay * (2 ** attempt)
                logger.warning(f"速率限制，等待 {delay}秒 后重试")
                import time
                time.sleep(delay)

            except TimeoutError:
                logger.warning(f"超时，重试 {attempt + 1}/{self.config.max_retries}")

            except AIReviewError as e:
                logger.error(f"AI复核错误: {e.message}")

                # 最后一次重试失败，返回默认结果
                if attempt == self.config.max_retries - 1:
                    return self._get_default_result(item, str(e))

        return None

    def _call_ai(self, prompt: str) -> tuple[bool, str]:
        """调用AI API

        Args:
            prompt: 提示词

        Returns:
            (success, response) 成功标志和响应内容
        """
        if not self.ai_client:
            raise AIReviewError("AI客户端未初始化")

        messages = [{'role': 'user', 'content': prompt}]

        try:
            success, response = self.ai_client.chat(messages)
            return success, response

        except Exception as e:
            error_msg = str(e).lower()

            if 'rate limit' in error_msg or 'too many requests' in error_msg:
                raise RateLimitError("API速率限制")
            elif 'timeout' in error_msg:
                raise TimeoutError("请求超时")
            else:
                raise AIReviewError(f"AI调用失败: {str(e)}", "api_error")

    def _update_status(self, result: AIReviewResult):
        """更新复核状态

        Args:
            result: AI复核结果
        """
        self.batch.status.reviewed_items += 1
        self.batch.status.success_count += 1

        # 更新分类数量
        if result.ai_risk == RiskLevel.SAFE:
            self.batch.status.safe_count += 1
        elif result.ai_risk == RiskLevel.DANGEROUS:
            self.batch.status.dangerous_count += 1
        else:
            self.batch.status.suspicious_count += 1

    def _get_default_result(self, item: ScanItem, error: str) -> AIReviewResult:
        """获取默认复核结果（所有重试失败时）

        Args:
            item: 扫描项
            error: 错误信息

        Returns:
            默认的AIReviewResult
        """
        return AIReviewResult(
            item_path=item.path,
            original_risk=item.risk_level,
            ai_risk=RiskLevel.SUSPICIOUS,
            confidence=0.1,
            function_description="评估失败",
            software_name="未知",
            risk_reason=f"AI评估失败: {error}",
            cleanup_suggestion="建议人工确认",
            ai_reasoning=f"API调用或解析失败，共尝试{self.config.max_retries}次",
            review_timestamp=datetime.now(),
            retry_count=self.config.max_retries,
            is_valid=False,
            parse_method="default"
        )


class AIReviewOrchestrator:
    """AI复核编排器 - 管理复核任务的执行"""

    def __init__(
        self,
        config: Optional[ReviewConfig] = None,
        ai_client=None,
        parent=None
    ):
        """初始化编排器

        Args:
            config: 复核配置
            ai_client: AI客户端
            parent: 父对象
        """
        self.config = config or ReviewConfig()
        self.ai_client = ai_client
        self.parent = parent
        self.current_worker: Optional[AIReviewWorker] = None

    def start_review(
        self,
        items: List[ScanItem],
        on_progress: Callable[[AIReviewStatus], None] = None,
        on_item_completed: Callable[[str, AIReviewResult], None] = None,
        on_item_failed: Callable[[str, str], None] = None,
        on_complete: Callable[[dict], None] = None
    ) -> AIReviewWorker:
        """开始复核任务

        Args:
            items: 待评估的项目列表
            on_progress: 进度回调
            on_item_completed: 项目完成回调
            on_item_failed: 项目失败回调
            on_complete: 完成回调

        Returns:
            AIReviewWorker实例
        """
        worker = AIReviewWorker(items, self.config, self.ai_client, self.parent)

        # 连接信号
        if on_progress:
            worker.progress_updated.connect(on_progress)
        if on_item_completed:
            worker.item_completed.connect(on_item_completed)
        if on_item_failed:
            worker.item_failed.connect(on_item_failed)
        if on_complete:
            worker.batch_completed.connect(on_complete)

        self.current_worker = worker
        worker.start()

        return worker

    def cancel_review(self):
        """取消当前复核任务"""
        if self.current_worker and not self.current_worker.isFinished():
            self.current_worker.cancel()
            self.current_worker.wait()
        self.current_worker = None

    def is_busy(self) -> bool:
        """检查是否正在工作

        Returns:
            bool: 是否忙碌
        """
        return (
            self.current_worker is not None and
            not self.current_worker.isFinished()
        )


# 便捷函数
async def review_single_item(
    item: ScanItem,
    ai_client,
    config: Optional[ReviewConfig] = None
) -> Optional[AIReviewResult]:
    """评估单个项目（异步版本）

    Args:
        item: 扫描项
        ai_client: AI客户端
        config: 配置

    Returns:
        AIReviewResult或None
    """
    review_config = config or ReviewConfig()

    prompt_builder = PromptBuilder(review_config)
    response_parser = ResponseParser(review_config.strict_parse)

    messages = [{
        'role': 'user',
        'content': prompt_builder.build_assessment_prompt(item)
    }]

    # 调用AI
    success, response = ai_client.chat(messages)

    if not success:
        logger.error(f"AI调用失败: {response}")
        return None

    # 解析响应
    result = response_parser.parse(response, item.path, item.risk_level)

    if not result:
        # 重试
        retry_prompt = prompt_builder.build_retry_prompt(item)
        messages = [{'role': 'user', 'content': retry_prompt}]
        success, response = ai_client.chat(messages)
        if success:
            result = response_parser.parse(response, item.path, item.risk_level)

    return result
