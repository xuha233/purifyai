"""
智能清理页面 UI - 全新设计

现代化、可视化的智能清理界面：
- 左侧：扫描配置与操作面板
- 中间：清理项目（卡片式展示）
- 右侧：统计与风险分析
- 顶部：进度状态与阶段指示
- 底部：执行控制

Design V2.0
"""
import os
from typing import Optional, List, Dict
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QRectF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QScrollArea, QFrame, QSplitter, QStackedWidget, QAbstractItemView,
    QSizePolicy, QToolButton, QMenu, QAction, QCheckBox, QPushButton,
    QDialog
)
from PyQt5.QtGui import QFont, QColor, QPainter, QLinearGradient, QPen, QBrush
from PyQt5.QtCore import pyqtProperty

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ProgressBar, FluentIcon, InfoBar,
    InfoBarPosition, CardWidget, StrongBodyLabel, IconWidget,
    MessageBox, ToolTipFilter, ToolTipPosition, Pivot, SegmentedWidget,
    ComboBox, SwitchButton, Action, RoundMenu, ComboBox, MenuAnimationType,
    Flyout, FlyoutAnimationType
)

from core.smart_cleaner import (
    SmartCleaner, SmartCleanConfig, SmartCleanPhase, ScanType,
    get_smart_cleaner, CleanupPlan, CleanupItem, CleanupStatus
)
from core.rule_engine import RiskLevel
from core.backup_manager import BackupManager, get_backup_manager
from core.models_smart import BackupType
from utils.logger import get_logger

logger = get_logger(__name__)


# ========== 颜色主题 ==========
class ThemeColors:
    """主题颜色"""
    PRIMARY = "#0078D4"
    SUCCESS = "#28a745"
    WARNING = "#ff9800"
    DANGER = "#dc3545"
    WARNING_DARK = "#f57c00"
    DANGER_DARK = "#c62828"
    ERROR = "#d32f2f"
    BACKGROUND = "#f8f9fa"
    CARD_BG = "#ffffff"
    TEXT_PRIMARY = "#2c2c2c"
    TEXT_SECONDARY = "#666666"
    TEXT_TERTIARY = "#999999"
    BORDER = "#e0e0e0"
    RISK_SAFE = ("#e6f7e6", "#28a745")
    RISK_WARY = ("#fff3e0", "#ff9800")
    RISK_DANGEROUS = ("#fee2e2", "#dc3545")
    RISK_UNKNOWN = ("#f5f5f5", "#666666")


# ========== 自定义组件 ==========

class GradientCard(QFrame):
    """渐变卡片效果"""

    def __init__(self, start_color: str, end_color: str, parent=None):
        super().__init__(parent)
        self.start_color = QColor(start_color)
        self.end_color = QColor(end_color)
        self.setFrameStyle(QFrame.NoFrame)

    def paintEvent(self, event):
        """绘制渐变背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, self.start_color)
        gradient.setColorAt(1, self.end_color)

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)


class StatCard(SimpleCardWidget):
    """统计卡片"""

    clicked = pyqtSignal()

    def __init__(self, icon: FluentIcon, title: str, value: str, subtitle: str,
                 color: str = ThemeColors.PRIMARY, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(36, 36)
        icon_widget.setStyleSheet(f'color: {color};')
        layout.addWidget(icon_widget)

        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        content_layout.setContentsMargins(0, 0, 0, 0)

        value_label = StrongBodyLabel(value)
        value_label.setStyleSheet(f'font-size: 20px; color: {color};')
        content_layout.addWidget(value_label)

        title_label = BodyLabel(title)
        title_label.setStyleSheet('font-size: 12px; color: #666;')
        content_layout.addWidget(title_label)

        if subtitle:
            subtitle_label = BodyLabel(subtitle)
            subtitle_label.setStyleSheet('font-size: 10px; color: #999;')
            content_layout.addWidget(subtitle_label)

        layout.addLayout(content_layout)
        layout.addStretch()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        super().mousePressEvent(event)
        self.clicked.emit()


class SpinnerWidget(QWidget):
    """旋转加载动画组件"""

    def __init__(self, size=24, color="#0078D4", parent=None):
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self._color = color
        self.setFixedSize(size, size)
        self._animation = QPropertyAnimation(self, b"rotation")
        self._animation.setDuration(800)
        self._animation.setStartValue(0)
        self._animation.setEndValue(360)
        self._animation.setLoopCount(-1)  # 无限循环
        self._animation.setEasingCurve(QEasingCurve.Linear)

    @pyqtProperty(float)
    def rotation(self) -> float:
        return self._angle

    @rotation.setter
    def rotation(self, value: float):
        self._angle = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置画笔
        pen = QPen(QColor(self._color), 3)
        painter.setPen(pen)

        # 绘制旋转的圆弧
        rect = QRectF(2, 2, self._size - 4, self._size - 4)

        # 绘制4段圆弧，形成加载效果
        start_angle = int(self._angle)
        for i in range(4):
            span = 45  # 每段45度
            draw_start = start_angle + i * 90
            painter.drawArc(rect, draw_start * 16, span * 16)

    def start(self):
        """启动动画"""
        self._animation.start()
        self.setVisible(True)

    def stop(self):
        """停止动画"""
        self._animation.stop()
        self.setVisible(False)


class ScanInfoCard(SimpleCardWidget):
    """扫描信息卡片 - 实时显示扫描状态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)

        # 水平布局：左边是内容，右边是spinner
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # 左侧：内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(6)

        # 标题和spinner容器
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # 标题
        title = BodyLabel("扫描进度")
        title.setStyleSheet('font-size: 12px; color: #999;')
        top_row.addWidget(title)
        top_row.addStretch()
        content_layout.addLayout(top_row)

        # 当前扫描路径
        self.current_path_label = StrongBodyLabel("")
        self.current_path_label.setWordWrap(True)
        self.current_path_label.setStyleSheet('font-size: 14px; color: #333;')
        self.current_path_label.setText("等待开始...")
        content_layout.addWidget(self.current_path_label)

        # 扫描详情
        self.scan_detail_label = BodyLabel("")
        self.scan_detail_label.setStyleSheet('font-size: 11px; color: #666;')
        self.scan_detail_label.setText("")
        content_layout.addWidget(self.scan_detail_label)

        main_layout.addLayout(content_layout, stretch=1)

        # 右侧：Spinner
        self.spinner = SpinnerWidget(size=36, color="#0078D4")
        self.spinner.setVisible(False)
        main_layout.addWidget(self.spinner)

    def set_current_path(self, path: str, detail: str = ""):
        """设置当前扫描路径"""
        # 缩短过长的路径
        if len(path) > 60:
            path = "..." + path[-57:]
        self.current_path_label.setText(f"正在扫描: {path}")
        if detail:
            self.scan_detail_label.setText(detail)
        else:
            self.scan_detail_label.setText("")

    def set_analyzing(self, detail: str = ""):
        """设置分析状态"""
        self.current_path_label.setText("正在分析扫描结果...")
        if detail:
            self.scan_detail_label.setText(detail)
        else:
            self.scan_detail_label.setText("")

    def clear(self):
        """清除信息"""
        self.current_path_label.setText("等待开始...")
        self.scan_detail_label.setText("")

    def show_animating(self, animating: bool):
        """显示/隐藏动画"""
        self.spinner.setVisible(animating)
        if animating:
            self.spinner.start()
        else:
            self.spinner.stop()


class CleanupItemCard(SimpleCardWidget):
    """清理项目卡片"""

    def __init__(self, item: CleanupItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.is_selected = False
        self.is_hovered = False

        self.setMinimumHeight(70)
        self.setMaximumHeight(90)

        self.init_ui()
        self.update_risk_style()

    def init_ui(self):
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(24, 24)
        self.checkbox.stateChanged.connect(self.on_check_changed)
        layout.addWidget(self.checkbox)

        # 文件图标
        icon_widget = IconWidget(FluentIcon.DOCUMENT)
        icon_widget.setFixedSize(32, 32)
        icon_widget.setStyleSheet('color: #666;')
        layout.addWidget(icon_widget)

        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # 名称行
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        # 文件名
        name_label = StrongBodyLabel(os.path.basename(self.item.path))
        name_label.setStyleSheet('font-size: 13px;')
        name_label.setMaximumWidth(200)
        name_row.addWidget(name_label)

        # 风险标签
        self.risk_label = BodyLabel("未知")
        self.risk_label.setStyleSheet('font-size: 10px; padding: 3px 8px; border-radius: 4px;')
        name_row.addWidget(self.risk_label)

        name_row.addStretch()
        info_layout.addLayout(name_row)

        # 路径 + 大小
        detail_row = QHBoxLayout()
        detail_row.setSpacing(8)

        # 路径（截断）
        path_display = self.item.path
        if len(path_display) > 60:
            path_display = path_display[:30] + '...' + path_display[-30:]
        path_label = BodyLabel(path_display)
        path_label.setStyleSheet('font-size: 11px; color: #999;')
        path_label.setMaximumWidth(350)
        detail_row.addWidget(path_label)

        detail_row.addStretch()

        # 大小
        size_label = StrongBodyLabel(self._format_size(self.item.size))
        size_label.setStyleSheet('font-size: 12px; color: #666;')
        detail_row.addWidget(size_label)

        # 备份类型标签
        backup_types = {
            BackupType.NONE: '无备份',
            BackupType.HARDLINK: '硬链接',
            BackupType.FULL: '完整备份'
        }
        backup_type_map = {
            RiskLevel.SAFE: BackupType.NONE,
            RiskLevel.SUSPICIOUS: BackupType.HARDLINK,
            RiskLevel.DANGEROUS: BackupType.FULL
        }
        backup_type = backup_type_map.get(self.item.ai_risk, BackupType.NONE)
        backup_text = backup_types.get(backup_type, '')

        if backup_text:
            backup_label = BodyLabel(backup_text)
            if backup_type == BackupType.NONE:
                backup_label.setStyleSheet('font-size: 10px; color: #bbb;')
            elif backup_type == BackupType.HARDLINK:
                backup_label.setStyleSheet('font-size: 10px; color: #66bb6a; padding: 2px 6px; background: #e8f5e9; border-radius: 3px;')
            else:
                backup_label.setStyleSheet('font-size: 10px; color: #42a5f5; padding: 2px 6px; background: #e3f2fd; border-radius: 3px;')
            detail_row.addWidget(backup_label)

        info_layout.addLayout(detail_row)
        layout.addLayout(info_layout)

    def update_risk_style(self):
        """更新风险风格"""
        risk_colors = {
            RiskLevel.SAFE: ThemeColors.RISK_SAFE,
            RiskLevel.SUSPICIOUS: ThemeColors.RISK_WARY,
            RiskLevel.DANGEROUS: ThemeColors.RISK_DANGEROUS
        }
        risk_labels = {
            RiskLevel.SAFE: '安全',
            RiskLevel.SUSPICIOUS: '可疑',
            RiskLevel.DANGEROUS: '危险'
        }

        # 获取风险对应的颜色，如果未知则使用wary
        bg_color, fg_color = risk_colors.get(self.item.ai_risk, ThemeColors.RISK_WARY)
        risk_text = risk_labels.get(self.item.ai_risk, '未知')

        self.risk_label.setText(risk_text)
        self.risk_label.setStyleSheet(f'''
            font-size: 10px; padding: 3px 8px; border-radius: 4px;
            background: {bg_color}; color: {fg_color}; font-weight: 500;
        ''')

    def on_check_changed(self, state):
        """复选框状态变化"""
        self.is_selected = (state == Qt.Checked)

        # 更新卡片样式
        if self.is_selected:
            self.setStyleSheet('''
                SimpleCardWidget {
                    background: #e3f2fd;
                    border: 1px solid #0078D4;
                    border-radius: 8px;
                }
            ''')
        else:
            self.setStyleSheet('''
                SimpleCardWidget {
                    background: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
                SimpleCardWidget:hover {
                    background: #fafafa;
                    border: 1px solid #0078D4;
                }
            ''')

    def enterEvent(self, event):
        """鼠标进入事件"""
        self.is_hovered = True
        if not self.is_selected:
            self.setStyleSheet('''
                SimpleCardWidget {
                    background: #fafafa;
                    border: 1px solid #d0d0d0;
                    border-radius: 8px;
                }
            ''')
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.is_hovered = False
        if not self.is_selected:
            self.setStyleSheet('''
                SimpleCardWidget {
                    background: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            ''')
        super().leaveEvent(event)

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class PhaseIndicator(QLabel):
    """简洁的阶段指示器 - 卡片式设计"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_phase = 0
        self.phases = [
            "1. 扫描系统",
            "2. AI 智能分析",
            "3. 预览清理项",
            "4. 执行清理"
        ]
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setFixedHeight(32)
        self.setAlignment(Qt.AlignCenter)
        self.update_display()

    def update_display(self):
        """更新显示"""
        active_text = self.phases[self.current_phase]
        self.setText(active_text)
        self.setStyleSheet(f'''
            QLabel {{
                background: #e3f2fd;
                color: #0078D4;
                padding: 8px 24px;
                border-radius: 16px;
                font-size: 14px;
                font-weight: 600;
            }}
        ''')
        self.update()

    def update_phase(self, phase_index: int):
        """更新阶段

        Args:
            phase_index: 当前阶段索引 (0-3)
        """
        self.current_phase = min(max(phase_index, 0), len(self.phases) - 1)
        self.update_display()


class SmartCleanupPage(QWidget):
    """智能清理页面 - 全新设计 V2.0

    分区域布局：
    - 顶部：阶段指示器和状态
    - 主体：三栏布局（配置、列表、统计）
    - 底部：操作按钮和进度
    """

    cleanup_phase_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # 初始化组件
        self.config = SmartCleanConfig()
        self.backup_mgr = get_backup_manager()
        self.cleaner = get_smart_cleaner(
            config=self.config,
            backup_mgr=self.backup_mgr
        )

        self.current_plan: Optional[CleanupPlan] = None
        self.item_cards: List[tuple[CleanupItemCard, CleanupItem]] = []

        # 当前状态
        self.state = 'idle'  # idle, scanning, analyzing, preview, executing, completed, error
        self._scan_start_time = 0  # 扫描开始时间

        # 连接信号
        self._connect_signals()

        self.init_ui()
        self.logger.info("[UI:SMART_CLEANUP V2] 智能清理页面初始化完成")

    def _connect_signals(self):
        """连接 SmartCleaner 信号"""
        self.cleaner.phase_changed.connect(self._on_phase_changed)
        self.cleaner.scan_progress.connect(self._on_scan_progress)
        self.cleaner.analyze_progress.connect(self._on_analyze_progress)
        self.cleaner.execute_progress.connect(self._on_execute_progress)
        self.cleaner.plan_ready.connect(self._on_plan_ready)
        self.cleaner.execution_completed.connect(self._on_execution_completed)
        self.cleaner.error.connect(self._on_error)

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # ========== 顶部：标题和阶段指示 ==========
        header_layout = QVBoxLayout()
        header_layout.setSpacing(12)

        # 标题行
        title_row = QHBoxLayout()
        header_icon = IconWidget(FluentIcon.SYNC)
        header_icon.setFixedSize(28, 28)
        header_icon.setStyleSheet('color: #0078D4;')
        title_row.addWidget(header_icon)

        title = SubtitleLabel("智能清理")
        title.setStyleSheet('font-size: 22px;')
        title_row.addWidget(title)
        title_row.addSpacing(20)

        # AI 状态指示器
        self.ai_status_indicator = QWidget()
        ai_layout = QHBoxLayout(self.ai_status_indicator)
        ai_layout.setContentsMargins(0, 0, 0, 0)

        ai_dot = QLabel("●")
        ai_dot.setStyleSheet(f'color: {"#28a745" if self.config.enable_ai else "#999"}; font-size: 10px;')
        ai_layout.addWidget(ai_dot)

        ai_text = BodyLabel(f"AI {'已启用' if self.config.enable_ai else '已禁用'}")
        ai_text.setStyleSheet('font-size: 12px; color: #666;')
        ai_layout.addWidget(ai_text)

        title_row.addWidget(self.ai_status_indicator)
        title_row.addStretch()

        # AI 切换开关
        self.ai_switch = SwitchButton()
        self.ai_switch.setChecked(self.config.enable_ai)
        self.ai_switch.checkedChanged.connect(self.toggle_ai)
        ai_switch_label = BodyLabel("AI 智能分析")
        ai_switch_label.setStyleSheet('font-size: 12px; color: #666; margin-right: 4px;')
        title_row.addWidget(ai_switch_label)
        title_row.addWidget(self.ai_switch)

        header_layout.addLayout(title_row)

        # 阶段指示器
        self.phase_indicator = PhaseIndicator()
        header_layout.addWidget(self.phase_indicator)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        header_layout.addWidget(self.progress_bar)

        self.status_label = BodyLabel("准备就绪，请选择扫描类型开始")
        self.status_label.setStyleSheet('color: #666; font-size: 13px;')
        header_layout.addWidget(self.status_label)

        # 先添加header_layout到main_layout
        main_layout.addLayout(header_layout)

        # ===== 扫描进度状态卡 =====
        self.scan_info_card = ScanInfoCard()
        self.scan_info_card.setVisible(False)
        main_layout.addWidget(self.scan_info_card)

        # ========== 主体：三栏布局 ==========
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setStyleSheet('''
            QSplitter::handle {
                background: #e0e0e0;
                width: 1px;
            }
            QSplitter::handle:hover {
                background: #0078D4;
            }
        ''')

        # 左侧：配置面板
        self.config_panel = self._create_config_panel()
        content_splitter.addWidget(self.config_panel)

        # 中间：项目列表
        self.items_panel = self._create_items_panel()
        content_splitter.addWidget(self.items_panel)

        # 右侧：统计面板
        self.stats_panel = self._create_stats_panel()
        content_splitter.addWidget(self.stats_panel)

        # 设置分割器比例
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setStretchFactor(2, 0)

        main_layout.addWidget(content_splitter, stretch=1)

        # ========== 底部：操作按钮 ==========
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        actions_layout.addStretch()

        # 刷新按钮
        self.refresh_btn = PushButton(FluentIcon.SYNC, "刷新")
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.refresh_btn.setFixedHeight(40)
        actions_layout.addWidget(self.refresh_btn)

        # 取消按钮
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedHeight(40)
        actions_layout.addWidget(self.cancel_btn)

        # 开始/预览按钮
        self.main_action_btn = PrimaryPushButton(FluentIcon.SEARCH, "开始扫描")
        self.main_action_btn.clicked.connect(self._on_main_action)
        self.main_action_btn.setFixedHeight(40)
        self.main_action_btn.setMinimumWidth(140)
        actions_layout.addWidget(self.main_action_btn)

        main_layout.addLayout(actions_layout)

        # 初始化统计
        self._update_empty_stats()

        # 超时检测定时器（60秒无响应则报告）
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)
        self.last_activity_time = 0

    def _create_config_panel(self) -> QWidget:
        """创建配置面板"""
        panel = SimpleCardWidget()
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(280)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("扫描配置")
        title.setStyleSheet('font-size: 16px;')
        layout.addWidget(title)

        # 扫描类型选择
        scan_type_label = BodyLabel("扫描类型")
        scan_type_label.setStyleSheet('font-size: 13px; color: #666; font-weight: 600;')
        layout.addWidget(scan_type_label)

        self.scan_type_combo = ComboBox()
        self.scan_type_combo.addItems(["系统文件", "浏览器缓存", "AppData 目录", "自定义路径"])
        self.scan_type_combo.setCurrentIndex(0)
        self.scan_type_combo.currentIndexChanged.connect(self._on_scan_type_changed)
        self.scan_type_combo.setFixedHeight(36)
        layout.addWidget(self.scan_type_combo)

        # 扫描强度
        intensity_label = BodyLabel("扫描强度")
        intensity_label.setStyleSheet('font-size: 13px; color: #666; font-weight: 600;')
        layout.addWidget(intensity_label)

        self.intensity_combo = ComboBox()
        self.intensity_combo.addItems(["轻度扫描", "标准扫描", "深度扫描"])
        self.intensity_combo.setCurrentIndex(1)
        self.intensity_combo.setFixedHeight(36)
        layout.addWidget(self.intensity_combo)

        # 扫描选项
        options_label = BodyLabel("扫描选项")
        options_label.setStyleSheet('font-size: 13px; color: #666; font-weight: 600;')
        layout.addWidget(options_label)

        self.include_large_files = QCheckBox("包含大文件 (>100MB)")
        self.include_large_files.setChecked(True)
        self.include_large_files.setStyleSheet('color: #555; margin-top: 8px;')
        layout.addWidget(self.include_large_files)

        self.include_hidden = QCheckBox("包含隐藏文件")
        self.include_hidden.setChecked(False)
        self.include_hidden.setStyleSheet('color: #555; margin-top: 8px;')
        layout.addWidget(self.include_hidden)

        self.include_system = QCheckBox("包含系统文件")
        self.include_system.setChecked(False)
        self.include_system.setStyleSheet('color: #555; margin-top: 8px;')
        layout.addWidget(self.include_system)

        layout.addStretch()

        # 快速操作
        quick_actions_label = BodyLabel("快速操作")
        quick_actions_label.setStyleSheet('font-size: 13px; color: #666; font-weight: 600;')
        layout.addWidget(quick_actions_label)

        self.auto_select_safe_btn = PushButton(FluentIcon.CHECKBOX, "自动选择安全项")
        self.auto_select_safe_btn.clicked.connect(self._auto_select_safe)
        self.auto_select_safe_btn.setEnabled(False)
        self.auto_select_safe_btn.setFixedHeight(36)
        layout.addWidget(self.auto_select_safe_btn)

        self.clear_selection_btn = PushButton(FluentIcon.DELETE, "清空选择")
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        self.clear_selection_btn.setEnabled(False)
        self.clear_selection_btn.setFixedHeight(36)
        layout.addWidget(self.clear_selection_btn)

        return panel

    def _create_items_panel(self) -> QWidget:
        """创建项目列表面板"""
        panel = SimpleCardWidget()

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题栏
        header = QHBoxLayout()
        title = SubtitleLabel("清理项目")
        title.setStyleSheet('font-size: 16px;')
        header.addWidget(title)

        header.addStretch()

        # 筛选器
        self.filter_combo = ComboBox()
        self.filter_combo.addItems(["全部项目", "安全项目", "可疑项目", "危险项目"])
        self.filter_combo.currentIndexChanged.connect(self._filter_items)
        self.filter_combo.setFixedWidth(120)
        self.filter_combo.setFixedHeight(32)
        header.addWidget(self.filter_combo)

        # 排序
        self.sort_combo = ComboBox()
        self.sort_combo.addItems(["大小降序", "大小升序", "名称升序", "名称降序"])
        self.sort_combo.currentIndexChanged.connect(self._sort_items)
        self.sort_combo.setFixedWidth(120)
        self.sort_combo.setFixedHeight(32)
        header.addWidget(self.sort_combo)

        layout.addLayout(header)

        # 项目计数
        self.items_count_label = BodyLabel("等待扫描...")
        self.items_count_label.setStyleSheet('color: #999; font-size: 12px;')
        layout.addWidget(self.items_count_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet('''
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #fafafa;
            }
        ''')

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setSpacing(8)
        self.items_layout.addStretch()

        scroll.setWidget(self.items_container)
        layout.addWidget(scroll, stretch=1)

        return panel

    def _create_stats_panel(self) -> QWidget:
        """创建统计面板"""
        panel = SimpleCardWidget()
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(240)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 标题
        title = SubtitleLabel("统计概览")
        title.setStyleSheet('font-size: 16px;')
        layout.addWidget(title)

        # 统计卡片 - 总数
        self.total_items_card = StatCard(
            FluentIcon.DOCUMENT,
            "发现项目", "0", "个文件"
        )
        layout.addWidget(self.total_items_card)

        # 统计卡片 - 总大小
        self.total_size_card = StatCard(
            FluentIcon.CLOUD,
            "总大小", "0",
            ThemeColors.PRIMARY
        )
        layout.addWidget(self.total_size_card)

        # 安全项
        self.safe_card = StatCard(
            FluentIcon.ACCEPT,
            "安全项", "0", ThemeColors.SUCCESS
        )
        layout.addWidget(self.safe_card)

        # 可疑项
        self.wary_card = StatCard(
            FluentIcon.COMPLETED,  # Use COMPLETED for warning/suspicious
            "可疑项", "0", ThemeColors.WARNING
        )
        layout.addWidget(self.wary_card)

        # 危险项
        self.dangerous_card = StatCard(
            FluentIcon.CANCEL,  # Use CANCEL/DANGER_ICON for dangerous
            "危险项", "0", ThemeColors.DANGER
        )
        layout.addWidget(self.dangerous_card)

        # 预计释放
        self.freed_card = StatCard(
            FluentIcon.SAVE,
            "预计释放", "0", "磁盘空间"
        )
        layout.addWidget(self.freed_card)

        layout.addStretch()

        # AI 统计
        ai_info_label = BodyLabel("AI 分析统计")
        ai_info_label.setStyleSheet('font-size: 13px; color: #666; font-weight: 600;')
        layout.addWidget(ai_info_label)

        self.ai_calls_label = BodyLabel("AI 调用次数: 0")
        self.ai_calls_label.setStyleSheet('font-size: 12px; color: #999; margin-left: 8px;')
        layout.addWidget(self.ai_calls_label)

        self.ai_cache_label = BodyLabel("缓存命中率: -")
        self.ai_cache_label.setStyleSheet('font-size: 12px; color: #999; margin-left: 8px;')
        layout.addWidget(self.ai_cache_label)

        return panel

    # ========== 事件处理 ==========

    def _on_scan_type_changed(self, index: int):
        """扫描类型变化"""
        self.logger.debug(f"[UI] 扫描类型变为: {index}")

    def _on_main_action(self):
        """主操作按钮点击"""
        if self.state == 'idle':
            self._on_scan_start()
        elif self.state == 'preview':
            self._on_execute_cleanup()
        elif self.state == 'completed':
            self._on_refresh()

    def _on_scan_start(self):
        """开始扫描"""
        scan_type_map = ["system", "browser", "appdata", "custom"]
        scan_type = scan_type_map[self.scan_type_combo.currentIndex()]
        scan_target = ""

        self.logger.info(f"[UI] 开始扫描: {scan_type}")
        self._scan_start_time = __import__('time').time()

        # 启动超时检测
        self._start_timeout_timer()

        # 初始化扫描信息卡片
        scan_type_names = {
            "system": "系统垃圾",
            "browser": "浏览器缓存",
            "appdata": "应用数据",
            "custom": "自定义路径"
        }
        scan_type_name = scan_type_names.get(scan_type, scan_type)

        # 设置UI状态为scanning（这会显示动画）
        self._set_ui_state('scanning')

        # 更新扫描信息卡片
        if hasattr(self, 'scan_info_card'):
            self.scan_info_card.set_current_path(f"正在扫描: {scan_type_name}", "初始化扫描器...")

        # 启动实时路径更新定时器（每2秒更新一次）
        if hasattr(self, 'scan_path_timer'):
            self.scan_path_timer.stop()
        self.scan_path_timer = QTimer()
        self.scan_path_timer.timeout.connect(self._update_scan_path)
        self.scan_path_timer.start(2000)

        # 启动扫描
        self.cleaner.start_scan(scan_type, scan_target)
        self.current_plan = None

    def _update_scan_path(self):
        """实时更新扫描路径显示"""
        if self.state != 'scanning':
            return

        import time
        elapsed = time.time() - self._scan_start_time

        scan_type_map = ["system", "browser", "appdata", "custom"]
        idx = self.scan_type_combo.currentIndex()
        scan_types = ["system", "browser", "appdata", "custom"]
        if idx >= 0 and idx < len(scan_types):
            scan_type = scan_types[idx]

        # 不同扫描类型的说明
        type_info = {
            'system': {
                'name': '系统垃圾扫描',
                'items': ['临时文件', '预取缓存', '系统日志', '更新缓存']
            },
            'browser': {
                'name': '浏览器缓存扫描',
                'items': ['Chrome 缓存', 'Edge 缓存', 'Firefox 缓存']
            },
            'appdata': {
                'name': 'AppData 文件夹扫描',
                'items': ['Roaming', 'Local', 'LocalLow']
            },
            'custom': {
                'name': '自定义路径扫描',
                'items': ['自定义路径']
            }
        }.get(scan_type, {'name': f'{scan_type} 扫描', 'items': []})

        items = type_info['items']
        current_item_idx = min(int(elapsed / 5) % len(items), len(items) - 1)
        current_item = items[current_item_idx]

        # 计算估计进度（基于时间）
        estimated_minutes = max(1, 5 - int(elapsed / 60))
        progress_info = f"已用时: {int(elapsed)}秒 (预计还需 ~{estimated_minutes}分钟)"

        self.scan_info_card.set_current_path(
            f"{type_info['name']} - {current_item}",
            progress_info
        )

    def _on_execute_cleanup(self):
        """执行清理"""
        selected_items = self._get_selected_items()
        if not selected_items:
            InfoBar.warning("提示", "请先选择要清理的项目",
                         parent=self, position=InfoBarPosition.TOP, duration=2000)
            return

        # 确认对话框
        total_size = sum(item.size for item in selected_items)
        msg_box = MessageBox(
            "确认清理",
            f"即将清理 {len(selected_items)} 个项目\n预计释放空间: {self._format_size(total_size)}\n\n"
            "⚠️ 此操作不可撤销，请确认！",
            self
        )
        msg_box.yesButton.setText("确认清理")
        msg_box.cancelButton.setText("取消")

        if msg_box.exec() != MessageBox.Yes:
            return

        self.logger.info(f"[UI] 开始清理 {len(selected_items)} 个项目")
        self.cleaner.execute_cleanup(selected_items)
        self._set_ui_state('executing')

    def _on_cancel(self):
        """取消操作"""
        self.logger.info("[UI] 取消操作")
        self.cleaner.cancel()
        self._set_ui_state('idle')

    def _on_refresh(self):
        """刷新"""
        self.logger.info("[UI] 刷新扫描")
        self._clear_items()
        self._set_ui_state('idle')

    def toggle_ai(self, enabled: bool):
        """切换 AI 状态"""
        self.config.enable_ai = enabled
        self.ai_status_indicator.children()[0].setText("●")
        self.ai_status_indicator.children()[0].setStyleSheet(
            f'color: {"#28a745" if enabled else "#999"}; font-size: 10px;'
        )
        self.ai_status_indicator.children()[1].setText(f"AI {'已启用' if enabled else '已禁用'}")

        # 重置清理器以应用新配置
        self.cleaner = get_smart_cleaner(
            config=self.config,
            backup_mgr=self.backup_mgr
        )
        self._connect_signals()
        self.logger.info(f"[UI] AI 已{'启用' if enabled else '禁用'}")

    # ========== 项目操作 ==========

    def _auto_select_safe(self):
        """自动选择安全项"""
        for card, item in self.item_cards:
            if item.ai_risk == RiskLevel.SAFE:
                card.checkbox.setChecked(True)

    def _clear_selection(self):
        """清空选择"""
        for card, _ in self.item_cards:
            card.checkbox.setChecked(False)

    def _filter_items(self, filter_index: int):
        """过滤项目"""
        risk_map = [None, RiskLevel.SAFE, RiskLevel.SUSPICIOUS, RiskLevel.DANGEROUS]
        risk_filter = risk_map[filter_index]

        for card, item in self.item_cards:
            if risk_filter is None or item.ai_risk == risk_filter:
                card.setVisible(True)
            else:
                card.setVisible(False)

        self._update_items_count()

    def _sort_items(self, sort_index: int):
        """排序项目"""
        # 移除所有卡片
        for card, _ in self.item_cards:
            self.items_layout.removeWidget(card)

        # 根据选项排序
        item_cards = self.item_cards.copy()
        if sort_index == 0:  # 大小降序
            item_cards.sort(key=lambda x: -x[1].size)
        elif sort_index == 1:  # 大小升序
            item_cards.sort(key=lambda x: x[1].size)
        elif sort_index == 2:  # 名称升序
            item_cards.sort(key=lambda x: os.path.basename(x[1].path))
        elif sort_index == 3:  # 名称降序
            item_cards.sort(key=lambda x: -ord(os.path.basename(x[1].path)[0]) if os.path.basename(x[1].path) else 0)

        # 重新添加
        for card, item in item_cards:
            self.items_layout.insertWidget(self.items_layout.count() - 1, card)

    def _get_selected_items(self) -> List[CleanupItem]:
        """获取选中的项目"""
        return [item for card, item in self.item_cards if card.is_selected]

    def _clear_items(self):
        """清空项目列表"""
        for card, _ in self.item_cards:
            card.deleteLater()
        self.item_cards.clear()
        self._update_empty_stats()

    # ========== SmartCleaner 信号回调 ==========

    def _on_phase_changed(self, phase: str):
        """阶段变化回调"""
        # 更新阶段指示器（4个阶段）
        phase_map = {
            'idle': 0,
            'scanning': 0,
            'analyzing': 1,
            'preview': 2,
            'executing': 3,
            'completed': 3,
            'error': 0
        }
        self.phase_indicator.update_phase(phase_map.get(phase, 0))

        # 更新状态标签
        phase_names = {
            'idle': '准备就绪',
            'scanning': '扫描中...',
            'analyzing': 'AI 分析中...',
            'preview': '预览计划',
            'executing': '执行清理中...',
            'completed': '清理完成',
            'error': '发生错误'
        }
        self.status_label.setText(phase_names.get(phase, phase))

        # 重要：同步UI状态（除了preview和completed，因为这会在各自的回调中处理）
        if phase in ('scanning', 'analyzing', 'executing'):
            self._set_ui_state(phase)
        elif phase == 'idle' or phase == 'error':
            self._set_ui_state(phase)

        self.cleanup_phase_changed.emit(phase)

    def _on_scan_progress(self, current: int, total: int):
        """扫描进度回调"""
        # 启动扫描动画（仅当尚未启动时）
        if hasattr(self, 'scan_info_card') and not self.scan_info_card.isVisible():
            self.scan_info_card.show_animating(True)

        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
            self.status_label.setText(f"扫描中... {current}/{total} ({percent}%)")
        else:
            self.progress_bar.setRange(0, 0)  # 不确定进度，显示忙碌动画
            self.status_label.setText("正在扫描...")

    def _on_analyze_progress(self, current: int, total: int):
        """分析进度回调"""
        # 更新最后活动时间
        import time
        self.last_activity_time = time.time()

        # 确保扫描信息卡片可见并显示动画
        if hasattr(self, 'scan_info_card'):
            self.scan_info_card.show_animating(True)

        self.scan_info_card.set_analyzing(f"A正在分析 {current}/{total} 个项目...")

        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
            self.status_label.setText(f"AI 分析中... {current}/{total} ({percent}%)")
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("AI 分析中...")

    def _on_timeout(self):
        """超时检测"""
        import time
        elapsed = time.time() - self.last_activity_time
        if elapsed >= 60:
            self.logger.warning(f"[UI:SMART_CLEANUP] 检测到超时卡住 ({elapsed:.1f}s)")
            self.status_label.setText("⚠️ 检测到卡住，请检查日志或重启")

            # 尝试发送取消信号
            if hasattr(self, 'cleaner') and self.cleaner:
                try:
                    self.cleaner.cancel()
                except:
                    pass

            InfoBar.warning(
                "操作超时",
                f"操作已超过 60 秒无响应。\n"
                f"当前状态: {self.status_label.text()}\n"
                f"请检查后台日志获取详细信息。",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=8000
            )
            # 重置UI状态
            self._set_ui_state('idle')

    def _start_timeout_timer(self):
        """启动超时检测"""
        import time
        self.last_activity_time = time.time()
        self.timeout_timer.start(60000)  # 60秒超时

    def _stop_timeout_timer(self):
        """停止超时检测"""
        self.timeout_timer.stop()

    def _on_execute_progress(self, current: int, total: int):
        """执行进度回调"""
        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
            self.status_label.setText(f"清理中... {current}/{total} ({percent}%)")

    def _on_plan_ready(self, plan: CleanupPlan):
        """清理计划就绪回调"""
        self.current_plan = plan
        self._load_items_from_plan(plan)
        self._update_stats_from_plan(plan)
        self._set_ui_state('preview')

        summary = f"Safe: {plan.safe_count} | Suspicious: {plan.suspicious_count} | Dangerous: {plan.dangerous_count}"
        self.status_label.setText(f"分析完成！{summary}")

    def _on_execution_completed(self, result):
        """执行完成回调"""
        self._set_ui_state('completed')

        success_text = f"清理完成！成功: {result.success_items} | 释放: {self._format_size(result.freed_size)}"
        if result.failed_items > 0:
            success_text += f" | 失败: {result.failed_items}"

        self.status_label.setText(success_text)
        InfoBar.success("清理完成", success_text,
                       parent=self, position=InfoBarPosition.TOP, duration=5000)

        # 更新预计释放为实际释放
        for card, item in self.item_cards:
            if item in result.cleared_items:
                card.deleteLater()
        self.item_cards = [x for x in self.item_cards if x[1] not in result.cleared_items]
        self._update_items_count()

    def _on_error(self, error_msg: str):
        """错误回调"""
        self._set_ui_state('error')
        self.status_label.setText(f"错误: {error_msg}")
        InfoBar.error("操作失败", error_msg,
                     parent=self, position=InfoBarPosition.TOP, duration=5000)

    # ========== UI 状态管理 ==========

    def _set_ui_state(self, state: str):
        """设置 UI 状态"""
        self.state = state

        # states that should hide animations
        animating_states = {'scanning', 'analyzing', 'executing'}

        if state not in animating_states:
            # 停止动画和超时检测（只在非动画状态）
            if hasattr(self, 'scan_animation'):
                self.scan_animation.stop()
            if hasattr(self, 'scan_path_timer'):
                self.scan_path_timer.stop()
            self.scan_info_card.setVisible(False)
            self.scan_info_card.show_animating(False)
            self._stop_timeout_timer()

        if state == 'idle':
            self.phase_indicator.update_phase(0)
            self.progress_bar.setVisible(False)
            self.main_action_btn.setText("开始扫描")
            self.main_action_btn.setIcon(FluentIcon.SEARCH)
            self.main_action_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.auto_select_safe_btn.setEnabled(False)
            self.clear_selection_btn.setEnabled(False)
            self.status_label.setText("准备就绪，请选择扫描类型开始")

        elif state == 'scanning':
            self.phase_indicator.update_phase(1)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 设置为不确定进度模式（旋转）
            self.status_label.setText("扫描中...")

            # 显示扫描动画组件
            self.scan_info_card.setVisible(True)
            self.scan_info_card.show_animating(True)

            self.main_action_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)
            self.auto_select_safe_btn.setEnabled(False)
            self.clear_selection_btn.setEnabled(False)

        elif state == 'analyzing':
            self.phase_indicator.update_phase(2)
            self.status_label.setText("正在分析...")

            # 保持扫描动画组件可见
            self.scan_info_card.setVisible(True)
            self.scan_info_card.show_animating(True)
            # 更新为分析状态
            self.scan_info_card.set_analyzing("AI 正在分析扫描结果...")

            self.main_action_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)

        elif state == 'preview':
            self.phase_indicator.update_phase(3)
            self.progress_bar.setVisible(False)
            self.main_action_btn.setText("执行清理")
            self.main_action_btn.setIcon(FluentIcon.DELETE)
            self.main_action_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.auto_select_safe_btn.setEnabled(True)
            self.clear_selection_btn.setEnabled(True)
            self.status_label.setText(f"发现 {len(self.current_plan.items) if self.current_plan else 0} 个可清理项")

        elif state == 'executing':
            self.phase_indicator.update_phase(4)
            self.progress_bar.setVisible(True)
            self.status_label.setText("清理中...")
            self.main_action_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)
            self.auto_select_safe_btn.setEnabled(False)
            self.clear_selection_btn.setEnabled(False)

        elif state == 'completed':
            self.phase_indicator.update_phase(5)
            self.progress_bar.setVisible(False)
            self.main_action_btn.setText("刷新")
            self.main_action_btn.setIcon(FluentIcon.SYNC)
            self.main_action_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.auto_select_safe_btn.setEnabled(True if self.item_cards else False)
            self.clear_selection_btn.setEnabled(True if self.item_cards else False)
            self.status_label.setText("清理完成")

        elif state == 'error':
            self.phase_indicator.update_phase(0)
            self.progress_bar.setVisible(False)
            self.main_action_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)
            self.status_label.setText("发生错误")

    def _load_items_from_plan(self, plan: CleanupPlan):
        """从清理计划加载项目"""
        self._clear_items()

        for item in plan.items:
            card = CleanupItemCard(item)
            self.items_layout.insertWidget(self.items_layout.count() - 1, card)
            self.item_cards.append((card, item))

            # 默认不选任何项目
            card.checkbox.setChecked(False)

        self._update_items_count()

    def _update_stats_from_plan(self, plan: CleanupPlan):
        """从清理计划更新统计"""
        # 使用子控件更新方法
        for widget in self.total_items_card.findChildren(StrongBodyLabel):
            if widget.font().pointSize() >= 18:
                widget.setText(str(len(plan.items)))
                break

        total_size = self._format_size(sum(i.size for i in plan.items))
        for widget in self.total_size_card.findChildren(StrongBodyLabel):
            if widget.font().pointSize() >= 18:
                widget.setText(total_size)
                break

        for widget, count in [
            (self.safe_card, plan.safe_count),
            (self.wary_card, plan.suspicious_count),
            (self.dangerous_card, plan.dangerous_count)
        ]:
            for child in widget.findChildren(StrongBodyLabel):
                if child.font().pointSize() >= 18:
                    child.setText(str(count))
                    break

        for widget in self.freed_card.findChildren(StrongBodyLabel):
            if widget.font().pointSize() >= 18:
                widget.setText(self._format_size(plan.estimated_freed))
                break

        self.ai_calls_label.setText(f"AI 调用次数: {plan.ai_call_count}")

        # 更新缓存命中率
        try:
            from core.ai_cache import get_ai_cache
            cache = get_ai_cache()
            stats = cache.get_statistics()
            hit_rate = stats.get('hit_rate', 0)
            self.ai_cache_label.setText(f"缓存命中率: {hit_rate:.1%}")
        except:
            self.ai_cache_label.setText(f"缓存命中率: -")

    def _update_empty_stats(self):
        """更新空的统计信息"""
        for widget, text in [
            (self.total_items_card, "0"),
            (self.total_size_card, "0 B"),
            (self.safe_card, "0"),
            (self.wary_card, "0"),
            (self.dangerous_card, "0"),
            (self.freed_card, "0 B"),
        ]:
            for child in widget.findChildren(StrongBodyLabel):
                if child.font().pointSize() >= 18:
                    child.setText(text)
                    break

        self.items_count_label.setText("等待扫描...")
        self.ai_calls_label.setText("AI 调用次数: 0")
        self.ai_cache_label.setText("缓存命中率: -")

    def _update_items_count(self):
        """更新项目计数"""
        visible_count = sum(1 for card, _ in self.item_cards if card.isVisible())
        total_count = len(self.item_cards)
        self.items_count_label.setText(f"显示 {visible_count} / {total_count} 个项目")

    # ========== 工具方法 ==========

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ========== 简单的清理报告对话框 ==========

class CleanupReportDialog(QDialog):
    """清理报告对话框"""

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setWindowTitle("清理报告")
        self.setMinimumSize(500, 400)
        self.result = result

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = SubtitleLabel("清理完成！")
        title.setStyleSheet('font-size: 20px;')
        layout.addWidget(title)

        # 统计卡片
        stats_card = SimpleCardWidget()
        stats_layout = QGridLayout(stats_card)
        stats_layout.setSpacing(16)

        # 成功清理
        success_label = SubtitleLabel("成功清理")
        success_label.setStyleSheet(f'color: {ThemeColors.SUCCESS};')
        success_count = SubtitleLabel(str(self.result.success_items))
        success_count.setStyleSheet(f'color: {ThemeColors.SUCCESS}; font-size: 24px;')
        stats_layout.addWidget(success_label, 0, 0)
        stats_layout.addWidget(success_count, 1, 0)

        # 释放空间
        freed_label = SubtitleLabel("释放空间")
        freed_label.setStyleSheet(f'color: {ThemeColors.PRIMARY};')
        freed_size = SubtitleLabel(SmartCleanupPage._format_size(self.result.freed_size))
        freed_size.setStyleSheet(f'color: {ThemeColors.PRIMARY}; font-size: 24px;')
        stats_layout.addWidget(freed_label, 0, 1)
        stats_layout.addWidget(freed_size, 1, 1)

        # 失败项目
        if self.result.failed_items > 0:
            fail_label = SubtitleLabel("失败项目")
            fail_label.setStyleSheet(f'color: {ThemeColors.ERROR};')
            fail_count = SubtitleLabel(str(self.result.failed_items))
            fail_count.setStyleSheet(f'color: {ThemeColors.ERROR}; font-size: 24px;')
            stats_layout.addWidget(fail_label, 2, 0)
            stats_layout.addWidget(fail_count, 3, 0)

        layout.addWidget(stats_card)

        # 跳过项目
        if self.result.skipped_items > 0:
            skip_label = BodyLabel(f"跳过 {self.result.skipped_items} 个项目（已清除或不存在）")
            skip_label.setStyleSheet('color: #999;')
            layout.addWidget(skip_label)

        layout.addStretch()

        # 关闭按钮
        close_btn = PrimaryPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignCenter)
