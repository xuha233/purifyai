"""
扫描状态指示器 - 小巧直观的工作状态显示
"""
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QProgressBar
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QFont
from qfluentwidgets import BodyLabel, IconWidget, FluentIcon, StrongBodyLabel


class ScanStatusWidget(QWidget):
    """扫描状态指示器 - 小巧紧凑的实时状态显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._is_animating = False
        self._animation_step = 0

    def setup_ui(self):
        self.setFixedHeight(48)
        self.setStyleSheet('''
            ScanStatusWidget {
                background: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            ScanStatusWidget[scanning="true"] {
                background: #0078D408;
                border: 1px solid #0078D430;
            }
            ScanStatusWidget[error="true"] {
                background: #dc354508;
                border: 1px solid #dc354530;
            }
            ScanStatusWidget[success="true"] {
                background: #28a74508;
                border: 1px solid #28a74530;
            }
        ''')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)

        # 状态图标和指示灯
        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(6)

        self.status_icon = IconWidget(FluentIcon.CHECKBOX)
        self.status_icon.setFixedSize(20, 20)
        self.status_icon.setStyleSheet('color: #888;')
        icon_layout.addWidget(self.status_icon)

        # 活动指示灯（小绿点）
        self.indicator = QLabel()
        self.indicator.setFixedSize(8, 8)
        self.indicator.setStyleSheet('''
            QLabel {
                background: #cccccc;
                border-radius: 4px;
            }
        ''')
        icon_layout.addWidget(self.indicator)

        layout.addLayout(icon_layout)

        # 状态信息 + 进度条
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # 第一行：状态文本和进度条
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.status_text = BodyLabel('就绪')
        self.status_text.setStyleSheet('font-size: 12px; color: #2c2c2c; font-weight: 500;')
        row1.addWidget(self.status_text)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet('''
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                background: #f0f0f0;
            }
            QProgressBar::chunk {
                background: #0078D4;
                border-radius: 2px;
            }
        ''')
        self.progress_bar.setVisible(False)
        row1.addWidget(self.progress_bar)

        row1.addStretch()
        info_layout.addLayout(row1)

        # 第二行：详细信息
        self.detail_text = BodyLabel('等待扫描')
        self.detail_text.setStyleSheet('font-size: 10px; color: #888;')
        info_layout.addWidget(self.detail_text)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 右侧统计
        self.stats_label = StrongBodyLabel('--')
        self.stats_label.setStyleSheet('font-size: 13px; color: #0078D4;')
        layout.addWidget(self.stats_label)

        # 动画计时器
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.start(500)

    def _update_pulse(self):
        """更新指示灯脉冲效果"""
        if not self._is_animating:
            return

        self._animation_step = (self._animation_step + 1) % 4

        # 创建脉冲效果
        opacity = 0.5 + 0.5 * (self._animation_step % 2)
        color = f'rgba(0, 120, 212, {opacity})'
        self.indicator.setStyleSheet(f'''
            QLabel {{
                background: {color};
                border-radius: 4px;
            }}
        ''')

    def idle(self, message=''):
        """空闲状态"""
        self._is_animating = False
        self.setProperty('scanning', 'false')
        self.setProperty('error', 'false')
        self.setProperty('success', 'false')
        self.style().unpolish(self)
        self.style().polish(self)

        self.status_icon.setIcon(FluentIcon.CHECKBOX)
        self.status_icon.setStyleSheet('color: #888;')
        self.status_text.setText('就绪')
        self.detail_text.setText(message or '等待扫描')
        self.progress_bar.setVisible(False)
        self.indicator.setStyleSheet('''
            QLabel {
                background: #cccccc;
                border-radius: 4px;
            }
        ''')
        self.stats_label.setText('--')

    def scanning(self, message='', scanned=0, found=0, progress=0):
        """扫描中状态"""
        self._is_animating = True
        self.setProperty('scanning', 'true')
        self.setProperty('error', 'false')
        self.setProperty('success', 'false')
        self.style().unpolish(self)
        self.style().polish(self)

        self.status_icon.setIcon(FluentIcon.SEARCH)
        self.status_icon.setStyleSheet('color: #0078D4;')
        self.status_text.setText('扫描中')
        self.detail_text.setText(message or '正在扫描...')
        self.progress_bar.setVisible(True)
        if progress > 0:
            self.progress_bar.setValue(int(progress))
        else:
            self.progress_bar.setRange(0, 0)  # 不确定进度
        self.stats_label.setText(f'{found} 项 / {scanned} 扫描')

    def complete(self, total_found, message=''):
        """完成状态"""
        self._is_animating = False
        self.setProperty('scanning', 'false')
        self.setProperty('error', 'false')
        self.setProperty('success', 'true')
        self.style().unpolish(self)
        self.style().polish(self)

        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(100)
        self.status_icon.setIcon(FluentIcon.PIN)
        self.status_icon.setStyleSheet('color: #28a745;')
        self.status_text.setText('扫描完成')
        self.detail_text.setText(message or f'发现 {total_found} 项')
        self.indicator.setStyleSheet('''
            QLabel {
                background: #28a745;
                border-radius: 4px;
            }
        ''')
        self.stats_label.setText(f'{total_found} 项')

    def error(self, message=''):
        """错误状态"""
        self._is_animating = False
        self.setProperty('scanning', 'false')
        self.setProperty('error', 'true')
        self.setProperty('success', 'false')
        self.style().unpolish(self)
        self.style().polish(self)

        self.progress_bar.setVisible(False)
        self.status_icon.setIcon(FluentIcon.CANCEL)
        self.status_icon.setStyleSheet('color: #dc3545;')
        self.status_text.setText('出错')
        self.detail_text.setText(message or '扫描过程中出现错误')
        self.indicator.setStyleSheet('''
            QLabel {
                background: #dc3545;
                border-radius: 4px;
            }
        ''')
        self.stats_label.setText('错误')

    def cancelled(self, message=''):
        """取消状态"""
        self._is_animating = False
        self.setProperty('scanning', 'false')
        self.setProperty('error', 'false')
        self.setProperty('success', 'false')
        self.style().unpolish(self)
        self.style().polish(self)

        self.progress_bar.setVisible(False)
        self.status_icon.setIcon(FluentIcon.CANCEL)
        self.status_icon.setStyleSheet('color: #dc3545;')
        self.status_text.setText('已取消')
        self.detail_text.setText(message or '扫描已取消')
        self.indicator.setStyleSheet('''
            QLabel {
                background: #dc3545;
                border-radius: 4px;
            }
        ''')
        self.stats_label.setText('--')
