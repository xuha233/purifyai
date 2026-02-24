# -*- coding: utf-8 -*-
"""
智能体自动恢复模块

提供异常自动恢复和重试机制
"""
import time
import asyncio
from typing import Callable, Optional, Dict, Any, TypeVar, List
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime

from .exceptions import (
    AgentException, RecoveryStrategy, unwrap_agent_exception,
    is_recoverable, MaxRetriesExceededError, ErrorContext
)
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class RecoveryConfig:
    """恢复配置"""
    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    exponential_backoff: bool = True
    jitter: bool = True
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_sec: int = 60


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    attempts: int = 0
    total_duration_ms: int = 0
    strategy_used: Optional[RecoveryStrategy] = None
    error: Optional[Exception] = None
    fallback_result: Optional[Any] = None


@dataclass
class CircuitBreakerState:
    """熔断器状态"""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False
    opened_at: Optional[datetime] = None


class CircuitBreaker:
    """熔断器 - 防止连续失败

    当失败次数超过阈值时，熔断器打开，暂不再尝试
    """

    def __init__(
        self,
        threshold: int = 5,
        timeout_sec: int = 60,
        name: str = "default"
    ):
        self.threshold = threshold
        self.timeout_sec = timeout_sec
        self.name = name
        self.state = CircuitBreakerState()

    def can_attempt(self) -> bool:
        """检查是否允许尝试"""
        # 检查熔断器是否打开
        if self.state.is_open:
            # 检查是否超时
            if self.state.opened_at:
                elapsed = (datetime.now() - self.state.opened_at).total_seconds()
                if elapsed >= self.timeout_sec:
                    # 熔断器超时，半开状态
                    self.state.is_open = False
                    logger.info(f"[CIRCUIT_BREAKER:{self.name}] 熔断器超时，进入半开状态")
                    return True
            logger.debug(f"[CIRCUIT_BREAKER:{self.name}] 熔断器打开，拒绝请求")
            return False

        return True

    def record_success(self):
        """记录成功"""
        self.state.failure_count = 0
        self.state.is_open = False
        logger.debug(f"[CIRCUIT_BREAKER:{self.name}] 操作成功，重置失败计数")

    def record_failure(self):
        """记录失败"""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.now()

        logger.warning(
            f"[CIRCUIT_BREAKER:{self.name}] 操作失败，失败计数: "
            f"{self.state.failure_count}/{self.threshold}"
        )

        # 达到阈值，打开熔断器
        if self.state.failure_count >= self.threshold:
            self.state.is_open = True
            self.state.opened_at = datetime.now()
            logger.warning(
                f"[CIRCUIT_BREAKER:{self.name}] 达到失败阈值，熔断器已打开"
            )

    def reset(self):
        """重置熔断器"""
        self.state = CircuitBreakerState()
        logger.info(f"[CIRCUIT_BREAKER:{self.name}] 熔断器已重置")


class RecoveryManager:
    """恢复管理器

    提供统一的异常恢复和重试机制
    """

    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recovery_stats: Dict[str, Dict[str, Any]] = {}

    def _get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                threshold=self.config.circuit_breaker_threshold,
                timeout_sec=self.config.circuit_breaker_timeout_sec,
                name=name
            )
        return self.circuit_breakers[name]

    def _get_delay(self, attempt: int, agent_exc: Optional[AgentException] = None) -> int:
        """计算重试延迟（毫秒）"""
        # 首先检查异常是否有自定义延迟
        if agent_exc and hasattr(agent_exc.context, "retry_after_seconds"):
            return agent_exc.context.retry_after_seconds * 1000

        base_delay = self.config.base_delay_ms

        if self.config.exponential_backoff:
            # 指数退避
            delay = base_delay * (2 ** (attempt - 1))
        else:
            # 线性增长
            delay = base_delay * attempt

        # 限制最大延迟
        delay = min(delay, self.config.max_delay_ms)

        # 添加抖动
        if self.config.jitter:
            import random
            delay = int(delay * (0.5 + random.random()))

        return delay

    def execute_with_recovery(
        self,
        func: Callable[[], T],
        name: str = "operation",
        fallback: Optional[Callable[[], T]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """执行函数并提供自动恢复

        Args:
            func: 要执行的函数
            name: 操作名称（用于日志和熔断器标识）
            fallback: 降级函数
            context: 上下文信息

        Returns:
            恢复结果
        """
        result = RecoveryResult(success=False)
        start_time = time.time()

        # 初始化统计
        if name not in self.recovery_stats:
            self.recovery_stats[name] = {
                "total_attempts": 0,
                "success_count": 0,
                "failure_count": 0,
                "recovery_count": 0
            }

        stats = self.recovery_stats[name]

        # 获取熔断器
        circuit_breaker = None
        if self.config.enable_circuit_breaker:
            circuit_breaker = self._get_circuit_breaker(name)

        for attempt in range(1, self.config.max_retries + 1):
            result.attempts = attempt
            stats["total_attempts"] += 1

            # 检查熔断器
            if circuit_breaker and not circuit_breaker.can_attempt():
                logger.warning(f"[RECOVERY:{name}] 熔断器打开，跳过尝试")
                result.error = Exception("熔断器打开，请求被拒绝")
                result.success = False
                return result

            try:
                # 执行函数
                value = func()

                # 成功
                result.success = True
                result.strategy_used = RecoveryStrategy.RETRY if attempt > 1 else None

                if circuit_breaker:
                    circuit_breaker.record_success()

                stats["success_count"] += 1
                if attempt > 1:
                    stats["recovery_count"] += 1

                result.total_duration_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    f"[RECOVERY:{name}] 操作成功 (尝试 {attempt}/{self.config.max_retries})"
                )

                return result

            except Exception as exc:
                # 提取 AgentException
                agent_exc = unwrap_agent_exception(exc)

                # 检查是否可恢复
                if not is_recoverable(exc) and agent_exc:
                    logger.warning(f"[RECOVERY:{name}] 异常不可恢复: {exc}")
                    result.error = exc

                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    stats["failure_count"] += 1
                    return result

                # 记录失败
                if circuit_breaker:
                    circuit_breaker.record_failure()

                stats["failure_count"] += 1
                result.error = exc

                # 如果是最后一次尝试，不再重试
                if attempt >= self.config.max_retries:
                    logger.error(
                        f"[RECOVERY:{name}] 达到最大重试次数 {self.config.max_retries}"
                    )

                    # 尝试降级策略
                    if fallback is not None:
                        logger.info(f"[RECOVERY:{name}] 尝试降级策略")
                        try:
                            fallback_value = fallback()
                            result.success = True
                            result.fallback_result = fallback_value
                            result.strategy_used = RecoveryStrategy.FALLBACK

                            stats["success_count"] += 1
                            stats["recovery_count"] += 1

                            logger.info(f"[RECOVERY:{name}] 降级策略成功")
                            return result
                        except Exception as fallback_exc:
                            logger.error(f"[RECOVERY:{name}] 降级策略失败: {fallback_exc}")

                    # 包装为 MaxRetriesExceededError
                    if agent_exc:
                        raise MaxRetriesExceededError(agent_exc) from exc
                    else:
                        raise MaxRetriesExceededError(
                            AgentException(
                                code=agent_exc.code if agent_exc else None,
                                message=str(exc)
                            )
                        ) from exc

                # 计算延迟
                delay_ms = self._get_delay(attempt, agent_exc)
                delay_sec = delay_ms / 1000.0

                logger.warning(
                    f"[RECOVERY:{name}] 操作失败 (尝试 {attempt}/{self.config.max_retries}), "
                    f"{delay_ms}ms 后重试: {exc}"
                )

                # 等待
                time.sleep(delay_sec)

        # 达到最大重试次数
        result.total_duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def execute_with_recovery_async(
        self,
        func: Callable[[], T],
        name: str = "operation",
        fallback: Optional[Callable[[], T]] = None
    ) -> RecoveryResult:
        """异步执行函数并提供自动恢复"""

        # 对于异步函数，使用 asyncio 包装
        async def wrapper():
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()

        # 使用同步版本处理
        return self.execute_with_recovery(
            lambda: asyncio.run(wrapper()),
            name,
            fallback
        )

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取恢复统计信息"""
        return self.recovery_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.recovery_stats.clear()

    def reset_circuit_breakers(self):
        """重置所有熔断器"""
        for cb in self.circuit_breakers.values():
            cb.reset()


# 全局恢复管理器
_global_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager(config: Optional[RecoveryConfig] = None) -> RecoveryManager:
    """获取全局恢复管理器"""
    global _global_recovery_manager
    if _global_recovery_manager is None or config is not None:
        _global_recovery_manager = RecoveryManager(config)
    return _global_recovery_manager


def with_recovery(
    name: Optional[str] = None,
    fallback: Optional[Callable] = None,
    config: Optional[RecoveryConfig] = None
):
    """装饰器：为函数添加自动恢复功能

    Usage:
        @with_recovery("scan_operation")
        def scan_files(path: str):
            ...

        @with_recovery(fallback=lambda: default_value)
        def risky_operation():
            ...
    """
    def decorator(func):
        recovery_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_recovery_manager(config)

            def execute():
                return func(*args, **kwargs)

            fb_func = None
            if fallback is not None:
                def fb_func():
                    return fallback(*args, **kwargs) if callable(fallback) else fallback

            result = manager.execute_with_recovery(
                execute,
                name=recovery_name,
                fallback=fb_func
            )

            if result.success:
                return result.fallback_result if result.fallback_result is not None else func(*args, **kwargs)

            # 如果没有成功且有错误，重新抛出
            if result.error:
                # 检查已经包装过的错误，避免重复包装
                if not isinstance(result.error, (AgentException, MaxRetriesExceededError)):
                    agent_exc = unwrap_agent_exception(result.error)
                    if agent_exc:
                        raise result.error from agent_exc
                raise result.error

            raise Exception("操作失败且未提供降级策略")

        return wrapper

    return decorator


# ========== 会话恢复策略 ==========

class SessionRecovery:
    """会话恢复策略

    当智能体会话出现异常时，尝试恢复会话状态
    """

    @staticmethod
    def can_recover(exc: AgentException) -> bool:
        """检查异常是否可通过会话恢复"""
        return exc.recovery_strategy in {
            RecoveryStrategy.RESTART_SESSION,
            RecoveryStrategy.RETRY
        }

    @staticmethod
    def prepare_recovery(exc: AgentException) -> Dict[str, Any]:
        """准备恢复信息"""
        recovery_info = {
            "strategy": exc.recovery_strategy.value,
            "max_retries": exc.max_retries,
            "preserve_state": True,
            "retry_after_ms": 0
        }

        # 根据错误类型调整恢复策略
        if exc.context.session_id:
            recovery_info["session_id"] = exc.context.session_id

        # 检查是否有自动重试延迟
        if hasattr(exc.context, "retry_after_seconds"):
            recovery_info["retry_after_ms"] = exc.context.retry_after_seconds * 1000

        return recovery_info
