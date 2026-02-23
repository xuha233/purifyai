"""
清理历史页面
显示清理历史记录，支持筛选、导出和查看详情

Feature 1 & 5: Report History Loading - 集成数据库报告查看
"""
import csv
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QComboBox, QPushButton, QLabel, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ComboBox, InfoBar, InfoBarPosition,
    SegmentedWidget, FluentIcon
)

# 导入时间工具
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
from utils.time_utils import parse_iso_timestamp

from core.database import get_database


class HistoryPage(QWidget):
    """清理历史页面

    Feature 1 & 5: Report History Loading - 支持查看详细的清理报告
    """

    # 信号
    view_report = pyqtSignal(int)  # report_id - 查看详细报告
    view_plan_report = pyqtSignal(str)  # plan_id - 通过计划ID查看报告

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_database()
        self.history_data = []
        self.init_ui()
        self.load_history()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题和操作按钮
        header_layout = QHBoxLayout()
        title = StrongBodyLabel('清理历史')
        title.setStyleSheet('font-size: 24px;')
        header_layout.addWidget(title)
        header_layout.addSpacing(20)

        desc = BodyLabel('查看和管理清理历史记录')
        desc.setStyleSheet('color: #666666; font-size: 14px;')
        header_layout.addWidget(desc)
        header_layout.addStretch()

        header_layout.addSpacing(20)

        self.refresh_btn = PushButton('刷新')
        self.refresh_btn.clicked.connect(self.load_history)
        header_layout.addWidget(self.refresh_btn)

        self.export_btn = PushButton('导出')
        self.export_btn.clicked.connect(self.export_history)
        header_layout.addWidget(self.export_btn)

        self.clear_btn = PushButton('清空历史')
        self.clear_btn.clicked.connect(self.clear_history)
        header_layout.addWidget(self.clear_btn)

        layout.addLayout(header_layout)

        # 统计信息卡片
        stats_card = SimpleCardWidget()
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 15, 20, 15)

        self.total_count_label = BodyLabel('已清理: 0 次')
        self.total_count_label.setStyleSheet('font-weight: bold; font-size: 13px;')
        stats_layout.addWidget(self.total_count_label)

        stats_layout.addSpacing(30)

        self.total_size_label = BodyLabel('总释放: 0 B')
        self.total_size_label.setStyleSheet('font-weight: bold; font-size: 13px;')
        stats_layout.addWidget(self.total_size_label)

        stats_layout.addSpacing(30)

        self.avg_size_label = BodyLabel('日均: 0 B')
        self.avg_size_label.setStyleSheet('font-weight: bold; font-size: 13px;')
        stats_layout.addWidget(self.avg_size_label)

        stats_layout.addStretch()

        layout.addWidget(stats_card)

        layout.addSpacing(15)

        # 趋势图卡片 (Feature 3: Enhanced Report Features)
        try:
            from ui.report_trends_chart import ReportTrendsCard

            trends_layout = QHBoxLayout()
            trends_layout.setSpacing(15)

            # 查看趋势按钮
            self.view_trends_btn = PushButton(FluentIcon.CALENDAR, "查看清理趋势")
            self.view_trends_btn.clicked.connect(self._show_trends_dialog)
            trends_layout.addStretch()
            trends_layout.addWidget(self.view_trends_btn)

            layout.addLayout(trends_layout)
        except ImportError:
            # 趋势图组件不可用时静默跳过
            pass

        layout.addSpacing(15)

        # 筛选区域
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(BodyLabel('筛选:'))

        self.type_filter = ComboBox()
        self.type_filter.addItems(['全部类型', '系统清理', '浏览器清理', 'AppData清理', '自定义清理'])
        self.type_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.type_filter)

        filter_layout.addSpacing(15)

        filter_layout.addWidget(BodyLabel('日期范围:'))

        self.date_filter = ComboBox()
        self.date_filter.addItems(['全部时间', '今天', '最近7天', '最近30天'])
        self.date_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.date_filter)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        layout.addSpacing(15)

        # 历史记录表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['时间', '类型', '清理数量', '释放空间', '操作'])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # 允许单选
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)

    def load_history(self):
        """加载历史记录 (Feature 5: Report History Loading)

        优先加载 cleanup_reports 表中的详细报告"""
        import logging
        logger = logging.getLogger(__name__)

        # 首先尝试加载 cleanup_reports
        try:
            self.reports_data = self.db.get_cleanup_reports(limit=200)
            logger.debug(f"[历史页] 加载的报告数: {len(self.reports_data)}")

            if self.reports_data:
                logger.debug(f"[历史页] 第一条报告: {self.reports_data[0]}")
                self.use_reports_mode = True
            else:
                # 回退到 clean_history
                self.history_data = self.db.get_clean_history(limit=200)
                logger.debug(f"[历史页] 回退到 clean_history: {len(self.history_data)} 条")
                self.use_reports_mode = False
        except Exception as e:
            logger.error(f"[历史页] 加载报告异常: {e}")
            # 回退到 clean_history
            self.history_data = self.db.get_clean_history(limit=200)
            self.use_reports_mode = False

        self.apply_filter()
        self.update_stats()

    def apply_filter(self):
        """应用筛选条件"""
        # 获取筛选条件
        type_filter = self.type_filter.currentText()
        date_filter = self.date_filter.currentText()

        # 计算日期范围
        date_start = None
        if date_filter == '今天':
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            date_start = today_start
        elif date_filter == '最近7天':
            from datetime import timedelta
            date_start = datetime.now() - timedelta(days=7)
        elif date_filter == '最近30天':
            from datetime import timedelta
            date_start = datetime.now() - timedelta(days=30)

        # 筛选数据
        filtered_data = []
        for item in self.history_data:
            # 类型筛选
            if type_filter != '全部类型':
                clean_type = self._get_type_name(item['clean_type'])
                if clean_type != type_filter.replace('清理', '').strip():
                    continue

            # 日期筛选
            if date_start:
                item_time = parse_iso_timestamp(item['timestamp_cleaned_at'])
                if item_time < date_start:
                    continue

            filtered_data.append(item)

        # 填充表格
        self._fill_table(filtered_data)

    def _fill_table(self, data: List[Dict[str, Any]]):
        """填充表格"""
        self.table.setRowCount(0)

        for item in data:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 时间
            if 'generated_at' in item:
                # Reports data
                timestamp = parse_iso_timestamp(item['generated_at'])
                time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                # 类型
                scan_type = item.get('scan_type', 'unknown')
                type_name = self._get_type_name(scan_type)
                # 清理数量
                summary = item.get('report_summary', {})
                count = summary.get('total_items', 0)
                # 释放空间
                size_bytes = item.get('total_freed_size', 0)
                size_str = self._format_size(size_bytes)
                # 操作 - 查看详细报告
                action_btn = QPushButton('查看报告')
                action_btn.clicked.connect(
                    lambda checked, report_id=item.get('report_id'), plan_id=item.get('plan_id'):
                    self._view_detailed_report(report_id, plan_id)
                )
            else:
                # Legacy clean_history data
                timestamp = parse_iso_timestamp(item['timestamp_cleaned_at'])
                time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                # 类型
                type_name = self._get_type_name(item['clean_type'])
                # 清理数量
                count = item['items_count']
                # 释放空间
                size_str = self._format_size(item['total_size'])
                # 操作
                action_btn = QPushButton('查看')
                action_btn.clicked.connect(lambda checked, item=item: self.show_details(item))

            # 设置表格项
            self.table.setItem(row, 0, QTableWidgetItem(time_str))

            # 类型
            type_item = QTableWidgetItem(type_name)
            if '系统' in type_name:
                type_item.setForeground(Qt.darkBlue)
            elif '浏览器' in type_name:
                type_item.setForeground(Qt.darkGreen)
            elif 'AppData' in type_name:
                type_item.setForeground(Qt.darkMagenta)
            self.table.setItem(row, 1, type_item)

            # 清理数量
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, count_item)

            # 释放空间
            size_item = QTableWidgetItem(size_str)
            self.table.setItem(row, 3, size_item)

            # 操作
            self.table.setCellWidget(row, 4, action_btn)

    def _view_detailed_report(self, report_id: Optional[int], plan_id: Optional[str]):
        """查看详细清理报告 (Feature 5: Report History Loading)

        Args:
            report_id: 报告ID
            plan_id: 计划ID
        """
        if report_id:
            self.view_report.emit(report_id)
        elif plan_id:
            self.view_plan_report.emit(plan_id)
        else:
            InfoBar.warning(
                "提示",
                "无法查看此报告的信息",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )

    def _get_type_name(self, clean_type: str) -> str:
        """获取类型名称"""
        type_map = {
            'system': '系统清理',
            'browser': '浏览器清理',
            'appdata': 'AppData清理',
            'custom': '自定义清理',
            'auto_daily': '自动清理（每日）',
            'auto_disk': '自动清理（磁盘）'
        }
        return type_map.get(clean_type, clean_type)

    def _format_size(self, size_bytes: int) -> str:
        """格式化大小"""
        if size_bytes == 0:
            return '0 B'

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f'{size:.2f} {units[unit_index]}'

    def update_stats(self):
        """更新统计信息"""
        # 使用当前可用的数据（reports_data 或 history_data）
        reports_data = getattr(self, 'reports_data', [])
        data = reports_data if reports_data else getattr(self, 'history_data', [])

        if not data:
            self.total_count_label.setText('已清理: 0 次')
            self.total_size_label.setText('总释放: 0 B')
            self.avg_size_label.setText('日均: 0 B')
            return

        total_count = len(data)

        # 计算总释放空间
        if 'total_freed_size' in data[0]:
            # Reports data
            total_size = sum(item['total_freed_size'] for item in data)
        else:
            # History data
            total_size = sum(item['total_size'] for item in data)

        self.total_count_label.setText(f'已清理: {total_count} 次')
        self.total_size_label.setText(f'总释放: {self._format_size(total_size)}')

        # 计算日均
        if total_count > 1:
            time_key = 'generated_at' if 'generated_at' in data[0] else 'timestamp_cleaned_at'
            first_time = parse_iso_timestamp(data[-1][time_key])
            last_time = parse_iso_timestamp(data[0][time_key])
            days = (last_time - first_time).days
            if days > 0:
                avg_size = total_size / days
                self.avg_size_label.setText(f'日均: {self._format_size(avg_size)}')
            else:
                self.avg_size_label.setText(f'日均: {self._format_size(total_size)}')
        else:
            self.avg_size_label.setText(f'日均: {self._format_size(total_size)}')

    def show_details(self, item: Dict[str, Any]):
        """显示详情"""
        details = [
            f"清理类型: {self._get_type_name(item['clean_type'])}",
            f"清理时间: {item['timestamp_cleaned_at']}",
            f"清理数量: {item['items_count']} 项",
            f"释放空间: {self._format_size(item['total_size'])}",
            f"耗时: {item['duration_ms'] / 1000:.2f} 秒"
        ]

        # 添加详细信息
        if item.get('details'):
            try:
                detail_data = json.loads(item['details'])
                for key, value in detail_data.items():
                    if isinstance(value, (str, int, float)):
                        details.append(f"{key}: {value}")
            except:
                pass

        QMessageBox.information(self, '清理详情', '\n'.join(details))

    def export_history(self):
        """导出历史记录"""
        # 选择导出格式
        reply = QMessageBox.question(
            self,
            '选择导出格式',
            '请选择导出格式',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            # CSV
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                '导出历史记录',
                '',
                'CSV 文件 (*.csv);;所有文件 (*.*)'
            )
            if file_path:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                self._export_csv(file_path)
        else:
            # JSON
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                '导出历史记录',
                '',
                'JSON 文件 (*.json);;所有文件 (*.*)'
            )
            if file_path:
                if not file_path.endswith('.json'):
                    file_path += '.json'
                self._export_json(file_path)

    def _export_csv(self, file_path: str):
        """导出为 CSV"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['时间', '类型', '清理数量', '释放空间', '耗时(ms)'])

                for item in self.history_data:
                    timestamp = parse_iso_timestamp(item['timestamp_cleaned_at'])
                    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

                    writer.writerow([
                        time_str,
                        self._get_type_name(item['clean_type']),
                        item['items_count'],
                        item['total_size'],
                        item['duration_ms']
                    ])

            QMessageBox.information(self, '成功', f'历史记录已导出到:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败:\n{str(e)}')

    def _export_json(self, file_path: str):
        """导出为 JSON"""
        try:
            export_data = []
            for item in self.history_data:
                timestamp = datetime.fromisoformat(item['timestamp_cleaned_at'].replace('Z', '+00:00'))

                export_item = {
                    'time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': self._get_type_name(item['clean_type']),
                    'items_count': item['items_count'],
                    'size': item['total_size'],
                    'size_formatted': self._format_size(item['total_size']),
                    'duration_ms': item['duration_ms']
                }

                if item.get('details'):
                    try:
                        export_item['details'] = json.loads(item['details'])
                    except:
                        export_item['details'] = item['details']

                export_data.append(export_item)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(self, '成功', f'历史记录已导出到:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出失败:\n{str(e)}')

    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self,
            '确认清空',
            '确定要清空所有清理历史记录吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            conn = None
            try:
                # 清空数据库中的历史记录（使用事务）
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM clean_history')
                conn.commit()

                # 重新加载
                self.load_history()

                QMessageBox.information(self, '成功', '历史记录已清空')
            except Exception as e:
                messagebox_text = f'清空失败:\n{str(e)}'
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('错误')
                msg_box.setText('清空失败')
                msg_box.setDetailedText(str(e))
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.exec_()

                # 事务回滚
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
            finally:
                if conn:
                    conn.close()

    def _show_trends_dialog(self):
        """显示趋势对话框 (Feature 3: Enhanced Report Features)"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            from ui.report_trends_chart import ReportTrendsCard

            # 获取报告数据
            reports_data = getattr(self, 'reports_data', [])
            if not reports_data:
                InfoBar.warning(
                    "提示",
                    "暂无报告数据",
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
            trends_card.update_trends(reports_data)
            layout.addWidget(trends_card)

            dialog.exec()

            logger.info("[历史页] 趋势图已显示")

        except ImportError:
            InfoBar.warning(
                "提示",
                "趋势图组件不可用",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        except Exception as e:
            logger.error(f"[历史页] 显示趋势图失败: {e}")
            InfoBar.error(
                "错误",
                f"显示趋势图失败: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
