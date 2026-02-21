"""
AI 分类缓存模块
提供内存缓存和数据库持久化缓存，加速 AI 分类
"""
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import lru_cache

from .database import get_database
from .rule_engine import RiskLevel

# 设置日志
logger = logging.getLogger(__name__)


class AICache:
    """AI 分类缓存管理器

    使用双层缓存策略:
    1. 内存缓存 (LRU) - 快速访问
    2. 数据库缓存 - 持久化，跨会话有效
    """

    def __init__(self):
        """初始化缓存"""
        self.db = get_database()
        # 内存缓存字典 (key: folder_name, value: CacheEntry)
        self._memory_cache: Dict[str, CacheEntry] = {}
        # 缓存默认 TTL (7 天)
        self.default_ttl = timedelta(days=7)
        # 线程锁，保护内存缓存的并发访问
        self._lock = threading.Lock()

    def get(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存的分类结果

        Args:
            folder_name: 文件夹名称

        Returns:
            包含 risk_level, reason, confidence 的字典，如果未找到返回 None
        """
        # 1. 先查内存缓存（线程安全）
        with self._lock:
            entry = self._memory_cache.get(folder_name)
            if entry and not entry.is_expired():
                return entry.to_dict()

        # 2. 再查数据库缓存 (数据库已有线程本地存储)
        db_cache = self._get_from_db(folder_name)
        if db_cache:
            # 计算是否过期
            cached_at = datetime.fromisoformat(db_cache['cached_at'].replace('Z', '+00:00'))
            if datetime.now() - cached_at < self.default_ttl:
                entry = CacheEntry(
                    folder_name=folder_name,
                    risk_level=db_cache['risk_level'],
                    reason=db_cache.get('reason', ''),
                    confidence=db_cache.get('confidence', 0.5),
                    cached_at=cached_at
                )
                # 更新内存缓存
                self._memory_cache[folder_name] = entry
                return entry.to_dict()

        return None

    def set(self, folder_name: str, risk_level: RiskLevel,
            reason: str = '', confidence: float = 0.5,
            ttl: timedelta = None) -> bool:
        """设置缓存

        Args:
            folder_name: 文件夹名称
            risk_level: 风险等级
            reason: 分类原因
            confidence: AI 置信度
            ttl: 缓存有效期，默认使用 default_ttl

        Returns:
            是否成功设置
        """
        try:
            cached_at = datetime.now()
            entry = CacheEntry(
                folder_name=folder_name,
                risk_level=risk_level,
                reason=reason,
                confidence=confidence,
                cached_at=cached_at,
                ttl=ttl or self.default_ttl
            )

            # 1. 更新内存缓存（线程安全）
            with self._lock:
                self._memory_cache[folder_name] = entry

            # 2. 写入数据库
            self._save_to_db(folder_name, risk_level, reason, confidence, cached_at)

            return True
        except Exception as e:
            logger.warning(f"Failed to set cache for '{folder_name}': {e}")
            return False

    def set_batch(self, items: List[tuple]) -> int:
        """批量设置缓存

        Args:
            items: (folder_name, risk_level, reason, confidence) 元组列表

        Returns:
            成功设置的数量
        """
        success_count = 0
        cached_at = datetime.now()

        for item in items:
            if len(item) >= 2:
                folder_name, risk_level = item[0], item[1]
                reason = item[2] if len(item) > 2 else ''
                confidence = item[3] if len(item) > 3 else 0.5

                if self.set(folder_name, risk_level, reason, confidence):
                    success_count += 1

        return success_count

    def clear(self, folder_name: str = None):
        """清除缓存

        Args:
            folder_name: 指定的文件夹名称，如果为 None 则清除所有缓存
        """
        if folder_name:
            # 清除指定缓存（线程安全）
            with self._lock:
                if folder_name in self._memory_cache:
                    del self._memory_cache[folder_name]
            self._clear_from_db(folder_name)
        else:
            # 清除所有缓存（线程安全）
            with self._lock:
                self._memory_cache.clear()
            self._clear_all_from_db()

    def invalidate_expired(self) -> int:
        """清除所有过期的缓存

        Returns:
            清除的数量
        """
        expired_keys = []

        # 检查内存缓存（线程安全）
        with self._lock:
            for key, entry in self._memory_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

        # 删除过期项（线程安全）
        with self._lock:
            for key in expired_keys:
                del self._memory_cache[key]

        # 清除数据库中的过期缓存
        self._clear_expired_from_db()

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            包含缓存统计的字典
        """
        memory_cache_count = len(self._memory_cache)

        try:
            db_cache_count = self.db.get_statistics().get('ai_classification_count', 0)
        except:
            db_cache_count = 0

        # 总缓存数量 (mapped to cache_size for dashboard)
        cache_size = memory_cache_count + db_cache_count

        # 计算命中率（需要额外跟踪）
        hit_count = 0
        total_queries = 0

        for entry in self._memory_cache.values():
            if hasattr(entry, 'hit_count'):
                hit_count += entry.hit_count

        hit_rate = hit_count / total_queries if total_queries > 0 else 0

        return {
            'memory_cache_count': memory_cache_count,
            'db_cache_count': db_cache_count,
            'hit_rate': hit_rate,
            'cache_size': cache_size,
            'total_size': cache_size  # 保持兼容性
        }

    def warmup(self, limit: int = 100):
        """预热内存缓存：从数据库加载最近使用的分类结果

        Args:
            limit: 加载的最大数量
        """
        try:
            # 从数据库获取最近使用的分类
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ai_classifications
                ORDER BY cached_at DESC
                LIMIT ?
            ''', (limit,))

            for row in cursor.fetchall():
                folder_name = row['folder_name']
                risk_level = row['risk_level']
                reason = row.get('reason', '')
                confidence = row.get('confidence', 0.5)
                cached_at = datetime.fromisoformat(row['cached_at'].replace('Z', '+00:00'))

                # 检查是否过期
                if datetime.now() - cached_at < self.default_ttl:
                    entry = CacheEntry(
                        folder_name=folder_name,
                        risk_level=risk_level,
                        reason=reason,
                        confidence=confidence,
                        cached_at=cached_at
                    )
                    # 线程安全地更新内存缓存
                    with self._lock:
                        self._memory_cache[folder_name] = entry
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
        finally:
            # 确保连接关闭
            try:
                if 'conn' in locals() and conn:
                    conn.close()
            except:
                # 线程本地存储连接可能已经被清理
                pass

    def _get_from_db(self, folder_name: str) -> Optional[Dict[str, Any]]:
        """从数据库获取缓存"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ai_classifications
                WHERE folder_name = ?
            ''', (folder_name,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.warning(f"Failed to get cache from DB for '{folder_name}': {e}")
            return None

    def _save_to_db(self, folder_name: str, risk_level: str,
                   reason: str, confidence: float, cached_at: datetime):
        """保存缓存到数据库"""
        conn = None
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 使用 UPSERT (INSERT 或 REPLACE)
            cursor.execute('''
                INSERT OR REPLACE INTO ai_classifications
                (folder_name, risk_level, reason, confidence, cached_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (folder_name, risk_level, reason, confidence,
                   cached_at.isoformat()))

            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to save cache to DB for '{folder_name}': {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
        finally:
            if conn:
                conn.close()

    def _clear_from_db(self, folder_name: str):
        """从数据库清除指定缓存"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM ai_classifications
                WHERE folder_name = ?
            ''', (folder_name,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _clear_all_from_db(self):
        """从数据库清除所有缓存"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ai_classifications')
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _clear_expired_from_db(self):
        """从数据库清除过期缓存"""
        try:
            cutoff_date = datetime.now() - self.default_ttl

            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM ai_classifications
                WHERE cached_at < ?
            ''', (cutoff_date.isoformat(),))
            conn.commit()
            conn.close()
        except Exception:
            pass


class CacheEntry:
    """缓存条目"""

    def __init__(self, folder_name: str, risk_level: RiskLevel,
                 reason: str, confidence: float,
                 cached_at: datetime = None, ttl: timedelta = None):
        self.folder_name = folder_name
        self.risk_level = risk_level
        self.reason = reason
        self.confidence = confidence
        self.cached_at = cached_at or datetime.now()
        self.ttl = ttl or timedelta(days=7)
        self.hit_count = 0  # 命中次数统计

    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() - self.cached_at > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'folder_name': self.folder_name,
            'risk_level': self.risk_level,
            'reason': self.reason,
            'confidence': self.confidence,
            'cached_at': self.cached_at.isoformat()
        }


# 全局 AI 缓存实例（单例模式）
_global_cache: Optional[AICache] = None


def get_ai_cache() -> AICache:
    """
    获取全局 AI 缓存实例（单例）

    Returns:
        AICache: AI 缓存实例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = AICache()
    return _global_cache
