"""
清理历史页面
显示清理历史记录，支持筛选、导出和查看详情
"""
import csv
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QComboBox, QPushButton, QLabel
)
from PyQt5.QtCore import Qt, QDate

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ComboBox
)

# 导入时间工具
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
from utils.time_utils import parse_iso_timestamp

from core.database import get_database


class HistoryPage(QWidget):
    """清理历史页面"""

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
        """加载历史记录"""
        import logging
        logger = logging.getLogger(__name__)
        self.history_data = self.db.get_clean_history(limit=200)
        logger.debug(f"[历史页] 加载的记录数: {len(self.history_data)}")
        if self.history_data and len(self.history_data) > 0:
            logger.debug(f"[历史页] 第一条记录: {self.history_data[0]}")
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
            timestamp = parse_iso_timestamp(item['timestamp_cleaned_at'])
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            self.table.setItem(row, 0, QTableWidgetItem(time_str))

            # 类型
            type_name = self._get_type_name(item['clean_type'])
            type_item = QTableWidgetItem(type_name)
            # 根据类型设置不同颜色
            if '系统' in type_name:
                type_item.setForeground(Qt.darkBlue)
            elif '浏览器' in type_name:
                type_item.setForeground(Qt.darkGreen)
            elif 'AppData' in type_name:
                type_item.setForeground(Qt.darkMagenta)
            self.table.setItem(row, 1, type_item)

            # 清理数量
            count_item = QTableWidgetItem(str(item['items_count']))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, count_item)

            # 释放空间
            size_str = self._format_size(item['total_size'])
            size_item = QTableWidgetItem(size_str)
            self.table.setItem(row, 3, size_item)

            # 操作
            action_btn = QPushButton('查看')
            action_btn.clicked.connect(lambda checked, item=item: self.show_details(item))
            self.table.setCellWidget(row, 4, action_btn)

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
        if not self.history_data:
            self.total_count_label.setText('已清理: 0 次')
            self.total_size_label.setText('总释放: 0 B')
            self.avg_size_label.setText('日均: 0 B')
            return

        total_count = len(self.history_data)
        total_size = sum(item['total_size'] for item in self.history_data)

        self.total_count_label.setText(f'已清理: {total_count} 次')
        self.total_size_label.setText(f'总释放: {self._format_size(total_size)}')

        # 计算日均
        if total_count > 1:
            first_time = parse_iso_timestamp(self.history_data[-1]['timestamp_cleaned_at'])
            last_time = parse_iso_timestamp(self.history_data[0]['timestamp_cleaned_at'])
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
