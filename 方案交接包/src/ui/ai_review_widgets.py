"""
AI复核功能模块 - UI组件
提供带AI复核结果的卡片组件 - 表格型样式（优化版）
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, StrongBodyLabel, IconWidget,
    FluentIcon, InfoBadge, SubtitleLabel, ToolButton
)

from core.models import ScanItem
from core.rule_engine import RiskLevel
from core.ai_review_models import AIReviewResult


class AIReviewCard(SimpleCardWidget):
    """带AI复核结果的卡片 - 表格型样式（优化版，无复选框）"""

    # 重新评估按钮点击信号
    re_evaluate_requested = pyqtSignal(str)  # 传递项目路径

    def __init__(self, item: ScanItem, ai_result: AIReviewResult = None, parent=None):
        """初始化卡片

        Args:
            item: 扫描项
            ai_result: AI复核结果
            parent: 父对象
        """
        super().__init__(parent)
        self.item = item
        self.ai_result = ai_result
        self.is_ai_reviewed = ai_result is not None

        self._init_ui()
        self._update_content()

    def _init_ui(self):
        """初始化UI - 表格型布局（优化版）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # ========== 第一行：基本信息行（带重新评估按钮）==========
        self.basic_row = QWidget()
        basic_layout = QHBoxLayout(self.basic_row)
        basic_layout.setContentsMargins(0, 0, 0, 0)
        basic_layout.setSpacing(10)

        # 风险状态圆点
        self.risk_dot = self._create_risk_dot(self.item.risk_level)
        basic_layout.addWidget(self.risk_dot)

        # 文件名/路径
        self.name_label = StrongBodyLabel(self._get_display_name())
        self.name_label.setStyleSheet('font-size: 13px; color: #2c2c2c;')
        basic_layout.addWidget(self.name_label, stretch=1)

        # 文件大小
        self.size_label = BodyLabel(self._format_size(self.item.size))
        self.size_label.setStyleSheet('font-size: 11px; color: #666;')
        basic_layout.addWidget(self.size_label)

        # AI徽章
        self.badge = QLabel("✓ AI")
        self.badge.setStyleSheet('font-size: 9px; background: #0078D4; color: white; padding: 2px 5px; border-radius: 3px;')
        self.badge.setVisible(False)
        basic_layout.addWidget(self.badge)

        # 重新评估按钮 - 使用文字按钮
        self.re_evaluate_btn = QPushButton("↻")
        self.re_evaluate_btn.setFixedSize(28, 24)
        self.re_evaluate_btn.setCursor(Qt.PointingHandCursor)
        self.re_evaluate_btn.setStyleSheet('''
            QPushButton {
                background: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #005a9e;
            }
            QPushButton:pressed {
                background: #004578;
            }
        ''')
        self.re_evaluate_btn.setToolTip("重新评估")
        self.re_evaluate_btn.setVisible(False)
        self.re_evaluate_btn.clicked.connect(lambda: self.re_evaluate_requested.emit(self.item.path))
        basic_layout.addWidget(self.re_evaluate_btn)

        # 复选框（放在右边）
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)  # AI卡片默认全选
        self.checkbox.setFixedSize(20, 20)
        basic_layout.addWidget(self.checkbox)

        layout.addWidget(self.basic_row)

        # ========== AI分析结果区域（表格型）==========
        self.ai_result_widget = QWidget()
        self.ai_result_widget.setVisible(False)

        result_layout = QVBoxLayout(self.ai_result_widget)
        result_layout.setContentsMargins(0, 4, 0, 0)
        result_layout.setSpacing(3)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background: #e5e5e5; margin: 0 4px;")
        result_layout.addWidget(separator)

        # 第一行：风险 | 原因
        row1 = QHBoxLayout()
        row1.setSpacing(15)

        self.risk_label = BodyLabel("风险：")
        self.risk_label.setStyleSheet('font-size: 10px; color: #888;')
        row1.addWidget(self.risk_label)

        self.risk_value = BodyLabel("")
        self.risk_value.setStyleSheet('font-size: 10px; font-weight: 600;')
        row1.addWidget(self.risk_value)

        self.reason_label = BodyLabel("原因：")
        self.reason_label.setStyleSheet('font-size: 10px; color: #888;')
        row1.addWidget(self.reason_label)

        self.reason_value = BodyLabel("")
        self.reason_value.setStyleSheet('font-size: 10px; color: #555;')
        self.reason_value.setWordWrap(True)
        row1.addWidget(self.reason_value, stretch=1)

        result_layout.addLayout(row1)

        # 第二行：软件 | 功能
        row2 = QHBoxLayout()
        row2.setSpacing(15)

        self.software_label = BodyLabel("软件：")
        self.software_label.setStyleSheet('font-size: 10px; color: #888;')
        row2.addWidget(self.software_label)

        self.software_value = BodyLabel("")
        self.software_value.setStyleSheet('font-size: 10px; color: #555;')
        row2.addWidget(self.software_value)

        self.function_label = BodyLabel("功能：")
        self.function_label.setStyleSheet('font-size: 10px; color: #888;')
        row2.addWidget(self.function_label)

        self.function_value = BodyLabel("")
        self.function_value.setStyleSheet('font-size: 10px; color: #555;')
        row2.addWidget(self.function_value, stretch=1)

        result_layout.addLayout(row2)

        # 第三行：建议
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        suggestion_icon = IconWidget(FluentIcon.INFO)
        suggestion_icon.setFixedSize(12, 12)
        suggestion_icon.setStyleSheet('color: #0078D4;')
        row3.addWidget(suggestion_icon)

        self.suggestion_value = BodyLabel("")
        self.suggestion_value.setStyleSheet('font-size: 10px; color: #0078D4; font-weight: 500;')
        self.suggestion_value.setWordWrap(True)
        row3.addWidget(self.suggestion_value, stretch=1)

        result_layout.addLayout(row3)

        layout.addWidget(self.ai_result_widget)

        # 初始高度
        self.setFixedHeight(32 if not self.is_ai_reviewed else 108)

    def _create_risk_dot(self, risk_level):
        """创建风险状态圆点"""
        widget = QWidget()
        widget.setFixedSize(7, 7)
        color = self._get_risk_color(risk_level)
        widget.setStyleSheet(f'''
            QWidget {{
                background: {color};
                border-radius: 3.5px;
            }}
        ''')
        return widget

    def _update_content(self):
        """更新卡片内容"""
        # 更新风险圆点颜色
        self.basic_row.layout().removeWidget(self.risk_dot)
        self.risk_dot.deleteLater()
        self.risk_dot = self._create_risk_dot(self.item.risk_level)
        self.basic_row.layout().insertWidget(0, self.risk_dot)

        # 更新名称
        self.name_label.setText(self._get_display_name())

        # 更新AI结果
        if self.ai_result:
            self._update_ai_review()
        else:
            self.ai_result_widget.setVisible(False)
            self.badge.setVisible(False)
            self.re_evaluate_btn.setVisible(False)
            self.setFixedHeight(32)

    def _update_ai_review(self):
        """更新AI复核结果显示"""
        self.ai_result_widget.setVisible(True)
        self.badge.setVisible(True)
        self.re_evaluate_btn.setVisible(True)

        # 更新风险
        risk_text = self._get_risk_label(self.ai_result.ai_risk)
        risk_color = self._get_risk_color(self.ai_result.ai_risk)
        self.risk_value.setText(risk_text)
        self.risk_value.setStyleSheet(f'font-size: 10px; font-weight: 600; color: {risk_color};')

        # 更新原因
        self.reason_value.setText(self.ai_result.risk_reason[:50] + "..." if len(self.ai_result.risk_reason) > 50 else self.ai_result.risk_reason)

        # 更新软件和功能
        software_name = self.ai_result.software_name[:15] + "..." if len(self.ai_result.software_name) > 15 else self.ai_result.software_name
        func_name = self.ai_result.function_description[:15] + "..." if len(self.ai_result.function_description) > 15 else self.ai_result.function_description
        self.software_value.setText(software_name)
        self.function_value.setText(func_name)

        # 更新建议
        suggestion = self.ai_result.cleanup_suggestion[:60] + "..." if len(self.ai_result.cleanup_suggestion) > 60 else self.ai_result.cleanup_suggestion
        self.suggestion_value.setText(suggestion)

        # 更新高度
        self.setFixedHeight(108)

    def update_ai_result(self, ai_result: AIReviewResult):
        """更新AI复核结果"""
        self.ai_result = ai_result
        self.is_ai_reviewed = True
        self._update_content()

    def get_checkbox(self):
        """获取复选框"""
        return self.checkbox

    def _get_display_name(self) -> str:
        """获取显示名称"""
        name = self.item.description
        # 根据是否有AI结果调整长度限制
        max_len = 45 if self.is_ai_reviewed else 55
        if len(name) > max_len:
            return name[:max_len] + "..."
        return name

    def _get_risk_icon(self, risk_level: RiskLevel) -> FluentIcon:
        """获取风险图标"""
        icon_map = {
            RiskLevel.SAFE: FluentIcon.CHECKBOX,
            RiskLevel.SUSPICIOUS: FluentIcon.INFO,
            RiskLevel.DANGEROUS: FluentIcon.DELETE
        }
        return icon_map.get(risk_level, FluentIcon.INFO)

    def _get_risk_color(self, risk_level) -> str:
        """获取风险颜色"""
        if hasattr(risk_level, 'value'):
            risk_level = risk_level.value
        color_map = {
            'safe': '#28a745',
            'suspicious': '#ffc107',
            'dangerous': '#dc3545'
        }
        return color_map.get(str(risk_level).lower(), '#999')

    def _get_risk_label(self, risk_level) -> str:
        """获取风险标签"""
        if hasattr(risk_level, 'value'):
            risk_level = risk_level.value
        label_map = {
            'safe': '安全',
            'suspicious': '疑似',
            'dangerous': '危险'
        }
        return label_map.get(str(risk_level).lower(), '未知')

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"


class ReviewProgressBar(QWidget):
    """AI复核进度条组件"""

    def __init__(self, parent=None):
        """初始化"""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 状态标题行
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.status_label = BodyLabel("🔍 AI复核就绪")
        self.status_label.setStyleSheet('font-size: 11px; color: #666;')
        header.addWidget(self.status_label)

        header.addStretch()

        self.progress_percent = BodyLabel("0%")
        self.progress_percent.setStyleSheet('font-size: 11px; font-weight: 600; color: #0078D4;')
        header.addWidget(self.progress_percent)

        layout.addLayout(header)

        # 进度条
        from qfluentwidgets import ProgressBar
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 当前项
        self.current_item_label = BodyLabel("")
        self.current_item_label.setStyleSheet('font-size: 10px; color: #999; padding-left: 4px;')
        self.current_item_label.setVisible(False)
        layout.addWidget(self.current_item_label)

        self.setMaximumHeight(60)

    def update_status(self, status):
        """更新状态

        Args:
            status: AIReviewStatus
        """
        from core.ai_review_models import AIReviewStatus

        if status.is_in_progress:
            self.status_label.setText(f"🔍 AI复核中... ({status.reviewed_items}/{status.total_items})")
            self.progress_bar.setValue(status.progress_percent)
            self.progress_percent.setText(f"{status.progress_percent}%")
            self.current_item_label.setText(f"当前: {self._get_short_path(status.current_item)}")
            self.current_item_label.setVisible(True)
        elif status.is_complete:
            self.status_label.setText("✅ AI复核完成")
            self.progress_bar.setValue(100)
            self.progress_percent.setText("100%")
            self.current_item_label.setVisible(False)
        else:
            self.status_label.setText("🔍 AI复核就绪")
            self.progress_bar.setValue(0)
            self.progress_percent.setText("0%")
            self.current_item_label.setVisible(False)

    def _get_short_path(self, path: str) -> str:
        """获取短路径显示"""
        if len(path) > 50:
            return "..." + path[-50:]
        return path


class ReviewSummaryCard(SimpleCardWidget):
    """AI复核摘要卡片"""

    def __init__(self, parent=None):
        """初始化"""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # 标题
        title = QHBoxLayout()
        title.setContentsMargins(0, 0, 0, 0)

        title_icon = IconWidget(FluentIcon.CHAT)
        title_icon.setFixedSize(18, 18)
        title_icon.setStyleSheet('color: #0078D4;')
        title.addWidget(title_icon)

        title_label = StrongBodyLabel("AI复核摘要")
        title_label.setStyleSheet('font-size: 13px; color: #2c2c2c;')
        title.addWidget(title_label)

        title.addStretch()

        layout.addLayout(title)

        # 统计行
        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(8)

        self.total_label = self._create_stat_label("总计", "0", "#2c2c2c")
        stats_row.addWidget(self.total_label)

        self.safe_label = self._create_stat_label("安全", "0", "#28a745")
        stats_row.addWidget(self.safe_label)

        self.suspicious_label = self._create_stat_label("疑似", "0", "#ffc107")
        stats_row.addWidget(self.suspicious_label)

        self.dangerous_label = self._create_stat_label("危险", "0", "#dc3545")
        stats_row.addWidget(self.dangerous_label)

        stats_row.addStretch()
        layout.addLayout(stats_row)

        # 消息
        self.message_label = BodyLabel("点击\"AI复核\"按钮开始评估...")
        self.message_label.setStyleSheet('font-size: 10px; color: #999;')
        layout.addWidget(self.message_label)

    def _create_stat_label(self, title: str, value: str, color: str) -> QWidget:
        """创建统计标签"""
        widget = QWidget()
        widget.setStyleSheet('background: #f5f5f5; border-radius: 6px;')

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        value_label = StrongBodyLabel(value)
        value_label.setStyleSheet(f'font-size: 14px; color: {color};')
        value_label.setAlignment(Qt.AlignCenter)

        title_label = BodyLabel(title)
        title_label.setStyleSheet('font-size: 9px; color: #666;')
        title_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(title_label)

        widget.value_label = value_label

        return widget

    def update_summary(self, status):
        """更新摘要

        Args:
            status: AIReviewStatus
        """
        total = status.reviewed_items

        self.total_label.value_label.setText(str(total))
        self.safe_label.value_label.setText(str(status.safe_count))
        self.suspicious_label.value_label.setText(str(status.suspicious_count))
        self.dangerous_label.value_label.setText(str(status.dangerous_count))

        if status.is_in_progress:
            self.message_label.setText("正在进行AI复核...")
        elif status.is_complete:
            if status.failed_count > 0:
                self.message_label.setText(f"完成！成功 {status.success_count}，失败 {status.failed_count}")
            else:
                self.message_label.setText("AI复核完成！请查看评估结果")


# InfoBadge位置枚举
class InfoBadgePosition:
    """InfoBadge位置"""
    TOP_RIGHT = "top_right"


class InfoBadge(QWidget):
    """信息徽章"""

    def __init__(self, text: str, position: str = "top_right", parent=None):
        """初始化"""
        super().__init__(parent)
        self.text = text
        self.position = position
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self.text)
        self.label.setStyleSheet('''
            QLabel {
                background: #0078D4;
                color: white;
                font-size: 8px;
                padding: 2px 6px;
                border-radius: 8px;
            }
        ''')
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)

    def setText(self, text: str):
        """设置文本"""
        self.text = text
        self.label.setText(text)

    def setCustomBackgroundColor(self, color: str):
        """设置背景颜色"""
        self.label.setStyleSheet(f'''
            QLabel {{
                background: {color};
                color: white;
                font-size: 8px;
                padding: 2px 6px;
                border-radius: 8px;
            }}
        ''')

    def getCustomBackgroundColor(self, color: str):
        """获取背景颜色"""
        self.setCustomBackgroundColor(color)


# 导出到__all__
__all__ = [
    'AIReviewCard',
    'ReviewProgressBar',
    'ReviewSummaryCard',
    'InfoBadge',
    'InfoBadgePosition',
]
