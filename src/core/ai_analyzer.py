"""
AI分析器 (AI Analyzer) - 带成本控制版本

Phase 2 Day 4 MVP功能:
- 批量评估逻辑
- AI成本控制逻辑
- 调用计数器
- 超限降级到规则引擎
- 疑似项优先调用AI

成本控制策略:
1. 规则引擎评估所有项（免费、快速）
2. 仅对 SusPicious 项调用AI
3. Safe 项直接跳过AI

成本对比:
- 全AI: 10万项 → 2000次API
- 混合: 2万可疑项 → 400次API (~节省80%)

成本计算（基于 GLM-4-Flash 定价）:
- Input: $0.14 / 1M tokens
- Output: $0.28 / 1M tokens
- 每次调用约 1000 tokens 输入 + 500 tokens 输出 = $0.21 / 次
"""
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

from .ai_client import AIClient, AIConfig
from .ai_prompt_builder import PromptBuilder
from .ai_response_parser import ResponseParser
from .rule_engine import RiskLevel, RuleEngine, Rule
from .cost_controller import CostController, CostConfig, CostControlMode as CCCMode
from .models import ScanItem
from .models_smart import CleanupItem, CleanupPlan
from utils.logger import get_logger

logger = get_logger(__name__)


class CostControlMode(Enum):
    """成本控制模式"""
    UNLIMITED = "unlimited"        # 无限制 - 全部使用 AI
    BUDGET = "budget"              # 预算模式 - 限制调用次数
    FALLBACK = "fallback"          # 回退模式 - 超限降级到规则引擎
    RULES_ONLY = "rules_only"      # 仅规则 - 不调用 AI


@dataclass
class AIAnalysisStats:
    """AI 分析统计"""
    total_items: int = 0
    items_with_ai: int = 0
    items_with_rules_only: int = 0
    safe_count: int = 0
    suspicious_count: int = 0
    dangerous_count: int = 0
    ai_calls: int = 0
    execution_time: float = 0.0
    # 成本信息
    total_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    # 降级状态
    is_degraded: bool = False
    degradation_reason: str = ""

    @property
    def ai_coverage(self) -> float:
        """AI覆盖率"""
        if self.total_items == 0:
            return 0.0
        return (self.items_with_ai / self.total_items) * 100

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_items": self.total_items,
            "items_with_ai": self.items_with_ai,
            "items_with_rules_only": self.items_with_rules_only,
            "safe_count": self.safe_count,
            "suspicious_count": self.suspicious_count,
            "dangerous_count": self.dangerous_count,
            "ai_calls": self.ai_calls,
            "execution_time": round(self.execution_time, 2),
            "total_cost": round(self.total_cost, 4),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "is_degraded": self.is_degraded,
            "degradation_reason": self.degradation_reason
        }


@dataclass
class CostControlConfig:
    """成本控制配置"""
    mode: CostControlMode = CostControlMode.FALLBACK
    max_calls_per_scan: int = 100      # 单次扫描最大AI调用次数
    batch_size: int = 50               # 批量评估大小
    only_analyze_suspicious: bool = True  # 仅分析可疑项
    fallback_to_rules: bool = True     # AI失败时回退到规则引擎


class AIAnalyzer:
    """AI分析器 - 成本控制版本

    分析策略:
    1. 规则引擎评估所有项（免费、快速）
    2. 仅对suspicious项调用AI
    3. Safe项直接跳过AI

    成本控制:
    - 调用计数器限制单次扫描的AI调用次数
    - 超限自动降级到规则引擎
    - 批量评估提高效率
    - 预算限制（USD）
    """

    def __init__(
        self,
        ai_config: Optional[AIConfig] = None,
        cost_config: Optional[CostControlConfig] = None,
        cost_controller: Optional[CostController] = None
    ):
        """初始化AI分析器

        Args:
            ai_config: AI配置
            cost_config: 成本控制配置
            cost_controller: 成本控制器实例
        """
        self.ai_config = ai_config or AIConfig()
        self.cost_config = cost_config or CostControlConfig()

        # 初始化组件
        self.ai_client = AIClient(self.ai_config) if self.ai_config.api_key else None
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser(strict=False)
        self.rule_engine = RuleEngine()

        # 成本控制
        self.cost_controller = cost_controller

        # 成本控制状态
        self._call_count = 0
        self._current_stats = AIAnalysisStats()
        self._start_time = 0.0

        self.logger = logger

    def _create_cost_controller(self) -> CostController:
        """创建成本控制器（如果尚未创建）"""
        if self.cost_controller is None:
            cc_config = CostConfig(
                mode=CCCMode(self.cost_config.mode.value),
                max_calls_per_scan=self.cost_config.max_calls_per_scan,
                max_budget_per_scan=2.0,  # 默认 $2.00
                fallback_to_rules=self.cost_config.fallback_to_rules
            )
            self.cost_controller = CostController(cc_config)
        return self.cost_controller

    def analyze_scan_results(
        self,
        items: List[ScanItem],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> CleanupPlan:
        """分析扫描结果并生成清理计划

        Args:
            items: 扫描项列表
            progress_callback: 进度回调 (current, total)

        Returns:
            CleanupPlan 清理计划
        """
        self._start_time = time.time()
        self._current_stats = AIAnalysisStats(total_items=len(items))
        self._call_count = 0

        # 确保成本控制器已初始化
        self._create_cost_controller()

        self.logger.info(f"[AI_ANALYZER] 开始分析 {len(items)} 个扫描项")
        self.logger.info(f"[AI_ANALYZER] 成本控制模式: {self.cost_config.mode.value}")

        # 重置成本控制器统计
        self.cost_controller.reset_scan_stats()

        # 生成计划ID
        plan_id = f"plan_{int(time.time())}"

        # 创建清理计划
        cleanup_items = []

        # 步骤1: 规则引擎评估所有项
        self.logger.info("[AI_ANALYZER] 步骤1: 规则引擎评估")
        for i, item in enumerate(items):
            if progress_callback:
                progress_callback(i, len(items))

            # 规则引擎评估
            risk_result = self._rule_assess(item)
            cleanup_item = self._to_cleanup_item(item, risk_result)
            cleanup_items.append(cleanup_item)

        # 步骤2: 筛选需要AI评估的项目
        if self.cost_config.mode == CostControlMode.RULES_ONLY:
            self.logger.info("[AI_ANALYZER] 规则仅模式，跳过AI评估")
        else:
            self._ai_assess_items(cleanup_items, progress_callback)

        # 步骤3: 生成清理计划
        plan = self._create_plan(plan_id, cleanup_items)

        # 计算统计数据
        self._calculate_stats(plan)

        self.logger.info(f"[AI_ANALYZER] 分析完成: "
                        f"总计={len(items)}, "
                        f"AI评估={self._call_count}, "
                        f"成本=${self._current_stats.total_cost:.4f}, "
                        f"耗时={self._current_stats.execution_time:.2f}s")

        return plan

    def _create_plan(self, plan_id: str, cleanup_items: List[CleanupItem]) -> CleanupPlan:
        """创建清理计划

        Args:
            plan_id: 计划ID
            cleanup_items: 清理项列表

        Returns:
            CleanupPlan
        """
        # 计算总大小和预计释放空间
        total_size = sum(item.size for item in cleanup_items)
        estimated_freed = sum(item.size for item in cleanup_items if item.is_safe)

        return CleanupPlan(
            plan_id=plan_id,
            scan_type="custom",
            scan_target="",
            items=cleanup_items,
            total_size=total_size,
            estimated_freed=estimated_freed,
            ai_call_count=self._call_count
        )

    def _rule_assess(self, item: ScanItem) -> Dict:
        """使用规则引擎评估项目

        Args:
            item: 扫描项

        Returns:
            评估结果字典
        """
        # 使用 RuleEngine 的 classify 方法，它只返回 RiskLevel
        risk_level = self.rule_engine.classify(item.path, item.size)

        # 根据风险等级生成描述
        description = self._get_rule_description(item.path, risk_level)

        return {
            'risk_level': risk_level.value,
            'reason': description,
            'method': 'rule'
        }

    def _ai_assess_items(
        self,
        cleanup_items: List[CleanupItem],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """AI评估筛选的项目

        Args:
            cleanup_items: 清理项列表
            progress_callback: 进度回调
        """
        self.logger.info("[AI_ANALYZER] 步骤2: AI评估")

        # 筛选需要AI评估的项目
        items_to_assess = []
        for item in cleanup_items:
            # 只评估可疑项（如果配置了仅评估可疑项）
            if self.cost_config.only_analyze_suspicious:
                if item.ai_risk == RiskLevel.SUSPICIOUS:
                    items_to_assess.append(item)
            else:
                # 评估所有非Safe项
                if item.ai_risk != RiskLevel.SAFE:
                    items_to_assess.append(item)

        self.logger.info(f"[AI_ANALYZER] 需要AI评估: {len(items_to_assess)} 项")

        # 设置成本控制器回调
        def on_limit_reached(reason: str):
            self._current_stats.is_degraded = True
            self._current_stats.degradation_reason = reason
            self.logger.warning(f"[AI_ANALYZER] 已降级: {reason}")

        self.cost_controller.set_on_limit_reached(on_limit_reached)

        # 批量评估
        total_assessed = 0
        input_tokens_total = 0
        output_tokens_total = 0

        for item in items_to_assess:
            # 使用成本控制器检查是否可以调用
            can_call, reason = self.cost_controller.can_make_call()
            if not can_call:
                self.logger.warning(
                    f"[AI_ANALYZER] {reason}，降级到规则引擎"
                )
                self._current_stats.is_degraded = True
                self._current_stats.degradation_reason = reason
                break

            # AI评估
            try:
                input_tokens, output_tokens = self._ai_assess_single(item)

                # 记录调用
                self.cost_controller.record_call(
                    input_tokens=input_tokens or 1000,
                    output_tokens=output_tokens or 500
                )

                total_assessed += 1
                self._call_count += 1

                if input_tokens:
                    input_tokens_total += input_tokens
                if output_tokens:
                    output_tokens_total += output_tokens

                if progress_callback:
                    progress_callback(total_assessed, len(items_to_assess))

            except Exception as e:
                self.logger.error(f"[AI_ANALYZER] AI评估失败 {item.path}: {e}")
                # 回退到规则引擎结果
                continue

        self._current_stats.items_with_ai = total_assessed
        self._current_stats.ai_calls = self._call_count
        self._current_stats.input_tokens = input_tokens_total
        self._current_stats.output_tokens = output_tokens_total
        self._current_stats.total_cost = self.cost_controller.get_stats().cost_in_current_period

    def _ai_assess_single(self, item: CleanupItem) -> tuple[int, int]:
        """AI评估单个项目

        Args:
            item: 清理项

        Returns:
            (input_tokens, output_tokens)
        """
        if not self.ai_client:
            return 0, 0

        # 构建提示词
        scan_item = self._to_scan_item(item)
        prompt = self.prompt_builder.build_assessment_prompt(scan_item)

        # 估算输入 tokens（基于字符数）
        input_tokens = len(prompt) // 4  # 约 4 字符 = 1 token

        # 调用AI
        success, response = self.ai_client.chat([
            {"role": "user", "content": prompt}
        ])

        if not success:
            self.logger.warning(f"[AI_ANALYZER] AI调用失败: {response}")
            if self.cost_config.fallback_to_rules:
                self.logger.info("[AI_ANALYZER] 回退到规则引擎")
            return input_tokens, 0

        # 估算输出 tokens
        output_tokens = len(response) // 4

        # 解析响应
        original_risk_enum = RiskLevel.SAFE  # 默认值
        result = self.response_parser.parse(response, item.path, original_risk_enum)
        if result:
            # 更新AI评估结果
            item.ai_risk = result.ai_risk
            self._current_stats.items_with_ai += 1
        elif self.cost_config.fallback_to_rules:
            self.logger.info("[AI_ANALYZER] 解析失败，回退到规则引擎")

        return input_tokens, output_tokens

    def _to_cleanup_item(self, scan_item: ScanItem, risk_result: Dict) -> CleanupItem:
        """将 ScanItem 转换为 CleanupItem

        Args:
            scan_item: 扫描项
            risk_result: 风险评估结果

        Returns:
            CleanupItem
        """
        # ScanItem 的 item_type 是字符串类型
        # ScanItem 的 risk_level 是字符串类型，需要转换为 RiskLevel 枚举
        risk_level_enum = RiskLevel.from_value(scan_item.risk_level)

        return CleanupItem(
            item_id=id(scan_item),
            path=scan_item.path,
            size=scan_item.size,
            item_type=scan_item.item_type,  # 字符串类型
            original_risk=risk_level_enum,
            ai_risk=RiskLevel.from_value(risk_result['risk_level'])
        )

    def _to_scan_item(self, cleanup_item: CleanupItem) -> ScanItem:
        """将 CleanupItem 转换为 ScanItem（用于AI评估）

        Args:
            cleanup_item: 清理项

        Returns:
            ScanItem
        """
        # ScanItem 的 item_type 是字符串类型 ('file' 或 'directory')
        item_type = cleanup_item.item_type if cleanup_item.item_type in ('file', 'directory') else 'file'

        return ScanItem(
            path=cleanup_item.path,
            description=f"文件: {cleanup_item.path}",  # CleanupItem 没有 description 属性
            size=cleanup_item.size,
            item_type=item_type,
            risk_level=cleanup_item.original_risk.value
        )

    def _get_rule_description(self, path: str, risk_level: RiskLevel) -> str:
        """根据路径和风险等级生成描述

        Args:
            path: 路径
            risk_level: 风险等级

        Returns:
            原因描述
        """
        path_lower = path.lower()

        if risk_level == RiskLevel.SAFE:
            safe_patterns = ['temp', 'cache', 'log', 'prefetch', 'thumb']
            for pattern in safe_patterns:
                if pattern in path_lower:
                    return f"清理项（{pattern}），可安全删除"
            return "安全清理项"

        elif risk_level == RiskLevel.DANGEROUS:
            dangerous_patterns = ['windows', 'program', 'system', 'system32', 'driver']
            for pattern in dangerous_patterns:
                if pattern in path_lower:
                    return f"系统关键文件（{pattern}），不建议删除"
            return "危险清理项"

        else:
            return "疑似项目，需用户确认"

    def _get_rule_reason(self, item: ScanItem, risk_level: RiskLevel) -> str:
        """获取规则评估的原因

        Args:
            item: 扫描项
            risk_level: 风险等级

        Returns:
            原因描述
        """
        path = item.path.lower()

        if risk_level == RiskLevel.SAFE:
            safe_patterns = ['temp', 'cache', 'log', 'prefetch', 'thumb']
            for pattern in safe_patterns:
                if pattern in path:
                    return f"清理项（{pattern}），可安全删除"
            return "安全清理项"

        elif risk_level == RiskLevel.DANGEROUS:
            dangerous_patterns = ['windows', 'program', 'system', 'system32', 'driver']
            for pattern in dangerous_patterns:
                if pattern in path:
                    return f"系统关键文件（{pattern}），不建议删除"
            return "危险清理项"

        else:
            return "疑似项目，需用户确认"

    def _calculate_stats(self, plan: CleanupPlan):
        """计算统计信息

        Args:
            plan: 清理计划
        """
        self._current_stats.execution_time = time.time() - self._start_time

        for item in plan.items:
            if item.ai_risk == RiskLevel.SAFE:
                self._current_stats.safe_count += 1
            elif item.ai_risk == RiskLevel.SUSPICIOUS:
                self._current_stats.suspicious_count += 1
            elif item.ai_risk == RiskLevel.DANGEROUS:
                self._current_stats.dangerous_count += 1

        self._current_stats.items_with_rules_only = (
            self._current_stats.total_items - self._current_stats.items_with_ai
        )

    def get_stats(self) -> AIAnalysisStats:
        """获取统计信息

        Returns:
            AIAnalysisStats
        """
        return self._current_stats

    def get_stats_report(self) -> str:
        """获取统计报告

        Returns:
            报告文本
        """
        stats = self.get_stats()
        report = (
            f"AI分析统计:\n"
            f"  总项目: {stats.total_items}\n"
            f"  AI评估: {stats.items_with_ai} ({stats.ai_coverage:.1f}%)\n"
            f"  规则仅: {stats.items_with_rules_only}\n"
            f"  AI调用: {stats.ai_calls}\n"
            f"  成本: ${stats.total_cost:.4f}\n"
            f"  Tokens: 输入={stats.input_tokens}, 输出={stats.output_tokens}\n"
            f"  耗时: {stats.execution_time:.2f}s\n"
            f"  风险分布: Safe={stats.safe_count}, "
            f"Suspicious={stats.suspicious_count}, "
            f"Dangerous={stats.dangerous_count}"
        )

        if stats.is_degraded:
            report += f"\n  降级状态: {stats.degradation_reason}"

        return report

    def get_cost_report(self) -> Dict:
        """获取成本报告

        Returns:
            成本报告字典
        """
        if self.cost_controller:
            return self.cost_controller.get_usage_report()
        return {
            "current_scan": {
                "calls": self._call_count,
                "max_calls": self.cost_config.max_calls_per_scan,
                "cost": self._current_stats.total_cost,
                "max_budget": 2.0,
                "call_usage_percent": 0.0,
                "budget_usage_percent": 0.0
            },
            "alert_level": "normal",
            "is_degraded": self._current_stats.is_degraded,
            "degradation_reason": self._current_stats.degradation_reason
        }

    def get_cost_summary(self) -> str:
        """获取成本摘要（用于UI显示）"""
        report = self.get_cost_report()
        scan = report["current_scan"]

        if report["is_degraded"]:
            status = f"[已降级] {report['degradation_reason']}"
        else:
            status = "正常"

        return (
            f"{status} | "
            f"调用: {scan['calls']}/{scan['max_calls']} | "
            f"成本: ${scan['cost']:.3f}/${scan['max_budget']:.2f}"
        )

    def reset_call_count(self):
        """重置调用计数"""
        self._call_count = 0
        self.logger.info("[AI_ANALYZER] 调用计数已重置")

    def get_call_count(self) -> int:
        """获取当前调用次数

        Returns:
            调用次数
        """
        return self._call_count

    def is_ai_enabled(self) -> bool:
        """检查AI是否启用

        Returns:
            是否启用
        """
        return (self.ai_client is not None and
                self.ai_config.api_key and
                self.cost_config.mode != CostControlMode.RULES_ONLY)

    def set_cost_config(self, config: CostControlConfig):
        """设置成本控制配置

        Args:
            config: 成本控制配置
        """
        self.cost_config = config

        # 如果有成本控制器，更新它
        if self.cost_controller:
            cc_config = CostConfig(
                mode=CCMode(config.mode.value),
                max_calls_per_scan=config.max_calls_per_scan,
                fallback_to_rules=config.fallback_to_rules
            )
            self.cost_controller.update_config(cc_config)

        self.logger.info(f"[AI_ANALYZER] 成本控制配置已更新: {config.mode.value}")

    def set_cost_controller(self, controller: CostController):
        """设置成本控制器

        Args:
            controller: 成本控制器
        """
        self.cost_controller = controller
        self.logger.info("[AI_ANALYZER] 成本控制器已设置")


# 便利函数
def get_ai_analyzer(
    ai_config: Optional[AIConfig] = None,
    cost_config: Optional[CostControlConfig] = None,
    cost_controller: Optional[CostController] = None
) -> AIAnalyzer:
    """获取AI分析器实例

    Args:
        ai_config: AI配置
        cost_config: 成本控制配置
        cost_controller: 成本控制器

    Returns:
        AIAnalyzer 实例
    """
    return AIAnalyzer(ai_config, cost_config, cost_controller)


def create_ai_analyzer_with_cost_control(
    api_key: str = "",
    max_calls: int = 100,
    max_budget: float = 2.0,
    mode: str = "fallback"
) -> AIAnalyzer:
    """创建带成本控制的AI分析器

    Args:
        api_key: API密钥
        max_calls: 最大调用次数
        max_budget: 最大预算（USD）
        mode: 模式 (unlimited, budget, fallback, rules_only)

    Returns:
        AIAnalyzer 实例
    """
    from .cost_controller import CostConfig

    ai_config = AIConfig(api_key=api_key) if api_key else AIConfig()

    cost_config = CostControlConfig(
        mode=CostControlMode(mode),
        max_calls_per_scan=max_calls,
        fallback_to_rules=True
    )

    cc_config = CostConfig(
        mode=CCMode(mode),
        max_calls_per_scan=max_calls,
        max_budget_per_scan=max_budget,
        fallback_to_rules=True
    )
    cost_controller = CostController(cc_config)

    return AIAnalyzer(ai_config, cost_config, cost_controller)
