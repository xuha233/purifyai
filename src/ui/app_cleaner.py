"""
AppData 清理页面 UI
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QCheckBox, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, CardWidget, SwitchButton, FluentIcon
)
from PyQt5.QtGui import QColor, QPalette

from core import AppDataScanner, Cleaner, format_size, RiskLevel, ScanItem
from ui.confirm_dialog import ConfirmDialog
from ui.windows_notification import WindowsNotification
from utils.progress_bar import AnimatedProgressBar


class AppCleanerPage(QWidget):
    """用户文件夹清理页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = []
        self.checkboxes = []
        self.folder_expanded = False  # 折叠状态
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = StrongBodyLabel('用户文件夹清理')
        title.setStyleSheet('font-size: 24px;')
        layout.addWidget(title)

        desc = BodyLabel('清理应用程序数据文件夹（Roaming/Local/LocalLow）')
        desc.setStyleSheet('color: #666666; font-size: 14px;')
        layout.addWidget(desc)
        layout.addSpacing(10)

        # 文件夹类型选择（折叠菜单样式）
        folder_card = SimpleCardWidget()
        folder_card.setObjectName('folderCard')
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.setContentsMargins(15, 15, 15, 15)

        # 折叠切换按钮
        folder_header_layout = QHBoxLayout()
        folder_header_layout.addWidget(StrongBodyLabel('选择文件夹类型'))
        folder_header_layout.addStretch()

        self.folder_expand_btn = PushButton('展开')
        self.folder_expand_btn.setMaximumWidth(80)
        self.folder_expand_btn.clicked.connect(self.toggle_folder_expander)
        folder_header_layout.addWidget(self.folder_expand_btn)

        folder_layout.addLayout(folder_header_layout)

        # 文件夹选项（默认隐藏）
        self.folder_options_widget = QWidget()
        self.folder_options_widget.setVisible(False)
        self.folder_options_layout = QVBoxLayout(self.folder_options_widget)
        self.folder_options_layout.setSpacing(5)
        self.folder_options_layout.setContentsMargins(0, 5, 0, 0)

        # 已选显示
        self.selected_folders_label = BodyLabel('已选: Roaming, Local, LocalLow')
        self.selected_folders_label.setStyleSheet('color: #666666; font-size: 11px;')
        self.folder_options_layout.addWidget(self.selected_folders_label)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.folder_options_layout.addWidget(separator)
        self.folder_options_layout.addSpacing(5)

        # 选项
        self.roaming_check = QCheckBox('Roaming')
        self.roaming_check.setChecked(True)
        self.roaming_check.stateChanged.connect(self.update_selected_folders)
        self.folder_options_layout.addWidget(self.roaming_check)

        self.local_check = QCheckBox('Local')
        self.local_check.setChecked(True)
        self.local_check.stateChanged.connect(self.update_selected_folders)
        self.folder_options_layout.addWidget(self.local_check)

        self.local_low_check = QCheckBox('LocalLow')
        self.local_low_check.setChecked(True)
        self.local_low_check.stateChanged.connect(self.update_selected_folders)
        self.folder_options_layout.addWidget(self.local_low_check)

        folder_layout.addWidget(self.folder_options_widget)

        layout.addWidget(folder_card)
        layout.addSpacing(10)

        # 按钮区域
        actions_layout = QHBoxLayout()
        self.scan_btn = PrimaryPushButton('扫描 AppData')
        self.scan_btn.clicked.connect(self.on_scan)
        actions_layout.addWidget(self.scan_btn)

        self.clean_btn = PushButton('清理选中项')
        self.clean_btn.clicked.connect(self.on_clean)
        self.clean_btn.setEnabled(False)
        actions_layout.addWidget(self.clean_btn)

        # 取消扫描按钮（初始隐藏）
        self.cancel_btn = PushButton('取消扫描')
        self.cancel_btn.clicked.connect(self.on_cancel_scan)
        self.cancel_btn.setVisible(False)
        actions_layout.addWidget(self.cancel_btn)

        layout.addLayout(actions_layout)
        layout.addSpacing(10)

        # 动画进度条（带速度显示）
        self.progress_widget = AnimatedProgressBar()
        layout.addWidget(self.progress_widget)

        layout.addSpacing(10)

        # 风险区间统计
        stats_layout = QHBoxLayout()
        self.safe_label = BodyLabel('安全: 0')
        self.safe_label.setStyleSheet('color: #28a745; font-weight: bold;')
        stats_layout.addWidget(self.safe_label)

        self.suspicious_label = BodyLabel('疑似: 0')
        self.suspicious_label.setStyleSheet('color: #ffc107; font-weight: bold;')
        stats_layout.addWidget(self.suspicious_label)

        self.dangerous_label = BodyLabel('危险: 0')
        self.dangerous_label.setStyleSheet('color: #dc3545; font-weight: bold;')
        stats_layout.addWidget(self.dangerous_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        layout.addSpacing(10)

        # 扫描结果区域
        self.results_label = StrongBodyLabel('扫描结果:')
        self.results_label.setStyleSheet('font-size: 16px;')
        layout.addWidget(self.results_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.results_container)

        layout.addWidget(scroll)

        # 扫描器和清理器
        self.scanner = AppDataScanner()
        self.cleaner = Cleaner()

        # 连接扫描器信号
        self.scanner.progress.connect(self.on_scan_progress)
        self.scanner.item_found.connect(self.on_item_found)
        self.scanner.error.connect(self.on_scan_error)
        self.scanner.complete.connect(self.on_scan_complete)

        # 连接清理器信号
        self.cleaner.progress.connect(self.on_clean_progress)
        self.cleaner.item_deleted.connect(self.on_item_deleted)
        self.cleaner.error.connect(self.on_clean_error)
        self.cleaner.complete.connect(self.on_clean_complete)

        # 风险计数
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}

        # 设置和通知
        from core.config_manager import get_config_manager
        self.config_mgr = get_config_manager()
        self.notification = WindowsNotification()

        # 初始化AI状态（从设置读取）
        self.update_selected_folders()

    def toggle_folder_expander(self):
        """切换文件夹选项展开/折叠"""
        self.folder_expanded = not self.folder_expanded
        self.folder_options_widget.setVisible(self.folder_expanded)
        self.folder_expand_btn.setText('收起' if self.folder_expanded else '展开')

    def update_selected_folders(self):
        """更新已选文件夹显示"""
        selected = []
        if self.roaming_check.isChecked():
            selected.append('Roaming')
        if self.local_check.isChecked():
            selected.append('Local')
        if self.local_low_check.isChecked():
            selected.append('LocalLow')

        text = ', '.join(selected) if selected else '未选择'
        self.selected_folders_label.setText(f'已选: {text}')

    def get_notification_manager(self):
        """获取通知管理器供外部调用"""
        return self.notification

    def on_scan(self):
        """开始扫描"""
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)  # 显示取消按钮

        # 重新加载AI配置
        self.scanner.reload_ai_config()

        # 获取选中的文件夹类型（转换为小写）
        folder_types = []
        if self.roaming_check.isChecked():
            folder_types.append('roaming')
        if self.local_check.isChecked():
            folder_types.append('local')
        if self.local_low_check.isChecked():
            folder_types.append('local_low')

        if not folder_types:
            self.progress_widget.status_label.setText('请至少选择一种文件夹类型')
            self.scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            return

        # 清空之前的结果
        for checkbox, card in self.checkboxes:
            checkbox.deleteLater()
            card.deleteLater()
        self.checkboxes.clear()
        self.scan_results.clear()
        self.ai_descriptions.clear()
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
        self.update_risk_labels()

        # 启动进度跟踪
        self.progress_widget.start_progress()

        # 启动扫描
        self.scanner.start_scan(folder_types)

    def on_cancel_scan(self):
        """取消扫描"""
        self.scanner.cancel_scan()
        self.progress_widget.status_label.setText('正在取消扫描...')

    def on_scan_progress(self, message):
        """扫描进度更新"""
        self.progress_widget.status_label.setText(message)

    def on_item_found(self, item):
        """发现项目"""
        self.scan_results.append(item)

        # 更新风险计数
        self.risk_counts[item.risk_level] += 1
        self.update_risk_labels()

        # 创建项目卡片
        card = self._create_item_card(item)
        self.results_layout.addWidget(card)

        # 添加复选框
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(lambda state, cb=checkbox: self.on_checkbox_changed(cb))
        self.results_layout.addWidget(checkbox)

        self.checkboxes.append((checkbox, card, item))

        # 更新进度
        self.progress_widget.increment_progress(1, f'已发现: {item.description}')

    def _create_item_card(self, item):
        """创建项目卡片"""
        card = SimpleCardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)

        # 解析描述中的风险评估方法信息
        base_desc = item.description
        assessment_method = ""
        if "(AI:" in base_desc:
            # AI增强: "Description (AI: ...)"
            idx = base_desc.index("(AI:")
            base_desc = base_desc[:idx].strip()
            assessment_method = "AI智能"
        elif "(白名单)" in base_desc:
            # 白名单保护
            base_desc = base_desc.replace("(白名单)", "").strip()
            assessment_method = "白名单保护"
        elif "(白名单保护)" in base_desc:
            base_desc = base_desc.replace("(白名单保护)", "").strip()
            assessment_method = "白名单保护"
        else:
            # 规则引擎
            assessment_method = "规则评估"

        # 名称
        name_label = BodyLabel(base_desc)
        name_label.setStyleSheet('font-weight: bold; font-size: 14px;')
        card_layout.addWidget(name_label)

        # 路径
        path_label = BodyLabel(item.path)
        path_label.setStyleSheet('color: #999999; font-size: 12px;')
        path_label.setWordWrap(True)
        card_layout.addWidget(path_label)

        # 大小、风险评估方法和风险等级
        info_layout = QHBoxLayout()
        size_label = BodyLabel(format_size(item.size))
        size_label.setStyleSheet('color: #666666; font-size: 12px;')

        # 评估方法标签
        method_label = BodyLabel(f'[{assessment_method}]')
        if assessment_method == "AI智能":
            method_label.setStyleSheet('color: #0078D4; font-size: 11px; font-weight: bold;')
        elif assessment_method == "白名单保护":
            method_label.setStyleSheet('color: #dc3545; font-size: 11px; font-weight: bold;')
        else:  # 规则评估
            method_label.setStyleSheet('color: #28a745; font-size: 11px;')

        risk_label = BodyLabel(self._get_risk_display(item.risk_level))
        risk_label.setStyleSheet(self._get_risk_style(item.risk_level))

        info_layout.addWidget(size_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(risk_label)
        info_layout.addStretch()

        card_layout.addLayout(info_layout)

        return card

    def _get_risk_display(self, risk_level):
        """获取风险等级显示文本"""
        if risk_level == 'safe':
            return '安全'
        elif risk_level == 'suspicious':
            return '疑似'
        else:
            return '危险'

    def _get_risk_style(self, risk_level):
        """获取风险等级样式"""
        if risk_level == 'safe':
            return 'color: #28a745; font-weight: bold;'
        elif risk_level == 'suspicious':
            return 'color: #ffc107; font-weight: bold;'
        else:
            return 'color: #dc3545; font-weight: bold;'

    def on_scan_error(self, message):
        """扫描错误"""
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_widget.status_label.setText(f'扫描错误: {message}')

    def on_scan_complete(self, results):
        """扫描完成"""
        self.scan_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)  # 隐藏取消按钮

        # 检查是否被取消（空结果表示取消）
        if not results:
            self.progress_widget.finish_progress('扫描已取消')
            return

        self.progress_widget.finish_progress(f'扫描完成，发现 {len(results)} 个项目')

        # 发送通知
        if self.notification.is_enabled():
            self.notification.show_scan_complete(len(results), sum(item.size for item in results))

        if results:
            self.clean_btn.setEnabled(True)

    def on_clean(self):
        """开始清理"""
        # 获取选中的项目
        selected_items = []
        for checkbox, card, item in self.checkboxes:
            if checkbox.isChecked():
                selected_items.append(item)

        if not selected_items:
            self.progress_widget.status_label.setText('请先选择要清理的项目')
            return

        # 检查是否需要确认
        confirm_enabled = self.config_mgr.get('cleanup/confirm_dialog', True)
        if confirm_enabled:
            from PyQt5.QtWidgets import QDialog
            dialog = ConfirmDialog(selected_items, self)
            if dialog.exec_() != QDialog.Accepted:
                return

            selected_items = dialog.get_items_to_clean()

            # 如果没有选择任何项目
            if not selected_items:
                self.progress_widget.status_label.setText('未选择任何项目')
                return

        # 开始清理
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.progress_widget.start_progress(len(selected_items))
        self.progress_widget.status_label.setText('正在清理...')

        # 记录待删除项
        self._items_to_delete = len(selected_items)
        self._deleted_count = 0

        # 启动清理
        self.cleaner.start_clean(selected_items, clean_type='appdata')

    def on_clean_progress(self, message):
        """清理进度更新"""
        self.progress_widget.status_label.setText(message)

    def on_item_deleted(self, path, size):
        """项目已删除"""
        self._deleted_count += 1
        self.progress_widget.increment_progress(1, f'已删除: {path}')

        # 更新 UI 显示
        for i, (checkbox, card, item) in enumerate(self.checkboxes):
            if item.path == path:
                self.checkboxes[i][0].setChecked(False)
                self.checkboxes[i][0].setEnabled(False)
                self.checkboxes[i][0].hide()
                self.checkboxes[i][1].hide()
                break

    def on_clean_error(self, message):
        """清理错误"""
        self.progress_widget.status_label.setText(f'清理错误: {message}')

    def on_clean_complete(self, result):
        """清理完成"""
        self.scan_btn.setEnabled(True)

        if result['success']:
            deleted_count = result['deleted_count']
            deleted_size = result['total_size']
            self.progress_widget.finish_progress(
                f'清理完成！删除了 {deleted_count} 个项目，释放 {format_size(deleted_size)}'
            )

            # 发送通知
            if self.notification.is_enabled():
                self.notification.show_clean_complete(deleted_count, deleted_size)

            # 移除已删除的项目
            new_checkboxes = []
            for checkbox, card, item in self.checkboxes:
                if checkbox.isEnabled():
                    new_checkboxes.append((checkbox, card, item))
                else:
                    card.deleteLater()
                    checkbox.deleteLater()

            self.checkboxes = new_checkboxes

            if not self.checkboxes:
                self.clean_btn.setEnabled(False)
        else:
            self.status_label.setText(f'清理失败: {result["errors"]}')

    def on_checkbox_changed(self, checkbox):
        """复选框状态变化"""
        pass

    def update_risk_labels(self):
        """更新风险标签"""
        self.safe_label.setText(f'安全: {self.risk_counts["safe"]}')
        self.suspicious_label.setText(f'疑似: {self.risk_counts["suspicious"]}')
        self.dangerous_label.setText(f'危险: {self.risk_counts["dangerous"]}')
