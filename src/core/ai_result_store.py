"""
AI复核功能模块 - 结果存储
管理AI复核结果的持久化存储
"""
import json
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from core.models import ScanItem
from core.rule_engine import RiskLevel
from core.ai_review_models import AIReviewResult, AIReviewStatus, AuditRecord, ReviewConfig
from core.ai_review_models import ReviewDecision


logger = logging.getLogger(__name__)


class AIResultStore:
    """AI复核结果存储"""

    def __init__(self, db_path: str = None):
        """初始化结果存储

        Args:
            db_path: 数据库路径，None则使用内存存储
        """
        self.db_path = db_path
        self.use_disk = db_path is not None
        self._memory_store: Dict[str, AIReviewResult] = {}
        self._batch_results: Dict[str, List[AIReviewResult]] = {}

    def save_result(self, result: AIReviewResult) -> bool:
        """保存单个复核结果

        Args:
            result: 复核结果

        Returns:
            bool: 是否保存成功
        """
        try:
            key = result.item_path

            if self.use_disk:
                return self._save_to_disk(key, result)
            else:
                self._memory_store[key] = result
                return True

        except Exception as e:
            logger.error(f"保存复核结果失败: {e}")
            return False

    def save_batch_results(
        self,
        batch_id: str,
        results: List[AIReviewResult]
    ) -> bool:
        """保存批量复核结果

        Args:
            batch_id: 批次ID
            results: 结果列表

        Returns:
            bool: 是否保存成功
        """
        try:
            self._batch_results[batch_id] = results

            # 同时保存到内存/磁盘
            for result in results:
                self.save_result(result)

            return True

        except Exception as e:
            logger.error(f"保存批量结果失败: {e}")
            return False

    def get_result(self, item_path: str) -> Optional[AIReviewResult]:
        """获取单个复核结果

        Args:
            item_path: 项目路径

        Returns:
            AIReviewResult或None
        """
        try:
            # 先查内存
            if item_path in self._memory_store:
                return self._memory_store[item_path]

            # 再查磁盘
            if self.use_disk:
                return self._load_from_disk(item_path)

            return None

        except Exception as e:
            logger.error(f"获取复核结果失败: {e}")
            return None

    def get_batch_results(self, batch_id: str) -> List[AIReviewResult]:
        """获取批次复核结果

        Args:
            batch_id: 批次ID

        Returns:
            结果列表
        """
        return self._batch_results.get(batch_id, [])

    def clear_old_results(self, ttl_seconds: int = 86400):
        """清理旧结果

        Args:
            ttl_seconds: 存活时间（秒）
        """
        try:
            cutoff = datetime.now() - timedelta(seconds=ttl_seconds)

            # 清理内存存储
            to_remove = []
            for key, result in self._memory_store.items():
                if result.review_timestamp and result.review_timestamp < cutoff:
                    to_remove.append(key)

            for key in to_remove:
                del self._memory_store[key]

            # 清理磁盘存储
            if self.use_disk:
                self._cleanup_disk(cutoff)

            logger.info(f"清理了 {len(to_remove)} 条过期结果")

        except Exception as e:
            logger.error(f"清理旧结果失败: {e}")

    def _save_to_disk(self, key: str, result: AIReviewResult) -> bool:
        """保存到磁盘

        Args:
            key: 存储键
            result: 复核结果

        Returns:
            bool: 是否成功
        """
        import os

        try:
            results_dir = os.path.join(self.db_path, "ai_results")
            os.makedirs(results_dir, exist_ok=True)

            # 使用路径的哈希作为文件名（避免路径中的特殊字符）
            import hashlib
            safe_key = hashlib.md5(key.encode()).hexdigest()

            file_path = os.path.join(results_dir, f"{safe_key}.json")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"保存到磁盘失败: {e}")
            return False

    def _load_from_disk(self, key: str) -> Optional[AIReviewResult]:
        """从磁盘加载

        Args:
            key: 存储键

        Returns:
            AIReviewResult或None
        """
        import os

        try:
            results_dir = os.path.join(self.db_path, "ai_results")
            import hashlib
            safe_key = hashlib.md5(key.encode()).hexdigest()
            file_path = os.path.join(results_dir, f"{safe_key}.json")

            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return AIReviewResult.from_dict(data)

        except Exception as e:
            logger.error(f"从磁盘加载失败: {e}")
            return None

    def _cleanup_disk(self, cutoff: datetime):
        """清理磁盘上的旧结果

        Args:
            cutoff: 截止时间
        """
        import os

        try:
            results_dir = os.path.join(self.db_path, "ai_results")
            if not os.path.exists(results_dir):
                return

            removed_count = 0
            for filename in os.listdir(results_dir):
                file_path = os.path.join(results_dir, filename)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    timestamp_str = data.get('review_timestamp')
                    if timestamp_str:
                        result_time = datetime.fromisoformat(timestamp_str)
                        if result_time < cutoff:
                            os.remove(file_path)
                            removed_count += 1

                except Exception:
                    continue

            logger.info(f"磁盘清理了 {removed_count} 条过期结果")

        except Exception as e:
            logger.error(f"磁盘清理失败: {e}")


class AuditLogManager:
    """人工审核日志管理器"""

    def __init__(self, db_path: str = None):
        """初始化日志管理器

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.use_disk = db_path is not None
        self._memory_logs: List[AuditRecord] = []

    def log_decision(
        self,
        item_path: str,
        user_decision: str,
        original_ai_risk: str,
        final_risk: str,
        reason: str = ""
    ) -> bool:
        """记录用户决策

        Args:
            item_path: 项目路径
            user_decision: 用户决策
            original_ai_risk: AI原始评估
            final_risk: 最终风险
            reason: 审核原因

        Returns:
            bool: 是否记录成功
        """
        from core.models import RiskLevel

        risk_map = {
            'safe': RiskLevel.SAFE,
            'suspicious': RiskLevel.SUSPICIOUS,
            'dangerous': RiskLevel.DANGEROUS
        }

        record = AuditRecord(
            item_path=item_path,
            user_decision=ReviewDecision.from_str(user_decision),
            original_ai_risk=risk_map.get(original_ai_risk),
            final_risk=risk_map.get(final_risk),
            audit_timestamp=datetime.now(),
            audit_reason=reason,
            changed_risk=(original_ai_risk != final_risk)
        )

        try:
            if self.use_disk:
                return self._save_to_disk(record)
            else:
                self._memory_logs.append(record)
                return True

        except Exception as e:
            logger.error(f"记录决策失败: {e}")
            return False

    def get_audit_logs(
        self,
        item_path: str = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """获取审核日志

        Args:
            item_path: 项目路径（过滤用）
            limit: 返回数量限制

        Returns:
            审核记录列表
        """
        logs = self._memory_logs[:]
        if self.use_disk:
            logs.extend(self._load_all_from_disk())

        # 过滤
        if item_path:
            logs = [log for log in logs if log.item_path == item_path]

        # 排序（最新在前）
        logs.sort(key=lambda x: x.audit_timestamp, reverse=True)

        return logs[:limit]

    def get_statistics(self) -> Dict:
        """获取审核统计信息

        Returns:
            统计数据字典
        """
        logs = self.get_audit_logs()

        stats = {
            'total': len(logs),
            'by_decision': {
                'keep': 0,
                'delete': 0,
                'skip': 0
            },
            'changed_decisions': 0,
            'by_original_risk': {
                'safe': 0,
                'suspicious': 0,
                'dangerous': 0
            },
            'by_final_risk': {
                'safe': 0,
                'suspicious': 0,
                'dangerous': 0
            }
        }

        for log in logs:
            # 按决策统计
            stats['by_decision'][log.user_decision.value] += 1

            # 更改决策
            if log.changed_risk:
                stats['changed_decisions'] += 1

            # 按风险统计
            if log.original_ai_risk:
                stats['by_original_risk'][log.original_ai_risk.value] += 1
            if log.final_risk:
                stats['by_final_risk'][log.final_risk.value] += 1

        return stats

    def _save_to_disk(self, record: AuditRecord) -> bool:
        """保存到磁盘

        Args:
            record: 审核记录

        Returns:
            bool: 是否成功
        """
        import os

        try:
            logs_dir = os.path.join(self.db_path, "audit_logs")
            os.makedirs(logs_dir, exist_ok=True)

            # 使用日期作为文件名
            date_str = datetime.now().strftime("%Y%m%d")
            file_path = os.path.join(logs_dir, f"{date_str}.jsonl")

            # 追加写入
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')

            return True

        except Exception as e:
            logger.error(f"保存日志到磁盘失败: {e}")
            return False

    def _load_all_from_disk(self) -> List[AuditRecord]:
        """从磁盘加载所有日志

        Returns:
            审核记录列表
        """
        import os

        logs = []

        try:
            logs_dir = os.path.join(self.db_path, "audit_logs")
            if not os.path.exists(logs_dir):
                return logs

            for filename in os.listdir(logs_dir):
                if not filename.endswith('.jsonl'):
                    continue

                file_path = os.path.join(logs_dir, filename)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                data = json.loads(line)
                                logs.append(AuditRecord.from_dict(data))

                except Exception as e:
                    logger.warning(f"读取日志文件 {filename} 失败: {e}")

        except Exception as e:
            logger.error(f"从磁盘加载日志失败: {e}")

        return logs


class ReviewConfig:
    """复核配置（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {
                'max_concurrent': 3,
                'max_retries': 3,
                'retry_delay': 1.0,
                'timeout': 30.0,
                'enable_caching': True,
                'cache_ttl': 86400,
                'strict_parse': True
            }
        return cls._instance

    def get(self, key: str, default=None):
        """获取配置

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)

    def set(self, key: str, value):
        """设置配置

        Args:
            key: 配置键
            value: 配置值
        """
        self._config[key] = value

    def load_from_config_manager(self, config_mgr):
        """从ConfigManager加载配置

        Args:
            config_mgr: ConfigManager实例
        """
        self.set('max_concurrent', config_mgr.get('review/max_concurrent', 3))
        self.set('max_retries', config_mgr.get('review/max_retries', 3))
        self.set('retry_delay', config_mgr.get('review/retry_delay', 1.0))
        self.set('timeout', config_mgr.get('review/timeout', 30.0))
        self.set('enable_caching', config_mgr.get('review/enable_caching', True))
        self.set('cache_ttl', config_mgr.get('review/cache_ttl', 86400))
        self.set('strict_parse', config_mgr.get('review/strict_parse', True))

    def save_settings(self, settings: QSettings):
        """保存配置到QSettings

        Args:
            settings: QSettings实例
        """
        settings.setValue('review/max_concurrent', self.get('max_concurrent'))
        settings.setValue('review/max_retries', self.get('max_retries'))
        settings.setValue('review/retry_delay', self.get('retry_delay'))
        settings.setValue('review/timeout', self.get('timeout'))
        settings.setValue('review/enable_caching', self.get('enable_caching'))
        settings.setValue('review/cache_ttl', self.get('cache_ttl'))
        settings.setValue('review/strict_parse', self.get('strict_parse'))


# 便捷函数
def get_result_store(db_path: str = None) -> AIResultStore:
    """获取结果存储实例

    Args:
        db_path: 数据库路径

    Returns:
        AIResultStore实例
    """
    return AIResultStore(db_path)


def get_audit_log_manager(db_path: str = None) -> AuditLogManager:
    """获取审核日志管理器实例

    Args:
        db_path: 数据库路径

    Returns:
        AuditLogManager实例
    """
    return AuditLogManager(db_path)


def get_review_config() -> ReviewConfig:
    """获取复核配置实例

    Returns:
        ReviewConfig实例
    """
    return ReviewConfig()


# 导入修复
from PyQt5.QtCore import QSettings
from core.ai_review_models import ReviewDecision
