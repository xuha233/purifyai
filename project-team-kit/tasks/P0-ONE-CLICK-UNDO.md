# P0-3: 一键撤销功能 - 任务书

**优先级：** 🔴 P0
**负责人：** Claude Code
**预计工时：** 4 小时
**依赖：** P0-1（一键清理）✅ + P0-2（自动备份系统）✅

---

## 📋 任务目标

实现一键撤销功能，允许用户在清理后 30 天内撤销清理操作，将文件从备份恢复到原位置。

---

## 🎯 核心功能

### 1. 撤销操作恢复
- 根据 CleanupReport 查找备份
- 选择性恢复文件
- 支持批量恢复（全部恢复）

### 2. 撤销状态管理
- 30 天撤销时限检查
- 撤销历史记录
- 备份有效性验证

### 3. 撤销 UI 交互
- 撤销按钮（已在 CleanupProgressWidget 中）
- 撤销进度显示
- 撤销结果反馈

---

## 📊 数据结构

### 1. RestoreSession（恢复会话）

```python
@dataclass
class RestoreSession:
    """文件恢复会话"""

    session_id: str              # 会话 ID
    backup_id: str               # 备份 ID（来自 CleanupReport）
    restore_mode: str            # 恢复模式：all, selected
    files: List[str]             # 选中的文件列表
    total_files: int             # 总文件数
    restored_files: int          # 已恢复文件数
    failed_files: int            # 恢复失败数
    status: str                  # 状态：pending, restoring, completed, failed
    created_at: datetime         # 创建时间
    completed_at: Optional[datetime] = None  # 完成时间
```

### 2. UndoHistory（撤销历史）

```python
@dataclass
class UndoHistory:
    """撤销历史记录"""

    cleanup_report_id: str      # 清理报告 ID
    backup_id: str               # 备份 ID
    cleanup_time: datetime       # 清理时间
    undo_time: Optional[datetime]  # 撤销时间
    can_undo: bool               # 是否可撤销（30 天内）
    status: str                  # 状态：available, undone, expired
```

---

## 🏗️ 实施步骤

### Part 1: 撤销管理器实现（2 小时）

**目标文件：** `src/core/restore_manager.py`

**实现类：** `RestoreManager`

**主要方法：**

#### 1.1 `create_restore_session(backup_id: str, files: Optional[List[str]] = None) -> RestoreSession`
**功能：** 创建恢复会话
**参数：**
- `backup_id`: 备份 ID
- `files`: 可选，指定的文件列表（None 表示全部恢复）

**返回：** RestoreSession 对象

**实现要点：**
- 根据 backup_id 加载 BackupManifest
- 验证备份有效性
- 创建 RestoreSession 对象
- 保存会话到文件（restore_sessions.json）

#### 1.2 `execute_restore(session_id: str) -> bool`
**功能：** 执行恢复操作
**参数：**
- `session_id`: 会话 ID

**返回：** 是否成功

**实现要点：**
- 加载 RestoreSession
- 调用 BackupManager.restore_from_manifest()
- 更新会话状态
- 返回恢复结果

#### 1.3 `get_undo_history(cleanup_report_id: Optional[str] = None) -> List[UndoHistory]`
**功能：** 获取撤销历史
**参数：**
- `cleanup_report_id`: 可选，指定的清理报告 ID

**返回：** UndoHistory 列表

**实现要点：**
- 读取 CleanupReport 历史（从 cleanup_orchestrator.py）
- 提取备份信息
- 检查 30 天有效期
- 生成 UndoHistory 列表

#### 1.4 `check_undo_validity(cleanup_report: CleanupReport) -> bool`
**功能：** 检查清理报告是否可撤销
**参数：**
- `cleanup_report`: 清理报告

**返回：** 是否可撤销

**实现要点：**
- 检查 completed_at 是否存在
- 检查是否在 30 天内
- 检查备份是否存在

---

### Part 2: 撤销信号定义（30 分钟）

**目标文件：** `src/core/signals.py`（如果不存在则创建）

**定义信号：** `RestoreSignal`

**信号类型：**

```python
class RestoreSignal(QObject):
    """文件恢复信号"""

    progress_updated = pyqtSignal(int, str)  # (percent, status)
    file_restored = pyqtSignal(str, bool)  # (path, success)
    restore_completed = pyqtSignal(RestoreSession)  # 会话完成
    restore_failed = pyqtSignal(str)  # (error_message)
```

---

### Part 3: 撤销 UI 组件（1 小时）

**目标文件：** `src/ui/restore_dialog.py`

**实现类：** `RestoreDialog`

**主要功能：**

#### 3.1 显示撤销历史列表
- 表格显示：清理时间、清理报告 ID、备份 ID、是否可撤销
- 可点击"撤销"按钮

#### 3.2 显示文件恢复进度
- 进度条
- 当前文件路径
- 成功/失败统计

#### 3.3 显示恢复结果
- 恢复成功提示
- 恢复失败详情
- 重试按钮

---

### Part 4: 集成到 CleanupProgressWidget（30 分钟）

**目标文件：** `src/ui/cleanup_progress_widget.py`

**修改内容：**

#### 4.1 完善 `_on_undo()` 方法
- 显示 RestoreDialog
- 创建 RestoreManager
- 执行恢复操作
- 更新 UI 状态

**参考现有实现（已有基础）：**
```python
def _on_undo(self):
    """撤销清理"""
    if self.current_report and self._can_undo(self.current_report):
        # TODO: 实现撤销逻辑
        # 1. 查找对应的备份
        # 2. 从备份恢复文件
        # 3. 更新清理历史
```

---

## 📝 验收标准

### 功能验收
- [ ] 能根据 CleanupReport 找到对应的备份
- [ ] 能成功恢复文件到原位置
- [ ] 能选择性恢复部分文件
- [ ] 能正确检查 30 天有效期
- [ ] 超过 30 天的清理报告无法撤销

### UI 验收
- [ ] 撤销按钮在 30 天内可点击
- [ ] 超过 30 天禁用并提示
- [ ] 显示恢复进度
- [ ] 显示恢复结果（成功/失败）
- [ ] InfoBar 提示清晰

### 代码质量
- [ ] 类型注解完整
- [ ] 文档字符串齐全
- [ ] 错误处理完善
- [ ] 日志记录完整
- [ ] 编译通过

---

## 🧪 测试用例

### 测试用例 1：恢复全部文件
**场景：** 用户点击"撤销清理"按钮，恢复全部文件

**步骤：**
1. 执行清理操作（生成 CleanupReport 和备份）
2. 点击"撤销清理"按钮
3. 确认恢复操作
4. 查看恢复进度
5. 验证文件已恢复到原位置

**预期结果：**
- 文件成功恢复
- 撤销历史记录更新
- UI 显示恢复成功

---

### 测试用例 2：恢复部分文件
**场景：** 用户选择部分文件进行恢复

**步骤：**
1. 执行清理操作
2. 显示 RestoreDialog
3. 选择部分文件
4. 执行恢复
5. 验证选中文件已恢复

**预期结果：**
- 选中文件成功恢复
- 未选中文件保持已清理状态

---

### 测试用例 3：30 天有效期检查
**场景：** 尝试撤销超过 30 天的清理操作

**步骤：**
1. 修改 CleanupReport.completed_at 为 31 天前
2. 尝试撤销
3. 查看提示信息

**预期结果：**
- 撤销按钮禁用
- 提示"此清理操作已超过 30 天，无法撤销"

---

### 测试用例 4：备份文件丢失
**场景：** 备份文件已删除，尝试撤销

**步骤：**
1. 执行清理操作
2. 手动删除备份文件
3. 尝试撤销
4. 查看错误提示

**预期结果：**
- 显示错误信息
- 提示备份文件不存在

---

## ⚠️ 注意事项

### 1. 备份文件位置
- 备份文件路径：`data/backups/`
- 备份清单：`data/backups/manifests/`

### 2. CleanupReport 存储位置
- 清理报告存储在 `CleanupOrchestrator` 中
- 需要从 CleanupOrchestrator 获取清理报告

### 3. 撤销历史持久化
- 撤销历史需要持久化到文件
- 建议：`data/cleanup_reports.json`

### 4. 错误处理
- 备份文件不存在 → 提示用户
- 恢复失败 → 显示详细错误信息
- 权限不足 → 提示以管理员身份运行

---

## 📚 参考资料

### 已完成的功能
- `BackupManager` (src/core/backup_manager.py)
  - `restore_from_manifest()` - 从清单恢复
  - `restore_backup()` - 通过 backup_id 恢复

- `CleanupOrchestrator` (src/agent/cleanup_orchestrator.py)
  - `CleanupReport` - 清理报告
  - `CleanupSignal` - 清理信号

### UI 组件
- `CleanupProgressWidget` (src/ui/cleanup_progress_widget.py)
  - `_on_undo()` - 撤销按钮处理（已有基础实现）

---

## 🎉 完成标志

- [x] [ ] RestoreManager 实现完成
- [x] [ ] RestoreSignal 信号定义完成
- [x] [ ] RestoreDialog UI 组件完成
- [x] [ ] 集成到 CleanupProgressWidget 完成
- [x] [ ] 所有测试用例通过
- [x] [ ] 代码编译通过
- [x] [ ] 文档更新（README.md）

---

**开始时间：** 2026-02-24 14:00
**预计完成时间：** 2026-02-24 18:00
**负责人：** Claude Code
**执行模式：** 小午调度，Claude Code 执行
