"""
批注生成器 - 自动生成扫描批注
"""
import os
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from core.annotation import (
        ScanAnnotation, AssessmentMethod, RiskLevel,
        generate_annotation_id, get_default_recommendation,
        format_annotation_note
    )
    from core.whitelist import Whitelist, get_whitelist
    from core.rule_engine import RuleEngine, get_rule_engine
    from core.ai_enhancer import get_ai_enhancer
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"导批注模块导入失败: {e}")


logger = logging.getLogger(__name__)


class AnnotationGenerator:
    """批注生成器 - 为扫描结果生成批注"""

    def __init__(self):
        self.whitelist = get_whitelist()
        self.rule_engine = get_rule_engine()
        self.ai_enhancer = get_ai_enhancer()

    def generate_annotation(self, item_data: Dict[str, Any], scan_source: str = 'system') -> ScanAnnotation:
        """为扫描项生成批注

        Args:
            item_data: 扫描项数据字典，包含 path, size, description, type 等
            scan_source: 扫描来源 (system, browser, custom)

        Returns:
            ScanAnnotation 批注对象
        """
        path = item_data.get('path', '')
        size = item_data.get('size', 0)
        description = item_data.get('description', '')
        item_type = item_data.get('type', 'folder')

        # 生成ID
        anno_id = generate_annotation_id(path)

        # 文件信息
        file_name = os.path.basename(path)
        file_ext = os.path.splitext(path)[1] if os.path.isfile(path) else ''

        # 三层评估
        assessment_result = self._evaluate_security(path, file_name, file_ext, size, scan_source)

        # 创建批注
        annotation = ScanAnnotation(
            id=anno_id,
            item_path=path,
            item_type=item_type,

            file_size=size,
            file_name=file_name,
            file_extension=file_ext,

            risk_level=assessment_result['risk_level'],
            risk_score=assessment_result['risk_score'],
            confidence=assessment_result['confidence'],

            assessment_method=assessment_result['method'],
            assessment_source=assessment_result['source'],
            assessment_details=assessment_result['details'],

            annotation_note=assessment_result.get('details', ''),
            annotation_tags=assessment_result['tags'],
            recommendation=assessment_result['recommendation'],

            ai_confidence=assessment_result.get('ai_confidence', 0),
            rule_match_count=assessment_result.get('rule_matches', 0),

            cache_hit=assessment_result.get('cached', False),
            cache_key=assessment_result.get('cache_key'),

            scan_source=scan_source,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        # 获取最后修改时间
        try:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                import datetime as dt
                annotation.last_modified = dt.datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            pass

        return annotation

    def _evaluate_security(self, path: str, file_name: str,
                           file_ext: str, size: int,
                           scan_source: str) -> Dict[str, Any]:
        """三层安全评估

        返回评估结果字典
        """
        result = {
            'method': 'rule',  # whitelist, rule, ai
            'source': '',      # 具体来源描述
            'details': '',    # 详细说明
            'risk_level': 'suspicious',
            'risk_score': 50,
            'confidence': 0.5,
            'tags': [],
            'cache_key': None,
            'cached': False,
            'ai_confidence': 0.0,
            'rule_matches': 0,
        }

        path_lower = path.lower()

        # === 第一层: 白名单检查 ===
        if self.whitelist.is_whitelisted(path):
            return {
                'method': AssessmentMethod.WHITELIST.value,
                'source': '白名单数据库',
                'details': f'{file_name} 在白名单中，受保护',
                'risk_level': RiskLevel.SAFE.value,
                'risk_score': 0,
                'confidence': 1.0,
                'tags': ['白名单', '受保护'],
                'recommendation': '保留',
                'cached': False,
            }

        # === 第二层: 规则引擎评估 ===
        rule_result = self.rule_engine.evaluate_path(path, size, None, os.path.isfile(path))
        rule_level_str = rule_result.value if hasattr(rule_result, 'value') else str(rule_result).lower()

        if rule_level_str in ['safe', 'dangerous']:
            # 规则确定的结果
            if rule_level_str == 'safe':
                result = {
                    'method': AssessmentMethod.RULE.value,
                    'source': '规则匹配',
                    'details': '规则判定为安全缓存',
                    'risk_level': RiskLevel.SAFE.value,
                    'risk_score': 20,
                    'confidence': 0.85,
                    'tags': ['规则评估', '可清理'],
                    'rule_matches': 1,
                    'recommendation': '可以清理',
                }
            elif rule_level_str == 'dangerous':
                result = {
                    'method': AssessmentMethod.RULE.value,
                    'source': '规则匹配',
                    'details': '规则判定为危险',
                    'risk_level': RiskLevel.DANGEROUS.value,
                    'risk_score': 85,
                    'confidence': 0.75,
                    'tags': ['规则评估', '危险'],
                    'rule_matches': 1,
                    'recommendation': '建议保留',
                }

            # 规则确定的就不需要AI评估了
            return result

        # 计算缓存键
        cache_key = hashlib.md5((path + file_name + str(size)).encode()).hexdigest()

        # 转换规则结果为字符串表示
        rule_level_str = rule_result.value if hasattr(rule_result, 'value') else str(rule_result).lower()

        # 如果AI未启用，直接用规则引擎结果
        if not self.ai_enhancer.is_enabled():
            result['method'] = AssessmentMethod.RULE.value
            result['source'] = '规则引擎评估'
            result['cache_key'] = cache_key

            # 根据风险等级设置分数
            if rule_level_str == 'safe':
                result['risk_level'] = RiskLevel.SAFE.value
                result['risk_score'] = 20
                result['confidence'] = 0.85
                result['recommendation'] = '可以清理'
                result['tags'] = ['规则评估']
            elif rule_level_str == 'dangerous':
                result['risk_level'] = RiskLevel.DANGEROUS.value
                result['risk_score'] = 85
                result['confidence'] = 0.75
                result['recommendation'] = '建议保留'
                result['tags'] = ['规则评估', '危险']
            else:  # suspicious
                result['risk_level'] = RiskLevel.SUSPICIOUS.value
                result['risk_score'] = 50
                result['confidence'] = 0.5
                result['recommendation'] = get_default_recommendation(RiskLevel.SUSPICIOUS.value, AssessmentMethod.RULE.value)
                result['tags'] = ['规则评估']
            return result

        # === 第三层: AI评估 ===
        # 尝试从缓存获取
        from core.annotation_storage import AnnotationStorage
        storage = AnnotationStorage()

        cached_annotation = storage.get_annotation(path)
        if cached_annotation and cached_annotation.assessment_method == AssessmentMethod.AI.value:
            # 使用缓存的AI评估结果
            # 检查缓存是否过期 (7天)
            import datetime as dt
            cache_age = (dt.datetime.now() - dt.datetime.fromisoformat(cached_annotation.created_at)).days
            if cache_age < 7:
                return {
                    'method': AssessmentMethod.AI.value,
                    'source': 'AI缓存',
                    'details': cached_annotation.annotation_note,
                    'risk_level': cached_annotation.risk_level,
                    'risk_score': cached_annotation.risk_score,
                    'confidence': cached_annotation.confidence,
                    'tags': ['AI', '缓存'],
                    'recommendation': cached_annotation.recommendation,
                    'cached': True,
                    'cache_key': cache_key,
                    'ai_confidence': cached_annotation.ai_confidence,
                }

        # 调用AI分类
        ai_result = self._call_ai_classification(path, file_name, file_ext, size, scan_source)

        if ai_result:
            ai_result['cache_key'] = cache_key

            # 结合规则和AI结果
            # 如果规则认为是安全的，偏向安全；如果规则认为是危险的，保持危险
            if rule_level_str == 'dangerous':
                # 规则认为是危险，保持危险
                ai_result['risk_score'] = max(ai_result['risk_score'], 70)
            elif rule_level_str == 'safe':
                # 规则认为是安全，略微降低AI风险分数
                ai_result['risk_score'] = min(ai_result['risk_score'], 40)
                if ai_result['risk_level'] != 'safe':
                    # 如果AI认为危险但规则认为安全，保守处理为疑似
                    ai_result['risk_level'] = 'suspicious'
                    ai_result['confidence'] = 0.6

            result = ai_result

        else:
            # AI评估失败，使用规则引擎结果
            result['method'] = AssessmentMethod.RULE.value
            result['source'] = '规则引擎评估(AI调用失败)'
            result['cache_key'] = cache_key
            result['details'] = 'AI调用失败，使用规则引擎结果'

            # 根据风险等级设置
            if rule_level_str == 'safe':
                result['risk_level'] = RiskLevel.SAFE.value
                result['risk_score'] = 20
                result['confidence'] = 0.85
                result['recommendation'] = '可以清理'
            elif rule_level_str == 'dangerous':
                result['risk_level'] = RiskLevel.DANGEROUS.value
                result['risk_score'] = 85
                result['confidence'] = 0.75
                result['recommendation'] = '建议保留'
            else:  # suspicious
                result['risk_level'] = RiskLevel.SUSPICIOUS.value
                result['risk_score'] = 50
                result['confidence'] = 0.5
                result['recommendation'] = get_default_recommendation(RiskLevel.SUSPICIOUS.value, AssessmentMethod.RULE.value)
            result['tags'] = ['规则评估', 'AI失败']

        return result

        return result

    def _call_ai_classification(self, path: str, file_name: str, file_ext: str,
                               size: int, scan_source: str) -> Optional[Dict[str, Any]]:
        """调用AI进行文件分类

        Returns:
            AI评估结果或None
        """
        try:
            from core.ai_client import AIClient, AIConfig
            from .config_manager import get_config_manager

            config_mgr = get_config_manager()
            ai_config = config_mgr.get_ai_config()
            api_url = ai_config['api_url']
            api_key = ai_config['api_key']
            ai_model = ai_config['api_model']
            ai_enabled = ai_config['enabled']

            if not ai_enabled or not api_url or not api_key:
                logger.debug("AI未启用或配置不完整")
                return None

            # 构建AI提示词
            prompt = self._build_ai_prompt(path, file_name, file_ext, size, scan_source)

            # 调用AI
            ai_config_obj = AIConfig(api_url=api_url, api_key=api_key, model=ai_model)
            ai_client = AIClient(ai_config_obj)

            # 调用API
            response = ai_client.classify_folder_risk(
                file_name, path, scan_source,
                f"{size / 1024:.1f} KB" if size > 0 else "未知"
            )

            if not response[0]:  # success
                logger.error(f"AI评估失败: {response[2]}")
                return None

            risk_str, reason, confidence = response[1], response[2], response[3]

            # 转换风险等级
            risk_map = {'安全': RiskLevel.SAFE.value, '疑似': RiskLevel.SUSPICIOUS.value, '危险': RiskLevel.DANGEROUS.value}
            risk_level = risk_map.get(risk_str, RiskLevel.SUSPICIOUS.value)

            # 计算风险分数
            score_map = {'安全': 20, '疑似': 50, '危险': 80}
            risk_score = score_map.get(risk_str, 50)

            # 生成标签
            tags = ['AI评估']
            if confidence > 0.8:
                tags.append('高置信度')
            elif confidence > 0.5:
                tags.append('中置信度')

            return {
                'method': AssessmentMethod.AI.value,
                'source': f'AI({risk_str})',
                'details': reason,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'confidence': confidence,
                'tags': tags,
                'recommendation': get_default_recommendation(risk_level, AssessmentMethod.AI.value),
                'ai_confidence': confidence,
            }

        except Exception as e:
            logger.error(f"AI分类调用失败: {e}")
            return None

    def _build_ai_prompt(self, path: str, file_name: str, file_ext: str,
                         size: int, scan_source: str) -> str:
        """构建AI提示词"""
        path_simple = os.path.dirname(path)
        size_desc = f"{size / 1024:.1f} KB" if size > 0 else "未知"

        # 根据扫描类型调整提示词
        if scan_source == 'system':
            return f"""你是一个文件安全专家。请评估以下 Windows 系统路径的安全性，指导用户是否可以安全删除。

## 文件信息
- 路径: {path}
- 文件名: {file_name}
- 路径类型: {path_simple}
- 文件大小: {size_desc}

## 判断标准
- **安全可以删除**: 临时文件、缓存、日志、预取文件
- **危险建议保留**: 系统配置、用户数据、重要程序文件

请严格按照以下JSON格式输出:
{{
    "risk_level": "安全/疑似/危险",
    "confidence": 0.0-1.0 (置信度),
    "reason": "评估理由(50字以内)"
}}
"""
        elif scan_source == 'appdata':
            location = 'Roaming' if 'Roaming' in path else ('Local' if 'Local' in path else 'LocalLow')

            return f"""你是一个应用数据安全专家。请评估以下 AppData 路径的安全性，这是用户应用的数据目录。

## 文件信息
- 路径: {path}
- 文件名: {file_name}
- 目录类型: {location} (Roaming/Local/LocalLow)
- 文件大小: {size_desc}

## 判断标准
- **安全可以删除**: 缓存 (cache, temp, tmp), 日志, 备份
- **疑似需确认**: 数据文件 (data, save, db, config), 配置
- **危险建议保留**: 同步配置, 个人设置, 重要数据

## 常见应用特征
- 浏览器Roaming中的缓存文件夹通常是安全的
- Local中的应用数据通常不建议删除

请严格按照以下JSON格式输出:
{{
    "risk_level": "安全/疑似/危险",
    "confidence": 0.0-1.0 (置信度),
    "reason": "评估理由(50字以内)"
}}
"""
        else:  # custom
            full_path = path
            size_desc = f"{size / 1024:.1f} KB" if size > 0 else "未知"

            return f"""你是一个文件安全专家。请评估以下用户指定的路径的安全性，指导用户是否可以安全删除。

## 文件信息
- 完整路径: {full_path}
- 文件名: {file_name}
- 文件后缀: {file_ext}
- 文件大小: {size_desc}

## 判断标准
- **安全可以删除**: 临时文件、缓存、日志、明确命名的临时目录
- **疑似需确认**: 不明确的文件名、数据文件、配置文件
- **危险建议保留**: 重要程序、用户数据、系统文件

## 路径分析要点
- 文件/文件夹名的语义
- 路径所在位置
- 与已知应用的关联

请严格按照以下JSON格式输出:
{{
    "risk_level": "安全/疑似/危险",
    "confidence": 0.0-1.0 (置信度),
    "reason": "评估理由(50字以内)"
}}
"""

    def generate_batch_annotations(self, items: List[Dict[str, Any]], scan_source: str) -> List[ScanAnnotation]:
        """批量生成批注

        Args:
            items: 扫描项列表
            scan_source: 扫描来源

        Returns:
            批注列表
        """
        annotations = []

        for item in items:
            try:
                anno = self.generate_annotation(item, scan_source)
                annotations.append(anno)
            except Exception as e:
                logger.error(f"生成批注失败: {e} - {item.get('path', 'unknown')}")

        return annotations
