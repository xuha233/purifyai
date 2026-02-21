"""
权限管理模块
用于检查和提升权限（Windows 管理员权限）
"""
import sys
import ctypes
import os


def is_admin() -> bool:
    """检查当前进程是否具有管理员权限

    Returns:
        bool: 是否具有管理员权限
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def request_admin_privilege():
    """请求管理员权限并重启程序

    注意：调用此函数将退出当前程序并启动新的
    管理员进程
    """
    try:
        # 获取当前脚本路径
        script = os.path.abspath(sys.argv[0])

        # 获取命令行参数
        params = ' '.join(sys.argv[1:])

        # 请求以管理员身份运行
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            'runas',        # verb: 请求管理员权限
            script,          # file:参数 要运行的程序
            params,          # parameters: 命令行参数
            None,           # working directory
            1,              # show command: SW_SHOWNORMAL
            None,           # operation
        )

        # 检查是否成功启动
        if result > 32:  # 如果结果大于 32，表示成功
            sys.exit(0)  # 退出当前程序

    except Exception as e:
        print(f'请求管理员权限失败: {e}')
        sys.exit(1)


def ensure_admin_or_fail() -> bool:
    """确保具有管理员权限，否则返回 False

    Returns:
        bool: 是否具有管理员权限
    """
    if not is_admin():
        return False
    return True


def get_current_user() -> str:
    """获取当前用户名

    Returns:
        str: 用户名
    """
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return 'Unknown'


def is_system_path(path: str) -> bool:
    """检查路径是否是系统路径（需要管理员权限）

    Args:
        path: 要检查的路径

    Returns:
        bool: 是否是系统路径
    """
    if not path:
        return False

    # 转换为大写进行检查
    path_upper = path.upper()

    # 系统路径列表
    system_paths = [
        r'C:\WINDOWS',
        r'C:\PROGRAMFILES',
        r'C:\PROGRAMFILES (X86)',
        r'C:\PROGRAMFILES (X86)',
    ]

    for system_path in system_paths:
        if path_upper.startswith(system_path):
            return True

    return False


def needs_admin_for_operation(operation_type: str, items: list) -> bool:
    """检查操作是否需要管理员权限

    Args:
        operation_type: 操作类型 ('scan' 或 'clean')
        items: 要操作的文件/文件夹列表

    Returns:
        bool: 是否需要管理员权限
    """
    if operation_type == 'scan':
        # 扫描操作通常不需要管理员权限
        return False

    if operation_type == 'clean':
        # 检查是否有任何系统路径
        for item in items:
            if hasattr(item, 'path'):
                path = item.path
            else:
                path = str(item)

            if is_system_path(path):
                return True

        return False
