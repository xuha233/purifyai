"""
回收站恢复对话框
用于查看和恢复被删除到回收站的文件
"""
import os
from typing import List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton
)

from core.safety.recovery import get_recovery_manager, RecoveryItem


class RecoveryDialog(QDialog):
    """回收站恢复对话框

    显示和恢复回收站中的文件
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recovery_manager = get_recovery_manager()
        self.recovery_items = []
        self.init_ui()
        self.load_recycle_bin()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle('回收站恢复')
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = StrongBodyLabel('回收站恢复')
        title.setStyleSheet('font-size: 18px;')
        layout.addWidget(title)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.count_label = BodyLabel('文件数: 0')
        self.count_label.setStyleSheet('color: #666666; font-size: 12px;')
        stats_layout.addWidget(self.count_label)

        self.size_label = BodyLabel('总大小: 0 B')
        self.size_label.setStyleSheet('color: #666666; font-size: 12px;')
        stats_layout.addWidget(self.size_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        layout.addSpacing(10)

        # 文件列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['文件名', '原始位置', '大小', '删除时间'])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        # 允许单选
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        layout.addWidget(self.table)

        # 操作按钮
        buttons_layout = QHBoxLayout()

        self.refresh_btn = PushButton('刷新')
        self.refresh_btn.clicked.connect(self.load_recycle_bin)
        buttons_layout.addWidget(self.refresh_btn)

        self.restore_btn = PrimaryPushButton('恢复选中文件')
        self.restore_btn.clicked.connect(self.restore_selected)
        self.restore_btn.setEnabled(False)
        buttons_layout.addWidget(self.restore_btn)

        self.restore_all_btn = PushButton('恢复全部')
        self.restore_all_btn.clicked.connect(self.restore_all)
        buttons_layout.addWidget(self.restore_all_btn)

        buttons_layout.addStretch()

        self.close_btn = PushButton('关闭')
        self.close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_btn)

        layout.addLayout(buttons_layout)

        # 连接表格选择事件
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

    def load_recycle_bin(self):
        """加载回收站文件列表"""
        # 清空表格
        self.table.setRowCount(0)
        self.recovery_items.clear()

        # 获取回收站文件
        try:
            self.recovery_items = self.recovery_manager.list_recycled_items()
        except Exception as e:
            self.recovery_items = []

        # 填充表格
        for item in self.recovery_items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 文件名
            name_item = QTableWidgetItem(os.path.basename(item.path))
            name_item.setData(Qt.UserRole, item)  # 保存物品数据
            self.table.setItem(row, 0, name_item)

            # 原始位置
            self.table.setItem(row, 1, QTableWidgetItem(item.original_path))

            # 大小
            size_str = self.recovery_manager.format_size(item.size)
            self.table.setItem(row, 2, QTableWidgetItem(size_str))

            # 删除时间
            time_str = item.deleted_time.strftime('%Y-%m-%d %H:%M:%S')
            self.table.setItem(row, 3, QTableWidgetItem(time_str))

        # 更新统计
        self.update_stats()

    def update_stats(self):
        """更新统计信息"""
        total_size = sum(item.size for item in self.recovery_items)
        self.count_label.setText(f'文件数: {len(self.recovery_items)}')
        self.size_label.setText(f'总大小: {self.recovery_manager.format_size(total_size)}')

        # 更新按钮状态
        has_items = len(self.recovery_items) > 0
        self.restore_all_btn.setEnabled(has_items)

    def on_selection_changed(self):
        """处理表格选择变化"""
        selected_items = self.table.selectedItems()
        self.restore_btn.setEnabled(len(selected_items) > 0)

    def restore_selected(self):
        """恢复选中的文件"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        # 恢复文件
        restored_count = 0
        for row in selected_rows:
            item = self.table.item(row, 0).data(Qt.UserRole)
            if self.recovery_manager.restore_item(item.path):
                restored_count += 1

        if restored_count > 0:
            QMessageBox.information(
                self, '恢复成功',
                f'成功恢复 {restored_count} 个文件'
            )
            # 刷新列表
            self.load_recycle_bin()
        else:
            QMessageBox.warning(
                self, '恢复失败',
                '未能恢复任何文件，请检查权限或文件状态'
            )

    def restore_all(self):
        """恢复所有文件"""
        reply = QMessageBox.question(
            self,
            '确认恢复',
            f'确定要恢复回收站中的所有 {len(self.recovery_items)} 个文件吗？',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            restored_count = self.recovery_manager.restore_all()

            QMessageBox.information(
                self, '恢复完成',
                f'成功恢复 {restored_count} 个文件'
            )

            # 刷新列表
            self.load_recycle_bin()

    def get_recovery_items(self) -> List[RecoveryItem]:
        """
        获取恢复项目列表

        Returns:
            List[RecoveryItem]: 恢复项目列表
        """
        return self.recovery_items.copy()
