"""
规则引擎模块
用于智能评估文件/文件夹的清理风险等级
"""
import os
import re
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class RiskLevel(Enum):
    """风险等级枚举"""
    SAFE = "safe"          # 安全 - 可直接删除
    SUSPICIOUS = "suspicious"  # 疑似 - 需用户确认
    DANGEROUS = "dangerous"    # 危险 - 不建议删除

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            RiskLevel.SAFE: "安全",
            RiskLevel.SUSPICIOUS: "疑似",
            RiskLevel.DANGEROUS: "危险"
        }
        return names.get(self, self.value)

    @classmethod
    def from_value(cls, value: str) -> 'RiskLevel':
        """从字符串值转换为 RiskLevel"""
        for level in cls:
            if level.value == value:
                return level
        return RiskLevel.SUSPICIOUS  # 默认为疑似

    @classmethod
    def from_string(cls, value: str) -> 'RiskLevel':
        """从字符串转换为 RiskLevel（兼容调用）"""
        return cls.from_value(value)


@dataclass
class Rule:
    """规则定义"""
    name: str
    risk_level: RiskLevel
    description: str
    # 规则条件
    path_patterns: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    folder_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    max_size: Optional[int] = None  # 字节
    min_size: Optional[int] = None  # 字节
    max_age_days: Optional[int] = None  # 最后访问时间（天）
    min_age_days: Optional[int] = None  # 最后访问时间（天）

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'risk_level': self.risk_level.value,
            'description': self.description,
            'path_patterns': self.path_patterns,
            'file_patterns': self.file_patterns,
            'folder_patterns': self.folder_patterns,
            'exclude_patterns': self.exclude_patterns,
            'max_size': self.max_size,
            'min_size': self.min_size,
            'max_age_days': self.max_age_days,
            'min_age_days': self.min_age_days
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Rule':
        """从字典创建 Rule"""
        return cls(
            name=data['name'],
            risk_level=RiskLevel.from_value(data['risk_level']),
            description=data['description'],
            path_patterns=data.get('path_patterns', []),
            file_patterns=data.get('file_patterns', []),
            folder_patterns=data.get('folder_patterns', []),
            exclude_patterns=data.get('exclude_patterns', []),
            max_size=data.get('max_size'),
            min_size=data.get('min_size'),
            max_age_days=data.get('max_age_days'),
            min_age_days=data.get('min_age_days')
        )


class RuleEngine:
    """规则引擎

    根据预定义规则评估文件/文件夹的清理风险等级
    支持三区间分类：安全/疑似/危险
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化规则引擎

        Args:
            config_path: 自定义规则配置文件路径
        """
        self.rules: List[Rule] = []
        self.user_feedback: Dict[str, RiskLevel] = {}
        self.config_path = config_path or 'data/rules.json'

        # 加载规则
        self._load_rules()
        self._load_user_feedback()

    def _load_built_in_rules(self) -> List[Rule]:
        """加载内置规则库

        Returns:
            List[Rule]: 内置规则列表
        """
        return [
            # ============ 安全规则 ============
            Rule(
                name="缓存文件夹",
                risk_level=RiskLevel.SAFE,
                description="常见的缓存文件夹",
                path_patterns=[
                    r'.*\\cache.*', r'.*\\Cache.*',
                    r'.*\\temp.*', r'.*\\Temp.*',
                    r'.*\\tmp.*', r'.*\\Tmp.*',
                    r'.*cache\\.*', r'.*Cache\\.*'
                ],
            ),
            Rule(
                name="日志文件夹",
                risk_level=RiskLevel.SAFE,
                description="日志文件",
                path_patterns=[r'.*\\logs.*', r'.*\\Logs.*', r'.*\\log\\.*'],
                file_patterns=['*.log', '*.txt'],
            ),
            Rule(
                name="预取文件",
                risk_level=RiskLevel.SAFE,
                description="Windows 预取文件，可自动生成",
                path_patterns=[r'.*\\Prefetch\\.*'],
            ),
            Rule(
                name="残留空文件夹",
                risk_level=RiskLevel.SAFE,
                description="小于 1KB 的空文件夹或残留文件夹",
                max_size=1024,
            ),
            Rule(
                name="长期未访问",
                risk_level=RiskLevel.SAFE,
                description="90 天以上未访问的文件",
                max_age_days=90,
            ),
            Rule(
                name="缩略图缓存",
                risk_level=RiskLevel.SAFE,
                description="Windows 缩略图缓存",
                path_patterns=[r'.*\\Thumbnail Cache\\.*', r'.*\\iconcache\\.*'],
            ),
            Rule(
                name="缩略图文件",
                risk_level=RiskLevel.SAFE,
                description="缩略图文件",
                file_patterns=['*.db', '*.thumb', '*.thumbs'],
            ),
            Rule(
                name="临时文件",
                risk_level=RiskLevel.SAFE,
                description="临时文件",
                file_patterns=['*.tmp', '*.temp', '*.bak', '*.old'],
            ),
            Rule(
                name="浏览器缓存",
                risk_level=RiskLevel.SAFE,
                description="浏览器缓存文件夹",
                path_patterns=[
                    r'.*\\Chrome\\.*\\Cache.*',
                    r'.*\\Edge\\.*\\Cache.*',
                    r'.*\\Firefox\\.*\\cache.*',
                    r'.*\\Opera\\.*\\Cache.*'
                ],
            ),
            Rule(
                name="更新缓存",
                risk_level=RiskLevel.SAFE,
                description="Windows 更新缓存",
                path_patterns=[r'.*\\SoftwareDistribution\\Download\\.*'],
            ),

            # ============ 疑似规则 ============
            Rule(
                name="配置文件",
                risk_level=RiskLevel.SUSPICIOUS,
                description="配置文件，需谨慎删除",
                file_patterns=['*.ini', '*.conf', '*.json', '*.xml', '*.yaml', '*.yml'],
                max_size=10240,  # 10KB
            ),
            Rule(
                name="数据文件夹",
                risk_level=RiskLevel.SUSPICIOUS,
                description="可能包含用户数据",
                path_patterns=[
                    r'.*\\data.*', r'.*\\Data.*',
                    r'.*\\user.*', r'.*\\User.*',
                    r'.*\\userdata.*', r'.*\\UserData.*'
                ],
            ),
            Rule(
                name="数据库文件",
                risk_level=RiskLevel.SUSPICIOUS,
                description="可能包含重要数据的数据库文件",
                file_patterns=['*.db', '*.sqlite', '*.sqlite3', '*.mdb'],
                exclude_patterns=[r'.*\\cache.*', r'.*\\Cache.*'],
            ),
            Rule(
                name="中等大小文件",
                risk_level=RiskLevel.SUSPICIOUS,
                description="不确定用途的中等大小文件（1MB-10MB）",
                min_size=1024 * 1024,  # 1MB
                max_size=10 * 1024 * 1024,  # 10MB
            ),
            Rule(
                name="文档文件",
                risk_level=RiskLevel.SUSPICIOUS,
                description="文档文件可能包含重要内容",
                file_patterns=['*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pdf', '*.txt'],
                exclude_patterns=[r'.*\\logs.*', r'.*\\Logs.*'],
            ),

            # ============ 危险规则 ============
            Rule(
                name="系统关键目录",
                risk_level=RiskLevel.DANGEROUS,
                description="系统关键文件，不建议删除",
                path_patterns=[
                    r'.*\\Windows\\System32\\.*',
                    r'.*\\Windows\\System.*',
                    r'.*\\Windows\\SysWOW64\\.*'
                ],
            ),
            Rule(
                name="系统引导文件",
                risk_level=RiskLevel.DANGEROUS,
                description="系统引导和启动相关文件",
                path_patterns=[r'.*\\boot.*', r'.*\\Boot.*', r'.*\\bootmgr.*'],
            ),
            Rule(
                name="系统配置",
                risk_level=RiskLevel.DANGEROUS,
                description="包含 config、settings 等关键词的文件",
                path_patterns=[r'.*\\config.*', r'.*\\settings.*', r'.*\\Config.*'],
                file_patterns=['*.cfg', '*.config', '*.settings'],
            ),
            Rule(
                name="程序文件",
                risk_level=RiskLevel.DANGEROUS,
                description="可执行文件和程序",
                file_patterns=['*.exe', '*.dll', '*.sys', '*.bat', '*.cmd', '*.ps1'],
            ),
            Rule(
                name="驱动程序",
                risk_level=RiskLevel.DANGEROUS,
                description="系统驱动程序",
                path_patterns=[r'.*\\drivers\\.*', r'.*\\DriverStore\\.*'],
            ),
            Rule(
                name="大型文件",
                risk_level=RiskLevel.DANGEROUS,
                description="大于 100MB 的大型文件，可能包含重要数据",
                min_size=100 * 1024 * 1024,  # 100MB
            ),
            Rule(
                name="用户文件目录",
                risk_level=RiskLevel.DANGEROUS,
                description="常见的用户文件目录",
                path_patterns=[
                    r'.*\\Documents\\.*',
                    r'.*\\Desktop\\.*',
                    r'.*\\Downloads\\.*',
                    r'.*\\Pictures\\.*',
                    r'.*\\Music\\.*',
                    r'.*\\Videos\\.*'
                ],
            ),
            Rule(
                name="注册表配置",
                risk_level=RiskLevel.DANGEROUS,
                description="注册表配置文件",
                file_patterns=['*.reg'],
            ),
        ]

    def _load_rules(self):
        """加载规则（先加载自定义规则，再加载内置规则）"""
        # 先尝试加载自定义规则
        custom_rules = self._load_custom_rules()
        if custom_rules:
            self.rules.extend(custom_rules)

        # 加载内置规则（只添加不在自定义规则中的）
        built_in_rules = self._load_built_in_rules()
        built_in_names = {r.name for r in custom_rules}

        for rule in built_in_rules:
            if rule.name not in built_in_names:
                self.rules.append(rule)

    def _load_custom_rules(self) -> List[Rule]:
        """加载自定义规则

        Returns:
            List[Rule]: 自定义规则列表
        """
        if not os.path.exists(self.config_path):
            return []

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Rule.from_dict(rule_data) for rule_data in data]
        except Exception as e:
            print(f"加载自定义规则失败: {e}")
            return []

    def _load_user_feedback(self):
        """加载用户反馈学习数据"""
        feedback_path = 'data/user_feedback.json'
        if not os.path.exists(feedback_path):
            return

        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.user_feedback = {
                    path: RiskLevel.from_value(level)
                    for path, level in data.items()
                }
        except Exception as e:
            print(f"加载用户反馈失败: {e}")

    def _save_user_feedback(self):
        """保存用户反馈学习数据"""
        feedback_path = 'data/user_feedback.json'
        try:
            os.makedirs(os.path.dirname(feedback_path), exist_ok=True)
            data = {
                path: level.value
                for path, level in self.user_feedback.items()
            }
            with open(feedback_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存用户反馈失败: {e}")

    def classify(self, path: str, size: int = 0, last_accessed: Optional[datetime] = None,
                 is_file: bool = True) -> RiskLevel:
        """
        根据规则引擎分类文件/文件夹

        Args:
            path: 文件/文件夹路径
            size: 大小（字节）
            last_accessed: 最后访问时间
            is_file: 是否为文件（False 为文件夹）

        Returns:
            RiskLevel: 风险等级
        """
        # 1. 检查用户反馈
        if path in self.user_feedback:
            return self.user_feedback[path]

        # 2. 检查内置规则（按优先级：危险 > 疑似 > 安全）
        # 先检查危险规则
        dangerous_matches = [r for r in self.rules if r.risk_level == RiskLevel.DANGEROUS]
        for rule in dangerous_matches:
            if self._matches_rule(path, size, last_accessed, is_file, rule):
                return RiskLevel.DANGEROUS

        # 检查疑似规则
        suspicious_matches = [r for r in self.rules if r.risk_level == RiskLevel.SUSPICIOUS]
        for rule in suspicious_matches:
            if self._matches_rule(path, size, last_accessed, is_file, rule):
                return RiskLevel.SUSPICIOUS

        # 检查安全规则
        safe_matches = [r for r in self.rules if r.risk_level == RiskLevel.SAFE]
        for rule in safe_matches:
            if self._matches_rule(path, size, last_accessed, is_file, rule):
                return RiskLevel.SAFE

        # 3. 默认为疑似
        return RiskLevel.SUSPICIOUS

    def evaluate_path(self, path: str, size: int = 0, last_accessed=None,
                      is_file: bool = True) -> RiskLevel:
        """
        评估文件/文件夹路径的风险等级（classify 的别名）

        Args:
            path: 文件/文件夹路径
            size: 大小（字节）
            last_accessed: 最后访问时间（datetime 或字符串）
            is_file: 是否为文件（False 为文件夹）

        Returns:
            RiskLevel: 风险等级
        """
        # 转换 last_accessed 为 datetime 对象
        last_accessed_dt = last_accessed
        if last_accessed is not None and isinstance(last_accessed, str):
            try:
                from datetime import datetime
                # 尝试解析不同格式的时间字符串
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        last_accessed_dt = datetime.strptime(last_accessed, fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                last_accessed_dt = None

        return self.classify(path, size, last_accessed_dt, is_file)

    def _matches_rule(self, path: str, size: int, last_accessed: Optional[datetime],
                     is_file: bool, rule: Rule) -> bool:
        """检查文件/文件夹是否匹配规则

        Args:
            path: 文件/文件夹路径
            size: 大小（字节）
            last_accessed: 最后访问时间
            is_file: 是否为文件
            rule: 规则

        Returns:
            bool: 是否匹配
        """
        # 1. 检查排除模式
        if rule.exclude_patterns:
            for pattern in rule.exclude_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return False

        # 2. 检查路径模式
        if rule.path_patterns:
            for pattern in rule.path_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    # 路径匹配后，检查其他条件
                    if self._check_size_condition(size, rule) and \
                       self._check_age_condition(last_accessed, rule):
                        return True
            # 如果有路径模式但都不匹配，返回 False
            return False

        # 3. 检查文件模式
        if rule.file_patterns and is_file:
            file_name = os.path.basename(path)
            for pattern in rule.file_patterns:
                # 将通配符转换为正则表达式
                regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
                if re.match(regex, file_name, re.IGNORECASE):
                    if self._check_size_condition(size, rule) and \
                       self._check_age_condition(last_accessed, rule):
                        return True
            # 如果有文件模式但都不匹配，返回 False
            return False

        # 4. 检查文件夹模式
        if rule.folder_patterns and not is_file:
            folder_name = os.path.basename(path)
            for pattern in rule.folder_patterns:
                regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
                if re.match(regex, folder_name, re.IGNORECASE):
                    if self._check_size_condition(size, rule) and \
                       self._check_age_condition(last_accessed, rule):
                        return True
            return False

        # 5. 如果没有路径/文件/文件夹模式，只检查大小和年龄
        if self._check_size_condition(size, rule) and \
           self._check_age_condition(last_accessed, rule):
            return True

        return False

    def _check_size_condition(self, size: int, rule: Rule) -> bool:
        """检查大小条件

        Args:
            size: 文件大小
            rule: 规则

        Returns:
            bool: 是否满足条件
        """
        # 确保 size 是整数
        try:
            size_int = int(size) if size is not None else 0
        except (ValueError, TypeError):
            size_int = 0

        if rule.max_size is not None and size_int > rule.max_size:
            return False
        if rule.min_size is not None and size_int < rule.min_size:
            return False
        return True

    def _check_age_condition(self, last_accessed: Optional[datetime], rule: Rule) -> bool:
        """检查文件年龄条件

        Args:
            last_accessed: 最后访问时间
            rule: 规则

        Returns:
            bool: 是否满足条件
        """
        if last_accessed is None:
            # 如果没有时间信息，年龄相关规则不匹配
            return rule.max_age_days is None and rule.min_age_days is None

        # 确保是 datetime 对象
        if not isinstance(last_accessed, datetime):
            return rule.max_age_days is None and rule.min_age_days is None

        age = datetime.now() - last_accessed
        age_days = age.total_seconds() / 86400

        if rule.max_age_days is not None and age_days < rule.max_age_days:
            return False
        if rule.min_age_days is not None and age_days > rule.min_age_days:
            return False
        return True

    def add_user_feedback(self, path: str, risk_level: RiskLevel):
        """添加用户反馈，学习用户偏好

        Args:
            path: 文件/文件夹路径
            risk_level: 用户指定的风险等级
        """
        self.user_feedback[path] = risk_level
        self._save_user_feedback()

    def remove_user_feedback(self, path: str):
        """移除用户反馈

        Args:
            path: 文件/文件夹路径
        """
        if path in self.user_feedback:
            del self.user_feedback[path]
            self._save_user_feedback()

    def add_custom_rule(self, rule: Rule):
        """添加自定义规则

        Args:
            rule: 规则
        """
        # 检查是否已存在同名规则
        self.rules = [r for r in self.rules if r.name != rule.name]
        self.rules.append(rule)
        self._save_custom_rules()

    def remove_custom_rule(self, rule_name: str):
        """移除自定义规则

        Args:
            rule_name: 规则名称
        """
        self.rules = [r for r in self.rules if r.name != rule_name]
        self._save_custom_rules()

    def _save_custom_rules(self):
        """保存自定义规则到配置文件"""
        custom_rules = [r for r in self.rules if r.name in {r.name for r in self._load_built_in_rules()}]
        custom_rules = [r for r in self.rules if r not in self._load_built_in_rules()]

        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            data = [rule.to_dict() for rule in custom_rules]
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存自定义规则失败: {e}")

    def get_rules_by_risk_level(self, risk_level: RiskLevel) -> List[Rule]:
        """获取指定风险等级的规则

        Args:
            risk_level: 风险等级

        Returns:
            List[Rule]: 规则列表
        """
        return [r for r in self.rules if r.risk_level == risk_level]

    def get_all_rules(self) -> List[Rule]:
        """获取所有规则

        Returns:
            List[Rule]: 规则列表
        """
        return self.rules.copy()

    # ------------------------------------------------------------------------
    # 批量评估方法 (Phase 2 Day 5 增强)
    # ------------------------------------------------------------------------

    def classify_batch(
        self,
        items: List[tuple[str, int]],
        progress_callback: Optional[Callable] = None
    ) -> List[RiskLevel]:
        """批量分类多个文件/文件夹

        Args:
            items: 文件/文件夹列表，每个元素为 (path, size) 元组
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            List[RiskLevel]: 风险等级列表
        """
        results = []
        total = len(items)

        for i, (path, size) in enumerate(items):
            risk_level = self.classify(path, size)
            results.append(risk_level)

            if progress_callback:
                progress_callback(i + 1, total)

        return results

    def evaluate_paths_batch(
        self,
        paths: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, RiskLevel]:
        """批量评估多个路径

        Args:
            paths: 路径列表
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            Dict[str, RiskLevel]: 路径到风险等级的映射
        """
        results = {}
        total = len(paths)

        for i, path in enumerate(paths):
            # 获取文件大小
            size = 0
            try:
                if os.path.exists(path):
                    size = os.path.getsize(path)
            except Exception:
                pass

            risk_level = self.classify(path, size)
            results[path] = risk_level

            if progress_callback:
                progress_callback(i + 1, total)

        return results

    def filter_by_risk_level(
        self,
        items: List[tuple[str, int]],
        risk_level: RiskLevel
    ) -> List[tuple[str, int]]:
        """根据风险等级过滤项目

        Args:
            items: 文件/文件夹列表
            risk_level: 要过滤的风险等级

        Returns:
            List[tuple[str, int]]: 匹配的项目列表
        """
        matched = []
        for path, size in items:
            if self.classify(path, size) == risk_level:
                matched.append((path, size))
        return matched

    def classify_with_description(
        self,
        path: str,
        size: int = 0,
        last_accessed: Optional[datetime] = None,
        is_file: bool = True
    ) -> tuple[RiskLevel, str]:
        """分类并返回描述信息

        Args:
            path: 文件/文件夹路径
            size: 大小（字节）
            last_accessed: 最后访问时间
            is_file: 是否为文件（False 为文件夹）

        Returns:
            tuple[RiskLevel, str]: (风险等级, 描述)
        """
        risk_level = self.classify(path, size, last_accessed, is_file)

        # 生成描述
        description = self._generate_description(path, risk_level)

        return risk_level, description

    def generate_description(self, path: str, risk_level: RiskLevel) -> str:
        """生成风险描述

        Args:
            path: 文件路径
            risk_level: 风险等级

        Returns:
            str: 描述文本
        """
        return self._generate_description(path, risk_level)

    def _generate_description(self, path: str, risk_level: RiskLevel) -> str:
        """生成风险等级描述

        Args:
            path: 文件路径
            risk_level: 风险等级

        Returns:
            str: 描述文本
        """
        path_lower = path.lower()
        filename = os.path.basename(path)

        if risk_level == RiskLevel.SAFE:
            safe_patterns = {
                'temp': '临时文件',
                'cache': '缓存数据',
                'log': '日志文件',
                'prefetch': '预取数据',
                'thumb': '缩略图缓存',
            }
            for pattern, desc in safe_patterns.items():
                if pattern in filename or pattern in path_lower:
                    return f"{desc}，可安全删除"
            return "安全清理项"

        elif risk_level == RiskLevel.DANGEROUS:
            dangerous_patterns = {
                'windows': 'Windows系统文件',
                'system32': '系统关键目录',
                'driver': '驱动程序',
                'program files': '程序安装目录',
            }
            for pattern, desc in dangerous_patterns.items():
                if pattern in path_lower:
                    return f"{desc}，不建议删除"
            if '.exe' in filename or '.dll' in filename:
                return "可执行程序，不建议删除"
            return "危险清理项"

        else:  # SUSPICIOUS
            suspicious_indicators = {
                'config': '配置文件',
                'settings': '设置文件',
                'data': '数据文件',
                'user': '用户数据',
            }
            for pattern, desc in suspicious_indicators.items():
                if pattern in path_lower:
                    return f"{desc}，需用户确认"
            return "疑似项目，需用户确认"


# 全局规则引擎实例（单例模式）
_global_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """获取全局规则引擎实例（单例）"""
    global _global_rule_engine
    if _global_rule_engine is None:
        _global_rule_engine = RuleEngine()
    return _global_rule_engine
