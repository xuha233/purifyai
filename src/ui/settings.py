"""
设置页面 - 配置应用程序设置
使用 ConfigManager 实现配置文件存储（JSON 格式）
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QLineEdit, QMessageBox, QSpinBox, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton, PrimaryPushButton, SwitchButton, ComboBox, LineEdit, TimeEdit, SpinBox as QFSpinBox

from whitelist_dialog import WhitelistDialog
from utils.startup import get_startup_manager

# 导入配置管理器
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.config_manager import get_config_manager


class SpinBox(QSpinBox):
    """SpinBox 包装类"""
    def __init__(self, minimum=None, maximum=None, value=None, spin=None, parent=None):
        super().__init__(parent)
        if minimum is not None:
            self.setMinimum(minimum)
        if maximum is not None:
            self.setMaximum(maximum)
        if value is not None:
            self.setValue(value)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = get_config_manager()
        self.console_callback = None  # 回调函数
        self.init_ui()
        self.load_settings()

    def set_console_callback(self, callback):
        """设置开发者控制台切换回调"""
        self.console_callback = callback

    def on_console_changed(self, checked: bool):
        """处理开发者控制台切换"""
        self.config_mgr.set('developer_console/enabled', checked)

        # 通过回调通知主窗口
        if self.console_callback:
            self.console_callback(checked)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = StrongBodyLabel('设置')
        title.setStyleSheet('font-size: 24px;')
        layout.addWidget(title)

        desc = BodyLabel('应用程序设置和首选项')
        desc.setStyleSheet('color: #666; font-size: 14px;')
        layout.addWidget(desc)
        layout.addSpacing(20)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # 通用设置
        general_card = SimpleCardWidget()
        general_layout = QVBoxLayout(general_card)
        general_layout.setContentsMargins(15, 15, 15, 15)

        general_title = StrongBodyLabel('通用设置')
        general_title.setStyleSheet('font-size: 16px;')
        general_layout.addWidget(general_title)
        general_layout.addSpacing(10)

        # 启用通知
        notify_layout = QHBoxLayout()
        notify_layout.addWidget(BodyLabel('启用通知:'))
        self.notify_switch = SwitchButton()
        self.notify_switch.checkedChanged.connect(self.on_notify_changed)
        notify_layout.addWidget(self.notify_switch)
        notify_layout.addStretch()
        general_layout.addLayout(notify_layout)
        general_layout.addSpacing(10)

        # 开机启动
        startup_layout = QHBoxLayout()
        startup_layout.addWidget(BodyLabel('开机启动:'))
        self.startup_switch = SwitchButton()
        self.startup_switch.checkedChanged.connect(self.on_startup_changed)
        startup_layout.addWidget(self.startup_switch)
        startup_layout.addStretch()
        general_layout.addLayout(startup_layout)

        # 开发者控制台
        console_layout = QHBoxLayout()
        console_layout.addWidget(BodyLabel('开发者控制台:'))
        self.console_switch = SwitchButton()
        console_enabled = self.config_mgr.get('developer_console/enabled', False)
        self.console_switch.setChecked(console_enabled)
        self.console_switch.checkedChanged.connect(self.on_console_changed)
        console_layout.addWidget(self.console_switch)
        console_layout.addStretch()
        general_layout.addLayout(console_layout)

        scroll_layout.addWidget(general_card)

        # 系统托盘设置
        tray_card = SimpleCardWidget()
        tray_layout = QVBoxLayout(tray_card)
        tray_layout.setContentsMargins(15, 15, 15, 15)

        tray_title = StrongBodyLabel('系统托盘')
        tray_title.setStyleSheet('font-size: 16px;')
        tray_layout.addWidget(tray_title)
        tray_layout.addSpacing(15)

        # 启用系统托盘
        tray_enabled_layout = QHBoxLayout()
        tray_enabled_layout.addWidget(BodyLabel('启用系统托盘:'))
        self.tray_enabled_switch = SwitchButton()
        self.tray_enabled_switch.checkedChanged.connect(self.on_tray_enabled_changed)
        tray_enabled_layout.addWidget(self.tray_enabled_switch)
        tray_enabled_layout.addStretch()
        tray_layout.addLayout(tray_enabled_layout)
        tray_layout.addSpacing(10)

        # 最小化到托盘
        minimize_layout = QHBoxLayout()
        minimize_layout.addWidget(BodyLabel('最小化到托盘:'))
        self.minimize_switch = SwitchButton()
        self.minimize_switch.checkedChanged.connect(self.on_minimize_changed)
        minimize_layout.addWidget(self.minimize_switch)
        minimize_layout.addStretch()
        tray_layout.addLayout(minimize_layout)
        tray_layout.addSpacing(10)

        # 关闭时最小化
        close_minimize_layout = QHBoxLayout()
        close_minimize_layout.addWidget(BodyLabel('关闭时最小化至托盘:'))
        self.close_minimize_switch = SwitchButton()
        self.close_minimize_switch.checkedChanged.connect(self.on_close_minimize_changed)
        close_minimize_layout.addWidget(self.close_minimize_switch)
        close_minimize_layout.addStretch()
        tray_layout.addLayout(close_minimize_layout)

        scroll_layout.addWidget(tray_card)

        # 调度器设置
        scheduler_card = SimpleCardWidget()
        scheduler_layout = QVBoxLayout(scheduler_card)
        scheduler_layout.setContentsMargins(15, 15, 15, 15)

        scheduler_title = StrongBodyLabel('自动清理调度')
        scheduler_title.setStyleSheet('font-size: 16px;')
        scheduler_layout.addWidget(scheduler_title)
        scheduler_layout.addSpacing(15)

        # 调度器类型
        scheduler_type_layout = QHBoxLayout()
        scheduler_type_layout.addWidget(BodyLabel('调度类型:'))
        self.scheduler_type_combo = ComboBox()
        self.scheduler_type_combo.addItems(['禁用', '每日定时', '磁盘空间'])
        self.scheduler_type_combo.currentIndexChanged.connect(self.on_scheduler_type_changed)
        scheduler_type_layout.addWidget(self.scheduler_type_combo)
        scheduler_type_layout.addStretch()
        scheduler_layout.addLayout(scheduler_type_layout)
        scheduler_layout.addSpacing(10)

        # 每日定时
        daily_time_layout = QHBoxLayout()
        daily_time_layout.addWidget(BodyLabel('每日定时:'))
        self.daily_time_edit = TimeEdit()
        self.daily_time_edit.displayFormat = 'HH:mm'
        self.daily_time_edit.timeChanged.connect(self.on_daily_time_changed)
        daily_time_layout.addWidget(self.daily_time_edit)
        daily_time_layout.addStretch()
        scheduler_layout.addLayout(daily_time_layout)
        scheduler_layout.addSpacing(10)

        # 磁盘阈值
        disk_threshold_layout = QHBoxLayout()
        disk_threshold_layout.addWidget(BodyLabel('磁盘空间阈值 (GB):'))
        self.disk_threshold_spin = SpinBox(minimum=10, maximum=500, value=50, parent=self)
        self.disk_threshold_spin.valueChanged.connect(self.on_disk_threshold_changed)
        disk_threshold_layout.addWidget(self.disk_threshold_spin)
        disk_threshold_layout.addStretch()
        scheduler_layout.addLayout(disk_threshold_layout)

        scroll_layout.addWidget(scheduler_card)

        # 回收站设置
        recycle_card = SimpleCardWidget()
        recycle_layout = QVBoxLayout(recycle_card)
        recycle_layout.setContentsMargins(15, 15, 15, 15)

        recycle_title = StrongBodyLabel('回收站设置')
        recycle_title.setStyleSheet('font-size: 16px;')
        recycle_layout.addWidget(recycle_title)
        recycle_layout.addSpacing(12)

        # 说明警告
        recycle_hint = BodyLabel('启用回收功能后，删除的文件将被压缩并保存到指定目录（处理时间将显著增加）')
        recycle_hint.setStyleSheet('color: #999; font-style: italic; margin-bottom: 8px;')
        recycle_layout.addWidget(recycle_hint)

        # 启用回收功能开关
        recycle_enabled_layout = QHBoxLayout()
        recycle_enabled_layout.addWidget(BodyLabel('启用回收功能:'))
        self.recycle_enabled_switch = SwitchButton()
        self.recycle_enabled_switch.checkedChanged.connect(self._on_recycle_enabled_changed)
        recycle_enabled_layout.addWidget(self.recycle_enabled_switch)
        recycle_enabled_layout.addStretch()
        recycle_layout.addLayout(recycle_enabled_layout)
        recycle_layout.addSpacing(15)

        # 自定义回收站路径
        recycle_path_title = QHBoxLayout()
        recycle_path_title.addWidget(BodyLabel('回收站文件夹路径:'))
        recycle_path_title.addStretch()
        recycle_layout.addLayout(recycle_path_title)

        recycle_path_sub_layout = QHBoxLayout()
        recycle_path_sub_layout.setContentsMargins(0, 0, 0, 0)
        self.recycle_path_edit = LineEdit()
        self.recycle_path_edit.setPlaceholderText('输入回收站文件夹路径，留空使用默认目录')
        self.recycle_path_edit.textChanged.connect(self._on_recycle_path_changed)
        recycle_path_sub_layout.addWidget(self.recycle_path_edit)

        self.recycle_browse_btn = PushButton('浏览...')
        self.recycle_browse_btn.setFixedWidth(80)
        self.recycle_browse_btn.clicked.connect(self._browse_recycle_path)
        recycle_path_sub_layout.addWidget(self.recycle_browse_btn)

        self.recycle_default_link = BodyLabel('或使用默认路径')
        self.recycle_default_link.setStyleSheet('color: #999; font-family: monospace; font-size: 11px; text-decoration: underline; cursor: pointer;')
        self.recycle_default_link.linkActivated.connect(self._use_default_recycle_path)
        self.recycle_default_link.setVisible(True)
        recycle_path_sub_layout.addWidget(self.recycle_default_link)
        recycle_path_sub_layout.addStretch()

        recycle_layout.addLayout(recycle_path_sub_layout)

        scroll_layout.addWidget(recycle_card)

        # AppData迁移功能
        appdata_card = SimpleCardWidget()
        appdata_layout = QVBoxLayout(appdata_card)
        appdata_layout.setContentsMargins(15, 15, 15, 15)

        appdata_title = StrongBodyLabel('AppData迁移功能')
        appdata_title.setStyleSheet('font-size: 16px;')
        appdata_layout.addWidget(appdata_title)
        appdata_layout.addSpacing(12)

        # 说明警告（demo）
        appdata_hint = BodyLabel('AppData迁移工具（演示版）：将大型AppData文件夹迁移到其他磁盘，通过符号链接实现透明重定向')
        appdata_hint.setStyleSheet('color: #999; font-style: italic; margin-bottom: 8px;')
        appdata_layout.addWidget(appdata_hint)

        # 启用AppData迁移开关
        appdata_enabled_layout = QHBoxLayout()
        appdata_enabled_layout.addWidget(BodyLabel('启用AppData迁移功能 (demo):'))
        self.appdata_migration_switch = SwitchButton()
        self.appdata_migration_switch.checkedChanged.connect(self._on_appdata_migration_changed)
        appdata_enabled_layout.addWidget(self.appdata_migration_switch)
        appdata_enabled_layout.addStretch()
        appdata_layout.addLayout(appdata_enabled_layout)

        scroll_layout.addWidget(appdata_card)

        # 清理设置
        clean_card = SimpleCardWidget()
        clean_layout = QVBoxLayout(clean_card)
        clean_layout.setContentsMargins(15, 15, 15, 15)

        clean_title = StrongBodyLabel('清理设置')
        clean_title.setStyleSheet('font-size: 16px;')
        clean_layout.addWidget(clean_title)
        clean_layout.addSpacing(15)

        # 删除前确认
        confirm_layout = QHBoxLayout()
        confirm_layout.addWidget(BodyLabel('删除前确认:'))
        self.confirm_switch = SwitchButton()
        self.confirm_switch.checkedChanged.connect(self.on_confirm_changed)
        confirm_layout.addWidget(self.confirm_switch)
        confirm_layout.addStretch()
        clean_layout.addLayout(confirm_layout)
        clean_layout.addSpacing(10)

        # 白名单管理
        whitelist_btn_layout = QHBoxLayout()
        self.whitelist_btn = PrimaryPushButton('管理白名单...')
        self.whitelist_btn.clicked.connect(self.open_whitelist_dialog)
        whitelist_btn_layout.addWidget(self.whitelist_btn)
        whitelist_btn_layout.addStretch()
        clean_layout.addLayout(whitelist_btn_layout)

        scroll_layout.addWidget(clean_card)

        # AI设置卡片
        ai_card = SimpleCardWidget()
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(15, 15, 15, 15)

        ai_title = StrongBodyLabel('AI评估设置')
        ai_title.setStyleSheet('font-size: 16px;')
        ai_layout.addWidget(ai_title)
        ai_layout.addSpacing(15)

        # 启用AI评估
        ai_enabled_layout = QHBoxLayout()
        ai_enabled_layout.addWidget(BodyLabel('启用AI评估:'))
        self.ai_enabled_switch = SwitchButton()
        self.ai_enabled_switch.checkedChanged.connect(self._on_ai_enabled_changed)
        ai_enabled_layout.addWidget(self.ai_enabled_switch)
        ai_enabled_layout.addStretch()
        ai_layout.addLayout(ai_enabled_layout)
        ai_layout.addSpacing(12)

        # AI 风险策略
        ai_risk_layout = QHBoxLayout()
        ai_risk_layout.addWidget(BodyLabel('AI 风险策略:'))
        self.ai_risk_combo = ComboBox()
        self.ai_risk_combo.addItems(['保守（确认后清理）', '激进（自动清理）'])
        self.ai_risk_combo.currentIndexChanged.connect(self._on_ai_risk_changed)
        ai_risk_layout.addWidget(self.ai_risk_combo)
        ai_risk_layout.addStretch()
        ai_layout.addLayout(ai_risk_layout)
        ai_layout.addSpacing(12)

        # API URL
        api_url_layout = QHBoxLayout()
        api_url_layout.addWidget(BodyLabel('API URL:'))
        self.api_url_edit = LineEdit()
        self.api_url_edit.setPlaceholderText('例如: https://api.openai.com/v1')
        self.api_url_edit.textChanged.connect(self._on_ai_config_changed)
        api_url_layout.addWidget(self.api_url_edit)
        ai_layout.addLayout(api_url_layout)

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(BodyLabel('API Key:'))
        self.api_key_edit = LineEdit()
        self.api_key_edit.setPlaceholderText('输入API密钥')
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.textChanged.connect(self._on_ai_config_changed)
        api_key_layout.addWidget(self.api_key_edit)
        ai_layout.addLayout(api_key_layout)

        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel('Model:'))
        self.ai_model_edit = LineEdit()
        self.ai_model_edit.setPlaceholderText('例如: gpt-4, gpt-3.5-turbo')
        self.ai_model_edit.textChanged.connect(self._on_ai_config_changed)
        model_layout.addWidget(self.ai_model_edit)
        ai_layout.addLayout(model_layout)

        # 测试连接按钮
        test_layout = QHBoxLayout()
        test_layout.addStretch()
        self.test_api_btn = PushButton('测试 API 连接')
        self.test_api_btn.clicked.connect(self.test_api_connection)
        test_layout.addWidget(self.test_api_btn)
        ai_layout.addLayout(test_layout)

        scroll_layout.addWidget(ai_card)

        scroll_layout.addStretch()

        # 底部按钮 - 隐藏保存按钮因为设置实时保存
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.addStretch()

        # self.save_btn = PrimaryPushButton('保存设置')
        # self.save_btn.clicked.connect(self.save_settings)
        # bottom_layout.addWidget(self.save_btn)

        self.reset_btn = PushButton('重置默认')
        self.reset_btn.clicked.connect(self.reset_settings)
        bottom_layout.addWidget(self.reset_btn)

        scroll_layout.addWidget(bottom_widget)

        scroll.setWidget(scroll_container)
        layout.addWidget(scroll)

    def load_settings(self):
        """加载设置"""
        # 通用设置
        self.notify_switch.setChecked(self.config_mgr.get('notification/enabled', True))
        self.startup_switch.setChecked(self.config_mgr.get('startup/enabled', False))

        # 系统托盘
        self.tray_enabled_switch.setChecked(self.config_mgr.get('system_tray/enabled', True))
        self.minimize_switch.setChecked(self.config_mgr.get('system_tray/minimize', True))
        self.close_minimize_switch.setChecked(self.config_mgr.get('system_tray/minimize_on_close', False))

        # 调度器
        try:
            self.scheduler_type_combo.setCurrentIndex(
                int(self.config_mgr.get('scheduler/type', 0)))
            time_str = self.config_mgr.get('scheduler/daily_time', '03:00')
            from PyQt5.QtCore import QTime
            self.daily_time_edit.setTime(QTime.fromString(time_str, 'HH:mm'))
        except Exception:
            pass

        self.disk_threshold_spin.setValue(self.config_mgr.get('scheduler/disk_threshold', 50))

        # 清理设置
        self.confirm_switch.setChecked(self.config_mgr.get('cleanup/confirm_dialog', True))

        # 回收站设置 - 从配置管理器读取
        try:
            recycle_enabled = self.config_mgr.get('recycle_enabled', False)
            recycle_path = self.config_mgr.get('recycle_path', '')
            # 如果有旧的 JSON 格式配置
            recycle_config = self.config_mgr.get('recycle', {})
            if recycle_config:
                recycle_enabled = recycle_config.get('enabled', False)
                recycle_path = recycle_config.get('folder_path', '')
            self.recycle_enabled_switch.setChecked(recycle_enabled)
            self.recycle_path_edit.setText(recycle_path)
        except Exception as e:
            pass

        # AI设置
        ai_config = self.config_mgr.get_ai_config()
        self.ai_enabled_switch.setChecked(ai_config['enabled'])
        self.api_url_edit.setText(ai_config['api_url'])
        self.api_key_edit.setText(ai_config['api_key'])
        self.ai_model_edit.setText(ai_config['api_model'])

        # AI 风险策略
        ai_risk = self.config_mgr.get('ai_risk_policy', 'conservative')
        if ai_risk == 'aggressive':
            self.ai_risk_combo.setCurrentIndex(1)
        else:
            self.ai_risk_combo.setCurrentIndex(0)

        # AppData迁移功能
        appdata_migration_enabled = self.config_mgr.get('appdata_migration/enabled', False)
        self.appdata_migration_switch.setChecked(appdata_migration_enabled)

    def on_notify_changed(self, checked: bool):
        """通知开关变更 - 实时保存"""
        self.config_mgr.set('notification/enabled', checked)

    def on_startup_changed(self, checked: bool):
        """开机启动开关变更 - 实时保存"""
        self.config_mgr.set('startup/enabled', checked)
        startup_mgr = get_startup_manager()
        if checked:
            startup_mgr.enable()
        else:
            startup_mgr.disable()

    def on_tray_enabled_changed(self, checked: bool):
        """系统托盘启用变更 - 实时保存"""
        self.config_mgr.set('system_tray/enabled', checked)
        startup_mgr = get_startup_manager()
        tray = startup_mgr.is_enabled()
        if checked and not tray:
            startup_mgr.enable()
        elif not checked and tray:
            startup_mgr.disable()

    def on_minimize_changed(self, checked: bool):
        """最小化到托盘变更 - 实时保存"""
        self.config_mgr.set('system_tray/minimize', checked)

    def on_close_minimize_changed(self, checked: bool):
        """关闭时最小化变更 - 实时保存"""
        self.config_mgr.set('system_tray/minimize_on_close', checked)

    def on_scheduler_type_changed(self, index: int):
        """调度器类型变更 - 实时保存"""
        self.config_mgr.set('scheduler/type', index)

        # 更新子选项可见性
        is_daily = (index == 1)
        is_disk = (index == 2)
        self.daily_time_edit.setEnabled(is_daily)
        self.disk_threshold_spin.setEnabled(is_disk)

    def on_daily_time_changed(self, time):
        """每日定时变更 - 实时保存"""
        self.config_mgr.set('scheduler/daily_time', time.toString('HH:mm'))

    def on_disk_threshold_changed(self, value: int):
        """磁盘阈值变更 - 实时保存"""
        self.config_mgr.set('scheduler/disk_threshold', value)

    def _on_recycle_enabled_changed(self, checked: bool):
        """回收功能开关变更"""
        recycle_dict = self.config_mgr.get('recycle', {})
        recycle_dict['enabled'] = checked
        self.config_mgr.set('recycle', recycle_dict)

    def _on_recycle_path_changed(self, path: str):
        """回收站路径变更"""
        recycle_dict = self.config_mgr.get('recycle', {})
        recycle_dict['folder_path'] = path
        self.config_mgr.set('recycle', recycle_dict)

    def _browse_recycle_path(self):
        """浏览回收站路径"""
        folder = QFileDialog.getExistingDirectory(self, '选择回收站文件夹')
        if folder:
            self.recycle_path_edit.setText(folder)

    def _use_default_recycle_path(self):
        """使用默认回收站路径"""
        default_path = os.path.join(os.path.expanduser('~'), 'PurifyAI_RecycleBin')
        self.recycle_path_edit.setText(default_path)

    def _on_appdata_migration_changed(self, checked: bool):
        """AppData迁移功能开关变更 - 实时保存"""
        self.config_mgr.set('appdata_migration/enabled', checked)
        # 通知主应用更新按钮可见性
        if self.window():
            if hasattr(self.window(), 'update_appdata_migration_button'):
                self.window().update_appdata_migration_button()

    def on_confirm_changed(self, checked: bool):
        """删除前确认变更 - 实时保存"""
        self.config_mgr.set('cleanup/confirm_dialog', checked)

    def _on_ai_enabled_changed(self, checked: bool):
        """AI启用开关变更"""
        self.config_mgr.set_ai_config(enabled=checked)

    def _on_ai_risk_changed(self, index: int):
        """AI 风险策略变更 - 实时保存"""
        # 0: 保守（需要确认）
        # 1: 激进（自动清理）
        risk_policy = 'aggressive' if index == 1 else 'conservative'
        self.config_mgr.set('ai_risk_policy', risk_policy)

    def _on_ai_config_changed(self):
        """AI配置变更"""
        api_url = self.api_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        api_model = self.ai_model_edit.text().strip()

        self.config_mgr.set_ai_config(api_url=api_url, api_key=api_key, api_model=api_model)


    def open_whitelist_dialog(self):
        """打开白名单管理对话框"""
        dialog = WhitelistDialog(self)
        dialog.exec_()

    def test_api_connection(self):
        """测试 API 连接"""
        from core import AIConfig, AIClient

        api_url = self.api_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        model = self.ai_model_edit.text().strip()

        # 验证配置
        config = AIConfig(
            api_url=api_url,
            api_key=api_key,
            model=model
        )

        is_valid, error_msg = config.validate()
        if not is_valid:
            QMessageBox.warning(self, '配置错误', error_msg)
            return

        # 测试连接
        self.test_api_btn.setEnabled(False)
        self.test_api_btn.setText('测试中...')

        test_thread = APITestThread(self, AIClient(config))
        test_thread.finished.connect(self.on_api_test_finished)
        test_thread.start()

    def on_api_test_finished(self, success, msg):
        """API 测试完成回调"""
        if success:
            QMessageBox.information(self, '测试成功', f'API 连接测试成功！\n\n{msg}')
        else:
            QMessageBox.critical(self, '测试失败', f'API 连接测试失败：\n\n{msg}')
        self.test_api_btn.setEnabled(True)
        self.test_api_btn.setText('测试 API 连接')

    def save_settings(self):
        """保存设置（确认保存提示）"""
        # 设置已实时保存，这里只是显示确认
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success('设置已保存', '您的设置已保存成功', orient=Qt.Horizontal, parent=self)

    def reset_settings(self):
        """重置为默认设置"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            '重置设置',
            '确定要重置所有设置为默认值吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清空配置文件中的所有设置
            self.config_mgr._config.clear()
            self.config_mgr._save_config()
            self.load_settings()
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success('设置已重置', '所有设置已恢复为默认值', orient=Qt.Horizontal, parent=self)


class APITestThread(QThread):
    """API 测试线程"""
    finished = pyqtSignal(bool, str)

    def __init__(self, parent, client):
        super().__init__(parent)
        self.client = client

    def run(self):
        try:
            self.client.test_connection()
            self.finished.emit(True, '连接成功')
        except Exception as e:
            self.finished.emit(False, str(e))
