"""
白名单管理对话框
提供可视化的白名单管理功能
"""
import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QFileDialog, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QComboBox, QInputDialog
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, LineEdit, ComboBox
)

from core.whitelist import get_whitelist


class WhitelistDialog(QDialog):
    """白名单管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('白名单管理')
        self.setFixedSize(600, 450)
        self.whitelist = get_whitelist()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = StrongBodyLabel('白名单管理')
        title.setStyleSheet('font-size: 18px;')
        layout.addWidget(title)

        # 描述
        desc = BodyLabel('添加路径或模式以保护重要文件不被清理')
        desc.setStyleSheet('color: #666666; font-size: 12px;')
        layout.addWidget(desc)

        # 筛选下拉框
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(BodyLabel('筛选:'))
        self.filter_combo = ComboBox()
        self.filter_combo.addItems(['全部', '路径', '模式'])
        self.filter_combo.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 白名单列表
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet('''
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
            QListWidget::item:selected {
                background: #e6f7ff;
            }
        ''')
        layout.addWidget(self.list_widget)

        # 操作按钮
        actions_layout = QHBoxLayout()

        self.add_path_btn = PushButton('添加路径')
        self.add_path_btn.clicked.connect(self.add_path)
        actions_layout.addWidget(self.add_path_btn)

        self.add_pattern_btn = PushButton('添加模式')
        self.add_pattern_btn.clicked.connect(self.add_pattern)
        actions_layout.addWidget(self.add_pattern_btn)

        self.import_btn = PushButton('导入')
        self.import_btn.clicked.connect(self.import_whitelist)
        actions_layout.addWidget(self.import_btn)

        self.export_btn = PushButton('导出')
        self.export_btn.clicked.connect(self.export_whitelist)
        actions_layout.addWidget(self.export_btn)

        self.remove_btn = PushButton('删除')
        self.remove_btn.clicked.connect(self.remove_selected)
        actions_layout.addWidget(self.remove_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # 统计信息
        self.stats_label = BodyLabel('')
        self.stats_label.setStyleSheet('color: #666666; font-size: 11px;')
        layout.addWidget(self.stats_label)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.close_btn = PushButton('关闭')
        self.close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.close_btn)

        self.apply_btn = PrimaryPushButton('确定')
        self.apply_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.apply_btn)

        layout.addLayout(bottom_layout)

    def load_data(self):
        """加载白名单数据"""
        self.list_widget.clear()

        paths, patterns = self.whitelist.get_all()
        filter_type = self.filter_combo.currentText()

        items_to_show = []
        if filter_type == '全部' or filter_type == '路径':
            for path in paths:
                item = QListWidgetItem(f'路径: {path}')
                item.setData(Qt.UserRole, ('path', path))
                items_to_show.append(item)

        if filter_type == '全部' or filter_type == '模式':
            for pattern in patterns:
                item = QListWidgetItem(f'模式: {pattern}')
                item.setData(Qt.UserRole, ('pattern', pattern))
                items_to_show.append(item)

        self.list_widget.addItems([item.text() for item in items_to_show])
        for i, item in enumerate(items_to_show):
            list_item = self.list_widget.item(i)
            list_item.setData(Qt.UserRole, item.data(Qt.UserRole))

        # 更新统计信息
        self.update_stats()

    def update_stats(self):
        """更新统计信息"""
        path_count, pattern_count = self.whitelist.get_all()
        total = path_count + pattern_count
        self.stats_label.setText(f'总计: {total} 项（路径: {path_count}, 模式: {pattern_count}）')

    def add_path(self):
        """添加路径"""
        dialog = QFileDialog()
        path = dialog.getExistingDirectory(self, '选择要保护的文件夹')
        if not path:
            file_path = dialog.getOpenFileName(self, '选择要保护的文件')
            if file_path and file_path[0]:
                path = file_path[0]

        if path:
            if self.whitelist.add_path(path):
                self.load_data()
                QMessageBox.information(self, '成功', f'已添加路径: {path}')
            else:
                QMessageBox.warning(self, '警告', '该路径已在白名单中')

    def add_pattern(self):
        """添加模式"""
        pattern, ok = QInputDialog.getText(
            self,
            '添加模式',
            '输入模式（支持通配符 * 和 ?）:',
            QLineEdit.Normal,
            '*.log'
        )
        if ok and pattern:
            if self.whitelist.add_pattern(pattern):
                self.load_data()
                QMessageBox.information(self, '成功', f'已添加模式: {pattern}')
            else:
                QMessageBox.warning(self, '警告', '该模式已在白名单中')

    def remove_selected(self):
        """删除选中的项目"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请先选择要删除的项目')
            return

        data = current_item.data(Qt.UserRole)
        if not data:
            return

        item_type, value = data

        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除"{value}"吗？',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if item_type == 'path':
                self.whitelist.remove_path(value)
            elif item_type == 'pattern':
                self.whitelist.remove_pattern(value)

            self.load_data()
            QMessageBox.information(self, '成功', '已删除')

    def import_whitelist(self):
        """导入白名单"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '导入白名单',
            '',
            'JSON 文件 (*.json);;所有文件 (*.*)'
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                count = 0
                for path in data.get('paths', []):
                    if self.whitelist.add_path(path):
                        count += 1
                for pattern in data.get('patterns', []):
                    if self.whitelist.add_pattern(pattern):
                        count += 1

                self.load_data()
                QMessageBox.information(self, '成功', f'成功导入 {count} 项')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')

    def export_whitelist(self):
        """导出白名单"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '导出白名单',
            '',
            'JSON 文件 (*.json);;所有文件 (*.*)'
        )

        if file_path:
            try:
                paths, patterns = self.whitelist.get_all()
                data = {
                    'paths': paths,
                    'patterns': patterns
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(self, '成功', f'已导出到: {file_path}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')
