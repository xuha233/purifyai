"""
文件预览模块
提供文件预览功能，包括元数据、文本内容预览、图片缩略图等
"""
import os
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PreviewResult:
    """文件预览结果"""
    path: str
    exists: bool
    size: int
    file_type: str
    description: str
    content_preview: Optional[str] = None
    is_text_file: bool = False
    is_image: bool = False
    modified_time: Optional[datetime] = None


class FilePreviewWidget:
    """文件预览功能类

    提供文件预览的核心功能
    """

    # 文本文件扩展名
    TEXT_EXTENSIONS = {
        '.txt', '.log', '.md', '.json', '.xml', '.yaml', '.yml',
        '.ini', '.cfg', '.conf', '.py', '.js', '.html', '.css',
        '.scss', '.java', '.c', '.cpp', '.h', '.hpp', '.bat',
        '.sh', '.ps1', '.csv', '.tsv'
    }

    # 图片文件扩展名
    IMAGE_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
        '.tiff', '.tif', '.webp', '.svg', '.psd'
    }

    @classmethod
    def get_file_extension(cls, path: str) -> str:
        """
        获取文件扩展名

        Args:
            path: 文件路径

        Returns:
            str: 文件扩展名（小写）
        """
        return os.path.splitext(path)[1].lower()

    @classmethod
    def is_text_file(cls, path: str) -> bool:
        """
        检查是否为文本文件

        Args:
            path: 文件路径

        Returns:
            bool: 是否为文本文件
        """
        ext = cls.get_file_extension(path)
        return ext in cls.TEXT_EXTENSIONS

    @classmethod
    def is_image_file(cls, path: str) -> bool:
        """
        检查是否为图片文件

        Args:
            path: 文件路径

        Returns:
            bool: 是否为图片文件
        """
        ext = cls.get_file_extension(path)
        return ext in cls.IMAGE_EXTENSIONS

    @classmethod
    def get_file_type(cls, path: str) -> str:
        """
        获取文件类型描述

        Args:
            path: 文件路径

        Returns:
            str: 文件类型描述
        """
        if os.path.isdir(path):
            return '文件夹'

        if cls.is_image_file(path):
            return '图片文件'

        if cls.is_text_file(path):
            return '文本文件'

        ext = cls.get_file_extension(path)
        if ext:
            return f'{ext[1:]} 文件'

        return '二进制文件'

    @classmethod
    def get_file_size(cls, path: str) -> int:
        """
        获取文件大小

        Args:
            path: 文件路径

        Returns:
            int: 文件大小（字节）
        """
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)
            elif os.path.isdir(path):
                total = 0
                for root, dirs, files in os.walk(path):
                    for file in files:
                        try:
                            total += os.path.getsize(os.path.join(root, file))
                        except (OSError, PermissionError):
                            pass
                return total
            return 0
        except (OSError, PermissionError):
            return 0

    @classmethod
    def get_modified_time(cls, path: str) -> Optional[datetime]:
        """
        获取文件修改时间

        Args:
            path: 文件路径

        Returns:
            datetime: 修改时间
        """
        try:
            mtime = os.path.getmtime(path)
            return datetime.fromtimestamp(mtime)
        except (OSError, PermissionError):
            return None

    @classmethod
    def read_text_content(cls, path: str, max_size: int = 1024) -> Optional[str]:
        """
        读取文本文件内容预览

        Args:
            path: 文件路径
            max_size: 最大读取字节数

        Returns:
            str: 文本内容预览
        """
        if not os.path.isfile(path):
            return None

        try:
            # 尝试用 UTF-8 读取
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_size)
                return content
        except Exception:
            # 尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read(max_size)
                        return content
                except Exception:
                    continue

        return None

    @classmethod
    def get_image_thumbnail_data(cls, path: str) -> Optional[bytes]:
        """
        获取图片缩略图数据

        Args:
            path: 图片文件路径

        Returns:
            bytes: 图片数据
        """
        try:
            from PyQt5.QtGui import QPixmap, QImage
            from io import BytesIO

            # 读取图片
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None

            # 缩放图片
            thumbnail = pixmap.scaled(
                200, 200,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # 保存为字节数据
            byte_array = BytesIO()
            thumbnail.save(byte_array, 'PNG')
            return byte_array.getvalue()
        except Exception:
            return None

    @classmethod
    def get_binary_hex_preview(cls, path: str, max_size: int = 512) -> Optional[str]:
        """
        获取二进制文件的十六进制预览

        Args:
            path: 文件路径
            max_size: 最大读取字节数

        Returns:
            str: 十六进制字符串
        """
        if not os.path.isfile(path):
            return None

        try:
            with open(path, 'rb') as f:
                data = f.read(max_size)

            # 转换为十六进制
            hex_str = ' '.join(f'{b:02x}' for b in data[:16])  # 只显示前16字节

            # 尝试显示 ASCII 字符
            try:
                ascii_preview = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:32])
            except Exception:
                ascii_preview = data[:32].decode('ascii', errors='ignore')

            return f'HEX: {hex_str}\nASCII: {ascii_preview}'
        except Exception:
            return None

    @classmethod
    def preview_file(cls, path: str) -> PreviewResult:
        """
        预览文件

        Args:
            path: 文件路径

        Returns:
            PreviewResult: 预览结果
        """
        exists = os.path.exists(path)

        if not exists:
            return PreviewResult(
                path=path,
                exists=False,
                size=0,
                file_type='未知',
                description='文件不存在'
            )

        file_type = cls.get_file_type(path)
        size = cls.get_file_size(path)
        modified_time = cls.get_modified_time(path)

        description = f'{file_type}'
        if cls.is_text_file(path):
            description += ' (可预览内容)'
        elif cls.is_image_file(path):
            description += ' (可预览图片)'

        content_preview = None
        is_text = cls.is_text_file(path)
        is_image = cls.is_image_file(path)

        # 尝试读取文本内容预览
        if is_text:
            content_preview = cls.read_text_content(path)

        return PreviewResult(
            path=path,
            exists=exists,
            size=size,
            file_type=file_type,
            description=description,
            content_preview=content_preview,
            is_text_file=is_text,
            is_image=is_image,
            modified_time=modified_time
        )

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """
        格式化大小为人类可读格式

        Args:
            size_bytes: 大小（字节）

        Returns:
            str: 格式化后的字符串
        """
        if size_bytes == 0:
            return '0 B'

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f'{size:.2f} {units[unit_index]}'


# 全局预览实例（单例模式）
_global_preview: Optional[FilePreviewWidget] = None


def get_preview() -> FilePreviewWidget:
    """
    获取全局预览实例（单例）

    Returns:
        FilePreviewWidget: 预览实例
    """
    global _global_preview
    if _global_preview is None:
        _global_preview = FilePreviewWidget()
    return _global_preview
