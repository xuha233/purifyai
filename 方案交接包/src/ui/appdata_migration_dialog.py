"""
AppData 文件夹迁移对话框 UI

提供友好的界面用于:
- 扫描可迁移的大型 AppData 文件夹
- 选择目标磁盘和路径
- 执行迁移操作
- 查看和管理迁移历史
- 回滚已迁移的项目
"""
import os
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QListWidgetItem,
    QFileDialog, QLabel, QCheckBox, QMessageBox, QScrollArea, QFrame, QSplitter
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ProgressBar, FluentIcon, InfoBar, InfoBarPosition,
    MessageBox, ComboBox
)
import psutil

from core.appdata_migration import (
    AppDataMigrationTool, ScanMigrationThread, MigrateThread,
    RollbackThread, MigrationItem, COMMON_APPS
)
from utils.logger import get_logger

logger = get_logger(__name__)


class MigrationItemWidget(QWidget):
    """迁移项目列表项组件"""

    def __init__(self, item: MigrationItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.selected = False
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setFixedSize(380, 80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.stateChanged.connect(self.on_check_changed)
        layout.addWidget(self.checkbox)

        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 名称 + 风险标签
        name_layout = QHBoxLayout()
        name_layout.setSpacing(6)

        name_label = BodyLabel(self.item.name)
        name_label.setStyleSheet('font-size: 13px; font-weight: 600; color: #2c2c2c;')
        name_layout.addWidget(name_label)

        # 风险标签
        risk_colors = {
            'safe': ('#e6f7e6', '#28a745'),      # 绿色
            'wary': ('#fff3e0', '#ff9800'),     # 橙色
            'dangerous': ('#fee2e2', '#dc3545'), # 红色
            'unknown': ('#f5f5f5', '#666666')     # 灰色
        }
        risk_labels = {
            'safe': '可迁移',
            'wary': '需谨慎',
            'dangerous': '不推荐',
            'unknown': '未知'
        }

        bg_color, fg_color = risk_colors.get(self.item.risk_level, risk_colors['unknown'])
        risk_text = risk_labels.get(self.item.risk_level, '未知')

        risk_label = BodyLabel(risk_text)
        risk_label.setStyleSheet(f'''
            font-size: 10px; padding: 2px 8px; border-radius: 4px;
            background: {bg_color}; color: {fg_color}; font-weight: 500;
        ''')
        name_layout.addWidget(risk_label)
        name_layout.addStretch()

        info_layout.addLayout(name_layout)

        # 路径（截断）
        path_display = self.item.path
        if len(path_display) > 45:
            path_display = '...' + path_display[-45:]
        path_label = BodyLabel(path_display)
        path_label.setStyleSheet('font-size: 11px; color: #666;')
        info_layout.addWidget(path_label)

        # 大小
        size_text = f"{self.item.size / (1024*1024):.1f} MB"
        if self.item.size >= 1024*1024*1024:
            size_text = f"{self.item.size / (1024*1024*1024):.2f} GB"
        size_label = BodyLabel(size_text)
        size_label.setStyleSheet('font-size: 12px; font-weight: 500; color: #0066cc;')
        info_layout.addWidget(size_label)

        layout.addLayout(info_layout, stretch=1)

    def on_check_changed(self, state):
        """复选框状态改变"""
        self.selected = (state == Qt.Checked)

    def is_selected(self) -> bool:
        """是否选中"""
        return self.selected


class AppDataMigrationDialog(QDialog):
    """AppData 文件夹迁移对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AppData 文件夹迁移工具")
        self.setMinimumSize(900, 600)

        self.migration_tool = AppDataMigrationTool()
        self.folders: List[MigrationItem] = []
        self.folder_widgets: List[MigrationItemWidget] = []

        self.scan_thread = None
        self.migrate_thread = None
        self.rollback_thread = None

        self.init_ui()
        self.check_prerequisites()
        self.load_target_info()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # ========== 标题区 ==========
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = SubtitleLabel("AppData 文件夹迁移工具")
        title.setStyleSheet('font-size: 20px;')
        header_layout.addWidget(title)
        header_layout.addSpacing(20)

        # 描述
        desc = BodyLabel("将大型 AppData 文件夹迁移到其他磁盘，通过符号链接实现透明重定向。")
        desc.setStyleSheet('color: #666; font-size: 13px;')
        header_layout.addWidget(desc)
        header_layout.addStretch()

        layout.addWidget(header)

        # ========== 分割器 ==========
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #e0e0e0;
            }
        """)

        # ========== 左侧：扫描和控制 ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 扫描设置卡片
        scan_card = SimpleCardWidget()
        scan_card_layout = QVBoxLayout(scan_card)
        scan_card_layout.setContentsMargins(16, 16, 16, 16)
        scan_card_layout.setSpacing(10)

        scan_card_layout.addWidget(BodyLabel("扫描设置"))

        # 扫描选项
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)

        options = [
            ('scan_roaming', 'Roaming', True),
            ('scan_local', 'Local', True),
            ('scan_local_low', 'LocalLow', False)
        ]

        for attr_name, label_text, checked in options:
            opt_widget = QWidget()
            opt_layout = QHBoxLayout(opt_widget)
            opt_layout.setContentsMargins(0, 0, 0, 0)
            opt_layout.setSpacing(6)

            checkbox = QCheckBox(label_text)
            checkbox.setChecked(checked)
            setattr(self, attr_name, checkbox)
            opt_layout.addWidget(checkbox)
            opt_layout.addStretch()

            options_layout.addWidget(opt_widget)

        scan_card_layout.addLayout(options_layout)

        # 最小大小
        size_layout = QHBoxLayout()
        size_layout.addWidget(BodyLabel("最小文件夹大小:"))
        self.min_size_combo = ComboBox()
        self.min_size_combo.addItems(['50 MB', '100 MB', '250 MB', '500 MB', '1 GB'])
        self.min_size_combo.setCurrentIndex(1)  # 100 MB 默认
        self.min_size_combo.setFixedWidth(120)
        size_layout.addWidget(self.min_size_combo)
        size_layout.addStretch()
        scan_card_layout.addLayout(size_layout)

        # 扫描按钮区域
        scan_btn_layout = QHBoxLayout()
        scan_btn_layout.addStretch()

        self.scan_btn = PrimaryPushButton(FluentIcon.SEARCH, "扫描文件夹")
        self.scan_btn.clicked.connect(self.scan_folders)
        self.scan_btn.setFixedHeight(40)
        scan_btn_layout.addWidget(self.scan_btn)
        scan_card_layout.addLayout(scan_btn_layout)

        left_layout.addWidget(scan_card)

        # 目标设置卡片
        target_card = SimpleCardWidget()
        target_card_layout = QVBoxLayout(target_card)
        target_card_layout.setContentsMargins(16, 16, 16, 16)
        target_card_layout.setSpacing(10)

        target_card_layout.addWidget(BodyLabel("目标位置"))

        # 磁盘选择
        drive_layout = QHBoxLayout()
        drive_layout.addWidget(BodyLabel("目标磁盘:"))
        self.drive_combo = ComboBox()
        self.drive_combo.setFixedWidth(200)
        self.drive_combo.currentIndexChanged.connect(self.on_drive_changed)
        drive_layout.addWidget(self.drive_combo)
        target_card_layout.addLayout(drive_layout)

        # 路径输入
        path_input_layout = QHBoxLayout()
        self.target_path_edit = PushButton()  # 用于显示路径
        self.target_path_edit.setEnabled(False)
        self.target_path_edit.setFixedHeight(32)
        path_input_layout.addWidget(self.target_path_edit)
        path_input_layout.addStretch()
        target_card_layout.addLayout(path_input_layout)

        # 磁盘信息
        self.drive_info = BodyLabel()
        self.drive_info.setStyleSheet('color: #666; font-size: 12px;')
        target_card_layout.addWidget(self.drive_info)

        left_layout.addWidget(target_card)

        # 说明卡片
        info_card = SimpleCardWidget()
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(16, 16, 16, 16)
        info_card_layout.setSpacing(10)

        info_label = BodyLabel("重要说明:")
        info_label.setStyleSheet('font-weight: 600;')
        info_card_layout.addWidget(info_label)

        info_texts = [
            "⚠️ 迁移过程会停止相关应用进程，请先保存工作",
            "⚠️ 迁移需要管理员权限以创建符号链接",
            "✓ 迁移后原路径将通过符号链接指向新位置",
            "✓ 迁移历史已保存，可随时回滚",
            "⚠️ 系统关键文件夹不建议迁移"
        ]

        for text in info_texts:
            label = BodyLabel(text)
            label.setStyleSheet('font-size: 12px; color: #666; margin-left: 8px;')
            label.setWordWrap(True)
            info_card_layout.addWidget(label)

        left_layout.addWidget(info_card)
        left_layout.addStretch()

        # ========== 右侧：文件夹列表和操作 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 列表标题
        list_header = QWidget()
        list_header_layout = QHBoxLayout(list_header)
        list_header_layout.setContentsMargins(0, 0, 0, 0)

        self.list_title = SubtitleLabel("可迁移的文件夹")
        list_header_layout.addWidget(self.list_title)
        list_header_layout.addStretch()

        right_layout.addWidget(list_header)

        # 文件夹列表（滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; }")

        self.folder_list_widget = QWidget()
        self.folder_list_layout = QVBoxLayout(self.folder_list_widget)
        self.folder_list_layout.setContentsMargins(8, 8, 8, 8)
        self.folder_list_layout.setSpacing(4)
        self.folder_list_layout.setAlignment(Qt.AlignTop)

        # 空状态
        self.empty_label = BodyLabel("点击'扫描文件夹'查找可迁移的 AppData 文件夹")
        self.empty_label.setStyleSheet('color: #999; font-size: 13px;')
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.folder_list_layout.addWidget(self.empty_label)

        scroll.setWidget(self.folder_list_widget)
        right_layout.addWidget(scroll, stretch=1)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        self.status_label = BodyLabel()
        self.status_label.setStyleSheet('color: #666; font-size: 12px;')
        self.status_label.setVisible(False)
        right_layout.addWidget(self.status_label)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.history_btn = PushButton(FluentIcon.HISTORY, "迁移历史")
        self.history_btn.clicked.connect(self.show_history)
        btn_layout.addWidget(self.history_btn)

        self.rollback_btn = PushButton(FluentIcon.UPDATE, "回滚")
        self.rollback_btn.clicked.connect(self.rollback_migration)
        self.rollback_btn.setEnabled(False)
        btn_layout.addWidget(self.rollback_btn)

        btn_layout.addStretch()

        self.select_all_btn = PushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_folders)
        btn_layout.addWidget(self.select_all_btn)

        self.migrate_btn = PrimaryPushButton(FluentIcon.SEND, "开始迁移")
        self.migrate_btn.clicked.connect(self.start_migration)
        self.migrate_btn.setEnabled(False)
        self.migrate_btn.setFixedHeight(40)
        self.migrate_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.migrate_btn)

        right_layout.addLayout(btn_layout)

        # 添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

    def check_prerequisites(self):
        """检查前置条件"""
        if not self.migration_tool.is_admin():
            InfoBar.warning(
                "需要管理员权限",
                "创建符号链接需要管理员权限，请以管理员身份运行程序。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

    def load_target_info(self):
        """加载目标磁盘信息"""
        drives = self.migration_tool.get_available_drives()
        self.drive_combo.clear()

        for i, drive in enumerate(drives):
            name = drive['drive']
            free_gb = drive['free'] / (1024 ** 3)
            display_text = f"{name} (可用: {free_gb:.1f} GB)"
            self.drive_combo.addItem(display_text, drive)

            # 默认选择第一个非C盘
            if i > 0 and 'C:' not in name:
                self.drive_combo.setCurrentIndex(i)

        if drives:
            self.on_drive_changed()

    def on_drive_changed(self):
        """磁盘选择改变"""
        current_data = self.drive_combo.currentData()
        if current_data:
            drive = current_data
            total_gb = drive['total'] / (1024 ** 3)
            used_gb = drive['used'] / (1024 ** 3)
            free_gb = drive['free'] / (1024 ** 3)
            percent = drive['percent']

            self.drive_info.setText(
                f"总容量: {total_gb:.0f} GB | 已用: {used_gb:.0f} GB | "
                f"可用: {free_gb:.1f} GB ({100 - percent:.0f}%)"
            )

            # 更新目标路径
            target_path = os.path.join(drive['drive'], 'AppData_Backup')
            self.target_path_edit.setText(target_path)

    def scan_folders(self):
        """扫描可迁移文件夹"""
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText("正在扫描...")

        # 清空列表
        self._clear_folder_list()
        self.folder_widgets.clear()
        self.folders.clear()
        self.migrate_btn.setEnabled(False)

        # 获取最小大小
        min_size_text = self.min_size_combo.currentText()
        min_size_mb = int(min_size_text.split()[0])

        # 创建扫描线程
        self.scan_thread = ScanMigrationThread(
            min_size_mb=min_size_mb,
            scan_roaming=self.scan_roaming.isChecked(),
            scan_local=self.scan_local.isChecked(),
            scan_local_low=self.scan_local_low.isChecked()
        )
        self.scan_thread.progress.connect(self._update_scan_progress)
        self.scan_thread.item_found.connect(self._add_folder_item)
        self.scan_thread.complete.connect(self._scan_complete)
        self.scan_thread.error.connect(self._scan_error)
        self.scan_thread.start()

    def _update_scan_progress(self, current: int, total: int):
        """更新扫描进度"""
        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
            self.status_label.setText(f"扫描中... ({current}/{total})")

    def _add_folder_item(self, item: MigrationItem):
        """添加文件夹到列表"""
        self.folders.append(item)

        widget = MigrationItemWidget(item)
        self.folder_widgets.append(widget)

        # 移除空状态
        if self.empty_label:
            self.empty_label.deleteLater()
            self.empty_label = None

        self.folder_list_layout.addWidget(widget)

    def _clear_folder_list(self):
        """清空文件夹列表"""
        while self.folder_list_layout.count():
            item = self.folder_list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.folder_list_layout.update()

    def _scan_complete(self, folders: List[MigrationItem]):
        """扫描完成"""
        self.folders = folders
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"扫描完成，发现 {len(folders)} 个文件夹")
        self.list_title.setText(f"可迁移的文件夹 ({len(folders)})")

        if folders:
            self.migrate_btn.setEnabled(True)
            self.select_all_btn.setEnabled(True)
        else:
            self.empty_label = BodyLabel("未发现可迁移的大型文件夹（尝试降低最小文件夹大小阈值）")
            self.empty_label.setStyleSheet('color: #999; font-size: 13px;')
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.folder_list_layout.addWidget(self.empty_label)
            self.select_all_btn.setEnabled(False)

    def _scan_error(self, message: str):
        """扫描错误"""
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        InfoBar.error('扫描失败', message, parent=self, position=InfoBarPosition.TOP)

    def select_all_folders(self):
        """全选/取消全选"""
        if hasattr(self, '_all_selected') and self._all_selected:
            # 取消全选
            for widget in self.folder_widgets:
                widget.checkbox.setChecked(False)
            self.select_all_btn.setText("全选")
            self._all_selected = False
        else:
            # 全选
            selected_count = 0
            for widget in self.folder_widgets:
                # 只全选安全的和疑似的，不选危险的
                if widget.item.risk_level != 'dangerous':
                    widget.checkbox.setChecked(True)
                    selected_count += 1
            self.select_all_btn.setText(f"取消全选 ({selected_count})")
            self._all_selected = True

    def get_selected_folders(self) -> List[MigrationItem]:
        """获取选中的文件夹"""
        selected = []
        for i, widget in enumerate(self.folder_widgets):
            if widget.checkbox.isChecked():
                selected.append(self.folders[i])
        return selected

    def start_migration(self):
        """开始迁移"""
        # 检查管理员权限
        if not self.migration_tool.is_admin():
            InfoBar.error('权限不足', '创建符号链接需要管理员权限，请以管理员身份运行程序。',
                         parent=self, position=InfoBarPosition.TOP, duration=5000)
            return

        # 获取选中的文件夹
        selected = self.get_selected_folders()
        if not selected:
            InfoBar.warning('提示', '请先选择要迁移的文件夹',
                           parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        # 检查危险的文件夹
        dangerous = [f for f in selected if f.risk_level == 'dangerous']
        if dangerous:
            confirm = QMessageBox.question(
                self,
                '警告',
                f'您选择了 {len(dangerous)} 个不推荐的文件夹（标记为红色），\n'
                f'这些文件夹可能包含系统关键数据。\n\n'
                f'是否继续？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

        # 确认对话框
        total_size = sum(f.size for f in selected) / (1024 ** 3)
        msg_box = MessageBox(
            '确认迁移',
            f'即将迁移 {len(selected)} 个文件夹到目标位置\n\n'
            f'总大小: {total_size:.2f} GB\n\n'
            f'⚠️ 迁移过程会停止相关应用进程！\n'
            f'⚠️ 请确保已保存所有工作！',
            self
        )
        msg_box.yesButton.setText('开始迁移')
        msg_box.cancelButton.setText('取消')

        if msg_box.exec() != MessageBox.Yes:
            return

        # 获取目标路径
        target_base = self.target_path_edit.text()
        if not target_base:
            InfoBar.error('错误', '请选择目标位置',
                         parent=self, position=InfoBarPosition.TOP)
            return

        # 开始迁移
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.scan_btn.setEnabled(False)
        self.migrate_btn.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.history_btn.setEnabled(False)
        self.rollback_btn.setEnabled(False)

        self.migrate_thread = MigrateThread(selected, target_base)
        self.migrate_thread.progress.connect(self.progress_bar.setValue)
        self.migrate_thread.status.connect(self._migration_status)
        self.migrate_thread.complete.connect(self._migration_complete)
        self.migrate_thread.error.connect(self._migration_error)
        self.migrate_thread.start()

    def _migration_status(self, message: str):
        """迁移状态更新"""
        self.status_label.setText(message)

    def _migration_complete(self, success: bool, message: str):
        """迁移完成"""
        self.scan_btn.setEnabled(True)
        self.migrate_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.history_btn.setEnabled(True)
        self.status_label.setText(message)
        self.progress_bar.setVisible(False)

        if success:
            info_bar = InfoBar.success('成功', message, parent=self,
                                      position=InfoBarPosition.TOP, duration=3000)

            # 保存迁移记录
            if self.migrate_thread.migrated_items:
                history = self.migration_tool.get_migration_history()
                for record in self.migrate_thread.migrated_items:
                    self.migration_tool.save_migration_record(record)

                # 启用回滚按钮
                self.rollback_btn.setEnabled(True)

                # 延迟关闭对话框
                QTimer.singleShot(2000, lambda: self.close())
        else:
            InfoBar.error('失败', message, parent=self, position=InfoBarPosition.TOP)

    def _migration_error(self, message: str):
        """迁移错误"""
        self.scan_btn.setEnabled(True)
        self.migrate_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.history_btn.setEnabled(True)
        self.status_label.setText("迁移失败")
        InfoBar.error('迁移失败', message, parent=self, position=InfoBarPosition.TOP)

    def show_history(self):
        """显示迁移历史"""
        history = self.migration_tool.get_migration_history()

        if not history:
            InfoBar.info('提示', '暂无迁移历史记录',
                        parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        # 创建历史对话框
        history_dialog = MigrationHistoryDialog(history, self)
        history_dialog.exec()

        # 更新回滚按钮状态
        self.rollback_btn.setEnabled(bool(history))

    def rollback_migration(self):
        """回滚迁移"""
        history = self.migration_tool.get_migration_history()
        if not history:
            InfoBar.info('提示', '没有可回滚的迁移记录',
                        parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        # 选择要回滚的项目
        rollback_dialog = RollbackDialog(history, self)
        if rollback_dialog.exec() == QDialog.Accepted:
            item = rollback_dialog.selected_item

            # 确认回滚
            msg_box = MessageBox(
                '确认回滚',
                f'即将回滚迁移项目:\n\n'
                f'名称: {item.get("name", "unknown")}\n'
                f'源路径: {item.get("source", "")}\n\n'
                f'此操作将移除符号链接并将文件移回原位。',
                self
            )
            msg_box.yesButton.setText('确认回滚')
            msg_box.cancelButton.setText('取消')

            if msg_box.exec() != MessageBox.Yes:
                return

            # 执行回滚
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setVisible(True)
            self.status_label.setText("正在回滚...")
            self.scan_btn.setEnabled(False)
            self.migrate_btn.setEnabled(False)
            self.select_all_btn.setEnabled(False)
            self.history_btn.setEnabled(False)

            self.rollback_thread = RollbackThread(item)
            self.rollback_thread.progress.connect(self.progress_bar.setValue)
            self.rollback_thread.status.connect(self._rollback_status)
            self.rollback_thread.complete.connect(self._rollback_complete)
            self.rollback_thread.error.connect(self._rollback_error)
            self.rollback_thread.start()

    def _rollback_status(self, message: str):
        """回滚状态更新"""
        self.status_label.setText(message)

    def _rollback_complete(self, success: bool, message: str):
        """回滚完成"""
        self.scan_btn.setEnabled(True)
        self.migrate_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.history_btn.setEnabled(True)
        self.status_label.setText(message)
        self.progress_bar.setVisible(False)

        if success:
            InfoBar.success('成功', message, parent=self, position=InfoBarPosition.TOP)
            # 更新回滚按钮状态
            history = self.migration_tool.get_migration_history()
            self.rollback_btn.setEnabled(bool(history))
        else:
            InfoBar.error('失败', message, parent=self, position=InfoBarPosition.TOP)

    def _rollback_error(self, message: str):
        """回滚错误"""
        self.scan_btn.setEnabled(True)
        self.migrate_btn.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.history_btn.setEnabled(True)
        self.status_label.setText("回滚失败")
        InfoBar.error('回滚失败', message, parent=self, position=InfoBarPosition.TOP)


class MigrationHistoryDialog(QDialog):
    """迁移历史对话框"""

    def __init__(self, history: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("迁移历史")
        self.setMinimumSize(600, 400)
        self.history = history
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title = SubtitleLabel(f"迁移历史 ({len(self.history)} 条记录)")
        layout.addWidget(title)

        # 历史列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setSpacing(8)

        for item in reversed(self.history):
            # 创建历史项卡片
            card = SimpleCardWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(8)

            # 第一行：名称 + 时间
            row1 = QHBoxLayout()
            name_label = BodyLabel(item.get('name', 'unknown'))
            name_label.setStyleSheet('font-size: 14px; font-weight: 600;')
            row1.addWidget(name_label)
            row1.addStretch()

            timestamp = item.get('timestamp', '')
            if timestamp:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_label = BodyLabel(dt.strftime('%Y-%m-%d %H:%M'))
                    time_label.setStyleSheet('color: #666; font-size: 12px;')
                    row1.addWidget(time_label)
                except:
                    pass

            card_layout.addLayout(row1)

            # 第二行：路径
            row2 = QHBoxLayout()
            source_label = BodyLabel(f"源: {item.get('source', '')[:50]}...")
            source_label.setStyleSheet('color: #666; font-size: 12px;')
            row2.addWidget(source_label)
            row2.addStretch()
            card_layout.addLayout(row2)

            # 第三行：目标 + 大小
            row3 = QHBoxLayout()
            target_label = BodyLabel(f"目标: {item.get('target', '')[:50]}...")
            target_label.setStyleSheet('color: #666; font-size: 12px;')
            row3.addWidget(target_label)
            row3.addStretch()

            size = item.get('size', 0)
            if size >= 1024 * 1024 * 1024:
                size_text = f"{size / (1024**3):.2f} GB"
            else:
                size_text = f"{size / (1024**2):.1f} MB"
            size_label = BodyLabel(size_text)
            size_label.setStyleSheet('color: #0066cc; font-size: 12px; font-weight: 500;')
            row3.addWidget(size_label)

            card_layout.addLayout(row3)

            list_layout.addWidget(card)

        list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, stretch=1)

        # 关闭按钮
        close_btn = PrimaryPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class RollbackDialog(QDialog):
    """回滚选择对话框"""

    def __init__(self, history: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要回滚的项目")
        self.setMinimumSize(600, 400)
        self.history = history
        self.selected_item = None
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("选择要回滚的迁移项目")
        layout.addWidget(title)

        # 项目列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setSpacing(8)

        for item in reversed(self.history):
            # 创建项卡片（可点击）
            card = SimpleCardWidget()
            card.setCursor(Qt.PointingHandCursor)
            card.setProperty('record_data', item)
            card.mousePressEvent = lambda e, i=item, c=card: self.on_card_clicked(i, c)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(6)

            # 第一行：名称
            row1 = QHBoxLayout()
            name_label = BodyLabel(item.get('name', 'unknown'))
            name_label.setStyleSheet('font-size: 14px; font-weight: 600;')
            row1.addWidget(name_label)
            row1.addStretch()

            timestamp = item.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_label = BodyLabel(dt.strftime('%Y-%m-%d %H:%M'))
                    time_label.setStyleSheet('color: #666; font-size: 12px;')
                    row1.addWidget(time_label)
                except:
                    pass

            card_layout.addLayout(row1)

            # 第二行：大小
            size = item.get('size', 0)
            if size >= 1024 * 1024 * 1024:
                size_text = f"{size / (1024**3):.2f} GB"
            else:
                size_text = f"{size / (1024**2):.1f} MB"
            size_label = BodyLabel(f"大小: {size_text}")
            size_label.setStyleSheet('color: #666; font-size: 12px;')
            card_layout.addWidget(size_label)

            list_layout.addWidget(card)

        list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, stretch=1)

        # 提示
        hint = BodyLabel("点击项目卡片选择，然后点击'回滚'按钮")
        hint.setStyleSheet('color: #999; font-style: italic;')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

    def on_card_clicked(self, item: Dict, card):
        """卡片点击事件"""
        # 取消其他卡片的选中样式
        for i in range(self.layout().itemAt(0).widget().layout().count() - 1):
            widget = self.layout().itemAt(0).widget().layout().itemAt(i).widget()
            if widget and isinstance(widget, SimpleCardWidget):
                widget.setStyleSheet('SimpleCardWidget { border: 1px solid #e0e0e0; border-radius: 8px; }')

        # 设置选中样式
        card.setStyleSheet('SimpleCardWidget { border: 2px solid #0078D4; border-radius: 8px; }')
        self.selected_item = item

        # 自动关闭并返回选中项
        self.accept()
