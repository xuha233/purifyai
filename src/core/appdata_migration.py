"""
AppData 文件夹迁移工具核心模块

提供 AppData 文件夹迁移到其他磁盘并通过符号链接重定向的功能。
支持扫描可迁移的大型文件夹、执行迁移、回滚操作以及迁移历史记录管理。
"""
import os
import shutil
import subprocess
import json
import time
import psutil
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


# 常见 AppData 应用风险评估字典（优化版）
COMMON_APPS = {
    # 浏览器相关（安全缓存）
    'Google': {'risk': 'safe', 'category': 'cache'},
    'Google Chrome': {'risk': 'safe', 'category': 'cache'},
    'Chrome': {'risk': 'safe', 'category': 'cache'},
    'Edge': {'risk': 'safe', 'category': 'cache'},
    'MicrosoftEdge': {'risk': 'safe', 'category': 'cache'},
    'Firefox': {'risk': 'safe', 'category': 'cache'},
    'Brave': {'risk': 'safe', 'category': 'cache'},
    'Opera': {'risk': 'safe', 'category': 'cache'},
    'Vivaldi': {'risk': 'safe', 'category': 'cache'},

    # 开发工具（安全）
    'Microsoft': {'risk': 'safe', 'category': 'config'},
    'VSCode': {'risk': 'safe', 'category': 'config'},
    'Code': {'risk': 'safe', 'category': 'config'},
    '.vscode': {'risk': 'safe', 'category': 'config'},
    'Node.js': {'risk': 'safe', 'category': 'cache'},
    'Python': {'risk': 'safe', 'category': 'cache'},
    'pip': {'risk': 'safe', 'category': 'cache'},
    'npm': {'risk': 'safe', 'category': 'cache'},
    'yarn': {'risk': 'safe', 'category': 'cache'},
    'NuGet': {'risk': 'safe', 'category': 'cache'},
    'JetBrains': {'risk': 'safe', 'category': 'config'},
    'PyCharm': {'risk': 'safe', 'category': 'config'},
    'Visual Studio': {'risk': 'safe', 'category': 'config'},
    'AndroidStudio': {'risk': 'safe', 'category': 'cache'},

    # 实用工具（安全）
    'Notion': {'risk': 'safe', 'category': 'user_data'},
    'Obsidian': {'risk': 'safe', 'category': 'user_data'},
    'Typora': {'risk': 'safe', 'category': 'config'},

    # 通信软件（用户数据，需确认）
    'WeChat': {'risk': 'wary', 'category': 'user_data'},
    'WeChat Files': {'risk': 'wary', 'category': 'user_data'},
    'QQ': {'risk': 'wary', 'category': 'user_data'},
    'DingTalk': {'risk': 'wary', 'category': 'user_data'},
    'Slack': {'risk': 'wary', 'category': 'user_data'},
    'Discord': {'risk': 'wary', 'category': 'user_data'},
    'Telegram': {'risk': 'wary', 'category': 'user_data'},
    'Teams': {'risk': 'wary', 'category': 'user_data'},

    # 游戏平台（用户数据）
    'Steam': {'risk': 'wary', 'category': 'user_data'},
    'EpicGames': {'risk': 'wary', 'category': 'user_data'},
    'Epic Games': {'risk': 'wary', 'category': 'user_data'},
    'Origin': {'risk': 'wary', 'category': 'user_data'},
    'Battle.net': {'risk': 'wary', 'category': 'user_data'},
    'Ubisoft': {'risk': 'wary', 'category': 'user_data'},

    # 云存储（用户数据）
    'OneDrive': {'risk': 'wary', 'category': 'user_data'},
    'Microsoft OneDrive': {'risk': 'wary', 'category': 'user_data'},
    'Dropbox': {'risk': 'wary', 'category': 'user_data'},
    'Baidu': {'risk': 'wary', 'category': 'user_data'},
    '坚果云': {'risk': 'wary', 'category': 'user_data'},

    # 创意工具（配置）
    'Adobe': {'risk': 'wary', 'category': 'config'},
    'Affinity': {'risk': 'wary', 'category': 'user_data'},
    'DaVinci': {'risk': 'wary', 'category': 'user_data'},

    # 生产力工具（配置）
    'WPS': {'risk': 'wary', 'category': 'user_data'},
    'Kingsoft': {'risk': 'safe', 'category': 'cache'},
}


# 风险级别定义：safe(可迁移), wary(需谨慎), dangerous(不推荐), unknown(未知)

@dataclass
class MigrationItem:
    """迁移项目数据类"""
    name: str                    # 文件夹名称
    path: str                    # 完整路径
    size: int                    # 大小（字节）
    app_type: str                # 应用类型
    category: str                # 类别
    risk_level: str = 'unknown'  # 风险级别 ('safe', 'wary', 'dangerous', 'unknown')
    risk_reason: str = ''         # 风险原因说明

    def __post_init__(self):
        """初始化后评估风险等级"""
        if self.risk_level == 'unknown':
            self._assess_risk()

    def _assess_risk(self):
        """根据文件夹名称智能评估风险等级"""
        folder_name = self.name.lower()

        # 1. 首先完全匹配常见应用名称
        for app_name, info in COMMON_APPS.items():
            # 使用精确匹配而非包含，避免误判
            if folder_name == app_name.lower() or folder_name.startswith(app_name.lower() + '_'):
                self.risk_level = info['risk']
                self.category = info['category']
                self.app_type = info['risk']
                self.risk_reason = f"已知应用: {app_name}"
                return

        # 2. 扩展的安全关键词检测（优化后的）
        safe_keywords = [
            # 缓存相关
            'cache', 'cachecache', 'codecache', 'gpucache', 'shadercache',
            # 临时文件
            'temp', 'tmp', 'download', 'crashdumps',
            # 日志
            'logs', 'session',
            # 缩略图
            'thumb', 'thumbnail', 'previews',
            # 安装器/更新
            'updates', 'setup', 'installer',
            # 构建产物
            'build', 'dist', 'out', 'node_modules',
            # 开发工具缓存
            'nuget', 'pip', 'packages', 'maven', 'gradle',
            # 其他
            'archive', 'backup', 'recyclebin'
        ]

        suspect_keywords = [
            'data', 'database', 'db', 'storage', 'profile', 'settings',
            'user', 'account', 'config', 'preference'
        ]

        # 3. 危险关键词 - 精确匹配特定系统关键目录
        dangerous_patterns = [
            r'^packages$',  # 完全匹配 packages（AppData/Packages 是应用商店应用）
            r'^windowsapps$',  # 完全匹配
            r'^\.',  # 隐藏系统文件夹如 System32 相关
        ]

        # 4. 检查安全关键词
        for keyword in safe_keywords:
            if keyword in folder_name:
                self.risk_level = 'safe'
                self.category = 'cache'
                self.app_type = 'safe'
                self.risk_reason = f"缓存/临时文件: {keyword}"
                return

        # 5. 检查危险模式（使用精确匹配）
        for pattern in dangerous_patterns:
            import re
            if re.match(pattern, folder_name):
                self.risk_level = 'dangerous'
                self.category = 'system'
                self.app_type = 'dangerous'
                self.risk_reason = "系统关键目录"
                return

        # 6. 特殊检测：AppData 目录级别的文件夹
        # 有些文件夹名很通用，如 'Google'、'Microsoft'，需要结合大小写检查
        if folder_name in ['microsoft', 'google', 'adobe', 'autodesk']:
            # 完全匹配这些公司名，通常是系统必要文件
            self.risk_level = 'dangerous'
            self.category = 'system'
            self.app_type = 'dangerous'
            self.risk_reason = "系统级应用目录"
            return

        # 7. 检查疑似关键词（用户数据相关但需要谨慎）
        for keyword in suspect_keywords:
            if keyword in folder_name:
                self.risk_level = 'wary'
                self.category = 'user_data'
                self.app_type = 'wary'
                self.risk_reason = f"包含用户数据: {keyword}"
                return

        # 8. 默认根据特征进一步分析
        # 如果文件夹名是纯英文且较长，可能是应用数据
        if len(self.name) > 3 and all(c.isalnum() or c in ['.', '-', '_'] for c in self.name):
            self.risk_level = 'wary'
            self.category = 'user_data'
            self.app_type = 'wary'
            self.risk_reason = "应用程序数据（需确认）"
        else:
            self.risk_level = 'unknown'
            self.category = 'unknown'
            self.app_type = 'unknown'
            self.risk_reason = "未能识别的文件夹"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class ScanMigrationThread(QThread):
    """扫描迁移项目线程"""
    progress = pyqtSignal(int, int)          # current, total
    item_found = pyqtSignal(MigrationItem)
    complete = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, min_size_mb: int = 100, scan_roaming: bool = True,
                 scan_local: bool = True, scan_local_low: bool = False):
        super().__init__()
        self.min_size_mb = min_size_mb
        self.min_size_bytes = min_size_mb * 1024 * 1024
        self.scan_roaming = scan_roaming
        self.scan_local = scan_local
        self.scan_local_low = scan_local_low
        self.is_cancelled = False

    def run(self):
        """执行扫描"""
        try:
            logger.info(f"[迁移扫描] 开始扫描 - 最小大小: {self.min_size_mb}MB")
            folders = []

            # 扫描各个 AppData 目录
            if self.scan_roaming:
                folders.extend(self._scan_directory('Roaming'))
            if self.scan_local:
                folders.extend(self._scan_directory('Local'))
            if self.scan_local_low:
                folders.extend(self._scan_directory('LocalLow'))

            logger.info(f"[迁移扫描] 扫描完成 - 发现 {len(folders)} 个文件夹")
            self.complete.emit(folders)

        except Exception as e:
            logger.error(f"[迁移扫描] 扫描失败: {e}")
            self.error.emit(f"扫描失败: {str(e)}")

    def _scan_directory(self, dir_type: str) -> List[MigrationItem]:
        """扫描指定 AppData 目录"""
        folders = []

        if dir_type == 'Roaming':
            appdata_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming')
        elif dir_type == 'Local':
            appdata_dir = os.environ.get('LOCALAPPDATA', '')
        elif dir_type == 'LocalLow':
            appdata_dir = os.environ.get('LOCALAPPDATA', '').replace('Local', 'LocalLow')
        else:
            return folders

        if not appdata_dir or not os.path.exists(appdata_dir):
            logger.debug(f"[迁移扫描] 目录不存在或无法访问: {appdata_dir}")
            return folders

        try:
            entries = os.listdir(appdata_dir)
            total = len(entries)
            logger.debug(f"[迁移扫描] 扫描 {dir_type}: {total} 个条目")

            for i, entry in enumerate(entries):
                if self.is_cancelled:
                    logger.info("[迁移扫描] 扫描已取消")
                    break

                folder_path = os.path.join(appdata_dir, entry)

                if os.path.isdir(folder_path):
                    # 跳过一些系统目录和已知不需要迁移的目录
                    if entry in ['Microsoft', 'WindowsApps', 'Packages', 'Temp']:
                        continue

                    size = self._calculate_size(folder_path)
                    if size >= self.min_size_bytes:
                        item = MigrationItem(
                            name=entry,
                            path=folder_path,
                            size=size,
                            app_type='unknown',
                            category='unknown'
                        )
                        self.item_found.emit(item)
                        folders.append(item)
                        logger.debug(f"[迁移扫描] 发现: {entry} - {size / (1024*1024):.1f}MB")

                self.progress.emit(i + 1, total)

        except PermissionError as e:
            logger.warning(f"[迁移扫描] 权限不足无法访问 {appdata_dir}: {e}")
        except Exception as e:
            logger.error(f"[迁移扫描] 扫描目录出错 {appdata_dir}: {e}")

        return folders

    def _calculate_size(self, path: str) -> int:
        """计算文件夹大小"""
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    try:
                        total += os.path.getsize(os.path.join(root, file))
                        # 限制扫描深度以提高性能
                        if total > self.min_size_bytes:
                            # 已经超过阈值，直接返回
                            return total
                    except (OSError, PermissionError):
                        pass
        except Exception:
            pass
        return total

    def cancel(self):
        """取消扫描"""
        self.is_cancelled = True


class MigrateThread(QThread):
    """迁移执行线程"""
    progress = pyqtSignal(int)             # 进度百分比 (0-100)
    status = pyqtSignal(str)               # 状态消息
    complete = pyqtSignal(bool, str)     # success, message
    error = pyqtSignal(str)                # 错误消息

    def __init__(self, items: List[MigrationItem], target_base: str):
        super().__init__()
        self.items = items
        self.target_base = target_base
        self.is_cancelled = False
        self.migrated_items = []

    def run(self):
        """执行迁移"""
        try:
            logger.info(f"[执行迁移] 开始迁移 {len(self.items)} 个项目到 {self.target_base}")

            # 检查目标路径
            if not os.path.exists(self.target_base):
                logger.info(f"[执行迁移] 创建目标目录: {self.target_base}")
                os.makedirs(self.target_base, exist_ok=True)

            # 验证目标磁盘空间
            required_space = sum(item.size for item in self.items) * 1.1  # 增加10%缓冲
            target_drive = os.path.splitdrive(self.target_base)[0]
            free_space = psutil.disk_usage(target_drive).free

            if free_space < required_space:
                required_gb = required_space / (1024**3)
                free_gb = free_space / (1024**3)
                self.error.emit(f"目标磁盘空间不足。需要约 {required_gb:.1f}GB，可用 {free_gb:.1f}GB")
                return

            total_items = len(self.items)

            for i, item in enumerate(self.items):
                if self.is_cancelled:
                    self.complete.emit(False, "迁移已取消")
                    return

                self.status.emit(f"正在迁移 ({i+1}/{total_items}): {item.name}")
                logger.info(f"[执行迁移] 迁移项目: {item.name}")

                # 计算进度
                progress = int((i / total_items) * 100)
                self.progress.emit(progress)

                target_path = os.path.join(self.target_base, item.name)

                # 执行迁移
                try:
                    success = self._migrate_single(item.path, target_path)
                    if success:
                        self.migrated_items.append({
                            'source': item.path,
                            'target': target_path,
                            'size': item.size,
                            'name': item.name,
                            'timestamp': datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"[执行迁移] 迁移失败 {item.name}: {e}")
                    # 继续迁移下一个项目
                    continue

            # 完成
            self.progress.emit(100)
            self.status.emit("迁移完成")
            logger.info(f"[执行迁移] 成功迁移 {len(self.migrated_items)} 个项目")
            self.complete.emit(True, f"成功迁移 {len(self.migrated_items)} 个项目")

        except Exception as e:
            logger.error(f"[执行迁移] 迁移过程出错: {e}")
            self.error.emit(f"迁移失败: {str(e)}")

    def _migrate_single(self, source: str, target: str) -> bool:
        """迁移单个文件夹"""
        try:
            # 1. 检查目标是否已存在
            if os.path.exists(target):
                if os.path.islink(target):
                    # 已是符号链接
                    return True
                else:
                    # 已存在文件/文件夹，添加后缀
                    base = target
                    counter = 1
                    while os.path.exists(target):
                        target = f"{base}_{counter}"
                        counter += 1

            # 2. 停止相关进程
            self._kill_processes_using(source)

            # 3. 复制文件夹
            self.status.emit(f"正在复制数据: {os.path.basename(source)}")
            shutil.copytree(source, target, ignore_errors=True)

            # 4. 删除源文件夹
            self.status.emit(f"正在清理源文件夹: {os.path.basename(source)}")
            if os.path.exists(source):
                shutil.rmtree(source, ignore_errors=True)

            # 5. 创建符号链接
            self.status.emit(f"创建符号链接: {os.path.basename(source)}")
            self._create_symlink(source, target)

            return True

        except Exception as e:
            logger.error(f"[迁移项目] 出错 {source}: {e}")
            # 尝试回滚
            try:
                if os.path.exists(target) and not os.path.islink(source):
                    # 如果目标已创建但未链接，尝试删除目标
                    shutil.rmtree(target, ignore_errors=True)
            except:
                pass
            raise

    def _create_symlink(self, source: str, target: str):
        """创建 Windows 目录符号链接（需要管理员权限）"""
        try:
            # 确保源路径的父目录存在
            parent_dir = os.path.dirname(source)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # 使用 mklink 创建目录符号链接
            # cmd /c mklink /D "源链接" "真实路径"
            result = subprocess.run(
                ['cmd', '/c', 'mklink', '/D', source, target],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise RuntimeError(f"创建符号链接失败: {error_msg}")

            logger.debug(f"[创建链接] 成功创建符号链接: {source} -> {target}")
            return True

        except subprocess.TimeoutExpired:
            raise RuntimeError("创建符号链接超时")
        except Exception as e:
            raise RuntimeError(f"创建符号链接失败: {e}")

    def _kill_processes_using(self, folder_path: str):
        """停止使用指定文件夹的进程"""
        folder_lower = folder_path.lower()
        try:
            killed_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'open_files']):
                try:
                    proc_info = proc.info
                    proc_exe = proc_info.get('exe', '').lower() if proc_info.get('exe') else ''

                    if not (folder_lower in proc_exe or folder_lower in (os.path.dirname(proc_exe) if proc_exe else '').lower()):
                        # 检查打开的文件
                        try:
                            for file in proc.open_files():
                                if file.path and folder_lower in file.path.lower():
                                    logger.debug(f"[停止进程] 停止进程: {proc.info.get('name')} (PID: {proc.info.get('pid')})")
                                    proc.kill()
                                    killed_processes.append(proc.info.get('name'))
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if killed_processes:
                logger.info(f"[停止进程] 已停止 {len(killed_processes)} 个进程: {', '.join(set(killed_processes))}")

        except Exception as e:
            logger.warning(f"[停止进程] 停止过程出错: {e}")

    def cancel(self):
        """取消迁移"""
        self.is_cancelled = True


class RollbackThread(QThread):
    """回滚线程"""
    progress = pyqtSignal(int)            # 进度百分比 (0-100)
    status = pyqtSignal(str)              # 状态消息
    complete = pyqtSignal(bool, str)     # success, message
    error = pyqtSignal(str)               # 错误消息

    def __init__(self, migration_record: Dict):
        super().__init__()
        self.source = migration_record.get('source')
        self.target = migration_record.get('original_target') or migration_record.get('target')
        self.is_cancelled = False

    def run(self):
        """执行回滚"""
        try:
            logger.info(f"[执行回滚] 开始回滚: {self.source} -> {self.target}")

            if not self.source or not self.target:
                self.error.emit("迁移记录不完整")
                return

            # 1. 检查符号链接是否存在
            self.status.emit("正在检查符号链接...")
            self.progress.emit(10)

            if not os.path.exists(self.source):
                self.error.emit("源路径不存在")
                return

            is_symlink = os.path.islink(self.source)

            # 2. 删除符号链接
            if is_symlink:
                self.status.emit("正在删除符号链接...")
                self.progress.emit(30)
                os.rmdir(self.source)  # 使用 rmdir 删除符号链接
                logger.info(f"[执行回滚] 已删除符号链接: {self.source}")
            else:
                logger.warning(f"[执行回滚] 源不是符号链接: {self.source}")

            # 3. 移回原位置
            self.status.emit("正在移回原位置...")
            self.progress.emit(60)

            if os.path.exists(self.target):
                if os.path.exists(self.source):
                    # 目标已存在且源不为符号链接（可能是恢复失败后的情况）
                    logger.warning(f"[执行回滚] 目标已存在且源存在，跳过移动: {self.target}")
                else:
                    shutil.move(self.target, self.source)
                    logger.info(f"[执行回滚] 已移回: {self.target} -> {self.source}")

            # 4. 清除历史记录
            self.status.emit("正在更新记录...")
            self.progress.emit(90)

            self._remove_history(self.source)

            self.progress.emit(100)
            self.status.emit("回滚完成")
            logger.info(f"[执行回滚] 回滚成功")
            self.complete.emit(True, "回滚完成")

        except Exception as e:
            logger.error(f"[执行回滚] 回滚失败: {e}")
            self.error.emit(f"回滚失败: {str(e)}")

    def _remove_history(self, source: str):
        """移除迁移历史记录"""
        tool = AppDataMigrationTool()
        tool.remove_migration_history(source)

    def cancel(self):
        """取消回滚"""
        self.is_cancelled = True


class AppDataMigrationTool(QObject):
    """AppData 迁移工具主类

    功能:
    - 扫描可迁移的 AppData 文件夹
    - 执行文件夹迁移并创建符号链接
    - 回滚迁移操作
    - 管理迁移历史记录
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_dir = os.path.join(os.path.expanduser('~'), '.purifyai')
        self.history_file = os.path.join(self.config_dir, 'appdata_migrations.json')
        self._ensure_history_file()

    def _ensure_history_file(self):
        """确保历史文件存在"""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir, exist_ok=True, mode=0o755)
            if not os.path.exists(self.history_file):
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                logger.debug(f"[迁移工具] 创建历史文件: {self.history_file}")
        except Exception as e:
            logger.error(f"[迁移工具] 创建历史文件失败: {e}")

    def get_migration_history(self) -> List[Dict]:
        """获取迁移历史记录"""
        try:
            if not os.path.exists(self.history_file):
                return []

            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return history
        except Exception as e:
            logger.error(f"[迁移工具] 读取历史记录失败: {e}")
            return []

    def save_migration_record(self, record: Dict):
        """保存迁移记录"""
        try:
            history = self.get_migration_history()
            history.append(record)

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            logger.info(f"[迁移工具] 保存迁移记录: {record.get('name', 'unknown')}")
        except Exception as e:
            logger.error(f"[迁移工具] 保存迁移记录失败: {e}")

    def remove_migration_history(self, source: str):
        """移除指定源的迁移历史"""
        try:
            history = self.get_migration_history()
            history = [h for h in history if h.get('source') != source]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            logger.info(f"[迁移工具] 移除迁移历史: {source}")
        except Exception as e:
            logger.error(f"[迁移工具] 移除迁移历史失败: {e}")

    def get_available_drives(self) -> List[Dict]:
        """获取可用磁盘列表"""
        drives = []
        try:
            for partition in psutil.disk_partitions():
                if partition.fstype and 'fixed' in partition.opts:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        drives.append({
                            'drive': partition.mountpoint,
                            'name': partition.device,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        })
                    except Exception:
                        pass

            # 按盘符排序
            drives.sort(key=lambda x: x['drive'])
            return drives
        except Exception as e:
            logger.error(f"[迁移工具] 获取磁盘列表失败: {e}")
            return []

    def is_admin(self) -> bool:
        """检查是否有管理员权限"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def check_symlink_support(self) -> bool:
        """检查是否支持符号链接（需要管理员权限）"""
        if not self.is_admin():
            return False

        try:
            # 创建测试符号链接
            test_link = os.path.join(self.config_dir, 'test_link')
            test_target = os.path.join(self.config_dir, 'test')

            # 如果测试目录不存在，创建一个
            if not os.path.exists(test_target):
                os.makedirs(test_target, exist_ok=True)

            # 尝试创建符号链接
            result = subprocess.run(
                ['cmd', '/c', 'mklink', '/D', test_link, test_target],
                shell=True,
                capture_output=True,
                timeout=10
            )

            # 测试成功则清理
            if result.returncode == 0:
                try:
                    os.rmdir(test_link)
                except:
                    pass
                return True

            return False
        except Exception as e:
            logger.debug(f"[迁移工具] 符号链接测试失败: {e}")
            return False

    @staticmethod
    def format_size(size: int) -> str:
        """格式化文件大小"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units[:-1]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} {units[-1]}"
