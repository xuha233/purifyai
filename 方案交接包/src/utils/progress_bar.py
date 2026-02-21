"""
进度条动画增强组件
提供平滑的进度条动画和实时速度显示
"""
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from qfluentwidgets import BodyLabel, ProgressBar
import time


class AnimatedProgressBar(QWidget):
    """带动画和实时速度显示的进度条"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 进度数据
        self.current_value = 0  # 当前进度 (0-100)
        self.target_value = 0    # 目标进度 (0-100)
        self.total_items = 0    # 总项目数
        self.processed_items = 0  # 已处理项目数
        self.start_time = None  # 开始时间

        # 速度统计
        self.speed_window = []  # 速度统计窗口

        # 动画定时器
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_progress)
        self.animation_interval = 30  # 动画刷新间隔 (ms)

        # 速度更新定时器
        self.speed_timer = QTimer(self)
        self.speed_timer.timeout.connect(self.update_speed)
        self.speed_interval = 500  # 速度更新间隔 (ms)

        # 当前速度
        self.current_speed = 0  # 项目/秒

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)

        # 设置平滑进度条样式
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #E5E5EB;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078D4, stop:1 #5CB3FF
                );
                border-radius: 4px;
            }
            """)
        layout.addWidget(self.progress_bar)

        # 状态信息行
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)

        self.status_label = BodyLabel('准备就绪')
        self.status_label.setStyleSheet('color: #666; font-size: 11px;')
        info_layout.addWidget(self.status_label)

        self.speed_label = BodyLabel('')
        self.speed_label.setStyleSheet('color: #666; font-size: 11px;')
        info_layout.addWidget(self.speed_label)

        self.count_label = BodyLabel('')
        self.count_label.setStyleSheet('color: #666; font-size: 11px;')
        info_layout.addWidget(self.count_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

    def start_progress(self, total_items: int = 0):
        """开始进度跟踪

        Args:
            total_items: 预计总项目数，如果为 0 则使用不确定进度
        """
        self.current_value = 0
        self.target_value = 0
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = time.time()
        self.speed_window.clear()
        self.current_speed = 0

        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100 if total_items > 0 else 0)

        self.status_label.setText('正在处理...')
        self.update_count_label()

        # 启动定时器
        if total_items > 0:
            self.animation_timer.start(self.animation_interval)
        self.speed_timer.start(self.speed_interval)

    def update_progress(self, current: int, total: int = None, message: str = None):
        """更新进度

        Args:
            current: 当前进度值或已处理项目数
            total: 总数（可选，用于动态调整）
            message: 状态消息
        """
        if total is not None:
            self.total_items = total

        if self.total_items > 0:
            # 使用项目数计算进度
            self.target_value = min(100, int((current / self.total_items) * 100))
            self.processed_items = current
        else:
            # 使用直接进度值
            self.target_value = min(100, current)

        if message:
            self.status_label.setText(message)

        self.update_count_label()

        # 如果动画定时器未启动，立即更新
        if not self.animation_timer.isActive():
            self.progress_bar.setValue(self.target_value)

        # 添加到速度窗口
        self.speed_window.append(time.time())

    def increment_progress(self, amount: int = 1, message: str = None):
        """增量更新进度

        Args:
            amount: 增加的项目数量
            message: 状态消息
        """
        self.processed_items += amount

        if self.total_items > 0:
            self.target_value = min(100, int((self.processed_items / self.total_items) * 100))
        else:
            # 不确定进度模式下，每增加10个项目更新10%
            if self.processed_items % 10 == 0:
                self.target_value = min(100, self.progress_bar.value() + 10)
                if self.target_value == 100:
                    self.target_value = 0

        if message:
            self.status_label.setText(message)

        self.update_count_label()
        self.speed_window.append(time.time())

    def animate_progress(self):
        """执行进度条动画"""
        if abs(self.target_value - self.current_value) < 1:
            self.current_value = self.target_value
            self.progress_bar.setValue(int(self.current_value))
            return

        # 平滑过渡（使用线性插值）
        step = (self.target_value - self.current_value) * 0.3
        self.current_value += step
        self.progress_bar.setValue(int(self.current_value))

    def update_speed(self):
        """更新速度显示"""
        if not self.start_time or not self.speed_window:
            return

        # 计算最近的速度（项目/秒）
        recent_time = time.time()
        cutoff_time = recent_time - 2.0  # 最近2秒
        recent_items = [t for t in self.speed_window if t > cutoff_time]

        if recent_items:
            self.current_speed = len(recent_items) / 2.0
        else:
            self.current_speed = 0

        self._update_speed_label()

    def _update_speed_label(self):
        """更新速度标签"""
        if self.current_speed > 0:
            self.speed_label.setText(f'速度: {self.current_speed:.1f} 项/秒')
        elif self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.speed_label.setText(f'平均: {self.processed_items / max(1, elapsed):.1f} 项/秒')
        else:
            self.speed_label.setText('')

    def update_count_label(self):
        """更新计数标签"""
        if self.total_items > 0:
            self.count_label.setText(f'{self.processed_items} / {self.total_items}')
        elif self.processed_items > 0:
            self.count_label.setText(f'已处理: {self.processed_items}')
        else:
            self.count_label.setText('')

    def finish_progress(self, message: str = '完成'):
        """完成进度

        Args:
            message: 完成消息
        """
        self.target_value = 100
        self.current_value = 100
        self.progress_bar.setValue(100)
        self.status_label.setText(message)
        self._update_speed_label()

        # 停止定时器
        self.animation_timer.stop()
        self.speed_timer.stop()

        # 计算总耗时
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.speed_label.setText(f'耗时: {elapsed:.1f}秒 平均: {self.processed_items / max(1, elapsed):.1f} 项/秒')
