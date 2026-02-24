# -*- coding: utf-8 -*-
"""
清理预览组件 - Cleanup Preview Components

显示智能推荐清理计划的预览信息
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal

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

from ..agent.smart_recommender import CleanupPlan, UserScenario, CleanupMode
from ..agent.cleanup_orchestrator import CleanupOrchestrator
from ..core.models import ScanItem
from utils.logger import get_logger

logger = get_logger(__name__)


class CleanupPreviewCard(QtWidgets.QWidget):
    """清理预览卡片

    显示智能推荐清理计划的预览
    """

    def __init__(self, plan: CleanupPlan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self._init_ui()
        self._populate_data()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        title_icon = IconWidget(FluentIcon.DOCUMENT)
        title_icon.setFixedSize(24, 24)
        title_icon.setStyleSheet("color: #0078D4;")
        title_row.addWidget(title_icon)

        title = SubtitleLabel("清理预览")
        title.setStyleSheet("font-size: 18px;")
        title_row.addWidget(title)

        title_row.addStretch()

        # 推荐徽章
        if self.plan.recommended:
            recommended_badge = QLabel("智能推荐")
            recommended_badge.setStyleSheet("""
                QLabel {
                    background: #E6F7FF;
                    color: #1890FF;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            title_row.addWidget(recommended_badge)

        main_layout.addLayout(title_row)

        # 模式信息
        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)

        mode_label = BodyLabel(
            f"清理模式: {CleanupMode(self.plan.mode).get_display_name()}"
        )
        mode_label.setStyleSheet("color: #666; font-size: 13px;")
        mode_row.addWidget(mode_label)

        mode_row.addStretch()
        main_layout.addLayout(mode_row)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background: #e0e0e0;")
        main_layout.addWidget(separator)

        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        # 预计释放空间
        space_card = self._create_stat_card(
            IconWidget(FluentIcon.SAVE),
            "预计释放空间",
            self._format_size(self.plan.estimated_space),
            "#52C41A",
        )
        stats_layout.addWidget(space_card)

        # 总文件数
        items_card = self._create_stat_card(
            IconWidget(FluentIcon.FOLDER),
            "清理文件数",
            str(len(self.plan.items)),
            "#1890FF",
        )
        stats_layout.addWidget(items_card)

        # 风险文件统计
        high_risk_card = self._create_stat_card(
            IconWidget(FluentIcon.WARNING),
            "高风险文件",
            str(self.plan.high_risk_count),
            "#FF4D4F" if self.plan.high_risk_count > 0 else "#999",
        )
        stats_layout.addWidget(high_risk_card)

        medium_risk_card = self._create_stat_card(
            IconWidget(FluentIcon.INFO),
            "中风险文件",
            str(self.plan.medium_risk_count),
            "#FAAD14",
        )
        stats_layout.addWidget(medium_risk_card)

        low_risk_card = self._create_stat_card(
            IconWidget(FluentIcon.ACCEPT),
            "低风险文件",
            str(self.plan.low_risk_count),
            "#52C41A",
        )
        stats_layout.addWidget(low_risk_card)

        main_layout.addLayout(stats_layout)

        # 风险提示
        if self.plan.high_risk_count > 0:
            risk_warning = QLabel(
                f"⚠️ 警告: 发现 {self.plan.high_risk_count} 个高风险文件，请谨慎操作"
            )
            risk_warning.setStyleSheet("""
                QLabel {
                    background: #FFF1F0;
                    color: #CF1322;
                    padding: 12px;
                    border-left: 4px solid #FF4D4F;
                    border-radius: 4px;
                    font-size: 13px;
                }
            """)
            risk_warning.setWordWrap(True)
            main_layout.addWidget(risk_warning)

        # 30天撤销提示
        undo_hint = QLabel("ℹ️ 清理前会自动备份所有文件，支持30天内撤销操作")
        undo_hint.setStyleSheet("""
            QLabel {
                background: #F0F9FF;
                color: #0958D9;
                padding: 12px;
                border-left: 4px solid #1890FF;
                border-radius: 4px;
                font-size: 13px;
            }
        """)
        undo_hint.setWordWrap(True)
        main_layout.addWidget(undo_hint)

    def _create_stat_card(self, icon, label: str, value: str, color: str) -> QFrame:
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        icon_row = QHBoxLayout()
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(20, 20)
        icon_widget.setStyleSheet(f"color: {color};")
        icon_row.addWidget(icon_widget)
        icon_row.addStretch()
        layout.addLayout(icon_row)

        value_label = StrongBodyLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; color: {color}; font-weight: 700;")
        layout.addWidget(value_label)

        label_widget = BodyLabel(label)
        label_widget.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(label_widget)

        return card

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def _populate_data(self):
        """填充数据"""
        pass


class CleanupPreviewDialog(QtWidgets.QDialog):
    """清理预览对话框

    显示清理计划并提供确认选项
    """

    def __init__(self, plan: CleanupPlan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.confirmed = False
        self._init_ui()
        self._adjust_size()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("清理预览")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # 标题
        title_label = SubtitleLabel("确认清理计划")
        title_label.setStyleSheet("font-size: 20px;")
        main_layout.addWidget(title_label)

        # 描述
        description = BodyLabel("AI 已生成智能清理计划，请仔细查看以下信息后确认执行。")
        description.setStyleSheet("color: #666; font-size: 14px;")
        main_layout.addWidget(description)

        # 预览卡片
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
            }
        """)

        self.preview_widget = CleanupPreviewCard(self.plan)
        scroll_area.setWidget(self.preview_widget)
        main_layout.addWidget(scroll_area, stretch=1)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background: #e0e0e0;")
        main_layout.addWidget(separator)

        # 操作按钮
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(12)

        cancel_btn = PushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        button_row.addStretch()

        continue_btn = PrimaryPushButton("继续清理")
        continue_btn.setFixedHeight(40)
        continue_btn.setMinimumWidth(160)
        continue_btn.clicked.connect(self._on_continue)
        button_row.addWidget(continue_btn)

        main_layout.addLayout(button_row)

    def _adjust_size(self):
        """调整对话框大小"""
        screen = QtWidgets.QApplication.primaryScreen()
        screen_size = screen.availableGeometry()
        self.setMaximumWidth(int(screen_size.width() * 0.8))
        self.setMaximumHeight(int(screen_size.height() * 0.8))

    def _on_continue(self):
        """继续清理"""
        self.confirmed = True
        self.accept()

    def is_confirmed(self) -> bool:
        """是否已确认"""
        return self.confirmed


# 修复导入
import QtWidgets
