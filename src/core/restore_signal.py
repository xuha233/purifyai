# -*- coding: utf-8 -*-
"""
恢复信号 (Restore Signal)

定义文件恢复的信号

作者: 小午 🦁
创建时间: 2026-02-24
"""

from PyQt5.QtCore import QObject, pyqtSignal

# ============================================================================
# 恢复信号
# ============================================================================

class RestoreSignal(QObject):
    """文件恢复信号（用于更新 UI）"""

    # 进度更新：(百分比, 当前状态描述)
    progress_updated = pyqtSignal(int, str)

    # 文件恢复：（文件路径, 成功/失败）
    file_restored = pyqtSignal(str, bool)

    # 恢复完成：恢复会话
    restore_completed = pyqtSignal(object)

    # 恢复失败：错误消息
    restore_failed = pyqtSignal(str)
