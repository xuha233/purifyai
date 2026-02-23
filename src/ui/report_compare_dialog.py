# -*- coding: utf-8 -*-
"""
报告对比对话框 (Report Compare Dialog)

Feature 3: Enhanced Report Features

功能:
- 对比两个或多个清理报告
- 显示差异统计
- 数据可视化对比
"""
from typing import List, Dict, Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter, QWidget
)
from PyQt5.QtGui import QColor, QFont

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel, SimpleCardWidget,
    CardWidget, FluentIcon, IconWidget, PrimaryPushButton, PushButton,
    ComboBox
)

from utils.logger import get_logger

logger = get_logger(__name__)


# ========== 对比数据卡片 ==========
class CompareDataCard(SimpleCardWidget):
    """对比数据卡片

    显示单个报告的摘要数据
    """

    def __init__(self, report: Dict, index: int, parent=None):
        super().__init__(parent)
        self.report = report
        self.index = index
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # 标题
        summary = self.report.get('report_summary', {})
        header_layout = QHBoxLayout()

        icon = IconWidget(FluentIcon.DOCUMENT)
        icon.setFixedSize(24, 24)
        icon.setStyleSheet('color: #0078D4;')
        header_layout.addWidget(icon)

        title = StrongBodyLabel(f"报告 {self.index}")
        title.setStyleSheet('font-size: 14px;')
        header_layout.addWidget(title)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 时间
        time_str = self.report.get('generated_at', '')
        time_label = BodyLabel(f"时间: {time_str[:19] if len(time_str) > 19 else time_str}")
        time_label.setStyleSheet('color: #666; font-size: 12px;')
        layout.addWidget(time_label)

        # 类型
        scan_type = summary.get('scan_type', '-')
        type_label = BodyLabel(f"类型: {scan_type}")
        type_label.setStyleSheet('color: #666; font-size: 12px;')
        layout.addWidget(type_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet('background-color: #e0e0e0;')
        layout.addWidget(line)

        # 数据行
        self._add_data_row(layout, "清理数量", str(summary.get('total_items', 0)))
        self._add_data_row(layout, "成功项", str(summary.get('success_items', 0)))
        self._add_data_row(layout, "失败项", str(summary.get('failed_items', 0)))
        self._add_data_row(layout, "释放空间", summary.get('freed_size', '0 B'))
        self._add_data_row(layout, "成功率", f"{summary.get('success_rate', 0)}%")

        layout.addStretch()

    def _add_data_row(self, layout: QVBoxLayout, label: str, value: str):
        """添加数据行

        Args:
            layout: 布局
            label: 标签
            value: 数值
        """
        row = QHBoxLayout()

        label_widget = BodyLabel(f"{label}:")
        label_widget.setStyleSheet('color: #999; font-size: 11px;')
        row.addWidget(label_widget)

        row.addStretch()

        value_widget = BodyLabel(value)
        value_widget.setStyleSheet('color: #333; font-weight: 600; font-size: 12px;')
        row.addWidget(value_widget)

        layout.addLayout(row)


# ========== 对比差异显示 ==========
class CompareDifference(SimpleCardWidget):
    """对比差异显示

    显示两个报告之间的差异
    """

    def __init__(self, report1: Dict, report2: Dict, parent=None):
        super().__init__(parent)
        self.report1 = report1
        self.report2 = report2
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # 标题
        header = QHBoxLayout()
        icon = IconWidget(FluentIcon.HISTORY)
        icon.setFixedSize(24, 24)
        icon.setStyleSheet('color: #0078D4;')
        header.addWidget(icon)

        title = StrongBodyLabel("差异对比")
        title.setStyleSheet('font-size: 14px;')
        header.addWidget(title)

        header.addStretch()
        layout.addLayout(header)

        # 差异数据表格
        self.diff_table = QTableWidget()
        self.diff_table.setColumnCount(3)
        self.diff_table.setHorizontalHeaderLabels(["指标", "变化", "百分比"])

        # 设置表格样式
        self.diff_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #555;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: 600;
                font-size: 11px;
            }
        """)

        self.diff_table.horizontalHeader().setStretchLastSection(True)
        self.diff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.diff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.diff_table.verticalHeader().setVisible(False)
        self.diff_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.diff_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.diff_table.setFixedHeight(200)

        layout.addWidget(self.diff_table)
        self._calculate_differences()

    def _calculate_differences(self):
        """计算差异"""
        summary1 = self.report1.get('report_summary', {})
        summary2 = self.report2.get('report_summary', {})

        metrics = [
            ("清理数量", "total_items", ""),
            ("成功项", "success_items", ""),
            ("失败项", "failed_items", ""),
            ("释放空间", "total_size_bytes", "freed_size_bytes"),
            ("成功率", "success_rate", "%"),
        ]

        self.diff_table.setRowCount(len(metrics))

        for i, (label, key, suffix) in enumerate(metrics):
            # 获取数值
            value1 = summary1.get(key, 0)
            value2 = summary2.get(key, 0)

            # 计算差异
            if "size" in key:
                diff_value = value2 - value1
                diff_str = self._format_size(diff_value)
                percent = self._calculate_percent(value1, value2) + "%"
            elif "rate" in key:
                diff_value = value2 - value1
                diff_str = f"{diff_value:+.1f}{suffix}"
                percent = f"{diff_value:+.1f}{suffix}"
            else:
                diff_value = value2 - value1
                diff_str = f"{diff_value:+d}"
                percent = self._calculate_percent(value1, value2) + "%"

            # 设置表格项
            self.diff_table.setItem(i, 0, QTableWidgetItem(label))

            diff_item = QTableWidgetItem(diff_str)
            diff_item.setTextAlignment(Qt.AlignCenter)
            self.diff_table.setItem(i, 1, diff_item)

            percent_item = QTableWidgetItem(percent)
            percent_item.setTextAlignment(Qt.AlignCenter)
            self.diff_table.setItem(i, 2, percent_item)

            # 根据差异设置颜色
            if value2 > value1:
                color = QColor("#28a745")  # 绿色 - 增加
            elif value2 < value1:
                color = QColor("#dc3545")  # 红色 - 减少
            else:
                color = QColor("#999")    # 灰色 - 不变

            diff_item.setForeground(color)
            percent_item.setForeground(color)

    def _format_size(self, size_bytes: int) -> str:
        """格式化大小"""
        if size_bytes == 0:
            return "0 B"

        sign = "+" if size_bytes > 0 else ""
        abs_size = abs(size_bytes)

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(abs_size)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{sign}{int(size)} {units[unit_index]}"
        else:
            return f"{sign}{size:.2f} {units[unit_index]}"

    def _calculate_percent(self, value1: float, value2: float) -> str:
        """计算百分比变化"""
        if value1 == 0:
            return "+100%" if value2 > 0 else "0%"

        diff = value2 - value1
        percent = (diff / value1) * 100
        return f"{percent:+.1f}"


# ========== 主对话框 ==========
class ReportCompareDialog(QDialog):
    """报告对比对话框

    用于对比两个或多个清理报告
    """

    compared = pyqtSignal(dict)  # 对比结果

    def __init__(self, reports: List[Dict], parent=None):
        super().__init__(parent)
        self.reports = reports
        self.logger = logger
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("报告对比")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = SubtitleLabel("清理报告对比")
        title.setStyleSheet('font-size: 18px;')
        layout.addWidget(title)

        # 选择器
        selector_layout = QHBoxLayout()

        selector_layout.addWidget(BodyLabel("对比报告:"))

        # 报告1选择
        self.report1_combo = ComboBox()
        self._populate_combo(self.report1_combo)
        selector_layout.addWidget(BodyLabel("报告 1:"))
        selector_layout.addWidget(self.report1_combo)

        selector_layout.addSpacing(20)

        # 报告2选择
        self.report2_combo = ComboBox()
        self._populate_combo(self.report2_combo)
        if len(self.reports) >= 2:
            self.report2_combo.setCurrentIndex(1)
        selector_layout.addWidget(BodyLabel("报告 2:"))
        selector_layout.addWidget(self.report2_combo)

        selector_layout.addStretch()

        # 比较按钮
        self.compare_btn = PrimaryPushButton(FluentIcon.SYNC, "对比")
        self.compare_btn.clicked.connect(self._on_compare)
        selector_layout.addWidget(self.compare_btn)

        layout.addLayout(selector_layout)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧：报告卡片
        self.cards_widget = QWidget()
        cards_layout = QVBoxLayout(self.cards_widget)
        cards_layout.setSpacing(12)

        # 占位符
        placeholder = BodyLabel("请选择两个报告进行对比")
        placeholder.setStyleSheet('color: #999; text-align: center;')
        placeholder.setAlignment(Qt.AlignCenter)
        cards_layout.addWidget(placeholder)

        splitter.addWidget(self.cards_widget)

        # 右侧：差异对比
        self.diff_widget = QWidget()
        diff_layout = QVBoxLayout(self.diff_widget)
        diff_layout.setSpacing(12)

        diff_placeholder = BodyLabel("对比结果将显示在这里")
        diff_placeholder.setStyleSheet('color: #999; text-align: center;')
        diff_placeholder.setAlignment(Qt.AlignCenter)
        diff_layout.addWidget(diff_placeholder)

        splitter.addWidget(self.diff_widget)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = PushButton("关闭")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        layout.addLayout(bottom_layout)

        # 连接信号
        self.report1_combo.currentIndexChanged.connect(self._on_selection_changed)
        self.report2_combo.currentIndexChanged.connect(self._on_selection_changed)

        self.logger.info("[COMPARE_DIALOG] 对话框初始化完成")

    def _populate_combo(self, combo: ComboBox):
        """填充下拉框

        Args:
            combo: 下拉框组件
        """
        for i, report in enumerate(self.reports):
            summary = report.get('report_summary', {})
            scan_type = summary.get('scan_type', 'unknown')
            time_str = report.get('generated_at', '')[:19] if report.get('generated_at') else ''
            combo.addItem(f"{scan_type} - {time_str}")

    def _on_selection_changed(self):
        """选择变化"""
        # 自动更新预览（如果选中了两个不同的报告）
        idx1 = self.report1_combo.currentIndex()
        idx2 = self.report2_combo.currentIndex()

        if idx1 != -1 and idx2 != -1 and idx1 != idx2:
            self._update_cards(idx1, idx2)

    def _update_cards(self, idx1: int, idx2: int):
        """更新报告卡片

        Args:
            idx1: 报告1索引
            idx2: 报告2索引
        """
        # 清空现有卡片
        cards_layout = self.cards_widget.layout()
        while cards_layout.count():
            item = cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新卡片
        card1 = CompareDataCard(self.reports[idx1], 1)
        card2 = CompareDataCard(self.reports[idx2], 2)
        cards_layout.addWidget(card1)
        cards_layout.addWidget(card2)

    def _on_compare(self):
        """执行对比"""
        idx1 = self.report1_combo.currentIndex()
        idx2 = self.report2_combo.currentIndex()

        if idx1 == -1 or idx2 == -1:
            return

        if idx1 == idx2:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                "提示",
                "请选择两个不同的报告进行对比",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            return

        # 更新卡片
        self._update_cards(idx1, idx2)

        # 显示差异对比
        diff_layout = self.diff_widget.layout()
        while diff_layout.count():
            item = diff_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        diff_widget = CompareDifference(self.reports[idx1], self.reports[idx2])
        diff_layout.addWidget(diff_widget)

        # 计算对比结果
        result = self._calculate_compare_result(self.reports[idx1], self.reports[idx2])
        self.compared.emit(result)

        self.logger.info(f"[COMPARE_DIALOG] 对比完成: report1={idx1}, report2={idx2}")

    def _calculate_compare_result(self, report1: Dict, report2: Dict) -> Dict:
        """计算对比结果

        Args:
            report1: 报告1
            report2: 报告2

        Returns:
            对比结果字典
        """
        summary1 = report1.get('report_summary', {})
        summary2 = report2.get('report_summary', {})

        return {
            'report_ids': [report1.get('report_id'), report2.get('report_id')],
            'scan_types': [summary1.get('scan_type'), summary2.get('scan_type')],
            'times': [report1.get('generated_at'), report2.get('generated_at')],
            'freed_space_diff': summary2.get('freed_size_bytes', 0) - summary1.get('freed_size_bytes', 0),
            'success_rate_diff': summary2.get('success_rate', 0) - summary1.get('success_rate', 0),
            'time_diff': self._parse_time(report2.get('generated_at')) -
                        self._parse_time(report1.get('generated_at'))
        }

    def _parse_time(self, time_str: str) -> float:
        """解析时间字符串

        Args:
            time_str: 时间字符串

        Returns:
            时间戳
        """
        try:
            from datetime import datetime
            return datetime.fromisoformat(time_str.replace('Z', '+00:00')).timestamp()
        except:
            return 0


# 便利函数
def show_report_compare_dialog(reports: List[Dict], parent=None) -> Optional[Dict]:
    """显示报告对比对话框

    Args:
        reports: 报告列表
        parent: 父窗口

    Returns:
        对比结果，如果用户取消则为 None
    """
    if len(reports) < 2:
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.warning(
            "提示",
            "需要至少2个报告才能进行对比",
            parent=parent,
            position=InfoBarPosition.TOP,
            duration=2000
        )
        return None

    dialog = ReportCompareDialog(reports, parent)
    result = {}

    @dialog.compared.connect
    def on_compared(compare_result):
        result.update(compare_result)

    dialog.exec()
    return result
