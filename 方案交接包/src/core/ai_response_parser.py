"""
AI复核功能模块 - 响应解析器
提供多种解析策略和容错机制
"""
import re
import json
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from core.rule_engine import RiskLevel
from core.ai_review_models import AIReviewResult


logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    data: Optional[Dict[str, Any]]
    method: str
    error: Optional[str] = None


class ResponseParser:
    """AI响应解析器 - 支持多种容错策略"""

    # 必需字段
    REQUIRED_FIELDS = {
        'ai_risk', 'confidence', 'function_description',
        'software_name', 'risk_reason', 'cleanup_suggestion'
    }

    # 风险等级映射
    RISK_MAP = {
        'safe': RiskLevel.SAFE,
        '安全': RiskLevel.SAFE,
        '0': RiskLevel.SAFE,
        'suspicious': RiskLevel.SUSPICIOUS,
        '疑似': RiskLevel.SUSPICIOUS,
        'warning': RiskLevel.SUSPICIOUS,
        '1': RiskLevel.SUSPICIOUS,
        'dangerous': RiskLevel.DANGEROUS,
        '危险': RiskLevel.DANGEROUS,
        'error': RiskLevel.DANGEROUS,
        '2': RiskLevel.DANGEROUS
    }

    def __init__(self, strict: bool = True):
        """初始化解析器

        Args:
            strict: 严格模式，严格模式要求所有字段完整
        """
        self.strict = strict
        # 解析策略列表，按优先级排序
        self.strategies = [
            (self._extract_json_block, "json_block"),
            (self._extract_json_only, "json_only"),
            (self._extract_key_value_pairs, "key_value"),
            (self._extract_markdown_table, "markdown_table"),
            (self._fallback_extract, "fallback")
        ]

    def parse(self, response: str, item_path: str, original_risk: RiskLevel = None) -> Optional[AIReviewResult]:
        """解析AI响应

        Args:
            response: AI响应文本
            item_path: 项目路径
            original_risk: 原始风险等级

        Returns:
            AIReviewResult解析成功，None解析失败
        """
        from datetime import datetime

        cleaned_response = self._clean_response(response)
        logger.debug(f"解析响应: {cleaned_response[:200]}...")

        for strategy, method_name in self.strategies:
            try:
                parse_result = strategy(cleaned_response)

                if parse_result.success and parse_result.data:
                    validated = self._validate_and_normalize(
                        parse_result.data,
                        item_path,
                        original_risk,
                        method_name
                    )

                    if validated:
                        validated.review_timestamp = datetime.now()
                        validated.parse_method = method_name
                        logger.debug(f"解析成功，方法: {method_name}")
                        return validated

            except Exception as e:
                logger.debug(f"策略 {method_name} 失败: {e}")
                continue

        logger.warning(f"所有解析策略均失败")
        return None

    def _clean_response(self, response: str) -> str:
        """清理响应文本

        Args:
            response: 原始响应

        Returns:
            清理后的响应
        """
        # 移除多余的空白
        cleaned = re.sub(r'\s+', ' ', response.strip())

        # 移除常见的前缀后缀
        prefixes = [
            r'^[Tt]he (result|output) is:\s*',
            r'^[Hh]ere is (the )?(result|output):\s*',
            r'^[Rr]esponse:\s*',
            r'^[Aa]nswer:\s*',
        ]

        for prefix in prefixes:
            cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _extract_json_block(self, response: str) -> ParseResult:
        """提取JSON代码块

        Args:
            response: 响应文本

        Returns:
            ParseResult
        """
        # 尝试提取 ```json``` 块
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)

        if match:
            return self._parse_json_text(match.group(1), "json_block")

        # 尝试提取 ``````` 块
        backtick_pattern = r'```\s*(\{.*?\})\s*```'
        match = re.search(backtick_pattern, response, re.DOTALL)

        if match:
            return self._parse_json_text(match.group(1), "json_block")

        return ParseResult(success=False, data=None, method="json_block")

    def _extract_json_only(self, response: str) -> ParseResult:
        """提取纯JSON（无代码块标记）

        Args:
            response: 响应文本

        Returns:
            ParseResult
        """
        # 尝试在响应中找到JSON对象
        json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        matches = re.findall(json_pattern, response)

        # 尝试所有匹配，从最长的开始
        matches.sort(key=len, reverse=True)

        for match in matches:
            result = self._parse_json_text(match, "json_only")
            if result.success:
                return result

        return ParseResult(success=False, data=None, method="json_only")

    def _parse_json_text(self, text: str, method: str = "json") -> ParseResult:
        """解析JSON文本

        Args:
            text: JSON文本
            method: 解析方法名称

        Returns:
            ParseResult
        """
        try:
            data = json.loads(text)
            return ParseResult(success=True, data=data, method=method)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON解析失败: {e}")
            return ParseResult(success=False, data=None, method=method,
                             error=f"JSON解析失败: {str(e)}")

    def _extract_key_value_pairs(self, response: str) -> ParseResult:
        """提取键值对（非JSON格式）

        Args:
            response: 响应文本

        Returns:
            ParseResult
        """
        data = {}

        # 定义提取模式
        patterns = {
            'ai_risk': [r'(?:ai_risk|risk|risk_level)["\s:]+["\']?([a-zA-Z]+)["\']?'],
            'confidence': [r'(?:confidence)["\s:]+([0-9.]+)'],
            'function_description': [r'(?:function_description|function|description)["\s:]+["\']([^"\']+)["\']'],
            'software_name': [r'(?:software_name|software|app)["\s:]+["\']([^"\']+)["\']'],
            'risk_reason': [r'(?:risk_reason|reason)["\s:]+["\']([^"\']+)["\']'],
            'cleanup_suggestion': [r'(?:cleanup_suggestion|suggestion)["\s:]+["\']([^"\']+)["\']']
        }

        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    # 取最后一个匹配
                    matches = list(re.finditer(pattern, response, re.IGNORECASE))
                    if matches:
                        value = matches[-1].group(1).strip()
                        # 移除可能的尾随标点
                        value = re.sub(r'[,;.。]+$', '', value)
                        data[field] = value
                        break

        if len(data) >= 4:  # 至少要有4个字段才认为有效
            return ParseResult(success=True, data=data, method="key_value")

        return ParseResult(success=False, data=None, method="key_value")

    def _extract_markdown_table(self, response: str) -> ParseResult:
        """提取Markdown表格

        Args:
            response: 响应文本

        Returns:
            ParseResult
        """
        # 查找表格行
        table_pattern = r'\|([^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|)'
        matches = re.findall(table_pattern, response)

        if not matches:
            return ParseResult(success=False, data=None, method="markdown_table")

        # 跳过表头和分隔行
        rows = [m.strip('|').split('|') for m in matches[2:] if '--' not in m]

        # 寻找包含AI数据的行
        for row in rows:
            if len(row) >= 6:
                data = {
                    'ai_risk': row[0].strip().strip('`\'"').lower(),
                    'confidence': float(row[1].strip()) if row[1].strip().replace('.', '').isdigit() else 0.5,
                    'function_description': row[2].strip().strip('`\'"'),
                    'software_name': row[3].strip().strip('`\'"'),
                    'risk_reason': row[4].strip().strip('`\'"'),
                    'cleanup_suggestion': row[5].strip().strip('`\'"')
                }
                return ParseResult(success=True, data=data, method="markdown_table")

        return ParseResult(success=False, data=None, method="markdown_table")

    def _fallback_extract(self, response: str) -> ParseResult:
        """回退提取 - 简单文本分析

        Args:
            response: 响应文本

        Returns:
            ParseResult
        """
        data = {
            'ai_risk': 'suspicious',
            'confidence': 0.3,
            'function_description': '无法识别',
            'software_name': '未知',
            'risk_reason': '解析失败',
            'cleanup_suggestion': '需人工确认'
        }

        # 尝试识别风险等级
        risk_keywords = {
            RiskLevel.SAFE: ['安全', 'safe', '可删除', '删除', '缓存', '临时', '日志'],
            RiskLevel.DANGEROUS: ['危险', 'dangerous', '不能删除', '重要', '数据', '用户'],
            RiskLevel.SUSPICIOUS: ['疑似', 'suspicious', '不确定', '需确认']
        }

        response_lower = response.lower()
        for risk_type, keywords in risk_keywords.items():
            if any(kw in response_lower for kw in keywords):
                data['ai_risk'] = risk_type.value
                break

        return ParseResult(success=True, data=data, method="fallback")

    def _validate_and_normalize(
        self,
        data: Dict[str, Any],
        item_path: str,
        original_risk: RiskLevel,
        method: str
    ) -> Optional[AIReviewResult]:
        """验证并规范化数据

        Args:
            data: 解析出的数据
            item_path: 项目路径
            original_risk: 原始风险
            method: 解析方法

        Returns:
            AIReviewResult或None
        """
        # 检查必需字段
        missing_fields = self.REQUIRED_FIELDS - set(data.keys())
        if missing_fields and self.strict:
            logger.debug(f"缺少必需字段: {missing_fields}")
            return None

        # 规范化风险等级
        ai_risk_value = str(data.get('ai_risk', 'suspicious')).lower()
        ai_risk = self._normalize_risk(ai_risk_value)

        # 规范化置信度
        confidence = float(data.get('confidence', 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return AIReviewResult(
            item_path=item_path,
            original_risk=original_risk,
            ai_risk=ai_risk,
            confidence=confidence,
            function_description=data.get('function_description', '')[:50],
            software_name=data.get('software_name', '未知')[:30],
            risk_reason=data.get('risk_reason', '')[:30],
            cleanup_suggestion=data.get('cleanup_suggestion', '')[:40],
            ai_reasoning=str(data),
            is_valid=True,
            parse_method=method
        )

    def _normalize_risk(self, risk_str: str) -> RiskLevel:
        """规范化风险等级

        Args:
            risk_str: 风险字符串

        Returns:
            RiskLevel
        """
        risk_str_lower = risk_str.lower()

        # 尝试精确匹配
        if risk_str_lower in ['safe', '安全', '可删除', '0']:
            return RiskLevel.SAFE
        elif risk_str_lower in ['dangerous', '危险', '不可删除', '2', 'error']:
            return RiskLevel.DANGEROUS
        else:
            return RiskLevel.SUSPICIOUS


# 便捷函数
def get_parser(strict: bool = True) -> ResponseParser:
    """获取响应解析器

    Args:
        strict: 严格模式

    Returns:
        ResponseParser实例
    """
    return ResponseParser(strict=strict)


def parse_with_retry(
    response: str,
    item_path: str,
    original_risk: RiskLevel = None,
    max_retries: int = 3,
    strict: bool = True
) -> Optional[AIReviewResult]:
    """带重试的解析

    Args:
        response: AI响应
        item_path: 项目路径
        original_risk: 原始风险
        max_retries: 最大重试次数
        strict: 严格模式

    Returns:
        AIReviewResult或None
    """
    parser = get_parser(strict)

    # 首次尝试
    result = parser.parse(response, item_path, original_risk)
    if result:
        return result

    # 重试（使用更宽松的模式）
    for attempt in range(max_retries - 1):
        parser = get_parser(strict=False)
        result = parser.parse(response, item_path, original_risk)
        if result:
            return result

        # 如果连续失败，返回默认结果
        from datetime import datetime
        return AIReviewResult(
            item_path=item_path,
            original_risk=original_risk,
            ai_risk=RiskLevel.SUSPICIOUS,
            confidence=0.2,
            function_description="解析失败",
            software_name="未知",
            risk_reason="AI响应格式错误",
            cleanup_suggestion="需人工确认",
            ai_reasoning=f"解析尝试{max_retries}次均失败",
            review_timestamp=datetime.now(),
            retry_count=max_retries,
            is_valid=False,
            parse_method="fallback"
        )

    return None
