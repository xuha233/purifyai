"""
应用配置管理 - 使用 JSON 文件存储，避免 QSettings 同步问题
"""
import json
import os
from typing import Any, Optional
import threading

class ConfigManager:
    """单例配置管理器"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'purifyai_config.json'
            )
            self._config = {}
            self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                print(f"配置已加载: {self.config_file}")
            except Exception as e:
                print(f"加载配置失败: {e}")
                self._config = {}
        else:
            self._config = {}

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reload_config(self):
        """强制重新加载配置文件"""
        self._load_config()

    def get_ai_config(self) -> dict:
        """获取AI配置（每次都重新读取确保最新值）"""
        self._load_config()  # 确保读取最新配置
        return {
            'enabled': self.get('ai_enabled', False),
            'api_key': self.get('ai_key', ''),
            'api_url': self.get('ai_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions'),
            'api_model': self.get('ai_model', 'glm-4-flash'),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config[key] = value
        self._save_config()

    def set_ai_config(self, enabled: bool = None, api_key: str = None,
                       api_url: str = None, api_model: str = None):
        """设置AI配置"""
        if enabled is not None:
            self.set('ai_enabled', enabled)
        if api_key is not None:
            self.set('ai_key', api_key.strip())
        if api_url is not None:
            self.set('ai_url', api_url.strip())
        if api_model is not None:
            self.set('ai_model', api_model.strip())

    def has_valid_ai_config(self) -> bool:
        """检查是否有有效的AI配置"""
        cfg = self.get_ai_config()
        return (
            cfg['enabled'] and
            cfg['api_key'] and
            cfg['api_url'] and
            len(cfg['api_key']) > 5  # API密钥至少5个字符
        )

    def log_ai_config(self, logger=None):
        """记录AI配置用于调试"""
        cfg = self.get_ai_config()
        msg = f"AI配置: enabled={cfg['enabled']}, key长度={len(cfg['api_key'])}, url={cfg['api_url'][:40]}, model={cfg['api_model']}"
        if logger:
            logger.info(msg)
        else:
            print(msg)
        return cfg


# 全局实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
