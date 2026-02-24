# -*- coding: utf-8 -*-
"""
清理进度组件 - Cleanup Progress Component

实时显示清理进度和状态
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer

from qfluentwidgets import (
    SimpleCardWidget,
    StrongBodyLabel,
    BodyLabel,
    SubtitleLabel,
    IconWidget,
    FluentIcon,
    PrimaryPushButton,
    PushButton,
    InfoBar,
    InfoBarPosition,
)

from ..agent.cleanup_orchestrator import (
    CleanupOrchestrator,
    CleanupSignal,
    CleanupPhase,
    CleanupReport,
)
from ..agent.smart_recommender import UserProfile, CleanupMode
from ..ui.restore_dialog import RestoreDialog
from utils.logger import get_logger

logger = get_logger(__name__)


class CleanupThread(QThread):
    """清理执行线程

    在后台线程中执行清理操作，避免阻塞 UI
    """

    progress_updated = pyqtSignal(int, str)
    phase_changed = pyqtSignal(str)
    cleanup_completed = pyqtSignal(CleanupReport)
    cleanup_failed = pyqtSignal(str)
    backup_progress = pyqtSignal(int, int)
    cleanup_status = pyqtSignal(str, bool)

    def __init__(
        self, orchestrator: CleanupOrchestrator, mode: str = CleanupMode.BALANCED.value
    ):
        super().__init__()
        self.orchestrator = orchestrator
        self.mode = mode

    def run(self):
        """执行清理"""
        try:
            report = self.orchestrator.execute_one_click_cleanup(self.mode)
            self.cleanup_completed.emit(report)
        except Exception as e:
            logger.error(f"[CleanupThread] 清理失败: {e}")
            self.cleanup_failed.emit(str(e))


class CleanupProgressWidget(SimpleCardWidget):
    """清理进度组件

    显示清理进度、阶段和统计信息
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cleanup_thread: Optional[CleanupThread] = None
        self.current_report: Optional[CleanupReport] = None
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        title_icon = IconWidget(FluentIcon.SYNC)
        title_icon.setFixedSize(24, 24)
        title_icon.setStyleSheet("color: #0078D4;")
        title_row.addWidget(title_icon)

        self.title_label = SubtitleLabel("清理进度")
        self.title_label.setStyleSheet("font-size: 18px;")
        title_row.addWidget(self.title_label)

        title_row.addStretch()

        # 状态指示
        self.status_icon = IconWidget(FluentIcon.ACCEPT)
        self.status_icon.setFixedSize(16, 16)
        self.status_icon.setStyleSheet("color: #52C41A;")
        self.status_icon.setVisible(False)
        title_row.addWidget(self.status_icon)

        self.status_label = BodyLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 13px;")
        title_row.addWidget(self.status_label)

        main_layout.addLayout(title_row)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background: #e0e0e0;")
        main_layout.addWidget(separator)

        # 当前阶段
        self.phase_label = BodyLabel("等待开始...")
        self.phase_label.setStyleSheet(
            "font-size: 14px; color: #333; font-weight: 600;"
        )
        main_layout.addWidget(self.phase_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #e0e0e0;
                border-radius: 12px;
                text-align: center;
                font-size: 12px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #0078D4, stop:1 #00a8cc);
                border-radius: 12px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # 详细信息
        self.details_label = BodyLabel("")
        self.details_label.setStyleSheet("color: #666; font-size: 13px;")
        self.details_label.setWordWrap(True)
        main_layout.addWidget(self.details_label)

        # 统计信息
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        self.success_count_label = BodyLabel("成功: 0")
        self.success_count_label.setStyleSheet("color: #52C41A; font-size: 13px;")
        stats_row.addWidget(self.success_count_label)

        self.failed_count_label = BodyLabel("失败: 0")
        self.failed_count_label.setStyleSheet("color: #FF4D4F; font-size: 13px;")
        stats_row.addWidget(self.failed_count_label)

        stats_row.addStretch()

        main_layout.addLayout(stats_row)

        # 撤销按钮
        self.undo_btn = PushButton("撤销清理")
        self.undo_btn.setFixedHeight(36)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._on_undo)
        main_layout.addWidget(self.undo_btn, alignment=Qt.AlignRight)

        # 备份提示
        self.backup_hint = QLabel("备份功能启用")
        self.backup_hint.setStyleSheet("""
            QLabel {
                background: #F0F9FF;
                color: #0958D9;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        self.backup_hint.setVisible(False)
        main_layout.addWidget(self.backup_hint)

    def start_cleanup(
        self, profile: UserProfile, mode: str = CleanupMode.BALANCED.value
    ):
        """开始清理

        Args:
            profile: 用户画像
            mode: 清理模式
        """
        # 清除之前的状态
        self._reset_ui()

        # 创建清理信号
        signal = CleanupSignal()
        signal.progress_updated.connect(self._on_progress_updated)
        signal.phase_changed.connect(self._on_phase_changed)
        signal.cleanup_completed.connect(self._on_cleanup_completed)
        signal.cleanup_failed.connect(self._on_cleanup_failed)
        signal.backup_progress.connect(self._on_backup_progress)
        signal.cleanup_status.connect(self._on_cleanup_status)

        # 创建清理编排器
        orchestrator = CleanupOrchestrator(profile, signal)

        # 创建并启动清理线程
        self.cleanup_thread = CleanupThread(orchestrator, mode)
        self.cleanup_thread.progress_updated.connect(self._on_progress_updated)
        self.cleanup_thread.phase_changed.connect(self._on_phase_changed)
        self.cleanup_thread.cleanup_completed.connect(self._on_cleanup_completed)
        self.cleanup_thread.cleanup_failed.connect(self._on_cleanup_failed)
        self.cleanup_thread.backup_progress.connect(self._on_backup_progress)
        self.cleanup_thread.cleanup_status.connect(self._on_cleanup_status)

        self.cleanup_thread.start()

        self._set_running_state()

    def _reset_ui(self):
        """重置 UI"""
        self.progress_bar.setValue(0)
        self.phase_label.setText("准备中...")
        self.details_label.setText("")
        self.success_count_label.setText("成功: 0")
        self.failed_count_label.setText("失败: 0")
        self.undo_btn.setEnabled(False)
        self.status_icon.setVisible(False)
        self.backup_hint.setVisible(True)

    def _set_running_state(self):
        """设置为运行状态"""
        self.status_icon.setVisible(True)
        self.status_label.setText("运行中")

    def _set_completed_state(self):
        """设置为完成状态"""
        self.status_icon.setStyleSheet("color: #52C41A;")
        self.status_label.setText("已完成")

    def _set_failed_state(self):
        """设置为失败状态"""
        self.status_icon.setStyleSheet("color: #FF4D4F;")
        self.status_label.setText("失败")

    def _on_progress_updated(self, percent: int, status: str):
        """进度更新"""
        self.progress_bar.setValue(percent)
        self.details_label.setText(status)

    def _on_phase_changed(self, phase: str):
        """阶段变化"""
        phase_enum = CleanupPhase(phase)
        self.phase_label.setText(f"当前阶段: {phase_enum.get_display_name()}")

    def _on_cleanup_completed(self, report: CleanupReport):
        """清理完成"""
        self.current_report = report
        self._set_completed_state()

        # 更新统计
        self.success_count_label.setText(f"成功: {report.success_items}")
        self.failed_count_label.setText(f"失败: {report.failed_items}")
        self.details_label.setText(
            f"清理完成！释放空间: {self._format_size(report.freed_size)}"
        )

        # 检查是否可以撤销（30天内）
        if self._can_undo(report):
            self.undo_btn.setEnabled(True)

        InfoBar.success(
            title="清理完成",
            content=f"成功清理 {report.success_items} 个文件，释放 {self._format_size(report.freed_size)}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

        logger.info(f"[CleanupProgress] 清理完成: {report.report_id}")

    def _on_cleanup_failed(self, error_message: str):
        """清理失败"""
        self._set_failed_state()
        self.details_label.setText(f"清理失败: {error_message}")

        InfoBar.error(
            title="清理失败",
            content=error_message,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000,
        )

        logger.error(f"[CleanupProgress] 清理失败: {error_message}")

    def _on_backup_progress(self, current: int, total: int):
        """备份进度"""
        percent = int((current / total) * 100) if total > 0 else 0
        self.details_label.setText(f"正在备份 ({current}/{total}): {percent}%")

    def _on_cleanup_status(self, path: str, success: bool):
        """清理状态"""
        if success:
            self.success_count_label.setText(f"成功: {self._get_success_count() + 1}")
        else:
            self.failed_count_label.setText(f"失败: {self._get_failed_count() + 1}")

    def _get_success_count(self) -> int:
        """获取成功数量"""
        text = self.success_count_label.text()
        try:
            return int(text.replace("成功: ", ""))
        except ValueError:
            return 0

    def _get_failed_count(self) -> int:
        """获取失败数量"""
        text = self.failed_count_label.text()
        try:
            return int(text.replace("失败: ", ""))
        except ValueError:
            return 0

    def _can_undo(self, report: CleanupReport) -> bool:
        """检查是否可以撤销（30天内）"""
        if not report.completed_at:
            return False

        time_since_cleanup = datetime.now() - report.completed_at
        return time_since_cleanup.days < 30

    def _on_undo(self):
        """撤销清理"""
        if not self.current_report:
            return

        if not self._can_undo(self.current_report):
            InfoBar.warning(
                title="无法撤销",
                content="此清理操作已超过30天，无法撤销",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
            return

        # 显示恢复对话框
        try:
            from ..core.restore_manager import RestoreManager
            from ..core.restore_signal import RestoreSignal
            from ..ui.restore_dialog import RestoreDialog, RestoreProgressDialog

            # 创建恢复对话框
            dialog = RestoreDialog(self)
            result = dialog.exec_()

            if result == QDialog.Accepted:
                # 用户点击撤销并成功
                self.undo_btn.setEnabled(False)
                logger.info(f"[CleanupProgress] 撤销成功: {self.current_report.report_id}")

        except ImportError as e:
            # 如果 RestoreManager 不存在，回退到 BackupManager
            logger.warning(f"[CleanupProgress] RestoreManager 不可用，使用 BackupManager: {e}")
            self._on_undo_fallback()
        except Exception as e:
            InfoBar.error(
                title="撤销失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )
            logger.error(f"[CleanupProgress] 撤销失败: {e}")

    def _on_undo_fallback(self):
        """撤销清理（后备方法，使用 BackupManager）"""
        try:
            from ..core.backup_manager import BackupManager

            # 创建备份管理器
            backup_manager = BackupManager()

            # 从清理报告中获取备份数据
            backup_entries = [
                d for d in self.current_report.details if d.get("type") == "backup"
            ]

            if not backup_entries:
                InfoBar.warning(
                    title="无法撤销",
                    content="未找到备份数据",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )
                return

            backup_id = backup_entries[0].get("backup_id")

            # 尝试恢复备份
            success = backup_manager.restore_backup(backup_id)

            if success:
                self.undo_btn.setEnabled(False)
                InfoBar.success(
                    title="撤销成功",
                    content=f"已从备份恢复文件 (备份ID: {backup_id[:8]}...)",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )
                logger.info(f"[CleanupProgress] 撤销成功: {backup_id}")
            else:
                InfoBar.error(
                    title="撤销失败",
                    content="无法从备份恢复文件，请检查备份是否完整",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                )
                logger.error(f"[CleanupProgress] 撤销失败: {backup_id}")

        except Exception as e:
            InfoBar.error(
                title="撤销失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )
            logger.error(f"[CleanupProgress] 撤销失败: {e}")

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def is_running(self) -> bool:
        """是否正在运行"""
        return self.cleanup_thread is not None and self.cleanup_thread.isRunning()

    def stop_cleanup(self):
        """停止清理"""
        if self.cleanup_thread and self.cleanup_thread.isRunning():
            self.cleanup_thread.terminate()
            self.cleanup_thread.wait()
            self._reset_ui()
            self.status_label.setText("已停止")
