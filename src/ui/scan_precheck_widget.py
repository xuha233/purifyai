# -*- coding: utf-8 -*-
"""
扫描预检查组件 UI (Scan Pre-Check Widget)

Feature 4: Pre-Check UI Integration

功能:
- 显示扫描前预检查结果
- 展示权限、磁盘空间、路径安全性检查
- 显示问题和警告
- 提供修复建议
"""
from typing import List, Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel, SimpleCardWidget,
    CardWidget, InfoBar, InfoBarPosition, FluentIcon, IconWidget,
    PrimaryPushButton, PushButton
)

from utils.scan_prechecker import ScanPreChecker, get_pre_checker
from core.models_smart import CheckResult
from utils.logger import get_logger

logger = get_logger(__name__)


# 颜色主题
class ThemeColors:
    PRIMARY = "#0078D4"
    SUCCESS = "#28a745"
    WARNING = "#ff9800"
    DANGER = "#dc3545"
    ERROR = "#d32f2f"
    BACKGROUND = "#f8f9fa"
    CARD_BG = "#ffffff"
    TEXT_PRIMARY = "#2c2c2c"
    TEXT_SECONDARY = "#666666"


class CheckItemWidget(QFrame):
    """检查项组件"""

    def __init__(self, icon: FluentIcon, message: str, is_issue: bool = False,
                 is_warning: bool = False, suggestion: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        # 根据类型设置颜色
        if is_issue:
            color = ThemeColors.DANGER
        elif is_warning:
            color = ThemeColors.WARNING
        else:
            color = ThemeColors.SUCCESS

        # 图标
        icon_widget = IconWidget(icon)
        icon_widget.setFixedSize(24, 24)
        icon_widget.setStyleSheet(f"color: {color};")
        layout.addWidget(icon_widget)

        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        msg_label = BodyLabel(message)
        msg_label.setStyleSheet(f"color: {ThemeColors.TEXT_PRIMARY};")
        content_layout.addWidget(msg_label)

        if suggestion:
            suggest_label = BodyLabel(f"💡 {suggestion}")
            suggest_label.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-size: 11px;")
            content_layout.addWidget(suggest_label)

        layout.addLayout(content_layout)
        layout.addStretch()


class ScanPreCheckWidget(SimpleCardWidget):
    """扫描预检查组件

    在扫描前显示预检查结果，确保系统状态安全
    """

    # 信号
    check_completed = pyqtSignal(bool)  # 是否可以继续扫描

    def __init__(self, parent=None):
        super().__init__(parent)

        self.checker = get_pre_checker()
        self.current_result: Optional[CheckResult] = None
        self.checking = False
        self.logger = logger

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题栏
        header_layout = QHBoxLayout()

        # 图标
        title_icon = IconWidget(FluentIcon.CHECKBOX)
        title_icon.setFixedSize(24, 24)
        title_icon.setStyleSheet('color: #0078D4;')
        header_layout.addWidget(title_icon)

        title = StrongBodyLabel("扫描前检查")
        title.setStyleSheet('font-size: 14px;')
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 状态标签
        self.status_label = BodyLabel("待检查")
        self.status_label.setStyleSheet('color: #666; font-size: 12px;')
        header_layout.addWidget(self.status_label)

        # 刷新按钮
        self.refresh_btn = PushButton(FluentIcon.SYNC, "")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setToolTip("重新检查")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # 检查结果列表
        self.checks_scroll = QScrollArea()
        self.checks_scroll.setWidgetResizable(True)
        self.checks_scroll.setWidgetResizable(False)
        self.checks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.checks_scroll.setMaximumHeight(200)
        self.checks_scroll.setStyleSheet('''
            QScrollArea {
                border: none;
                background: transparent;
            }
        ''')

        self.checks_container = QWidget()
        self.checks_layout = QVBoxLayout(self.checks_container)
        self.checks_layout.setSpacing(0)
        self.checks_layout.setContentsMargins(0, 0, 0, 0)
        self.checks_layout.addStretch()

        self.checks_scroll.setWidget(self.checks_container)
        layout.addWidget(self.checks_scroll)

        # 初始消息
        self._show_checking_state(False)

    def _show_checking_state(self, checking: bool, message: str = ""):
        """显示检查状态

        Args:
            checking: 是否正在检查
            message: 额外消息
        """
        if checking:
            self.status_label.setText("检查中...")
            self.status_label.setStyleSheet('color: #0078D4; font-size: 12px;')
            self._clear_check_items()
            self._add_check_item(FluentIcon.SYNC, "正在检查系统状态...", False, False, "")
        else:
            self.status_label.setText(message or "待检查")
            self.status_label.setStyleSheet(f'color: {"#28a745" if message == "通过" else "#666"}; font-size: 12px;')

    def _clear_check_items(self):
        """清空检查项"""
        # 移除所有子组件，除了最后的 stretch
        while self.checks_layout.count() > 1:
            item = self.checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_check_item(
        self,
        icon: FluentIcon,
        message: str,
        is_issue: bool = False,
        is_warning: bool = False,
        suggestion: str = ""
    ):
        """添加检查项

        Args:
            icon: 图标
            message: 消息
            is_issue: 是否是问题
            is_warning: 是否是警告
            suggestion: 建议信息
        """
        # 插入在 stretch 之前
        item_widget = CheckItemWidget(icon, message, is_issue, is_warning, suggestion)
        if self.checks_layout.count() > 0:
            # 移除 stretch
            stretch = self.checks_layout.takeAt(self.checks_layout.count() - 1)
        self.checks_layout.insertWidget(self.checks_layout.count(), item_widget)
        # 重新添加 stretch
        self.checks_layout.addStretch()

    def run_precheck(self, scan_paths: List[str], required_space_mb: int = 100) -> CheckResult:
        """运行预检查

        Args:
            scan_paths: 扫描路径列表
            required_space_mb: 所需磁盘空间（MB）

        Returns:
            检查结果
        """
        self.checking = True
        self._show_checking_state(True)

        try:
            # 执行完整预检查
            # self.logger.info(f"[PRECHECK_UI] 开始预检查: {len(scan_paths)} 个路径")
            result = self.checker.full_precheck(scan_paths, required_space_mb)

            self.current_result = result
            self._display_result(result)

            # 发出信号
            self.check_completed.emit(result.can_scan)

            # self.logger.info(f"[PRECHECK_UI] 预检查完成: can_scan={result.can_scan}")

            return result

        except Exception as e:
            # self.logger.error(f"[PRECHECK_UI] 预检查异常: {e}")
            result = CheckResult()
            result.add_issue(f"预检查失败: {str(e)}")
            self._display_result(result)
            return result
        finally:
            self.checking = False

    def _display_result(self, result: CheckResult):
        """显示检查结果

        Args:
            result: 检查结果
        """
        if result.can_scan:
            self._show_checking_state(False, "通过")
            self._add_check_item(
                FluentIcon.ACCEPT,
                "所有检查通过，可以开始扫描",
                False, False, ""
            )

            # 显示警告（如果有）
            for warning in result.warnings[:3]:  # 最多显示3个
                self._add_check_item(
                    FluentIcon.INFO,
                    warning,
                    False, True, "扫描时请注意"
                )
        else:
            self._show_checking_state(False, "未通过")
            self._add_check_item(
                FluentIcon.CANCEL,
                f"预检查未通过，发现 {len(result.issues)} 个问题",
                True, False, "请修复问题后再扫描"
            )

        # 显示问题
        for issue in result.issues:
            suggestion = self._get_suggestion_for_issue(issue)
            self._add_check_item(
                FluentIcon.ERROR,
                issue,
                True, False, suggestion
            )

        # 显示警告
        for warning in result.warnings:
            self._add_check_item(
                FluentIcon.WARNING,
                warning,
                False, True, "扫描时请注意"
            )

    def _get_suggestion_for_issue(self, issue: str) -> str:
        """根据问题获取建议

        Args:
            issue: 问题描述

        Returns:
            建议信息
        """
        issue_lower = issue.lower()

        if "权限" in issue_lower or "permission" in issue_lower:
            return "尝试以管理员身份运行程序"
        elif "磁盘" in issue_lower or "space" in issue_lower:
            return "清理磁盘空间后重试"
        elif "不存在" in issue_lower or "not found" in issue_lower:
            return "请检查路径是否正确"
        elif "不是目录" in issue_lower or "not a directory" in issue_lower:
            return "请选择一个有效的目录"
        else:
            return "请查看详细信息"

    def _on_refresh_clicked(self):
        """刷新按钮点击"""
        # 这个方法需要父组件调用 run_precheck
        # 只是发出一个信号通知父组件
        pass

    def set_result(self, result: CheckResult):
        """直接设置结果（不运行检查）

        Args:
            result: 检查结果
        """
        self.current_result = result
        self._display_result(result)


class PreCheckDialog(QWidget):
    """预检查对话框

    显示完整的预检查结果并提供操作选项
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.check_result: Optional[CheckResult] = None
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title_layout = QHBoxLayout()
        title = SubtitleLabel("扫描前预检查")
        title.setStyleSheet('font-size: 18px;')
        title_layout.addWidget(title)
        layout.addLayout(title_layout)

        # 说明
        desc = BodyLabel(
            "在开始扫描前，我们会对系统进行检查以确保操作安全。"
            "如果发现问题，请修复后再开始扫描。"
        )
        desc.setStyleSheet('color: #666; font-size: 13px;')
        layout.addWidget(desc)

        # 检查结果组件
        self.precheck_widget = ScanPreCheckWidget()
        layout.addWidget(self.precheck_widget)

        # 操作按钮
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        self.continue_btn = PrimaryPushButton(FluentIcon.RIGHT_ARROW, "继续扫描")
        self.continue_btn.clicked.connect(self._on_continue_clicked)
        actions_layout.addWidget(self.continue_btn)

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        actions_layout.addWidget(self.cancel_btn)

        layout.addLayout(actions_layout)

    def run_checks(self, scan_paths: List[str], required_space_mb: int = 100) -> bool:
        """运行预检查

        Args:
            scan_paths: 扫描路径列表
            required_space_mb: 所需磁盘空间（MB）

        Returns:
            用户是否选择继续
        """
        self.check_result = self.precheck_widget.run_precheck(scan_paths, required_space_mb)

        # 更新按钮状态
        if self.check_result.can_scan:
            self.continue_btn.setText("继续扫描")
            self.continue_btn.setEnabled(True)
        else:
            self.continue_btn.setText("无法继续（请修复问题）")
            self.continue_btn.setEnabled(False)

        return self.check_result.can_scan

    def _on_continue_clicked(self):
        """继续按钮点击"""
        pass  # 由父组件处理

    def _on_cancel_clicked(self):
        """取消按钮点击"""
        pass  # 由父组件处理


# 便利函数
def get_pre_check_widget() -> ScanPreCheckWidget:
    """获取预检查组件实例"""
    return ScanPreCheckWidget()


def get_pre_check_dialog() -> PreCheckDialog:
    """获取预检查对话框实例"""
    return PreCheckDialog()
