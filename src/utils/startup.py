"""
Windows 开机启动管理模块
使用 Windows 注册表管理开机启动项
"""
import os
import sys
import winreg
from typing import Tuple, Optional


class StartupManager:
    """开机启动管理器"""

    # 注册表路径
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def __init__(self, app_name: str = "PurifyAI"):
        """初始化启动管理器

        Args:
            app_name: 应用程序名称
        """
        self.app_name = app_name
        self.app_path = self._get_app_path()

    def _get_app_path(self) -> Optional[str]:
        """获取应用可执行文件路径

        Returns:
            应用路径，如果无法获取返回 None
        """
        try:
            # 获取当前 Python 脚本路径或打包后的可执行文件路径
            if getattr(sys, 'frozen', False):
                # 打包后的可执行文件路径
                return sys.executable
            else:
                # 开发环境下的脚本路径
                # 使用 pythonw.exe 运行以避免控制台窗口
                import sys
                python_exe = "pythonw.exe" if hasattr(sys, 'executable') else "python.exe"
                import os
                python_path = os.path.join(os.path.dirname(sys.executable), python_exe)
                if os.path.exists(python_path):
                    main_script = sys.argv[0]
                    main_script_abs = os.path.abspath(main_script)
                    return f'"{python_path}" "{main_script_abs}"'
                else:
                    # 备选方案：使用 sys.executable
                    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        except Exception:
            return None

    def is_enabled(self) -> bool:
        """检查是否已启用开机启动

        Returns:
            是否已启用
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY, 0, winreg.KEY_READ) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, self.app_name)
                    return value == self.app_path
                except FileNotFoundError:
                    return False
        except Exception:
            return False

    def enable(self) -> Tuple[bool, str]:
        """启用开机启动

        Returns:
            (是否成功, 错误信息)
        """
        if not self.app_path:
            return False, "无法获取应用路径"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY,
                               0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.app_path)
            return True, ""
        except PermissionError:
            return False, "需要管理员权限"
        except Exception as e:
            return False, str(e)

    def disable(self) -> Tuple[bool, str]:
        """禁用开机启动

        Returns:
            (是否成功, 错误信息)
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY,
                               0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, self.app_name)
            return True, ""
        except FileNotFoundError:
            return False, "开机启动项不存在"
        except Exception as e:
            return False, str(e)

    def toggle(self) -> Tuple[bool, str]:
        """切换开机启动状态

        Returns:
            (是否成功, 错误信息)
        """
        if self.is_enabled():
            return self.disable()
        else:
            return self.enable()


# 全局启动管理器实例（单例模式）
_global_manager: Optional[StartupManager] = None


def get_startup_manager() -> StartupManager:
    """
    获取全局启动管理器实例（单例）

    Returns:
        StartupManager: 启动管理器实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = StartupManager()
    return _global_manager
