# -*- coding: utf-8 -*-
"""
工具注册表 - 管理智能体工具

职责:
1. 工具注册和发现
2. 工具验证
3. 工具执行
4. 错误处理和诊断
"""
from typing import Dict, Type, Callable, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import traceback

from .base import ToolBase
from utils.logger import get_logger

logger = get_logger(__name__)


_tools_registry: Dict[str, ToolBase] = {}


def register_tool(tool_class: Type[ToolBase]) -> Type[ToolBase]:
    """工具注册装饰器

    用法:
    @register_tool
    class MyTool(ToolBase):
        NAME = "my_tool"
        DESCRIPTION = "..."

        def execute(self, input_json, workspace):
            ...
    """
    tool_instance = tool_class()
    _tools_registry[tool_instance.NAME] = tool_instance
    return tool_instance


def get_tool(name: str) -> Optional[ToolBase]:
    """获取工具实例

    Args:
        name: 工具名称

    Returns:
        工具实例，如果不存在返回 None
    """
    return _tools_registry.get(name)


def get_all_tools() -> Dict[str, ToolBase]:
    """获取所有已注册的工具

    Returns:
        工具字典
    """
    return _tools_registry.copy()


def get_tools_schema() -> List[Dict[str, Any]]:
    """获取所有工具的 Schema 列表

    Returns:
        工具 Schema 列表 (OpenAI 格式)
    """
    tools = []

    for name, tool in _tools_registry.items():
        try:
            schema = tool.get_schema()
            if schema:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.DESCRIPTION,
                        "parameters": schema
                    }
                })
        except Exception as e:
            logger.warning(f"[TOOLS] 获取工具 {name} schema 失败: {e}")

    return tools


def print_tools_info():
    """打印工具信息（调试用）"""
    tools = get_all_tools()
    logger.info(f"[TOOLS] 已注册 {len(tools)} 个工具:")
    for tool_name, tool in tools.items():
        logger.info(f"  - {tool_name}: {tool.DESCRIPTION}")


# ============ 错误处理和诊断 ============

@dataclass
class ToolExecutionError:
    """工具执行错误详情"""
    tool_name: str
    error_type: str
    error_message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    inputs: Dict[str, Any] = field(default_factory=dict)
    workspace: Optional[str] = None
    stack_trace: str = ""
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "inputs": self.inputs,
            "workspace": self.workspace,
            "suggestions": self.suggestions
        }

    def to_user_friendly_message(self) -> str:
        """生成用户友好的错误消息"""
        message = f"工具 '{self.tool_name}' 执行失败: {self.error_message}\n"

        if self.suggestions:
            message += "\n建议:\n"
            for i, suggestion in enumerate(self.suggestions, 1):
                message += f"  {i}. {suggestion}\n"

        return message


def validate_tool_inputs(tool_name: str, inputs: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """验证工具输入参数

    Args:
        tool_name: 工具名称
        inputs: 输入参数
        schema: 工具 Schema

    Returns:
        错误列表（空列表表示验证通过）
    """
    errors = []

    if not schema:
        return errors

    required_params = schema.get("required", [])
    properties = schema.get("properties", {})

    # 检查必需参数
    for param in required_params:
        if param not in inputs or inputs[param] is None:
            errors.append(f"缺少必需参数: {param}")
        elif inputs[param] == "":
            errors.append(f"参数 '{param}' 的值不能为空")

    # 检查参数类型
    for param_name, param_value in inputs.items():
        if param_name not in properties:
            errors.append(f"未知参数: {param_name}")
            continue

        param_schema = properties[param_name]
        expected_type = param_schema.get("type")

        if expected_type and param_value is not None:
            type_errors = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict
            }

            if expected_type in type_errors:
                expected_py_type = type_errors[expected_type]
                if not isinstance(param_value, expected_py_type):
                    errors.append(
                        f"参数 '{param_name}' 类型错误: 期望 {expected_type}, "
                        f"实际 {type(param_value).__name__}"
                    )

            # 检查整数范围
            if expected_type == "integer":
                min_val = param_schema.get("minimum")
                max_val = param_schema.get("maximum")
                if min_val is not None and param_value < min_val:
                    errors.append(f"参数 '{param_name}' 小于最小值 {min_val}")
                if max_val is not None and param_value > max_val:
                    errors.append(f"参数 '{param_name}' 大于最大值 {max_val}")

            # 检查字符串长度
            if expected_type == "string":
                min_len = param_schema.get("minLength")
                max_len = param_schema.get("maxLength")
                if min_len is not None and len(param_value) < min_len:
                    errors.append(f"参数 '{param_name}' 长度小于最小值 {min_len}")
                if max_len is not None and len(param_value) > max_len:
                    errors.append(f"参数 '{param_name}' 长度大于最大值 {max_len}")

    return errors


def execute_tool_safely(
    tool_name: str,
    inputs: Dict[str, Any],
    workspace: Optional[str] = None,
    include_diagnostics: bool = True
) -> Dict[str, Any]:
    """安全执行工具并返回结构化结果

    Args:
        tool_name: 工具名称
        inputs: 输入参数
        workspace: 工作目录
        include_diagnostics: 是否包含诊断信息

    Returns:
        执行结果字典
    """
    result = {
        "success": False,
        "output": "",
        "error": None,
        "error_details": None,
        "duration_ms": 0
    }

    import time
    start_time = time.time()

    try:
        # 获取工具
        tool = get_tool(tool_name)
        if tool is None:
            available = list(get_all_tools().keys())
            error = ToolExecutionError(
                tool_name=tool_name,
                error_type="ToolNotFound",
                error_message=f"工具 '{tool_name}' 未找到",
                inputs=inputs,
                workspace=workspace
            )
            error.suggestions = [
                f"可用工具: {', '.join(available[:5])}" + ("..." if len(available) > 5 else ""),
                "请检查工具名称拼写是否正确"
            ]
            result["error"] = str(error)
            if include_diagnostics:
                result["error_details"] = error.to_dict()
            return result

        # 验证输入
        validation_errors = validate_tool_inputs(tool_name, inputs, tool.get_schema())
        if validation_errors:
            error = ToolExecutionError(
                tool_name=tool_name,
                error_type="ValidationError",
                error_message=f"输入验证失败: {'; '.join(validation_errors)}",
                inputs=inputs,
                workspace=workspace
            )
            error.suggestions = validation_errors
            result["error"] = str(error)
            if include_diagnostics:
                result["error_details"] = error.to_dict()
            return result

        # 执行工具
        output = tool.execute(inputs, workspace)

        result["success"] = True
        result["output"] = output
        result["duration_ms"] = int((time.time() - start_time) * 1000)

        logger.debug(
            f"[TOOLS] 工具 {tool_name} 执行成功, "
            f"耗时: {result['duration_ms']}ms, 输出长度: {len(output)}"
        )

        return result

    except PermissionError as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type="PermissionError",
            error_message=str(e),
            inputs=inputs,
            workspace=workspace,
            stack_trace=traceback.format_exc()
        )
        error.suggestions = [
            "检查是否有足够的文件系统权限",
            "尝试以管理员身份运行",
            f"检查路径/文件是否正确: {inputs.get('path', '')}"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 权限错误 {tool_name}: {e}")

    except FileNotFoundError as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type="FileNotFoundError",
            error_message=str(e),
            inputs=inputs,
            workspace=workspace,
            stack_trace=traceback.format_exc()
        )
        path = inputs.get("path", "")
        error.suggestions = [
            f"检查路径是否存在: {path}",
            "路径区分大小写",
            "使用绝对路径或相对路径确保正确"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 文件未找到 {tool_name}: {e}")

    except UnicodeDecodeError as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type="UnicodeDecodeError",
            error_message=f"文件编码错误: {e}",
            inputs=inputs,
            workspace=workspace
        )
        error.suggestions = [
            "文件可能是二进制文件",
            "尝试使用二进制模式读取",
            "确认文件编码（如 UTF-8, GBK 等）"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 编码错误 {tool_name}: {e}")

    except ValueError as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type="ValueError",
            error_message=str(e),
            inputs=inputs,
            workspace=workspace,
            stack_trace=traceback.format_exc()
        )
        error.suggestions = [
            "检查输入参数的值格式是否正确",
            "参数类型是否匹配"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 值错误 {tool_name}: {e}")

    except ConnectionError as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type="ConnectionError",
            error_message=str(e),
            inputs=inputs,
            workspace=workspace,
            stack_trace=traceback.format_exc()
        )
        error.suggestions = [
            "检查网络连接",
            "检查目标服务器是否在线",
            "检查防火墙设置"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 连接错误 {tool_name}: {e}")

    except TimeoutError as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type="TimeoutError",
            error_message=str(e),
            inputs=inputs,
            workspace=workspace,
            stack_trace=traceback.format_exc()
        )
        error.suggestions = [
            "操作超时，请重试",
            "检查系统资源使用情况",
            "减少处理的数据量"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 超时错误 {tool_name}: {e}")

    except Exception as e:
        error = ToolExecutionError(
            tool_name=tool_name,
            error_type=type(e).__name__,
            error_message=str(e),
            inputs=inputs,
            workspace=workspace,
            stack_trace=traceback.format_exc()
        )
        error.suggestions = [
            "查看日志了解更多信息",
            "尝试简化输入参数后重试",
            "如果问题持续存在，请联系技术支持"
        ]
        result["error"] = str(error)
        if include_diagnostics:
            result["error_details"] = error.to_dict()
        logger.error(f"[TOOLS] 工具执行失败 {tool_name}: {e}", exc_info=True)

    result["duration_ms"] = int((time.time() - start_time) * 1000)
    return result


def format_tool_error_for_user(error_details: Dict[str, Any]) -> str:
    """格式化工具错误供用户查看

    Args:
        error_details: 错误详情字典

    Returns:
        用户友好的错误消息
    """
    tool_name = error_details.get("tool_name", "未知工具")
    error_type = error_details.get("error_type", "UnknownError")
    error_message = error_details.get("error_message", "未知错误")

    lines = [
        f"工具执行失败: {tool_name}",
        f"错误类型: {error_type}",
        f"详细信息: {error_message}"
    ]

    suggestions = error_details.get("suggestions", [])
    if suggestions:
        lines.append("\n建议操作:")
        for i, suggestion in enumerate(suggestions, 1):
            lines.append(f"  {i}. {suggestion}")

    workspace = error_details.get("workspace")
    if workspace:
        lines.append(f"\n工作目录: {workspace}")

    return "\n".join(lines)
