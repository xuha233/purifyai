# -*- coding: utf-8 -*-
"""
AI 成本控制面板 - 实时显示成本使用情况

提供以下功能：
1. 实时显示成本使用情况
2. 显示调用次数限制
3. 显示预算使用进度
4. 降级状态提示
"""
from typing import Dict, Optional, Callable
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QPushButton, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

from .agent_config import DEFAULT_AGENT_CONFIG


class CostDisplayWidget(QWidget):
    """成本显示面板 - 实时显示当前成本使用情况"""

    # 信号
    limit_reached = pyqtSignal(str)  # 达到限制信号
    alert_triggered = pyqtSignal(str, str)  # 警告信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cost_controller = None
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.setInterval(1000)  # 每秒更新

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("AI 成本使用情况")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(title)

        # 主显示区域
        self._create_main_display(layout)

        # 进度条区域
        self._create_progress_section(layout)

        # 统计信息区域
        self._create_stats_section(layout)

        layout.addStretch()

    def _create_main_display(self, parent_layout: QVBoxLayout):
        """创建主显示区域"""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(frame)

        # 状态标签
        self._status_label = QLabel("状态: 正常")
        self._status_label.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self._status_label)

        # 调用次数和成本
        info_layout = QHBoxLayout()

        # 调用次数
        calls_layout = QVBoxLayout()
        calls_label = QLabel("调用次数")
        calls_label.setStyleSheet("color: #666; font-size: 12px;")
        self._calls_label = QLabel("0 / 100")
        self._calls_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        calls_layout.addWidget(calls_label)
        calls_layout.addWidget(self._calls_label)
        info_layout.addLayout(calls_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: #ccc;")
        info_layout.addWidget(separator)

        # 成本
        cost_layout = QVBoxLayout()
        cost_label = QLabel("已消费")
        cost_label.setStyleSheet("color: #666; font-size: 12px;")
        self._cost_label = QLabel("$0.000")
        self._cost_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        cost_layout.addWidget(cost_label)
        cost_layout.addWidget(self._cost_label)
        info_layout.addLayout(cost_layout)

        # 预算
        budget_layout = QVBoxLayout()
        budget_label = QLabel("预算上限")
        budget_label.setStyleSheet("color: #666; font-size: 12px;")
        self._budget_label = QLabel("$2.00")
        self._budget_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        budget_layout.addWidget(budget_label)
        budget_layout.addWidget(self._budget_label)
        info_layout.addLayout(budget_layout)

        layout.addLayout(info_layout)
        parent_layout.addWidget(frame)

    def _create_progress_section(self, parent_layout: QVBoxLayout):
        """创建进度条区域"""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(frame)

        # 预算进度条标签
        budget_progress_label = QLabel("预算使用进度")
        budget_progress_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(budget_progress_label)

        # 预算进度条
        self._budget_progress = QProgressBar()
        self._budget_progress.setRange(0, 100)
        self._budget_progress.setValue(0)
        self._budget_progress.setTextVisible(True)
        self._budget_progress.setFixedHeight(20)
        self._budget_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 10px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                border-radius: 8px;
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self._budget_progress)

        # 调用次数进度条
        calls_progress_label = QLabel("调用次数进度")
        calls_progress_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(calls_progress_label)

        self._calls_progress = QProgressBar()
        self._calls_progress.setRange(0, 100)
        self._calls_progress.setValue(0)
        self._calls_progress.setTextVisible(True)
        self._calls_progress.setFixedHeight(20)
        self._calls_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 10px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                border-radius: 8px;
                background-color: #2196F3;
            }
        """)
        layout.addWidget(self._calls_progress)

        parent_layout.addWidget(frame)

    def _create_stats_section(self, parent_layout: QVBoxLayout):
        """创建统计信息区域"""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QGridLayout(frame)

        # 今日统计
        today_label = QLabel("今日统计")
        today_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(today_label, 0, 0)

        self._today_calls = QLabel("调用: 0")
        self._today_cost = QLabel("成本: $0.00")
        layout.addWidget(self._today_calls, 0, 1)
        layout.addWidget(self._today_cost, 0, 2)

        # 累计统计
        total_label = QLabel("累计统计")
        total_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(total_label, 1, 0)

        self._total_calls = QLabel("调用: 0")
        self._total_cost = QLabel("成本: $0.00")
        layout.addWidget(self._total_calls, 1, 1)
        layout.addWidget(self._total_cost, 1, 2)

        parent_layout.addWidget(frame)

    def set_cost_controller(self, controller):
        """设置成本控制器

        Args:
            controller: CostController 实例
        """
        from .cost_controller import CostController

        self._cost_controller = controller

        # 设置回调
        if hasattr(controller, 'set_on_limit_reached'):
            controller.set_on_limit_reached(self._on_limit_reached)

        if hasattr(controller, 'set_on_alert'):
            controller.set_on_alert(self._on_alert)

        if hasattr(controller, 'set_on_stats_update'):
            controller.set_on_stats_update(self._on_stats_update)

        # 启动更新定时器
        self._update_timer.start()

    def _on_limit_reached(self, reason: str):
        """达到限制回调"""
        self.limit_reached.emit(reason)
        self._update_display()

    def _on_alert(self, level, message):
        """预算警告回调"""
        from .cost_controller import BudgetAlertLevel
        self.alert_triggered.emit(level.value, message)
        self._update_display()

    def _on_stats_update(self, stats):
        """统计更新回调"""
        self._update_display()

    def _update_display(self):
        """更新显示"""
        if not self._cost_controller:
            return

        try:
            report = self._cost_controller.get_usage_report()
            scan = report["current_scan"]
            today = report.get("today", {})
            all_time = report.get("all_time", {})

            # 更新状态
            if report.get("is_degraded", False):
                status = f"[已降级] {report.get('degradation_reason', '')}"
                self._status_label.setText(f"状态: {status}")
                self._status_label.setStyleSheet("color: #ff4d4f; font-weight: bold;")
            else:
                alert_level = report.get("alert_level", "normal")
                if alert_level == "warning":
                    status = "警告: 预算使用超过 80%"
                    self._status_label.setText(f"状态: {status}")
                    self._status_label.setStyleSheet("color: #faad14; font-weight: bold;")
                elif alert_level == "critical":
                    status = "严重: 预算使用超过 90%"
                    self._status_label.setText(f"状态: {status}")
                    self._status_label.setStyleSheet("color: #ff4d4f; font-weight: bold;")
                elif alert_level == "exceeded":
                    status = "已超出预算限制!"
                    self._status_label.setText(f"状态: {status}")
                    self._status_label.setStyleSheet("color: #ff4d4f; font-weight: bold;")
                else:
                    status = "正常"
                    self._status_label.setText(f"状态: {status}")
                    self._status_label.setStyleSheet("color: #52c41a; font-weight: bold;")

            # 更新调用次数
            calls = scan.get('calls', 0)
            max_calls = scan.get('max_calls', 100)
            self._calls_label.setText(f"{calls} / {max_calls}")

            # 更新成本
            cost = scan.get('cost', 0.0)
            max_budget = scan.get('max_budget', 2.0)
            self._cost_label.setText(f"${cost:.3f}")
            self._budget_label.setText(f"${max_budget:.2f}")

            # 更新进度条
            call_usage = scan.get('call_usage_percent', 0)
            budget_usage = scan.get('budget_usage_percent', 0)

            self._calls_progress.setValue(int(call_usage))
            self._budget_progress.setValue(int(budget_usage))

            # 更新进度条颜色
            self._update_progress_colors(budget_usage)

            # 今日统计
            self._today_calls.setText(f"调用: {today.get('calls', 0)}")
            self._today_cost.setText(f"成本: ${today.get('cost', 0.0):.2f}")

            # 累计统计
            self._total_calls.setText(f"调用: {all_time.get('calls', 0)}")
            self._total_cost.setText(f"成本: ${all_time.get('cost', 0.0):.2f}")

        except Exception as e:
            print(f"[CostDisplayWidget] 更新显示失败: {e}")

    def _update_progress_colors(self, usage_percent: float):
        """根据使用率更新进度条颜色"""
        if usage_percent >= 100:
            color = "#ff4d4f"  # 红色
        elif usage_percent >= 80:
            color = "#faad14"  # 黄色
        else:
            color = "#52c41a"  # 绿色

        style = f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 10px;
                text-align: center;
                background-color: white;
            }}
            QProgressBar::chunk {{
                border-radius: 8px;
                background-color: {color};
            }}
        """
        self._budget_progress.setStyleSheet(style)

    def get_summary(self) -> Dict:
        """获取摘要信息

        Returns:
            摘要字典
        """
        if not self._cost_controller:
            return {}

        report = self._cost_controller.get_usage_report()
        return {
            "calls": report["current_scan"].get("calls", 0),
            "max_calls": report["current_scan"].get("max_calls", 100),
            "cost": report["current_scan"].get("cost", 0.0),
            "max_budget": report["current_scan"].get("max_budget", 2.0),
            "budget_usage_percent": report["current_scan"].get("budget_usage_percent", 0),
            "is_degraded": report.get("is_degraded", False),
            "status": self._status_label.text()
        }

    def stop_updates(self):
        """停止更新"""
        self._update_timer.stop()

    def start_updates(self):
        """开始更新"""
        self._update_timer.start()


class CostControlPanel(QWidget):
    """成本控制面板 - 完整配置和显示"""

    # 信号
    config_changed = pyqtSignal(dict)  # 配置变更信号
    limit_reached = pyqtSignal(str)    # 达到限制信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cost_controller = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 成本显示
        self._display = CostDisplayWidget()
        self._display.limit_reached.connect(self._on_limit_reached)
        layout.addWidget(self._display)

        # 配置区域
        self._create_config_section(layout)

        # 按钮区域
        self._create_button_section(layout)

    def _create_config_section(self, parent_layout: QVBoxLayout):
        """创建配置区域"""
        group = QGroupBox("成本控制设置")
        group.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout = QGridLayout(group)

        # 模式选择
        layout.addWidget(QLabel("控制模式:"), 0, 0)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            ("unlimited", "无限制模式"),
            ("budget", "预算模式"),
            ("fallback", "回退模式"),
            ("rules_only", "仅规则模式")
        ])
        self._mode_combo.setCurrentText("fallback")
        self._mode_combo.currentTextChanged.connect(self._on_config_changed)
        layout.addWidget(self._mode_combo, 0, 1, 1, 2)

        # 单次扫描最大调用次数
        layout.addWidget(QLabel("单次扫描最大调用次数:"), 1, 0)
        self._max_calls_spin = QSpinBox()
        self._max_calls_spin.setRange(1, 10000)
        self._max_calls_spin.setValue(100)
        self._max_calls_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self._max_calls_spin, 1, 1)

        # 单次扫描最大预算
        layout.addWidget(QLabel("单次扫描最大预算 ($):"), 2, 0)
        self._max_budget_spin = QDoubleSpinBox()
        self._max_budget_spin.setRange(0.01, 1000.0)
        self._max_budget_spin.setValue(2.0)
        self._max_budget_spin.setDecimals(2)
        self._max_budget_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self._max_budget_spin, 2, 1)

        # 每日最大预算
        layout.addWidget(QLabel("每日最大预算 ($):"), 3, 0)
        self._max_daily_budget_spin = QDoubleSpinBox()
        self._max_daily_budget_spin.setRange(0.01, 5000.0)
        self._max_daily_budget_spin.setValue(10.0)
        self._max_daily_budget_spin.setDecimals(2)
        self._max_daily_budget_spin.valueChanged.connect(self._on_config_changed)
        layout.addWidget(self._max_daily_budget_spin, 3, 1)

        # 降级到规则引擎
        self._fallback_check = QCheckBox("超限时降级到规则引擎")
        self._fallback_check.setChecked(True)
        self._fallback_check.stateChanged.connect(self._on_config_changed)
        layout.addWidget(self._fallback_check, 4, 0, 1, 3)

        parent_layout.addWidget(group)

    def _create_button_section(self, parent_layout: QVBoxLayout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()

        # 重置统计按钮
        self._reset_button = QPushButton("重置统计")
        self._reset_button.clicked.connect(self._reset_stats)
        button_layout.addWidget(self._reset_button)

        # 刷新按钮
        self._refresh_button = QPushButton("刷新")
        self._refresh_button.clicked.connect(self._refresh)
        button_layout.addWidget(self._refresh_button)

        parent_layout.addLayout(button_layout)

    def set_cost_controller(self, controller):
        """设置成本控制器

        Args:
            controller: CostController 实例
        """
        self._cost_controller = controller
        self._display.set_cost_controller(controller)

        # 同步配置到 UI
        if controller:
            config = controller.config
            self._mode_combo.setCurrentText(config.mode.value if hasattr(config.mode, 'value') else str(config.mode))
            self._max_calls_spin.setValue(config.max_calls_per_scan)
            self._max_budget_spin.setValue(config.max_budget_per_scan)
            self._max_daily_budget_spin.setValue(config.max_budget_per_day)
            self._fallback_check.setChecked(config.fallback_to_rules)

    def _on_config_changed(self):
        """配置变更处理"""
        from .cost_controller import CostConfig, CostControlMode as CCCMode

        if not self._cost_controller:
            return

        config = CostConfig(
            mode=CCMode(self._mode_combo.currentData() or self._mode_combo.currentText()),
            max_calls_per_scan=self._max_calls_spin.value(),
            max_budget_per_scan=self._max_budget_spin.value(),
            max_budget_per_day=self._max_daily_budget_spin.value(),
            fallback_to_rules=self._fallback_check.isChecked()
        )

        self._cost_controller.update_config(config)

        # 发送配置变更信号
        self.config_changed.emit(config.to_dict())

    def _on_limit_reached(self, reason: str):
        """达到限制处理"""
        self.limit_reached.emit(reason)

    def _reset_stats(self):
        """重置统计"""
        if self._cost_controller:
            self._cost_controller.reset_scan_stats()
            self._display._update_display()

    def _refresh(self):
        """刷新显示"""
        self._display._update_display()

    def get_config(self) -> dict:
        """获取当前配置"""
        return {
            "mode": self._mode_combo.currentText(),
            "max_calls_per_scan": self._max_calls_spin.value(),
            "max_budget_per_scan": self._max_budget_spin.value(),
            "max_budget_per_day": self._max_daily_budget_spin.value(),
            "fallback_to_rules": self._fallback_check.isChecked()
        }

    def get_summary(self) -> Dict:
        """获取摘要信息"""
        return self._display.get_summary()


# 导出
__all__ = [
    'CostDisplayWidget',
    'CostControlPanel'
]
