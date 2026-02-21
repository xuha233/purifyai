"""
系统清理页面 UI
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QCheckBox, QStackedWidget, QFrame, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, SegmentedWidget, SubtitleLabel, InfoBar, InfoBarPosition,
    ProgressBar, CardWidget, FluentIcon, ProgressRing
)
import traceback
import logging

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_cleaner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from core import SystemScanner, Cleaner, format_size, RiskLevel, ScanItem
from core.appdata_scanner_simple import AppDataScanner
from ui.confirm_dialog import ConfirmDialog
from ui.windows_notification import WindowsNotification
from utils.progress_bar import AnimatedProgressBar
from PyQt5.QtCore import QSettings


class SystemCleanerPage(QWidget):
    """系统清理页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_results = []
        self.checkboxes = []
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = StrongBodyLabel('系统清理')
        title.setStyleSheet('font-size: 24px;')
        layout.addWidget(title)

        desc = BodyLabel('清理 Windows 系统文件和 AppData 缓存')
        desc.setStyleSheet('color: #666666; font-size: 14px;')
        layout.addWidget(desc)
        layout.addSpacing(20)

        # 扫描类型选项卡
        mode_title = SubtitleLabel('扫描类型')
        layout.addWidget(mode_title)

        self.mode_segment = SegmentedWidget()
        self.mode_segment.addItem('system', 'System')
        self.mode_segment.addItem('appdata', 'AppData')
        self.mode_segment.setCurrentItem('system')
        self.mode_segment.currentItemChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_segment)
        layout.addSpacing(15)

        # 堆栈页面
        self.stack = QStackedWidget()

        # 系统文件扫描页面
        self.system_widget = QWidget()
        system_layout = QVBoxLayout(self.system_widget)

        system_types_layout = QHBoxLayout()
        self.temp_check = QCheckBox('临时文件')
        self.temp_check.setChecked(True)
        system_types_layout.addWidget(self.temp_check)

        self.prefetch_check = QCheckBox('预取文件')
        self.prefetch_check.setChecked(True)
        system_types_layout.addWidget(self.prefetch_check)

        self.logs_check = QCheckBox('日志文件')
        self.logs_check.setChecked(True)
        system_types_layout.addWidget(self.logs_check)

        self.update_cache_check = QCheckBox('更新缓存')
        self.update_cache_check.setChecked(True)
        system_types_layout.addWidget(self.update_cache_check)

        system_types_layout.addStretch()
        system_layout.addLayout(system_types_layout)
        system_layout.addSpacing(10)

        self.system_scan_btn = PrimaryPushButton('扫描系统文件')
        self.system_scan_btn.clicked.connect(self.on_system_scan)
        system_layout.addWidget(self.system_scan_btn)

        system_layout.addStretch()
        self.stack.addWidget(self.system_widget)

        # AppData 扫描页面
        self.appdata_widget = QWidget()
        appdata_layout = QVBoxLayout(self.appdata_widget)

        appdata_types_layout = QHBoxLayout()
        self.roaming_check = QCheckBox('Roaming')
        self.roaming_check.setChecked(True)
        appdata_types_layout.addWidget(self.roaming_check)

        self.local_check = QCheckBox('Local')
        self.local_check.setChecked(True)
        appdata_types_layout.addWidget(self.local_check)

        self.locallow_check = QCheckBox('LocalLow')
        self.locallow_check.setChecked(False)
        appdata_types_layout.addWidget(self.locallow_check)

        appdata_types_layout.addStretch()
        appdata_layout.addLayout(appdata_types_layout)
        appdata_layout.addSpacing(10)

        self.appdata_scan_btn = PrimaryPushButton('扫描 AppData')
        self.appdata_scan_btn.clicked.connect(self.on_appdata_scan)
        appdata_layout.addWidget(self.appdata_scan_btn)

        # AppData 提示
        appdata_hint = BodyLabel('AppData 扫描会查找应用程序缓存和临时文件，建议在 AI 评估后清理')
        appdata_hint.setStyleSheet('color: #666; font-size: 11px;')
        appdata_layout.addWidget(appdata_hint)

        appdata_layout.addStretch()
        self.stack.addWidget(self.appdata_widget)

        layout.addWidget(self.stack)

        # 扫描进度区域 - 卡片式设计
        self.progress_card = CardWidget()
        self.progress_card.setFixedHeight(80)
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(15, 10, 15, 10)
        progress_layout.setSpacing(5)

        # 状态和进度行
        progress_row = QHBoxLayout()
        self.status_label = BodyLabel('就绪')
        self.status_label.setStyleSheet('font-size: 12px; color: #666;')
        progress_row.addWidget(self.status_label)

        progress_row.addStretch()

        self.count_label = BodyLabel('0 项')
        self.count_label.setStyleSheet('font-size: 12px; color: #999;')
        progress_row.addWidget(self.count_label)

        progress_layout.addLayout(progress_row)

        # 进度条和统计
        progress_second_row = QHBoxLayout()
        self.progress_bar = ProgressBar()
        progress_second_row.addWidget(self.progress_bar)
        progress_second_row.addSpacing(15)
        self.stats_label = BodyLabel('等待开始扫描...')
        self.stats_label.setStyleSheet('font-size: 11px; color: #999;')
        progress_second_row.addWidget(self.stats_label)
        progress_layout.addLayout(progress_second_row)

        self.progress_card.setVisible(True)  # 始终显示
        layout.addWidget(self.progress_card)

        # 扫描结果区域（三个分类 - 使用选项卡）
        from qfluentwidgets import Pivot

        results_card = SimpleCardWidget()
        results_layout = QVBoxLayout(results_card)
        results_layout.setContentsMargins(15, 10, 15, 10)
        results_layout.setSpacing(8)

        # 头部：标题和全选按钮
        results_header_layout = QHBoxLayout()
        results_header_layout.addWidget(StrongBodyLabel('扫描结果'))
        results_header_layout.addStretch()

        # 全选/反选按钮
        self.select_all_btn = PushButton('全选')
        self.select_all_btn.clicked.connect(self.select_all_safe_items)
        results_header_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = PushButton('取消全选')
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        results_header_layout.addWidget(self.deselect_all_btn)

        results_layout.addLayout(results_header_layout)

        # 选项卡切换风险类型
        pivot_layout = QHBoxLayout()
        self.pivot = Pivot(self)

        self.pivot.addItem('safe', '安全')
        self.pivot.addItem('suspicious', '疑似')
        self.pivot.addItem('dangerous', '危险')
        self.pivot.setCurrentItem('safe')
        self.pivot.currentItemChanged.connect(self.on_pivot_changed)

        pivot_layout.addWidget(self.pivot)
        pivot_layout.addStretch()
        results_layout.addLayout(pivot_layout)
        results_layout.addSpacing(10)

        # 结果堆栈
        self.result_stack = QStackedWidget()

        # 安全区 - 简化结构
        self.safe_container = QWidget()
        self.safe_layout = QVBoxLayout(self.safe_container)
        self.safe_layout.setSpacing(8)
        self.safe_layout.addStretch()
        self.safe_scroll = QScrollArea()
        self.safe_scroll.setWidget(self.safe_container)
        self.safe_scroll.setWidgetResizable(True)
        self.safe_scroll.setFrameShape(QScrollArea.NoFrame)
        self.result_stack.addWidget(self.safe_scroll)

        # 疑似区
        self.suspicious_container = QWidget()
        self.suspicious_layout = QVBoxLayout(self.suspicious_container)
        self.suspicious_layout.setSpacing(8)
        self.suspicious_layout.addStretch()
        self.suspicious_scroll = QScrollArea()
        self.suspicious_scroll.setWidget(self.suspicious_container)
        self.suspicious_scroll.setWidgetResizable(True)
        self.suspicious_scroll.setFrameShape(QScrollArea.NoFrame)
        self.result_stack.addWidget(self.suspicious_scroll)

        # 危险区
        self.dangerous_container = QWidget()
        self.dangerous_layout = QVBoxLayout(self.dangerous_container)
        self.dangerous_layout.setSpacing(8)
        self.dangerous_layout.addStretch()
        self.dangerous_scroll = QScrollArea()
        self.dangerous_scroll.setWidget(self.dangerous_container)
        self.dangerous_scroll.setWidgetResizable(True)
        self.dangerous_scroll.setFrameShape(QScrollArea.NoFrame)
        self.result_stack.addWidget(self.dangerous_scroll)

        ai_btn_layout = QHBoxLayout()
        ai_btn_layout.addStretch()
        self.ai_evaluate_btn = PrimaryPushButton('AI 评估所有疑似项目')
        self.ai_evaluate_btn.clicked.connect(self.on_ai_evaluate_all)
        self.ai_evaluate_btn.setEnabled(False)
        ai_btn_layout.addWidget(self.ai_evaluate_btn)
        self.suspicious_layout.addLayout(ai_btn_layout)

        results_layout.addWidget(self.result_stack)
        layout.addWidget(results_card)

        # 初始隐藏安全区域以外的标签
        self.safe_section = None
        self.suspicious_section = None
        self.dangerous_section = None

        # 底部操作区域
        actions_layout = QHBoxLayout()

        self.clean_btn = PrimaryPushButton('清理选中项')
        self.clean_btn.clicked.connect(self.on_clean)
        self.clean_btn.setEnabled(False)
        actions_layout.addWidget(self.clean_btn)

        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.cancel_btn.setVisible(False)
        actions_layout.addWidget(self.cancel_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        layout.addSpacing(10)

        # 初始化
        self.system_scanner = SystemScanner()
        self.appdata_scanner = AppDataScanner()
        self.cleaner = Cleaner()

        # 连接信号
        self.system_scanner.progress.connect(self.on_scan_progress)
        self.system_scanner.item_found.connect(self.on_item_found)
        self.system_scanner.error.connect(self.on_scan_error)
        self.system_scanner.complete.connect(self.on_scan_complete)

        self.appdata_scanner.progress.connect(self.on_scan_progress)
        self.appdata_scanner.item_found.connect(self.on_item_found)
        self.appdata_scanner.error.connect(self.on_scan_error)
        self.appdata_scanner.complete.connect(self.on_scan_complete)

        self.cleaner.progress.connect(self.on_clean_progress)
        self.cleaner.item_deleted.connect(self.on_item_deleted)
        self.cleaner.error.connect(self.on_clean_error)
        self.cleaner.complete.connect(self.on_clean_complete)

        # 状态
        self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
        self.current_mode = 'system'
        self.current_scanner = self.system_scanner

        logger.info("SystemCleanerPage UI 初始化完成")

        # 设置和通知
        from core.config_manager import get_config_manager
        self.config_mgr = get_config_manager()
        self.notification = WindowsNotification()

    # Pivot 切换相关方法
    def on_pivot_changed(self, route_key: str):
        """切换结果选项卡"""
        index_map = {'safe': 0, 'suspicious': 1, 'dangerous': 2}
        self.result_stack.setCurrentIndex(index_map.get(route_key, 0))

    # 选择功能
    def select_all_safe_items(self):
        """全选安全区域项目"""
        container = self._get_container_for_risk('safe')
        if container:
            layout = container.layout()
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    widget.setChecked(True)

    def deselect_all_items(self):
        """取消全选"""
        for layout in [self.safe_layout, self.suspicious_layout, self.dangerous_layout]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QCheckBox):
                    widget.setChecked(False)

    def on_mode_changed(self, route_key: str):
        """切换扫描模式"""
        if route_key == 'system':
            self.current_mode = 'system'
            self.current_scanner = self.system_scanner
            self.stack.setCurrentIndex(0)
        else:
            self.current_mode = 'appdata'
            self.current_scanner = self.appdata_scanner
            self.stack.setCurrentIndex(1)

        self._clear_results()

    def _clear_results(self):
        """清空扫描结果"""
        try:
            logger.debug(f"清空扫描结果，当前 items: {len(self.checkboxes)}")
            for checkbox, card, item in self.checkboxes:
                try:
                    checkbox.deleteLater()
                    card.deleteLater()
                except Exception as e:
                    logger.warning(f"删除控件失败: {e}")

            self.checkboxes.clear()
            self.scan_results.clear()
            self.risk_counts = {'safe': 0, 'suspicious': 0, 'dangerous': 0}
            self.update_risk_labels()

            # 清空各区域内容
            self._clear_layout(self.safe_layout)
            self._clear_layout(self.suspicious_layout)
            self._clear_layout(self.dangerous_layout)

            # 重置清理统计
            if hasattr(self, '_deleted_size'):
                delattr(self, '_deleted_size')
        except Exception as e:
            logger.error(f"清空结果失败: {e}\n{traceback.format_exc()}")

    def _clear_container(self, container):
        """清空容器内容"""
        if container is None:
            return
        try:
            layout = container.layout()
            if layout is None:
                return
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        except Exception as e:
            logger.error(f"清空容器失败: {e}\n{traceback.format_exc()}")

    def _clear_layout(self, layout):
        """清空布局内容"""
        if layout is None:
            return
        try:
            # 从末尾开始删除，避免索引问题
            while layout.count() > 0:
                item = layout.takeAt(layout.count() - 1)
                if item.widget():
                    item.widget().deleteLater()
        except Exception as e:
            logger.error(f"清空布局失败: {e}\n{traceback.format_exc()}")

    def on_system_scan(self):
        """开始系统扫描"""
        try:
            logger.info("开始系统扫描")
            self.system_scan_btn.setEnabled(False)
            self.appdata_scan_btn.setEnabled(False)
            self.clean_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)

            scan_types = []
            if self.temp_check.isChecked():
                scan_types.append('temp')
            if self.prefetch_check.isChecked():
                scan_types.append('prefetch')
            if self.logs_check.isChecked():
                scan_types.append('logs')
            if self.update_cache_check.isChecked():
                scan_types.append('update_cache')

            if not scan_types:
                self.status_label.setText('请至少选择一种扫描类型')
                InfoBar.warning(
                    title='警告',
                    content='请至少选择一种扫描类型',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                self.system_scan_btn.setEnabled(True)
                self.appdata_scan_btn.setEnabled(True)
                self.cancel_btn.setVisible(False)
                return

            self._clear_results()
            self.progress_card.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_bar.setRange(0, 100)  # 不确定性进度
            self.progress_bar.setRange(0, 0)  # 显示忙碌状态
            self.status_label.setText('正在初始化扫描...')
            self.count_label.setText('0 项')
            self.stats_label.setText('扫描中...')
            logger.info(f"启动系统扫描，类型: {scan_types}")
            self.system_scanner.start_scan(scan_types)
        except Exception as e:
            logger.error(f"系统扫描启动失败: {e}\n{traceback.format_exc()}")
            self._show_error("启动扫描失败", str(e))

    def on_appdata_scan(self):
        """开始 AppData 扫描"""
        try:
            logger.info("开始 AppData 扫描")
            self.system_scan_btn.setEnabled(False)
            self.appdata_scan_btn.setEnabled(False)
            self.clean_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)
            self.ai_evaluate_btn.setEnabled(False)

            scan_types = []
            if self.roaming_check.isChecked():
                scan_types.append('roaming')
            if self.local_check.isChecked():
                scan_types.append('local')
            if self.locallow_check.isChecked():
                scan_types.append('local_low')

            if not scan_types:
                self.status_label.setText('请至少选择一种文件夹类型')
                InfoBar.warning(
                    title='警告',
                    content='请至少选择一种文件夹类型',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                self.system_scan_btn.setEnabled(True)
                self.appdata_scan_btn.setEnabled(True)
                self.cancel_btn.setVisible(False)
                return

            self._clear_results()
            self.progress_card.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setRange(0, 0)  # 忙碌状态
            self.status_label.setText('正在初始化扫描...')
            self.count_label.setText('0 项')
            self.stats_label.setText('扫描中...')
            logger.info(f"启动 AppData 扫描，类型: {scan_types}")
            self.appdata_scanner.start_scan(scan_types)
        except Exception as e:
            logger.error(f"AppData 扫描启动失败: {e}\n{traceback.format_exc()}")
            self._show_error("启动扫描失败", str(e))

    def on_scan_progress(self, message):
        """扫描进度更新"""
        self.status_label.setText(message)
        logger.debug(f"扫描进度: {message}")

    def on_cancel(self):
        """取消操作"""
        self.current_scanner.cancel_scan()
        self.cancel_btn.setVisible(False)
        self.status_label.setText('操作已取消')
        self.stats_label.setText('已取消')

    def on_item_found(self, item):
        """发现项目"""
        try:
            # 确保 risk_level 是字符串
            risk_level_str = self._normalize_risk_level(item.risk_level)

            logger.debug(f"发现项目: {item.description}, 风险: {risk_level_str}, 大小: {item.size}")

            self.scan_results.append(item)
            self.risk_counts[risk_level_str] += 1

            # 更新进度显示
            total_size = sum(item.size for item in self.scan_results)
            self.count_label.setText(f'{len(self.scan_results)} 项')
            self.stats_label.setText(f'累计: {format_size(total_size)} | {len(self.scan_results)} 个项目')

            self.update_risk_labels()

            # 添加到对应的区域布局
            target_layout = self._get_layout_for_risk(risk_level_str)
            if target_layout:
                row_widget, checkbox = self._create_item_row(item)
                # 在 addStretch 之前插入
                count = target_layout.count()
                # 如果最后一个元素是 stretch，在其之前插入
                if count > 0:
                    last_item = target_layout.itemAt(count - 1)
                    if last_item and last_item.stretch() > 0:
                        # 移除 stretch，插入 item，再添加 stretch
                        target_layout.takeAt(count - 1)
                        target_layout.addWidget(row_widget)
                        # 重新添加 stretch 保持布局
                        from PyQt5.QtWidgets import QSpacerItem
                        spacer = QSpacerItem(20, 40, 0, 1)
                        target_layout.addItem(spacer)
                    else:
                        target_layout.addWidget(row_widget)
                else:
                    target_layout.addWidget(row_widget)
                self.checkboxes.append((checkbox, row_widget, item))
            else:
                logger.error(f"未找到风险等级 {risk_level_str} 对应的布局")
        except Exception as e:
            logger.error(f"处理扫描项目失败: {e}\n{traceback.format_exc()}")

    def _normalize_risk_level(self, risk_level):
        """标准化风险等级为字符串"""
        if risk_level is None:
            return 'suspicious'

        # 如果是 RiskLevel 枚举
        if hasattr(risk_level, 'value'):
            return risk_level.value

        # 如果是字符串，确保小写
        risk_str = str(risk_level).lower()

        # 验证是有效的风险等级
        if risk_str not in ['safe', 'suspicious', 'dangerous']:
            logger.warning(f"未知的风险等级: {risk_level}，标记为 suspicious")
            return 'suspicious'

        return risk_str

    def _get_container_for_risk(self, risk_level):
        """根据风险等级获取对应的容器（已弃用，兼容保留）"""
        return self._get_layout_for_risk(risk_level)

    def _get_layout_for_risk(self, risk_level):
        """根据风险等级获取对应的布局容器"""
        if risk_level == 'safe':
            return self.safe_layout
        elif risk_level == 'suspicious':
            return self.suspicious_layout
        elif risk_level == 'dangerous':
            return self.dangerous_layout
        return None

    def _create_item_row(self, item):
        """创建项目行（包含复选框和卡片）"""
        # 外层容器
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        # 复选框
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # 默认选中
        checkbox.setFixedSize(20, 20)

        # 卡片样式
        card = SimpleCardWidget()
        card.setMinimumHeight(60)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(15)

        # 左侧：项目图标/标志
        icon_label = BodyLabel()
        risk_color_map = {
            'safe': '#28a745',
            'suspicious': '#ffc107',
            'dangerous': '#dc3545'
        }
        risk_color = risk_color_map.get(self._normalize_risk_level(item.risk_level), '#999')
        icon_label.setStyleSheet(f'font-size: 24px; color: {risk_color};')
        icon_label.setText('●')
        card_layout.addWidget(icon_label)

        # 中间：项目信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 名称
        name_label = BodyLabel(item.description)
        name_label.setStyleSheet('font-weight: bold; font-size: 13px;')
        info_layout.addWidget(name_label)

        # 路径
        path_label = BodyLabel(item.path)
        path_label.setStyleSheet('color: #999; font-size: 11px;')
        path_label.setWordWrap(True)
        info_layout.addWidget(path_label)

        card_layout.addLayout(info_layout)
        card_layout.addStretch()

        # 右侧：大小
        size_label = BodyLabel(format_size(item.size))
        size_label.setStyleSheet('color: #666; font-size: 12px; font-weight: 500;')
        card_layout.addWidget(size_label)

        row_layout.addWidget(checkbox)
        row_layout.addWidget(card, stretch=1)

        return row_widget, checkbox

        # 路径
        path_label = BodyLabel(item.path)
        path_label.setStyleSheet('color: #999999; font-size: 11px;')
        path_label.setWordWrap(True)
        card_layout.addWidget(path_label)

        # 大小
        size_label = BodyLabel(format_size(item.size))
        size_label.setStyleSheet('color: #666666; font-size: 12px;')
        card_layout.addWidget(size_label)

        return card

    def on_ai_evaluate_item(self, item):
        """AI 评估单个项目"""
        from PyQt5.QtCore import QTimer
        self.status_label.setText(f'AI评估中: {item.description}...')

        # 模拟 AI 评估（实际可调用 AI API）
        item.ai_assessment = '应用数据 - 建议保留'
        item.risk_level = 'dangerous'
        self.risk_counts['suspicious'] -= 1
        self.risk_counts['dangerous'] += 1

        # 更新 UI
        QTimer.singleShot(500, lambda: self._update_item_risk(item, 'dangerous'))

    def on_ai_evaluate_all(self):
        """AI 评估所有疑似项目"""
        try:
            self.ai_evaluate_btn.setEnabled(False)
            self.progress_card.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 忙碌状态
            self.status_label.setText('AI 评估中...')
            self.stats_label.setText('正在处理...')

            # 获取疑似项目
            suspicious_items = [item for item in self.scan_results
                               if self._normalize_risk_level(item.risk_level) == 'suspicious']

            logger.info(f"开始评估 {len(suspicious_items)} 个疑似项目")

            if not suspicious_items:
                self.status_label.setText('没有需要评估的项目')
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
                self.stats_label.setText('0 个项目')
                self.ai_evaluate_btn.setEnabled(True)
                self.cancel_btn.setVisible(False)
                return

            # 检查 AI 配置
            ai_config = self.config_mgr.get_ai_config()
            api_url = ai_config['api_url']
            api_key = ai_config['api_key']
            ai_model = ai_config['api_model']
            ai_enabled = ai_config['enabled']

            if not ai_enabled or not api_url or not api_key:
                logger.warning("AI 未配置，使用模拟评估")
                self._simulate_ai_evaluation(suspicious_items)
                return

            # 使用 AI 进行评估
            from PyQt5.QtCore import QThread
            from core import AIConfig, AIClient

            ai_config = AIConfig(api_url=api_url, api_key=api_key, model=ai_model)
            ai_client = AIClient(ai_config)

            evaluated_count = 0
            for i, item in enumerate(suspicious_items):
                if self.cancel_btn.isVisible():
                    break

                self.status_label.setText(f'AI 评估中 ({i+1}/{len(suspicious_items)})...')

                # 调用 AI 评估
                try:
                    folder_name = os.path.basename(item.path)
                    folder_type = 'Local'
                    if 'Roaming' in item.path:
                        folder_type = 'Roaming'
                    elif 'LocalLow' in item.path:
                        folder_type = 'LocalLow'

                    success, risk_level, reason = ai_client.classify_folder_risk(
                        folder_name, item.path, folder_type, format_size(item.size)
                    )

                    if success:
                        # 映射风险等级
                        risk_map = {
                            '安全': 'safe',
                            '疑似': 'suspicious',
                            '危险': 'dangerous'
                        }
                        new_risk = risk_map.get(risk_level, 'dangerous')

                        # 更新描述
                        if reason:
                            item.description = f'{os.path.basename(item.path)} (AI: {reason})'

                        logger.info(f"AI 评估 {folder_name}: {risk_level} - {reason}")

                        if new_risk != 'suspicious':
                            self._update_item_risk(item, new_risk)
                    else:
                        logger.warning(f"AI 评估失败: {reason}")
                        # AI 失败则标记为危险
                        self._update_item_risk(item, 'dangerous')

                    evaluated_count += 1
                    self.stats_label.setText(f'已评估 {evaluated_count}/{len(suspicious_items)}')

                    # 每评估5个项目暂停一下，避免限流
                    if (i + 1) % 5 == 0:
                        from PyQt5.QtCore import QCoreApplication
                        QCoreApplication.processEvents()

                except Exception as e:
                    logger.error(f"AI 评估单个项目失败: {e}")
                    # AI 失败则标记为危险（保守策略）
                    self._update_item_risk(item, 'dangerous')

            self.update_risk_labels()
            self.ai_evaluate_btn.setEnabled(True)
            self.clean_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.status_label.setText('AI 评估完成')
            self.stats_label.setText(f'已评估 {evaluated_count} 个项目')
        except Exception as e:
            logger.error(f"AI评估失败: {e}\n{traceback.format_exc()}")
            self._show_error("AI评估失败", str(e))
            if self.ai_evaluate_btn:
                self.ai_evaluate_btn.setEnabled(True)
            # 出错时使用模拟评估作为fallback
            suspicious_items = [item for item in self.scan_results
                               if self._normalize_risk_level(item.risk_level) == 'suspicious']
            if suspicious_items:
                self._simulate_ai_evaluation(suspicious_items)

    def _simulate_ai_evaluation(self, suspicious_items):
        """模拟 AI 评估（当 AI 未配置时使用）"""
        from PyQt5.QtCore import QCoreApplication

        for i, item in enumerate(suspicious_items):
            if self.cancel_btn.isVisible():
                break

            self.status_label.setText(f'规则评估中 ({i+1}/{len(suspicious_items)})...')

            folder_name = os.path.basename(item.path).lower()

            # 缓存关键词 - 安全
            cache_keywords = ['cache', 'temp', 'tmp', 'logs', 'download', 'prefetch']
            # 数据关键词 - 危险
            dangerous_keywords = ['data', 'settings', 'config', 'profile', 'save',
                               'sync', 'plugin', 'extension', 'backup', 'database', 'db']

            if any(kw in folder_name for kw in cache_keywords):
                self._update_item_risk(item, 'safe')
                logger.info(f"规则评估 {item.path}: 安全")
            elif any(kw in folder_name for kw in dangerous_keywords):
                new_desc = f'{os.path.basename(item.path)} (规则: 可能包含用户数据)'
                item.description = new_desc
                self._update_item_risk(item, 'dangerous')
                logger.info(f"规则评估 {item.path}: 危险")
            else:
                new_desc = f'{os.path.basename(item.path)} (规则: 需谨慎)'
                item.description = new_desc
                self._update_item_risk(item, 'dangerous')
                logger.info(f"规则评估 {item.path}: 危险")

            self.stats_label.setText(f'已评估 {i+1}/{len(suspicious_items)}')
            QCoreApplication.processEvents()

        self.update_risk_labels()
        self.ai_evaluate_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText('规则评估完成')
        self.stats_label.setText(f'已评估 {len(suspicious_items)} 个项目')

    def _update_item_risk(self, item, new_risk):
        """更新项目的风险等级"""
        try:
            # 移除旧卡片
            self._remove_item_card(item)

            # 获取旧风险等级并减少计数
            old_risk_str = self._normalize_risk_level(item.risk_level)
            if old_risk_str in self.risk_counts:
                self.risk_counts[old_risk_str] -= 1

            # 标准化新风险等级
            new_risk_str = self._normalize_risk_level(new_risk)

            # 更新项目的风险等级
            item.risk_level = new_risk_str

            # 更新新风险计数
            self.risk_counts[new_risk_str] += 1

            # 添加到新的布局
            target_layout = self._get_layout_for_risk(new_risk_str)
            if target_layout:
                row_widget, checkbox = self._create_item_row(item)
                # 根据风险决定是否默认选中
                checkbox.setChecked(new_risk_str == 'safe')
                target_layout.addWidget(row_widget)
                self.checkboxes.append((checkbox, row_widget, item))
            else:
                logger.error(f"未找到风险等级 {new_risk_str} 对应的布局")
        except Exception as e:
            logger.error(f"更新项目风险失败: {e}\n{traceback.format_exc()}")

    def _remove_item_card(self, path_or_item):
        """移除项目卡片

        参数 path_or_item: 可以是路径字符串或 ScanItem 对象
        """
        # 兼容旧的调用方式（传入对象）
        if hasattr(path_or_item, 'path'):
            target_path = path_or_item.path
        else:
            target_path = path_or_item

        for i, (checkbox, card, existing_item) in enumerate(self.checkboxes):
            if existing_item.path == target_path:
                checkbox.deleteLater()
                card.deleteLater()
                self.checkboxes.pop(i)
                break

    def update_risk_labels(self):
        """更新风险标签（已弃用，选项卡已显示计数）"""
        # 风险计数改为在选项卡标题中显示，这里保留空方法以防兼容
        pass

    def get_risk_counts_label(self):
        """获取风险计数的显示文本"""
        count_map = {
            'safe': f'安全 ({self.risk_counts["safe"]})',
            'suspicious': f'疑似 ({self.risk_counts["suspicious"]})',
            'dangerous': f'危险 ({self.risk_counts["dangerous"]})'
        }
        return count_map

    def on_scan_error(self, message):
        """扫描错误"""
        logger.error(f"扫描错误: {message}")
        self.system_scan_btn.setEnabled(True)
        self.appdata_scan_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.status_label.setText(f'扫描错误: {message}')
        self.stats_label.setText('扫描失败')

        InfoBar.error(
            title='扫描错误',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def on_scan_complete(self, results):
        """扫描完成"""
        try:
            logger.info(f"扫描完成，结果数量: {len(results)}")
            self.system_scan_btn.setEnabled(True)
            self.appdata_scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)

            # 检查是否被取消
            if not results:
                self.status_label.setText('扫描已取消')
                self.stats_label.setText('已取消')
                return

            # 显示完成信息
            self.status_label.setText('扫描完成')
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            total_size = sum(item.size for item in results)
            self.stats_label.setText(f'发现 {len(results)} 个项目，总计 {format_size(total_size)}')

            # 启用清理按钮
            self.clean_btn.setEnabled(True)

            # 启用 AI 评估按钮（如果有疑似项目）
            if self.risk_counts['suspicious'] > 0 and self.ai_evaluate_btn:
                self.ai_evaluate_btn.setEnabled(True)

            # 发送通知
            if self.notification.is_enabled():
                try:
                    self.notification.show_scan_complete(len(results), total_size)
                except Exception as e:
                    logger.error(f"发送通知失败: {e}")

        except Exception as e:
            logger.error(f"扫描完成处理失败: {e}\n{traceback.format_exc()}")
            self.system_scan_btn.setEnabled(True)
            self.appdata_scan_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)

    def on_clean(self):
        """清理选中项"""
        try:
            logger.info("开始清理选中项")
            # 获取选中项
            selected_items = []
            for checkbox, card, item in self.checkboxes:
                if checkbox.isChecked():
                    selected_items.append(item)

            if not selected_items:
                self.status_label.setText('请先选择要清理的项目')
                InfoBar.warning(
                    title='提示',
                    content='请先选择要清理的项目',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            # 确认对话框
            if self.config_mgr.get('cleanup/confirm_dialog', True):
                dialog = ConfirmDialog(selected_items, self)
                if dialog.exec_() != QDialog.Accepted:
                    return
                selected_items = dialog.get_items_to_clean()
                if not selected_items:
                    self.status_label.setText('未选择任何项目')
                    return

            # 开始清理
            self.system_scan_btn.setEnabled(False)
            self.appdata_scan_btn.setEnabled(False)
            self.clean_btn.setEnabled(False)
            self.progress_card.setVisible(True)
            self.progress_bar.setRange(0, len(selected_items))
            self.progress_bar.setValue(0)
            self.status_label.setText('正在清理...')
            self.count_label.setText(f'0/{len(selected_items)}')
            self.stats_label.setText(f'待清理: {len(selected_items)} 项')

            # 启动清理器
            clean_type = 'system'
            if self.current_mode == 'appdata':
                clean_type = 'appdata'

            logger.info(f"启动清理，项目数: {len(selected_items)}, 类型: {clean_type}")
            self.cleaner.start_clean(selected_items, clean_type=clean_type)
        except Exception as e:
            logger.error(f"清理启动失败: {e}\n{traceback.format_exc()}")
            self._show_error("启动清理失败", str(e))
            self.system_scan_btn.setEnabled(True)
            self.appdata_scan_btn.setEnabled(True)
            self.clean_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)

    def on_clean_progress(self, message):
        """清理进度"""
        self.status_label.setText(message)
        logger.debug(f"清理进度: {message}")

    def on_item_deleted(self, path, size):
        """项目已删除"""
        try:
            logger.debug(f"项目已删除: {path}, 大小: {size}")

            # 更新进度
            current_value = self.progress_bar.value()
            self.progress_bar.setValue(current_value + 1)

            # 更新统计
            deleted_count = self.progress_bar.value()
            max_value = self.progress_bar.maximum()
            self.count_label.setText(f'{deleted_count}/{max_value}')

            # 更新清理统计
            if hasattr(self, '_deleted_size'):
                self._deleted_size += size
            else:
                self._deleted_size = size

            self.stats_label.setText(f'已清理 {self.progress_bar.value()} 项，释放 {format_size(self._deleted_size)}')

            self._remove_item_card(path)
        except Exception as e:
            logger.error(f"处理项目删除失败: {e}\n{traceback.format_exc()}")

    def on_clean_error(self, message):
        """清理错误"""
        logger.error(f"清理错误: {message}")
        self.status_label.setText(f'清理错误: {message}')
        self.stats_label.setText('清理失败')
        self.system_scan_btn.setEnabled(True)
        self.appdata_scan_btn.setEnabled(True)
        self.clean_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)

        InfoBar.error(
            title='清理错误',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def _show_error(self, title: str, message: str):
        """显示错误信息"""
        logger.error(f"{title}: {message}")
        self.status_label.setText(f'{title}: {message}')
        InfoBar.error(
            title=title,
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def on_clean_complete(self, result):
        """清理完成"""
        try:
            logger.info(f"清理完成，结果: {result}")
            self.system_scan_btn.setEnabled(True)
            self.appdata_scan_btn.setEnabled(True)

            if result['success']:
                deleted_count = result['deleted_count']
                deleted_size = result['total_size']

                # 显示完成信息
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
                self.status_label.setText('清理完成')
                self.stats_label.setText(f'已删除 {deleted_count} 个项目，释放 {format_size(deleted_size)}')

                # 发送通知
                if self.notification.is_enabled():
                    try:
                        self.notification.show_clean_complete(deleted_count, deleted_size)
                    except Exception as e:
                        logger.error(f"发送清理完成通知失败: {e}")

                # 移除已删除项
                new_checkboxes = []
                for checkbox, card, item in self.checkboxes:
                    if checkbox.isChecked():
                        card.hide()
                        checkbox.hide()
                    else:
                        new_checkboxes.append((checkbox, card, item))
                self.checkboxes = new_checkboxes

                # 更新计数 - 需要正确处理 risk_level
                for item in self.scan_results[:]:
                    try:
                        risk_level_str = self._normalize_risk_level(item.risk_level)
                        if not any(cb.isChecked() and it.path == item.path for cb, _, it in self.checkboxes):
                            if risk_level_str in self.risk_counts:
                                self.risk_counts[risk_level_str] -= 1
                    except Exception as e:
                        logger.error(f"更新计数失败: {e}")

                self.update_risk_labels()
            else:
                self._show_error("清理失败", result.get('error', '未知错误'))
        except Exception as e:
            logger.error(f"清理完成处理失败: {e}\n{traceback.format_exc()}")
            self._show_error("处理清理结果失败", str(e))

    def get_notification_manager(self):
        """获取通知管理器"""
        return self.notification
