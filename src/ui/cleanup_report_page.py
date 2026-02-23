# -*- coding: utf-8 -*-
"""
清理报告页面 UI (Cleanup Report Page)

显示清理执行结果详情：
- 清理摘要卡片
- 统计数据概览
- 失败项表格
- 重试失败项
- 恢复已删除项目
- 导出报告 (JSON/HTML)
- 返回扫描页面
"""
import os
from typing import Optional, List
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QFileDialog
)
from PyQt5.QtGui import QColor, QBrush

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel, SimpleCardWidget,
    CardWidget, PushButton, PrimaryPushButton, InfoBar,
    InfoBarPosition, IconWidget, FluentIcon,
    ScrollArea, Pivot, SegmentedWidget, ToolButton, RoundMenu, Action,
    Flyout, FlyoutAnimationType, ComboBox
)

from core.cleanup_report_generator import (
    CleanupReport, CleanupReportGenerator, get_report_generator
)
from core.models_smart import (
    CleanupPlan, ExecutionResult, RecoveryRecord,
    CleanupItem, RiskLevel, FailureInfo
)
from core.recovery_manager import RecoveryManager, get_recovery_manager
from core.backup_manager import BackupManager, get_backup_manager
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
    BORDER = "#e0e0e0"


# ========== 统计卡片 ==========
class StatCard(CardWidget):
    """统计卡片"""

    def __init__(self, icon: FluentIcon, title: str, value: str,
                 subtitle: str = "", color: str = ThemeColors.PRIMARY,
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(40, 40)
        icon_widget.setStyleSheet(f"color: {color};")
        layout.addWidget(icon_widget)

        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.value_label = StrongBodyLabel(value)
        self.value_label.setStyleSheet(f"font-size: 24px; color: {color};")
        content_layout.addWidget(self.value_label)

        self.title_label = BodyLabel(title)
        self.title_label.setStyleSheet("font-size: 13px; color: #666;")
        content_layout.addWidget(self.title_label)

        if subtitle:
            self.subtitle_label = BodyLabel(subtitle)
            self.subtitle_label.setStyleSheet("font-size: 11px; color: #999;")
            content_layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None

        layout.addLayout(content_layout)
        layout.addStretch()

    def set_value(self, value: str):
        """更新数值"""
        self.value_label.setText(value)

    def set_title(self, title: str):
        """更新标题"""
        self.title_label.setText(title)


# ========== 失败项表格 ==========
class FailuresTable(QTableWidget):
    """失败项表格"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置表格属性
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "路径", "大小", "风险等级", "错误类型", "建议操作", "时间"
        ])

        # 设置表格样式
        self.setStyleSheet("""
            QTableWidget {
              gridline-color: #e0e0e0;
              background-color: white;
              selection-background-color: #e3f2fd;
            }
            QTableWidget::item {
              padding: 8px;
              border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
              background-color: #e3f2fd;
            }
            QHeaderView::section {
              background-color: #f8f9fa;
              color: #666;
              padding: 10px;
              border: none;
              border-bottom: 1px solid #e0e0e0;
              font-weight: 600;
            }
        """)

        # 设置表头
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 路径自动拉伸
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        # 设置行高
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)

        # 设置属性
        self.setSortingEnabled(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def load_failures(self, failures: List[Dict]):
        """加载失败项列表"""
        self.setRowCount(len(failures))

        for row, fail in enumerate(failures, start=0):
            self._create_row(row, fail)

    def _create_row(self, row: int, fail: Dict):
        """创建表格行"""
        # 路径
        path_item = QTableWidgetItem(fail["path"])
        path_item.setData(Qt.UserRole, fail["item_id"])  # 存储item_id
        path_item.setToolTip(fail["path"])
        self.setItem(row, 0, path_item)

        # 大小
        size_item = QTableWidgetItem(fail["size"])
        size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setItem(row, 1, size_item)

        # 风险等级
        risk_item = QTableWidgetItem(fail["risk_display"])
        risk_item.setTextAlignment(Qt.AlignCenter)
        risk_item.setBackground(self._get_risk_bg(fail["risk_level"]))
        risk_item.setForeground(self._get_risk_fg(fail["risk_level"]))
        self.setItem(row, 2, risk_item)

        # 错误类型
        error_item = QTableWidgetItem(fail["error_type_display"])
        error_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 3, error_item)

        # 建议操作
        action_item = QTableWidgetItem(fail["suggested_action_display"])
        action_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 4, action_item)

        # 时间
        time_item = QTableWidgetItem(fail["timestamp"])
        time_item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 5, time_item)

    def _get_risk_bg(self, risk_level: str) -> QBrush:
        """获取风险等级背景色"""
        colors = {
            "safe": QColor("#e6f7e6"),
            "suspicious": QColor("#fff3e0"),
            "dangerous": QColor("#fee2e2"),
        }
        return QBrush(colors.get(risk_level, QColor("#f5f5f5")))

    def _get_risk_fg(self, risk_level: str) -> QBrush:
        """获取风险等级前景色"""
        colors = {
            "safe": QColor("#28a745"),
            "suspicious": QColor("#ff9800"),
            "dangerous": QColor("#dc3545"),
        }
        return QBrush(colors.get(risk_level, QColor("#666666")))


# ========== 清理报告页面 ==========
class CleanupReportPage(QWidget):
    """清理报告页面

    显示清理执行结果的详细报告
    """

    return_to_scan = pyqtSignal()
    retry_failed = pyqtSignal(list)
    navigate_to_recovery = pyqtSignal()
    view_trends = pyqtSignal()  # 查看趋势图

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_report: Optional[CleanupReport] = None
        self.current_plan: Optional[CleanupPlan] = None
        self.current_result: Optional[ExecutionResult] = None

        self.report_generator = get_report_generator()
        self.recovery_manager = get_recovery_manager()
        self.backup_manager = get_backup_manager()

        # 获取 smart_cleaner 实例用于重试 (Feature 2: Retry Failed Items)
        self.cleaner = None

        # 报告历史数据 (用于趋势图和对比)
        self.report_history: List[Dict] = []

        self.logger = logger
        self._load_report_history()

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ========== 顶部标题栏 ==========
        top_bar = QHBoxLayout()

        self.title_label = SubtitleLabel("清理报告")
        self.title_label.setMinimumWidth(200)
        top_bar.addWidget(self.title_label)

        top_bar.addStretch()

        # 导出按钮
        self.export_btn = ToolButton(FluentIcon.SAVE, self)
        self.export_btn.setToolTip("导出报告")
        self.export_btn.clicked.connect(self._on_export_report)
        top_bar.addWidget(self.export_btn)

        # 返回按钮
        self.back_btn = ToolButton(FluentIcon.HOME, self)
        self.back_btn.setToolTip("返回扫描")
        self.back_btn.clicked.connect(self.return_to_scan.emit)
        top_bar.addWidget(self.back_btn)

        main_layout.addLayout(top_bar)

        # ========== 滚动区域 ==========
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scroll_content = QWidget()
        scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 报告信息卡片 ==========
        self.info_card = SimpleCardWidget()
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(16)

        # 计划ID
        self.plan_id_label = BodyLabel("计划 ID: -")
        info_layout.addWidget(self.plan_id_label)

        # 执行状态
        self.status_label = BodyLabel("状态: -")
        info_layout.addWidget(self.status_label)

        # 执行时间
        self.time_label = BodyLabel("执行时间: -")
        info_layout.addWidget(self.time_label)

        # 扫描类型
        self.scan_type_label = BodyLabel("扫描类型: -")
        info_layout.addWidget(self.scan_type_label)

        scroll_layout.addWidget(self.info_card)

        # ========== 统计卡片区域 ==========
        self.stats_card = CardWidget()
        stats_layout = QHBoxLayout(self.stats_card)
        stats_layout.setSpacing(12)
        stats_layout.setContentsMargins(16, 16, 16, 16)

        # 成功卡片
        self.success_card = StatCard(
            FluentIcon.ACCEPT,
            "成功项目",
            "0",
            "已清理",
            ThemeColors.SUCCESS
        )
        stats_layout.addWidget(self.success_card)

        # 失败卡片
        self.failed_card = StatCard(
            FluentIcon.CANCEL,
            "失败项目",
            "0",
            "异常",
            ThemeColors.DANGER
        )
        stats_layout.addWidget(self.failed_card)

        # 跳过卡片
        self.skipped_card = StatCard(
            FluentIcon.CANCEL,
            "跳过项目",
            "0",
            "已忽略",
            ThemeColors.WARNING
        )
        stats_layout.addWidget(self.skipped_card)

        # 释放空间卡片
        self.freed_card = StatCard(
            FluentIcon.FOLDER,
            "释放空间",
            "0 B",
            "磁盘清理",
            ThemeColors.PRIMARY
        )
        stats_layout.addWidget(self.freed_card)

        scroll_layout.addWidget(self.stats_card)

        # ========== 详细统计区域 ==========
        self.detail_stats_card = CardWidget()
        detail_layout = QHBoxLayout(self.detail_stats_card)
        detail_layout.setSpacing(12)
        detail_layout.setContentsMargins(16, 16, 16, 16)

        # 成功率卡片
        self.rate_card = StatCard(
            FluentIcon.CLOUD,
            "成功率",
            "0%",
            "质量指标",
            ThemeColors.SUCCESS
        )
        detail_layout.addWidget(self.rate_card)

        # 执行时长卡片
        self.duration_card = StatCard(
            FluentIcon.HISTORY,
            "执行时长",
            "0s",
            "时间消耗",
            ThemeColors.PRIMARY
        )
        detail_layout.addWidget(self.duration_card)

        # 总项目卡片
        self.total_card = StatCard(
            FluentIcon.DOCUMENT,
            "总项目数",
            "0",
            "扫描结果",
            ThemeColors.PRIMARY
        )
        detail_layout.addWidget(self.total_card)

        # AI 模型卡片
        self.ai_model_card = StatCard(
            FluentIcon.ROBOT,
            "AI 模型",
            "-",
            "风险评估",
            ThemeColors.PRIMARY
        )
        detail_layout.addWidget(self.ai_model_card)

        scroll_layout.addWidget(self.detail_stats_card)

        # ========== 失败项区域 ==========
        self.failures_card = CardWidget()
        failures_layout = QVBoxLayout(self.failures_card)
        failures_layout.setSpacing(12)
        failures_layout.setContentsMargins(16, 16, 16, 16)

        # 标题
        failures_header = QHBoxLayout()
        self.failures_title = SubtitleLabel("失败项列表")
        failures_header.addWidget(self.failures_title)
        failures_header.addStretch()

        # 重试按钮
        self.retry_btn = PrimaryPushButton(FluentIcon.SYNC, "重试失败项")
        self.retry_btn.clicked.connect(self._on_retry_failed)
        self.retry_btn.setEnabled(False)
        failures_header.addWidget(self.retry_btn)

        failures_layout.addLayout(failures_header)

        # 表格
        self.failures_table = FailuresTable()
        self.failures_table.setFixedHeight(300)
        failures_layout.addWidget(self.failures_table)

        scroll_layout.addWidget(self.failures_card)

        # ========== 操作区域 ==========
        self.action_card = SimpleCardWidget()
        action_layout = QHBoxLayout(self.action_card)
        action_layout.setSpacing(12)
        action_layout.setContentsMargins(16, 12, 16, 12)

        action_layout.addStretch()

        # 查看趋势按钮 (Feature 3: Enhanced Report Features)
        self.view_trends_btn = PushButton(FluentIcon.PIE_SINGLE, "查看趋势")
        self.view_trends_btn.clicked.connect(self._on_view_trends)
        action_layout.addWidget(self.view_trends_btn)

        # 对比报告按钮 (Feature 3: Enhanced Report Features)
        self.compare_btn = PushButton(FluentIcon.SYNC, "对比报告")
        self.compare_btn.clicked.connect(self._on_compare_reports)
        action_layout.addWidget(self.compare_btn)

        # 导出 JSON 按钮
        self.export_json_btn = PushButton(FluentIcon.CODE, "导出 JSON")
        self.export_json_btn.clicked.connect(lambda: self._export_as("json"))
        action_layout.addWidget(self.export_json_btn)

        # 导出 HTML 按钮
        self.export_html_btn = PushButton(FluentIcon.DOCUMENT, "导出 HTML")
        self.export_html_btn.clicked.connect(lambda: self._export_as("html"))
        action_layout.addWidget(self.export_html_btn)

        # 查看恢复记录按钮
        self.view_recovery_btn = PushButton(FluentIcon.HISTORY, "查看恢复记录")
        self.view_recovery_btn.clicked.connect(self.navigate_to_recovery.emit)
        action_layout.addWidget(self.view_recovery_btn)

        scroll_layout.addWidget(self.action_card)
        scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # 初始状态
        self._set_empty_state()

    def set_cleaner(self, cleaner):
        """设置 SmartCleaner 实例（用于重试功能）

        Args:
            cleaner: SmartCleaner 实例
        """
        self.cleaner = cleaner

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

        self.logger.info(f"[REPORT] 显示报告: {result.plan_id}")
        self._update_ui_with_report()

    def _update_ui_with_report(self):
        """根据报告更新 UI"""
        report = self.current_report
        summary = report.summary
        stats = report.statistics

        # 更新顶部信息
        self.plan_id_label.setText(f"计划 ID: {summary['plan_id']}")
        self.status_label.setText(f"状态: {summary['status']}")
        self.time_label.setText(f"执行时间: {summary['started_at']}")
        self.scan_type_label.setText(f"扫描类型: {summary.get('scan_type', '-')}")

        # 更新统计卡片
        self.success_card.set_value(str(summary['success_items']))
        self.failed_card.set_value(str(summary['failed_items']))
        self.skipped_card.set_value(str(summary['skipped_items']))
        self.freed_card.set_value(summary['freed_size'])

        # 更新详细统计
        self.rate_card.set_value(f"{summary['success_rate']}%")
        self.duration_card.set_value(summary['duration_formatted'])
        self.total_card.set_value(str(summary['total_items']))

        # AI 模型信息
        ai_model = summary.get('ai_model', '-')
        if summary.get('used_rule_engine', False):
            ai_model = f"{ai_model} + 规则"
        self.ai_model_card.set_value(ai_model)

        # 更新失败项表格
        if report.failures:
            self.failures_title.setText(f"失败项列表 ({len(report.failures)})")
            self.failures_card.setVisible(True)
            self.failures_table.load_failures(report.failures)
            self.retry_btn.setEnabled(True)
        else:
            self.failures_title.setText("失败项列表 (无)")
            self.failures_card.setVisible(True)
            self.failures_table.setRowCount(0)
            self.retry_btn.setEnabled(False)

    def _set_empty_state(self):
        """设置空状态"""
        self.plan_id_label.setText("计划 ID: -")
        self.status_label.setText("状态: -")
        self.time_label.setText("执行时间: -")
        self.scan_type_label.setText("扫描类型: -")

        self.success_card.set_value("0")
        self.failed_card.set_value("0")
        self.skipped_card.set_value("0")
        self.freed_card.set_value("0 B")

        self.rate_card.set_value("0%")
        self.duration_card.set_value("0s")
        self.total_card.set_value("0")
        self.ai_model_card.set_value("-")

        self.failures_title.setText("失败项列表")
        self.failures_table.setRowCount(0)
        self.retry_btn.setEnabled(False)

    def _on_retry_failed(self):
        """重试失败项"""
        if not self.current_report or not self.current_report.failures:
            return

        # 获取失败项的 item_id 列表
        failed_item_ids = [
            fail["item_id"]
            for fail in self.current_report.failures
        ]

        self.logger.info(f"[REPORT] 重试失败项: {len(failed_item_ids)} 项")

        # 如果有 smart_cleaner 实例，直接重试
        if self.cleaner:
            try:
                # 检查是否处于可以重试的状态
                from core.smart_cleaner import SmartCleanPhase
                if self.cleaner.get_current_phase() != SmartCleanPhase.IDLE:
                    InfoBar.warning(
                        "提示",
                        "请等待当前操作完成后再重试",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=2000
                    )
                    return

                # 执行重试
                success = self.cleaner.retry_failed_items(failed_item_ids)
                if success:
                    InfoBar.success(
                        "重试启动",
                        f"正在重试 {len(failed_item_ids)} 个失败项...",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=3000
                    )
                    self.retry_btn.setEnabled(False)
                    self.retry_btn.setText("重试中...")
                else:
                    InfoBar.warning(
                        "提示",
                        "没有有效的失败项可重试",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=2000
                    )
            except Exception as e:
                self.logger.error(f"[REPORT] 重试失败: {e}")
                InfoBar.error(
                    "重试失败",
                    f"重试失败: {str(e)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
        else:
            # 发出信号让父组件处理
            self.retry_failed.emit(failed_item_ids)

    def load_report_by_id(self, report_id: int):
        """从数据库加载历史报告 (Feature 1: Report History Loading)

        Args:
            report_id: 报告ID
        """
        from core.database import get_database

        db = get_database()
        report_data = db.get_cleanup_report(report_id=report_id)

        if not report_data:
            InfoBar.warning(
                "提示",
                "报告不存在或已被删除",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        # 重构报告对象（简化版本，因为原始 ExecutionResult 无法从 JSON 恢复）
        class SimpleReport:
            def __init__(self, data):
                self.plan_id = data.get('plan_id', '')
                self.summary = data.get('report_summary', {})
                self.statistics = data.get('report_statistics', {})
                self.failures = data.get('report_failures', [])
                self.recovery_records = []
                self.generated_at = data.get('generated_at', '')

        self.current_report = SimpleReport(report_data)
        self._update_ui_with_report()

        self.logger.info(f"[REPORT] 已加载历史报告: report_id={report_id}")

    def load_report_by_plan_id(self, plan_id: str):
        """从数据库加载历史报告（通过计划ID）

        Args:
            plan_id: 计划ID
        """
        from core.database import get_database

        db = get_database()
        report_data = db.get_cleanup_report(plan_id=plan_id)

        if not report_data:
            InfoBar.warning(
                "提示",
                f"计划 {plan_id} 的报告不存在",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        # 重构报告对象
        class SimpleReport:
            def __init__(self, data):
                self.plan_id = data.get('plan_id', '')
                self.summary = data.get('report_summary', {})
                self.statistics = data.get('report_statistics', {})
                self.failures = data.get('report_failures', [])
                self.recovery_records = []
                self.generated_at = data.get('generated_at', '')

        self.current_report = SimpleReport(report_data)
        self._update_ui_with_report()

        self.logger.info(f"[REPORT] 已加载历史报告: plan_id={plan_id}")

    def _on_export_report(self):
        """导出报告（快捷菜单）"""
        menu = RoundMenu(parent=self)

        json_action = Action(FluentIcon.CODE, "导出为 JSON", menu)
        json_action.triggered.connect(lambda: self._export_as("json"))
        menu.addAction(json_action)

        html_action = Action(FluentIcon.DOCUMENT, "导出为 HTML", menu)
        html_action.triggered.connect(lambda: self._export_as("html"))
        menu.addAction(html_action)

        menu.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def _export_as(self, format: str):
        """导出报告为指定格式

        Args:
            format: 导出格式 ("json" 或 "html")
        """
        if not self.current_report:
            InfoBar.warning(
                "提示",
                "没有可导出的报告",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return

        # 获取保存路径
        extensions = {
            "json": "JSON 文件 (*.json)",
            "html": "HTML 文件 (*.html)",
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"导出 {format.upper()} 报告",
            f"cleanup_report_{self.current_report.plan_id}.{format}",
            extensions[format]
        )

        if not file_path:
            return

        # 导出报告
        success = False
        if format == "json":
            success = self.report_generator.export_to_json(self.current_report, file_path)
        elif format == "html":
            success = self.report_generator.export_to_html(self.current_report, file_path)

        if success:
            InfoBar.success(
                "导出成功",
                f"报告已保存到: {os.path.basename(file_path)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            self.logger.info(f"[REPORT] 导出 {format.upper()} 成功: {file_path}")
        else:
            InfoBar.error(
                "导出失败",
                f"无法导出报告到: {os.path.basename(file_path)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
            self.logger.error(f"[REPORT] 导出 {format.upper()} 失败: {file_path}")

    def show_failure_list(self):
        """显示失败项列表"""
        if self.scroll_content:
            # 滚动到失败项区域
            self.scroll_area.ensureVisible(
                self.failures_card.pos().x(),
                self.failures_card.pos().y()
            )

    # ========== Feature 3: Enhanced Report Features ==========

    def _load_report_history(self):
        """加载报告历史数据

        用于趋势图和对比功能
        """
        from core.database import get_database

        try:
            db = get_database()
            self.report_history = db.get_cleanup_reports(limit=50)
            # self.logger.info(f"[REPORT] 加载报告历史: {len(self.report_history)} 条")
        except Exception as e:
            # self.logger.error(f"[REPORT] 加载报告历史失败: {e}")
            self.report_history = []

    def _on_view_trends(self):
        """查看趋势图 (Feature 3: Enhanced Report Features)"""
        from ui.report_trends_chart import ReportTrendsCard

        if not self.report_history:
            InfoBar.warning(
                "提示",
                "暂无历史报告数据",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        # 创建趋势图对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("清理趋势")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        # 添加趋势卡片
        trends_card = ReportTrendsCard()
        trends_card.update_trends(self.report_history)
        layout.addWidget(trends_card)

        dialog.exec()

        self.logger.info("[REPORT] 趋势图已显示")

    def _on_compare_reports(self):
        """对比报告 (Feature 3: Enhanced Report Features)"""
        if len(self.report_history) < 2:
            InfoBar.warning(
                "提示",
                "需要至少2个历史报告才能进行对比",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        from ui.report_compare_dialog import show_report_compare_dialog

        # 更新历史数据（包含当前报告）
        reports = self.report_history.copy()

        # 如果有当前报告，添加到开头
        if self.current_report and hasattr(self.current_report, 'plan_id'):
            current_report_data = {
                'plan_id': self.current_report.plan_id,
                'report_summary': self.current_report.summary,
                'report_statistics': self.current_report.statistics,
                'report_failures': self.current_report.failures,
                'generated_at': self.current_report.generated_at.isoformat(),
            }
            reports.insert(0, current_report_data)

        # 显示对比对话框
        result = show_report_compare_dialog(reports, parent=self)

        if result:
            self.logger.info(f"[REPORT] 报告对比完成: {result}")
