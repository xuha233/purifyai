"""开发者控制台页面 - 实时显示日志、诊断信息和错误上报（专注版）"""

import json
import logging
import os
import sys
import io
import traceback
import re
from datetime import datetime
from typing import List, Optional, Dict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QComboBox, QPushButton, QFileDialog, QFrame, QCheckBox,
    QLineEdit, QTabWidget, QGroupBox, QTableWidget, QTableWidgetItem,
    QHBoxLayout as QtHBoxLayout, QSplitter, QAbstractItemView, QApplication,
    QProgressDialog, QInputDialog, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer, pyqtSlot, QMimeData, QMutex, QMutexLocker
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont, QSyntaxHighlighter
from PyQt5.QtWidgets import QMessageBox
from qfluentwidgets import (
    CardWidget, StrongBodyLabel, BodyLabel, PushButton,
    SimpleCardWidget, RoundMenu, Action, InfoBar, InfoBarPosition, FluentIcon,
    SearchLineEdit, ProgressRing, PrimaryPushButton
)

from utils.logger import ConsoleLogHandler
from utils.debug_monitor import get_debug_monitor, ErrorContext
from utils.realtime_logger import RealTimeLogger, RealTimeRedirector, install_realtime_excepthook
from .developer_console_window import DeveloperConsoleWindow


# 日志级别颜色配置
LOG_COLORS = {
    'DEBUG': '#808080',      # 灰色
    'INFO': '#0078D4',       # 蓝色
    'WARNING': '#FFA500',    # 琥色
    'ERROR': '#DC3545',      # 红色
    'CRITICAL': '#8B0000',    # 深红
    'STDOUT': '#4EC9B0',     # 标准输出（绿色）
    'STDERR': '#F48771',     # 标准错误（橙色）
    'EXCEPTION': '#FF4757',   # 异常（红色）
}

# 日志级别列表
LOG_LEVELS = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# 最大日志行数
MAX_LOG_LINES = 10000
MAX_DISPLAY_LINES = 5000


class LogSyntaxHighlighter(QSyntaxHighlighter):
    """简单的日志语法高亮"""

    def highlightBlock(self, text: str):
        """高亮显示日志文本块"""
        if not text:
            return

        # 时间戳格式匹配：HH:MM:SS.mmm
        time_pattern = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3}')
        time_format = QTextCharFormat()
        time_format.setForeground(QColor('#888888'))
        time_format.setFontWeight(QFont.Bold)

        # 日志级别匹配：[LEVEL]
        level_pattern = re.compile(r'\[(DEBUG|INFO|WARNING|ERROR|CRITICAL|STDOUT|STDERR|EXCEPTION)\]')
        level_format = QTextCharFormat()
        level_format.setFontWeight(QFont.Bold)

        # 高亮时间戳
        for match in time_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), time_format)

        # 高亮日志级别
        for match in level_pattern.finditer(text):
            level_name = match.group(1)
            level_format.setForeground(QColor(LOG_COLORS.get(level_name, '#d4d4d4')))
            self.setFormat(match.start(), match.end() - match.start(), level_format)


class StdoutRedirector(QObject):
    """重定向 stdout 到开发者控制台（线程安全版本）"""
    output_received = pyqtSignal(str)  # 输出信号

    def __init__(self, original_stdout):
        super().__init__()
        self.original_stdout = original_stdout
        self._buffer = ""
        self._mutex = QMutex()  # 线程安全锁

    def write(self, text):
        try:
            if text.strip() or self._buffer:
                with QMutexLocker(self._mutex):
                    self._buffer += text
                    while '\n' in self._buffer:
                        line, self._buffer = self._buffer.split('\n', 1)
                        if line:
                            self.output_received.emit(line)
            try:
                if self.original_stdout and hasattr(self.original_stdout, 'write'):
                    self.original_stdout.write(text)
            except:
                pass
        except Exception:
            pass  # 捕获所有异常，避免中断

    def flush(self):
        if self._buffer:
            self.output_received.emit(self._buffer)
            self._buffer = ""
        try:
            if self.original_stdout and hasattr(self.original_stdout, 'flush'):
                self.original_stdout.flush()
        except:
            pass


class StderrRedirector(QObject):
    """重定向 stderr 到开发者控制台（线程安全版本）"""
    output_received = pyqtSignal(str)  # 输出信号

    def __init__(self, original_stderr):
        super().__init__()
        self.original_stderr = original_stderr
        self._buffer = ""
        self._mutex = QMutex()  # 线程安全锁

    def write(self, text):
        try:
            if text.strip() or self._buffer:
                with QMutexLocker(self._mutex):
                    self._buffer += text
                    while '\n' in self._buffer:
                        line, self._buffer = self._buffer.split('\n', 1)
                        if line:
                            self.output_received.emit(line)
            try:
                if self.original_stderr and hasattr(self.original_stderr, 'write'):
                    self.original_stderr.write(text)
            except:
                pass
        except Exception:
            pass  # 捕获所有异常，避免中断

    def flush(self):
        if self._buffer:
            self.output_received.emit(self._buffer)
            self._buffer = ""
        try:
            if self.original_stderr and hasattr(self.original_stderr, 'flush'):
                self.original_stderr.flush()
        except:
            pass


class ExceptionHook:
    """全局异常捕获钩子"""
    def __init__(self, console_page):
        self.console_page = console_page
        self.original_hook = None

    def hook(self, exc_type, exc_value, exc_traceback):
        """捕获未处理的异常"""
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = ''.join(tb_lines)

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.console_page._add_manual_log('EXCEPTION', 'Uncaught', timestamp, tb_text)

        try:
            monitor = get_debug_monitor()
            monitor.capture_error(exc_value, {
                'exception_type': str(exc_type),
                'uncaught': True
            })
        except:
            pass

        if self.original_hook:
            self.original_hook(exc_type, exc_value, exc_traceback)


class LogStatisticsWidget(QWidget):
    """日志统计和错误分析小组件（专注版）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor = get_debug_monitor()
        self.init_ui()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(2000)

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 统计摘要卡片
        summary_card = SimpleCardWidget()
        summary_layout = QHBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)

        self.total_logs_label = BodyLabel("日志: 0")
        self.total_logs_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        summary_layout.addWidget(self.total_logs_label)

        summary_layout.addSpacing(20)

        self.error_count_label = BodyLabel("错误: 0")
        self.error_count_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #DC3545;')
        summary_layout.addWidget(self.error_count_label)

        summary_layout.addSpacing(20)

        self.warning_count_label = BodyLabel("警告: 0")
        self.warning_count_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #FFA500;')
        summary_layout.addWidget(self.warning_count_label)

        summary_layout.addStretch()

        # 导出错误日志按钮
        export_btn = PushButton(FluentIcon.SAVE, "导出错误日志")
        export_btn.clicked.connect(self.export_error_report)
        summary_layout.addWidget(export_btn)

        layout.addWidget(summary_card)

        # 错误统计表格
        table_group = QGroupBox("错误类型统计（按发生次数排序）")
        table_layout = QVBoxLayout(table_group)

        self.error_table = QTableWidget()
        self.error_table.setColumnCount(4)
        self.error_table.setHorizontalHeaderLabels(['错误类型', '次数', '最后发生', '首次发生'])
        self.error_table.horizontalHeader().setStretchLastSection(True)
        self.error_table.setAlternatingRowColors(True)
        self.error_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.error_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.error_table.itemDoubleClicked.connect(self.on_error_double_clicked)
        table_layout.addWidget(self.error_table)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.reload_btn = PushButton(FluentIcon.SYNC, "刷新")
        self.reload_btn.clicked.connect(self.update_stats)
        btn_layout.addWidget(self.reload_btn)

        copy_btn = PushButton(FluentIcon.COPY, "复制选中")
        copy_btn.clicked.connect(self.copy_selected)
        btn_layout.addWidget(copy_btn)

        clear_btn = PushButton(FluentIcon.DELETE, "清空错误")
        clear_btn.clicked.connect(self.clear_errors)
        btn_layout.addWidget(clear_btn)

        table_layout.addLayout(btn_layout)
        layout.addWidget(table_group, stretch=1)

    def update_stats(self):
        """更新统计信息"""
        try:
            error_stats = self.monitor.get_error_stats()
            recent_errors = error_stats.get('recent_errors', [])

            # 更新摘要
            total = error_stats.get('total_errors', 0)
            self.error_count_label.setText(f"错误: {total}")

            # 统计警告（从日志中推断）
            warnings = sum(1 for e in self.monitor.errors if 'Warning' in str(e.error_type) or 'warning' in str(e.message))
            self.warning_count_label.setText(f"警告: {min(warnings, total)}")

            # 更新表格
            self.error_table.setRowCount(0)

            # 显示错误类型统计
            row = 0
            for error_type, count in sorted(
                error_stats.get('by_type', {}).items(),
                key=lambda x: -x[1]
            )[:50]:
                self.error_table.insertRow(row)
                self.error_table.setItem(row, 0, QTableWidgetItem(str(error_type)))
                self.error_table.setItem(row, 1, QTableWidgetItem(str(count)))

                # 获取最近和首次发生时间
                errors_of_type = [e for e in recent_errors if e.error_type == error_type]
                if errors_of_type:
                    latest = max(errors_of_type, key=lambda e: e.timestamp)
                    earliest = min(errors_of_type, key=lambda e: e.timestamp)
                    self.error_table.setItem(row, 2, QTableWidgetItem(latest.timestamp.strftime("%H:%M:%S")))
                    self.error_table.setItem(row, 3, QTableWidgetItem(earliest.timestamp.strftime("%H:%M:%S")))
                row += 1

            # 自动调整列宽
            self.error_table.resizeColumnsToContents()

        except Exception as e:
            logging.error(f"更新错误统计失败: {e}")

    def on_error_double_clicked(self, item):
        """双击错误项显示详情"""
        row = item.row()
        error_type = self.error_table.item(row, 0).text()

        # 显示错误详情对话框
        error_items = [e for e in self.monitor.errors if e.error_type == error_type]
        if error_items:
            self.show_error_detail(error_items[-1])

    def show_error_detail(self, error_context: ErrorContext):
        """显示错误详情"""
        dialog = ErrorDetailDialog(error_context, self)
        dialog.exec()

    def copy_selected(self):
        """复制选中的错误信息"""
        current_row = self.error_table.currentRow()
        if current_row >= 0:
            error_type = self.error_table.item(current_row, 0).text()
            count = self.error_table.item(current_row, 1).text()

            # 获取该类型的所有错误
            error_items = [e for e in self.monitor.errors if e.error_type == error_type]
            if error_items:
                # 格式化为可复制的文本
                text = f"错误类型: {error_type}\n"
                text += f"发生次数: {count}\n\n"
                text += "最近错误详情:\n"
                text += "=" * 60 + "\n\n"
                text += f"时间: {error_items[-1].timestamp}\n"
                text += f"消息: {error_items[-1].message}\n\n"
                text += "调用上下文:\n"
                for key, value in error_items[-1].context_info.items():
                    if key != 'caller_file':  # 跳过过长的调用栈
                        text += f"  {key}: {value}\n"
                text += "\n"
                text += error_items[-1].traceback_str

                QApplication.clipboard().setText(text)
                InfoBar.success(
                    '已复制',
                    '错误详情已复制到剪贴板',
                    parent=self,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )

    def clear_errors(self):
        """清空错误记录"""
        confirm = QMessageBox.question(
            self,
            '确认清空',
            '确定要清空所有错误记录吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.monitor.clear_errors()
            self.update_stats()
            InfoBar.success(
                '已清空',
                '所有错误记录已被清空',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000
            )

    def export_error_report(self):
        """导出错误报告（用于上报）"""
        errors = list(self.monitor.errors)
        if not errors:
            QMessageBox.information(self, '导出', '没有错误记录可以导出。')
            return

        # 选择导出格式
        format_dialog = QMessageBox(self)
        format_dialog.setWindowTitle('选择导出格式')
        format_dialog.setText('请选择要导出的格式:')
        txt_btn = format_dialog.addButton('文本报告', QMessageBox.ActionRole)
        json_btn = format_dialog.addButton('完整JSON', QMessageBox.ActionRole)
        clipboard_btn = format_dialog.addButton('复制到剪贴板', QMessageBox.ActionRole)
        format_dialog.setStandardButtons(QMessageBox.Cancel)

        format_dialog.exec()

        clicked = format_dialog.clickedButton()

        if clicked == clipboard_btn:
            self.copy_error_report_to_clipboard()
        else:
            # 文件对话框
            default_name = f'PurifyAI_ErrorReport_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            if clicked == txt_btn:
                default_name += '.txt'
            else:
                default_name += '.json'

            filename, _ = QFileDialog.getSaveFileName(
                self,
                '导出错误报告',
                default_name,
                '文本格式 (*.txt);;JSON格式 (*.json)' if clicked == txt_btn else 'JSON格式 (*.json);;文本格式 (*.txt)'
            )

            if not filename:
                return

            try:
                if filename.endswith('.json'):
                    self._export_json(filename)
                else:
                    self._export_text(filename)

                InfoBar.success(
                    '导出成功',
                    f'错误报告已保存到 {os.path.basename(filename)}',
                    parent=self,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )

            except Exception as e:
                QMessageBox.critical(self, '导出失败', str(e))

    def copy_error_report_to_clipboard(self):
        """复制错误报告到剪贴板（便于粘贴上报）"""
        errors = list(self.monitor.errors)
        if not errors:
            return

        report = self._generate_text_report()
        QApplication.clipboard().setText(report)

        InfoBar.success(
            '已复制',
            '错误报告已复制到剪贴板，可直接粘贴提交',
            parent=self,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000
        )

    def _export_text(self, filename: str):
        """导出为文本格式"""
        content = self._generate_text_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

    def _export_json(self, filename: str):
        """导出为JSON格式"""
        errors = list(self.monitor.errors)
        data = {
            'generated_at': datetime.now().isoformat(),
            'total_errors': len(errors),
            'errors': [
                {
                    'type': e.error_type,
                    'message': e.message,
                    'timestamp': e.timestamp.isoformat(),
                    'traceback': e.traceback_str,
                    'context': e.context_info
                }
                for e in errors
            ]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _generate_text_report(self) -> str:
        """生成文本格式的错误报告"""
        errors = list(self.monitor.errors)
        error_stats = self.monitor.get_error_stats()

        report = []
        report.append("=" * 70)
        report.append("PurifyAI 错误报告")
        report.append("=" * 70)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"错误总数: {len(errors)}")
        report.append("")

        # 按类型统计
        report.append("-" * 70)
        report.append("错误类型统计:")
        report.append("-" * 70)
        for error_type, count in sorted(error_stats.get('by_type', {}).items(), key=lambda x: -x[1]):
            report.append(f"  {error_type}: {count} 次")
        report.append("")

        # 详细错误信息（最近的10个）
        report.append("-" * 70)
        report.append("详细错误记录 (最近的10个):")
        report.append("-" * 70)
        report.append("")

        for i, error in enumerate(reversed(errors[-10:]), 1):
            report.append(f"[{i}] {error.error_type}")
            report.append(f"    时间: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"    消息: {error.message[:200] + ('...' if len(error.message) > 200 else '')}")

            # 添加关键上下文
            context = error.context_info
            if 'caller_function' in context:
                report.append(f"    调用: {context.get('caller_function')}()")
            if 'module' in context:
                report.append(f"    模块: {context.get('module')}")
            if 'call_chain' in context and context['call_chain'] != '无':
                report.append(f"    调用链: {context['call_chain']}")
            report.append("")

            # 堆栈跟踪（截断前50行）
            tb_lines = error.traceback_str.split('\n')
            if len(tb_lines) > 50:
                tb_lines = tb_lines[:50] + ['... (堆栈跟踪已截断)']
            report.append("    堆栈跟踪:")
            for line in tb_lines:
                report.append(f"    {line}")
            report.append("")
            report.append("-" * 70)
            report.append("")

        return '\n'.join(report)


class ErrorDetailDialog(QDialog):
    """错误详情对话框"""

    def __init__(self, error_context: ErrorContext, parent=None):
        super().__init__(parent)
        self.error_context = error_context
        self.setWindowTitle(f"错误详情: {error_context.error_type}")
        self.setMinimumSize(800, 600)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 错误信息卡片
        info_card = SimpleCardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(10)

        title = StrongBodyLabel(f"{self.error_context.error_type}: {self.error_context.message[:100]}")
        title.setStyleSheet('font-size: 18px; color: #DC3545;')
        info_layout.addWidget(title)

        info_layout.addWidget(BodyLabel(f"发生时间: {self.error_context.timestamp}"))

        layout.addWidget(info_card)

        # 上下文信息
        context_group = QGroupBox("上下文信息")
        context_layout = QVBoxLayout(context_group)

        context_table = QTableWidget()
        context_table.setColumnCount(2)
        context_table.setHorizontalHeaderLabels(['字段', '值'])
        context_table.horizontalHeader().setStretchLastSection(True)

        for key, value in self.error_context.context_info.items():
            row = context_table.rowCount()
            context_table.insertRow(row)
            context_table.setItem(row, 0, QTableWidgetItem(str(key)))

            value_str = str(value)
            if len(value_str) > 500:
                value_str = value_str[:500] + "...（已截断）"
            context_table.setItem(row, 1, QTableWidgetItem(value_str))

        context_layout.addWidget(context_table)
        layout.addWidget(context_group)

        # 堆栈跟踪
        trace_group = QGroupBox("堆栈跟踪")
        trace_layout = QVBoxLayout(trace_group)

        trace_display = QTextEdit()
        trace_display.setReadOnly(True)
        trace_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 11px;
            }
        """)
        trace_display.setPlainText(self.error_context.traceback_str)

        trace_layout.addWidget(trace_display)
        layout.addWidget(trace_group, stretch=1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        copy_btn = PrimaryPushButton("复制完整信息")
        copy_btn.clicked.connect(self.copy_full_info)
        btn_layout.addWidget(copy_btn)

        close_btn = PushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def copy_full_info(self):
        """复制完整错误信息到剪贴板"""
        info = []
        info.append(f"错误类型: {self.error_context.error_type}")
        info.append(f"消息: {self.error_context.message}")
        info.append(f"时间: {self.error_context.timestamp}")
        info.append("\n--- 上下文 ---")
        for key, value in self.error_context.context_info.items():
            info.append(f"{key}: {value}")
        info.append("\n--- 堆栈跟踪 ---")
        info.append(self.error_context.traceback_str)

        text = '\n'.join(info)
        QApplication.clipboard().setText(text)

        InfoBar.success(
            '已复制',
            '完整错误信息已复制到剪贴板',
            parent=self,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000
        )


class DeveloperConsolePage(QWidget):
    """开发者控制台页面 - 实时显示日志和控制台输出（专注版）"""

    page_loaded = pyqtSignal()  # 页面加载信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_level = 'ALL'
        self.filter_text = ''
        self.all_logs = []
        self.monitor = get_debug_monitor()

        # 输出重定向相关
        self.stdout_redirector = None
        self.stderr_redirector = None
        self.exception_hook = None
        self.original_stdout = None
        self.original_stderr = None
        self.io_enabled = True
        self._is_owning_io = False  # 标记是否拥有IO重定向

        # 独立窗口
        self.independent_window = None

        # 简化的更新机制 - 延迟更新标志
        self.update_pending = False
        self.update_scheduled = False

        # 静态变量：追踪哪个组件拥有IO重定向
        self._io_owner = None  # 'page' or 'window' or None

        self.init_ui()
        self.init_logger()
        self.init_io_redirector()
        self.init_menu()
        self.setup_error_callbacks()
        self.page_loaded.emit()

    def init_ui(self):
        """初始化用户界面"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧：日志显示区域
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(30, 30, 10, 30)
        left_layout.setSpacing(15)

        # 标题
        title_layout = QHBoxLayout()
        title = StrongBodyLabel('开发者控制台')
        title.setStyleSheet('font-size: 24px;')
        title_layout.addWidget(title)
        title_layout.addStretch()

        self.io_capture_check = QCheckBox('捕获控制台输出')
        self.io_capture_check.setChecked(True)
        self.io_capture_check.stateChanged.connect(self.toggle_io_capture)
        title_layout.addWidget(self.io_capture_check)

        self.pause_scroll_check = QCheckBox('暂停自动滚动')
        self.pause_scroll_check.setChecked(False)
        title_layout.addWidget(self.pause_scroll_check)

        # 实时日志控制
        self.rt_logger = RealTimeLogger()
        self.rt_logger_enabled = False

        self.rt_logger_btn = PushButton('📝 实时日志', self)
        self.rt_logger_btn.clicked.connect(self.toggle_realtime_logger)
        title_layout.addWidget(self.rt_logger_btn)

        self.rt_log_clear_btn = PushButton('清理日志', self)
        self.rt_log_clear_btn.clicked.connect(self.clear_rt_logs)
        self.rt_log_clear_btn.setEnabled(False)
        title_layout.addWidget(self.rt_log_clear_btn)

        # 独立窗口按钮
        self.open_window_btn = PushButton('独立窗口', self)
        self.open_window_btn.setIcon(FluentIcon.FULL_SCREEN)
        self.open_window_btn.clicked.connect(self.open_independent_window)
        title_layout.addWidget(self.open_window_btn)

        left_layout.addLayout(title_layout)

        # 说明
        desc = BodyLabel('实时显示应用程序日志、print输出和错误信息。可导出错误报告进行问题上报。')
        desc.setStyleSheet('color: #666; font-size: 14px;')
        left_layout.addWidget(desc)

        # 控制栏卡片
        header_card = CardWidget()
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(10)

        # 控制按钮
        self.refresh_btn = PushButton('刷新', self)
        self.refresh_btn.setIcon(FluentIcon.SYNC)
        self.refresh_btn.clicked.connect(self.refresh_logs)

        self.clear_btn = PushButton('清空', self)
        self.clear_btn.setIcon(FluentIcon.DELETE)
        self.clear_btn.clicked.connect(self.clear_logs)

        self.copy_all_btn = PushButton('复制', self)
        self.copy_all_btn.setIcon(FluentIcon.COPY)
        self.copy_all_btn.clicked.connect(self.copy_all_logs)

        self.export_btn = PushButton('导出', self)
        self.export_btn.setIcon(FluentIcon.SAVE)
        self.export_btn.clicked.connect(self.export_logs)

        # 搜索
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText('搜索日志...')
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_text_changed)

        # 过滤下拉框
        filter_label = BodyLabel('级别:')
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(LOG_LEVELS)
        self.filter_combo.setCurrentText('ALL')
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)

        # 添加控件到布局
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.clear_btn)
        header_layout.addWidget(self.copy_all_btn)
        header_layout.addWidget(self.export_btn)
        header_layout.addWidget(self.search_input)
        header_layout.addStretch()
        header_layout.addWidget(filter_label)
        header_layout.addWidget(self.filter_combo)

        left_layout.addWidget(header_card)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('QTabWidget::pane { border: 1px solid #ddd; }')

        # 日志标签页
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                border-radius: 4px;
                border: 1px solid #444;
            }
        """)

        # 添加语法高亮
        self.highlighter = LogSyntaxHighlighter(self.log_display.document())

        # 错误统计标签页
        self.stats_tab = LogStatisticsWidget()

        self.tabs.addTab(self.log_display, "日志输出")
        self.tabs.addTab(self.stats_tab, "错误统计")

        left_layout.addWidget(self.tabs, 1)

        # 状态栏
        status_card = SimpleCardWidget()
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(15, 10, 15, 10)

        self.status_log_count = BodyLabel('日志: 0')
        self.status_filter = BodyLabel('过滤: ALL')
        self.status_errors = BodyLabel('错误: 0')
        self.status_time = BodyLabel('')
        self.rt_log_status = BodyLabel('')

        status_layout.addWidget(self.status_log_count)
        status_layout.addSpacing(30)
        status_layout.addWidget(self.status_filter)
        status_layout.addSpacing(30)
        status_layout.addWidget(self.status_errors)
        status_layout.addSpacing(30)
        status_layout.addWidget(self.status_time)
        status_layout.addSpacing(30)
        status_layout.addWidget(self.rt_log_status)
        status_layout.addStretch()

        left_layout.addWidget(status_card)
        main_layout.addWidget(left_container)

    def init_logger(self):
        """初始化控制台日志处理器"""
        self.log_handler = ConsoleLogHandler(self)
        self.log_handler.setLevel(logging.DEBUG)
        self.log_handler.log_signal.connect(self._on_log_received)

    def init_io_redirector(self):
        """初始化标准输出/错误重定向"""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self.stdout_redirector = StdoutRedirector(self.original_stdout)
        self.stderr_redirector = StderrRedirector(self.original_stderr)

        self.stdout_redirector.output_received.connect(self._on_stdout_received)
        self.stderr_redirector.output_received.connect(self._on_stderr_received)

    def setup_io_redirector(self):
        """启用标准输出/错误重定向（仅当没有其他组件拥有IO时）"""
        # 检查是否有独立窗口拥有IO
        if (self.independent_window and self.independent_window.isVisible() and
            hasattr(self.independent_window, '_is_owning_io') and
            self.independent_window._is_owning_io):
            # 独立窗口已拥有IO，页面不获取
            return

        if not self.io_enabled:
            return

        sys.stdout = self.stdout_redirector
        sys.stderr = self.stderr_redirector
        DeveloperConsolePage._io_owner = 'page'
        self._is_owning_io = True

        self.exception_hook = ExceptionHook(self)
        self.exception_hook.original_hook = sys.excepthook
        sys.excepthook = self.exception_hook.hook

        print("[开发者控制台-页面] 控制台输出捕获已启用")

    def restore_io_redirector(self):
        """恢复原始的输出"""
        # 只有当这个页面拥有IO时才恢复
        if not self._is_owning_io:
            return

        sys.stdout = self.original_stdout if self.original_stdout else sys.__stdout__
        sys.stderr = self.original_stderr if self.original_stderr else sys.__stderr__

        if self.exception_hook and self.exception_hook.original_hook:
            sys.excepthook = self.exception_hook.original_hook

        DeveloperConsolePage._io_owner = None
        self._is_owning_io = False

    def toggle_io_capture(self, state):
        """切换IO捕获状态"""
        self.io_enabled = (state == Qt.Checked)
        if self.io_enabled:
            self.setup_io_redirector()
            self._add_manual_log('INFO', 'DeveloperConsole', datetime.now().strftime("%H:%M:%S.%f")[:-3], "控制台输出捕获已启用")
        else:
            self.restore_io_redirector()
            self._add_manual_log('INFO', 'DeveloperConsole', datetime.now().strftime("%H:%M:%S.%f")[:-3], "控制台输出捕获已禁用")

    def setup_error_callbacks(self):
        """设置错误回调"""
        self.monitor.add_error_callback(self.on_error_occurred)

    def on_error_occurred(self, error_context: ErrorContext):
        """错误发生时的回调"""
        error_count = len(self.monitor.errors)
        self.status_errors.setText(f'错误: {error_count}')

    def _on_stdout_received(self, text: str):
        """处理接收到的stdout输出"""
        if not self.io_enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._add_manual_log('STDOUT', 'stdout', timestamp, text.rstrip())

    def _on_stderr_received(self, text: str):
        """处理接收到的stderr输出"""
        if not self.io_enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._add_manual_log('STDERR', 'stderr', timestamp, text.rstrip())

    def _add_manual_log(self, level: str, logger_name: str, timestamp: str, message: str):
        """手动添加日志到控制台（轻量级）"""
        # 如果独立窗口打开且可见，主页面不处理日志，避免冲突
        if (self.independent_window and self.independent_window.isVisible()):
            return

        log_entry = {
            'level': level,
            'logger': logger_name,
            'timestamp': timestamp,
            'message': message
        }

        # 限制内存使用
        self.all_logs.append(log_entry)
        if len(self.all_logs) > MAX_LOG_LINES:
            self.all_logs = self.all_logs[-MAX_LOG_LINES:]

        # 仅在页面可见时更新
        if self.isVisible():
            self._schedule_update()

    def _on_log_received(self, level: str, logger_name: str, timestamp: str, message: str):
        """处理接收到的日志信号（轻量级）"""
        # 如果独立窗口打开且可见，主页面不处理日志，避免冲突
        if (self.independent_window and self.independent_window.isVisible()):
            return

        log_entry = {
            'level': level,
            'logger': logger_name,
            'timestamp': timestamp,
            'message': message
        }

        # 限制内存使用
        self.all_logs.append(log_entry)
        if len(self.all_logs) > MAX_LOG_LINES:
            self.all_logs = self.all_logs[-MAX_LOG_LINES:]

        # 仅在页面可见时更新
        if self.isVisible():
            self._schedule_update()

    def _schedule_update(self):
        """计划一次UI更新（防抖）"""
        # 如果独立窗口打开，完全跳过更新
        if self.independent_window and self.independent_window.isVisible():
            return

        # 如果页面不可见，完全跳过更新
        if not self.isVisible():
            return

        if not self.update_scheduled:
            self.update_scheduled = True
            QTimer.singleShot(200, self._do_update)  # 增加到200ms

    def _do_update(self):
        """执行UI更新（批量处理，线程安全）"""
        # 双重检查：如果独立窗口打开或页面不可见，立即返回
        if (self.independent_window and self.independent_window.isVisible()) or not self.isVisible():
            self.update_scheduled = False
            return

        self.update_scheduled = False

        try:
            # 只显示最近100条日志，减少UI渲染压力
            recent_logs = self.all_logs[-100:] if len(self.all_logs) > 100 else self.all_logs

            # 如果日志太多，直接清空队列，避免无限增长
            if len(self.all_logs) > 5000:
                self.all_logs = self.all_logs[-1000:]

            # 简单文本方式更新
            lines = []
            for log in recent_logs:
                try:
                    if not self._should_show_log(log['level']) or not self._should_show_by_search(log['message']):
                        continue
                    color = LOG_COLORS.get(log['level'], '#d4d4d4')
                    # 转义HTML特殊字符
                    message = log['message'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    lines.append(f'<span style="color:{color}">[{log["level"]}] {log["timestamp"]} - {log["logger"]} - {message}</span>')
                except Exception:
                    pass

            if lines:
                self.log_display.setHtml('<br>'.join(lines))
                if not self.pause_scroll_check.isChecked():
                    self.log_display.moveCursor(QTextCursor.End)

            # 不频繁更新状态栏（每次只更新计数）
            if len(self.all_logs) % 50 == 0:  # 每50条日志更新一次状态
                self._update_status_bar()
        except Exception as e:
            # 捕获更新异常，避免影响后续日志
            pass

    def _should_show_log(self, level: str) -> bool:
        """""检查是否应该显示指定级别的日志"""
        if self.filter_level == 'ALL':
            return True

        level_priority = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}
        min_level = level_priority.get(self.filter_level, 0)
        return level_priority.get(level, 0) >= min_level

    def _should_show_by_search(self, message: str) -> bool:
        """检查是否应该显示（基于搜索条件）"""
        if not self.filter_text:
            return True
        return self.filter_text.lower() in message.lower()

    def _count_filtered_logs(self) -> int:
        """计算过滤后的日志数量"""
        level_priority = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}
        min_level = level_priority.get(self.filter_level, 0)

        return sum(
            1 for log in self.all_logs
            if level_priority.get(log['level'], 0) >= min_level
            and self._should_show_by_search(log['message'])
        )

    def _update_filtered_display(self):
        """根据当前过滤更新显示的日志（轻量级）"""
        level_priority = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}
        min_level = level_priority.get(self.filter_level, 0)

        # 只显示最近500条符合过滤的日志
        filtered = [
            log for log in self.all_logs
            if level_priority.get(log['level'], 0) >= min_level
            and self._should_show_by_search(log['message'])
        ][-500:]  # 只最后500条

        # 简单文本方式更新
        lines = []
        for log in filtered:
            color = LOG_COLORS.get(log['level'], '#d4d4d4')
            lines.append(f'<span style="color:{color}">[{log["level"]}] {log["timestamp"]} - {log["logger"]} - {log["message"]}</span>')

        if lines:
            self.log_display.setHtml('<br>'.join(lines))
            self.log_display.moveCursor(QTextCursor.End)

        self._update_status_bar(len(filtered))

    def _update_status_bar(self, visible_count: int = None):
        """更新状态栏信息"""
        total_count = len(self.all_logs)

        if visible_count is None:
            visible_count = total_count if self.filter_level == 'ALL' else self._count_filtered_logs()

        if self.filter_level == 'ALL':
            self.status_log_count.setText(f'日志: {visible_count}')
        else:
            self.status_log_count.setText(f'日志: {visible_count}/{total_count}')

        self.status_filter.setText(f'过滤: {self.filter_level}')
        self.status_time.setText(f'当前: {datetime.now().strftime("%H:%M:%S")}')
        self.status_errors.setText(f'错误: {len(self.monitor.errors)}')

        # 更新实时日志状态
        if self.rt_logger_enabled:
            stats = self.rt_logger.get_stats()
            self.rt_log_status.setText(f'实时日志: {stats["log_count"]}条 | {stats["file_size_mb"]:.1f}MB')
            self.rt_log_status.setStyleSheet('color: #0078D4;')
        else:
            self.rt_log_status.setText('实时日志: 未启用')
            self.rt_log_status.setStyleSheet('color: #999;')

    def _append_log(self, cursor: QTextCursor, level: str, logger_name: str,
                   timestamp: str, message: str):
        """用格式化添加日志条目"""
        color = LOG_COLORS.get(level, '#d4d4d4')
        text = f'[{level:<8}] {timestamp} - {logger_name} - {message}\n'

        char_format = QTextCharFormat()
        char_format.setForeground(QColor(color))

        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text, char_format)

    def setup_root_logger(self):
        """将控制台处理器添加到根日志器"""
        root_logger = logging.getLogger()

        if self.log_handler in root_logger.handlers:
            root_logger.removeHandler(self.log_handler)

        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.DEBUG)
        logging.info('开发者控制台: 开始日志捕获')

    def cleanup_root_logger(self):
        """从根日志器中移除控制台处理器"""
        root_logger = logging.getLogger()
        if self.log_handler in root_logger.handlers:
            root_logger.removeHandler(self.log_handler)

    def init_menu(self):
        """初始化日志显示的上下文菜单"""
        self.log_display.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_display.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        """在指定位置显示上下文菜单"""
        menu = RoundMenu(parent=self.log_display)
        menu.addAction(Action(FluentIcon.COPY, '复制选中', triggered=self.copy_selected))
        menu.addAction(Action(FluentIcon.COPY, '复制全部', triggered=self.copy_all_logs))
        menu.addSeparator()
        menu.addAction(Action(FluentIcon.DELETE, '清空全部', triggered=self.clear_logs))
        menu.addAction(Action(FluentIcon.SAVE, '导出...', triggered=self.export_logs))
        menu.addSeparator()
        menu.addAction(Action(FluentIcon.SYNC, '刷新显示', triggered=self.refresh_logs))
        menu.exec(self.log_display.mapToGlobal(pos))

    def on_filter_changed(self, level: str):
        """处理过滤级别变化"""
        self.filter_level = level
        self._update_filtered_display()

    def on_search_text_changed(self, text: str):
        """处理搜索文本变化"""
        self.filter_text = text
        self._update_filtered_display()

    def refresh_logs(self):
        """刷新日志显示"""
        self._update_filtered_display()
        self.stats_tab.update_stats()

        InfoBar.success(
            '已刷新',
            f'日志已更新 (总计 {len(self.all_logs)} 条)',
            parent=self,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def clear_logs(self):
        """清空所有日志"""
        self.all_logs.clear()
        self.log_display.clear()
        self._update_status_bar(0)

        self.monitor.clear_errors()
        self.stats_tab.update_stats()

        InfoBar.success(
            '已清空',
            '所有日志和错误记录已被清空',
            parent=self,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def copy_selected(self):
        """复制选中的文本到剪贴板"""
        selected = self.log_display.textCursor().selectedText()
        if selected:
            QApplication.clipboard().setText(selected)
            InfoBar.success(
                '已复制',
                '选中文本已复制到剪贴板',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000
            )

    def copy_all_logs(self):
        """复制所有显示的日志到剪贴板"""
        if not self.all_logs:
            return

        text = '========================================\n'
        text += f'PurifyAI 日志导出\n'
        text += f'导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
        text += f'过滤: {self.filter_level} | 数量: {len(self.all_logs)}\n'
        text += '========================================\n\n'

        for log in self.all_logs:
            text += f'[{log["level"]:<8}] {log["timestamp"]} - {log["logger"]} - {log["message"]}\n'

        QApplication.clipboard().setText(text)

        InfoBar.success(
            '已复制',
            f'所有日志已复制到剪贴板',
            parent=self,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def export_logs(self):
        """导出日志到文本文件"""
        if not self.all_logs:
            QMessageBox.information(self, '导出', '没有日志可导出。')
            return

        default_name = f'PurifyAI_Logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        filename, _ = QFileDialog.getSaveFileName(
            self,
            '导出日志',
            default_name,
            '文本文件 (*.txt);;所有文件 (*)'
        )

        if not filename:
            return

        try:
            content = '========================================\n'
            content += 'PurifyAI 日志导出\n'
            content += f'导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            content += f'总日志数量: {len(self.all_logs)}\n'
            content += f'错误数量: {len(self.monitor.errors)}\n\n'

            for log in self.all_logs:
                content += f'[{log["level"]:<8}] {log["timestamp"]} - {log["logger"]} - {log["message"]}\n'

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            InfoBar.success(
                '已导出',
                f'日志已导出到 {os.path.basename(filename)}',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000
            )

        except Exception as e:
            logging.error(f'导出日志失败: {e}')
            QMessageBox.critical(self, '导出错误', str(e))

    def open_independent_window(self):
        """打开独立开发者控制台窗口"""
        # 在打开独立窗口前，页面先释放IO
        self.restore_io_redirector()

        if self.independent_window is None or not self.independent_window.isVisible():
            self.independent_window = DeveloperConsoleWindow(self)
            self.independent_window.show()
            self.independent_window.raise_()
            self.independent_window.activateWindow()
            InfoBar.success(
                '独立窗口已打开',
                '开发者控制台现已在新窗口中运行\n已将控制台输出重定向至独立窗口',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        else:
            self.independent_window.raise_()
            self.independent_window.activateWindow()

    def showEvent(self, event):
        """显示事件 - 延迟加载日志，避免阻塞UI"""
        super().showEvent(event)
        self.setup_root_logger()
        self.setup_io_redirector()

        # 不立即更新显示，避免处理过多日志导致卡死
        # 只初始化一个空状态，等待新的日志进来
        self.log_display.clear()
        self._update_status_bar()

    def hideEvent(self, event):
        """隐藏事件 - 只清理日志，不释放IO"""
        super().hideEvent(event)
        self.cleanup_root_logger()
        self.log_display.clear()  # 隐藏时清空显示，节省内存
        # 不自动恢复IO，避免与独立窗口冲突

    # ==================== 实时日志功能 ====================

    def toggle_realtime_logger(self):
        """切换实时日志开关"""
        if self.rt_logger_enabled:
            # 禁用实时日志
            self.rt_logger.disable()
            self.rt_logger_enabled = False
            self.rt_logger_btn.setText('📝 实时日志')
            self.rt_logger_btn.setStyleSheet('')
            self.rt_log_clear_btn.setEnabled(False)

            InfoBar.success(
                '实时日志已停止',
                '日志记录已停止，日志文件已保存',
                parent=self,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        else:
            # 启用实时日志
            if self.rt_logger.enable():
                self.rt_logger_enabled = True
                self.rt_logger_btn.setText('🔵 实时日志运行中')
                self.rt_logger_btn.setStyleSheet('color: #0078D4; font-weight: bold;')
                self.rt_log_clear_btn.setEnabled(True)

                # 安装异常钩子
                install_realtime_excepthook()

                # 写入启动日志
                self.rt_logger.write('INFO', 'RealTimeLogger', '实时日志已启用')
                self.rt_logger.write('INFO', 'System', f'Python版本: {sys.version}')
                self.rt_logger.write('INFO', 'System', f'工作目录: {os.getcwd()}')

                InfoBar.success(
                    '实时日志已启动',
                    '所有日志将立即写入到磁盘，即使程序崩溃也不会丢失',
                    parent=self,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            else:
                InfoBar.error(
                    '启动失败',
                    '无法创建实时日志文件，请检查目录权限',
                    parent=self,
                    orient=Qt.Horizontal,
                )

        self._update_status_bar()

    def clear_rt_logs(self):
        """清理实时日志文件"""
        from PyQt5.QtWidgets import QCheckBox

        # 创建确认对话框
        confirm = QMessageBox(self)
        confirm.setWindowTitle('确认清理')
        confirm.setText('确定要清理所有实时日志吗？')
        confirm.setInformativeText('这将删除所有实时日志文件，此操作不可恢复。')

        keep_chk = QCheckBox('保留最新的10个日志文件')
        confirm.setCheckBox(keep_chk)

        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)

        if confirm.exec() == QMessageBox.Yes:
            if self.rt_logger.clear():
                # 如果选择保留，重新启用
                if keep_chk.isChecked() and self.rt_logger_enabled:
                    self.rt_logger.enable()

                InfoBar.success(
                    '清理完成',
                    '实时日志文件已清理',
                    parent=self,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000
                )
            else:
                InfoBar.error(
                    '清理失败',
                    '无法删除日志文件',
                    parent=self,
                    orient=Qt.Horizontal,
                )

            self._update_status_bar()

    def _write_to_rt_log(self, level: str, logger_name: str, timestamp: str, message: str):
        """将日志写入实时文件"""
        if self.rt_logger_enabled:
            self.rt_logger.write(level, logger_name, message, timestamp)

    # 重写日志接收方法，添加实时日志写入
    def _on_log_received(self, level: str, logger_name: str, timestamp: str, message: str):
        """处理接收到的日志信号（带实时日志）"""
        # 写入实时文件（如果启用）
        if self.rt_logger_enabled:
            self.rt_logger.write(level, logger_name, message, timestamp)

        # 如果独立窗口打开且可见，完全跳过主页面处理，避免冲突
        if self.independent_window and self.independent_window.isVisible():
            return

        log_entry = {
            'level': level,
            'logger': logger_name,
            'timestamp': timestamp,
            'message': message
        }

        # 限制内存使用
        self.all_logs.append(log_entry)
        if len(self.all_logs) > MAX_LOG_LINES:
            self.all_logs = self.all_logs[-MAX_LOG_LINES:]

        # 仅在页面可见时更新
        if self.isVisible():
            self._schedule_update()

    def _on_stdout_received(self, text: str):
        """处理接收到的stdout输出（带实时日志）"""
        if not self.io_enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # 写入实时文件
        if self.rt_logger_enabled:
            self.rt_logger.write('STDOUT', 'stdout', timestamp, text.rstrip())

        # 如果独立窗口打开且可见，完全跳过主页面处理
        if (self.independent_window and self.independent_window.isVisible()):
            return

        # 不添加到UI（stdout输出太多，只写入实时日志）
        self._add_manual_log('STDOUT', 'stdout', timestamp, text.rstrip()[:100])  # 只保存前100字符

    def _on_stderr_received(self, text: str):
        """处理接收到的stderr输出（带实时日志）"""
        if not self.io_enabled:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # 写入实时文件
        if self.rt_logger_enabled:
            self.rt_logger.write('STDERR', 'stderr', timestamp, text.rstrip())

        # 如果独立窗口打开且可见，完全跳过主页面处理
        if (self.independent_window and self.independent_window.isVisible()):
            return

        # stderr 重要，添加到UI
        self._add_manual_log('STDERR', 'stderr', timestamp, text.rstrip[:200])  # 只保存前200字符

    def _add_manual_log(self, level: str, logger_name: str, timestamp: str, message: str):
        """手动添加日志到控制台（带实时日志）"""
        # 写入实时文件
        if self.rt_logger_enabled:
            self.rt_logger.write(level, logger_name, timestamp, message)

        # 如果独立窗口打开且可见，主页面不处理日志，避免冲突
        if (self.independent_window and self.independent_window.isVisible()):
            return

        log_entry = {
            'level': level,
            'logger': logger_name,
            'timestamp': timestamp,
            'message': message
        }

        # 限制内存使用
        self.all_logs.append(log_entry)
        if len(self.all_logs) > MAX_LOG_LINES:
            self.all_logs = self.all_logs[-MAX_LOG_LINES:]

        # 仅在页面可见时更新
        if self.isVisible():
            self._schedule_update()
