"""
确认清理对话框
显示三区间统计（安全/疑似/危险 数量和大小）
可视化进度条和危险项目警告列表
"""
from typing import List
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PyQt5.QtCore import Qt

from qfluentwidgets import StrongBodyLabel, BodyLabel, SimpleCardWidget, PushButton, PrimaryPushButton, ProgressBar
from core.models import ScanItem
from core.scanner import format_size


class ConfirmDialog(QDialog):
    """清理确认对话框

    显示三区间统计和危险项目警告
    """

    def __init__(self, items: List[ScanItem], parent=None):
        super().__init__(parent)
        self.items = items
        self.items_to_clean = items.copy()
        self.setWindowTitle('确认清理')
        self.setFixedSize(500, 450)
        self.init_ui()
        self.calculate_statistics()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = StrongBodyLabel('确认清理')
        title.setStyleSheet('font-size: 18px;')
        layout.addWidget(title)

        layout.addSpacing(15)

        # 统计区域 - 使用卡片样式
        stats_card = SimpleCardWidget()
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(15, 15, 15, 15)
        stats_layout.setSpacing(10)

        # 安全项目
        safe_layout = QVBoxLayout()
        safe_label_layout = QHBoxLayout()
        self.safe_count_label = BodyLabel('安全: 0')
        self.safe_count_label.setStyleSheet('color: #28a745; font-weight: bold; font-size: 12px;')
        self.safe_size_label = BodyLabel('0 B')
        self.safe_size_label.setStyleSheet('color: #666666; font-size: 11px;')
        safe_label_layout.addWidget(self.safe_count_label)
        safe_label_layout.addStretch()
        safe_label_layout.addWidget(self.safe_size_label)
        safe_layout.addLayout(safe_label_layout)
        self.safe_progress = ProgressBar()
        self.safe_progress.setValue(0)
        self.safe_progress.setRange(0, 100)
        self.safe_progress.setFixedHeight(10)
        safe_layout.addWidget(self.safe_progress)
        stats_layout.addLayout(safe_layout)

        stats_layout.addSpacing(10)

        # 疑似项目
        suspicious_layout = QVBoxLayout()
        suspicious_label_layout = QHBoxLayout()
        self.suspicious_count_label = BodyLabel('疑似: 0')
        self.suspicious_count_label.setStyleSheet('color: #ffc107; font-weight: bold; font-size: 12px;')
        self.suspicious_size_label = BodyLabel('0 B')
        self.suspicious_size_label.setStyleSheet('color: #666666; font-size: 11px;')
        suspicious_label_layout.addWidget(self.suspicious_count_label)
        suspicious_label_layout.addStretch()
        suspicious_label_layout.addWidget(self.suspicious_size_label)
        suspicious_layout.addLayout(suspicious_label_layout)
        self.suspicious_progress = ProgressBar()
        self.suspicious_progress.setValue(0)
        self.suspicious_progress.setRange(0, 100)
        self.suspicious_progress.setFixedHeight(10)
        suspicious_layout.addWidget(self.suspicious_progress)
        stats_layout.addLayout(suspicious_layout)

        stats_layout.addSpacing(10)

        # 危险项目
        dangerous_layout = QVBoxLayout()
        dangerous_label_layout = QHBoxLayout()
        self.dangerous_count_label = BodyLabel('危险: 0')
        self.dangerous_count_label.setStyleSheet('color: #dc3545; font-weight: bold; font-size: 12px;')
        self.dangerous_size_label = BodyLabel('0 B')
        self.dangerous_size_label.setStyleSheet('color: #666666; font-size: 11px;')
        dangerous_label_layout.addWidget(self.dangerous_count_label)
        dangerous_label_layout.addStretch()
        dangerous_label_layout.addWidget(self.dangerous_size_label)
        dangerous_layout.addLayout(dangerous_label_layout)
        self.dangerous_progress = ProgressBar()
        self.dangerous_progress.setValue(0)
        self.dangerous_progress.setRange(0, 100)
        self.dangerous_progress.setFixedHeight(10)
        dangerous_layout.addWidget(self.dangerous_progress)
        stats_layout.addLayout(dangerous_layout)

        layout.addWidget(stats_card)

        layout.addSpacing(15)

        # 总计
        total_layout = QHBoxLayout()
        self.total_label = BodyLabel('总计: 0 项目 / 0 B')
        self.total_label.setStyleSheet('font-weight: bold; font-size: 13px;')
        total_layout.addWidget(self.total_label)
        total_layout.addStretch()
        layout.addLayout(total_layout)

        layout.addSpacing(15)

        # 危险项目警告
        warning_label = StrongBodyLabel('⚠️ 危险项目需谨慎:')
        warning_label.setStyleSheet('font-size: 14px; color: #dc3545;')
        layout.addWidget(warning_label)

        # 危险项目列表
        warning_scroll = QScrollArea()
        warning_scroll.setWidgetResizable(True)
        warning_scroll.setFrameShape(QScrollArea.NoFrame)
        warning_scroll.setMaximumHeight(100)

        self.warning_container = QWidget()
        self.warning_layout = QVBoxLayout(self.warning_container)
        self.warning_layout.setSpacing(5)
        self.warning_layout.setContentsMargins(0, 0, 0, 0)

        warning_scroll.setWidget(self.warning_container)
        layout.addWidget(warning_scroll)

        layout.addSpacing(15)

        # 提示信息
        hint_label = BodyLabel('文件将被移动到回收站，可以恢复。')
        hint_label.setStyleSheet('color: #666666; font-size: 11px; font-style: italic;')
        layout.addWidget(hint_label)

        layout.addStretch()

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.confirm_btn = PrimaryPushButton('确认清理')
        self.confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.confirm_btn)

        layout.addLayout(button_layout)

    def calculate_statistics(self):
        """计算统计信息"""
        self.stats = {
            'safe': {'count': 0, 'size': 0, 'items': []},
            'suspicious': {'count': 0, 'size': 0, 'items': []},
            'dangerous': {'count': 0, 'size': 0, 'items': []}
        }

        total_size = 0

        for item in self.items:
            # 获取风险等级（处理枚举对象）
            risk_level = item.risk_level
            if hasattr(risk_level, 'value'):
                risk_level = risk_level.value
            elif isinstance(risk_level, str):
                risk_level = risk_level
            else:
                risk_level = str(risk_level).lower()

            # 确保risk_level是字典中存在的键
            if risk_level not in self.stats:
                risk_level = 'safe'  # 默认为安全

            self.stats[risk_level]['count'] += 1
            self.stats[risk_level]['size'] += item.size
            self.stats[risk_level]['items'].append(item)
            total_size += item.size

        # 更新UI
        self._update_stats_ui(total_size)

    def _update_stats_ui(self, total_size):
        """更新统计UI"""
        total_count = len(self.items)

        # 安全项目
        safe_count = self.stats['safe']['count']
        safe_size = self.stats['safe']['size']
        self.safe_count_label.setText(f'安全: {safe_count}')
        self.safe_size_label.setText(format_size(safe_size))
        safe_percent = int((safe_count / total_count * 100)) if total_count > 0 else 0
        self.safe_progress.setValue(safe_percent)

        # 疑似项目
        suspicious_count = self.stats['suspicious']['count']
        suspicious_size = self.stats['suspicious']['size']
        self.suspicious_count_label.setText(f'疑似: {suspicious_count}')
        self.suspicious_size_label.setText(format_size(suspicious_size))
        suspicious_percent = int((suspicious_count / total_count * 100)) if total_count > 0 else 0
        self.suspicious_progress.setValue(suspicious_percent)

        # 危险项目
        dangerous_count = self.stats['dangerous']['count']
        dangerous_size = self.stats['dangerous']['size']
        self.dangerous_count_label.setText(f'危险: {dangerous_count}')
        self.dangerous_size_label.setText(format_size(dangerous_size))
        dangerous_percent = int((dangerous_count / total_count * 100)) if total_count > 0 else 0
        self.dangerous_progress.setValue(dangerous_percent)

        # 总计
        self.total_label.setText(f'总计: {total_count} 项目 / {format_size(total_size)}')

        # 更新危险项目列表
        self._update_dangerous_items()

    def _update_dangerous_items(self):
        """更新危险项目列表"""
        # 清空现有项目
        for i in reversed(range(self.warning_layout.count())):
            child = self.warning_layout.itemAt(i).widget()
            if child is not None:
                child.deleteLater()

        # 添加危险项目
        dangerous_items = self.stats['dangerous']['items']
        for item in dangerous_items[:10]:  # 最多显示10个
            item_label = BodyLabel(f'• {item.description}')
            item_label.setStyleSheet('color: #dc3545; font-size: 11px;')
            item_label.setWordWrap(True)
            self.warning_layout.addWidget(item_label)

        if len(dangerous_items) > 10:
            more_label = BodyLabel(f'• ... 还有 {len(dangerous_items) - 10} 个危险项目')
            more_label.setStyleSheet('color: #dc3545; font-size: 11px;')
            self.warning_layout.addWidget(more_label)

    def get_items_to_clean(self) -> List[ScanItem]:
        """获取要清理的项目列表

        Returns:
            List[ScanItem]: 要清理的项目列表
        """
        return self.items_to_clean

    def exclude_dangerous(self, exclude: bool = True):
        """
        是否排除危险项目

        Args:
            exclude: 是否排除危险项目
        """
        if exclude:
            self.items_to_clean = [item for item in self.items if item.risk_level != 'dangerous']
        else:
            self.items_to_clean = self.items.copy()

    def get_safe_items(self) -> List[ScanItem]:
        """获取安全项目列表"""
        return self.stats['safe']['items']

    def get_suspicious_items(self) -> List[ScanItem]:
        """获取疑似项目列表"""
        return self.stats['suspicious']['items']

    def get_dangerous_items(self) -> List[ScanItem]:
        """获取危险项目列表"""
        return self.stats['dangerous']['items']

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()
