import sqlite3
import os
import threading
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from ..utils.logger import get_logger


class Database:
    """Database manager for scan results caching with thread-safe connections"""

    # Class-level flag for first-time table creation
    _tables_created = False
    _tables_created_lock = threading.Lock()

    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            # Use data directory for database
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(current_dir, '..', '..', 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'cleanmaster.db')

        self.db_path = db_path
        self._tables_created = False
        self.logger = get_logger(__name__)

        # Create tables on first instantiation
        self._create_tables_once()

    def _create_tables_once(self):
        """Create tables only once (thread-safe)"""
        with Database._tables_created_lock:
            if not Database._tables_created:
                try:
                    # Use a temporary connection for table creation
                    conn = sqlite3.connect(self.db_path)
                    conn.row_factory = sqlite3.Row
                    self._create_tables_schema(conn)
                    Database._tables_created = True
                finally:
                    if 'conn' in locals():
                        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection for the current thread

        Uses thread-local storage to store connections, ensuring each thread
        has its own connection.
        """
        if not hasattr(threading.current_thread(), '_db_connection'):
            threading.current_thread()._db_connection = None

        conn = threading.current_thread()._db_connection
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            threading.current_thread()._db_connection = conn
        return conn

    def _create_tables_schema(self, conn: sqlite3.Connection):
        """Create all necessary tables"""
        cursor = conn.cursor()

        # ============================================================================
        # 新增: 智能清理表结构 (Phase 1 Day 1 数据库优化)
        # ============================================================================

        # 原因表（共享，去重）- 用于存储清理原因
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_reasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reason TEXT NOT NULL,
                hash TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                reference_count INTEGER DEFAULT 1
            )
        ''')

        # 清理计划表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_plans (
                plan_id TEXT PRIMARY KEY,
                plan_name TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                scan_target TEXT NOT NULL,
                total_items INTEGER NOT NULL DEFAULT 0,
                total_size INTEGER NOT NULL DEFAULT 0,
                estimated_freed_size INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # 清理项目主表（精简版 - MVP优化）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                path TEXT NOT NULL,
                size INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                original_risk TEXT NOT NULL,
                ai_risk TEXT NOT NULL,
                reason_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id),
                FOREIGN KEY (reason_id) REFERENCES cleanup_reasons (id)
            )
        ''')

        # 执行记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                total_items INTEGER NOT NULL DEFAULT 0,
                success_items INTEGER NOT NULL DEFAULT 0,
                failed_items INTEGER NOT NULL DEFAULT 0,
                skipped_items INTEGER NOT NULL DEFAULT 0,
                total_size INTEGER NOT NULL DEFAULT 0,
                freed_size INTEGER NOT NULL DEFAULT 0,
                failed_size INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id)
            )
        ''')

        # 恢复记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recovery_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                original_path TEXT NOT NULL,
                backup_path TEXT,
                backup_type TEXT NOT NULL,
                restored INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id)
            )
        ''')

        # 清理报告汇总表 (Feature 1: Report Persistence)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT UNIQUE NOT NULL,
                execution_id INTEGER,
                report_summary TEXT NOT NULL,
                report_statistics TEXT NOT NULL,
                report_failures TEXT,
                generated_at TEXT NOT NULL,
                scan_type TEXT,
                total_freed_size INTEGER DEFAULT 0,
                FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id),
                FOREIGN KEY (execution_id) REFERENCES cleanup_executions(execution_id)
            )
        ''')

        # 新表的索引
        self._create_smart_cleanup_indexes(cursor)

        # ============================================================================
        # 原有表结构（保持兼容）
        # ============================================================================

        # Folder scans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folder_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_type TEXT NOT NULL,
                folder_name TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                folder_size INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'suspicious',
                last_modified TEXT NOT NULL,
                file_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(folder_type, folder_path)
            )
        ''')

        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_scan_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                file_type TEXT,
                last_modified TEXT NOT NULL,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (folder_scan_id) REFERENCES folder_scans (id)
            )
        ''')

        # Clean history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clean_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clean_type TEXT NOT NULL,
                items_count INTEGER NOT NULL,
                total_size INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                timestamp_cleaned_at TEXT NOT NULL,
                details TEXT
            )
        ''')

        # AI clean classifications cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT NOT NULL UNIQUE,
                folder_path TEXT,
                risk_level TEXT NOT NULL,
                reason TEXT,
                confidence REAL DEFAULT 0.5,
                cached_at TEXT NOT NULL
            )
        ''')

        # System scan results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                path TEXT NOT NULL,
                size INTEGER NOT NULL DEFAULT 0,
                description TEXT,
                risk_level TEXT NOT NULL DEFAULT 'safe',
                last_scanned TEXT NOT NULL,
                UNIQUE(scan_type, path)
            )
        ''')

        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_folder_scans_type
            ON folder_scans(folder_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_folder_scans_path
            ON folder_scans(folder_path)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_folder_id
            ON files(folder_scan_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_clean_history_timestamp
            ON clean_history(timestamp_cleaned_at)
        ''')

        conn.commit()

    def get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        return datetime.now().isoformat()

    # ==========================================================================
    # 智能清理数据库操作方法 (Phase 1 Day 1 数据库优化)
    # ==========================================================================

    def _create_smart_cleanup_indexes(self, cursor: sqlite3.Cursor):
        """创建智能清理表的索引

        Args:
            cursor: 数据库游标
        """
        indexes = [
            ('idx_cleanup_plans_scan_type', 'cleanup_plans', 'scan_type'),
            ('idx_cleanup_plans_status', 'cleanup_plans', 'status'),
            ('idx_cleanup_items_plan_id', 'cleanup_items', 'plan_id'),
            ('idx_cleanup_items_status', 'cleanup_items', 'status'),
            ('idx_cleanup_items_reason_id', 'cleanup_items', 'reason_id'),
            ('idx_cleanup_executions_plan_id', 'cleanup_executions', 'plan_id'),
            ('idx_cleanup_executions_status', 'cleanup_executions', 'status'),
            ('idx_recovery_log_plan_id', 'recovery_log', 'plan_id'),
            ('idx_cleanup_reasons_hash', 'cleanup_reasons', 'hash'),
            # Cleanup reports indexes
            ('idx_cleanup_reports_plan_id', 'cleanup_reports', 'plan_id'),
            ('idx_cleanup_reports_generated_at', 'cleanup_reports', 'generated_at'),
            ('idx_cleanup_reports_scan_type', 'cleanup_reports', 'scan_type'),
        ]

        for index_name, table, column in indexes:
            cursor.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table} ({column})
            ''')
        self.logger.info(f"[DATABASE] Created {len(indexes)} smart cleanup indexes")

    def _get_or_create_reason_id(
        self,
        conn: sqlite3.Connection,
        reason: str
    ) -> int:
        """获取或创建原因ID（使用提供的连接，不关闭）

        Args:
            conn: 数据库连接
            reason: 原因文本

        Returns:
            原因ID
        """
        cursor = conn.cursor()
        reason_hash = self._get_reason_hash(reason)
        now = self.get_current_timestamp()

        # 查询是否存在
        cursor.execute('''
            SELECT id FROM cleanup_reasons WHERE hash = ?
        ''', (reason_hash,))
        row = cursor.fetchone()

        if row:
            # 已存在，增加引用计数
            reason_id = row[0]
            cursor.execute('''
                UPDATE cleanup_reasons SET reference_count = reference_count + 1
                WHERE id = ?
            ''', (reason_id,))
            return reason_id

        # 不存在，插入新记录
        cursor.execute('''
            INSERT INTO cleanup_reasons (reason, hash, created_at, reference_count)
            VALUES (?, ?, ?, 1)
        ''', (reason, reason_hash, now))
        return cursor.lastrowid

    def add_or_get_reason(self, reason: str) -> int:
        """添加或获取原因ID（去重）

        Args:
            reason: 原因文本

        Returns:
            原因ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        reason_hash = self._get_reason_hash(reason)
        now = self.get_current_timestamp()

        # 查询是否存在
        cursor.execute('''
            SELECT id FROM cleanup_reasons WHERE hash = ?
        ''', (reason_hash,))
        row = cursor.fetchone()

        if row:
            # 已存在，增加引用计数
            reason_id = row[0]
            cursor.execute('''
                UPDATE cleanup_reasons SET reference_count = reference_count + 1
                WHERE id = ?
            ''', (reason_id,))
            conn.commit()
            return reason_id

        # 不存在，插入新记录
        cursor.execute('''
            INSERT INTO cleanup_reasons (reason, hash, created_at, reference_count)
            VALUES (?, ?, ?, 1)
        ''', (reason, reason_hash, now))
        reason_id = cursor.lastrowid
        conn.commit()
        return reason_id

    def _get_reason_hash(self, reason: str) -> str:
        """生成原因的 MD5 哈希

        Args:
            reason: 原因文本

        Returns:
            MD5 哈希字符串
        """
        return hashlib.md5(reason.encode('utf-8')).hexdigest()

    def create_cleanup_plan(
        self,
        plan_id: str,
        plan_name: str,
        scan_type: str,
        scan_target: str
    ) -> bool:
        """创建清理计划

        Args:
            plan_id: 计划ID
            plan_name: 计划名称
            scan_type: 扫描类型
            scan_target: 扫描目标

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = self.get_current_timestamp()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO cleanup_plans
                (plan_id, plan_name, scan_type, scan_target, total_items, total_size,
                 estimated_freed_size, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, 0, 0, 'pending', ?, ?)
            ''', (plan_id, plan_name, scan_type, scan_target, now, now))
            conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"[DATABASE] 创建清理计划失败: {e}")
            return False

    def update_cleanup_plan(
        self,
        plan_id: str,
        total_items: int = None,
        total_size: int = None,
        estimated_freed_size: int = None,
        status: str = None
    ) -> bool:
        """更新清理计划

        Args:
            plan_id: 计划ID
            total_items: 总项目数
            total_size: 总大小
            estimated_freed_size: 预计释放空间
            status: 状态

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if total_items is not None:
            updates.append('total_items = ?')
            params.append(total_items)
        if total_size is not None:
            updates.append('total_size = ?')
            params.append(total_size)
        if estimated_freed_size is not None:
            updates.append('estimated_freed_size = ?')
            params.append(estimated_freed_size)
        if status is not None:
            updates.append('status = ?')
            params.append(status)

        if updates:
            updates.append('updated_at = ?')
            params.append(self.get_current_timestamp())
            params.append(plan_id)

            cursor.execute(f'''
                UPDATE cleanup_plans
                SET {', '.join(updates)}
                WHERE plan_id = ?
            ''', params)
            conn.commit()
            return True

        return False

    def add_cleanup_item(
        self,
        plan_id: str,
        path: str,
        size: int,
        item_type: str,
        original_risk: str,
        ai_risk: str,
        reason: str
    ) -> Optional[int]:
        """添加清理项目

        Args:
            plan_id: 计划ID
            path: 文件/目录路径
            size: 大小
            item_type: 项目类型
            original_risk: 原始风险
            ai_risk: AI评估风险
            reason: 清理原因

        Returns:
            项目ID，失败返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 获取或创建 reason_id（使用同一个连接）
            reason_id = self._get_or_create_reason_id(conn, reason)

            now = self.get_current_timestamp()
            cursor.execute('''
                INSERT INTO cleanup_items
                (plan_id, path, size, item_type, original_risk, ai_risk,
                 reason_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            ''', (plan_id, path, size, item_type, original_risk, ai_risk,
                   reason_id, now, now))
            item_id = cursor.lastrowid

            # 更新计划统计
            cursor.execute('''
                UPDATE cleanup_plans
                SET total_items = total_items + 1,
                    total_size = total_size + ?,
                    updated_at = ?
                WHERE plan_id = ?
            ''', (size, now, plan_id))

            conn.commit()
            return item_id
        except Exception as e:
            self.logger.error(f"[DATABASE] 添加清理项目失败: {e}")
            conn.rollback()
            return None

    def get_cleanup_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取清理计划

        Args:
            plan_id: 计划ID

        Returns:
            计划信息字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM cleanup_plans WHERE plan_id = ?
        ''', (plan_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_cleanup_items(
        self,
        plan_id: str,
        limit: int = 1000,
        offset: int = 0,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """获取清理项目列表

        Args:
            plan_id: 计划ID
            limit: 限制数量
            offset: 偏移量
            status: 状态过滤

        Returns:
            项目列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT ci.*, cr.reason
            FROM cleanup_items ci
            LEFT JOIN cleanup_reasons cr ON ci.reason_id = cr.id
            WHERE ci.plan_id = ?
        '''
        params = [plan_id]

        if status:
            query += ' AND ci.status = ?'
            params.append(status)

        query += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def create_execution(
        self,
        plan_id: str,
        total_items: int = 0,
        total_size: int = 0
    ) -> Optional[int]:
        """创建执行记录

        Args:
            plan_id: 计划ID
            total_items: 总项目数
            total_size: 总大小

        Returns:
            执行ID，失败返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            now = self.get_current_timestamp()
            cursor.execute('''
                INSERT INTO cleanup_executions
                (plan_id, started_at, total_items, total_size, status, created_at)
                VALUES (?, ?, ?, ?, 'running', ?)
            ''', (plan_id, now, total_items, total_size, now))
            execution_id = cursor.lastrowid
            conn.commit()
            return execution_id
        except Exception as e:
            self.logger.error(f"[DATABASE] 创建执行记录失败: {e}")
            return None

    def update_execution(
        self,
        execution_id: int,
        success_items: int = None,
        failed_items: int = None,
        freed_size: int = None,
        status: str = None,
        error_message: str = None
    ) -> bool:
        """更新执行记录

        Args:
            execution_id: 执行ID
            success_items: 成功项目数
            failed_items: 失败项目数
            freed_size: 释放大小
            status: 状态
            error_message: 错误消息

        Returns:
            是否成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if success_items is not None:
            updates.append('success_items = ?')
            params.append(success_items)
        if failed_items is not None:
            updates.append('failed_items = ?')
            params.append(failed_items)
        if freed_size is not None:
            updates.append('freed_size = ?')
            params.append(freed_size)
        if status is not None:
            updates.append('status = ?')
            params.append(status)
        if error_message is not None:
            updates.append('error_message = ?')
            params.append(error_message)

        if updates:
            params.append(execution_id)
            cursor.execute(f'''
                UPDATE cleanup_executions
                SET {', '.join(updates)}, completed_at = ?
                WHERE execution_id = ?
            ''', params + [self.get_current_timestamp()])
            conn.commit()
            return True

        return False

    def add_recovery_log(
        self,
        plan_id: str,
        item_id: int,
        original_path: str,
        backup_path: str = None,
        backup_type: str = 'none'
    ) -> Optional[int]:
        """添加恢复记录

        Args:
            plan_id: 计划ID
            item_id: 清理项目ID
            original_path: 原始路径
            backup_path: 备份路径
            backup_type: 备份类型

        Returns:
            记录ID，失败返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            now = self.get_current_timestamp()
            cursor.execute('''
                INSERT INTO recovery_log
                (plan_id, item_id, original_path, backup_path, backup_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (plan_id, item_id, original_path, backup_path, backup_type, now))
            log_id = cursor.lastrowid
            conn.commit()
            return log_id
        except Exception as e:
            self.logger.error(f"[DATABASE] 添加恢复记录失败: {e}")
            return None

    # ==========================================================================
    # 清理报告数据库操作方法 (Feature 1: Report Persistence)
    # ==========================================================================

    def save_cleanup_report(self, plan_id: str, report_data: Dict) -> Optional[int]:
        """保存清理报告到数据库

        Args:
            plan_id: 清理计划ID
            report_data: 报告数据字典，包含 summary, statistics, failures 等

        Returns:
            报告ID，失败返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            now = self.get_current_timestamp()

            # 序列化报告数据为 JSON
            summary_json = json.dumps(report_data.get('summary', {}), ensure_ascii=False)
            statistics_json = json.dumps(report_data.get('statistics', {}), ensure_ascii=False)
            failures_json = json.dumps(report_data.get('failures', []), ensure_ascii=False)

            # 获取扫描类型
            scan_type = report_data.get('summary', {}).get('scan_type')
            total_freed_size = report_data.get('summary', {}).get('freed_size_bytes', 0)

            cursor.execute('''
                INSERT OR REPLACE INTO cleanup_reports
                (plan_id, report_summary, report_statistics, report_failures,
                 generated_at, scan_type, total_freed_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (plan_id, summary_json, statistics_json, failures_json,
                  now, scan_type, total_freed_size))

            report_id = cursor.lastrowid
            conn.commit()

            self.logger.info(f"[DATABASE] 报告已保存: report_id={report_id}, plan_id={plan_id}")
            return report_id

        except Exception as e:
            self.logger.error(f"[DATABASE] 保存报告失败: {e}")
            conn.rollback()
            return None

    def get_cleanup_report(self, report_id: int = None, plan_id: str = None) -> Optional[Dict[str, Any]]:
        """获取清理报告

        Args:
            report_id: 报告ID (如果为 None，则使用 plan_id 查询)
            plan_id: 计划ID (如果 report_id 为 None 时使用)

        Returns:
            报告数据字典，失败返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if report_id:
                cursor.execute('''
                    SELECT * FROM cleanup_reports WHERE report_id = ?
                ''', (report_id,))
            elif plan_id:
                cursor.execute('''
                    SELECT * FROM cleanup_reports WHERE plan_id = ?
                ''', (plan_id,))
            else:
                return None

            row = cursor.fetchone()
            if not row:
                return None

            # 解析 JSON 数据
            report = dict(row)
            if isinstance(report.get('report_summary'), str):
                report['report_summary'] = json.loads(report['report_summary'])
            if isinstance(report.get('report_statistics'), str):
                report['report_statistics'] = json.loads(report['report_statistics'])
            if isinstance(report.get('report_failures'), str):
                report['report_failures'] = json.loads(report['report_failures'])

            return report

        except Exception as e:
            self.logger.error(f"[DATABASE] 获取报告失败: {e}")
            return None

    def get_cleanup_reports(
        self,
        limit: int = 50,
        offset: int = 0,
        scan_type: str = None
    ) -> List[Dict[str, Any]]:
        """获取清理报告列表

        Args:
            limit: 限制数量
            offset: 偏移量
            scan_type: 扫描类型过滤

        Returns:
            报告列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = '''
                SELECT report_id, plan_id, generated_at, scan_type, total_freed_size,
                       report_summary, report_statistics, report_failures
                FROM cleanup_reports
            '''
            params = []

            if scan_type:
                query += ' WHERE scan_type = ?'
                params.append(scan_type)

            query += ' ORDER BY generated_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            reports = []
            for row in rows:
                report = dict(row)
                # 解析 JSON 数据
                if isinstance(report.get('report_summary'), str):
                    report['report_summary'] = json.loads(report['report_summary'])
                if isinstance(report.get('report_statistics'), str):
                    report['report_statistics'] = json.loads(report['report_statistics'])
                if isinstance(report.get('report_failures'), str):
                    report['report_failures'] = json.loads(report['report_failures'])
                reports.append(report)

            return reports

        except Exception as e:
            self.logger.error(f"[DATABASE] 获取报告列表失败: {e}")
            return []

    def get_cleanup_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """获取清理项目

        Args:
            item_id: 项目ID

        Returns:
            项目数据字典，失败返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT ci.*, cr.reason
                FROM cleanup_items ci
                LEFT JOIN cleanup_reasons cr ON ci.reason_id = cr.id
                WHERE ci.id = ?
            ''', (item_id,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

        except Exception as e:
            self.logger.error(f"[DATABASE] 获取清理项目失败: {e}")
            return None

    def get_reports_summary_stats(self) -> Dict[str, Any]:
        """获取报告统计摘要

        Returns:
            统计摘要字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 总报告数
            cursor.execute('SELECT COUNT(*) as total FROM cleanup_reports')
            total_count = cursor.fetchone()['total']

            # 总释放空间
            cursor.execute('SELECT SUM(total_freed_size) as total_freed FROM cleanup_reports')
            total_freed = cursor.fetchone()['total_freed'] or 0

            # 按扫描类型统计
            cursor.execute('''
                SELECT scan_type, COUNT(*) as count, SUM(total_freed_size) as freed
                FROM cleanup_reports
                GROUP BY scan_type
                ORDER BY count DESC
            ''')
            by_type = {row['scan_type'] or 'unknown': {
                'count': row['count'],
                'freed': row['freed'] or 0
            } for row in cursor.fetchall()}

            # 最近一周报告数
            import datetime
            week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM cleanup_reports
                WHERE generated_at > ?
            ''', (week_ago,))
            recent_count = cursor.fetchone()['count']

            return {
                'total_reports': total_count,
                'total_freed_size': total_freed,
                'by_type': by_type,
                'recent_reports': recent_count
            }

        except Exception as e:
            self.logger.error(f"[DATABASE] 获取报告统计失败: {e}")
            return {
                'total_reports': 0,
                'total_freed_size': 0,
                'by_type': {},
                'recent_reports': 0
            }


    # ==========================================================================
    # 原有数据库操作方法（保持兼容）
    # ==========================================================================

    # Folder scan operations
    def upsert_folder_scan(self, folder_type: str, folder_name: str,
                          folder_path: str, folder_size: int,
                          risk_level: str = 'suspicious',
                          file_count: int = 0,
                          last_modified: str = None) -> int:
        """Insert or update folder scan record"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if last_modified is None:
            last_modified = self.get_current_timestamp()

        now = self.get_current_timestamp()

        cursor.execute('''
            INSERT OR REPLACE INTO folder_scans
            (folder_type, folder_name, folder_path, folder_size, risk_level,
             last_modified, file_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (folder_type, folder_name, folder_path, folder_size, risk_level,
               last_modified, file_count, now, now))

        conn.commit()
        return cursor.lastrowid

    def get_folder_scan(self, folder_type: str, folder_path: str) -> Optional[Dict[str, Any]]:
        """Get folder scan record"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM folder_scans
            WHERE folder_type = ? AND folder_path = ?
        ''', (folder_type, folder_path))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_folder_scans(self, folder_type: str = None,
                             risk_level: str = None) -> List[Dict[str, Any]]:
        """Get all folder scan records, optionally filtered"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM folder_scans WHERE 1=1'
        params = []

        if folder_type:
            query += ' AND folder_type = ?'
            params.append(folder_type)

        if risk_level:
            query += ' AND risk_level = ?'
            params.append(risk_level)

        query += ' ORDER BY folder_size DESC'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def delete_folder_scan(self, folder_type: str, folder_path: str) -> bool:
        """Delete folder scan record"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM folder_scans
            WHERE folder_type = ? AND folder_path = ?
        ''', (folder_type, folder_path))

        conn.commit()
        return cursor.rowcount > 0

    # System scan operations
    def upsert_system_scan(self, scan_type: str, path: str, size: int,
                          description: str = None,
                          risk_level: str = 'safe') -> int:
        """Insert or update system scan record"""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = self.get_current_timestamp()

        cursor.execute('''
            INSERT OR REPLACE INTO system_scans
            (scan_type, path, size, description, risk_level, last_scanned)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (scan_type, path, size, description, risk_level, now))

        conn.commit()
        return cursor.lastrowid

    def get_system_scans(self, scan_type: str = None) -> List[Dict[str, Any]]:
        """Get system scan records"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if scan_type:
            cursor.execute('''
                SELECT * FROM system_scans
                WHERE scan_type = ?
                ORDER BY size DESC
            ''', (scan_type,))
        else:
            cursor.execute('''
                SELECT * FROM system_scans
                ORDER BY size DESC
            ''')

        return [dict(row) for row in cursor.fetchall()]

    def delete_system_scan(self, scan_type: str, path: str) -> bool:
        """Delete system scan record"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM system_scans
            WHERE scan_type = ? AND path = ?
        ''', (scan_type, path))

        conn.commit()
        return cursor.rowcount > 0

    # Clean history operations
    def add_clean_history(self, clean_type: str, items_count: int,
                         total_size: int, duration_ms: int,
                         details: Dict[str, Any] = None) -> int:
        """Add clean history record"""
        conn = self._get_connection()
        cursor = conn.cursor()

        details_json = json.dumps(details) if details else None
        timestamp = self.get_current_timestamp()

        self.logger.info(f"[DB:CLEAN_HISTORY] 添加记录: type={clean_type}, count={items_count}, size={total_size}, time={timestamp}")

        cursor.execute('''
            INSERT INTO clean_history
            (clean_type, items_count, total_size, duration_ms,
             timestamp_cleaned_at, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (clean_type, items_count, total_size, duration_ms,
               timestamp, details_json))

        conn.commit()
        row_id = cursor.lastrowid
        self.logger.debug(f"[DB:CLEAN_HISTORY] 记录添加成功，ID: {row_id}")
        return row_id

    def get_clean_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get clean history records"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM clean_history
            ORDER BY timestamp_cleaned_at DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    # AI classification operations
    def upsert_ai_classification(self, folder_name: str, folder_path: str = None,
                                 risk_level: str = 'suspicious',
                                 reason: str = None,
                                 confidence: float = 0.5) -> int:
        """Insert or update AI classification record"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO ai_classifications
            (folder_name, folder_path, risk_level, reason, confidence, cached_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (folder_name, folder_path, risk_level, reason,
               confidence, self.get_current_timestamp()))

        conn.commit()
        return cursor.lastrowid

    def get_ai_classification(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """Get AI classification record"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM ai_classifications
            WHERE folder_name = ?
        ''', (folder_name,))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}

        # Folder scan counts by risk level
        cursor.execute('''
            SELECT risk_level, COUNT(*) as count, SUM(folder_size) as total_size
            FROM folder_scans
            GROUP BY risk_level
        ''')
        stats['folder_scans'] = {
            row['risk_level']: {
                'count': row['count'],
                'total_size': row['total_size']
            }
            for row in cursor.fetchall()
        }

        # Clean history count
        cursor.execute('SELECT COUNT(*) as count FROM clean_history')
        stats['clean_history_count'] = cursor.fetchone()['count']

        # Total cleaned size (mapped to total_freed_space for dashboard)
        cursor.execute('SELECT SUM(total_size) as total FROM clean_history')
        result = cursor.fetchone()
        stats['total_freed_space'] = result['total'] or 0

        # Total items cleaned (mapped to total_cleaned_files)
        cursor.execute('SELECT SUM(items_count) as total FROM clean_history')
        result = cursor.fetchone()
        stats['total_cleaned_files'] = result['total'] or 0

        # Total scan count (clean history count)
        stats['total_scan_count'] = stats['clean_history_count']

        # AI classification count for cache stats
        cursor.execute('SELECT COUNT(*) as count FROM ai_classifications')
        stats['ai_classification_count'] = cursor.fetchone()['count']

        return stats

    def get_recent_cleans(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent clean history records

        Args:
            limit: Maximum number of records to return

        Returns:
            List of clean history records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM clean_history
            ORDER BY timestamp_cleaned_at DESC
            LIMIT ?
        ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def clear_old_cache(self, days: int = 30):
        """Clear old cached data"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() -
                      datetime.timedelta(days=days)).isoformat()

        cursor.execute('''
            DELETE FROM ai_classifications
            WHERE cached_at < ?
        ''', (cutoff_date,))

        conn.commit()

    def close(self):
        """Close the current thread's database connection"""
        if hasattr(threading.current_thread(), '_db_connection'):
            conn = threading.current_thread()._db_connection
            if conn:
                conn.close()
                threading.current_thread()._db_connection = None


# Singleton instance
_db_instance: Optional[Database] = None
_db_lock = threading.Lock()


def get_database() -> Database:
    """Get database singleton instance (thread-safe)"""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = Database()
    return _db_instance


def close_database():
    """Close all database connections"""
    global _db_instance
    with _db_lock:
        if _db_instance is not None:
            # Close the singleton's connection
            _db_instance.close()
            _db_instance = None
