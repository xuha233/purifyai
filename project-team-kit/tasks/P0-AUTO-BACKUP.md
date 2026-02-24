# P0-2: 自动备份系统

**任务类型：** 核心功能（P0）
**优先级：** 最高
**预计时间：** 1 天
**负责人：** Claude Code（后端）
**前端测试：** OpenCode
**开始时间：** 2026-02-24 13:10

---

## 📋 任务目标

实现自动备份系统，确保清理操作的安全性，支持一键撤销功能。

---

## 🎯 核心功能

### 1. 备份触发时机
- ✅ 清理前自动备份（P0-1 CleanupOrchestrator 已集成）
- ✅ 定时自动备份
- ✅ 手动触发备份

### 2. 备份内容
- ✅ 文件内容
- ✅ 文件元数据（权限、时间戳）
- ✅ 目录结构
- ✅ 备份清单

### 3. 备份存储
- ✅ 压缩存储（节省空间）
- ✅ 版本管理（保留最近 N 个版本）
- ✅ 自动清理过期备份

### 4. 恢复功能
- ✅ 单文件恢复
- ✅ 批量恢复
- ✅ 选择性恢复

---

## 📐 数据结构

### BackupProfile

```python
@dataclass
class BackupProfile:
    """备份配置"""
    profile_id: str
    name: str                                    # 备份配置名称
    backup_paths: List[str]                      # 备份路径列表
    exclude_patterns: List[str]                 # 排除模式
    compression_level: int                       # 压缩级别 (0-9)
    retention_days: int                          # 保留天数
    max_versions: int                            # 最大版本数
    schedule: str                                # 备份计划 (cron 表达式)
    enabled: bool
    created_at: datetime
    updated_at: datetime
```

### BackupManifest

```python
@dataclass
class BackupManifest:
    """备份清单"""
    manifest_id: str
    backup_id: str
    files: List[BackupFileInfo]
    total_size: int
    compressed_size: int
    created_at: datetime
```

### BackupFileInfo

```python
@dataclass
class BackupFileInfo:
    """备份文件信息"""
    original_path: str
    backup_path: str
    size: int
    compressed_size: int
    checksum: str                                # SHA256
    permissions: int
    modified_time: float
```

---

## 🔧 实施步骤

### Part 1: BackupManager 增强（30 分钟）

**文件：** `src/core/backup_manager.py`

**现有功能：**
- `backup_file(path, backup_path)` - 单文件备份
- `restore_file(backup_path, target_path)` - 单文件恢复

**需要添加：**

1. `backup_profile(profile: BackupProfile, files: List[str]) -> BackupManifest`
   - 根据配置创建备份清单
   - 批量备份文件
   - 生成压缩包

2. `backup_system(paths: List[str], exclude: List[str]) -> BackupManifest`
   - 系统级备份
   - 支持排除模式

3. `restore_from_manifest(manifest: BackupManifest, files: Optional[List[str]] = None)`
   - 从清单恢复
   - 支持选择性恢复

4. `get_backup_history(days: int = 30) -> List[BackupManifest]`
   - 获取备份历史

5. `cleanup_old_backups(retention_days: int, max_versions: int)`
   - 清理过期备份

---

### Part 2: 备份调度器（20 分钟）

**文件：** `src/core/backup_scheduler.py`

**实现类：**

```python
class BackupScheduler:
    """备份调度器"""

    def __init__(self, backup_dir: str):
        self.backup_dir = backup_dir
        self.active_profiles: Dict[str, BackupProfile] = {}
        self.scheduled_tasks: List[Dict] = []

    def add_profile(self, profile: BackupProfile):
        """添加备份配置"""

    def remove_profile(self, profile_id: str):
        """移除备份配置"""

    def start(self):
        """启动调度器"""

    def stop(self):
        """停止调度器"""

    def trigger_manual_backup(self, profile_id: str) -> BackupManifest:
        """手动触发备份"""

    def get_next_run_time(self, profile_id: str) -> Optional[datetime]:
        """获取下次运行时间"""
```

---

### Part 3: 集成到 CleanupOrchestrator（10 分钟）

**文件：** `src/agent/cleanup_orchestrator.py`

**修改：**

1. 增强 `backup_before_cleanup()` 方法
   - 使用增强的 BackupManager
   - 返回 BackupManifest
   - 记录到 CleanupReport

2. 添加 `get_cleanup_backups()` 方法
   - 获取与清理相关的备份

---

## 📝 实现要点

### 1. 压缩存储

使用 `zipfile` 模块：
```python
import zipfile

def create_backup_zip(backup_id: str, files: List[BackupFileInfo]) -> str:
    zip_path = os.path.join(backup_dir, f"{backup_id}.zip")
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for file_info in files:
            zf.write(file_info.backup_path, arcname=file_info.original_path)
    return zip_path
```

### 2. 校验和计算

```python
import hashlib

def calculate_checksum(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        sha256.update(f.read())
    return sha256.hexdigest()
```

### 3. Cron 表达式解析

使用 `schedule` 或 `apscheduler`：
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    backup_function,
    'cron',
    hour=cron.hour,
    minute=cron.minute,
    id=profile_id
)
```

---

## ✅ 验收标准

1. ✅ 备份配置创建和管理
2. ✅ 自动备份触发（定时 + 清理前）
3. ✅ 备份压缩存储
4. ✅ 备份清单记录
5. ✅ 恢复功能（单文件 + 批量）
6. ✅ 备份历史查询
7. ✅ 过期备份清理
8. ✅ 集成到 CleanupOrchestrator
9. ✅ 单元测试覆盖率 > 80%
10. ✅ 代码编译通过

---

## 📊 测试用例

**文件：** `tests/test_backup_manager.py`

```python
def test_backup_single_file():
    """测试单文件备份"""

def test_backup_profile():
    """测试配置备份"""

def test_backup_compression():
    """测试备份压缩"""

def test_restore_from_manifest():
    """测试从清单恢复"""

def test_cleanup_old_backups():
    """测试清理过期备份"""

def test_backup_scheduler():
    """测试备份调度器"""
```

---

## 🎨 UI 集成（后续）

**文件：** `src/pages/backup_page.py`

**功能：**
- 备份配置列表
- 创建/编辑/删除备份配置
- 备份历史查看
- 手动触发备份
- 恢复操作

---

## 📅 后续任务

### 依赖任务
- ✅ P0-1 CleanupOrchestrator 已完成

### 后续任务
- P0-3 一键撤销功能（依赖本任务）
- P0-4 增量清理模式

---

**任务状态：** 🟡 待开始
**创建时间：** 2026-02-24 13:10
**预计开始：** 2026-02-24 13:12（OpenCode 完成 P0-1 Part 3 后立即开始）
