"""
白名单管理模块
保护用户指定的文件/文件夹不被清理
"""
import os
import json
from typing import Set, List, Tuple


class Whitelist:
    """
    白名单管理类
    支持精确路径匹配和模式匹配
    """

    def __init__(self, config_path: str = 'data/whitelist.json'):
        """
        初始化白名单

        Args:
            config_path: 白名单配置文件路径
        """
        self.config_path = config_path
        self.paths: Set[str] = set()  # 精确路径匹配
        self.patterns: Set[str] = set()  # 模式匹配
        self._load()

    def _load(self):
        """从文件加载白名单"""
        if not os.path.exists(self.config_path):
            # 创建默认配置
            self._save()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.paths = set(data.get('paths', []))
                self.patterns = set(data.get('patterns', []))
        except json.JSONDecodeError as e:
            print(f'白名单配置文件格式错误: {e}')
            # 重置为空
            self.paths = set()
            self.patterns = set()
        except Exception as e:
            print(f'加载白名单失败: {e}')
            self.paths = set()
            self.patterns = set()

    def _save(self):
        """保存白名单到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            data = {
                'paths': list(self.paths),
                'patterns': list(self.patterns)
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'保存白名单失败: {e}')

    def add_path(self, path: str) -> bool:
        """
        添加路径到白名单

        Args:
            path: 要添加的路径

        Returns:
            bool: 是否添加成功（不在白名单中）
        """
        # 规范化路径
        normalized = self._normalize_path(path)

        if normalized in self.paths:
            return False

        self.paths.add(normalized)
        self._save()
        return True

    def add_pattern(self, pattern: str) -> bool:
        """
        添加模式到白名单

        Args:
            pattern: 要添加的模式（支持通配符 * 和 ?）

        Returns:
            bool: 是否添加成功（不在白名单中）
        """
        if pattern in self.patterns:
            return False

        self.patterns.add(pattern)
        self._save()
        return True

    def remove_path(self, path: str) -> bool:
        """
        从白名单移除路径

        Args:
            path: 要移除的路径

        Returns:
            bool: 是否移除成功（在白名单中）
        """
        normalized = self._normalize_path(path)

        if normalized not in self.paths:
            return False

        self.paths.remove(normalized)
        self._save()
        return True

    def remove_pattern(self, pattern: str) -> bool:
        """
        从白名单移除模式

        Args:
            pattern: 要移除的模式

        Returns:
            bool: 是否移除成功（在白名单中）
        """
        if pattern not in self.patterns:
            return False

        self.patterns.remove(pattern)
        self._save()
        return True

    def is_safe(self, path: str) -> bool:
        """
        检查路径是否在白名单中

        Args:
            path: 要检查的路径

        Returns:
            bool: 是否在白名单中
        """
        # 1. 精确匹配
        normalized = self._normalize_path(path)

        # 检查精确路径匹配
        for safe_path in self.paths:
            # 检查是否是子路径
            if self._is_subpath(normalized, safe_path):
                return True
            # 检查白名单路径是否是当前路径的子路径
            if self._is_subpath(safe_path, normalized):
                return True

        # 2. 模式匹配
        for pattern in self.patterns:
            if self._matches_pattern(normalized, pattern):
                return True

        return False

    def is_protected(self, path: str) -> bool:
        """
        检查路径是否受白名单保护（is_safe 的别名）

        Args:
            path: 要检查的路径

        Returns:
            bool: 是否在白名单中
        """
        return self.is_safe(path)

    def is_whitelisted(self, path: str) -> bool:
        """
        检查路径是否在白名单中（is_safe 的别名）

        Args:
            path: 要检查的路径

        Returns:
            bool: 是否在白名单中
        """
        return self.is_safe(path)

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        规范化路径（统一分隔符和大小写）

        Args:
            path: 原始路径

        Returns:
            str: 规范化后的路径
        """
        # 替换反斜杠为正斜杠
        path = path.replace('\\', '/')

        # 去除尾部斜杠
        if path.endswith('/'):
            path = path.rstrip('/')

        # 转换为小写（Windows 不区分大小写）
        return path.lower()

    @staticmethod
    def _is_subpath(path: str, parent: str) -> bool:
        """
        检查一个路径是否是另一个路径的子路径

        Args:
            path: 子路径
            parent: 父路径

        Returns:
            bool: path 是否是 parent 的子路径
        """
        # 规范化路径
        path = path.replace('\\', '/')
        parent = parent.replace('\\', '/')

        # 添加尾部斜杠以便正确匹配
        if not parent.endswith('/'):
            parent += '/'

        return path.startswith(parent)

    @staticmethod
    def _matches_pattern(path: str, pattern: str) -> bool:
        """
        检查路径是否匹配模式

        支持通配符：* 匹配任意字符（除 /），** 匹配任意字符

        Args:
            path: 要检查的路径
            pattern: 模式字符串

        Returns:
            bool: 是否匹配
        """
        # 简单实现：将通配符模式转换为正则表达式
        import re

        # 转义特殊字符
        regex_pattern = re.escape(pattern)

        # 替换通配符
        # ** 匹配任意字符（包括 /）
        regex_pattern = regex_pattern.replace(r'\*\*', '.*')
        # * 匹配任意字符（除 /）
        regex_pattern = regex_pattern.replace(r'\*', '[^/]*')
        # ? 匹配单个字符（除 /）
        regex_pattern = regex_pattern.replace(r'\?', '[^/]')

        try:
            # 添加开始和结束锚点
            regex_pattern = '^' + regex_pattern + '$'
            return bool(re.match(regex_pattern, path, re.IGNORECASE))
        except re.error:
            return False

    def get_all(self) -> Tuple[List[str], List[str]]:
        """
        获取所有白名单项

        Returns:
            Tuple[List[str], List[str]]: (paths, patterns)
        """
        return sorted(list(self.paths)), sorted(list(self.patterns))

    def clear(self):
        """清空白名单"""
        self.paths.clear()
        self.patterns.clear()
        self._save()

    def is_empty(self) -> bool:
        """检查白名单是否为空"""
        return len(self.paths) == 0 and len(self.patterns) == 0

    def count(self) -> int:
        """返回白名单项目数量"""
        return len(self.paths) + len(self.patterns)

    def get_info(self) -> str:
        """获取白名单信息"""
        path_count = len(self.paths)
        pattern_count = len(self.patterns)
        return f'路径: {path_count}, 模式: {pattern_count}'


# 全局白名单实例（单例模式）
_global_whitelist: Whitelist = None


def get_whitelist() -> Whitelist:
    """
    获取全局白名单实例（单例）

    Returns:
        Whitelist: 白名单实例
    """
    global _global_whitelist
    if _global_whitelist is None:
        _global_whitelist = Whitelist()
    return _global_whitelist
