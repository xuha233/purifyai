"""
批注存储层 - SQLite实现
"""
import sqlite3
import os
import json
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from core.annotation import ScanAnnotation, AssessmentMethod, generate_annotation_id


class AnnotationStorage:
    """批注存储接口"""

    def __init__(self, db_path: str = None):
        """初始化存储

        Args:
            db_path: 数据库文件路径，默认放在用户数据目录
        """
        if db_path is None:
            data_dir = Path.home() / '.purifyai'
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / 'annotations.db'

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        # 确保父目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # 批注表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    item_path TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    scan_timestamp TEXT NOT NULL,

                    -- 文件信息
                    file_size INTEGER DEFAULT 0,
                    file_name TEXT DEFAULT '',
                    file_extension TEXT DEFAULT '',

                    -- 风险评估
                    risk_level TEXT NOT NULL,
                    risk_score INTEGER DEFAULT 50,
                    confidence REAL DEFAULT 0.5,

                    -- 评估来源
                    assessment_method TEXT NOT NULL,
                    assessment_source TEXT,
                    assessment_details TEXT,

                    -- 批注核心
                    annotation_note TEXT DEFAULT '',
                    annotation_tags TEXT DEFAULT '',
                    recommendation TEXT DEFAULT '',

                    -- 置信度相关
                    ai_confidence REAL DEFAULT 0.5,
                    rule_match_count INTEGER DEFAULT 0,

                    -- 缓存
                    cache_hit BOOLEAN DEFAULT 0,
                    cache_key TEXT,
                    cache_ttl INTEGER,

                    -- 元数据
                    last_modified TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),

                    -- 用户标记
                    user_reviewed BOOLEAN DEFAULT 0,
                    user_safe_confirmed,

                    -- 关联
                    scan_source,
                    parent_scan_id TEXT,

                    -- 全文搜索索引
                    item_path_to_index TEXT,
                    annotation_to_index TEXT
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_level ON annotations(risk_level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assessment_method ON annotations(assessment_method)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON annotations(scan_timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_reviewed ON annotations(user_reviewed)")

            # FTS 表用于全文搜索
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS annotations_fts
                USING FTS5(item_path_to_index, annotation_to_index, content='', tokenize='unicode61')
            """)

            # 修复的触发器：使用 INSERT OR REPLACE 而不是 UPDATE
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS annotations_fts_insert
                AFTER INSERT ON annotations BEGIN
                    INSERT OR REPLACE INTO annotations_fts(rowid, item_path_to_index, annotation_to_index)
                    VALUES (
                        (SELECT rowid FROM annotations_fts WHERE rowid = new.rowid),
                        new.item_path || ' ' || new.file_name,
                        new.annotation_note
                    )
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS annotations_fts_delete
                AFTER DELETE ON annotations BEGIN
                    DELETE FROM annotations_fts WHERE rowid = old.rowid
                END
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS annotations_fts_update_old
                AFTER UPDATE ON annotations BEGIN
                    UPDATE annotations_fts SET
                        item_path_to_index = new.item_path || ' ' || new.file_name,
                        annotation_to_index = new.annotation_note
                    WHERE rowid = new.rowid
                END
            """)

            conn.commit()

    def save_annotation(self, annotation: ScanAnnotation) -> bool:
        """保存批注

        Returns:
            bool: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # 更新时间戳
                import datetime
                annotation.updated_at = datetime.datetime.now().isoformat()

                conn.execute("""
                    INSERT OR REPLACE INTO annotations (
                        id, item_path, item_type, scan_timestamp,

                        file_size, file_name, file_extension,

                        risk_level, risk_score, confidence,

                        assessment_method, assessment_source, assessment_details,

                        annotation_note, annotation_tags, recommendation,

                        ai_confidence, rule_match_count,

                        cache_hit, cache_key, cache_ttl,

                        last_modified, updated_at,

                        user_reviewed, user_safe_confirmed,

                        scan_source, parent_scan_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    annotation.id,
                    annotation.item_path,
                    annotation.item_type,
                    annotation.scan_timestamp,

                    annotation.file_size,
                    annotation.file_name,
                    annotation.file_extension,

                    annotation.risk_level,
                    annotation.risk_score,
                    annotation.confidence,

                    annotation.assessment_method,
                    annotation.assessment_source,
                    annotation.assessment_details,

                    annotation.annotation_note,
                    '|'.join(annotation.annotation_tags),
                    annotation.recommendation,

                    annotation.ai_confidence,
                    annotation.rule_match_count,

                    annotation.cache_hit,
                    annotation.cache_key,
                    annotation.cache_ttl,

                    annotation.last_modified,
                    annotation.updated_at,

                    int(annotation.user_reviewed),
                    annotation.user_safe_confirmed,

                    annotation.scan_source,
                    annotation.parent_scan_id,
                ))
                conn.commit()

            return True

        except Exception as e:
            import logging
            logging.error(f"保存批注失败: {e}")
            return False

    def get_annotation(self, item_path: str) -> Optional[ScanAnnotation]:
        """根据路径获取批注

        Args:
            item_path: 文件路径

        Returns:
            批注对象或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cur = conn.execute("""
                    SELECT * FROM annotations WHERE item_path = ?
                """, (item_path,))

                row = cur.fetchone()
                if row:
                    tags = row['annotation_tags'].split('|') if row['annotation_tags'] else []

                    note = ScanAnnotation(
                        id=row['id'],
                        item_path=row['item_path'],
                        item_type=row['item_type'],
                        scan_timestamp=row['scan_timestamp'],

                        file_size=row['file_size'],
                        file_name=row['file_name'],
                        file_extension=row['file_extension'],

                        risk_level=row['risk_level'],
                        risk_score=row['risk_score'],
                        confidence=row['confidence'],

                        assessment_method=row['assessment_method'],
                        assessment_source=row['assessment_source'],
                        assessment_details=row['assessment_details'],

                        annotation_note=row['annotation_note'],
                        annotation_tags=tags,

                        recommendation=row['recommendation'],

                        ai_confidence=row['ai_confidence'],
                        rule_match_count=row['rule_match_count'],

                        cache_hit=bool(row['cache_hit']),
                        cache_key=row['cache_key'],
                        cache_ttl=row['cache_ttl'],

                        last_modified=row['last_modified'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],

                        user_reviewed=bool(row['user_reviewed']),
                        user_safe_confirmed=row['user_safe_confirmed'],

                        scan_source=row['scan_source'],
                        parent_scan_id=row['parent_scan_id'],
                    )

                    return note
                return None

        except Exception as e:
            import logging
            logging.error(f"获取批注失败: {e}")
            return None

    def get_batch_annotations(self, paths: List[str]) -> dict:
        """批量获取批注

        Args:
            paths: 文件路径列表

        Returns:
            {路径: 批注对象}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                placeholders = ','.join(['?' for _ in paths])
                query = f"SELECT * FROM annotations WHERE item_path IN ({placeholders})"

                cur = conn.execute(query, paths)
                results = cur.fetchall()

            notes_dict = {}
            for row in results:
                tags = row['annotation_tags'].split('|') if row['annotation_tags'] else []

                note = ScanAnnotation(
                    id=row['id'],
                    item_path=row['item_path'],
                    item_type=row['item_type'],
                    scan_timestamp=row['scan_timestamp'],

                    file_size=row['file_size'],
                    file_name=row['file_name'],
                    file_extension=row['file_extension'],

                    risk_level=row['risk_level'],
                    risk_score=row['risk_score'],
                    confidence=row['confidence'],

                    assessment_method=row['assessment_method'],
                    assessment_source=row['assessment_source'],
                    assessment_details=row['assessment_details'],

                    annotation_note=row['annotation_note'],
                    annotation_tags=tags,

                    recommendation=row['recommendation'],

                    ai_confidence=row['ai_confidence'],
                    rule_match_count=row['rule_match_count'],

                    cache_hit=bool(row['cache_hit']),
                    cache_key=row['cache_key'],
                    cache_ttl=row['cache_ttl'],

                    last_modified=row['last_modified'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],

                    user_reviewed=bool(row['user_reviewed']),
                    user_safe_confirmed=row['user_safe_confirmed'],

                    scan_source=row['scan_source'],
                    parent_scan_id=row['parent_scan_id'],
                )

                notes_dict[row['item_path']] = note

            return notes_dict

        except Exception as e:
            import logging
            logging.error(f"批量获取批注失败: {e}")
            return {}

    def delete_annotation(self, annotation_id: str) -> bool:
        """删除批注

        Args:
            annotation_id: 批注ID

        Returns:
            bool: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
                conn.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"删除批注失败: {e}")
            return False

    def list_annotations(self, filters: dict = None) -> List[ScanAnnotation]:
        """查询批注列表

        Args:
            filters: 过滤条件，支持:
                - risk_level: 风险等级列表
                - assessment_method: 评估方法
                - scan_source: 扫描来源
                - user_reviewed: 用户已审核
                - cache_hit: 缓存命中
                - limit: 限制数量
                - offset: 偏移量

        Returns:
            批注列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                query = "SELECT * FROM annotations WHERE 1=1"
                params = []

                if filters:
                    if 'risk_levels' in filters and filters['risk_levels']:
                        placeholders = ','.join(['?' for _ in filters['risk_levels']])
                        query += f" AND risk_level IN ({placeholders})"
                        params.extend(filters['risk_levels'])

                    if 'assessment_methods' in filters:
                        placeholders = ','.join(['?' for _ in filters['assessment_methods']])
                        query += f" AND assessment_method IN ({placeholders})"
                        params.extend(filters['assessment_methods'])

                    if 'scan_source' in filters and filters['scan_source']:
                        query += " AND scan_source = ?"
                        params.append(filters['scan_source'])

                    if 'user_reviewed' in filters:
                        query += " AND user_reviewed = ?"
                        params.append(int(filters['user_reviewed']))

                    if 'cache_hit' in filters:
                        query += " AND cache_hit = ?"
                        params.append(int(filters['cache_hit']))

                    # 排序
                    query += " ORDER BY scan_timestamp DESC"

                    # 限制
                    if 'limit' in filters:
                        query += " LIMIT ?"
                        params.append(filters['limit'])

                    if 'offset' in filters:
                        query += " OFFSET ?"
                        params.append(filters['offset'])

                cur = conn.execute(query, params)
                rows = cur.fetchall()

            results = []
            for row in rows:
                tags = row['annotation_tags'].split('|') if row['annotation_tags'] else []

                note = ScanAnnotation(
                    id=row['id'],
                    item_path=row['item_path'],
                    item_type=row['item_type'],
                    scan_timestamp=row['scan_timestamp'],

                    file_size=row['file_size'],
                    file_name=row['file_name'],
                    file_extension=row['file_extension'],

                    risk_level=row['risk_level'],
                    risk_score=row['risk_score'],
                    confidence=row['confidence'],

                    assessment_method=row['assessment_method'],
                    assessment_source=row['assessment_source'],
                    assessment_details=row['assessment_details'],

                    annotation_note=row['annotation_note'],
                    annotation_tags=tags,

                    recommendation=row['recommendation'],

                    ai_confidence=row['ai_confidence'],
                    rule_match_count=row['rule_match_count'],

                    cache_hit=bool(row['cache_hit']),
                    cache_key=row['cache_key'],
                    cache_ttl=row['cache_ttl'],

                    last_modified=row['last_modified'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],

                    user_reviewed=bool(row['user_reviewed']),
                    user_safe_confirmed=row['user_safe_confirmed'],

                    scan_source=row['scan_source'],
                    parent_scan_id=row['parent_scan_id'],
                )

                results.append(note)

            return results

        except Exception as e:
            import logging
            logging.error(f"查询批注列表失败: {e}")
            return []

    def search_annotations(self, keyword: str, limit: int = 50) -> List[ScanAnnotation]:
        """搜索批注

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的批注列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT annotations.*
                    FROM annotations
                    JOIN annotations_fts ON annotations.rowid = annotations_fts.rowid
                    WHERE annotations_fts MATCH ?
                    ORDER BY scan_timestamp DESC
                    LIMIT ?
                """

                cur = conn.execute(query, (keyword, limit))
                rows = cur.fetchall()

            results = []
            for row in rows:
                tags = row['annotation_tags'].split('|') if row['annotation_tags'] else []

                note = ScanAnnotation(
                    id=row['id'],
                    item_path=row['item_path'],
                    item_type=row['item_type'],
                    scan_timestamp=row['scan_timestamp'],

                    file_size=row['file_size'],
                    file_name=row['file_name'],
                    file_extension=row['file_extension'],

                    risk_level=row['risk_level'],
                    risk_score=row['risk_score'],
                    confidence=row['confidence'],

                    assessment_method=row['assessment_method'],
                    assessment_source=row['assessment_source'],
                    assessment_details=row['assessment_details'],

                    annotation_note=row['annotation_note'],
                    annotation_tags=tags,

                    recommendation=row['recommendation'],

                    ai_confidence=row['ai_confidence'],
                    rule_match_count=row['rule_match_count'],

                    cache_hit=bool(row['cache_hit']),
                    cache_key=row['cache_key'],
                    cache_ttl=row['cache_ttl'],

                    last_modified=row['last_modified'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],

                    user_reviewed=bool(row['user_reviewed']),
                    user_safe_confirmed=row['user_safe_confirmed'],

                    scan_source=row['scan_source'],
                    parent_scan_id=row['parent_scan_id'],
                )

                results.append(note)

            return results

        except Exception as e:
            import logging
            logging.error(f"搜索批注失败: {e}")
            return []

    def get_statistics(self) -> dict:
        """获取批注统计信息

        Returns:
            统计数据
        """
        try:
            with sqlite3.connect(self.db_path) as conn:

                # 总数
                total = conn.execute("SELECT COUNT(*) FROM annotations").fetchone()[0]

                # 按风险等级统计
                risk_stats = {}
                for risk in ['safe', 'suspicious', 'dangerous']:
                    count = conn.execute("SELECT COUNT(*) FROM annotations WHERE risk_level = ?", (risk,)).fetchone()[0]
                    risk_stats[risk] = count

                # 按评估方法统计
                method_stats = {}
                for method in ['whitelist', 'rule', 'ai']:
                    count = conn.execute("SELECT COUNT(*) FROM annotations WHERE assessment_method = ?", (method,)).fetchone()[0]
                    method_stats[method] = count

                # 缓存命中率
                cache_hit_count = conn.execute("SELECT COUNT(*) FROM annotations WHERE cache_hit = 1").fetchone()[0]
                cache_hit_rate = cache_hit_count / total if total > 0 else 0

                # 最近扫描
                latest = conn.execute("""
                    SELECT scan_timestamp FROM annotations ORDER BY scan_timestamp DESC LIMIT 1
                """).fetchone()

                return {
                    'total': total,
                    'risk_stats': risk_stats,
                    'method_stats': method_stats,
                    'cache_hit_rate': cache_hit_rate,
                    'latest_scan': latest[0] if latest else None,
                }

        except Exception as e:
            import logging
            logging.error(f"获取统计信息失败: {e}")
            return {'total': 0, 'risk_stats': {}, 'method_stats': {}, 'cache_hit_rate': 0}

    def clear_cache(self, ttl_days: int = 7):
        """清除过期缓存

        Args:
            ttl_days: 缓存保留天数
        """
        try:
            cutoff = (datetime.now() - timedelta(days=ttl_days)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM annotations WHERE
                        cache_hit = 1 AND
                        created_at < ?
                """, (cutoff,))
                conn.commit()

        except Exception as e:
            import logging
            logging.error(f"清除缓存失败: {e}")

    def cleanup_old_annotations(self, days_to_keep: int = 30):
        """清理旧的批注数据

        Args:
            days_to_keep: 保留天数，超过此天数的批注将被删除
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

                conn.execute("""
                    DELETE FROM annotations WHERE
                        created_at < ?
                """, (cutoff,))
                conn.commit()

        except Exception as e:
            import logging
            logging.error(f"清理旧批注失败: {e}")
