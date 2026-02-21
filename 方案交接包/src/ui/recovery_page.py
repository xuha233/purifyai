"""
回收站恢复页面
自定义回收站管理，支持扫描和管理回收站内所有文件（包括用户手动添加的）
系统回收站仅提供打开 Windows 回收站的入口
"""
import os
import shutil
import subprocess
import logging
from typing import List, Dict, Any
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QSplitter, QTabWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, SubtitleLabel, CardWidget, FluentIcon, InfoBar,
    InfoBarPosition
)
from core.safety.custom_recycle_bin import get_custom_recycle_bin, get_custom_recycle_path
from core.config_manager import get_config_manager


class RecoveryPage(QWidget):
    """回收站恢复页面

    系统回收站：只提供打开 Windows 回收站的入口
    自定义回收站：扫描和管理软件管理的回收站文件
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = get_config_manager()
        self.custom_items = []
        self.init_ui()
        self.load_all_items()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        header_layout = QHBoxLayout()
        title = StrongBodyLabel('回收站恢复')
        title.setStyleSheet('font-size: 24px;')
        header_layout.addWidget(title)
        header_layout.addSpacing(20)

        desc = BodyLabel('管理自定义回收站的文件')
        desc.setStyleSheet('color: #666666; font-size: 14px;')
        header_layout.addWidget(desc)
        header_layout.addStretch()

        header_layout.addSpacing(20)

        self.refresh_btn = PushButton('刷新')
        self.refresh_btn.clicked.connect(self.load_all_items)
        header_layout.addWidget(self.refresh_btn)

        self.clear_custom_btn = PushButton('清空回收站')
        self.clear_custom_btn.clicked.connect(self.clear_custom_recycle)
        header_layout.addWidget(self.clear_custom_btn)

        layout.addLayout(header_layout)

        # 统计信息卡片
        stats_card = SimpleCardWidget()
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 15, 20, 15)

        self.count_label = BodyLabel('文件数: 0 项')
        self.count_label.setStyleSheet('color: #666666; font-size: 12px;')
        stats_layout.addWidget(self.count_label)

        self.size_label = BodyLabel('总大小: 0 B')
        self.size_label.setStyleSheet('color: #666666; font-size: 12px;')
        stats_layout.addWidget(self.size_label)

        stats_layout.addSpacing(20)

        self.managed_label = BodyLabel('托管: 0')
        self.managed_label.setStyleSheet('color: #666666; font-size: 12px;')
        stats_layout.addWidget(self.managed_label)

        stats_layout.addSpacing(20)

        self.unmanaged_label = BodyLabel('未管理: 0')
        self.unmanaged_label.setStyleSheet('color: #996699; font-size: 12px;')
        stats_layout.addWidget(self.unmanaged_label)

        stats_layout.addStretch()

        layout.addWidget(stats_card)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('QTabWidget::pane { border: 1px solid #ddd; }')

        # 系统回收站标签
        self.system_tab = QWidget()
        system_tab_layout = QVBoxLayout(self.system_tab)
        system_tab_layout.setContentsMargins(20, 50, 20, 20)

        # 系统回收站内容
        system_content_card = SimpleCardWidget()
        system_content = QVBoxLayout(system_content_card)
        system_content.setContentsMargins(30, 30, 30, 30)
        system_content.setSpacing(20)

        sys_title = SubtitleLabel('Windows 系统回收站')
        sys_title.setStyleSheet('color: #666666;')
        system_content.addWidget(sys_title)

        system_content.addSpacing(20)

        sys_desc = BodyLabel(
            '系统回收站由 Windows 操作系统管理。点击下方按钮可直接打开 Windows 回收站。'
        )
        sys_desc.setStyleSheet('color: #999999; font-size: 13px;')
        sys_desc.setWordWrap(True)
        system_content.addWidget(sys_desc)

        system_content.addSpacing(30)

        # 打开系统回收站按钮
        self.open_system_recycle_btn = PushButton('打开系统回收站')
        self.open_system_recycle_btn.setIcon(FluentIcon.FOLDER)
        self.open_system_recycle_btn.setMinimumHeight(40)
        self.open_system_recycle_btn.clicked.connect(self.open_system_recycle_bin)
        system_content.addWidget(self.open_system_recycle_btn)

        system_content.addStretch()
        system_tab_layout.addWidget(system_content_card)

        # 自定义回收站标签
        self.custom_recycle_tab = QWidget()
        custom_layout = QVBoxLayout(self.custom_recycle_tab)
        custom_layout.setContentsMargins(10, 10, 10, 10)

        self.custom_table = self._create_custom_table()
        custom_layout.addWidget(self.custom_table)

        self.tabs.addTab(self.system_tab, '系统回收站')
        self.tabs.addTab(self.custom_recycle_tab, '自定义回收站')

        layout.addWidget(self.tabs)

        # 操作按钮
        buttons_layout = QHBoxLayout()

        self.restore_btn = PrimaryPushButton('恢复选中文件')
        self.restore_btn.clicked.connect(self.restore_selected)
        self.restore_btn.setEnabled(False)
        buttons_layout.addWidget(self.restore_btn)

        self.open_folder_btn = PushButton('打开回收站文件夹')
        self.open_folder_btn.clicked.connect(self.open_recycle_folder)
        buttons_layout.addWidget(self.open_folder_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # 连接表格选择事件
        self.custom_table.itemSelectionChanged.connect(self.on_selection_changed)

    def _create_custom_table(self) -> QTableWidget:
        """创建自定义回收站文件表格"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['文件名', '原始位置', '大小', '删除时间', '状态'])

        # 设置列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        # 允许选择
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)

        return table

    def load_all_items(self):
        """加载所有回收站文件"""
        self.load_custom_recycle_bin()
        self.update_stats()

    def load_custom_recycle_bin(self):
        """加载自定义回收站文件列表（扫描所有文件）"""
        # 清空表格
        self.custom_table.setRowCount(0)
        self.custom_items.clear()

        # 获取自定义回收站路径
        try:
            recycle_path = get_custom_recycle_path(self.config_mgr)
            custom_recycle = get_custom_recycle_bin(recycle_path)
            self.custom_items = custom_recycle.scan_all_items()
        except Exception as e:
            self.custom_items = []
            recycle_path = '未启用'

        # 填充表格
        for item in self.custom_items:
            row = self.custom_table.rowCount()
            self.custom_table.insertRow(row)

            item_type = item.get('type', 'unknown')
            is_managed = item.get('is_managed', False)

            # 文件名
            if item_type == 'managed':
                display_name = os.path.basename(item.get('original_name', 'Unknown'))
            elif item_type == 'unmanaged_zip':
                display_name = item.get('name', 'Unknown')
            elif item_type == 'regular':
                display_name = item.get('name', 'Unknown')
            else:
                display_name = 'Unknown'

            name_item = QTableWidgetItem(display_name)
            name_item.setData(Qt.UserRole, item)

            # 样式处理
            if item_type == 'regular':
                name_item.setForeground(Qt.gray)
                name_item.setText('📁 ' + display_name)
            elif not is_managed:
                name_item.setForeground(QColor('#8B4513'))  # 未管理显示为褐色

            self.custom_table.setItem(row, 0, name_item)

            # 原始位置
            if item_type == 'managed':
                self.custom_table.setItem(row, 1, QTableWidgetItem(item.get('original_path', '')))
            elif item_type == 'unmanaged_zip':
                self.custom_table.setItem(row, 1, QTableWidgetItem('未记录'))
            else:
                self.custom_table.setItem(row, 1, QTableWidgetItem('-'))

            # 大小
            if item_type in ['managed', 'unmanaged_zip']:
                size = item.get('original_size', 0)
            else:
                size = item.get('size', 0)
            size_str = self._format_size(size)
            self.custom_table.setItem(row, 2, QTableWidgetItem(size_str))

            # 删除时间
            if item_type == 'managed':
                deleted_at = item.get('deleted_at', '')
            elif item_type == 'unmanaged_zip':
                deleted_at = item.get('deleted_at', '')
            else:
                deleted_at = item.get('modified_at', '')

            if deleted_at:
                try:
                    dt = datetime.fromisoformat(deleted_at)
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = deleted_at[:19]
            else:
                time_str = '未知'
            self.custom_table.setItem(row, 3, QTableWidgetItem(time_str))

            # 状态
            status_item = QTableWidgetItem()
            if item_type == 'managed':
                risk_level = item.get('risk_level', 'unknown')
                status_item.setText(risk_level)
                if risk_level == 'dangerous':
                    status_item.setForeground(Qt.red)
                elif risk_level == 'suspicious':
                    status_item.setForeground(QColor('#FFA500'))
                else:
                    status_item.setForeground(Qt.darkGreen)
            elif item_type == 'unmanaged_zip':
                status_item.setText('未管理(压缩)')
                status_item.setForeground(QColor('#8B4513'))
            elif item_type == 'regular':
                status_item.setText('普通文件')
                status_item.setForeground(Qt.gray)
            else:
                status_item.setText('-')

            self.custom_table.setItem(row, 4, status_item)

    def update_stats(self):
        """更新统计信息"""
        if self.custom_items:
            total_size = sum(
                item.get('original_size', 0) if item['type'] in ['managed', 'unmanaged_zip']
                else item.get('size', 0)
                for item in self.custom_items
            )
        else:
            total_size = 0

        managed_count = sum(1 for item in self.custom_items if item.get('is_managed', False))
        unmanaged_count = len(self.custom_items) - managed_count

        self.count_label.setText(f'文件数: {len(self.custom_items)} 项')
        self.size_label.setText(f'总大小: {self._format_size(total_size)}')
        self.managed_label.setText(f'托管: {managed_count}')
        self.unmanaged_label.setText(f'未管理: {unmanaged_count}')

        try:
            recycle_path = get_custom_recycle_path(self.config_mgr)
            path_short = recycle_path if len(recycle_path) < 50 else recycle_path[:47] + '...'
            self.custom_path_label.setText(f'路径: {path_short}')
        except:
            pass

    def on_selection_changed(self):
        """处理表格选择变化"""
        selected_rows = set()
        for item in self.custom_table.selectedItems():
            selected_rows.add(item.row())
        has_selection = len(selected_rows) > 0
        self.restore_btn.setEnabled(has_selection)

    def open_system_recycle_bin(self):
        """打开 Windows 系统回收站"""
        try:
            import win32api
            # 使用 Windows 回收站的特殊标识符打开
            # 回收站 CLSID: {645FF040-5081-101B-9F08-00AA002F954E}
            recycle_path = "::{645FF040-5081-101B-9F08-00AA002F954E}"
            win32api.ShellExecute(
                0,          # hwnd
                "open",     # operation
                recycle_path,
                "",         # parameters
                None,       # directory
                1           # SW_SHOWNORMAL
            )
            InfoBar.success(
                '已打开',
                '已打开 Windows 系统回收站',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            logging.info(f"[回收站:INFO] 已打开 Windows 系统回收站 (CLSID: {recycle_path})")
        except Exception as e:
            logging.error(f"[回收站:ERROR] 打开系统回收站失败: {e}")
            QMessageBox.warning(
                self, '打开失败',
                f'无法打开系统回收站: {str(e)}\n\n请手动按下 Win + R，输入 shell:RecycleBinFolder 后按回车打开回收站'
            )

    def open_recycle_folder(self):
        """打开自定义回收站文件夹"""
        try:
            recycle_path = get_custom_recycle_path(self.config_mgr)
            if not recycle_path or not os.path.exists(recycle_path):
                QMessageBox.warning(
                    self, '路径无效',
                    '自定义回收站路径未配置或不存在。\n\n请在设置中配置回收站路径。'
                )
                return

            import win32api
            win32api.ShellExecute(
                0, 'open', recycle_path, '', None, 0x0010
            )
            InfoBar.success(
                '已打开',
                f'已打开回收站文件夹: {recycle_path}',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        except Exception as e:
            QMessageBox.warning(
                self, '打开失败',
                f'无法打开回收站文件夹: {str(e)}\n\n请检查路径权限。'
            )

    def restore_selected(self):
        """恢复选中的文件"""
        selected_rows = set()
        for item in self.custom_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            return

        reply = QMessageBox.question(
            self,
            '确认恢复',
            f'确定要恢复选中的 {len(selected_rows)} 个文件吗？',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            recycle_path = get_custom_recycle_path(self.config_mgr)
            custom_recycle = get_custom_recycle_bin(recycle_path)

            restored_count = 0
            for row in selected_rows:
                item = self.custom_table.item(row, 0).data(Qt.UserRole)
                item_type = item.get('type', 'unknown')
                file_path = item.get('path', '')

                if item_type == 'managed':
                    if custom_recycle.restore_item(item.get('id')):
                        restored_count += 1
                elif file_path:
                    if custom_recycle.restore_by_path(file_path):
                        restored_count += 1

            if restored_count > 0:
                QMessageBox.information(
                    self, '恢复完成',
                    f'成功恢复 {restored_count} 个文件'
                )
                self.load_all_items()
            else:
                QMessageBox.warning(
                    self, '恢复失败',
                    '未能恢复任何文件，请检查权限或文件状态'
                )

        except Exception as e:
            QMessageBox.critical(
                self, '恢复失败',
                f'恢复失败: {str(e)}'
            )

    def clear_custom_recycle(self):
        """清空自定义回收站（删除所有文件）"""
        reply = QMessageBox.question(
            self,
            '确认清空',
            '确定要清空自定义回收站目录中的所有文件吗？\n包括用户手动添加的文件。此操作不可恢复！',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                recycle_path = get_custom_recycle_path(self.config_mgr)
                custom_recycle = get_custom_recycle_bin(recycle_path)
                managed_count = custom_recycle.clear_all()

                # 删除目录中所有剩余文件（未被管理的）
                remaining_count = 0
                for entry in os.listdir(recycle_path):
                    entry_path = os.path.join(recycle_path, entry)
                    if os.path.isdir(entry_path):
                        shutil.rmtree(entry_path)
                        remaining_count += 1
                    elif entry != 'recycle_index.json':
                        try:
                            os.remove(entry_path)
                            remaining_count += 1
                        except:
                            pass

                total_count = managed_count + remaining_count
                QMessageBox.information(
                    self, '清空完成',
                    f'已删除 {total_count} 个文件（托管: {managed_count}, 未管理: {remaining_count}）'
                )

                self.load_all_items()
            except Exception as e:
                QMessageBox.critical(
                    self, '清空失败',
                    f'清空回收站失败: {str(e)}'
                )

    def _format_size(self, size_bytes: int) -> str:
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

    def showEvent(self, event):
        """显示事件 - 刷新数据"""
        super().showEvent(event)
        self.load_all_items()
