"""
AI复核功能模块 - 提示词构建器
提供严格的格式化AI评估提示词
"""
from typing import Optional
from core.models import ScanItem
from core.rule_engine import RiskLevel


class PromptBuilder:
    """AI复核提示词构建器"""

    # 系统提示词
    SYSTEM_PROMPT = """# 角色：Windows 文件安全评估专家

你是一个经验丰富的Windows文件系统专家，擅长评估文件/文件夹的删除风险。
你的任务是根据提供的文件信息，准确判断其删除风险。

## 重要规则
1. 必须严格按照要求的JSON格式输出
2. 不要包含任何JSON之外的解释性文字
3. 所有字段必须填写，不可省略
4. 对于不确定的判断，请设置较低的置信度并标记为suspicious
"""

    # 评估标准
    ASSESSMENT_CRITERIA = """## 评估标准

### 🟢 安全 (safe) - 可安全删除
- 明确的缓存文件夹（cache, GPUCache, CodeCache, Code Cache）
- 临时文件夹（temp, tmp）
- 预取数据文件夹（Prefetch）
- 日志文件夹（logs, Logs）
- 缩略图缓存（thumbnails, cache2, Thumbnail）
- 下载缓存文件夹（Downloads）
- 应用卸载残留
- 90天以上未访问的文件

### 🟡 疑似 (suspicious) - 需用户确认
- 配置文件文件夹（config, settings）
- 不确定用途的文件夹
- 可能包含用户数据的目录
- 应用程序核心文件夹（非系统关键）
- 预设文件、偏好设置

### 🔴 危险 (dangerous) - 不建议删除
- 系统关键数据
- 用户重要数据（UserData, data）
- 删除会导致应用无法启动的核心目录
- 数据库存储目录（.db files）
- 登录数据（login data）
- Cookie文件（cookies）
- 可执行程序文件（.exe, .dll）
"""

    def __init__(self, config: Optional[dict] = None):
        """初始化提示词构建器

        Args:
            config: 复核配置
        """
        self.config = config or {}

    def build_assessment_prompt(self, item: ScanItem) -> str:
        """构建评估提示词（基础版）

        Args:
            item: 扫描项

        Returns:
            提示词字符串
        """
        # 格式化文件大小
        size_text = self._format_size(item.size)

        # 原始风险等级
        original_risk_text = self._risk_level_to_text(item.risk_level)

        prompt = f"""{self.SYSTEM_PROMPT}

{self.ASSESSMENT_CRITERIA}

## 文件信息
- 路径: {item.path}
- 类型: {item.item_type}
- 大小: {size_text}
- 原始评级: {original_risk_text}
- 描述: {item.description}

## 输出要求
**必须严格按照以下JSON格式输出，不要包含任何其他文字**：

```json
{{
    "ai_risk": "safe"|"suspicious"|"dangerous",
    "confidence": 0.0-1.0,
    "function_description": "功能描述（30字以内）",
    "software_name": "所属软件（20字以内，未知填\"未知\"）",
    "risk_reason": "风险原因（20字以内）",
    "cleanup_suggestion": "清理建议（25字以内）"
}}
```

如果无法准确判断，confidence请设为<0.5，ai_risk设为suspicious。"""

        return prompt

    def build_retry_prompt(self, item: ScanItem, error_type: str = "format") -> str:
        """构建重试提示词（简化版）

        Args:
            item: 扫描项
            error_type: 错误类型

        Returns:
            简化的提示词字符串
        """
        base_prompt = """# 职责：严格按照JSON格式输出

## 输出格式（必须完全一致）：
```json
{
    "ai_risk": "safe",
    "confidence": 0.8,
    "function_description": "描述",
    "software_name": "软件名",
    "risk_reason": "原因",
    "cleanup_suggestion": "建议"
}
```

## 评估项
路径: {path}
类型: {item_type}
大小: {size}

请直接输出JSON，无需其他说明。"""

        return base_prompt.format(
            path=item.path,
            item_type=item.item_type,
            size=self._format_size(item.size)
        )

    def build_browser_assessment_prompt(self, item: ScanItem) -> str:
        """构建浏览器专用评估提示词

        Args:
            item: 扫描项

        Returns:
            浏览器评估提示词字符串
        """
        size_text = self._format_size(item.size)

        prompt = f"""{self.SYSTEM_PROMPT}

## 浏览器缓存评估标准

### 🟢 安全 (safe) - 可安全删除
- Code Cache（代码缓存）
- GPUCache（GPU缓存）
- Service Worker（服务工作线程缓存）
- Cache Storage（缓存存储）
- IndexedDB（临时数据库）
- Session Storage（会话存储）
- Temp（临时文件）
- Logs（日志文件）

### 🟡 疑似 (suspicious) - 需用户确认
- Preferences（偏好设置）
- Local State（本地状态）

### 🔴 危险 (dangerous) - 不建议删除
- UserData（用户数据，包含书签、历史、扩展）
- Cookies（Cookie文件）
- Login Data（登录数据）
- Web Data（Web数据，存储表单等）
- History（历史记录）
- Extension State（扩展状态）

## 文件信息
- 路径: {item.path}
- 类型: {item.item_type}
- 大小: {size_text}

## 输出要求
```json
{{
    "ai_risk": "safe"|"suspicious"|"dangerous",
    "confidence": 0.0-1.0,
    "function_description": "功能描述（30字以内）",
    "software_name": "所属浏览器（20字以内）",
    "risk_reason": "风险原因（20字以内）",
    "cleanup_suggestion": "清理建议（25字以内）"
}}
```

直接输出JSON，无其他内容。"""

        return prompt

    def build_custom_assessment_prompt(self, item: ScanItem) -> str:
        """构建自定义路径评估提示词

        Args:
            item: 扫描项

        Returns:
            自定义评估提示词字符串
        """
        size_text = self._format_size(item.size)

        prompt = f"""{self.SYSTEM_PROMPT}

## 自定义路径评估标准

### 🟢 安全 (safe) - 可安全删除
- 明确的缓存、临时、日志文件夹
- 以".cache"、".tmp"、".log"结尾的文件
- 90天以上未访问
- 已知卸载软件的残留

### 🟡 疑似 (suspicious) - 需用户确认
- 配置、设置文件
- 数据文件（.dat, .data, .db的可能）
- 不确定用途

### 🔴 危险 (dangerous) - 不建议删除
- 可执行文件（.exe, .bat, .cmd, .ps1）
- 系统关键目录标记（System32, Windows, Program Files）
- 数据库文件（.db, .sqlite, .mdb）
- 用户文档类文件

## 文件信息
- 路径: {item.path}
- 类型: {item.item_type}
- 大小: {size_text}

## 输出要求
```json
{{
    "ai_risk": "safe"|"suspicious"|"dangerous",
    "confidence": 0.0-1.0,
    "function_description": "功能描述（30字以内）",
    "software_name": "所属软件（20字以内，未知填\"未知\"）",
    "risk_reason": "风险原因（20字以内）",
    "cleanup_suggestion": "清理建议（25字以内）"
}}
```

直接输出JSON，无其他内容。"""

        return prompt

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小

        Args:
            size_bytes: 字节数

        Returns:
            格式化后的大小字符串
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    @staticmethod
    def _risk_level_to_text(risk_level: RiskLevel) -> str:
        """将风险等级转换为文本

        Args:
            risk_level: 风险等级

        Returns:
            文本表示
        """
        if risk_level is None:
            return "unknown"
        risk_map = {
            RiskLevel.SAFE: "safe",
            RiskLevel.SUSPICIOUS: "suspicious",
            RiskLevel.DANGEROUS: "dangerous"
        }
        if hasattr(risk_level, 'value'):
            return risk_map.get(risk_level, "unknown")
        return risk_map.get(risk_level, "unknown")


# 便捷函数
def get_prompt_builder(prompt_type: str = "standard") -> PromptBuilder:
    """获取提示词构建器

    Args:
        prompt_type: 提示词类型

    Returns:
        PromptBuilder实例
    """
    builder = PromptBuilder()
    builder.prompt_type = prompt_type
    return builder
