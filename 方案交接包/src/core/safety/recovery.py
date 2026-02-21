"""
文件恢复模块
基于 Windows 回收站实现文件恢复功能
"""
import os
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    import pythoncom
    import win32security
    from win32com.shell import shell, shellcon
    from ctypes import windll, create_unicode_buffer
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


@dataclass
class RecoveryItem:
    """回收站项目"""
    path: str
    original_path: str
    size: int
    deleted_time: datetime
    is_folder: bool


class RecoveryManager:
    """恢复管理器

    基于 Windows 回收站实现文件恢复功能
    """

    def __init__(self):
        """
        初始化恢复管理器
        """
        self._recycle_bin_path = self._get_recycle_bin_path()

    def _get_recycle_bin_path(self) -> str:
        """获取回收站路径"""
        try:
            CSIDL_BITBUCKET = 0x000a
            MAX_PATH = 260
            buffer = create_unicode_buffer(MAX_PATH)
            windll.shell32.SHGetFolderPathW(0, CSIDL_BITBUCKET, 0, 0, buffer)
            if buffer.value:
                return buffer.value
        except Exception:
            pass
        # 回退到系统回收站路径
        return os.path.join(os.environ['SystemDrive'], '$Recycle.Bin')

    def list_recycled_items(self) -> List[RecoveryItem]:
        """列出回收站中的项目"""
        items = []
        recycle_base = self._get_recycle_bin_path()

        if not HAS_WIN32 or not os.path.exists(recycle_base):
            return items

        try:
            pythoncom.CoInitialize()

            # 获取当前用户 SID
            user_sid = self._get_user_sid()

            # 优先扫描当前用户的回收站目录
            user_recycle_dir = os.path.join(recycle_base, user_sid)
            if os.path.exists(user_recycle_dir):
                self._scan_recycle_directory(user_recycle_dir, items)
            else:
                # 如果当前用户回收站不可访问，扫描所有用户的
                for entry in os.scandir(recycle_base):
                    if entry.is_dir(follow_symlinks=False) and entry.name.startswith('S-'):
                        self._scan_recycle_directory(entry.path, items)

        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 扫描系统回收站失败: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass

        return items

    def _get_user_sid(self) -> str:
        """获取当前用户的 SID"""
        try:
            sid = win32security.LookupAccountName(None, os.environ['USERNAME'])[0]
            # PySID 对象转字符串
            return str(sid)
        except:
            return ""

    def _scan_recycle_directory(self, recycle_dir: str, items: List[RecoveryItem]):
        """扫描回收站目录"""
        try:
            for entry in os.scandir(recycle_dir):
                if not entry.is_file(follow_symlinks=False) or not entry.name.startswith('$I'):
                    continue

                item = self._parse_recycle_info_file(entry.path, recycle_dir)
                if item:
                    items.append(item)
        except Exception:
            pass

    def _parse_recycle_info_file(self, info_file_path: str, recycle_dir: str) -> Optional[RecoveryItem]:
        """解析回收站信息文件 ($I开头的文件)"""
        try:
            import struct

            with open(info_file_path, 'rb') as f:
                # 读取文件头结构
                data = f.read(544)

            # 文件大小（偏移 16）
            file_size = struct.unpack('<Q', data[16:24])[0]

            # 删除时间（偏移 8）
            deleted_qword = struct.unpack('<Q', data[8:16])[0]
            deleted_timestamp = (deleted_qword - 116444736000000000) / 10000000
            deleted_time = datetime.fromtimestamp(deleted_timestamp)

            # 文件名长度（偏移 20）
            name_length = struct.unpack('<I', data[20:24])[0]

            # 文件名（偏移 24）
            name_bytes = data[24:24 + name_length * 2]
            original_name = name_bytes.decode('utf-16le').rstrip('\x00')

            # 查找对应的实际文件
            base_name = os.path.basename(info_file_path)
            data_filename = base_name.replace('$I', '$R', 1)
            data_file_path = os.path.join(recycle_dir, data_filename)

            # 原始路径（回退到使用文件名）
            original_path = f'$RecycleBin\\{original_name}'

            # 判断是否为文件夹（通过检查是否有对应的目录）
            is_folder = False
            dir_path = data_file_path.replace('$R', '$I', 1) + '.dir'
            if os.path.exists(dir_path):
                is_folder = True

            return RecoveryItem(
                path=data_file_path,
                original_path=original_path,
                size=file_size,
                deleted_time=deleted_time,
                is_folder=is_folder
            )

        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 解析信息文件失败 {info_file_path}: {e}")
            return None

    def restore_item(self, item_path: str) -> bool:
        """恢复文件到原始位置"""
        if not HAS_WIN32 or not os.path.exists(item_path):
            return False

        try:
            # 获取原始路径
            original_path = self._parse_original_path(item_path)

            # 移除 $R 前缀
            filename = os.path.basename(item_path)
            if filename.startswith('$R'):
                filename = filename[2:]

            if not original_path:
                # 使用默认恢复位置
                restore_dir = os.path.expanduser('~')
                original_path = os.path.join(restore_dir, f'Restored_{filename}')

            # 确保目标目录存在
            target_dir = os.path.dirname(original_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # 移动文件
            import shutil
            shutil.move(item_path, original_path)

            return True

        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 恢复文件失败 {item_path}: {e}")
            return False

    def restore_all(self) -> int:
        """恢复所有文件"""
        items = self.list_recycled_items()
        success_count = 0
        for item in items:
            if self.restore_item(item.path):
                success_count += 1
        return success_count

    def _parse_original_path(self, recycle_path: str) -> Optional[str]:
        """从回收站文件路径解析原始路径"""
        try:
            # Windows 回收站文件格式: $Ixxxxx... (信息文件)
            import struct

            # 获取信息文件路径（将 $R 替换为 $I）
            filename = os.path.basename(recycle_path)
            info_filename = filename.replace('$R', '$I', 1)
            info_path = os.path.join(os.path.dirname(recycle_path), info_filename)

            if not os.path.exists(info_path):
                return None

            # 读取信息文件
            with open(info_path, 'rb') as f:
                data = f.read(520)

            # 在 Windows 回收站中，原始路径存储在特定偏移
            # 通常在删除时间之后，大约 20-28 字节后开始
            # Windows 7+: 偏移 28 处是原始路径的开始
            offset = 28 if len(data) >= 32 else 20
            try:
                path_bytes = data[offset:]
                path_str = path_bytes.decode('utf-16le')

                # 查找 null 终止符
                null_pos = path_str.find('\x00')
                if null_pos != -1:
                    path_str = path_str[:null_pos]

                # 验证路径有效性
                if path_str and (':' in path_str or len(path_str) > 3):
                    return path_str
            except Exception:
                pass

        except Exception:
            pass
        return None

    def empty_recycle_bin(self) -> bool:
        """清空回收站"""
        if not HAS_WIN32:
            return False
        try:
            from win32com.shell import shell, shellcon
            shell.SHEmptyRecycleBin(
                0, None,
                shellcon.SHERB_NOCONFIRMATION
            )
            return True
        except Exception:
            return False

    def get_recycle_bin_size(self) -> int:
        """获取回收站总大小"""
        items = self.list_recycled_items()
        return sum(item.size for item in items)

    def get_recycle_bin_count(self) -> int:
        """获取回收站文件数量"""
        items = self.list_recycled_items()
        return len(items)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """格式化大小"""
        if size_bytes == 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f'{size:.2f} {units[unit_index]}'


# 全局恢复管理器实例
_global_recovery: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    """获取全局恢复管理器实例（单例）"""
    global _global_recovery
    if _global_recovery is None:
        _global_recovery = RecoveryManager()
    return _global_recovery
