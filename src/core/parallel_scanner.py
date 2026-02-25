"""
Parallel Scanner Module
Multi-threaded scanning for improved performance
"""
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional, List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import multiprocessing

from .models import ScanItem
from .scanner import SystemScanner, ScanRiskAssessor
from .rule_engine import RiskLevel
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScanProgress:
    """扫描进度信息"""
    total_paths: int = 0
    completed_paths: int = 0
    current_path: str = ''
    total_size: int = 0
    total_files: int = 0
    start_time: float = field(default_factory=time.time)
    errors: List[str] = field(default_factory=list)

    @property
    def elapsed_seconds(self) -> float:
        """已用时间（秒）"""
        return time.time() - self.start_time

    @property
    def speed_mb_per_sec(self) -> float:
        """扫描速度 MB/s"""
        if self.elapsed_seconds == 0:
            return 0
        return (self.total_size / 1024 / 1024) / self.elapsed_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_paths': self.total_paths,
            'completed_paths': self.completed_paths,
            'current_path': self.current_path,
            'total_size': self.total_size,
            'total_files': self.total_files,
            'elapsed_seconds': round(self.elapsed_seconds, 2),
            'speed_mb_per_sec': round(self.speed_mb_per_sec, 2),
            'errors_count': len(self.errors)
        }


class ParallelScanner:
    """多线程并行扫描器

    使用 ThreadPoolExecutor 并行扫描多个路径，显著提升扫描速度。

    Features:
    - 自动检测最优线程数（基于CPU核心数）
    - 支持进度回调
    - 线程安全的结果收集
    - 取消支持
    """

    # 默认配置
    DEFAULT_MAX_WORKERS = None  # None = CPU核心数
    MIN_WORKERS = 1
    MAX_WORKERS_LIMIT = 32  # 最大线程数限制

    def __init__(self, max_workers: Optional[int] = None,
                 use_ai_evaluation: bool = False):
        """初始化并行扫描器

        Args:
            max_workers: 最大工作线程数，None表示自动检测
            use_ai_evaluation: 是否使用AI风险评估
        """
        self._max_workers = max_workers
        self._use_ai_evaluation = use_ai_evaluation
        self._is_running = False
        self._is_cancelled = False
        self._lock = threading.Lock()
        self._progress = ScanProgress()

        # 风险评估器
        self._risk_assessor = ScanRiskAssessor(use_ai_evaluation=use_ai_evaluation)

        logger.info(f"[ParallelScanner] 初始化完成, max_workers={self._max_workers}")

    @staticmethod
    def get_optimal_thread_count() -> int:
        """获取最优线程数

        基于CPU核心数计算，I/O密集型任务可以设置更多线程。

        Returns:
            推荐的线程数
        """
        cpu_count = multiprocessing.cpu_count()
        # I/O密集型任务，线程数可以是CPU核心数的2-4倍
        optimal = min(cpu_count * 2, ParallelScanner.MAX_WORKERS_LIMIT)
        return max(optimal, ParallelScanner.MIN_WORKERS)

    def set_thread_count(self, count: int) -> None:
        """设置线程数

        Args:
            count: 线程数，必须在有效范围内
        """
        if count < self.MIN_WORKERS:
            logger.warning(f"[ParallelScanner] 线程数 {count} 小于最小值 {self.MIN_WORKERS}，使用最小值")
            self._max_workers = self.MIN_WORKERS
        elif count > self.MAX_WORKERS_LIMIT:
            logger.warning(f"[ParallelScanner] 线程数 {count} 大于最大值 {self.MAX_WORKERS_LIMIT}，使用最大值")
            self._max_workers = self.MAX_WORKERS_LIMIT
        else:
            self._max_workers = count
        logger.info(f"[ParallelScanner] 设置线程数为 {self._max_workers}")

    def get_thread_count(self) -> int:
        """获取当前线程数配置

        Returns:
            当前配置的线程数
        """
        if self._max_workers is None:
            return self.get_optimal_thread_count()
        return self._max_workers

    def set_ai_enabled(self, enabled: bool) -> None:
        """启用或禁用AI评估

        Args:
            enabled: True启用，False禁用
        """
        self._use_ai_evaluation = enabled
        self._risk_assessor.set_ai_enabled(enabled)

    def scan_parallel(self,
                      paths: List[str],
                      progress_callback: Optional[Callable[[ScanProgress], None]] = None,
                      item_callback: Optional[Callable[[ScanItem], None]] = None,
                      max_workers: Optional[int] = None) -> List[ScanItem]:
        """并行扫描多个路径

        Args:
            paths: 要扫描的路径列表
            progress_callback: 进度回调函数
            item_callback: 发现项目时的回调函数
            max_workers: 本次扫描使用的线程数，None使用实例配置

        Returns:
            所有扫描结果列表
        """
        if self._is_running:
            logger.warning("[ParallelScanner] 扫描已在运行中")
            return []

        self._is_running = True
        self._is_cancelled = False
        self._progress = ScanProgress(total_paths=len(paths))
        results: List[ScanItem] = []

        # 确定工作线程数
        workers = max_workers or self._max_workers or self.get_optimal_thread_count()
        logger.info(f"[ParallelScanner] 开始并行扫描 {len(paths)} 个路径, 线程数: {workers}")

        start_time = time.time()

        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                # 提交所有扫描任务
                future_to_path = {}
                for path in paths:
                    if self._is_cancelled:
                        break
                    future = executor.submit(self._scan_single_path, path, item_callback)
                    future_to_path[future] = path

                # 收集结果
                for future in as_completed(future_to_path):
                    if self._is_cancelled:
                        break

                    path = future_to_path[future]
                    try:
                        path_results = future.result()
                        with self._lock:
                            results.extend(path_results)
                            self._progress.completed_paths += 1
                            self._progress.current_path = path

                        # 进度回调
                        if progress_callback:
                            progress_callback(self._progress)

                    except Exception as e:
                        logger.error(f"[ParallelScanner] 扫描路径失败 {path}: {e}")
                        with self._lock:
                            self._progress.errors.append(f"{path}: {str(e)}")

        except Exception as e:
            logger.error(f"[ParallelScanner] 并行扫描异常: {e}")
        finally:
            self._is_running = False

        duration = time.time() - start_time
        total_size = sum(item.size for item in results)
        logger.info(f"[ParallelScanner] 扫描完成: {len(results)} 项目, "
                   f"{total_size/1024/1024:.2f}MB, 耗时 {duration:.2f}秒")

        return results

    def _scan_single_path(self, path: str,
                          item_callback: Optional[Callable[[ScanItem], None]] = None) -> List[ScanItem]:
        """扫描单个路径

        Args:
            path: 要扫描的路径
            item_callback: 发现项目时的回调

        Returns:
            该路径的扫描结果
        """
        results: List[ScanItem] = []

        if self._is_cancelled:
            return results

        if not os.path.exists(path):
            logger.warning(f"[ParallelScanner] 路径不存在: {path}")
            return results

        try:
            # 计算目录大小
            size = SystemScanner._get_directory_size(
                path,
                cancel_flag=lambda: self._is_cancelled
            )

            if self._is_cancelled:
                return results

            # 风险评估
            risk_level, description = self._risk_assessor.assess(
                path=path,
                description=self._get_path_description(path),
                size=size,
                item_type='directory'
            )

            # 创建扫描项
            item = ScanItem(
                path=path,
                size=size,
                item_type='directory',
                description=description,
                risk_level=risk_level
            )
            results.append(item)

            # 更新进度
            with self._lock:
                self._progress.total_size += size
                self._progress.total_files += 1

            # 回调
            if item_callback:
                item_callback(item)

        except PermissionError:
            logger.warning(f"[ParallelScanner] 无权限访问: {path}")
        except Exception as e:
            logger.error(f"[ParallelScanner] 扫描异常 {path}: {e}")

        return results

    def _get_path_description(self, path: str) -> str:
        """获取路径的描述

        Args:
            path: 路径

        Returns:
            描述字符串
        """
        path_lower = path.lower()

        # 常见路径描述映射
        descriptions = {
            'temp': '临时文件',
            'cache': '缓存文件',
            'log': '日志文件',
            'download': '下载文件',
            'recycle': '回收站',
            'thumbs': '缩略图缓存',
            'prefetch': '预读取文件',
            'crash': '崩溃报告',
            'backup': '备份文件',
            'old': '旧版本文件',
        }

        for key, desc in descriptions.items():
            if key in path_lower:
                return desc

        return Path(path).name or path

    def cancel(self) -> None:
        """取消当前扫描"""
        logger.info("[ParallelScanner] 取消扫描")
        self._is_cancelled = True

    def is_running(self) -> bool:
        """检查是否正在扫描

        Returns:
            True表示正在扫描
        """
        return self._is_running

    def get_progress(self) -> ScanProgress:
        """获取当前进度

        Returns:
            当前进度信息
        """
        return self._progress


class ParallelScannerManager:
    """并行扫描管理器

    单例模式，管理全局扫描器实例
    """
    _instance: Optional['ParallelScannerManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._scanner = None
        return cls._instance

    def get_scanner(self, max_workers: Optional[int] = None,
                    use_ai_evaluation: bool = False) -> ParallelScanner:
        """获取扫描器实例

        Args:
            max_workers: 最大线程数
            use_ai_evaluation: 是否使用AI评估

        Returns:
            ParallelScanner 实例
        """
        if self._scanner is None:
            self._scanner = ParallelScanner(
                max_workers=max_workers,
                use_ai_evaluation=use_ai_evaluation
            )
        return self._scanner

    def reset_scanner(self) -> None:
        """重置扫描器"""
        self._scanner = None


def get_parallel_scanner(max_workers: Optional[int] = None,
                         use_ai_evaluation: bool = False) -> ParallelScanner:
    """获取并行扫描器实例

    Args:
        max_workers: 最大线程数
        use_ai_evaluation: 是否使用AI评估

    Returns:
        ParallelScanner 实例
    """
    return ParallelScannerManager().get_scanner(max_workers, use_ai_evaluation)
