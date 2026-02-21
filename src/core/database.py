import sqlite3
import os
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from utils.logger import get_logger


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
