"""
AI 智能增强模块
将 AI 集成到扫描和清理流程中
"""
from typing import Optional
from .ai_client import AIClient, AIConfig
from .rule_engine import RiskLevel
from .models import ScanItem
from .config_manager import get_config_manager


class AIEnhancer:
    """
    AI 智能增强器
    使用 AI 对文件/文件夹进行风险评估和描述
    """

    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        初始化 AI 增强器

        Args:
            ai_client: AI 客户端实例，如果为 None 则使用默认配置
        """
        if ai_client is None:
            # 从配置管理器读取配置
            config_mgr = get_config_manager()
            ai_cfg = config_mgr.get_ai_config()
            self.ai_client = AIClient(AIConfig(
                api_url=ai_cfg['api_url'],
                api_key=ai_cfg['api_key'],
                model=ai_cfg['api_model']
            ))
        else:
            self.ai_client = ai_client

    def is_enabled(self) -> bool:
        """检查 AI 是否已启用（有有效的 API 密钥）

        Returns:
            bool: AI 是否可用
        """
        config = self.ai_client.config
        return bool(config.api_key)

    def assess_and_describe_with_ai(self, item: ScanItem) -> tuple[str, str, bool]:
        """
        使用 AI 评估文件/文件夹的风险并生成描述

        Args:
            item: 要评估的扫描项

        Returns:
            (risk_level, description, ai_used) - 风险等级、描述和是否使用了AI
        """
        # AI 未启用，返回原始值
        if not self.is_enabled():
            return item.risk_level, item.description, False

        try:
            # 准备提示词
            prompt = self._build_risk_assessment_prompt(item)
            messages = [{'role': 'user', 'content': prompt}]

            # 调用 AI - 返回 (success, result)
            success, response = self.ai_client.chat(messages)

            if success:
                # 解析 AI 响应
                risk_level, description = self._parse_risk_response(response)
                if risk_level:
                    return risk_level, description, True
                else:
                    # 解析失败，返回原始值
                    return item.risk_level, item.description, False
            else:
                # AI 调用失败，返回原始值
                print(f'AI 调用失败: {response}')
                return item.risk_level, item.description, False

        except Exception as e:
            print(f'AI 风险评估失败: {e}')
            # 回退到规则引擎结果
            return item.risk_level, item.description, False

    def get_ai_description(self, item: ScanItem) -> tuple[str, bool]:
        """使用 AI 获取文件/文件夹的详细描述

        Args:
            item: 要描述的扫描项

        Returns:
            (description, ai_used) - 描述和是否使用了AI
        """
        if not self.is_enabled():
            return item.description, False

        try:
            prompt = self._build_description_prompt(item)
            messages = [{'role': 'user', 'content': prompt}]
            success, response = self.ai_client.chat(messages)

            if success:
                # 尝试从JSON中提取description
                try:
                    import json
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
                        desc = data.get("description", response)
                        return desc.strip(), True
                except Exception:
                    pass

                return response.strip(), True
            else:
                return item.description, False

        except Exception as e:
            print(f'AI 描述生成失败: {e}')
            return item.description, False

    def _build_risk_assessment_prompt(self, item: ScanItem) -> str:
        """构建风险评估提示词"""
        prompt = f"""# 角色：Windows AppData 安全评估专家

## 任务
评估以下 AppData 文件夹的安全性，将其分为三个风险等级。

## 评估标准

### 安全 - 可直接删除
1. 明确的缓存文件夹（cache, Cache, GPUCache, Code Cache）
2. 临时文件夹（temp, Temp, tmp）
3. 预取数据文件夹（Prefetch）
4. 日志文件夹（logs, Logs）
5. 下载缓存文件夹（Downloads）
6. 缩略图缓存（thumbnails, cache2, Thumbnail）

### 疑似 - 需要用户确认
1. 配置文件文件夹（config, settings）
2. 用户数据文件夹（UserData, data）
3. 不确定用途的文件夹
4. 应用程序核心文件夹（非系统关键）

### 危险 - 不建议删除
1. 系统关键数据
2. 用户重要数据
3. 删除会导致应用无法启动的核心目录
4. 数据库存储目录

## 文件夹信息
路径: {item.path}
类型: {item.item_type}
大小: {self._format_size(item.size)}

## 输出要求
请按照以下 JSON 格式输出（不要包含其他文字，只输出JSON）:
{{"risk_level": "safe"|"suspicious"|"dangerous", "reason": "简要说明原因（20字以内）"}}"""
        return prompt

    def _build_description_prompt(self, item: ScanItem) -> str:
        """构建描述生成提示词"""
        # 针对 AppData 的定制化提示词
        if item.item_type == 'directory':
            prompt = f"""# 角色：Windows AppData 分析专家
## 任务
分析以下 AppData 文件夹信息并给出简要描述。
## 要求
- 从文件夹路径推断所属软件名称
- 判断该文件夹的数据类型（缓存/配置/用户数据/日志等）
- 说明该文件夹的大致用途
## 文件夹信息
路径: {item.path}
## 输出格式
请按照以下 JSON 格式输出（只输出 JSON，不要其他文字）:
{{"description": "软件名称 - 数据类型"}}"""
        else:
            prompt = f"""# 角色：Windows 文件分析专家
## 任务
分析以下文件的用途。
## 文件信息
路径: {item.path}
## 输出格式
请按照以下 JSON 格式输出（只输出 JSON，不要其他文字）:
{{"description": "文件用途描述"}}"""
        return prompt

    def _parse_risk_response(self, response: str) -> tuple[str, str]:
        """解析 AI 的风险等级响应

        Args:
            response: AI 响应文本

        Returns:
            (risk_level, description) - 风险等级和原因
        """
        response_lower = response.lower().strip()

        # 尝试解析 JSON
        try:
            import json
            # 尝试提取 JSON 代码块
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

            # 尝试解析 JSON
            if json_str.startswith('{'):
                data = json.loads(json_str)
                risk_level_str = data.get("risk_level", "")
                reason = data.get("reason", "")

                # 标准化风险等级
                if "safe" in risk_level_str.lower():
                    risk_level = "safe"
                elif "suspicious" in risk_level_str.lower() or "可疑" in risk_level_str:
                    risk_level = "suspicious"
                elif "dangerous" in risk_level_str.lower() or "危险" in risk_level_str:
                    risk_level = "dangerous"
                else:
                    risk_level = "suspicious"

                return risk_level, reason

        except Exception:
            pass

        # 回退到简单文本匹配
        if 'danger' in response_lower or '危险' in response:
            return "dangerous", "AI评估为危险"
        elif 'suspicious' in response_lower or '疑似' in response_lower:
            return "suspicious", "AI评估为疑似"
        elif 'safe' in response_lower or '安全' in response_lower:
            return "safe", "AI评估为安全"

        # 默认返回疑似
        return "suspicious", "AI评估结果"

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化大小"""
        if size < 1024:
            return str(size)
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        elif size < 1024 * 1024 * 1024:
            return f'{size / (1024 * 1024):.1f} MB'
        else:
            return f'{size / (1024 * 1024 * 1024):.1f} GB'


def get_ai_enhancer(ai_config: Optional[AIConfig] = None) -> AIEnhancer:
    """
    获取 AI 增强器实例（总是从配置管理器读取最新配置）

    Args:
        ai_config: AI 配置（此参数已废弃，保留用于兼容性），如果提供会使用此配置

    Returns:
        AIEnhancer: AI 增强器实例（每次都是最新配置）
    """
    # 每次都从配置管理器读取最新配置
    config_mgr = get_config_manager()
    ai_cfg = config_mgr.get_ai_config()

    # 如果提供了 ai_config，使用它（兼容性）
    if ai_config is not None:
        ai_config_to_use = ai_config
    else:
        ai_config_to_use = AIConfig(
            api_url=ai_cfg['api_url'],
            api_key=ai_cfg['api_key'],
            model=ai_cfg['api_model']
        )

    return AIEnhancer(AIClient(ai_config_to_use))
