# -*- coding: utf-8 -*-
"""
报告趋势图组件 (Report Trends Chart)

Feature 3: Enhanced Report Features

功能:
- 显示清理历史趋势图
- 显示释放空间趋势
- 显示失败率趋势
- 显示扫描类型分布
"""
from typing import List, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QStackedWidget
)
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, SimpleCardWidget, CardWidget,
    FluentIcon, IconWidget, ComboBox, SegmentedWidget
)

from utils.logger import get_logger

logger = get_logger(__name__)


# ========== 简单图表组件 ==========
class SimpleBarChart(QWidget):
    """简单的柱状图组件（不依赖matplotlib）

    用于显示清理报告的趋势数据
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.data: List[Dict] = []
        self.color = QColor("#0078D4")
        self.bar_width = 20
        self.bar_spacing = 10

    def set_data(self, data: List[Dict], value_key: str, label_key: str,
                  color: QColor = None):
        """设置图表数据

        Args:
            data: 数据列表
            value_key: 数值键名
            label_key: 标签键名
            color: 柱状图颜色
        """
        self.data = data
        self.value_key = value_key
        self.label_key = label_key
        if color:
            self.color = color
        self.update()

    def paintEvent(self, event):
        """绘制图表"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.data:
            # 无数据时显示提示
            painter.setPen(QColor("#999"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            return

        # 计算区域
        margin_left = 60
        margin_right = 20
        margin_top = 30
        margin_bottom = 40

        chart_width = self.width() - margin_left - margin_right
        chart_height = self.height() - margin_top - margin_bottom

        # 找出最大值
        values = [item.get(self.value_key, 0) for item in self.data]
        max_value = max(values) if values else 0
        if max_value == 0:
            max_value = 1

        # 绘制背景
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(Qt.NoPen)
        painter.drawRect(margin_left, margin_top, chart_width, chart_height)

        # 绘制网格线
        grid_lines = 5
        painter.setPen(QPen(QColor("#e0e0e0"), 1, Qt.DashLine))
        for i in range(grid_lines):
            y = margin_top + (chart_height * i / grid_lines)
            painter.drawLine(margin_left, int(y), margin_left + chart_width, int(y))

            # 绘制Y轴标签
            value = int(max_value * (grid_lines - i) / grid_lines)
            painter.setPen(QColor("#666"))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(
                margin_left - 50, int(y) - 10, 50, 20,
                Qt.AlignRight | Qt.AlignVCenter,
                self._format_value(value)
            )

        # 计算柱状图宽度和位置
        num_bars = min(len(self.data), 20)  # 最多显示20条
        total_bar_width = self.bar_width * num_bars + self.bar_spacing * (num_bars - 1)
        start_x = margin_left + (chart_width - total_bar_width) / 2

        # 绘制柱状图
        for i, item in enumerate(self.data[:20]):
            value = item.get(self.value_key, 0)
            bar_height = (value / max_value) * chart_height if max_value > 0 else 0

            x = start_x + i * (self.bar_width + self.bar_spacing)
            y = margin_top + chart_height - bar_height

            # 绘制柱子
            painter.setBrush(QBrush(self.color))
            painter.setPen(QPen(self.color, 1))
            painter.drawRect(int(x), int(y), self.bar_width, int(bar_height))

            # 绘制数值
            if bar_height > 20:
                painter.setPen(QColor("#333"))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(
                    int(x), int(y) - 20, self.bar_width, 20,
                    Qt.AlignCenter, self._format_value(value)
                )

            # 绘制X轴标签
            label = item.get(self.label_key, str(i + 1))
            if len(label) > 8:
                label = label[:8] + "..."
            painter.setPen(QColor("#666"))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(
                int(x), margin_top + chart_height + 5,
                self.bar_width, 30, Qt.AlignCenter, label
            )

        # 绘制坐标轴
        painter.setPen(QPen(QColor("#333"), 2))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + chart_height)
        painter.drawLine(margin_left, margin_top + chart_height,
                      margin_left + chart_width, margin_top + chart_height)

    def _format_value(self, value: int) -> str:
        """格式化数值"""
        if value >= 1024 ** 3:
            return f"{value / (1024 ** 3):.1f} GB"
        elif value >= 1024 ** 2:
            return f"{value / (1024 ** 2):.1f} MB"
        elif value >= 1024:
            return f"{value / 1024:.1f} KB"
        return str(value)


class PieChartWidget(QWidget):
    """简单的饼图组件（扫描类型分布）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.data: Dict[str, int] = {}

        # 扫描类型颜色
        self.type_colors = {
            "system": QColor("#0078D4"),
            "browser": QColor("#28a745"),
            "appdata": QColor("#ff9800"),
            "custom": QColor("#9c27b0"),
            "retry": QColor("#dc3545"),
            "unknown": QColor("#666666")
        }

        # 扫描类型名称
        self.type_names = {
            "system": "系统",
            "browser": "浏览器",
            "appdata": "应用",
            "custom": "自定义",
            "retry": "重试",
            "unknown": "其他"
        }

    def set_data(self, data: Dict[str, int]):
        """设置饼图数据

        Args:
            data: 类型 -> 数量 的字典
        """
        self.data = data
        self.update()

    def paintEvent(self, event):
        """绘制饼图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.data:
            painter.setPen(QColor("#999"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            return

        # 计算总和
        total = sum(self.data.values())
        if total == 0:
            return

        # 绘制扇形
        center_x = self.width() // 2 - 100
        center_y = self.height() // 2
        radius = min(80, (self.height() // 2) - 20)

        start_angle = 90 * 16  # 12点方向开始

        for scan_type, count in self.data.items():
            if count == 0:
                continue

            sweep_angle = int((count / total) * 360 * 16)
            color = self.type_colors.get(scan_type, self.type_colors["unknown"])

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#fff"), 1))
            painter.drawPie(center_x - radius, center_y - radius,
                          radius * 2, radius * 2, start_angle, sweep_angle)

            start_angle = (start_angle + sweep_angle) % (360 * 16)

            # 绘制图例
            legend_x = center_x + radius + 20
            legend_y = center_y - radius + int((start_angle / 16 - 90) / 360 * radius * 2)
            painter.setBrush(QBrush(color))
            painter.drawRect(legend_x, legend_y, 12, 12)
            painter.setPen(QColor("#333"))
            painter.setFont(QFont("Arial", 9))
            name = self.type_names.get(scan_type, scan_type)
            percentage = (count / total) * 100
            painter.drawText(legend_x + 20, legend_y, 100, 15, Qt.AlignLeft | Qt.AlignVCenter,
                           f"{name}: {percentage:.1f}%")


# ========== 趋势卡片 ==========
class ReportTrendsCard(SimpleCardWidget):
    """报告趋势卡片

    显示清理报告的各种趋势图表
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 先创建图表组件
        self.bar_chart = SimpleBarChart()
        self.pie_chart = PieChartWidget()
        self.success_chart = SimpleBarChart()
        self.success_chart.color = QColor("#28a745")  # 绿色

        self.init_ui()
        self.logger = logger

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题栏
        header_layout = QHBoxLayout()

        icon = IconWidget(FluentIcon.HISTORY)
        icon.setFixedSize(24, 24)
        icon.setStyleSheet('color: #0078D4;')
        header_layout.addWidget(icon)

        title = BodyLabel("清理趋势")
        title.setStyleSheet('font-weight: bold; font-size: 14px;')
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 时间范围选择
        self.range_combo = ComboBox()
        self.range_combo.addItems(["最近7次", "最近30次", "全部"])
        self.range_combo.setCurrentIndex(0)
        header_layout.addWidget(self.range_combo)

        layout.addLayout(header_layout)

        # 图表选项卡
        self.tab_segmented = SegmentedWidget()
        self.tab_segmented.addItem('释放空间')
        self.tab_segmented.addItem('扫描类型')
        self.tab_segmented.addItem('成功率')
        self.tab_segmented.setCurrentItem('释放空间')

        layout.addWidget(self.tab_segmented)

        # 图表堆叠区域
        self.stacked_widget = QStackedWidget()

        # 柱状图页面
        bar_page = QWidget()
        bar_layout = QVBoxLayout(bar_page)
        bar_layout.setContentsMargins(0, 10, 0, 0)
        bar_layout.addWidget(self.bar_chart)
        bar_layout.addStretch()
        self.stacked_widget.addWidget(bar_page)

        # 饼图页面
        pie_page = QWidget()
        pie_layout = QHBoxLayout(pie_page)
        pie_layout.setContentsMargins(0, 10, 0, 0)
        pie_layout.addWidget(self.pie_chart)
        pie_layout.addStretch()

        # 图例
        legend_layout = QVBoxLayout()
        legend_layout.setSpacing(8)

        legend_data = [
            ("系统", "#0078D4"),
            ("浏览器", "#28a745"),
            ("应用", "#ff9800"),
            ("自定义", "#9c27b0"),
            ("重试", "#dc3545"),
        ]

        for name, color in legend_data:
            row = QHBoxLayout()
            row.setSpacing(6)

            color_box = QLabel()
            color_box.setFixedSize(12, 12)
            color_box.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            row.addWidget(color_box)

            label = BodyLabel(name)
            label.setStyleSheet('font-size: 11px; color: #666;')
            row.addWidget(label)

            row.addStretch()
            legend_layout.addLayout(row)

        legend_layout.addStretch()
        pie_layout.addLayout(legend_layout)

        self.stacked_widget.addWidget(pie_page)

        # 成功率图表页面
        success_page = QWidget()
        success_layout = QVBoxLayout(success_page)
        success_layout.setContentsMargins(0, 10, 0, 0)
        success_layout.addWidget(self.success_chart)
        success_layout.addStretch()
        self.stacked_widget.addWidget(success_page)

        layout.addWidget(self.stacked_widget)
        self.stacked_widget.setCurrentIndex(0)

        # 连接选项卡切换
        self.tab_segmented.currentItemChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        """选项卡切换处理"""
        self.stacked_widget.setCurrentIndex(index)

        layout.addWidget(self.tab_segmented)

        # 图表堆叠区域
        self.stacked_widget = QStackedWidget()

        # 柱状图页面
        bar_page = QWidget()
        bar_layout = QVBoxLayout(bar_page)
        bar_layout.setContentsMargins(0, 10, 0, 0)
        bar_layout.addWidget(self.bar_chart)
        bar_layout.addStretch()
        self.stacked_widget.addWidget(bar_page)

        # 饼图页面
        pie_page = QWidget()
        pie_layout = QHBoxLayout(pie_page)
        pie_layout.setContentsMargins(0, 10, 0, 0)
        pie_layout.addWidget(self.pie_chart)
        pie_layout.addStretch()

        # 图例
        legend_layout = QVBoxLayout()
        legend_layout.setSpacing(8)

        legend_data = [
            ("系统", "#0078D4"),
            ("浏览器", "#28a745"),
            ("应用", "#ff9800"),
            ("自定义", "#9c27b0"),
            ("重试", "#dc3545"),
        ]

        for name, color in legend_data:
            row = QHBoxLayout()
            row.setSpacing(6)

            color_box = QLabel()
            color_box.setFixedSize(12, 12)
            color_box.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            row.addWidget(color_box)

            label = BodyLabel(name)
            label.setStyleSheet('font-size: 11px; color: #666;')
            row.addWidget(label)

            row.addStretch()
            legend_layout.addLayout(row)

        legend_layout.addStretch()
        pie_layout.addLayout(legend_layout)

        self.stacked_widget.addWidget(pie_page)

        # 成功率图表页面
        success_page = QWidget()
        success_layout = QVBoxLayout(success_page)
        success_layout.setContentsMargins(0, 10, 0, 0)
        success_layout.addWidget(self.success_chart)
        success_layout.addStretch()
        self.stacked_widget.addWidget(success_page)

        layout.addWidget(self.stacked_widget)
        self.stacked_widget.setCurrentIndex(0)

    def _show_bar_chart(self):
        """显示柱状图"""
        self.stacked_widget.setCurrentIndex(0)

    def _show_pie_chart(self):
        """显示饼图"""
        self.stacked_widget.setCurrentIndex(1)

    def _show_success_chart(self):
        """显示成功率图表"""
        self.stacked_widget.setCurrentIndex(2)

    def update_trends(self, reports: List[Dict]):
        """更新趋势图

        Args:
            reports: 报告数据列表
        """
        if not reports:
            self.logger.warning("[TRENDS] 没有报告数据")
            return

        # 根据选择的时间范围筛选报告
        range_index = self.range_combo.currentIndex()
        if range_index == 0 and len(reports) > 7:
            filtered_reports = reports[:7]
        elif range_index == 1 and len(reports) > 30:
            filtered_reports = reports[:30]
        else:
            filtered_reports = reports

        # 反转报告顺序（最新的在右边）
        filtered_reports = filtered_reports[:][::-1]

        # 更新释放空间图表
        space_data = []
        for report in filtered_reports:
            summary = report.get('report_summary', {})
            space_data.append({
                "value": report.get('total_freed_size', 0),
                "label": report.get('scan_type', '')
            })

        self.bar_chart.set_data(space_data, "value", "label")

        # 更新扫描类型分布
        type_data = {}
        for report in filtered_reports:
            scan_type = report.get('scan_type', 'unknown')
            type_data[scan_type] = type_data.get(scan_type, 0) + 1

        self.pie_chart.set_data(type_data)

        # 更新成功率图表
        success_data = []
        for report in filtered_reports:
            summary = report.get('report_summary', {})
            success_rate = summary.get('success_rate', 0)
            success_data.append({
                "value": success_rate,
                "label": report.get('scan_type', '')
            })

        self.success_chart.set_data(success_data, "value", "label")

        self.logger.info(f"[TRENDS] 趋势图已更新: {len(filtered_reports)} 条报告")


# 便利函数
def get_report_trends_card() -> ReportTrendsCard:
    """获取趋势卡片实例"""
    return ReportTrendsCard()
