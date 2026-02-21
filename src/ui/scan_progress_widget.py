"""
扫描进度显示组件 - 直观的进度条和信息
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, IconWidget, FluentIcon
)


class ScanProgressWidget(SimpleCardWidget):
    """扫描进度显示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.reset()

    def setup_ui(self):
        self.setFixedHeight(140)
        self.setStyleSheet('''
            SimpleCardWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        ''')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 头部：扫描项目
        header = QHBoxLayout()
        header.setSpacing(8)

        self.scan_icon = IconWidget(FluentIcon.SEARCH)
        self.scan_icon.setFixedSize(20, 20)
        self.scan_icon.setStyleSheet('color: #0078D4;')
        header.addWidget(self.scan_icon)

        self.scan_status = BodyLabel('准备中...')
        self.scan_status.setStyleSheet('font-size: 12px; color: #666;')
        header.addWidget(self.scan_status)
        header.addStretch()

        layout.addLayout(header)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet('''
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: #f5f5f5;
                text-align: center;
                color: #666;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: #0078D4;
                border-radius: 3px;
            }
        ''')
        layout.addWidget(self.progress_bar)

        # 详细信息行
        details_row = QWidget()
        details_layout = QHBoxLayout(details_row)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(12)

        # 已扫描数量
        self.scanned_count = StrongBodyLabel('0')
        self.scanned_count.setStyleSheet('font-size: 14px; color: #2d2d2d; font-weight: 600;')
        scanned_layout = QVBoxLayout()
        scanned_layout.setSpacing(2)
        scanned_label = BodyLabel('已扫描')
        scanned_label.setStyleSheet('font-size: 10px; color: #888;')
        scanned_layout.addWidget(scanned_label)
        scanned_layout.addWidget(self.scanned_count)
        details_layout.addLayout(scanned_layout)

        # 发现项目
        self.found_count = StrongBodyLabel('0')
        self.found_count.setStyleSheet('font-size: 14px; color: #0078D4; font-weight: 600;')
        found_layout = QVBoxLayout()
        found_layout.setSpacing(2)
        found_label = BodyLabel('发现')
        found_label.setStyleSheet('font-size: 10px; color: #888;')
        found_layout.addWidget(found_label)
        found_layout.addWidget(self.found_count)
        details_layout.addLayout(found_layout)

        # 风险分布
        self.risk_info = BodyLabel('--')
        self.risk_info.setStyleSheet('font-size: 11px; color: #666;')
        risk_layout = QVBoxLayout()
        risk_label = BodyLabel('风险')
        risk_label.setStyleSheet('font-size: 10px; color: #888;')
        risk_layout.addWidget(risk_label)
        risk_layout.addWidget(self.risk_info)
        details_layout.addLayout(risk_layout)

        details_layout.addStretch()

        # 速度
        self.speed_info = BodyLabel('--')
        self.speed_info.setStyleSheet('font-size: 11px; color: #666;')
        speed_layout = QVBoxLayout()
        speed_label = BodyLabel('速度')
        speed_label.setStyleSheet('font-size: 10px; color: #888;')
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_info)
        details_layout.addLayout(speed_layout)

        layout.addWidget(details_row)

        # 底部状态栏
        self.bottom_status = BodyLabel('等待开始扫描')
        self.bottom_status.setStyleSheet('font-size: 10px; color: #999;')
        layout.addWidget(self.bottom_status)

    def start_scan(self, scan_type: str = 'system'):
        """开始扫描"""
        self.reset()
        self.scan_status.setText(f'扫描中: {self.get_scan_type_name(scan_type)}')
        self.scan_icon.setIcon(FluentIcon.SYNC)
        self.scan_icon.setStyleSheet('color: #0078D4;')
        self.bottom_status.setText('正在扫描...')

    def update_progress(self, message: str, percent: int = None):
        """更新进度信息"""
        self.bottom_status.setText(message)
        if percent is not None:
            self.progress_bar.setValue(percent)

    def update_counts(self, scanned: int, found: int, risks: dict):
        """更新统计信息"""
        self.scanned_count.setText(str(scanned))
        self.found_count.setText(str(found))

        # 风险分布
        risk_text = f'安全:{risks.get("safe", 0)} 疑似:{risks.get("suspicious", 0)}'
        self.risk_info.setText(risk_text)

    def update_speed(self, speed: str):
        """更新扫描速度"""
        self.speed_info.setText(speed)

    def complete_scan(self, total_found: int):
        """扫描完成"""
        self.progress_bar.setValue(100)
        self.scan_status.setText('扫描完成')
        self.scan_icon.setIcon(FluentIcon.PIN)
        self.scan_icon.setStyleSheet('color: #28a745;')
        self.bottom_status.setText(f'完成，发现 {total_found} 项')

    def cancel_scan(self):
        """取消扫描"""
        self.scan_status.setText('已取消')
        self.scan_icon.setIcon(FluentIcon.CANCEL)
        self.scan_icon.setStyleSheet('color: #dc3545;')
        self.bottom_status.setText('扫描已取消')

    def error_scan(self, error_msg: str):
        """扫描错误"""
        self.scan_status.setText('扫描错误')
        self.scan_icon.setIcon(FluentIcon.ERROR)
        self.scan_icon.setStyleSheet('color: #dc3545;')
        self.bottom_status.setText(f'错误: {error_msg}')

    def reset(self):
        """重置状态"""
        self.progress_bar.setValue(0)
        self.scan_status.setText('准备中...')
        self.scan_icon.setIcon(FluentIcon.SEARCH)
        self.scan_icon.setStyleSheet('color: #666;')
        self.scanned_count.setText('0')
        self.found_count.setText('0')
        self.risk_info.setText('--')
        self.speed_info.setText('--')
        self.bottom_status.setText('等待开始扫描')

    def get_scan_type_name(self, scan_type: str) -> str:
        """获取扫描类型名称"""
        names = {
            'system': '系统文件',
            'browser': '浏览器缓存',
            'appdata': '应用数据',
            'custom': '自定义路径',
        }
        return names.get(scan_type, scan_type)
