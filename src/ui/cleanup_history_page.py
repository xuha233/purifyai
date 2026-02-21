"""
清理历史页面 UI - Cleanup History Page

Phase 6 MVP功能:
- 显示历史清理记录
- 按时间、状态、类型过滤
- 统计信息展示
- 查看执行结果
- 一键恢复失败项

Features:
- 分页加载历史记录
- 实时搜索和过滤
- 可视化统计图表
- 执行详情展示
- 快速操作按钮
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QDialog, QScrollArea, QFrame, QSplitter,
    QGridLayout, QPushButton, QComboBox, QLineEdit
)

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, SimpleCardWidget, PushButton,
    PrimaryPushButton, ProgressBar, FluentIcon, InfoBar,
    InfoBarPosition, CardWidget, StrongBodyLabel, IconWidget,
    SearchLineEdit, TableWidget, ComboBox
)
from PyQt5.QtWidgets import QHeaderView, QTableWidgetItem, QAbstractItemView

from core.smart_cleaner import SmartCleaner, SmartCleanConfig, get_smart_cleaner
from core.models_smart import CleanupPlan, CleanupItem, CleanupStatus, ExecutionResult, ExecutionStatus
from core.recovery_manager import RecoveryManager, get_recovery_manager
from core.database import get_database
from core.rule_engine import RiskLevel
from utils.logger import get_logger

logger = get_logger(__name__)


class HistoryRecord:
    """历史记录数据类"""

    def __init__(
        self,
        plan_id: str,
        plan_name: str,
        scan_type: str,
        scan_target: str,
        total_items: int,
        total_size: int,
        estimated_freed: int,
        status: str,
        created_at: str,
        completed_at: Optional[str] = None,
        success_count: int = 0,
        failed_count: int = 0,
        skipped_count: int = 0,
        freed_size: int = 0
    ):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.scan_type = scan_type
        self.scan_target = scan_target
        self.total_items = total_items
        self.total_size = total_size
        self.estimated_freed = estimated_freed
        self.status = status
        self.created_at = created_at
        self.completed_at = completed_at
        self.success_count = success_count
        self.failed_count = failed_count
        self.skipped_count = skipped_count
        self.freed_size = freed_size

    @property
    def is_running(self) -> bool:
        return self.status == ExecutionStatus.RUNNING.value

    @property
    def is_completed(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED.value

    @property
    def has_failures(self) -> bool:
        return self.failed_count > 0


class LoadHistoryThread(QThread):
    """加载历史记录线程"""

    progress = pyqtSignal(int, int)  # current, total
    completed = pyqtSignal(list)      # records
    error = pyqtSignal(str)           # error_msg

    def __init__(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        scan_type_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ):
        super().__init__()
        self.limit = limit
        self.offset = offset
        self.status_filter = status_filter
        self.scan_type_filter = scan_type_filter
        self.date_from = date_from
        self.date_to = date_to
        self.is_cancelled = False

    def run(self):
        """执行加载"""
        try:
            db = get_database()
            conn = db._get_connection()
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if self.status_filter:
                conditions.append("status = ?")
                params.append(self.status_filter)

            if self.scan_type_filter:
                conditions.append("scan_type = ?")
                params.append(self.scan_type_filter)

            if self.date_from:
                conditions.append("created_at >= ?")
                params.append(self.date_from.isoformat())

            if self.date_to:
                conditions.append("created_at <= ?")
                params.append(self.date_to.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询总数
            count_query = f'SELECT COUNT(*) FROM cleanup_plans WHERE {where_clause}'
            cursor.execute(count_query, params)
            total = cursor.fetchone()['count']

            # 查询历史记录
            query = f'''
                SELECT * FROM cleanup_plans
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([self.limit, self.offset])

            cursor.execute(query, params)

            # 加载执行结果
            records = []
            for row in cursor.fetchall():
                record = HistoryRecord(
                    plan_id=row['plan_id'],
                    plan_name=row['plan_name'] or f"{row['scan_type'].title()} 扫描",
                    scan_type=row['scan_type'],
                    scan_target=row['scan_target'],
                    total_items=row['total_items'],
                    total_size=row['total_size'],
                    estimated_freed=row['estimated_freed_size'],
                    status=row['status'],
                    created_at=row['created_at'],
                    completed_at=row.get('updated_at')
                )

                # 加载执行结果
                exec_query = '''
                    SELECT * FROM cleanup_executions
                    WHERE plan_id = ?
                    ORDER BY started_at DESC
                    LIMIT 1
                '''
                cursor.execute(exec_query, (row['plan_id'],))
                exec_row = cursor.fetchone()

                if exec_row:
                    record.success_count = exec_row['success_items']
                    record.failed_count = exec_row['failed_items']
                    record.skipped_count = exec_row['skipped_items']
                    record.freed_size = exec_row['freed_size']

                records.append(record)

                if not self._is_cancelled():
                    self.progress.emit(len(records), total)

            conn.close()

            if not self._is_cancelled():
                self.completed.emit(records)

        except Exception as e:
            self.error.emit(f"加载历史记录失败: {str(e)}")

    def _is_cancelled(self) -> bool:
        """检查是否取消（线程安全）"""
        return self.is_cancelled

    def cancel(self):
        """取消加载"""
        self.is_cancelled = True


class HistoryRecordWidget(CardWidget):
    """历史记录卡片组件"""

    def __init__(self, record: HistoryRecord, parent=None):
        super().__init__(parent)
        self.record = record
        self.setMinimumHeight(80)
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        icon = IconWidget(FluentIcon.HISTORY)
        icon.setFixedSize(32, 32)
        layout.addWidget(icon)

        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 标题行
        title_row = QHBoxLayout()
        title = StrongBodyLabel(self.record.plan_name)
        title.setMaximumWidth(200)
        title.setStyleSheet('font-size: 14px;')
        title_row.addWidget(title)

        # 状态标签
        status_colors = {
            'pending': ('#fff3e0', '#ff9800'),
            'running': ('#e3f2fd', '#2196f3'),
            'completed': ('#e6f7e6', '#28a745'),
            'partial_success': ('#fff8e1', '#ffc107'),
            'cancelled': ('#ffebee', '#f44336'),
            'error': ('#fee2e2', '#dc3545')
        }
        bg, fg = status_colors.get(self.record.status, status_colors['pending'])
        status_label = BodyLabel(self._get_status_text())
        status_label.setStyleSheet(f'font-size: 10px; padding: 2px 8px; border-radius: 4px; background: {bg}; color: {fg};')

        title_row.addWidget(status_label)
        title_row.addStretch()
        info_layout.addLayout(title_row)

        # 信息行
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        # 扫描类型
        scan_label = BodyLabel(self.record.scan_type)
        scan_label.setStyleSheet('font-size: 11px; color: #666;')
        info_row.addWidget(scan_label)

        # 项目数量
        items_label = BodyLabel(f"项目: {self.record.total_items}")
        items_label.setStyleSheet('font-size: 11px; color: #666;')
        info_row.addWidget(items_label)

        # 文件大小
        size_label = BodyLabel(f"大小: {self._format_size(self.record.total_size)}")
        size_label.setStyleSheet('font-size: 11px; color: #666;')
        info_row.addWidget(size_label)

        if self.record.is_completed:
            released = BodyLabel(f"释放: {self._format_size(self.record.freed_size)}")
            released.setStyleSheet('font-size: 11px; color: #28a745;')
            info_row.addWidget(released)

        if self.record.has_failures:
            failed = BodyLabel(f"失败: {self.record.failed_count}")
            failed.setStyleSheet('font-size: 11px; color: #dc3545;')
            info_row.addWidget(failed)

        info_row.addStretch()
        info_layout.addLayout(info_row)

        # 时间信息
        time_label = BodyLabel(self._format_time(self.record.created_at))
        time_label.setStyleSheet('font-size: 10px; color: #999;')
        info_layout.addWidget(time_label)

        layout.addLayout(info_layout)

        # 操作按钮
        action_layout = QVBoxLayout()
        action_layout.setSpacing(4)

        # 详情按钮
        details_btn = PushButton("详情")
        details_btn.setFixedHeight(28)
        details_btn.clicked.connect(self._show_details)
        action_layout.addWidget(details_btn)

        # 恢复按钮（仅已完成的记录且有失败项）
        if self.record.is_completed and self.record.has_failures:
            recover_btn = PushButton("恢复失败项")
            recover_btn.setFixedHeight(28)
            recover_btn.clicked.connect(self._recover_failed_items)
            action_layout.addWidget(recover_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            'pending': '准备中',
            'running': '执行中',
            'completed': '已完成',
            'partial_success': '部分成功',
            'cancelled': '已取消',
            'error': '错误'
        }
        return status_map.get(self.record.status, self.record.status)

    def _show_details(self):
        """显示详情"""
        parent = self.parentWidget()
        if parent:
            # 发送详情请求信号
            if hasattr(parent, 'show_record_details'):
                parent.show_record_details(self.record)

    def _recover_failed_items(self):
        """恢复失败项"""
        parent = self.parentWidget()
        if parent and hasattr(parent, 'recover_failed_items'):
            parent.recover_failed_items(self.record)

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 8
        return f"{size:.1f} TB"

    def _format_time(self, time_str: str) -> str:
        """格式化时间"""
        try:
            dt = datetime.fromisoformat(time_str)
            now = datetime.now()
            delta = now - dt

            if delta.days == 0:
                if delta.seconds < 3600:
                    return f"{delta.seconds // 60} 分钟前"
                else:
                    return f"{delta.seconds // 3600} 小时前"
            elif delta.days == 1:
                return "昨天"
            elif delta.days < 7:
                return f"{delta.days} 天前"
            else:
                return dt.strftime("%Y-%m-%d")
        except:
            return time_str


class HistoryRecordDetailsDialog(QDialog):
    """历史记录详情对话框"""

    def __init__(self, record: HistoryRecord, parent=None):
        super().__init__(parent)
        self.setWindowTitle("清理计划详情")
        self.setMinimumSize(700, 500)
        self.record = record
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        header = QHBoxLayout()
        icon = IconWidget(FluentIcon.DOCUMENT)
        icon.setFixedSize(32, 32)
        header.addWidget(icon)

        title = SubtitleLabel(self.record.plan_name)
        header.addWidget(title)

        header.addStretch()
        layout.addLayout(header)

        # 基本信息卡片
        info_card = CardWidget()
        info_layout = QGridLayout(info_card)
        info_layout.setSpacing(12)

        # 状态列
        status_labels = [
            "计划 ID:", "扫描类型:", "扫描目标:", "项目数:",
            "文件大小:", "预计释放:", "执行状态:", "创建时间:"
        ]
        status_values = [
            self.record.plan_id,
            self.record.scan_type,
            self.record.scan_target,
            str(self.record.total_items),
            self._format_size(self.record.total_size),
            self._format_size(self.record.estimated_freed),
            self._get_status_text(),
            self.record.created_at
        ]

        for i, (label, value) in enumerate(zip(status_labels, status_values)):
            lbl = BodyLabel(label)
            val = BodyLabel(value)
            val.setStyleSheet('font-weight: 500; color: #333;')

            info_layout.addWidget(lbl, i // 4, (i % 4) * 2)
            info_layout.addWidget(val, i // 4, (i % 4) * 2 + 1)

        layout.addWidget(info_card)

        # 执行结果
        if self.record.is_completed:
            result_card = self._create_result_card()
            layout.addWidget(result_card)
        else:
            status_text = SubtitleLabel("执行中..." if self.record.is_running else "等待执行")
            status_text.setStyleSheet('color: #ff9800;')
            layout.addWidget(status_text)

        # close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = PushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedHeight(36)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_result_card(self) -> CardWidget:
        """创建执行结果卡片"""
        card = CardWidget()
        card.setFixedHeight(100)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 标题
        title = SubtitleLabel("执行结果")
        layout.addWidget(title)

        # 统计行
        stats_row = QHBoxLayout()
        stats_row.setSpacing(24)

        if self.record.success_count > 0:
            success_info = f"成功: {self.record.success_count} 项"
            success_label = BodyLabel(success_info)
            success_label.setStyleSheet('font-size: 14px; color: #28a745;')
            stats_row.addWidget(success_label)

        if self.record.failed_count > 0:
            fail_info = f"失败: {self.record.failed_count} 项"
            fail_label = BodyLabel(fail_info)
            fail_label.setStyleSheet('font-size: 14px; color: #dc3545;')
            stats_row.addWidget(fail_label)

        if self.record.skipped_count > 0:
            skip_info = f"跳过: {self.record.skipped_count} 项"
            skip_label = BodyLabel(skip_info)
            skip_label.setStyleSheet('font-size: 14px; color: #666;')
            stats_row.addWidget(skip_label)

        stats_row.addStretch()
        layout.addLayout(stats_row)

        # 已释放空间
        freed_label = BodyLabel(f"已释放: {self._format_size(self.record.freed_size)}")
        freed_label.setStyleSheet('font-size: 16px; color: #007bff; font-weight: 600;')
        layout.addWidget(freed_label)

        return card

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            'pending': '准备中',
            'running': '执行中',
            'completed': '已完成',
            'partial_success': '部分成功',
            'cancelled': '已取消',
            'error': '错误'
        }
        return status_map.get(self.record.status, self.record.status)

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 8
        return f"{size:.1f} TB"


class CleanupHistoryPage(QWidget):
    """清理历史页面

    显示历史清理记录：
- 分页加载
- 过滤搜索
- 统计信息
- 详情查看
- 一键恢复失败项
"""

    # 信号
    record_details_requested = pyqtSignal(object)  # HistoryRecord
    recover_requested = pyqtSignal(object)          # HistoryRecord

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)

        # 组件
        self.recovery_mgr = get_recovery_manager()

        # 数据
        self.history_records: list[HistoryRecord] = []
        self.load_thread: Optional[LoadHistoryThread] = None

        # 过滤状态
        self.current_filter_status = None
        self.current_filter_type = None
        self.current_date_from = None
        self.current_date_to = None

        # 分页
        self.current_page = 0
        self.page_size = 20

        self.init_ui()
        self._load_history()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # ========== 标题栏 ==========
        header = QHBoxLayout()

        icon = IconWidget(FluentIcon.HISTORY)
        icon.setFixedSize(32, 32)
        header.addWidget(icon)

        title = SubtitleLabel("清理历史")
        title.setStyleSheet('font-size: 24px;')
        header.addWidget(title)

        header.addStretch()

        # 刷新按钮
        self.refresh_btn = PushButton(FluentIcon.SYNC, "刷新")
        self.refresh_btn.clicked.connect(self._load_history)
        self.refresh_btn.setFixedHeight(36)
        header.addWidget(self.refresh_btn)

        main_layout.addLayout(header)

        # ========== 过滤工具栏 ==========
        filter_card = SimpleCardWidget()
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(12)

        # 状态过滤
        filter_layout.addWidget(BodyLabel("状态:"))
        self.status_combo = ComboBox()

        filter_layout.addWidget(self.status_combo)

        # 类型过滤
        filter_layout.addWidget(BodyLabel("类型:"))
        self.type_combo = ComboBox()

        filter_layout.addWidget(self.type_combo)

        # 搜索框
        filter_layout.addStretch()
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("搜索计划名称...")
        self.search_edit.setFixedWidth(200)
        filter_layout.addWidget(self.search_edit)

        # 过滤按钮
        self.filter_btn = PushButton("应用")
        self.filter_btn.clicked.connect(self._apply_filters)
        filter_layout.addWidget(self.filter_btn)

        # 重置按钮
        self.reset_btn = PushButton("重置")
        self.reset_btn.clicked.connect(self._reset_filters)
        filter_layout.addWidget(self.reset_btn)

        main_layout.addWidget(filter_card)

        # ========== 统计卡片 ==========
        stats_card = SimpleCardWidget()
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(24)

        # 总计划数
        self.total_plans_label = BodyLabel("0 项")
        self.total_plans_label.setStyleSheet('font-size: 24px; font-weight: 600; color: #333;')
        stats_layout.addWidget(self.total_plans_label)

        # 总清理大小
        self.total_size_label = BodyLabel("0 B")
        self.total_size_label.setStyleSheet('font-size: 18px; color: #666;')
        stats_layout.addWidget(self.total_size_label)

        # 已释放空间
        self.freed_size_label = BodyLabel("0 B")
        self.freed_size_label.setStyleSheet('font-size: 18px; color: #28a745;')
        stats_layout.addWidget(self.freed_size_label)

        stats_layout.addStretch()
        main_layout.addWidget(stats_card)

        # ========== 历史记录列表 ==========
        list_card = SimpleCardWidget()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(12, 12, 12, 12)

        header_row = QHBoxLayout()
        header_label = BodyLabel("历史记录")
        header_row.addWidget(header_label)

        header_row.addStretch()
        list_layout.addLayout(header_row)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.records_container = QWidget()
        self.records_layout = QVBoxLayout(self.records_container)
        self.records_layout.setSpacing(8)
        self.records_layout.addStretch()

        scroll.setWidget(self.records_container)
        list_layout.addWidget(scroll)

        main_layout.addWidget(list_card)

        main_layout.addStretch()

    def _load_history(self, page: int = 0):
        """加载历史记录

        Args:
            page: 页码
        """
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.cancel()
            self.load_thread.wait(1000)

        self.logger.info("[HISTORY] 加载清理历史")

        self.load_thread = LoadHistoryThread(
            limit=self.page_size,
            offset=page * self.page_size,
            status_filter=self.current_filter_status,
            scan_type_filter=self.current_filter_type,
            date_from=self.current_date_from,
            date_to=self.current_date_to
        )

        self.load_thread.completed.connect(self._on_load_completed)
        self.load_thread.error.connect(self._on_load_error)
        self.load_thread.start()

    def _on_load_completed(self, records: list[HistoryRecord]):
        """加载完成回调

        Args:
            records: 历史记录列表
        """
        self.history_records = records

        # 清除现有组件
        for i in reversed(range(self.records_layout.count())):
            widget = self.records_layout.itemAt(i)
            if widget:
                widget.deleteLater()

        # 添加新记录
        for record in self.history_records:
            record_widget = HistoryRecordWidget(record, self)
            self.records_layout.insertWidget(
                self.records_layout.count() - 1,
                record_widget
            )

        # 更新统计
        self._update_stats()

        self.logger.info(f"[HISTORY] 加载完成: {len(records)} 条记录")

    def _on_load_error(self, error_msg: str):
        """加载错误回调

        Args:
            error_msg: 错误消息
        """
        self.logger.error(f"[HISTORY] 加载失败: {error_msg}")
        InfoBar.error("错误", error_msg, parent=self, position=InfoBarPosition.TOP, duration=5000)

    def _update_stats(self):
        """更新统计信息"""
        total_plans = len(self.history_records)
        total_size = sum(r.total_size for r in self.history_records)
        freed_size = sum(r.freed_size for r in self.history_records)

        self.total_plans_label.setText(f"{total_plans} 项")
        self.total_size_label.setText(self._format_size(total_size))
        self.freed_size_label.setText(self._format_size(freed_size))

    def _apply_filters(self):
        """应用过滤器并重新加载"""
        self.current_filter_status = self.status_combo.currentText() if self.status_combo.currentText() else None
        self.current_filter_type = self.type_combo.currentText() if self.type_combo.currentText() else None

        # 处理特殊状态
        if self.current_filter_status == "全部":
            self.current_filter_status = None

        if self.current_filter_type == "全部":
            self.current_filter_type = None

        # 搜索关键词
        keyword = self.search_edit.text().strip()

        # 应用关键词过滤在加载后进行（简化实现）
        # TODO: 可以将搜索逻辑集成到 LoadHistoryThread

        self._load_history(self.current_page)

    def _reset_filters(self):
        """重置过滤器"""
        self.status_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        self.search_edit.clear()
        self.current_filter_status = None
        self.current_filter_type = None
        self._load_history(0)

    def show_record_details(self, record: HistoryRecord):
        """显示记录详情

        Args:
            record: 历史记录
        """
        dialog = HistoryRecordDetailsDialog(record, self)
        dialog.exec()

    def recover_failed_items(self, record: HistoryRecord):
        """恢复失败项

        Args:
            record: 历史记录
        """
        if not record.is_completed:
            InfoBar.warning("提示", "只能恢复已完成的清理记录", parent=self, position=InfoBarPosition.TOP)
            return

        if not record.has_failures:
            InfoBar.info("信息", "该清理记录没有失败项", parent=self, position=InfoBarPosition.TOP)
            return

        # 从恢复管理器恢复失败项
        count = self.recovery_mgr.restore_failed_items(record.plan_id)

        if count > 0:
            InfoBar.success("成功", f"已恢复 {count} 个失败项", parent=self, position=InfoBarPosition.TOP, duration=3000)
        else:
            InfoBar.info("信息", "没有可恢复的失败项", parent=self, position=InfoBarPosition.TOP)

    def _format_size(self, size: int) -> str:
        """格式化大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 8
        return f"{size:.1f} TB"
