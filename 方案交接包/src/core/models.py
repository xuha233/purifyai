"""
Core data models
Shared data structures used across the application
"""
import os
import time
from typing import Dict, Any


class ScanItem:
    """Scanned item information"""
    def __init__(self, path: str, size: int, item_type: str,
                 description: str = '', risk_level: str = 'safe', annotation=None):
        self.path = path
        self.size = size
        self.item_type = item_type  # 'file' or 'directory'
        self.description = description
        self.risk_level = risk_level  # 'safe', 'suspicious', 'dangerous'
        self.annotation = annotation  # Optional ScanAnnotation object
        self.last_modified = self._get_modified_time(path)
        # 新增字段
        self.judgment_method = 'rule'  # 'rule' 或 'ai'
        self.ai_explanation = ''  # AI输出项目说明

    @staticmethod
    def _get_modified_time(path: str) -> str:
        """Get last modified time"""
        try:
            stat = os.stat(path)
            return str(stat.st_mtime)
        except Exception:
            return str(time.time())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'size': self.size,
            'item_type': self.item_type,
            'description': self.description,
            'risk_level': self.risk_level,
            'last_modified': self.last_modified,
            'annotation': self.annotation,
            'judgment_method': self.judgment_method,
            'ai_explanation': self.ai_explanation
        }
