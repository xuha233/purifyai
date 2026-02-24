"""
数据库迁移脚本 - MVP v1.1 数据库优化

根据 01_MVP实施计划_v1.1.md 的数据库优化方案：

问题1修复 - 数据库冗余:
- 分离大字段 (reason) 到 reasons 表
- 使用原因表共享去重 (MD5 hash)
- 主表存储路径、大小、风险等级

新表结构:
1. cleanup_items (主表)
2. cleanup_reasons (原因表，共享，去重)
3. cleanup_plans
4. cleanup_executions
5. recovery_log
"""
import sqlite3
import os
import hashlib
from typing import Optional
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseMigration:
    """数据库迁移管理类"""

    def __init__(self, db_path: str = None):
        """初始化迁移管理器

        Args:
            db_path: 数据库路径
        """
        if db_path is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(current_dir, '..', '..', 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'cleanmaster.db')

        self.db_path = db_path
        self.logger = logger

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_reason_hash(self, reason: str) -> str:
        """生成原因的 MD5 哈希

        Args:
            reason: 原因文本

        Returns:
            MD5 哈希字符串
        """
        return hashlib.md5(reason.encode('utf-8')).hexdigest()

    def run_migrations(self) -> bool:
        """运行所有迁移

        Returns:
            是否成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 检查是否需要迁移
            current_version = self._get_schema_version(cursor)
            if current_version >= 2:
                self.logger.info(f"[DB_MIGRATION] 数据库版本 {current_version}，无需迁移")
                conn.close()
                return True

            self.logger.info(f"[DB_MIGRATION] 开始迁移数据库 (版本 {current_version} -> 2)")

            # 执行迁移
            self._create_cleanup_reasons_table(cursor)
            self._create_cleanup_plans_table(cursor)
            self._create_cleanup_items_table(cursor)
            self._create_cleanup_executions_table(cursor)
            self._create_recovery_log_table(cursor)

            # 创建索引
            self._create_indexes(cursor)

            # 更新版本号
            self._update_schema_version(cursor, version=2)

            conn.commit()
            conn.close()

            self.logger.info("[DB_MIGRATION] 数据库迁移完成")
            return True

        except Exception as e:
            self.logger.error(f"[DB_MIGRATION] 迁移失败: {e}", exc_info=True)
            return False

    def _get_schema_version(self, cursor: sqlite3.Cursor) -> int:
        """获取数据库模式版本

        Args:
            cursor: 数据库游标

        Returns:
            版本号
        """
        cursor.execute('''
            SELECT value FROM settings WHERE key = 'schema_version'
        ''')
        row = cursor.fetchone()
        if row:
            return int(row['value'])
        return 1  # 默认版本

    def _update_schema_version(self, cursor: sqlite3.Cursor, version: int):
        """更新数据库模式版本

        Args:
            cursor: 数据库游标
            version: 新版本号
        """
        # 首先创建 settings 表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # 更新版本号
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES ('schema_version', ?, ?)
        ''', (str(version), now))

    def _create_cleanup_reasons_table(self, cursor: sqlite3.Cursor):
        """创建原因表（共享，去重）

        Args:
            cursor: 数据库游标

        通过 MD5 hash 实现去重，相同的 reason 只存储一次
        """
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_reasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reason TEXT NOT NULL,
                hash TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                reference_count INTEGER DEFAULT 1
            )
        ''')
        self.logger.info("[DB_MIGRATION] 表 cleanup_reasons 已创建")

    def _create_cleanup_plans_table(self, cursor: sqlite3.Cursor):
        """创建清理计划表

        Args:
            cursor: 数据库游标
        """
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
        self.logger.info("[DB_MIGRATION] 表 cleanup_plans 已创建")

    def _create_cleanup_items_table(self, cursor: sqlite3.Cursor):
        """创建清理项目主表（精简版）

        Args:
            cursor: 数据库游标

        精简设计:
        - 仅存储路径、大小、类型等基础信息
        - reason 通过 reason_id 关联到 reasons 表
        - 大字段（完整原因）不在此表存储
        """
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
        self.logger.info("[DB_MIGRATION] 表 cleanup_items 已创建")

    def _create_cleanup_executions_table(self, cursor: sqlite3.Cursor):
        """创建执行记录表

        Args:
            cursor: 数据库游标
        """
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
        self.logger.info("[DB_MIGRATION] 表 cleanup_executions 已创建")

    def _create_recovery_log_table(self, cursor: sqlite3.Cursor):
        """创建恢复记录表

        Args:
            cursor: 数据库游标
        """
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
        self.logger.info("[DB_MIGRATION] 表 recovery_log 已创建")

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """创建索引以提升查询性能

        Args:
            cursor: 数据库游标
        """
        indexes = [
            # cleanup_plans 索引
            ('idx_cleanup_plans_scan_type', 'cleanup_plans', 'scan_type'),
            ('idx_cleanup_plans_status', 'cleanup_plans', 'status'),

            # cleanup_items 索引
            ('idx_cleanup_items_plan_id', 'cleanup_items', 'plan_id'),
            ('idx_cleanup_items_status', 'cleanup_items', 'status'),
            ('idx_cleanup_items_reason_id', 'cleanup_items', 'reason_id'),

            # cleanup_executions 索引
            ('idx_cleanup_executions_plan_id', 'cleanup_executions', 'plan_id'),
            ('idx_cleanup_executions_status', 'cleanup_executions', 'status'),

            # recovery_log 索引
            ('idx_recovery_log_plan_id', 'recovery_log', 'plan_id'),
            ('idx_recovery_log_restored', 'recovery_log', 'restored'),

            # cleanup_reasons 索引
            ('idx_cleanup_reasons_hash', 'cleanup_reasons', 'hash'),
        ]

        for index_name, table, column in indexes:
            cursor.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {table} ({column})
            ''')

        self.logger.info(f"[DB_MIGRATION] 创建了 {len(indexes)} 个索引")

    # ----------------------------------------------------------------------
    # 数据操作方法
    # ----------------------------------------------------------------------

    def add_or_get_reason(self, reason: str) -> int:
        """添加或获取原因ID

        Args:
            reason: 原因文本

        Returns:
            原因ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        reason_hash = self._get_reason_hash(reason)
        now = datetime.now().isoformat()

        # 查询是否存在
        cursor.execute('''
            SELECT id FROM cleanup_reasons WHERE hash = ?
        ''', (reason_hash,))
        row = cursor.fetchone()

        if row:
            # 已存在，增加引用计数
            reason_id = row['id']
            cursor.execute('''
                UPDATE cleanup_reasons SET reference_count = reference_count + 1
                WHERE id = ?
            ''', (reason_id,))
            conn.commit()
            conn.close()
            return reason_id

        # 不存在，插入新记录
        cursor.execute('''
            INSERT INTO cleanup_reasons (reason, hash, created_at, reference_count)
            VALUES (?, ?, ?, 1)
        ''', (reason, reason_hash, now))
        reason_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reason_id

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
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        try:
            cursor.execute('''
                INSERT INTO cleanup_plans
                (plan_id, plan_name, scan_type, scan_target, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (plan_id, plan_name, scan_type, scan_target, now, now))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"[DB_MIGRATION] 创建清理计划失败: {e}")
            conn.close()
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
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 获取或创建 reason_id
            reason_id = self.add_or_get_reason(reason)

            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO cleanup_items
                (plan_id, path, size, item_type, original_risk, ai_risk, reason_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (plan_id, path, size, item_type, original_risk, ai_risk, reason_id, now, now))
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
            conn.close()
            return item_id
        except Exception as e:
            self.logger.error(f"[DB_MIGRATION] 添加清理项目失败: {e}")
            conn.rollback()
            conn.close()
            return None

    def get_cleanup_plan(self, plan_id: str) -> Optional[dict]:
        """获取清理计划

        Args:
            plan_id: 计划ID

        Returns:
            计划信息字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM cleanup_plans WHERE plan_id = ?
        ''', (plan_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_cleanup_items(self, plan_id: str, limit: int = 1000) -> list:
        """获取清理项目列表

        Args:
            plan_id: 计划ID
            limit: 限制数量

        Returns:
            项目列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT ci.*, cr.reason
            FROM cleanup_items ci
            LEFT JOIN cleanup_reasons cr ON ci.reason_id = cr.id
            WHERE ci.plan_id = ?
            LIMIT ?
        ''', (plan_id, limit))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]


# 测试函数
def test_migration():
    """测试数据库迁移"""
    print("[TEST] 开始测试数据库迁移...")

    # 创建临时数据库测试
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_db_path = os.path.join(current_dir, '..', '..', 'data', 'test_migration.db')

    # 删除旧测试数据库
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    migration = DatabaseMigration(test_db_path)

    # 运行迁移
    success = migration.run_migrations()
    if success:
        print("[TEST] 迁移成功")

        # 测试创建清理计划
        plan_id = f"test_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        migration.create_cleanup_plan(
            plan_id=plan_id,
            plan_name="测试计划",
            scan_type="system",
            scan_target="C:/Temp"
        )
        print(f"[TEST] 创建清理计划: {plan_id}")

        # 测试添加清理项目
        item_id = migration.add_cleanup_item(
            plan_id=plan_id,
            path="C:/Temp/test.txt",
            size=1024,
            item_type="file",
            original_risk="safe",
            ai_risk="safe",
            reason="临时文件，可以直接删除"
        )
        print(f"[TEST] 添加清理项目: {item_id}")

        # 测试查询
        plan = migration.get_cleanup_plan(plan_id)
        print(f"[TEST] 查询计划: {plan['plan_name']}, 项目数: {plan['total_items']}")

        items = migration.get_cleanup_items(plan_id)
        print(f"[TEST] 查询项目: {len(items)} 个")

        # 清理测试数据库
        os.remove(test_db_path)
        print("[TEST] 测试完成，清理测试数据库")
    else:
        print("[TEST] 迁移失败")


if __name__ == "__main__":
    test_migration()
