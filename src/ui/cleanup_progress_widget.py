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
from ..agent.smart_recommender import UserProfile, CleanupMode, CleanupPlan
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
        self, orchestrator: CleanupOrchestrator, mode: str = CleanupMode.BALANCED.value,
        is_incremental: bool = False
    ):
        super().__init__()
        self.orchestrator = orchestrator
        self.mode = mode
        self.is_incremental = is_incremental  # 是否为增量清理

    def run(self):
        """执行清理"""
        try:
            if self.is_incremental:
                # 执行增量清理
                report = self.orchestrator.execute_incremental_cleanup(self.mode)
            else:
                # 执行完整清理
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
        self.current_plan: Optional[CleanupPlan] = None  # 保存当前清理计划
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        self.title_icon = IconWidget(FluentIcon.SYNC)
        self.title_icon.setFixedSize(24, 24)
        self.title_icon.setStyleSheet("color: #0078D4;")
        title_row.addWidget(self.title_icon)

        self.title_label = SubtitleLabel("清理进度")
        self.title_label.setStyleSheet("font-size: 18px;")
        title_row.addWidget(self.title_label)

        # 增量清理徽章（默认隐藏）
        self.incremental_badge = BodyLabel("增量")
        self.incremental_badge.setStyleSheet("""
            QLabel {
                background: #722ED1;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        self.incremental_badge.setVisible(False)
        title_row.addWidget(self.incremental_badge)

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

        # 增量清理提示栏（默认隐藏）
        self.incremental_hint = QLabel("快速清理：仅清理新增垃圾文件")
        self.incremental_hint.setStyleSheet("""
            QLabel {
                background: linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%);
                color: #6D28D9;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 12px;
                border-left: 4px solid #722ED1;
            }
        """)
        self.incremental_hint.setVisible(False)
        main_layout.addWidget(self.incremental_hint)

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

        # 增量清理统计（默认隐藏）
        incremental_stats_row = QHBoxLayout()
        incremental_stats_row.setSpacing(20)
        self.new_files_label = BodyLabel("")
        self.new_files_label.setStyleSheet("color: #722ED1; font-size: 12px;")
        incremental_stats_row.addWidget(self.new_files_label)

        self.skipped_files_label = BodyLabel("")
        self.skipped_files_label.setStyleSheet("color: #8B5CF6; font-size: 12px;")
        incremental_stats_row.addWidget(self.skipped_files_label)

        self.speed_improvement_label = BodyLabel("")
        self.speed_improvement_label.setStyleSheet("color: #A78BFA; font-size: 12px; font-weight: 600;")
        incremental_stats_row.addWidget(self.speed_improvement_label)

        incremental_stats_row.addStretch()
        self.incremental_stats_widget = QWidget()
        self.incremental_stats_widget.setLayout(incremental_stats_row)
        self.incremental_stats_widget.setVisible(False)
        main_layout.addWidget(self.incremental_stats_widget)

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
        self,
        profile: UserProfile,
        mode: str = CleanupMode.BALANCED.value,
        cleanup_plan: Optional[CleanupPlan] = None,
        is_incremental: bool = False
    ):
        """开始清理

        Args:
            profile: 用户画像
            mode: 清理模式
            cleanup_plan: 清理计划（可选，用于增量清理）
            is_incremental: 是否为增量清理
        """
        # 保存清理计划（用于增量清理）
        self.current_plan = cleanup_plan
        self.is_incremental = is_incremental or (cleanup_plan and cleanup_plan.is_incremental)

        # 清除之前的状态
        self._reset_ui()

        # 如果是增量清理，显示增量清理相关UI
        if self.is_incremental:
            self._show_incremental_ui()

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
        self.cleanup_thread = CleanupThread(orchestrator, mode, is_incremental)
        self.cleanup_thread.progress_updated.connect(self._on_progress_updated)
        self.cleanup_thread.phase_changed.connect(self._on_phase_changed)
        self.cleanup_thread.cleanup_completed.connect(self._on_cleanup_completed)
        self.cleanup_thread.cleanup_failed.connect(self._on_cleanup_failed)
        self.cleanup_thread.backup_progress.connect(self._on_backup_progress)
        self.cleanup_thread.cleanup_status.connect(self._on_cleanup_status)

        self.cleanup_thread.start()

        self._set_running_state()

    def _show_incremental_ui(self):
        """显示增量清理UI元素"""
        self.incremental_badge.setVisible(True)
        self.incremental_hint.setVisible(True)
        self.incremental_stats_widget.setVisible(True)
        self.title_label.setText("增量清理进度")
        self.title_icon.setIcon(FluentIcon.FAST_FORWARD)

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

        # 隐藏增量清理UI
        self.incremental_badge.setVisible(False)
        self.incremental_hint.setVisible(False)
        self.incremental_stats_widget.setVisible(False)
        self.title_label.setText("清理进度")
        self.title_icon.setIcon(FluentIcon.SYNC)

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

        # 如果是增量清理，显示额外统计信息
        if report.is_incremental:
            self._update_incremental_stats(report)

        self.details_label.setText(
            f"清理完成！释放空间: {self._format_size(report.freed_size)}"
        )

        # 如果是增量清理，保存文件列表
        if self.current_plan and self.current_plan.is_incremental:
            self._save_incremental_files(report)

        # 检查是否可以撤销（30天内）
        if self._can_undo(report):
            self.undo_btn.setEnabled(True)

        # 根据清理类型显示不同的提示信息
        if report.is_incremental:
            content = (
                f"增量清理完成！新增 {report.success_items} 个文件，"
                f"跳过 {report.skipped_files_count} 个已处理文件，"
                f"释放 {self._format_size(report.freed_size)}"
            )
        else:
            content = f"成功清理 {report.success_items} 个文件，释放 {self._format_size(report.freed_size)}"

        InfoBar.success(
            title="清理完成",
            content=content,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

        logger.info(f"[CleanupProgress] 清理完成: {report.report_id}")

    def _update_incremental_stats(self, report: CleanupReport):
        """更新增量清理统计信息

        Args:
            report: 清理报告
        """
        if not report.is_incremental:
            return

        # 更新增量文件统计
        self.new_files_label.setText(f"新增文件: {report.new_files_count}")
        self.skipped_files_label.setText(f"跳过文件: {report.skipped_files_count}")

        # 更新速度提升统计
        if report.speed_improvement > 0:
            self.speed_improvement_label.setText(
                f"速度提升: {report.speed_improvement:.1f}%"
            )
        else:
            self.speed_improvement_label.setText("")

        # 上次清理时间
        if report.last_cleanup_time:
            time_diff = datetime.now() - report.last_cleanup_time
            if time_diff.days > 0:
                time_str = f"{time_diff.days} 天前"
            else:
                time_str = f"{int(time_diff.seconds / 3600)} 小时前"
            self.details_label.setText(
                f"上次清理: {time_str} | "
                f"新增文件: {report.new_files_count} 个 | "
                f"释放: {self._format_size(report.freed_size)}"
            )

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

    def _save_incremental_files(self, report: CleanupReport):
        """保存增量清理的文件列表

        Args:
            report: 清理报告
        """
        try:
            # 从清理报告中提取清理成功的文件路径
            cleaned_files = [
                d.get('path') for d in report.details
                if d.get('success', False) and d.get('path')
            ]

            if cleaned_files:
                # 调用 SmartRecommender 保存文件列表
                from ..agent.smart_recommender import SmartRecommender

                recommender = SmartRecommender()
                recommender.save_last_cleanup_files(cleaned_files)

                logger.info(f"[CleanupProgress] 已保存 {len(cleaned_files)} 个增量清理文件到 last_cleanup_files.json")

                # 用户提示（可选）
                InfoBar.info(
                    title="增量清理记录已保存",
                    content=f"已记录 {len(cleaned_files)} 个清理文件用于下次增量清理",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                )

        except Exception as e:
            # 保存失败不影响清理结果，只记录警告
            logger.warning(f"[CleanupProgress] 保存增量清理文件列表失败: {e}")

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
