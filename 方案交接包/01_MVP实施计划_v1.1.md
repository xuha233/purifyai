# PurifyAI × WinDirStat 智能清理 - MVP 实施计划 v1.1

> **版本**: v1.1 (修复审核反馈)
> **日期**: 2026-02-21
> **预计开发时间**: 13天

---

## 📑 变更说明

基于审核反馈（`审核反馈报告.md`），本版本修复以下问题：

| 问题 | 修复方式 |
|------|---------|
| 问题1: 数据库冗余 | 分离大字段，使用原因表 |
| 问题2: 内存占用估值低 | CleanupItem轻量化，ID索引 |
| 问题3: AI成本未考虑 | 优先规则引擎，降级AI |
| 问题4: 备份设计不完整 | 添加完整BackupManager设计 |
| 问题5: UI线程阻塞 | 使用QThread异步执行 |
| 问题6: 错误恢复不完整 | 添加RecoveryManager |
| 问题7: 性能指标不合理 | 修正为合理基准 |

**时间调整**: 11天 → 13天 (+2天)

---

## 目录

1. [MVP 范围定义](#1-mvp-范围定义)
2. [开发阶段划分](#2-开发阶段划分)
3. [详细任务清单](#3-详细任务清单)
4. [关键问题修复](#4-关键问题修复)
5. [优化功能实现](#5-优化功能实现)
6. [验收标准](#6-验收标准)
7. [风险与缓解](#7-风险与缓解)
8. [V2 版本规划](#8-v2-版本规划)

---

## 1. MVP 范围定义

### 1.1 MVP 包含功能

| 功能模块 | 说明 | 依赖 |
|---------|------|------|
| 智能扫描选择器 | 根据扫描类型选择扫描器 | 现有扫描器 |
| 深度磁盘扫描器 | 基础API扫描 | CustomScanner |
| AI批量分析器 | 风险评估+规则引擎降级 | AI客户端+规则引擎 |
| 智能执行器 | 容错重试执行 | Cleaner |
| 高危确认对话框 | Dangerous项确认 | - |
| 恢复管理器 | 错误恢复机制 | - |
| 备份管理器 | 轻量级备份 | - |

### 1.2 MVP 新增功能（基于审核反馈）

| 功能 | 说明 | 优先级 |
|------|------|-------|
| 扫描进度预估 | 显示剩余时间 | P1 |
| 扫描预检查 | 检查权限等前期问题 | P1 |
| 扫描结果导出 | CSV/JSON导出 | P2 |
| 规则引擎优先 | AI降级策略 | P0 |

### 1.3 MVP 用户体验流程

```
用户打开"智能清理"页面
  ↓
[扫描预检查]
  ├─ 检查路径权限
  ├─ 检查磁盘空间
  └─ 检查路径存在
  ↓
选择扫描类型（系统/浏览器/AppData/自定义）
  ↓
选择扫描目标（路径）
  ↓
[开始智能清理]
  ↓
扫描进行中 → 进度条 + 剩余时间
  ↓
扫描完成 → [规则引擎评估] → [AI评估可疑项]
  ↓
生成清理计划 → 显示统计
  ↓
[高危确认对话框]（如有dangerous项）
  ↓
智能执行清理（带重试+恢复记录）
  ├─ 失败重试3次
  └─ 记录恢复信息
  ↓
执行完成 → 显示简化版报告
  ↓
[结果导出]（可选）
  ├─ 导出CSV
  └─ 导出JSON
  ↓
[完成]
```

---

## 2. 开发阶段划分

| 阶段 | 时间 | 交付物 | 负责人 |
|------|------|--------|-------|
| **Phase 0: 环境准备** | 0.5天 | 开发环境配置 | - |
| **Phase 1: 数据模型与扫描** | 3天 | 数据模型+扫描选择器+基础扫描器+数据库优化 | 开发1 |
| **Phase 2: AI分析与成本控制** | 2.5天 | AI分析器+规则引擎降级 | 开发2 |
| **Phase 3: 执行与恢复** | 3天 | 执行器+RecoveryManager+BackupManager+异步执行 | 开发1 |
| **Phase 4: 报告与优化** | 2.5天 | 报告生成器+报告页面+性能优化 | 开发2 |
| **Phase 5: 测试与验证** | 1.5天 | 端到端测试+验收验证 | 两人 |
| **总计** | **13天** | - | - |

---

## 3. 详细任务清单

### Phase 0: 环境准备 (0.5天)

**任务**:
- [ ] 创建新分支 `feature/smart-clean-mvp`
- [ ] 安装pytest测试框架
- [ ] 确认依赖库版本（PyQt5, QFluentWidgets, openai等）
- [ ] 熟悉现有代码结构
- [ ] 设置开发数据库

**产出**: 开发环境就绪

---

### Phase 1: 数据模型与扫描 (3天)

#### Day 0.5: 数据模型（轻量化）

**问题2修复**: 内存占用优化

**任务**:
- [ ] 创建 `src/core/models_smart.py`
  - [ ] `CleanupItem`（轻量化，只有ID/path/size）
  - [ ] `ItemDetail`（详细信息，按需加载）
  - [ ] `CleanupPlan` 数据类
  - [ ] `ExecutionResult` 数据类
  - [ ] `RecoveryRecord` 数据类
  - [ ] `CleanupStatus` 枚举
  - [ ] `ExecutionStatus` 枚举
- [ ] 编写数据模型单元测试

**预期产出**: `models_smart.py` (~180行)

---

#### Day 1: 数据库优化

**问题1修复**: 数据库冗余

**任务**:
- [ ] 设计优化后的数据库结构
- [ ] 创建数据库迁移脚本
  - [ ] `cleanup_items` 表（主表）
  - [ ] `cleanup_reasons` 表（原因表，共享）
  - [ ] `cleanup_plans` 表
  - [ ] `cleanup_executions` 表
  - [ ] `recovery_log` 表（恢复记录）
- [ ] 更新 `src/core/database.py`
  - [ ] 添加新表创建逻辑
  - [ ] 添加数据插入优化方法

**数据库优化方案**:
```sql
-- 主表（精简）
CREATE TABLE cleanup_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    path TEXT NOT NULL,           -- 仅存储路径
    size INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    original_risk TEXT NOT NULL,
    ai_risk TEXT NOT NULL,
    reason_id INTEGER,            -- 关联索引
    status TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id),
    FOREIGN KEY (reason_id) REFERENCES cleanup_reasons(id)
);

-- 原因表（共享，去重）
CREATE TABLE cleanup_reasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT NOT NULL,         -- 完整原因
    hash TEXT UNIQUE               -- MD5去重
);

-- 恢复记录表
CREATE TABLE recovery_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    original_path TEXT NOT NULL,
    backup_path TEXT,
    backup_type TEXT NOT NULL,   -- 'none', 'hardlink', 'full'
    restored BOOLEAN DEFAULT 0,
    timestamp TEXT NOT NULL
);
```

**预期产出**: 数据库迁移脚本，database.py 更新

---

#### Day 1.5: 监控设计

**任务**:
- [ ] 更新 `src/core/config_manager.py`
  - [ ] 添加数据库配置
  - [ ] 添加AI成本配置
- [ ] 测试数据库连接和操作

**配置扩展**:
```json
{
  "database": {
    "path": "G:\\docker\\diskclean\\src\\data\\purifyai.db",
    "backup_path": "G:\\docker\\diskclean\\src\\data\\purifyai_backup.db",
    "max_items_per_plan": 100000,
    "enable_compression": true
  },
  "ai": {
    "cost_control": {
      "enabled": true,
      "max_calls_per_scan": 100,
      "fallback_to_rules": true,
      "only_suspicious_ai": true
    }
  }
}
```

---

#### Day 2: 扫描器实现

**任务**:
- [ ] 创建 `src/core/smart_scan_selector.py`
  - [ ] `SmartScanSelector` 类
  - [ ] 扫描器选择逻辑
  - [ ] 扫描配置管理
- [ ] 创建 `src/core/depth_disk_scanner.py`
  - [ ] `DepthDiskScanner` 类
  - [ ] 基础API扫描逻辑
  - [ ] 进度信号发射
  - [ ] 目录跳过逻辑
- [ ] 集成到现有扫描器系统
  - [ ] 修改 `scanner.py` 导出
  - [ ] 测试各扫描器选择

**预期产出**:
- `smart_scan_selector.py` (~100行)
- `depth_disk_scanner.py` (~200行)
- 所有单元测试通过

---

#### Day 3: 监控设计

**任务**:
- [ ] 创建扫描进度模块 `src/utils/progress_estimator.py`
  - [ ] `ProgressEstimator` 类
  - [ ] 剩余时间估算
  - [ ] 扫描预检查
- [ ] 测试预估准确性

**预期产出**: `progress_estimator.py` (~150行)

---

### Phase 2: AI分析与成本控制 (2.5天)

#### Day 4: AI分析器（带成本控制）

**问题3修复**: AI成本控制

**任务**:
- [ ] 创建 `src/core/ai_analyzer.py`
  - [ ] `AIAnalyzer` 类
  - [ ] 批量评估逻辑
  - [ ] 提示词构建（复用现有）
  - [ ] 响应解析
- [ ] AI成本控制逻辑
  - [ ] 调用计数器
  - [ ] 超限降级到规则引擎
  - [ ] 疑似项优先调用AI

**AI成本控制策略**:
```python
class AIAnalyzer:
    """AI分析器 - 成本控制版本"""

    def analyze_scan_results(self, items: List[ScanItem]) -> CleanupPlan:
        """
        分析策略:
        1. 规则引擎评估所有项（免费、快速）
        2. 仅对suspicious项调用AI
        3. Safe项直接跳过AI

        成本对比:
        - 全AI: 10万项 → 2000次API
        - 混合: 2万可疑项 → 400次API (~节省80%)
        """
        # 步骤1: 规则引擎评估
        [self._rule_assess(item) for item in items]

        # 步骤2: 筛选可疑项
        suspicious = [i for i in items if i.risk == RiskLevel.SUSPICIOUS]
        dangerous = [i for i in items if i.risk == RiskLevel.DANGEROUS]

        # 步骤3: AI评估可疑项
        if len(suspicious) > 0 and self.ai_call_count < self.max_calls:
            self._ai_assess_batch(suspicious[:50])  # 每批50项

        # 步骤4: Dangerous项保留 Dangerous 风险
```

**预期产出**: `ai_analyzer.py` (~250行)

---

#### Day 5: 规则引擎增强

**任务**:
- [ ] 增强 `src/core/rule_engine.py`
  - [ ] 添加批量评估方法
  - [ ] 添加Suspicious级别识别
  - [ ] 添加reason_id生成（关联到reasons表）
- [ ] 编写规则引擎单元测试
- [ ] 集成测试

**预期产出**: 规则引擎更新 (~80行修改)

---

### Phase 3: 执行与恢复 (3天)

#### Day 5.5: 备份管理器

**问题4修复**: 完整BackupManager设计

**任务**:
- [ ] 创建 `src/core/backup_manager.py`
  - [ ] `BackupManager` 类
  - [ ] 等级差异化备份（Safe不备份、Suspicious硬链接、Dangerous完整）
  - [ ] 备份记录管理
  - [ ] 自动清理（7天）
- [ ] 编写备份管理器测试

**BackupManager设计**:
```python
class BackupManager(QObject):
    """备份管理器"""

    def __init__(self):
        self.backup_root = os.path.expanduser('~/AppData/Local/PurifyAI/Backups')
        self.backup_db = os.path.join(self.backup_root, 'backups.db')
        self._init_database()

    def create_backup(self, item: CleanupItem) -> Optional[BackupInfo]:
        """创建备份（差异化策略）"""
        if item.ai_risk == RiskLevel.SAFE:
            return None  # Safe项不备份

        elif item.ai_risk == RiskLevel.SUSPICIOUS:
            # Suspicious: 创建硬链接（几KB）
            return self._create_hardlink(item)

        else:
            # Dangerous: 完整备份
            return self._create_full_backup(item)

    def get_backup_info(self, plan_id: str, item_id: int) -> Optional[BackupInfo]:
        """获取备份信息"""
        return self.db.execute(
            "SELECT * FROM backups WHERE plan_id=? AND item_id=?",
            (plan_id, item_id)
        ).fetchone()

    def cleanup_old_backups(self, days: int = 7):
        """清理旧备份"""
        cutoff = datetime.now() - timedelta(days=days)
        self.db.execute(
            "DELETE FROM backups WHERE created_at < ?",
            (cutoff.isoformat(),)
        )
```

**预期产出**: `backup_manager.py` (~250行)

---

#### Day 6: 执行器（异步）

**问题5修复**: UI线程阻塞

**任务**:
- [ ] 创建 `src/core/smart_executor.py`
  - [ ] `SmartExecutor` 类（QThread）
  - [ ] 异步执行逻辑
  - [ ] 容错重试机制
  - [ ] 进度信号发射
  - [ ] 失败记录
- [ ] 编写执行器单元测试
- [ ] 测试异步执行性能

**异步执行设计**:
```python
class SmartExecutor(QThread):
    """智能执行器 - 异步版本"""

    progress = pyqtSignal(str)  # 进度信号
    item_completed = pyqtSignal(str, bool)  # path, success
    complete = pyqtSignal(ExecutionResult)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cleaner = Cleaner()
        self.backup_manager = BackupManager()
        self.recovery_manager = RecoveryManager()
        self._is_paused = False
        self._is_cancelled = False

    def run(self):
        """在线程中执行（不阻塞UI）"""
        try:
            result = ExecutionResult(...)

            for item in items_to_execute:
                if self._is_cancelled:
                    break
                while self._is_paused:
                    self.msleep(100)

                success = self._execute_item(item, result)
                self.item_completed.emit(item.path, success)

            self.complete.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True
```

**预期产出**: `smart_executor.py` (~300行)

---

#### Day 7: 恢复管理器

**问题6修复**: 错误恢复机制

**任务**:
- [ ] 创建 `src/core/recovery_manager.py`
  - [ ] `RecoveryManager` 类
  - [ ] 回滚所有操作
  - [ ] 恢复单个项目
- [ ] 编写恢复管理器测试

**RecoveryManager设计**:
```python
class RecoveryManager(QObject):
    """恢复管理器"""

    def __init__(self):
        self.recovery_log: List[RecoveryRecord] = []

    def record_deletion(self, item: CleanupItem, backup_path: str):
        """记录删除操作"""
        record = RecoveryRecord(
            item_id=item.item_id,
            original_path=item.path,
            backup_path=backup_path,
            backup_type=self._get_backup_type(item),
            timestamp=datetime.now()
        )
        self.recovery_log.append(record)

    def rollback_all(self) -> RollbackResult:
        """回滚所有操作"""
        failed_items = []

        for record in reversed(self.recovery_log):
            if not self._restore_record(record):
                failed_items.append(record)

        success_count = len(self.recovery_log) - len(failed_items)
        self.recovery_log.clear()

        return RollbackResult(
            total=len(self.recovery_log),
            success=success_count,
            failed=len(failed_items),
            failed_items=failed_items
        )

    def recover_item(self, plan_id: str, item_id: int) -> bool:
        """恢复单个项目"""
        record = self._get_record(plan_id, item_id)
        if record:
            return self._restore_record(record)
        return False
```

**预期产出**: `recovery_manager.py` (~180行)

---

### Phase 4: 报告与优化 (2.5天)

#### Day 8: UI实现

**任务**:
- [ ] 创建 `src/ui/smart_cleaner.py`
  - [ ] `SmartCleanPage` 类
  - [ ] 扫描设置区域
  - [ ] 进度显示区域（含剩余时间）
  - [ ] 实时统计卡片
- [ ] 创建 `src/ui/high_risk_dialog.py`
  - [ ] `HighRiskConfirmDialog` 类
  - [ ] 高危项列表表格
  - [ ] 全选/全不选按钮
  - [ ] 确认删除/全部保留按钮
- [ ] 集成到主应用
  - [ ] 修改 `app.py` 添加导航栏入口
  - [ ] 连接异步工作流

**预期产出**:
- `smart_cleaner.py` (~450行)
- `high_risk_dialog.py` (~200行)

---

#### Day 8.5: 扫描预检查和导出

**任务**:
- [ ] 创建 `src/utils/scan_prechecker.py`
  - [ ] `ScanPreChecker` 类
  - [ ] 权限检查
  - [ ] 磁盘空间检查
  - [ ] 路径有效性检查
- [ ] 创建 `src/utils/scan_result_exporter.py`
  - [ ] 扫描结果导出
  - [ ] CSV格式导出
  - [ ] JSON格式导出

**预期产出**:
- `scan_prechecker.py` (~100行)
- `scan_result_exporter.py` (~120行)

---

#### Day 9: 报告系统

**任务**:
- [ ] 创建 `src/core/cleanup_report_generator.py`
  - [ ] `CleanupReportGenerator` 类
  - [ ] 统计计算
  - [ ] 报告数据生成
- [ ] 创建 `src/ui/cleanup_report_page.py`
  - [ ] `CleanupReportPage` 类
  - [ ] 统计摘要区域
  - [ ] 失败项列表（可重试）
  - [ ] 恢复功能按钮
- [ ] 数据库扩展和初始化

**预期产出**:
- `cleanup_report_generator.py` (~150行)
- `cleanup_report_page.py` (~350行)

---

#### Day 9.5: 工作流集成

**任务**:
- [ ] 创建 `src/core/smart_clean_workflow.py`
  - [ ] `SmartCleanWorkflow` 类
  - [ ] 完整流程编排
  - [ ] 异步执行协调
  - [ ] 状态管理
- [ ] UI与工作流对接
  - [ ] 连接按钮到工作流
  - [ ] 连接信号（异步回调）
- [ ] 端到端测试

**预期产出**: `smart_clean_workflow.py` (~250行)

---

### Phase 5: 测试与验证 (1.5天)

#### Day 10: 测试

**问题7修复**: 性能指标验证

**任务**:
- [ ] 单元测试完整检查
  - [ ] 数据模型测试
  - [ ] 扫描器测试
  - [ ] AI分析器测试
  - [ ] 执行器测试（异步）
  - [ ] 备份管理器测试
- [ ] 集成测试
  - [ ] 系统垃圾清理流程
  - [ ] AppData清理流程
  - [ ] 自定义路径清理流程
  - [ ] 高危确认流程
- [ ] 性能测试
  - [ ] 1万项扫描（<30秒）
  - [ ] 1000项分析（<1分钟）
  - [ ] 100项清理（<2秒）
  - [ ] 内存占用监控（<300MB）

**修正后的性能指标**:
| 指标 | 目标值 | 说明 |
|------|-------|------|
| 1GB目录扫描 | <20秒 | 基础API |
| 1000项分析 | <1分钟 | 规则引擎为主 |
| 100项清理 | <2秒 | 重试机制 |
| 内存占用 | <300MB | 优化后 |

---

#### Day 11: 单元测试框架

**优化5**: pytest框架

**任务**:
- [ ] 配置pytest测试框架
- [ ] 编写测试用例（每个模块至少5个）
- [ ] 测试覆盖率检查（目标>80%）
- [ ] 性能基准测试

**测试文件结构**:
```
tests/
├── __init__.py
├── conftest.py           # pytest配置
├── fixtures/             # 测试夹具
├── test_models.py        # 数据模型测试
├── test_scanner.py       # 扫描器测试
├── test_ai_analyzer.py   # AI分析器测试
├── test_executor.py      # 执行器测试
├── test_backup.py        # 备份管理器测试
└── test_recovery.py      # 恢复管理器测试
```

**预期产出**: 完整测试套件（~600行）

---

#### Day 11.5: 文档与最终验证

**任务**:
- [ ] 代码审查与最终检查
- [ ] 更新文档
  - [ ] 更新快速对接指南
  - [ ] 更新技术档案
  - [ ] 编写用户使用文档
- [ ] 最终验收测试
- [ ] 性能基准验证

---

### 备用时间 (0.5天)

**任务**:
- [ ] 未完成任务的补充
- [ ] 额外的bug修复
- [ ] 性能优化

---

## 4. 关键问题修复

### 问题1: 数据库设计冗余 ✅修复

**修复方案**: 独立原因表 + 索引

**详见**: Phase 1 - Day 1

| 修复内容 | 影响 |
|---------|------|
| 独立cleanup_reasons表 | 10万项节约90MB |
| reason_id关联索引 | 轻量数据访问 |

---

### 问题2: 内存占用 ✅修复

**修复方案**: CleanupItem轻量化 + ItemDetail

**详见**: Phase 1 - Day 0.5

| 修复内容 | 影响 |
|---------|------|
| CleanupItem仅存核心字段 | 减少内存60% |
| ItemDetail按需加载 | 高峰时缓存可控 |

---

### 问题3: AI成本 ✅修复

**修复方案**: 规则引擎优先，AI降级

**详见**: Phase 2 - Day 4

| 修复内容 | 影响 |
|---------|------|
| 仅20%可疑项调用AI | 节省80%API费用 |
| 超限自动降级 | 成本可控 |

---

### 问题4: 备份管理器 ✅修复

**修复方案**: 完整BackupManager设计

**详见**: Phase 3 - Day 5.5

---

### 问题5: UI线程阻塞 ✅修复

**修复方案**: QThread异步执行

**详见**: Phase 3 - Day 6

---

### 问题6: 错误恢复 ✅修复

**修复方案**: RecoveryManager

**详见**: Phase 3 - Day 7

---

### 问题7: 性能指标 ✅修复

**修复方案**: 修正合理值

| 原指标 | 修正后 | 说明 |
|-------|-------|------|
| 100GB<30秒 | 1GB<20秒 | 调整为合理范围 |
| 10万项<5min | 1000项<1min | 调整为合理范围 |
| >100项/秒 | >50项/秒 | 考虑重试 |
| <500MB | <300MB | 优化后目标 |

---

## 5. 优化功能实现

### 优化1: 扫描进度预估 ✅

**详见**: Phase 1 - Day 3

### 优化2: 扫描预检查 ✅

**详见**: Phase 4 - Day 8.5

### 优化3: 扫描暂停/恢复 ✅

**详见**: Phase 3 - Day 6 (SmartExecutor)

### 优化4: 扫描结果导出 ✅

**详见**: Phase 4 - Day 8.5

### 优化5: pytest框架 ✅

**详见**: Phase 5 - Day 11

---

## 6. 验收标准

### 6.1 功能验收

| 功能 | 验收标准 | 优先级 | 状态 |
|------|---------|:------:|:----:|
| 数据库优化 | 10万项<20MB | P0 | ✅计划 |
| AI成本控制 | API调用<500次/10万项 | P0 | ✅计划 |
| 异步执行 | UI不阻塞 | P0 | ✅计划 |
| 错误恢复 | 可回滚所有操作 | P0 | ✅计划 |
| 备份| 按风险等级备份 | P1 | ✅计划 |
| 扫描预估 | 显示剩余时间 | P1 | ✅计划 |
| 预检查 | 提前检查权限 | P1 | ✅计划 |

### 6.2 性能验收

| 指标 | 目标值 | 测试方法 |
|------|-------|---------|
| 1GB目录扫描 | <20秒 | 性能测试 |
| 1000项分析 | <1分钟 | 性能测试 |
| 100项清理 | <2秒 | 性能测试 |
| 内存占用 | <300MB | 资源监控 |

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:----:|:----:|---------|
| AI API不稳定 | 中 | 高 | ✅ MVP已包含规则引擎降级 |
| 扫描器权限问题 | 高 | 中 | ✅ 添加扫描预检查 |
| 内存占用过高 | 中 | 高 | ✅ 轻量化设计 |
| 异步执行复杂 | 中 | 中 | ✅ 使用QThreadPool |
| 数据库迁移失败 | 低 | 高 | ✅ 提供迁移脚本 |

---

## 8. V2 版本规划

### 8.1 V2 增强功能

| 功能 | 预计时间 | 说明 |
|------|---------|------|
| NTFS MFT扫描 | 3-5天 | 移植MFT，大幅提速 |
| 完整备份机制 | 2-3天 | 完善备份和恢复 |
| Treemap可视化 | 3-4天 | 磁盘空间可视化 |
| 高级报告图表 | 2天 | 饼图、柱图等 |
| AI成本进一步优化 | 2天 | 本地模型或缓存 |

### 8.2 V2 开发时间

**总计**: 12-16天
**MVP + V2**: 25-29天

---

## 附录

### A. 数据库表结构（MVP优化版）

```sql
-- 清理计划表
CREATE TABLE cleanup_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT UNIQUE NOT NULL,
    scan_type TEXT NOT NULL,
    scan_target TEXT NOT NULL,
    total_items INTEGER,
    total_size INTEGER,
    safe_count INTEGER,
    suspicious_count INTEGER,
    dangerous_count INTEGER,
    estimated_freed INTEGER,
    ai_summary TEXT,
    ai_model TEXT,
    ai_call_count INTEGER DEFAULT 0,
    used_rule_engine BOOLEAN DEFAULT 0,
    analyzed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 原因表（共享，用于节省空间）
CREATE TABLE cleanup_reasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT NOT NULL,
    hash TEXT UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 清理项表（主表，轻量化）
CREATE TABLE cleanup_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    original_risk TEXT NOT NULL,
    ai_risk TEXT NOT NULL,
    reason_id INTEGER,  -- 关联原因表
    status TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    cleaned_at TEXT,
    FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id),
    FOREIGN KEY (reason_id) REFERENCES cleanup_reasons(id)
);

-- 恢复记录表
CREATE TABLE recovery_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    original_path TEXT NOT NULL,
    backup_path TEXT,
    backup_type TEXT NOT NULL,
    restored BOOLEAN DEFAULT 0,
    timestamp TEXT NOT NULL
);

-- 执行结果表
CREATE TABLE cleanup_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_items INTEGER,
    success_items INTEGER,
    failed_items INTEGER,
    skipped_items INTEGER,
    total_size INTEGER,
    freed_size INTEGER,
    failed_size INTEGER,
    status TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id)
);
```

---

**文档版本**: v1.1
**最后更新**: 2026-02-21
**审核状态**: 修复后待复审
