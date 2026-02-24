# -*- coding: utf-8 -*-
"""
智能推荐模块 (Smart Recommender)

实现用户画像、清理计划生成和智能推荐算法

作者: 小午 🦁
创建时间: 2026-02-24
"""

import os
import uuid
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Set
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from ..core.models import ScanItem
from ..core.scanner import Scanner
from ..core.risk_assessment import RiskAssessmentSystem


# ============================================================================
# 枚举定义
# ============================================================================

class UserScenario(Enum):
    """用户场景"""
    GAMING = "gaming"           # 游戏玩家
    OFFICE = "office"           # 办公电脑
    DEVELOPER = "developer"     # 开发环境
    GENERAL = "general"         # 普通用户

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            UserScenario.GAMING: "游戏玩家",
            UserScenario.OFFICE: "办公电脑",
            UserScenario.DEVELOPER: "开发环境",
            UserScenario.GENERAL: "普通用户"
        }
        return names.get(self, self.value)


class CleanupMode(Enum):
    """清理模式"""
    CONSERVATIVE = "conservative"  # 保守模式
    BALANCED = "balanced"          # 平衡模式
    AGGRESSIVE = "aggressive"     # 激进模式

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            CleanupMode.CONSERVATIVE: "保守模式",
            CleanupMode.BALANCED: "平衡模式",
            CleanupMode.AGGRESSIVE: "激进模式"
        }
        return names.get(self, self.value)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    installed_packages: List[str] = field(default_factory=list)
    disk_usage: Dict[str, float] = field(default_factory=dict)
    cleanup_history: List[str] = field(default_factory=list)
    last_cleanup_time: Optional[datetime] = None
    preferred_mode: str = CleanupMode.BALANCED.value
    scenario: str = UserScenario.GENERAL.value
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CleanupPlan:
    """清理计划"""
    plan_id: str
    items: List[ScanItem] = field(default_factory=list)
    estimated_space: int = 0
    risk_percentage: float = 0.0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    recommended: bool = False
    mode: str = CleanupMode.BALANCED.value
    is_incremental: bool = False  # 是否为增量清理
    base_plan_id: Optional[str] = None  # 基础清理计划ID（增量清理时使用）
    created_at: datetime = field(default_factory=datetime.now)

    def calculate_stats(self):
        """计算统计数据"""
        self.estimated_space = sum(item.size for item in self.items)
        self.high_risk_count = sum(1 for item in self.items if item.risk_level in ['dangerous', 'suspicious'])
        self.medium_risk_count = sum(1 for item in self.items if item.risk_level == 'suspicious')
        self.low_risk_count = sum(1 for item in self.items if item.risk_level == 'safe')
        total = len(self.items)
        self.risk_percentage = (self.high_risk_count / total * 100) if total > 0 else 0.0


# ============================================================================
# 智能推荐器
# ============================================================================

class SmartRecommender:
    """智能推荐器

    功能：
    1. 构建用户画像（安装的软件、磁盘使用、清理历史）
    2. 检测用户场景（游戏/办公/开发/普通）
    3. 根据场景和模式推荐清理计划
    4. 支持增量清理（只清理新文件）
    """

    # 用户场景识别规则
    SCENARIO_RULES = {
        UserScenario.GAMING: {
            'keywords': ['Steam', 'Epic Games', 'Ubisoft', 'Origin', 'Battle.net'],
            'directories': [
                r'C:\Program Files (x86)\Steam',
                r'C:\Program Files (x86)\Epic Games',
                r'C:\Program Files (x86)\Ubisoft',
            ],
            'scan_paths': [
                r'C:\Program Files (x86)\Steam\steamapps\downloading',
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp'),
            ],
        },
        UserScenario.OFFICE: {
            'keywords': ['Office', 'WPS', 'Notion', 'LibreOffice'],
            'directories': [
                r'C:\Program Files\Microsoft Office',
                r'C:\Program Files\WPS Office',
            ],
            'scan_paths': [
                os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Microsoft', 'Word'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Microsoft', 'Excel'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp'),
            ],
        },
        UserScenario.DEVELOPER: {
            'keywords': ['Python', 'Node.js', 'Docker', 'Git', 'Visual Studio', 'IntelliJ'],
            'directories': [
                os.path.join(os.path.expanduser('~'), '.python'),
                os.path.join(os.path.expanduser('~'), '.npm'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'npm'),
            ],
            'scan_paths': [
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', 'pip'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', 'npm'),
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', '__pycache__'),
            ],
        },
        UserScenario.GENERAL: {
            'keywords': [],
            'directories': [],
            'scan_paths': [
                r'C:\Windows\Temp',
                os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp'),
            ],
        },
    }

    # 清理模式阈值
    MODE_THRESHOLDS = {
        CleanupMode.CONSERVATIVE: {
            'max_risk': 10,           # 只清理风险值 < 10 的文件
            'max_file_size': 50 * 1024 * 1024,  # 最大文件大小 50MB
            'skip_system': True,      # 跳过系统文件
        },
        CleanupMode.BALANCED: {
            'max_risk': 30,           # 清理风险值 < 30 的文件
            'max_file_size': None,    # 无大小限制
            'skip_system': True,      # 跳过系统文件
        },
        CleanupMode.AGGRESSIVE: {
            'max_risk': 70,           # 清理风险值 < 70 的文件
            'max_file_size': None,    # 无大小限制
            'skip_system': False,     # 不跳过系统文件（除了关键文件）
        },
    }

    # 预设过滤规则
    PROFILE_FILTERS = {
        'gaming': [
            lambda x: 'Games' in x.path,
            lambda x: 'Cache' in x.path,
            lambda x: 'downloading' in x.path.lower(),
        ],
        'office': [
            lambda x: 'Office' in x.path,
            lambda x: '.tmp' in x.path.lower(),
            lambda x: '~$' in x.path,  # Office 临时文件
        ],
        'developer': [
            lambda x: 'node_modules' in x.path,
            lambda x: '__pycache__' in x.path,
            lambda x: '.pyc' in x.path,
            lambda x: 'pip' in x.path,
        ],
        'general': [
            lambda x: 'Temp' in x.path,
            lambda x: 'Cache' in x.path,
            lambda x: '.tmp' in x.path.lower(),
        ],
    }

    def __init__(self):
        """初始化智能推荐器"""
        self.scanner = Scanner()
        self.risk_system = RiskAssessmentSystem()
        self.profile_cache: Optional[UserProfile] = None

    def build_user_profile(self) -> UserProfile:
        """构建用户画像

        步骤：
        1. 扫描常用软件目录
        2. 识别用户场景（游戏/办公/开发）
        3. 分析磁盘使用情况
        4. 加载清理历史
        """
        user_id = self._generate_user_id()
        installed_packages = self._scan_installed_packages()
        scenario = self.detect_user_scenario_from_packages(installed_packages)
        disk_usage = self._analyze_disk_usage()
        cleanup_history = self._load_cleanup_history()
        last_cleanup_time = self._get_last_cleanup_time()

        profile = UserProfile(
            user_id=user_id,
            installed_packages=installed_packages,
            disk_usage=disk_usage,
            cleanup_history=cleanup_history,
            last_cleanup_time=last_cleanup_time,
            scenario=scenario.value,
            updated_at=datetime.now()
        )

        self.profile_cache = profile
        return profile

    def detect_user_scenario(self, profile: UserProfile) -> UserScenario:
        """检测用户场景"""
        # 如果扫描时已经检测到，直接返回
        if profile.scenario:
            return UserScenario(profile.scenario)

        # 基于安装的软件识别
        return self.detect_user_scenario_from_packages(profile.installed_packages)

    def detect_user_scenario_from_packages(self, packages: List[str]) -> UserScenario:
        """从安装的软件包检测用户场景"""
        for scenario, rules in self.SCENARIO_RULES.items():
            for keyword in rules['keywords']:
                for package in packages:
                    if keyword.lower() in package.lower():
                        return scenario

        return UserScenario.GENERAL

    def recommend(self, profile: UserProfile, mode: str = CleanupMode.BALANCED.value) -> CleanupPlan:
        """推荐清理计划

        步骤：
        1. 扫描系统
        2. 根据用户场景过滤文件
        3. 计算风险等级
        4. 生成清理计划
        """
        plan_id = str(uuid.uuid4())
        scenario = UserScenario(profile.scenario)
        rules = self.SCENARIO_RULES.get(scenario, self.SCENARIO_RULES[UserScenario.GENERAL])

        # 扫描目标路径
        all_items = []
        for scan_path in rules['scan_paths']:
            if os.path.exists(scan_path):
                try:
                    items = self.scanner.scan_recursive(scan_path, max_depth=3)
                    all_items.extend(items)
                except Exception as e:
                    print(f"[SmartRecommender] 扫描失败: {scan_path}, 错误: {e}")

        # 根据用户场景过滤
        filtered_items = self.filter_by_profile(all_items, scenario.value)

        # 根据清理模式过滤
        mode_enum = CleanupMode(mode)
        mode_rule = self.MODE_THRESHOLDS.get(mode_enum, self.MODE_THRESHOLDS[CleanupMode.BALANCED])
        filtered_items = self.filter_by_mode(filtered_items, mode_rule)

        # 评估风险
        for item in filtered_items:
            risk = self.risk_system.assess_risk(item)
            item.risk_level = risk.level.value

        # 创建清理计划
        plan = CleanupPlan(
            plan_id=plan_id,
            items=filtered_items,
            mode=mode,
            recommended=True,
        )
        plan.calculate_stats()

        return plan

    def recommend_incremental(self, mode: str = CleanupMode.BALANCED.value) -> CleanupPlan:
        """增量推荐（只清理上次清理后新增的文件）

        步骤：
        1. 扫描系统并生成基础清理计划
        2. 加载上次清理的文件列表
        3. 过滤出新增文件（在上次清理列表中不存在的文件）
        4. 生成清理计划

        返回的 CleanupPlan 特点：
        - items: 只包含上次清理后新增的可清理文件
        - estimated_space: 新增文件的总大小
        - risk_percentage/high_risk_count/等: 仅基于新增文件计算

        边界情况：
        - last_cleanup_files.json 不存在: 全部文件都是新文件
        - 某些文件已删除: 这些文件不在扫描结果中，不影响增量逻辑
        """
        if self.profile_cache is None:
            self.profile_cache = self.build_user_profile()

        # 获取基础清理计划（包含所有符合条件文件）
        base_plan = self.recommend(self.profile_cache, mode)

        # 加载上次清理的文件列表，转换为 set 提高查找效率
        last_cleanup_files = set(self.load_last_cleanup_files())

        # 过滤出新增文件（不在上次清理列表中的文件）
        new_items = [item for item in base_plan.items if item.path not in last_cleanup_files]

        # 创建增量清理计划
        incremental_plan = CleanupPlan(
            plan_id=str(uuid.uuid4()),
            items=new_items,
            mode=mode,
            recommended=True,
            is_incremental=True,
            base_plan_id=base_plan.plan_id,
        )
        incremental_plan.calculate_stats()

        return incremental_plan

    def filter_by_profile(self, items: List[ScanItem], profile: str) -> List[ScanItem]:
        """根据用户场景过滤文件"""
        filters = self.PROFILE_FILTERS.get(profile, self.PROFILE_FILTERS['general'])
        filtered = []

        for item in items:
            # 检查是否匹配任意一个过滤器
            for filter_func in filters:
                try:
                    if filter_func(item):
                        filtered.append(item)
                        break
                except Exception:
                    continue

        return filtered

    def filter_by_mode(self, items: List[ScanItem], mode_rule: Dict) -> List[ScanItem]:
        """根据清理模式过滤文件"""
        filtered = []

        for item in items:
            # 检查文件大小限制
            if mode_rule.get('max_file_size') and item.size > mode_rule['max_file_size']:
                continue

            # 检查系统文件
            if mode_rule.get('skip_system'):
                path_lower = item.path.lower()
                if any(sys_dir in path_lower for sys_dir in ['windows', 'program files', 'system32']):
                    continue

            # 风险值检查在评估时完成
            filtered.append(item)

        return filtered

    def _generate_user_id(self) -> str:
        """生成用户 ID"""
        import hashlib
        import socket
        hostname = socket.gethostname()
        return hashlib.md5(hostname.encode()).hexdigest()

    def _scan_installed_packages(self) -> List[str]:
        """扫描常用软件目录"""
        packages = []

        # 扫描 Program Files
        common_dirs = [
            r'C:\Program Files',
            r'C:\Program Files (x86)',
        ]

        for base_dir in common_dirs:
            if os.path.exists(base_dir):
                try:
                    for item in os.listdir(base_dir):
                        item_path = os.path.join(base_dir, item)
                        if os.path.isdir(item_path):
                            packages.append(item)
                except Exception as e:
                    print(f"[SmartRecommender] 扫描失败: {base_dir}, 错误: {e}")

        return packages

    def _analyze_disk_usage(self) -> Dict[str, float]:
        """分析磁盘使用情况"""
        usage = {}

        drives = [f"{d}:\\" for d in "CDEFG" if os.path.exists(f"{d}:\\")]
        for drive in drives:
            try:
                stat = os.statvfs(drive) if hasattr(os, 'statvfs') else None
                if stat:
                    total = stat.f_blocks * stat.f_frsize
                    free = stat.f_bavail * stat.f_frsize
                    usage[drive] = ((total - free) / total) * 100
                else:
                    # Windows 备用方案
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(drive),
                        None,
                        ctypes.byref(total_bytes),
                        ctypes.byref(free_bytes)
                    )
                    usage[drive] = ((total_bytes.value - free_bytes.value) / total_bytes.value) * 100
            except Exception as e:
                print(f"[SmartRecommender] 分析磁盘失败: {drive}, 错误: {e}")

        return usage

    def _load_cleanup_history(self) -> List[str]:
        """加载清理历史"""
        history_file = os.path.join(os.path.expanduser('~'), '.purifyai', 'cleanup_history.json')
        history = []

        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    history = data.get('history', [])
            except Exception as e:
                print(f"[SmartRecommender] 加载历史失败: {e}")

        return history

    def _get_last_cleanup_time(self) -> Optional[datetime]:
        """获取最后一次清理时间"""
        history_file = os.path.join(os.path.expanduser('~'), '.purifyai', 'cleanup_history.json')

        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_time = data.get('last_cleanup')
                    if last_time:
                        return datetime.fromisoformat(last_time)
            except Exception:
                pass

        return None

    def load_last_cleanup_files(self) -> List[str]:
        """从 data/last_cleanup_files.json 读取上次清理的文件列表

        Returns:
            List[str]: 上次清理的文件列表，文件不存在时返回空列表
        """
        data_dir = os.path.join('data')
        files_path = os.path.join(data_dir, 'last_cleanup_files.json')

        if not os.path.exists(files_path):
            return []

        try:
            with open(files_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('files', [])
        except Exception as e:
            print(f"[SmartRecommender] 加载清理文件列表失败: {e}")
            return []

    def save_last_cleanup_files(self, files: List[str]) -> None:
        """将文件列表保存到 data/last_cleanup_files.json

        Args:
            files: 要保存的文件列表
        """
        data_dir = os.path.join('data')
        files_path = os.path.join(data_dir, 'last_cleanup_files.json')

        # 自动创建 data 目录（如果不存在）
        os.makedirs(data_dir, exist_ok=True)

        try:
            with open(files_path, 'w', encoding='utf-8') as f:
                json.dump({'files': files}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SmartRecommender] 保存清理文件列表失败: {e}")
