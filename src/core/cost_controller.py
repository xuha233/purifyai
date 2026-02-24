"""
AI 成本控制器 (AI Cost Controller)

提供全面的 AI API 成本控制功能：
1. 调用次数限制
2. 预算限制（USD）
3. 自动降级到规则引擎
4. 实时成本跟踪

成本计算（基于 OpenAI/GPT 定价，GLM 类似）：
- Input: $0.01 / 1M tokens
- Output: $0.03 / 1M tokens
- 每次调用约 1000 tokens 输入 + 500 tokens 输出 = $0.025 / 次
"""
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import os

from ..utils.logger import get_logger

logger = get_logger(__name__)


class CostControlMode(Enum):
    """成本控制模式"""
    UNLIMITED = "unlimited"        # 无限制 - 全部使用 AI
    BUDGET = "budget"              # 预算模式 - 限制调用次数和金额
    FALLBACK = "fallback"          # 回退模式 - 超限降级到规则引擎
    RULES_ONLY = "rules_only"      # 仅规则 - 不调用 AI


class BudgetAlertLevel(Enum):
    """预算警告级别"""
    NORMAL = "normal"      # 正常
    WARNING = "warning"    # 警告（达到 80%）
    CRITICAL = "critical"  # 严重（达到 100%）
    EXCEEDED = "exceeded"  # 已超出


@dataclass
class CostStats:
    """成本统计"""
    session_start: datetime = field(default_factory=datetime.now)
    total_calls: int = 0
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    calls_in_current_period: int = 0
    cost_in_current_period: float = 0.0

    def reset_period(self):
        """重置周期统计"""
        self.calls_in_current_period = 0
        self.cost_in_current_period = 0.0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "session_start": self.session_start.isoformat(),
            "total_calls": self.total_calls,
            "total_cost": round(self.total_cost, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "calls_in_current_period": self.calls_in_current_period,
            "cost_in_current_period": round(self.cost_in_current_period, 4)
        }


@dataclass
class CostConfig:
    """成本控制配置"""
    # 调用次数限制
    max_calls_per_scan: int = 100          # 单次扫描最大调用次数
    max_calls_per_day: int = 1000          # 每日最大调用次数
    max_calls_per_month: int = 10000       # 每月最大调用次数

    # 预算限制（USD）
    max_budget_per_scan: float = 2.0       # 单次扫描最大预算 ($2.00)
    max_budget_per_day: float = 10.0       # 每日最大预算 ($10.00)
    max_budget_per_month: float = 50.0    # 每月最大预算 ($50.00)

    # 成本率（USD per token，基于 GLM-4-Flash 定价）
    input_cost_per_million: float = 0.14   # $0.14 / 1M input tokens
    output_cost_per_million: float = 0.28  # $0.28 / 1M output tokens

    # 降级设置
    fallback_to_rules: bool = True         # 超限降级到规则引擎
    alert_threshold: float = 0.8           # 警告阈值（达到预算的 80%）

    # 模式
    mode: CostControlMode = CostControlMode.FALLBACK

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "max_calls_per_scan": self.max_calls_per_scan,
            "max_calls_per_day": self.max_calls_per_day,
            "max_calls_per_month": self.max_calls_per_month,
            "max_budget_per_scan": self.max_budget_per_scan,
            "max_budget_per_day": self.max_budget_per_day,
            "max_budget_per_month": self.max_budget_per_month,
            "input_cost_per_million": self.input_cost_per_million,
            "output_cost_per_million": self.output_cost_per_million,
            "fallback_to_rules": self.fallback_to_rules,
            "alert_threshold": self.alert_threshold,
            "mode": self.mode.value
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CostConfig":
        """从字典创建配置"""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                if key == "mode" and isinstance(value, str):
                    setattr(config, key, CostControlMode(value))
                else:
                    setattr(config, key, value)
        return config


class CostController:
    """AI 成本控制器

    功能：
    1. 跟踪 AI 调用次数和成本
    2. 执行调用次数和预算限制
    3. 达到限制时自动降级
    4. 提供实时成本统计
    """

    def __init__(self, config: Optional[CostConfig] = None, config_file: Optional[str] = None):
        """初始化成本控制器

        Args:
            config: 成本配置
            config_file: 配置文件路径（用于持久化）
        """
        self.config = config or CostConfig()
        self.config_file = config_file

        # 统计信息
        self.stats = CostStats()
        self._daily_stats: Dict[str, CostStats] = {}  # 按日期存储的统计
        self._monthly_stats: Dict[str, CostStats] = {}  # 按月份存储的统计

        # 回调函数
        self._on_limit_reached: Optional[Callable] = None
        self._on_alert: Optional[Callable[[BudgetAlertLevel, str], None]] = None
        self._on_stats_update: Optional[Callable[[CostStats], None]] = None

        # 状态
        self._is_degraded = False
        self._degradation_reason = ""
        self._current_alert_level = BudgetAlertLevel.NORMAL

        # 加载持久化数据
        self._load_stats()

        self.logger = logger

    def can_make_call(self, estimated_cost: float = 0.025) -> tuple[bool, str]:
        """检查是否可以发起 AI 调用

        Args:
            estimated_cost: 预估成本（默认 $0.025 / 次）

        Returns:
            (是否可以调用, 原因)
        """
        # 检查模式
        if self.config.mode == CostControlMode.RULES_ONLY:
            return False, "规则模式：已禁用 AI 调用"

        if self.config.mode == CostControlMode.UNLIMITED:
            return True, "无限制模式"

        # 检查单次扫描限制
        if (self.config.max_calls_per_scan > 0 and
            self.stats.calls_in_current_period >= self.config.max_calls_per_scan):
            return False, f"达到单次扫描调用限制 ({self.config.max_calls_per_scan})"

        if (self.config.max_budget_per_scan > 0 and
            self.stats.cost_in_current_period >= self.config.max_budget_per_scan):
            return False, f"达到单次扫描预算限制 (${self.config.max_budget_per_scan:.2f})"

        # 检查每日限制
        daily_key = datetime.now().strftime("%Y-%m-%d")
        daily_stats = self._daily_stats.get(daily_key, CostStats())
        if (self.config.max_calls_per_day > 0 and
            daily_stats.calls_in_current_period >= self.config.max_calls_per_day):
            return False, f"达到每日调用限制 ({self.config.max_calls_per_day})"

        if (self.config.max_budget_per_day > 0 and
            daily_stats.cost_in_current_period >= self.config.max_budget_per_day):
            return False, f"达到每日预算限制 (${self.config.max_budget_per_day:.2f})"

        # 预估成本检查
        if (self.config.max_budget_per_scan > 0 and
            self.stats.cost_in_current_period + estimated_cost > self.config.max_budget_per_scan):
            return False, f"预估成本超出扫描预算"

        return True, "可以调用"

    def record_call(
        self,
        input_tokens: int = 1000,
        output_tokens: int = 500,
        cost: Optional[float] = None
    ) -> Dict:
        """记录一次 AI 调用

        Args:
            input_tokens: 输入 tokens
            output_tokens: 输出 tokens
            cost: 实际成本（如果未提供则自动计算）

        Returns:
            调用统计信息
        """
        # 计算成本
        if cost is None:
            cost = self._calculate_cost(input_tokens, output_tokens)

        # 更新统计
        self.stats.total_calls += 1
        self.stats.total_cost += cost
        self.stats.total_input_tokens += input_tokens
        self.stats.total_output_tokens += output_tokens
        self.stats.calls_in_current_period += 1
        self.stats.cost_in_current_period += cost

        # 更新每日统计
        daily_key = datetime.now().strftime("%Y-%m-%d")
        if daily_key not in self._daily_stats:
            self._daily_stats[daily_key] = CostStats()
        self._daily_stats[daily_key].total_calls += 1
        self._daily_stats[daily_key].total_cost += cost
        self._daily_stats[daily_key].calls_in_current_period += 1
        self._daily_stats[daily_key].cost_in_current_period += cost

        # 更新每月统计
        monthly_key = datetime.now().strftime("%Y-%m")
        if monthly_key not in self._monthly_stats:
            self._monthly_stats[monthly_key] = CostStats()
        self._monthly_stats[monthly_key].total_calls += 1
        self._monthly_stats[monthly_key].total_cost += cost
        self._monthly_stats[monthly_key].calls_in_current_period += 1
        self._monthly_stats[monthly_key].cost_in_current_period += cost

        # 检查是否达到限制并触发降级
        self._check_limits()

        # 触发统计更新回调
        if self._on_stats_update:
            self._on_stats_update(self.stats)

        # 保存统计
        self._save_stats()

        return {
            "call_count": self.stats.calls_in_current_period,
            "total_cost": self.stats.total_cost,
            "period_cost": self.stats.cost_in_current_period,
            "is_degraded": self._is_degraded
        }

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """计算成本

        Args:
            input_tokens: 输入 tokens
            output_tokens: 输出 tokens

        Returns:
            成本（USD）
        """
        input_cost = (input_tokens / 1_000_000) * self.config.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.config.output_cost_per_million
        return input_cost + output_cost

    def _check_limits(self):
        """检查是否达到限制"""
        # 检查扫描调用次数限制
        if (self.config.max_calls_per_scan > 0 and
            self.stats.calls_in_current_period >= self.config.max_calls_per_scan):
            self._trigger_degradation(f"达到调用次数限制 ({self.config.max_calls_per_scan})")
            return

        # 检查扫描预算限制
        if (self.config.max_budget_per_scan > 0 and
            self.stats.cost_in_current_period >= self.config.max_budget_per_scan):
            self._trigger_degradation(f"达到预算限制 (${self.config.max_budget_per_scan:.2f})")
            return

        # 检查每日预算限制
        daily_key = datetime.now().strftime("%Y-%m-%d")
        daily_stats = self._daily_stats.get(daily_key, CostStats())
        if (self.config.max_budget_per_day > 0 and
            daily_stats.cost_in_current_period >= self.config.max_budget_per_day):
            self._trigger_degradation(f"达到每日预算限制 (${self.config.max_budget_per_day:.2f})")
            return

        # 检查预算警告阈值
        if self.config.max_budget_per_scan > 0:
            budget_usage = self.stats.cost_in_current_period / self.config.max_budget_per_scan
            if budget_usage >= 1.0:
                self._update_alert_level(BudgetAlertLevel.EXCEEDED)
            elif budget_usage >= self.config.alert_threshold:
                self._update_alert_level(BudgetAlertLevel.WARNING)
            else:
                self._update_alert_level(BudgetAlertLevel.NORMAL)

    def _trigger_degradation(self, reason: str):
        """触发降级

        Args:
            reason: 降级原因
        """
        if not self._is_degraded:
            self._is_degraded = True
            self._degradation_reason = reason
            self.logger.warning(f"[COST_CONTROLLER] 降级到规则引擎: {reason}")

            if self._on_limit_reached:
                self._on_limit_reached(reason)

    def _update_alert_level(self, level: BudgetAlertLevel):
        """更新警告级别

        Args:
            level: 新的警告级别
        """
        if level != self._current_alert_level:
            old_level = self._current_alert_level
            self._current_alert_level = level

            message = self._get_alert_message(level)
            self.logger.info(f"[COST_CONTROLLER] 预算警告: {old_level.value} -> {level.value}")

            if self._on_alert:
                self._on_alert(level, message)

    def _get_alert_message(self, level: BudgetAlertLevel) -> str:
        """获取警告消息

        Args:
            level: 警告级别

        Returns:
            警告消息
        """
        if self.config.max_budget_per_scan <= 0:
            return ""

        usage = (self.stats.cost_in_current_period / self.config.max_budget_per_scan) * 100

        if level == BudgetAlertLevel.NORMAL:
            return f"正常: 已使用 ${self.stats.cost_in_current_period:.2f}"

        elif level == BudgetAlertLevel.WARNING:
            return f"警告: 已使用 {usage:.0f}% 预算 (${self.stats.cost_in_current_period:.2f}/${self.config.max_budget_per_scan:.2f})"

        elif level == BudgetAlertLevel.CRITICAL:
            return f"严重: 已使用 {usage:.0f}% 预算"

        elif level == BudgetAlertLevel.EXCEEDED:
            return f"已超出预算限制!"

        return ""

    def reset_scan_stats(self):
        """重置当前扫描统计"""
        self.stats.calls_in_current_period = 0
        self.stats.cost_in_current_period = 0
        self._is_degraded = False
        self._degradation_reason = ""
        self._current_alert_level = BudgetAlertLevel.NORMAL
        self.logger.info("[COST_CONTROLLER] 扫描统计已重置")

    def reset_daily_stats(self):
        """重置每日统计"""
        self._daily_stats.clear()
        self.logger.info("[COST_CONTROLLER] 每日统计已重置")

    def get_stats(self) -> CostStats:
        """获取统计信息"""
        return self.stats

    def get_daily_stats(self, date: Optional[datetime] = None) -> CostStats:
        """获取指定日期的统计

        Args:
            date: 日期（默认今天）

        Returns:
            统计信息
        """
        date_key = (date or datetime.now()).strftime("%Y-%m-%d")
        return self._daily_stats.get(date_key, CostStats())

    def get_monthly_stats(self, month: Optional[datetime] = None) -> CostStats:
        """获取指定月份的统计

        Args:
            month: 月份（默认当前月）

        Returns:
            统计信息
        """
        monthly_key = (month or datetime.now()).strftime("%Y-%m")
        return self._monthly_stats.get(monthly_key, CostStats())

    def get_usage_report(self) -> Dict:
        """获取使用报告

        Returns:
            使用报告字典
        """
        daily_stats = self.get_daily_stats()
        monthly_stats = self.get_monthly_stats()

        # 计算使用率
        call_usage = 0.0
        budget_usage = 0.0

        if self.config.max_calls_per_scan > 0:
            call_usage = (self.stats.calls_in_current_period / self.config.max_calls_per_scan) * 100

        if self.config.max_budget_per_scan > 0:
            budget_usage = (self.stats.cost_in_current_period / self.config.max_budget_per_scan) * 100

        return {
            "current_scan": {
                "calls": self.stats.calls_in_current_period,
                "max_calls": self.config.max_calls_per_scan,
                "cost": round(self.stats.cost_in_current_period, 4),
                "max_budget": self.config.max_budget_per_scan,
                "call_usage_percent": round(call_usage, 1),
                "budget_usage_percent": round(budget_usage, 1)
            },
            "today": {
                "calls": daily_stats.calls_in_current_period,
                "max_calls": self.config.max_calls_per_day,
                "cost": round(daily_stats.cost_in_current_period, 4),
                "max_budget": self.config.max_budget_per_day
            },
            "this_month": {
                "calls": monthly_stats.total_calls,
                "max_calls": self.config.max_calls_per_month,
                "cost": round(monthly_stats.total_cost, 4),
                "max_budget": self.config.max_budget_per_month
            },
            "all_time": {
                "calls": self.stats.total_calls,
                "cost": round(self.stats.total_cost, 4)
            },
            "alert_level": self._current_alert_level.value,
            "is_degraded": self._is_degraded,
            "degradation_reason": self._degradation_reason
        }

    def get_summary_text(self) -> str:
        """获取摘要文本（用于UI显示）"""
        report = self.get_usage_report()
        scan = report["current_scan"]

        if self._is_degraded:
            status = f"[已降级] {self._degradation_reason}"
        elif self._current_alert_level == BudgetAlertLevel.WARNING:
            status = f"[警告] 已使用 {scan['budget_usage_percent']:.0f}% 预算"
        elif self._current_alert_level == BudgetAlertLevel.CRITICAL:
            status = f"[严重] 已使用 {scan['budget_usage_percent']:.0f}% 预算"
        else:
            status = "正常"

        return (
            f"{status} | "
            f"调用: {scan['calls']}/{scan['max_calls']} | "
            f"成本: ${scan['cost']:.3f}/${scan['max_budget']:.2f}"
        )

    def set_on_limit_reached(self, callback: Callable[[str], None]):
        """设置达到限制时的回调

        Args:
            callback: 回调函数，接收原因字符串
        """
        self._on_limit_reached = callback

    def set_on_alert(self, callback: Callable[[BudgetAlertLevel, str], None]):
        """设置预算警告回调

        Args:
            callback: 回调函数，接收（警告级别，消息）
        """
        self._on_alert = callback

    def set_on_stats_update(self, callback: Callable[[CostStats], None]):
        """设置统计更新回调

        Args:
            callback: 回调函数，接收统计信息
        """
        self._on_stats_update = callback

    def update_config(self, config: CostConfig):
        """更新配置

        Args:
            config: 新的成本配置
        """
        self.config = config
        self.logger.info(f"[COST_CONTROLLER] 配置已更新: mode={config.mode.value}")

    def _get_stats_file(self) -> str:
        """获取统计文件路径"""
        if self.config_file:
            return self.config_file.replace(".json", "_stats.json")
        return "cost_stats.json"

    def _save_stats(self):
        """保存统计到文件"""
        try:
            stats_file = self._get_stats_file()
            data = {
                "stats": self.stats.to_dict(),
                "daily_stats": {
                    k: v.to_dict() for k, v in self._daily_stats.items()
                },
                "monthly_stats": {
                    k: v.to_dict() for k, v in self._monthly_stats.items()
                },
                "last_saved": datetime.now().isoformat()
            }
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"[COST_CONTROLLER] 保存统计失败: {e}")

    def _load_stats(self):
        """从文件加载统计"""
        try:
            stats_file = self._get_stats_file()
            if not os.path.exists(stats_file):
                return

            with open(stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载统计
            if "stats" in data:
                stats_data = data["stats"]
                self.stats = CostStats(
                    session_start=datetime.fromisoformat(stats_data.get("session_start", datetime.now().isoformat())),
                    total_calls=stats_data.get("total_calls", 0),
                    total_cost=stats_data.get("total_cost", 0.0),
                    total_input_tokens=stats_data.get("total_input_tokens", 0),
                    total_output_tokens=stats_data.get("total_output_tokens", 0)
                )

            # 加载每日统计
            self._daily_stats = {}
            for k, v in data.get("daily_stats", {}).items():
                self._daily_stats[k] = CostStats(
                    total_calls=v.get("total_calls", 0),
                    total_cost=v.get("total_cost", 0.0),
                    calls_in_current_period=v.get("calls_in_period", 0),
                    cost_in_current_period=v.get("cost_in_period", 0.0)
                )

            # 加载每月统计
            self._monthly_stats = {}
            for k, v in data.get("monthly_stats", {}).items():
                self._monthly_stats[k] = CostStats(
                    total_calls=v.get("total_calls", 0),
                    total_cost=v.get("total_cost", 0.0)
                )

        except Exception as e:
            self.logger.error(f"[COST_CONTROLLER] 加载统计失败: {e}")


def get_cost_controller(
    config: Optional[CostConfig] = None,
    config_file: Optional[str] = None
) -> CostController:
    """获取成本控制器实例

    Args:
        config: 成本配置
        config_file: 配置文件路径

    Returns:
        CostController 实例
    """
    return CostController(config, config_file)
