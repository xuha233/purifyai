"""
磁盘空间监控模块
使用 psutil 监控磁盘空间
当可用空间低于阈值时触发信号
"""
import os
from typing import List, Tuple, Optional
from PyQt5.QtCore import QObject, pyqtSignal
import psutil

from .config_manager import get_config_manager


class DiskMonitor(QObject):
    """磁盘空间监控器

    监控指定磁盘的空间使用情况
    当可用空间低于阈值时触发信号
    """
    # Signals
    disk_space_low = pyqtSignal(str, int)  # disk_path, free_space_gb
    disk_space_normal = pyqtSignal(str, int)  # disk_path, free_space_gb
    disk_space_changed = pyqtSignal(dict)  # dict with disk info

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = get_config_manager()
        self.monitored_disks = []
        self.threshold_gb = self._load_threshold()
        self._load_monitored_disks()

    def _load_threshold(self) -> int:
        """加载磁盘空间阈值（GB）"""
        return self.config_mgr.get('scheduler/disk_threshold', 10)

    def _load_monitored_disks(self):
        """加载要监控的磁盘列表"""
        self.monitored_disks = self.config_mgr.get('disk_monitor/disks', [])

    def _save_monitored_disks(self):
        """保存要监控的磁盘列表"""
        self.config_mgr.set('disk_monitor/disks', self.monitored_disks)

    def set_threshold(self, threshold_gb: int):
        """
        设置磁盘空间阈值

        Args:
            threshold_gb: 阈值（GB）
        """
        self.threshold_gb = threshold_gb
        self.config_mgr.set('scheduler/disk_threshold', threshold_gb)

    def get_threshold(self) -> int:
        """
        获取磁盘空间阈值

        Returns:
            int: 阈值（GB）
        """
        return self.threshold_gb

    @staticmethod
    def get_all_disks() -> List[dict]:
        """
        获取所有磁盘信息

        Returns:
            List[dict]: 磁盘信息列表
            {
                'device': 'C:',
                'mountpoint': 'C:\\',
                'fstype': 'NTFS',
                'total_gb': 100,
                'used_gb': 50,
                'free_gb': 50,
                'percent': 50
            }
        """
        disks = []
        partitions = psutil.disk_partitions(all=True)

        for partition in partitions:
            try:
                # 跳过非本地磁盘
                if 'cdrom' in partition.opts or partition.fstype == '':
                    continue

                usage = psutil.disk_usage(partition.mountpoint)
                disk_info = {
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percent': usage.percent
                }
                disks.append(disk_info)
            except Exception:
                continue

        return disks

    def get_disk_info(self, disk_path: str) -> Optional[dict]:
        """
        获取指定磁盘的信息

        Args:
            disk_path: 磁盘路径（如 'C:\\' 或 'C:'）

        Returns:
            dict: 磁盘信息，如果失败返回 None
        """
        try:
            # 规范化路径
            if not disk_path.endswith('\\'):
                disk_path = disk_path + '\\'

            usage = psutil.disk_usage(disk_path)
            return {
                'device': disk_path,
                'mountpoint': disk_path,
                'total_gb': round(usage.total / (1024**3), 2),
                'used_gb': round(usage.used / (1024**3), 2),
                'free_gb': round(usage.free / (1024**3), 2),
                'percent': usage.percent
            }
        except Exception:
            return None

    def check_disk_space(self, disk_path: str = None, emit_signal: bool = True) -> dict:
        """
        检查磁盘空间

        Args:
            disk_path: 磁盘路径，如果为 None 则检查系统盘
            emit_signal: 是否发送信号

        Returns:
            dict: 磁盘信息
        """
        # 如果没有指定磁盘，使用系统盘
        if disk_path is None:
            disk_path = os.environ.get('SYSTEMDRIVE', 'C:')

        disk_info = self.get_disk_info(disk_path)
        if disk_info is None:
            return {}

        if emit_signal:
            # 发送磁盘空间变化信号
            self.disk_space_changed.emit(disk_info)

            # 检查是否低于阈值
            if disk_info['free_gb'] < self.threshold_gb:
                self.disk_space_low.emit(disk_path, disk_info['free_gb'])
            else:
                self.disk_space_normal.emit(disk_path, disk_info['free_gb'])

        return disk_info

    def add_monitored_disk(self, disk_path: str):
        """
        添加要监控的磁盘

        Args:
            disk_path: 磁盘路径
        """
        if disk_path not in self.monitored_disks:
            self.monitored_disks.append(disk_path)
            self._save_monitored_disks()

    def remove_monitored_disk(self, disk_path: str):
        """
        移除要监控的磁盘

        Args:
            disk_path: 磁盘路径
        """
        if disk_path in self.monitored_disks:
            self.monitored_disks.remove(disk_path)
            self._save_monitored_disks()

    def check_all_monitored_disks(self):
        """
        检查所有监控的磁盘空间
        """
        for disk_path in self.monitored_disks:
            self.check_disk_space(disk_path)

    @staticmethod
    def get_system_disk_path() -> str:
        """
        获取系统盘路径

        Returns:
            str: 系统盘路径
        """
        return os.environ.get('SYSTEMDRIVE', 'C:') + '\\'


# 全局磁盘监控器实例（单例模式）
_global_disk_monitor: Optional[DiskMonitor] = None


def get_disk_monitor() -> DiskMonitor:
    """
    获取全局磁盘监控器实例（单例）

    Returns:
        DiskMonitor: 磁盘监控器实例
    """
    global _global_disk_monitor
    if _global_disk_monitor is None:
        _global_disk_monitor = DiskMonitor()
    return _global_disk_monitor
