# PurifyAI × WinDirStat 智能清理 - MVP 实施计划

> **版本**: v1.0
> **日期**: 2026-02-21
> **预计开发时间**: 11天

---

## 目录

1. [MVP 范围定义](#1-mvp-范围定义)
2. [开发阶段划分](#2-开发阶段划分)
3. [详细任务清单](#3-详细任务清单)
4. [验收标准](#4-验收标准)
5. [风险与缓解](#5-风险与缓解)
6. [V2 版本规划](#6-v2-版本规划)

---

## 1. MVP 范围定义

### 1.1 MVP 包含功能

| 功能模块 | 说明 | 依赖 |
|---------|------|------|
| 智能扫描选择器 | 根据扫描类型选择扫描器 | 现有扫描器 |
| 深度磁盘扫描器 | 基础API扫描（NTFS MFT延后） | CustomScanner |
| AI批量分析器 | 风险评估+规则引擎降级 | AI客户端+规则引擎 |
| 智能执行器 | 容错重试执行（无备份） | Cleaner |
| 高危确认对话框 | Dangerous项确认 | - |
| 简化版报告 | 统计+失败项列表 | Database |

### 1.2 MVP 不包含功能

| 功能 | 计划版本 | 原因 |
|------|---------|------|
| NTFS MFT快速扫描 | V2 | 需要单独开发，先验证MVP |
| 完整备份机制 | V2 | MVP 简化为硬链接备份 |
| Treemap可视化 | V2 | 开发复杂，非核心功能 |
| 高级报告图表 | V2 | MVP 先用统计列表 |

### 1.3 MVP 用户体验流程

```
用户打开"智能清理"页面
  ↓
选择扫描类型（系统/浏览器/AppData/自定义）
  ↓
选择扫描目标（路径）
  ↓
[开始智能清理]
  ↓
扫描进行中 → 进度条显示
  ↓
扫描完成 → AI分析
  ├─ AI成功→ 生成清理计划
  └─ AI失败→ 规则引擎降级
  ↓
[高危确认对话框]（如有dangerous项）
  ↓
智能执行清理（带重试）
  ↓
执行完成 → 显示简化版报告
  ↓
[完成]
```

---

## 2. 开发阶段划分

| 阶段 | 时间 | 交付物 | 负责人 |
|------|------|--------|-------|
| **Phase 0: 环境准备** | 0.5天 | 开发环境配置 | - |
| **Phase 1: 数据模型与扫描** | 2天 | 数据模型+扫描选择器+基础扫描器 | 开发1 |
| **Phase 2: AI分析** | 2天 | AI分析器+规则引擎降级 | 开发2 |
| **Phase 3: 执行器与UI** | 2.5天 | 执行器+主页面+确认对话框 | 开发1 |
| **Phase 4: 报告与集成** | 2天 | 报告生成器+报告页面+集成测试 | 开发2 |
| **Phase 5: 测试与优化** | 2天 | 端到端测试+性能优化 | 两人 |
| **总计** | **11天** | - | - |

---

## 3. 详细任务清单

### Phase 0: 环境准备 (0.5天)

**任务**:
- [ ] 创建新分支 `feature/smart-clean-mvp`
- [ ] 确认依赖库版本（PyQt5, QFluentWidgets, openai等）
- [ ] 熟悉现有代码结构（Scanner, Cleaner, AI模块）
- [ ] 设置开发数据库（测试用）

**产出**:
- 开发环境就绪
- 代码分支创建成功

---

### Phase 1: 数据模型与扫描 (2天)

#### Day 1: 数据模型定义

**任务**:
- [ ] 创建 `src/core/models_smart.py`
  - [ ] `CleanupItem` 数据类
  - [ ] `CleanupPlan` 数据类
  - [ ] `ExecutionResult` 数据类
  - [ ] `FailureInfo` 数据类
  - [ ] `CleanupStatus` 枚举
  - [ ] `ExecutionStatus` 枚举
- [ ] 编写数据模型单元测试
- [ ] 代码审查

**预期产出**: `models_smart.py` (~150行)，测试覆盖率 > 90%

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

### Phase 2: AI分析 (2天)

#### Day 3: AI分析器

**任务**:
- [ ] 创建 `src/core/ai_analyzer.py`
  - [ ] `AIAnalyzer` 类
  - [ ] 批量评估逻辑
  - [ ] 提示词构建（复用现有）
  - [ ] 响应解析
- [ ] 增强提示词模板
  - [ ] 批量评估提示词
  - [ ] 单项确认提示词

**预期产出**: `ai_analyzer.py` (~200行)

---

#### Day 4: 规则引擎降级

**任务**:
- [ ] 增强 `src/core/rule_engine.py`
  - [ ] 添加批量评估方法
  - [ ] 风险等级映射
- [ ] 修改 `AIAnalyzer` 实现降级
  - [ ] AI失败时的规则引擎回退
  - [ ] 部分失败处理
- [ ] 集成测试

**预期产出**:
- 规则引擎更新 (~50行修改)
- 集成测试通过

---

### Phase 3: 执行器与UI (2.5天)

#### Day 5: 执行器

**任务**:
- [ ] 创建 `src/core/smart_executor.py`
  - [ ] `SmartExecutor` 类
  - [ ] 容错重试机制
  - [ ] 进度信号发射
  - [ ] 失败记录
- [ ] 编写执行器单元测试
  - [ ] 重试逻辑测试
  - [ ] 失败处理测试

**预期产出**: `smart_executor.py` (~250行)，测试通过

---

#### Day 6-7: UI实现

**任务**:
- [ ] 创建 `src/ui/smart_cleaner.py`
  - [ ] `SmartCleanPage` 类
  - [ ] 扫描设置区域
  - [ ] 进度显示区域
  - [ ] 实时统计卡片
- [ ] 创建 `src/ui/high_risk_dialog.py`
  - [ ] `HighRiskConfirmDialog` 类
  - [ ] 高危项列表表格
  - [ ] 全选/全不选按钮
  - [ ] 确认删除/全部保留按钮
- [ ] 集成到主应用
  - [ ] 修改 `app.py` 添加新页面
  - [ ] 添加导航栏入口

**预期产出**:
- `smart_cleaner.py` (~400行)
- `high_risk_dialog.py` (~200行)
- UI集成完成

---

### Phase 4: 报告与集成 (2天)

#### Day 8: 报告系统

**任务**:
- [ ] 创建 `src/core/cleanup_report_generator.py`
  - [ ] `CleanupReportGenerator` 类
  - [ ] 统计计算
  - [ ] 报告数据生成
- [ ] 创建 `src/ui/cleanup_report_page.py`
  - [ ] `CleanupReportPage` 类
  - [ ] 统计摘要区域
  - [ ] 失败项列表
  - [ ] 失败项重试按钮
- [ ] 数据库扩展
  - [ ] 创建新表结构
  - [ ] 实现数据持久化

**预期产出**:
- `cleanup_report_generator.py` (~150行)
- `cleanup_report_page.py` (~300行)
- 数据库迁移脚本

---

#### Day 9: 工作流集成

**任务**:
- [ ] 创建 `src/core/smart_clean_workflow.py`
  - [ ] `SmartCleanWorkflow` 类
  - [ ] 完整流程编排
  - [ ] 状态管理
- [ ] UI与工作流对接
  - [ ] 连接按钮到工作流
  - [ ] 连接信号
- [ ] 端到端测试

**预期产出**: `smart_clean_workflow.py` (~200行)

---

### Phase 5: 测试与优化 (2天)

#### Day 10: 测试

**任务**:
- [ ] 单元测试完整检查
  - [ ] 数据模型测试
  - [ ] 扫描器测试
  - [ ] AI分析器测试
  - [ ] 执行器测试
- [ ] 集成测试
  - [ ] 系统垃圾清理流程
  - [ ] AppData清理流程
  - [ ] 自定义路径清理流程
  - [ ] 高危确认流程
- [ ] 边界情况测试
  - [ ] 权限错误场景
  - [ ] 文件占用场景
  - [ ] AI调用失败场景
  - [ ] 大量文件场景

#### Day 11: 优化与文档

**任务**:
- [ ] 性能优化
  - [ ] 内存占用检查
  - [ ] 扫描速度优化
  - [ ] AI响应优化
- [ ] 错误处理完善
  - [ ] 所有可能的异常处理
  - [ ] 用户友好的错误消息
- [ ] 文档更新
  - [ ] 更新快速对接指南
  - [ ] 更新技术档案
  - [ ] 编写用户使用文档
- [ ] 代码审查与最终检查

---

## 4. 验收标准

### 4.1 功能验收

| 功能 | 验收标准 | 测试方法 |
|------|---------|---------|
| 扫描选择 | 选择不同类型调用正确扫描器 | 单元测试 |
| 深度扫描 | 能扫描指定路径，正确跳过系统目录 | 集成测试 |
| AI分析 | 正确评估风险等级，生成清理计划 | 集成测试 |
| 规则降级 | AI失败时降级到规则引擎 | 边界测试 |
| 执行清理 | 失败项重试3次，记录正确 | 集成测试 |
| 高危确认 | Dangerous项弹出确认对话框 | UI测试 |
| 报告生成 | 统计正确，失败项可重试 | 集成测试 |

### 4.2 性能验收

| 指标 | 目标值 | 测试方法 |
|------|-------|---------|
| 100GB目录扫描 | < 3分钟 (基础API) | 性能测试 |
| 1000项AI分析 | < 2分钟 | 性能测试 |
| 清理执行速度 | > 50项/秒 | 性能测试 |
| 内存占用 | < 300MB | 资源监控 |

### 4.3 代码质量

- [ ] 单元测试覆盖率 > 85%
- [ ] 无内存泄漏
- [ ] 符合 PEP 8 规范
- [ ] 完整的错误处理
- [ ] 详细的日志记录
- [ ] 代码审查通过

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:----:|:----:|---------|
| AI API不稳定 | 中 | 高 | MVP已包含规则引擎降级 |
| 扫描器权限问题 | 高 | 中 | 添加错误提示，建议用户以管理员运行 |
| 内存占用过高 | 中 | 高 | 分批加载，限制同时显示项数 |
| 文件占用导致删除失败 | 高 | 中 | 失败项记录，提供手动重试 |
| 开发时间超期 | 中 | 中 | 灵活调整MVP范围，延后非核心功能 |

---

## 6. V2 版本规划

### 6.1 V2 增强功能

| 功能 | 说明 | 预计时间 |
|------|------|---------|
| NTFS MFT扫描 | 移植WinDirStat的MFT扫描，大幅提升速度 | 3-5天 |
| 完整备份机制 | 完整文件备份+恢复功能 | 2-3天 |
| Treemap可视化 | 磁盘空间可视化展示 | 3-4天 |
| 高级报告图表 | 饼图、柱图等统计图表 | 2天 |
| 性能优化 | 进一步优化扫描和AI处理速度 | ongoing |

### 6.2 V2 开发时间预估

**总计**: 10-14天
**MVP + V2 总计**: 21-25天

---

## 附录

### A. 配置扩展

```json
{
  "smart_clean": {
    "enabled": true,
    "default_scan_type": "system",
    "confirm_dangerous": true,
    "auto_confirm_suspicious": true,
    "max_retries": 3,
    "retry_delay": 2,
    "use_mft": false,
    "backup_enabled": false,
    "batch_size": 50,
    "ai_timeout": 30
  }
}
```

### B. 数据库表结构（MVP）

```sql
-- 清理计划表
CREATE TABLE IF NOT EXISTS cleanup_plans (
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
    used_rule_engine BOOLEAN DEFAULT 0,
    analyzed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 清理项表
CREATE TABLE IF NOT EXISTS cleanup_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    original_risk TEXT NOT NULL,
    ai_risk TEXT NOT NULL,
    ai_reason TEXT,
    confidence REAL,
    status TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    cleaned_at TEXT,
    FOREIGN KEY (plan_id) REFERENCES cleanup_plans(plan_id)
);

-- 清理执行结果表
CREATE TABLE IF NOT EXISTS cleanup_executions (
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

### C. 文件清单（MVP）

```
src/
├── core/
│   ├── models_smart.py          # 数据模型 (新增)
│   ├── smart_scan_selector.py   # 扫描选择器 (新增)
│   ├── depth_disk_scanner.py    # 深度扫描器 (新增)
│   ├── ai_analyzer.py           # AI分析器 (新增)
│   ├── smart_executor.py        # 智能执行器 (新增)
│   ├── smart_clean_workflow.py  # 工作流 (新增)
│   ├── cleanup_report_generator.py  # 报告生成器 (新增)
│   ├── rule_engine.py           # 规则引擎 (修改)
│   └── database.py              # 数据库 (修改表结构)
│
└── ui/
    ├── smart_cleaner.py         # 智能清理页面 (新增)
    ├── high_risk_dialog.py      # 高危确认对话框 (新增)
    ├── cleanup_report_page.py   # 报告页面 (新增)
    └── app.py                   # 主应用 (修改)
```

**新增代码量**: ~2,000行
**修改代码量**: ~200行

---

**文档完成时间**: 2026-02-21
**下次评审**: Phase 1 完成后（开发第3天）
