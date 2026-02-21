"""
时间解析工具模块
提供统一的 ISO 时间字符串解析功能
"""
from datetime import datetime
from typing import Optional


def parse_iso_timestamp(iso_str: str) -> Optional[datetime]:
    """解析 ISO 时间字符串

    统一处理 'Z' 和 +00:00 格式的时间字符串

    Args:
        iso_str: ISO 时间字符串

    Returns:
        datetime 对象，解析失败返回 None
    """
    if not iso_str:
        return None

    try:
        # 处理 'Z' 结尾的 UTC 时间
        iso_str = iso_str.replace('Z', '+00:00')
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError) as e:
        return None


def format_now_iso() -> str:
    """获取当前时间的 ISO 格式字符串

    Returns:
        ISO 格式时间字符串 (UTC +00:00)
    """
    return datetime.now().isoformat()


__all__ = ['parse_iso_timestamp', 'format_now_iso']
