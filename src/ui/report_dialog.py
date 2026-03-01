# -*- coding: utf-8 -*-
"""
清理报告对话框 (Report Dialog)

显示清理执行结果的详细信息：
- 清理统计面板（文件数、释放空间、按类别分组）
- AI 建议面板（风险提示、优化建议）
- 操作历史列表

用于在清理完成后快速查看报告，无需导航到独立页面。
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QScrollArea, QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel, SimpleCardWidget,
    CardWidget, PushButton, PrimaryPushButton, InfoBar,
    InfoBarPosition, IconWidget, FluentIcon,
    ScrollArea, Pivot, ToolButton, ProgressBar, CaptionLabel
)

from core.cleanup_report_generator import (
    CleanupReport, CleanupReportGenerator, get_report_generator
)
from core.models_smart import (
    CleanupPlan, ExecutionResult, RecoveryRecord,
    CleanupItem, RiskLevel, FailureInfo
)
from utils.logger import get_logger

logger = get_logger(__name__)


# ========== 颜色主题 ==========
class ThemeColors:
    """主题颜色"""
    PRIMARY = "#0078D4"
    SUCCESS = "#28a745"
    WARNING = "#ff9800"
    DANGER = "#dc3545"
    ERROR = "#d32f2f"
    BACKGROUND = "#f8f9fa"
    CARD_BG = "#ffffff"
    TEXT_PRIMARY = "#2c2c2c"
    TEXT_SECONDARY = "#666666"
    TEXT_TERTIARY = "#999999"
    BORDER = "#e0e0e0"


# ========== 工具函数 ==========
def format_size(size_bytes: int) -> str:
    """格式化字节大小为可读格式"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} 分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} 小时"


# ========== 统计卡片组件 ==========
class StatCard(SimpleCardWidget):
    """统计卡片 - 显示单个统计数据"""
    
    def __init__(self, icon: FluentIcon, title: str, value: str,
                 subtitle: str = "", color: str = ThemeColors.PRIMARY,
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.color = color
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # 图标
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(36, 36)
        icon_widget.setStyleSheet(f"color: {color};")
        layout.addWidget(icon_widget)
        
        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.value_label = StrongBodyLabel(value)
        self.value_label.setStyleSheet(f"font-size: 20px; color: {color};")
        content_layout.addWidget(self.value_label)
        
        self.title_label = BodyLabel(title)
        self.title_label.setStyleSheet("font-size: 12px; color: #666;")
        content_layout.addWidget(self.title_label)
        
        if subtitle:
            self.subtitle_label = CaptionLabel(subtitle)
            self.subtitle_label.setStyleSheet("font-size: 10px; color: #999;")
            content_layout.addWidget(self.subtitle_label)
        
        layout.addLayout(content_layout)
        layout.addStretch()
    
    def set_value(self, value: str):
        """更新数值"""
        self.value_label.setText(value)
    
    def set_title(self, title: str):
        """更新标题"""
        self.title_label.setText(title)


# ========== 风险统计面板 ==========
class RiskStatsPanel(CardWidget):
    """风险统计面板 - 按类别分组显示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        title = StrongBodyLabel("风险分布统计")
        title.setStyleSheet("font-size: 14px;")
        layout.addWidget(title)
        
        # 安全项目
        safe_layout = QVBoxLayout()
        safe_header = QHBoxLayout()
        self.safe_label = BodyLabel("✓ 安全项目")
        self.safe_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 13px;")
        self.safe_count = BodyLabel("0 项")
        self.safe_count.setStyleSheet("color: #28a745; font-size: 13px;")
        safe_header.addWidget(self.safe_label)
        safe_header.addStretch()
        safe_header.addWidget(self.safe_count)
        safe_layout.addLayout(safe_header)
        
        self.safe_progress = ProgressBar()
        self.safe_progress.setValue(0)
        self.safe_progress.setFixedHeight(8)
        safe_layout.addWidget(self.safe_progress)
        
        self.safe_size = CaptionLabel("0 B")
        self.safe_size.setStyleSheet("color: #666; font-size: 11px;")
        safe_layout.addWidget(self.safe_size)
        layout.addLayout(safe_layout)
        
        # 疑似项目
        suspicious_layout = QVBoxLayout()
        suspicious_header = QHBoxLayout()
        self.suspicious_label = BodyLabel("⚠ 疑似项目")
        self.suspicious_label.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 13px;")
        self.suspicious_count = BodyLabel("0 项")
        self.suspicious_count.setStyleSheet("color: #ff9800; font-size: 13px;")
        suspicious_header.addWidget(self.suspicious_label)
        suspicious_header.addStretch()
        suspicious_header.addWidget(self.suspicious_count)
        suspicious_layout.addLayout(suspicious_header)
        
        self.suspicious_progress = ProgressBar()
        self.suspicious_progress.setValue(0)
        self.suspicious_progress.setFixedHeight(8)
        # 设置进度条颜色为橙色
        self.suspicious_progress.setStyleSheet("""
            ProgressBar {
                background-color: #fff3e0;
                border: none;
                border-radius: 4px;
            }
            ProgressBar::chunk {
                background-color: #ff9800;
                border-radius: 4px;
            }
        """)
        suspicious_layout.addWidget(self.suspicious_progress)
        
        self.suspicious_size = CaptionLabel("0 B")
        self.suspicious_size.setStyleSheet("color: #666; font-size: 11px;")
        suspicious_layout.addWidget(self.suspicious_size)
        layout.addLayout(suspicious_layout)
        
        # 危险项目
        dangerous_layout = QVBoxLayout()
        dangerous_header = QHBoxLayout()
        self.dangerous_label = BodyLabel("✗ 危险项目")
        self.dangerous_label.setStyleSheet("color: #dc3545; font-weight: bold; font-size: 13px;")
        self.dangerous_count = BodyLabel("0 项")
        self.dangerous_count.setStyleSheet("color: #dc3545; font-size: 13px;")
        dangerous_header.addWidget(self.dangerous_label)
        dangerous_header.addStretch()
        dangerous_header.addWidget(self.dangerous_count)
        dangerous_layout.addLayout(dangerous_header)
        
        self.dangerous_progress = ProgressBar()
        self.dangerous_progress.setValue(0)
        self.dangerous_progress.setFixedHeight(8)
        # 设置进度条颜色为红色
        self.dangerous_progress.setStyleSheet("""
            ProgressBar {
                background-color: #fee2e2;
                border: none;
                border-radius: 4px;
            }
            ProgressBar::chunk {
                background-color: #dc3545;
                border-radius: 4px;
            }
        """)
        dangerous_layout.addWidget(self.dangerous_progress)
        
        self.dangerous_size = CaptionLabel("0 B")
        self.dangerous_size.setStyleSheet("color: #666; font-size: 11px;")
        dangerous_layout.addWidget(self.dangerous_size)
        layout.addLayout(dangerous_layout)
    
    def update_stats(self, safe_count: int, safe_size: int,
                     suspicious_count: int, suspicious_size: int,
                     dangerous_count: int, dangerous_size: int,
                     total_count: int):
        """更新统计数据"""
        # 安全项目
        self.safe_count.setText(f"{safe_count} 项")
        self.safe_size.setText(format_size(safe_size))
        safe_percent = int((safe_count / total_count * 100)) if total_count > 0 else 0
        self.safe_progress.setValue(safe_percent)
        
        # 疑似项目
        self.suspicious_count.setText(f"{suspicious_count} 项")
        self.suspicious_size.setText(format_size(suspicious_size))
        suspicious_percent = int((suspicious_count / total_count * 100)) if total_count > 0 else 0
        self.suspicious_progress.setValue(suspicious_percent)
        
        # 危险项目
        self.dangerous_count.setText(f"{dangerous_count} 项")
        self.dangerous_size.setText(format_size(dangerous_size))
        dangerous_percent = int((dangerous_count / total_count * 100)) if total_count > 0 else 0
        self.dangerous_progress.setValue(dangerous_percent)


# ========== AI 建议面板 ==========
class AISuggestionPanel(CardWidget):
    """AI 建议面板 - 显示风险提示和优化建议"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        header = QHBoxLayout()
        title = StrongBodyLabel("🤖 AI 分析与建议")
        title.setStyleSheet("font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        
        self.ai_model_label = CaptionLabel("模型: -")
        self.ai_model_label.setStyleSheet("color: #999; font-size: 11px;")
        header.addWidget(self.ai_model_label)
        layout.addLayout(header)
        
        # 风险提示区域
        self.risk_section = QWidget()
        risk_layout = QVBoxLayout(self.risk_section)
        risk_layout.setSpacing(8)
        risk_layout.setContentsMargins(0, 0, 0, 0)
        
        self.risk_title = BodyLabel("⚠️ 风险提示")
        self.risk_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #dc3545;")
        risk_layout.addWidget(self.risk_title)
        
        self.risk_content = BodyLabel("暂无风险提示")
        self.risk_content.setStyleSheet("font-size: 12px; color: #666;")
        self.risk_content.setWordWrap(True)
        risk_layout.addWidget(self.risk_content)
        
        layout.addWidget(self.risk_section)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0;")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        # 优化建议区域
        self.suggestion_section = QWidget()
        suggestion_layout = QVBoxLayout(self.suggestion_section)
        suggestion_layout.setSpacing(8)
        suggestion_layout.setContentsMargins(0, 0, 0, 0)
        
        self.suggestion_title = BodyLabel("💡 优化建议")
        self.suggestion_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #0078D4;")
        suggestion_layout.addWidget(self.suggestion_title)
        
        self.suggestion_content = BodyLabel("暂无优化建议")
        self.suggestion_content.setStyleSheet("font-size: 12px; color: #666;")
        self.suggestion_content.setWordWrap(True)
        suggestion_layout.addWidget(self.suggestion_content)
        
        layout.addWidget(self.suggestion_section)
    
    def update_suggestions(self, ai_model: str, risk_summary: str,
                           suggestions: str, has_dangerous: bool = False):
        """更新 AI 建议内容"""
        self.ai_model_label.setText(f"模型: {ai_model}" if ai_model else "模型: 规则引擎")
        
        # 更新风险提示
        if risk_summary:
            self.risk_content.setText(risk_summary)
            if has_dangerous:
                self.risk_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #dc3545;")
            else:
                self.risk_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ff9800;")
        else:
            self.risk_content.setText("✅ 未发现高风险项目，清理操作相对安全")
            self.risk_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #28a745;")
        
        # 更新优化建议
        if suggestions:
            self.suggestion_content.setText(suggestions)
        else:
            self.suggestion_content.setText("建议定期清理临时文件和缓存，保持系统流畅运行")


# ========== 操作历史列表 ==========
class OperationHistoryPanel(CardWidget):
    """操作历史面板 - 显示清理操作记录"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.operations = []
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        header = QHBoxLayout()
        title = StrongBodyLabel("📋 操作历史")
        title.setStyleSheet("font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        
        self.operation_count = CaptionLabel("共 0 项操作")
        self.operation_count.setStyleSheet("color: #999; font-size: 11px;")
        header.addWidget(self.operation_count)
        layout.addLayout(header)
        
        # 操作列表容器
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFixedHeight(180)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #fafafa;
            }
        """)
        
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(4)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        
        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area)
        
        # 初始提示
        self.empty_label = BodyLabel("暂无操作记录")
        self.empty_label.setStyleSheet("color: #999; font-size: 12px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.list_layout.addWidget(self.empty_label)
    
    def update_operations(self, operations: List[Dict[str, Any]]):
        """更新操作列表
        
        Args:
            operations: 操作列表，每个操作包含：
                - path: 文件路径
                - size: 文件大小
                - status: 状态 (success/failed/skipped)
                - risk: 风险等级
                - timestamp: 时间戳 (可选)
        """
        # 清空现有列表
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.operations = operations
        self.operation_count.setText(f"共 {len(operations)} 项操作")
        
        if not operations:
            self.empty_label = BodyLabel("暂无操作记录")
            self.empty_label.setStyleSheet("color: #999; font-size: 12px;")
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.list_layout.addWidget(self.empty_label)
            return
        
        # 添加操作项
        for op in operations[:50]:  # 最多显示 50 条
            item_widget = self._create_operation_item(op)
            self.list_layout.addWidget(item_widget)
        
        self.list_layout.addStretch()
    
    def _create_operation_item(self, op: Dict[str, Any]) -> QWidget:
        """创建操作项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        # 状态图标
        status = op.get('status', 'success')
        if status == 'success':
            status_icon = "✓"
            status_color = "#28a745"
        elif status == 'failed':
            status_icon = "✗"
            status_color = "#dc3545"
        else:
            status_icon = "○"
            status_color = "#999"
        
        status_label = BodyLabel(status_icon)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 14px; font-weight: bold;")
        status_label.setFixedWidth(20)
        layout.addWidget(status_label)
        
        # 路径
        path = op.get('path', '未知路径')
        filename = os.path.basename(path) if path else '未知文件'
        path_label = BodyLabel(filename)
        path_label.setStyleSheet("font-size: 12px; color: #333;")
        path_label.setToolTip(path)
        layout.addWidget(path_label, 1)
        
        # 大小
        size = op.get('size', 0)
        size_label = CaptionLabel(format_size(size))
        size_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(size_label)
        
        # 风险等级
        risk = op.get('risk', 'safe')
        risk_colors = {
            'safe': ('#28a745', '安全'),
            'suspicious': ('#ff9800', '疑似'),
            'dangerous': ('#dc3545', '危险')
        }
        risk_color, risk_text = risk_colors.get(risk, ('#666', '-'))
        risk_label = CaptionLabel(risk_text)
        risk_label.setStyleSheet(f"color: {risk_color}; font-size: 11px;")
        layout.addWidget(risk_label)
        
        return widget


# ========== 主对话框 ==========
class ReportDialog(QDialog):
    """清理报告对话框
    
    显示清理执行的详细报告，包括：
    - 清理统计（文件数、大小、类别）
    - AI 建议和风险评估
    - 操作历史列表
    """
    
    # 信号
    export_requested = pyqtSignal(str)  # 导出报告请求 (格式: json/html)
    retry_failed_requested = pyqtSignal(list)  # 重试失败项请求
    view_full_report = pyqtSignal()  # 查看完整报告
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_report: Optional[CleanupReport] = None
        self.current_plan: Optional[CleanupPlan] = None
        self.current_result: Optional[ExecutionResult] = None
        
        self.report_generator = get_report_generator()
        self.logger = logger
        
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("清理报告")
        self.setMinimumSize(700, 600)
        self.resize(750, 650)
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # ========== 顶部标题栏 ==========
        top_bar = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        
        title = SubtitleLabel("📊 清理报告")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_layout.addWidget(title)
        
        self.subtitle_label = CaptionLabel("计划 ID: -")
        self.subtitle_label.setStyleSheet("color: #666; font-size: 12px;")
        title_layout.addWidget(self.subtitle_label)
        
        top_bar.addLayout(title_layout)
        top_bar.addStretch()
        
        # 关闭按钮
        self.close_btn = ToolButton(FluentIcon.CLOSE, self)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.close)
        top_bar.addWidget(self.close_btn)
        
        main_layout.addLayout(top_bar)
        
        # ========== 统计卡片区域 ==========
        self.stats_container = QWidget()
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setSpacing(12)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        # 成功卡片
        self.success_card = StatCard(
            FluentIcon.ACCEPT,
            "成功清理",
            "0",
            "项",
            ThemeColors.SUCCESS
        )
        stats_layout.addWidget(self.success_card)
        
        # 释放空间卡片
        self.freed_card = StatCard(
            FluentIcon.FOLDER,
            "释放空间",
            "0 B",
            "",
            ThemeColors.PRIMARY
        )
        stats_layout.addWidget(self.freed_card)
        
        # 成功率卡片
        self.rate_card = StatCard(
            FluentIcon.PERCENT,
            "成功率",
            "0%",
            "",
            ThemeColors.SUCCESS
        )
        stats_layout.addWidget(self.rate_card)
        
        # 执行时长卡片
        self.duration_card = StatCard(
            FluentIcon.STOP_WATCH,
            "执行时长",
            "0s",
            "",
            ThemeColors.PRIMARY
        )
        stats_layout.addWidget(self.duration_card)
        
        main_layout.addWidget(self.stats_container)
        
        # ========== 中间内容区域（使用 Pivot 切换） ==========
        self.content_pivot = Pivot(self)
        self.content_pivot.setFixedHeight(36)
        main_layout.addWidget(self.content_pivot)
        
        # 内容堆叠
        self.content_stack = QWidget()
        stack_layout = QVBoxLayout(self.content_stack)
        stack_layout.setSpacing(8)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        
        # 统计面板页
        stats_page = QWidget()
        stats_page_layout = QVBoxLayout(stats_page)
        stats_page_layout.setSpacing(12)
        stats_page_layout.setContentsMargins(0, 0, 0, 0)
        
        # 风险统计
        self.risk_stats_panel = RiskStatsPanel()
        stats_page_layout.addWidget(self.risk_stats_panel)
        
        # AI 建议面板
        self.ai_suggestion_panel = AISuggestionPanel()
        stats_page_layout.addWidget(self.ai_suggestion_panel)
        
        # 操作历史面板
        self.operation_history_panel = OperationHistoryPanel()
        stats_page_layout.addWidget(self.operation_history_panel)
        
        stack_layout.addWidget(stats_page)
        
        # 失败项面板页
        failures_page = QWidget()
        failures_layout = QVBoxLayout(failures_page)
        failures_layout.setSpacing(12)
        failures_layout.setContentsMargins(0, 0, 0, 0)
        
        self.failures_panel = OperationHistoryPanel()
        failures_layout.addWidget(self.failures_panel)
        
        stack_layout.addWidget(failures_page)
        
        # 添加 Pivot 页面
        self.content_pivot.addItem(
            routeKey='stats',
            text='清理统计',
            onClick=lambda: self._switch_page(0)
        )
        self.content_pivot.addItem(
            routeKey='failures',
            text='失败项',
            onClick=lambda: self._switch_page(1)
        )
        
        main_layout.addWidget(self.content_stack)
        
        # ========== 底部操作区 ==========
        action_bar = QHBoxLayout()
        action_bar.setSpacing(12)
        
        # 左侧信息
        self.time_label = CaptionLabel("执行时间: -")
        self.time_label.setStyleSheet("color: #666; font-size: 11px;")
        action_bar.addWidget(self.time_label)
        
        action_bar.addStretch()
        
        # 导出按钮
        self.export_btn = PushButton(FluentIcon.SAVE, "导出报告")
        self.export_btn.clicked.connect(self._on_export)
        action_bar.addWidget(self.export_btn)
        
        # 重试失败项按钮
        self.retry_btn = PushButton(FluentIcon.SYNC, "重试失败项")
        self.retry_btn.clicked.connect(self._on_retry_failed)
        self.retry_btn.setVisible(False)
        action_bar.addWidget(self.retry_btn)
        
        # 查看详细报告按钮
        self.view_detail_btn = PrimaryPushButton(FluentIcon.DOCUMENT, "查看完整报告")
        self.view_detail_btn.clicked.connect(self._on_view_detail)
        action_bar.addWidget(self.view_detail_btn)
        
        main_layout.addLayout(action_bar)
        
        # 设置初始状态
        self._set_empty_state()
    
    def _switch_page(self, index: int):
        """切换页面"""
        # 这里可以扩展为多页面切换
        pass
    
    def show_report(
        self,
        plan: Optional[CleanupPlan],
        result: ExecutionResult,
        recovery_records: Optional[List[RecoveryRecord]] = None
    ):
        """显示清理报告
        
        Args:
            plan: 清理计划（可选）
            result: 执行结果
            recovery_records: 恢复记录（可选）
        """
        self.current_plan = plan
        self.current_result = result
        
        # 生成报告
        self.current_report = self.report_generator.generate_report(
            plan, result, recovery_records
        )
        
        self.logger.info(f"[REPORT_DIALOG] 显示报告: {result.plan_id}")
        self._update_ui()
    
    def _update_ui(self):
        """更新 UI 显示"""
        report = self.current_report
        summary = report.summary
        stats = report.statistics
        
        # 更新顶部信息
        self.subtitle_label.setText(f"计划 ID: {summary['plan_id']}")
        self.time_label.setText(f"执行时间: {summary['started_at']}")
        
        # 更新统计卡片
        self.success_card.set_value(str(summary['success_items']))
        self.freed_card.set_value(summary['freed_size'])
        self.rate_card.set_value(f"{summary['success_rate']}%")
        self.duration_card.set_value(summary['duration_formatted'])
        
        # 更新风险统计面板
        if self.current_plan:
            self.risk_stats_panel.update_stats(
                safe_count=self.current_plan.safe_count,
                safe_size=sum(i.size for i in self.current_plan.items 
                              if i.ai_risk == RiskLevel.SAFE) if self.current_plan.items else 0,
                suspicious_count=self.current_plan.suspicious_count,
                suspicious_size=sum(i.size for i in self.current_plan.items 
                                    if i.ai_risk == RiskLevel.SUSPICIOUS) if self.current_plan.items else 0,
                dangerous_count=self.current_plan.dangerous_count,
                dangerous_size=sum(i.size for i in self.current_plan.items 
                                   if i.ai_risk == RiskLevel.DANGEROUS) if self.current_plan.items else 0,
                total_count=self.current_plan.total_items
            )
        else:
            # 使用 summary 中的数据
            self.risk_stats_panel.update_stats(
                safe_count=summary.get('safe_count', 0),
                safe_size=0,
                suspicious_count=summary.get('suspicious_count', 0),
                suspicious_size=0,
                dangerous_count=summary.get('dangerous_count', 0),
                dangerous_size=0,
                total_count=summary['total_items']
            )
        
        # 更新 AI 建议面板
        ai_model = summary.get('ai_model', '-')
        ai_summary = self.current_plan.ai_summary if self.current_plan else ""
        has_dangerous = (self.current_plan.dangerous_count > 0) if self.current_plan else False
        
        # 生成建议内容
        risk_summary = self._generate_risk_summary(summary, has_dangerous)
        suggestions = self._generate_suggestions(summary, stats)
        
        self.ai_suggestion_panel.update_suggestions(
            ai_model=ai_model,
            risk_summary=risk_summary,
            suggestions=suggestions,
            has_dangerous=has_dangerous
        )
        
        # 更新操作历史
        operations = self._build_operations_list()
        self.operation_history_panel.update_operations(operations)
        
        # 更新失败项面板
        if report.failures:
            self.retry_btn.setVisible(True)
            failure_ops = [
                {
                    'path': f['path'],
                    'size': f['size_bytes'],
                    'status': 'failed',
                    'risk': f['risk_level']
                }
                for f in report.failures
            ]
            self.failures_panel.update_operations(failure_ops)
        else:
            self.retry_btn.setVisible(False)
            self.failures_panel.update_operations([])
    
    def _generate_risk_summary(self, summary: Dict, has_dangerous: bool) -> str:
        """生成风险摘要"""
        if has_dangerous:
            dangerous_count = summary.get('dangerous_count', 0)
            return f"⚠️ 发现 {dangerous_count} 个危险项目，建议仔细确认后再清理。危险项目可能导致程序异常或数据丢失。"
        
        suspicious_count = summary.get('suspicious_count', 0)
        if suspicious_count > 0:
            return f"⚡ 发现 {suspicious_count} 个疑似项目，建议确认后再清理。这些文件可能被某些程序使用。"
        
        return "✅ 所有项目均为安全级别，清理操作风险较低。"
    
    def _generate_suggestions(self, summary: Dict, stats: Dict) -> str:
        """生成优化建议"""
        suggestions = []
        
        # 根据释放空间给出建议
        freed_size = summary.get('freed_size_bytes', 0)
        if freed_size > 1024 * 1024 * 1024:  # > 1GB
            suggestions.append("🎉 本次清理释放了超过 1GB 空间，建议定期进行清理保持系统流畅。")
        elif freed_size > 100 * 1024 * 1024:  # > 100MB
            suggestions.append("✨ 本次清理效果不错，建议每周进行一次系统清理。")
        
        # 根据成功率给出建议
        success_rate = summary.get('success_rate', 0)
        if success_rate < 90:
            failed_items = summary.get('failed_items', 0)
            suggestions.append(f"⚠️ 有 {failed_items} 个项目清理失败，可能是文件被占用或权限不足。")
        
        # 根据 AI 使用情况给出建议
        ai_model = summary.get('ai_model')
        if ai_model:
            suggestions.append(f"🤖 本次清理使用了 {ai_model} 进行智能分析。")
        
        # 根据扫描类型给出建议
        scan_type = summary.get('scan_type', '')
        if 'temp' in scan_type.lower() or 'cache' in scan_type.lower():
            suggestions.append("💡 临时文件和缓存会持续生成，建议设置定期自动清理。")
        
        return "\n".join(suggestions) if suggestions else "建议定期清理临时文件和缓存，保持系统流畅运行。"
    
    def _build_operations_list(self) -> List[Dict[str, Any]]:
        """构建操作列表"""
        operations = []
        
        if not self.current_plan or not self.current_result:
            return operations
        
        # 从执行结果构建操作列表
        # 成功项
        for item in self.current_plan.items[:30]:  # 限制显示数量
            # 检查是否在失败列表中
            is_failed = any(
                f.item.item_id == item.item_id 
                for f in self.current_result.failures
            )
            operations.append({
                'path': item.path,
                'size': item.size,
                'status': 'failed' if is_failed else 'success',
                'risk': item.ai_risk.value if hasattr(item.ai_risk, 'value') else str(item.ai_risk)
            })
        
        return operations
    
    def _set_empty_state(self):
        """设置空状态"""
        self.subtitle_label.setText("计划 ID: -")
        self.time_label.setText("执行时间: -")
        
        self.success_card.set_value("0")
        self.freed_card.set_value("0 B")
        self.rate_card.set_value("0%")
        self.duration_card.set_value("0s")
        
        self.risk_stats_panel.update_stats(0, 0, 0, 0, 0, 0, 0)
        self.operation_history_panel.update_operations([])
        self.failures_panel.update_operations([])
    
    def _on_export(self):
        """导出报告"""
        if not self.current_report:
            InfoBar.warning(
                "提示",
                "没有可导出的报告",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        self.export_requested.emit("json")
    
    def _on_retry_failed(self):
        """重试失败项"""
        if not self.current_report or not self.current_report.failures:
            return
        
        failed_item_ids = [f["item_id"] for f in self.current_report.failures]
        self.retry_failed_requested.emit(failed_item_ids)
        self.close()
    
    def _on_view_detail(self):
        """查看详细报告"""
        self.view_full_report.emit()
        self.close()


# ========== 便捷函数 ==========
def show_report_dialog(
    plan: Optional[CleanupPlan],
    result: ExecutionResult,
    recovery_records: Optional[List[RecoveryRecord]] = None,
    parent=None
) -> ReportDialog:
    """创建并显示报告对话框
    
    Args:
        plan: 清理计划
        result: 执行结果
        recovery_records: 恢复记录
        parent: 父组件
    
    Returns:
        ReportDialog: 报告对话框实例
    """
    dialog = ReportDialog(parent)
    dialog.show_report(plan, result, recovery_records)
    return dialog
