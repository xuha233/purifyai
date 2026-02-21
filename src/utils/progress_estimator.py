"""
扫描进度预估模块 (Progress Estimator)

参考 WinDirStat 的进度显示逻辑，提供智能的扫描进度估算。

功能:
- 剩余时间估算
- 扫描预检查 (权限、磁盘空间、路径存在性)
- 进度报告生成
"""
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import psutil

from utils.logger import get_logger

logger = get_logger(__name__)


class PreCheckStatus(Enum):
    """预检查状态枚举"""
    PASSED = "passed"          # 通过
    WARNING = "warning"        # 警告但不阻止
    FAILED = "failed"          # 失败，阻止扫描


@dataclass
class PreCheckResult:
    """预检查结果数据类

    Attributes:
        status: 检查状态
        message: 结果消息
        details: 详细信息字典
    """
    status: PreCheckStatus
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class ScanProgress:
    """扫描进度数据类

    Attributes:
        current: 当前已完成数量
        total: 总数量
        current_path: 当前扫描路径
        found_items: 发现的清理项数量
        skipped_items: 跳过的项目数量
        start_time: 开始时间戳
        last_update: 上次更新时间戳
    """
    current: int = 0
    total: int = 0
    current_path: str = ""
    found_items: int = 0
    skipped_items: int = 0
    start_time: float = 0.0
    last_update: float = field(default_factory=time.time)

    @property
    def percentage(self) -> float:
        """计算进度百分比

        Returns:
            进度百分比 (0-100)
        """
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100

    @property
    def elapsed_time(self) -> float:
        """计算已用时间（秒）

        Returns:
            已用时间秒数
        """
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    @property
    def estimated_remaining(self) -> float:
        """估算剩余时间（秒）

        使用加权移动平均来平滑估算：
        - 近期速度的权重更高
        - 避免初期波动导致的剧烈变化

        Returns:
            剩余时间秒数
        """
        if self.current == 0 or self.total == 0:
            return 0.0

        elapsed = self.elapsed_time
        if elapsed < 1.0:  # 不足1秒，无法准确估算
            return 0.0

        # 基础速率 (项目/秒)
        base_rate = self.current / elapsed

        if base_rate == 0:
            return 0.0

        # 简单线性估算
        remaining = (self.total - self.current) / base_rate
        return max(0, remaining)

    @property
    def current_rate(self) -> float:
        """当前处理速率（项目/秒）

        基于最近的更新时间计算瞬时速率。

        Returns:
            每秒处理的项目数
        """
        if self.current == 0:
            return 0.0

        elapsed = self.elapsed_time
        if elapsed > 0:
            return self.current / elapsed
        return 0.0

    def update(self, current: int, path: str = ""):
        """更新进度

        Args:
            current: 当前处理数量
            path: 当前路径
        """
        self.current = current
        self.current_path = path
        self.last_update = time.time()

    def to_dict(self) -> Dict:
        """转换为字典

        Returns:
            包含进度信息的字典
        """
        return {
            'current': self.current,
            'total': self.total,
            'percentage': self.percentage,
            'current_path': self.current_path,
            'found_items': self.found_items,
            'skipped_items': self.skipped_items,
            'elapsed_time': self.elapsed_time,
            'estimated_remaining': self.estimated_remaining,
            'current_rate': self.current_rate,
        }


class ProgressEstimator:
    """进度估算器

    提供智能的扫描进度估算和预检查功能。

    使用场景:
    - 扫描前进行权限和磁盘空间检查
    - 扫描过程中实时估算剩余时间
    - 生成进度报告
    """
    # 最小文件数阈值，低于此阈值使用简单估算
    MIN_ITEMS_FOR_ADVANCED_ESTIMATE = 100

    # 预检查最小可用空间 (MB)
    MIN_FREE_SPACE_MB = 100

    def __init__(self):
        """初始化进度估算器"""
        self._progress = ScanProgress()
        self._rate_history: List[float] = []
        self.logger = logger

    def precheck_scan(
        self,
        scan_path: str,
        check_permissions: bool = True,
        check_disk_space: bool = True,
        check_path_exists: bool = True
    ) -> Tuple[bool, List[PreCheckResult]]:
        """扫描预检查

        Args:
            scan_path: 扫描路径
            check_permissions: 是否检查权限
            check_disk_space: 是否检查磁盘空间
            check_path_exists: 是否检查路径存在

        Returns:
            (是否通过, 检查结果列表)
        """
        self.logger.info(f"[PROGRESS] 开始预检查: {scan_path}")
        results: List[PreCheckResult] = []

        # 检查路径是否存在
        if check_path_exists:
            result = self._check_path_exists(scan_path)
            results.append(result)
            if result.status == PreCheckStatus.FAILED:
                return False, results

        # 检查磁盘空间
        if check_disk_space:
            result = self._check_disk_space(scan_path)
            results.append(result)
            if result.status == PreCheckStatus.FAILED:
                return False, results

        # 检查权限
        if check_permissions:
            result = self._check_permissions(scan_path)
            results.append(result)
            if result.status == PreCheckStatus.FAILED:
                return False, results

        # 所有检查通过
        self.logger.info(f"[PROGRESS] 预检查通过: {len(results)} 项检查")
        return True, results

    def _check_path_exists(self, path: str) -> PreCheckResult:
        """检查路径是否存在

        Args:
            path: 路径

        Returns:
            检查结果
        """
        if not os.path.exists(path):
            return PreCheckResult(
                status=PreCheckStatus.FAILED,
                message=f"路径不存在: {path}"
            )

        if not os.path.isdir(path):
            return PreCheckResult(
                status=PreCheckStatus.FAILED,
                message=f"路径不是目录: {path}"
            )

        return PreCheckResult(
            status=PreCheckStatus.PASSED,
            message="路径检查通过",
            details={'path': path, 'type': 'directory'}
        )

    def _check_disk_space(self, path: str) -> PreCheckResult:
        """检查磁盘空间

        Args:
            path: 路径

        Returns:
            检查结果
        """
        try:
            disk = psutil.disk_usage(path)
            free_mb = disk.free / (1024 * 1024)

            if free_mb < self.MIN_FREE_SPACE_MB:
                return PreCheckResult(
                    status=PreCheckStatus.FAILED,
                    message=f"磁盘空间不足 (最少需要 {self.MIN_FREE_SPACE_MB}MB)",
                    details={
                        'free_mb': free_mb,
                        'required_mb': self.MIN_FREE_SPACE_MB
                    }
                )

            return PreCheckResult(
                status=PreCheckStatus.PASSED,
                message=f"磁盘空间充足: {free_mb:.1f}MB 可用",
                details={'free_mb': free_mb, 'total_gb': disk.total / (1024 ** 3)}
            )

        except Exception as e:
            self.logger.error(f"[PROGRESS] 磁盘空间检查失败: {e}")
            return PreCheckResult(
                status=PreCheckStatus.WARNING,
                message=f"无法检查磁盘空间: {str(e)}",
                details={'error': str(e)}
            )

    def _check_permissions(self, path: str) -> PreCheckResult:
        """检查路径权限

        Args:
            path: 路径

        Returns:
            检查结果
        """
        try:
            # 尝试读取目录
            os.listdir(path)
            return PreCheckResult(
                status=PreCheckStatus.PASSED,
                message="权限检查通过"
            )
        except PermissionError:
            return PreCheckResult(
                status=PreCheckStatus.FAILED,
                message=f"无权限访问路径: {path}"
            )
        except Exception as e:
            self.logger.warning(f"[PROGRESS] 权限检查异常: {e}")
            return PreCheckResult(
                status=PreCheckStatus.WARNING,
                message=f"权限检查异常: {str(e)}",
                details={'error': str(e)}
            )

    def start_scan(self, total: int):
        """开始扫描，初始化进度跟踪

        Args:
            total: 预计总数量
        """
        self._progress = ScanProgress(
            total=total,
            start_time=time.time()
        )
        self._rate_history.clear()
        self.logger.info(f"[PROGRESS] 开始扫描，预计 {total} 个项目")

    def update_progress(self, current: int, path: str = ""):
        """更新扫描进度

        Args:
            current: 当前完成数量
            path: 当前处理的路径
        """
        self._progress.update(current, path)

        # 记录当前速率
        if self._progress.elapsed_time > 0:
            current_rate = current / self._progress.elapsed_time
            self._rate_history.append(current_rate)
            # 只保留最近20个速率记录
            if len(self._rate_history) > 20:
                self._rate_history.pop(0)

    def get_progress(self) -> ScanProgress:
        """获取当前进度

        Returns:
            ScanProgress 对象
        """
        return self._progress

    def get_estimated_remaining_time(self) -> float:
        """获取预估剩余时间（秒）

        使用加权平均算法：
        - 越近期的速率权重越高
        - 初期波动较大后期趋于稳定

        Returns:
            剩余时间秒数
        """
        if self._progress.current == 0 or self._progress.total == 0:
            return 0.0

        elapsed = self._progress.elapsed_time
        if elapsed < 1.0:
            return 0.0

        # 如果历史记录足够，使用加权平均
        if len(self._rate_history) >= 5:
            # 权重计算: 越近期的记录权重越高
            weights = list(range(1, len(self._rate_history) + 1))
            total_weight = sum(weights)
            weighted_sum = sum(rate * w for rate, w in zip(self._rate_history, weights))
            avg_rate = weighted_sum / total_weight
        else:
            # 使用当前速率
            avg_rate = self._progress.current_rate

        if avg_rate == 0:
            return 0.0

        remaining = (self._progress.total - self._progress.current) / avg_rate
        return max(0, remaining)

    def get_progress_report(self) -> Dict:
        """获取进度报告

        Returns:
            包含详细进度信息的字典
        """
        progress = self._progress
        remaining = self.get_estimated_remaining_time()

        return {
            'progress': progress.to_dict(),
            'estimated_remaining': remaining,
            'summary': self._generate_summary(progress, remaining)
        }

    def _generate_summary(
        self,
        progress: ScanProgress,
        remaining: float
    ) -> str:
        """生成进度摘要

        Args:
            progress: 进度对象
            remaining: 剩余时间

        Returns:
            摘要文本
        """
        pct = progress.percentage
        elapsed = progress.elapsed_time

        if remaining < 60:
            time_str = f"{int(remaining)} 秒"
        elif remaining < 3600:
            time_str = f"{int(remaining // 60)} 分 {int(remaining % 60)} 秒"
        else:
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            time_str = f"{hours} 小时 {mins} 分钟"

        if elapsed < 60:
            elapsed_str = f"{int(elapsed)} 秒"
        elif elapsed < 3600:
            elapsed_str = f"{int(elapsed // 60)} 分 {int(elapsed % 60)} 秒"
        else:
            hours = int(elapsed // 3600)
            mins = int((elapsed % 3600) // 60)
            elapsed_str = f"{hours} 小时 {mins} 分钟"

        return (f"进度: {pct:.1f}% "
                f"({progress.current}/{progress.total}) "
                f"| 已用时间: {elapsed_str} "
                f"| 预计剩余: {time_str}"
                f"| 发现: {progress.found_items} 项")

    def add_found_item(self):
        """增加发现的项目计数"""
        self._progress.found_items += 1

    def add_skipped_item(self):
        """增加跳过的项目计数"""
        self._progress.skipped_items += 1

    def is_scan_completed(self) -> bool:
        """检查扫描是否完成

        Returns:
            是否完成
        """
        return self._progress.current >= self._progress.total


# 便利函数
def get_progress_estimator() -> ProgressEstimator:
    """获取进度估算器实例

    Returns:
        ProgressEstimator 实例
    """
    return ProgressEstimator()


def format_time(seconds: float) -> str:
    """格式化时间为可读字符串

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串
    """
    if seconds < 60:
        return f"{int(seconds)} 秒"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins} 分 {secs} 秒"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours} 小时 {mins} 分钟"
