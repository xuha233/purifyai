# -*- coding: utf-8 -*-
"""
恢复对话框 (Restore Dialog)

显示撤销历史列表和文件恢复进度

作者: 小午 🦁
创建时间: 2026-02-24
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QFrame,
    QAbstractItemView,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

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
    TableWidget,
    setTheme,
    Theme,
)

from core.restore_manager import RestoreManager, RestoreSession, UndoHistory
from agent.cleanup_orchestrator import CleanupReport
from utils.logger import get_logger

logger = get_logger(__name__)


class RestoreDialog(QDialog):
    """恢复对话框

    显示撤销历史列表和恢复进度
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.restore_manager = RestoreManager()
        self._init_ui()
        self._load_undo_history()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("撤销清理")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        title_icon = IconWidget(FluentIcon.HISTORY)
        title_icon.setFixedSize(24, 24)
        title_icon.setStyleSheet("color: #0078D4;")
        title_row.addWidget(title_icon)

        title = SubtitleLabel("撤销历史")
        title.setStyleSheet("font-size: 18px;")
        title_row.addWidget(title)

        title_row.addStretch()

        main_layout.addLayout(title_row)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background: #e0e0e0;")
        main_layout.addWidget(separator)

        # 撤销历史表格
        self.history_table = TableWidget(self)
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "清理时间",
            "清理报告 ID",
            "备份 ID",
            "是否可撤销",
            "状态"
        ])

        # 设置表格属性
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        main_layout.addWidget(self.history_table)

        # 按钮行
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)

        self.undo_btn = PrimaryPushButton("撤销选中的清理")
        self.undo_btn.setFixedHeight(40)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._on_undo_selected)
        button_row.addWidget(self.undo_btn)

        button_row.addStretch()

        self.refresh_btn = PushButton("刷新列表")
        self.refresh_btn.setFixedHeight(40)
        self.refresh_btn.clicked.connect(self._load_undo_history)
        button_row.addWidget(self.refresh_btn)

        self.close_btn = PushButton("关闭")
        self.close_btn.setFixedHeight(40)
        self.close_btn.clicked.connect(self.accept)
        button_row.addWidget(self.close_btn)

        main_layout.addLayout(button_row)

        # 连接表格选择信号
        self.history_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_undo_history(self):
        """加载撤销历史"""
        self.history_table.setRowCount(0)

        history_list = self.restore_manager.get_undo_history()

        for idx, history in enumerate(history_list):
            self.history_table.insertRow(idx)

            # 清理时间
            time_text = history.cleanup_time.strftime("%Y-%m-%d %H:%M:%S")
            time_item = QTableWidgetItem(time_text)
            self.history_table.setItem(idx, 0, time_item)

            # 清理报告 ID
            item = QTableWidgetItem(history.cleanup_report_id)
            self.history_table.setItem(idx, 1, item)

            # 备份 ID
            item = QTableWidgetItem(history.backup_id[:8] + "...")
            self.history_table.setItem(idx, 2, item)

            # 是否可撤销
            can_undo_text = "是" if history.can_undo else "否"
            can_undo_item = QTableWidgetItem(can_undo_text)
            self.history_table.setItem(idx, 3, can_undo_item)

            # 状态
            status_text = self._get_status_display(history.status)
            status_item = QTableWidgetItem(status_text)
            if history.status == "expired":
                status_item.setForeground(QColor("#999999"))
            elif history.status == "undone":
                status_item.setForeground(QColor("#52C41A"))

            self.history_table.setItem(idx, 4, status_item)

            # 存储完整数据
            self.history_table.item(idx, 0).setData(Qt.UserRole, history)

    def _get_status_display(self, status: str) -> str:
        """获取状态显示文本"""
        status_map = {
            "available": "可撤销",
            "undone": "已撤销",
            "expired": "已过期"
        }
        return status_map.get(status, status)

    def _on_selection_changed(self):
        """选择变化"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if len(selected_rows) == 0:
            self.undo_btn.setEnabled(False)
            return

        # 检查是否可撤销
        row = selected_rows[0].row()
        history = self.history_table.item(row, 0).data(Qt.UserRole)

        if history.can_undo and history.status == "available":
            self.undo_btn.setEnabled(True)
            self.undo_btn.setText(f"撤销清理（{history.cleanup_time.strftime('%Y-%m-%d %H:%M')}）")
        else:
            self.undo_btn.setEnabled(False)
            if history.status == "expired":
                self.undo_btn.setText("已超过30天，无法撤销")
            elif history.status == "undone":
                self.undo_btn.setText("已撤销此清理")
            else:
                self.undo_btn.setText("无法撤销")

    def _on_undo_selected(self):
        """撤销选中的清理"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if len(selected_rows) == 0:
            return

        row = selected_rows[0].row()
        history = self.history_table.item(row, 0).data(Qt.UserRole)

        # 确认对话框
        confirm = QMessageBox.question(
            self,
            "确认撤销",
            f"确定要撤销 {history.cleanup_time.strftime('%Y-%m-%d %H:%M:%S')} 的清理操作吗？\n\n"
            f"文件将从备份恢复到原位置。",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        # 执行撤销
        try:
            # 创建恢复会话
            session = self.restore_manager.create_restore_session(history.backup_id)

            # 执行恢复
            success = self.restore_manager.execute_restore(session.session_id)

            if success:
                # 更新撤销历史
                history.status = "undone"
                history.can_undo = False
                history.undo_time = datetime.now()

                # 提示成功
                InfoBar.success(
                    title="撤销成功",
                    content=f"已成功撤销 {history.cleanup_time.strftime('%Y-%m-%d %H:%M')} 的清理操作",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                )

                # 刷新列表
                self._load_undo_history()
            else:
                InfoBar.error(
                    title="撤销失败",
                    content="撤销操作失败，请查看日志",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                )

        except Exception as e:
            logger.error(f"[RestoreDialog] 撤销失败: {e}")
            InfoBar.error(
                title="撤销失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )


class RestoreProgressDialog(QDialog):
    """恢复进度对话框

    显示文件恢复进度
    """

    def __init__(self, session: RestoreSession, parent=None):
        super().__init__(parent)
        self.session = session
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("恢复进度")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("文件恢复中...")
        title.setStyleSheet("font-size: 18px;")
        main_layout.addWidget(title)

        # 会话 ID
        session_id_label = BodyLabel(f"会话 ID: {self.session.session_id[:8]}...")
        session_id_label.setStyleSheet("color: #999; font-size: 12px;")
        main_layout.addWidget(session_id_label)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background: #e0e0e0;")
        main_layout.addWidget(separator)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(30)
        main_layout.addWidget(self.progress_bar)

        # 详细信息
        self.details_label = BodyLabel("")
        self.details_label.setStyleSheet("color: #666; font-size: 14px;")
        self.details_label.setWordWrap(True)
        main_layout.addWidget(self.details_label)

        # 统计信息
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        self.success_count_label = BodyLabel("成功: 0")
        self.success_count_label.setStyleSheet("color: #52C41A; font-size: 14px; font-weight: 600;")
        stats_row.addWidget(self.success_count_label)

        self.failed_count_label = BodyLabel("失败: 0")
        self.failed_count_label.setStyleSheet("color: #FF4D4F; font-size: 14px; font-weight: 600;")
        stats_row.addWidget(self.failed_count_label)

        stats_row.addStretch()

        main_layout.addLayout(stats_row)

        # 按钮行
        button_row = QHBoxLayout()

        self.close_btn = PushButton("关闭")
        self.close_btn.setFixedHeight(40)
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        button_row.addWidget(self.close_btn)

        main_layout.addLayout(button_row, alignment=Qt.AlignRight)

    def update_progress(self, percent: int, status: str):
        """更新进度

        Args:
            percent: 百分比
            status: 状态描述
        """
        self.progress_bar.setValue(percent)
        self.details_label.setText(status)

    def update_stats(self, success_count: int, failed_count: int):
        """更新统计

        Args:
            success_count: 成功数量
            failed_count: 失败数量
        """
        self.success_count_label.setText(f"成功: {success_count}")
        self.failed_count_label.setText(f"失败: {failed_count}")

    def set_completed(self):
        """设置为完成状态"""
        self.progress_bar.setValue(100)
        self.details_label.setText("恢复完成！")
        self.close_btn.setEnabled(True)

    def set_failed(self, error_message: str):
        """设置为失败状态

        Args:
            error_message: 错误消息
        """
        self.details_label.setText(f"恢复失败: {error_message}")
        self.close_btn.setEnabled(True)
