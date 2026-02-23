# -*- coding: utf-8 -*-
"""
文件系统工具实现

提供 Read, Write, Ls, Glob, Grep 等文件系统操作工具
"""
import os
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base import ToolBase
from utils.logger import get_logger

logger = get_logger(__name__)


class ReadTool(ToolBase):
    """读取文件内容工具"""

    NAME = "read"
    DESCRIPTION = "读取文件内容或列出目录内容。支持目录递归列举、文件 offset/limit 分页读取。"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件或目录路径"
                },
                "offset": {
                    "type": "integer",
                    "description": "读取起始行号（从0开始，默认0）"
                },
                "limit": {
                    "type": "integer",
                    "description": "最大读取行数（默认全部）"
                }
            },
            "required": ["path"]
        }

    def execute(self, input_json: Dict[str, Any], workspace: Optional[str] = None) -> str:
        path = input_json.get("path", "")
        offset = input_json.get("offset", 0)
        limit = input_json.get("limit", 0)

        # 解析路径
        if workspace and not os.path.isabs(path):
            full_path = os.path.join(workspace, path)
        else:
            full_path = path

        try:
            if os.path.isdir(full_path):
                return self._list_directory(full_path)
            elif os.path.isfile(full_path):
                return self._read_file(full_path, offset, limit)
            else:
                return f"路径不存在: {full_path}"
        except Exception as e:
            logger.error(f"[ReadTool] 读取失败: {full_path}, 错误: {e}")
            return f"读取失败: {str(e)}"

    def _list_directory(self, dir_path: str) -> str:
        """列出目录内容"""
        try:
            entries = []
            for entry in os.listdir(dir_path):
                entry_path = os.path.join(dir_path, entry)
                try:
                    stat = os.stat(entry_path)
                    size = stat.st_size
                    is_dir = os.path.isdir(entry_path)

                    # 目录用 / 标识
                    display_name = entry + "/" if is_dir else entry

                    entries.append({
                        "name": display_name,
                        "path": entry_path,
                        "size": size,
                        "is_directory": is_dir
                    })
                except OSError:
                    # 忽略无法访问的文件
                    pass

            # 转换为 JSON 格式
            return json.dumps({
                "type": "directory",
                "path": dir_path,
                "entries": entries,
                "count": len(entries)
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"列出目录失败: {str(e)}"

    def _read_file(self, file_path: str, offset: int, limit: int) -> str:
        """读取文件内容"""
        try:
            # 尝试读取文本文件
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # 应用 offset 和 limit
            if offset > 0:
                lines = lines[offset:]

            if limit > 0:
                lines = lines[:limit]

            content = "".join(lines)

            return json.dumps({
                "type": "file",
                "path": file_path,
                "content": content,
                "lines": len(lines),
                "line_offset": offset
            }, ensure_ascii=False)

        except UnicodeDecodeError:
            try:
                # 尝试二进制读取
                with open(file_path, "rb") as f:
                    data = f.read()

                return json.dumps({
                    "type": "binary",
                    "path": file_path,
                    "size": len(data),
                    "preview": data[:100].hex()
                }, ensure_ascii=False)
            except Exception as e:
                return f"二进制读取也失败: {str(e)}"


class WriteTool(ToolBase):
    """写入文件内容工具"""

    NAME = "write"
    DESCRIPTION = "创建新文件或覆盖现有文件内容。"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "文件内容"
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "是否自动创建父目录（默认false）"
                }
            },
            "required": ["path", "content"]
        }

    def execute(self, input_json: Dict[str, Any], workspace: Optional[str] = None) -> str:
        path = input_json.get("path", "")
        content = input_json.get("content", "")
        create_dirs = input_json.get("create_dirs", False)

        # 解析路径
        if workspace and not os.path.isabs(path):
            full_path = os.path.join(workspace, path)
        else:
            full_path = path

        try:
            # 如果需要创建目录
            if create_dirs:
                parent_dir = os.path.dirname(full_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)

            # 写入文件
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"[WriteTool] 写入文件: {full_path}, 大小: {len(content)} 字节")
            return f"成功写入文件: {full_path}"

        except Exception as e:
            logger.error(f"[WriteTool] 写入失败: {full_path}, 错误: {e}")
            return f"写入失败: {str(e)}"


class EditTool(ToolBase):
    """编辑文件内容工具（字符串替换）"""

    NAME = "edit"
    DESCRIPTION = "在现有文件中精确替换字符串内容。"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "old_str": {
                    "type": "string",
                    "description": "要替换的旧字符串"
                },
                "new_str": {
                    "type": "string",
                    "description": "新字符串内容"
                }
            },
            "required": ["path", "old_str", "new_str"]
        }

    def execute(self, input_json: Dict[str, Any], workspace: Optional[str] = None) -> str:
        path = input_json.get("path", "")
        old_str = input_json.get("old_str", "")
        new_str = input_json.get("new_str", "")

        # 解析路径
        if workspace and not os.path.isabs(path):
            full_path = os.path.join(workspace, path)
        else:
            full_path = path

        try:
            # 读取文件
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查是否有旧字符串
            if old_str not in content:
                return f"未找到要替换的字符串: {old_str[:50]}..."

            # 替换
            new_content = content.replace(old_str, new_str)

            # 写回文件
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # 统计替换次数
            count = content.count(old_str)

            logger.info(f"[EditTool] 编辑文件: {full_path}, 替换 {count} 次")
            return f"成功编辑文件: {full_path}, 替换次数: {count}"

        except Exception as e:
            logger.error(f"[EditTool] 编辑失败: {full_path}, 错误: {e}")
            return f"编辑失败: {str(e)}"


class GlobTool(ToolBase):
    """文件模式搜索工具"""

    NAME = "glob"
    DESCRIPTION = "使用模式匹配搜索文件。支持 **/* 递归搜索。"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "文件匹配模式 (支持 **/* 递归)"
                },
                "path": {
                    "type": "string",
                    "description": "搜索起始路径（默认当前目录）"
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回结果数（默认100）"
                }
            },
            "required": ["pattern"]
        }

    def execute(self, input_json: Dict[str, Any], workspace: Optional[str] = None) -> str:
        pattern = input_json.get("pattern", "")
        search_path = input_json.get("path", workspace or ".")
        limit = input_json.get("limit", 100)

        try:
            # 解析路径
            if workspace and not os.path.isabs(search_path):
                full_path = os.path.join(workspace, search_path)
            else:
                full_path = search_path

            # 使用 pathlib glob
            path_obj = Path(full_path)
            results = []

            # 搜索文件
            for file_path in path_obj.glob(pattern):
                if file_path.is_file():
                    results.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size
                    })

                    if limit > 0 and len(results) >= limit:
                        break

            # 按修改时间排序（如果可能）
            # 这里简化处理，直接返回

            return json.dumps({
                "pattern": pattern,
                "search_path": full_path,
                "count": len(results),
                "results": results
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"[GlobTool] 搜索失败: {pattern}, 错误: {e}")
            return f"搜索失败: {str(e)}"


class GrepTool(ToolBase):
    """内容搜索工具"""

    NAME = "grep"
    DESCRIPTION = "在文件中搜索包含指定内容的文本。支持正则表达式。"

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "搜索模式（支持正则表达式）"
                },
                "path": {
                    "type": "string",
                    "description": "文件或目录路径"
                },
                "include": {
                    "type": "string",
                    "description": "文件包含模式（如 *.py）"
                },
                "context": {
                    "type": "integer",
                    "description": "显示匹配行前后的行数（默认0）"
                }
            },
            "required": ["pattern", "path"]
        }

    def execute(self, input_json: Dict[str, Any], workspace: Optional[str] = None) -> str:
        pattern = input_json.get("pattern", "")
        search_path = input_json.get("path", "")
        include = input_json.get("include", "")
        context = input_json.get("context", 0)

        try:
            # 解析路径
            if workspace and not os.path.isabs(search_path):
                full_path = os.path.join(workspace, search_path)
            else:
                full_path = search_path

            # 编译正则表达式
            try:
                regex = re.compile(pattern)
            except re.error as e:
                return f"正则表达式错误: {str(e)}"

            results = []

            def search_file(file_path: Path):
                """搜索单个文件"""
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for i, line in enumerate(lines):
                        if regex.search(line):
                            # 获取上下文
                            start = max(0, i - context)
                            end = min(len(lines), i + context + 1)

                            context_lines = []
                            for j in range(start, end):
                                prefix = ">" if j == i else " "
                                context_lines.append(f"{prefix}{j+1:4d}: {lines[j].rstrip()}")

                            results.append({
                                "file": str(file_path),
                                "line_number": i + 1,
                                "line": line.rstrip(),
                                "context": context_lines
                            })
                except (OSError, UnicodeDecodeError):
                    pass

            path_obj = Path(full_path)

            if path_obj.is_file():
                search_file(path_obj)
            elif path_obj.is_dir():
                # 搜索目录中的文件
                for file_path in path_obj.rglob("*"):
                    if file_path.is_file():
                        # 检查 include 模式
                        if include:
                            if not file_path.match(include):
                                continue
                        search_file(file_path)

            return json.dumps({
                "pattern": pattern,
                "path": full_path,
                "matches": len(results),
                "results": results
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"[GrepTool] 搜索失败: {pattern}, 错误: {e}")
            return f"搜索失败: {str(e)}"


# 注册工具
from . import register_tool

register_tool(ReadTool)
register_tool(WriteTool)
register_tool(EditTool)
register_tool(GlobTool)
register_tool(GrepTool)

logger.info(f"[FILE_TOOLS] 已注册文件系统工具: Read, Write, Edit, Glob, Grep")
