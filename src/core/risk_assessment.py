"""
风险评估系统模块
整合规则引擎和AI评估，提供统一的风险评估接口
"""
from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from .rule_engine import RuleEngine, RiskLevel, Rule
from .models import ScanItem
from .ai_client import AIClient, AIConfig
from .whitelist import get_whitelist


@dataclass
class RuleAssessmentResult:
    """规则评估结果"""
    risk_level: RiskLevel
    matched_rules: List[Rule]
    confidence: float  # 规则匹配的置信度 (0-1)
    reason: str  # 评估原因


@dataclass
class DecisionReport:
    """给AI的决策报告"""
    item_path: str
    item_type: str
    size: int
    rule_assessment: RuleAssessmentResult
    context: dict  # 额外上下文信息


@dataclass
class FinalRiskAssessment:
    """最终风险评估结果"""
    risk_level: RiskLevel
    reason: str
    method: str  # "rule_only" 或 "ai_enhanced"
    rule_assessment: Optional[RuleAssessmentResult]
    ai_response: Optional[str]


class RiskAssessmentSystem:
    """
    风险评估系统

    提供统一的风险评估接口：
    1. 首先使用规则引擎进行基础评估
    2. 如果启用AI，将规则评估结果报告给AI进行最终决策
    """

    def __init__(self, ai_config: Optional[AIConfig] = None, ai_enabled: bool = True):
        """
        初始化风险评估系统

        Args:
            ai_config: AI 配置
            ai_enabled: 是否启用AI评估
        """
        self.rule_engine = RuleEngine()
        self.ai_config = ai_config
        self.ai_enabled = ai_enabled
        self.ai_client: Optional[AIClient] = None

        try:
            if ai_config and ai_enabled:
                self.ai_client = AIClient(ai_config)
                self._validate_ai_config()
        except Exception as e:
            print(f"AI初始化失败: {e}")
            self.ai_enabled = False
            self.ai_client = None

    def enable_ai(self, enabled: bool):
        """启用/禁用AI评估"""
        self.ai_enabled = enabled

    def set_ai_config(self, ai_config: AIConfig):
        """设置AI配置"""
        self.ai_config = ai_config
        if self.ai_enabled:
            self.ai_client = AIClient(ai_config)
            self._validate_ai_config()

    def _validate_ai_config(self):
        """验证AI配置是否有效"""
        if self.ai_client:
            is_valid, _ = self.ai_client.config.validate()
            if not is_valid and self.ai_enabled:
                # AI配置无效，禁用AI评估
                print("AI配置无效，将使用规则引擎进行评估")

    def assess_item(self, item: ScanItem) -> FinalRiskAssessment:
        """
        评估单个扫描项的风险等级

        流程：
        1. 检查白名单
        2. 使用规则引擎评估
        3. 如果启用AI，将规则结果报告给AI进行最终决策

        Args:
            item: 扫描项

        Returns:
            FinalRiskAssessment: 最终风险评估结果
        """
        # 1. 检查白名单
        whitelist = get_whitelist()
        if whitelist.is_protected(item.path):
            return FinalRiskAssessment(
                risk_level=RiskLevel.DANGEROUS,
                reason="在白名单保护中",
                method="whitelist",
                rule_assessment=None,
                ai_response=None
            )

        # 2. 获取文件最后访问时间（用于规则评估）
        try:
            import os
            last_accessed = datetime.fromtimestamp(os.path.getatime(item.path))
        except:
            last_accessed = None

        # 3. 规则引擎评估
        rule_result = self._assess_with_rules(
            item.path, item.size, last_accessed, item.item_type == 'file'
        )

        # 4. 如果禁用AI或AI不可用，直接返回规则评估结果
        if not self.ai_enabled or not self.ai_client:
            return FinalRiskAssessment(
                risk_level=rule_result.risk_level,
                reason=rule_result.reason,
                method="rule_only",
                rule_assessment=rule_result,
                ai_response=None
            )

        # 5. AI增强评估
        ai_result = self._assess_with_ai(item, rule_result)

        if ai_result:
            # ai_result 是 (risk_level, reason) tuple
            risk_level, reason = ai_result
            return FinalRiskAssessment(
                risk_level=risk_level,
                reason=reason,
                method="ai_enhanced",
                rule_assessment=rule_result,
                ai_response=reason  # AI response is the reason
            )
        else:
            # AI评估失败，回退到规则结果
            return FinalRiskAssessment(
                risk_level=rule_result.risk_level,
                reason=rule_result.reason + " (AI评估失败)",
                method="rule_only",
                rule_assessment=rule_result,
                ai_response=None
            )

    def _assess_with_rules(self, path: str, size: int, last_accessed: Optional[datetime],
                           is_file: bool) -> RuleAssessmentResult:
        """
        使用规则引擎评估

        Args:
            path: 文件路径
            size: 文件大小
            last_accessed: 最后访问时间
            is_file: 是否为文件

        Returns:
            RuleAssessmentResult: 规则评估结果
        """
        # 使用规则引擎分类
        risk_level = self.rule_engine.classify(path, size, last_accessed, is_file)

        # 查找匹配的规则
        matched_rules = []
        for rule in self.rule_engine.rules:
            if self._matches_rule(path, size, last_accessed, is_file, rule):
                matched_rules.append(rule)

        # 计算置信度
        if matched_rules:
            # 如果有明确匹配规则，置信度较高
            if len(matched_rules) == 1:
                confidence = 0.9
            else:
                confidence = 0.7
        else:
            # 无匹配规则，使用默认分类
            confidence = 0.3

        # 生成评估原因
        if matched_rules:
            rule_names = [r.name for r in matched_rules[:3]]  # 最多显示3个
            reason = f"匹配规则: {', '.join(rule_names)}"
        else:
            reason = "按照规则引擎默认分类"

        return RuleAssessmentResult(
            risk_level=risk_level,
            matched_rules=matched_rules,
            confidence=confidence,
            reason=reason
        )

    def _assess_with_ai(self, item: ScanItem, rule_result: RuleAssessmentResult) -> Optional[Tuple[RiskLevel, str]]:
        """
        使用AI进行增强评估

        将规则评估结果报告给AI，由AI进行最终决策

        Args:
            item: 扫描项
            rule_result: 规则评估结果

        Returns:
            (risk_level, reason) AI评估结果，失败返回None
        """
        try:
            # 构建决策报告
            report = self._build_decision_report(item, rule_result)

            # 构建提示词
            prompt = self._build_ai_prompt(report)

            # 调用AI
            messages = [{'role': 'user', 'content': prompt}]
            success, response = self.ai_client.chat(messages)

            if success:
                # 解析AI响应
                return self._parse_ai_response(response)
            else:
                print(f"AI调用失败: {response}")
                return None

        except Exception as e:
            print(f"AI评估异常: {e}")
            return None

    def _build_decision_report(self, item: ScanItem, rule_result: RuleAssessmentResult) -> DecisionReport:
        """
        构建给AI的决策报告

        Args:
            item: 扫描项
            rule_result: 规则评估结果

        Returns:
            DecisionReport: 决策报告
        """
        return DecisionReport(
            item_path=item.path,
            item_type=item.item_type,
            size=item.size,
            rule_assessment=rule_result,
            context={
                "matched_rules_count": len(rule_result.matched_rules),
                "rule_confidence": rule_result.confidence,
                "has_description": bool(item.description)
            }
        )

    def _build_ai_prompt(self, report: DecisionReport) -> str:
        """
        构建AI评估提示词

        将规则评估结果报告给AI，让AI进行最终决策

        Args:
            report: 决策报告

        Returns:
            str: AI提示词
        """
        rule = report.rule_assessment

        # 规则评估信息
        rule_info = f"""
## 规则引擎评估结果
- 评估等级: {rule.risk_level.value}
- 匹配规则数量: {len(rule.matched_rules)}
- 规则置信度: {rule.confidence:.1%}
- 评估原因: {rule.reason}
"""

        if rule.matched_rules:
            rule_info += f"\n- 匹配的规则:\n"
            for r in rule.matched_rules[:5]:  # 最多显示5个
                rule_info += f"  * {r.name}: {r.description}\n"

        # 构建完整提示词
        prompt = f"""# 角色：Windows 文件安全仲裁专家

## 任务
你是一个文件安全专家，需要根据规则引擎的评估结果，对文件/文件夹的删除风险进行最终判断。

## 规则引擎评估报告
{rule_info}

## 文件信息
- 路径: {report.item_path}
- 类型: {report.item_type}
- 大小: {self._format_size(report.size)}

## 评估标准
### 安全 (safe) - 可安全删除
- 规则引擎判定为安全，且规则置信度 >= 70%
- 明确的缓存、临时文件、日志文件等
- 90天以上未访问的文件

### 疑似 (suspicious) - 需用户确认
- 规则引擎判定为疑似，或规则置信度 < 70%
- 不确定用途的文件/文件夹
- 配置文件、数据文件等

### 危险 (dangerous) - 不建议删除
- 规则引擎判定为危险
- 系统关键文件、可执行程序、用户重要数据

## 决策原则
1. **尊重规则引擎结果**: 如果规则引擎有明确匹配且置信度高，应尊重其判断
2. **风险优先**: 宁可保守（偏向风险等级高），也不要误删重要文件
3. **AI作为仲裁**: 你的作用是对规则引擎结果进行复核和微调，而非完全重写

## 输出要求
请根据规则引擎评估报告，给出最终的风险等级判断。
输出格式为JSON（只输出JSON，不要其他文字）:
{{"risk_level": "safe"|"suspicious"|"dangerous", "reason": "简要说明最终判断理由（30字以内）"}}"""

        return prompt

    def _parse_ai_response(self, response: str) -> Optional[Tuple[RiskLevel, str]]:
        """
        解析AI响应

        Args:
            response: AI响应文本

        Returns:
            (risk_level, reason) AI评估结果
        """
        try:
            import json

            # 尝试提取JSON
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                json_str = response[json_start:json_end].strip()
            elif '```' in response:
                json_start = response.find('```') + 3
                json_end = response.find('```', json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()

            if json_str.startswith('{'):
                data = json.loads(json_str)
                risk_level_str = data.get("risk_level", "")
                reason = data.get("reason", "")

                # 标准化风险等级
                if "safe" in risk_level_str.lower():
                    risk_level = RiskLevel.SAFE
                elif "suspicious" in risk_level_str.lower() or "疑似" in risk_level_str:
                    risk_level = RiskLevel.SUSPICIOUS
                elif "dangerous" in risk_level_str.lower() or "危险" in risk_level_str:
                    risk_level = RiskLevel.DANGEROUS
                else:
                    risk_level = RiskLevel.SUSPICIOUS

                return risk_level, reason

        except Exception as e:
            print(f"解析AI响应失败: {e}")

        # 回退到简单文本匹配
        response_lower = response.lower()
        if 'danger' in response_lower or '危险' in response_lower:
            return RiskLevel.DANGEROUS, "AI判定为危险"
        elif 'safe' in response_lower or '安全' in response_lower:
            return RiskLevel.SAFE, "AI判定为安全"
        else:
            return None

    def _matches_rule(self, path: str, size: int, last_accessed: Optional[datetime],
                      is_file: bool, rule: Rule) -> bool:
        """检查文件/文件夹是否匹配规则"""
        return self.rule_engine._matches_rule(path, size, last_accessed, is_file, rule)

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"


# 全局风险评估系统实例（单例模式）
_global_system: Optional[RiskAssessmentSystem] = None


def get_risk_assessment_system(ai_config: Optional[AIConfig] = None, ai_enabled: Optional[bool] = None) -> RiskAssessmentSystem:
    """
    获取全局风险评估系统实例（单例）

    Args:
        ai_config: AI 配置（如果为 None 则从配置管理器读取）
        ai_enabled: 是否启用AI评估（如果为 None 则从配置管理器读取）

    Returns:
        RiskAssessmentSystem: 风险评估系统实例
    """
    global _global_system

    # 从配置管理器读取 AI 配置
    if ai_config is None or ai_enabled is None:
        from .config_manager import get_config_manager
        config_mgr = get_config_manager()
        ai_cfg = config_mgr.get_ai_config()
        if ai_config is None:
            ai_config = AIConfig(
                api_url=ai_cfg['api_url'],
                api_key=ai_cfg['api_key'],
                model=ai_cfg['api_model']
            )
        if ai_enabled is None:
            ai_enabled = ai_cfg['enabled']

    # 首次创建或需要重新初始化
    if _global_system is None:
        _global_system = RiskAssessmentSystem(ai_config, ai_enabled)
    else:
        # 总是更新配置（确保使用最新配置）
        _global_system.set_ai_config(ai_config)
        _global_system.enable_ai(ai_enabled)

    return _global_system
