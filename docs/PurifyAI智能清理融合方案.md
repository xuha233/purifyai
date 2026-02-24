# PurifyAI × WinDirStat 智能清理融合方案
> 功能设计书与实现方案书

**版本**: v1.0  
**日期**: 2026-02-21  
**项目**: PurifyAI 智能清理工具增强版

---

## 目录

1. [需求概述](#1-需求概述)
2. [功能设计](#2-功能设计)
3. [架构设计](#3-架构设计)
4. [数据模型设计](#4-数据模型设计)
5. [核心流程设计](#5-核心流程设计)
6. [AI交互设计](#6-ai交互设计)
7. [UI设计](#7-ui设计)
8. [实现方案](#8-实现方案)
9. [WinDirStat功能融合策略](#9-windirstat功能融合策略)
10. [测试与验收](#10-测试与验收)

---

## 1. 需求概述

### 1.1 核心目标

将 PurifyAI 的现有 AI 智能评估能力与 WinDirStat 的深度磁盘扫描能力融合，实现：

1. **智能全流程清理**: 选择磁盘/目录 → 扫描 → AI分析 → 自动执行清理 → 完成
2. **无人值守运行**: AI分析后，根据风险等级自动执行清理（高危需确认）
3. **混合扫描策略**: 根据不同场景选择最优扫描方式
4. **智能容错**: 失败项自动重试，确保整体流程稳定性

### 1.2 用户回答汇总

| 问题 | 选择 | 说明 |
|------|------|------|
| 自动清理支持 | 仅手动触发 | 用户手动选择位置后执行智能清理 |
| 风险确认策略 | 高风险需确认 | safe/suspicious自动执行，dangerous需用户确认 |
| 扫描范围 | 混合模式 | 针对不同场景使用不同的扫描策略 |
| 容错机制 | 智能重试 | 失败项自动重试指定次数后跳过 |

---

## 2. 功能设计

### 2.1 功能架构

```
智能全自动清理
├── 选择目标（磁盘/目录）
├── 智能扫描引擎（混合模式）
│   ├── 快速扫描（系统垃圾、浏览器缓存）
│   └── 深度扫描（完整磁盘遍历）
├── AI智能分析
│   ├── 风险评估（safe/suspicious/dangerous）
│   ├── 清理建议
│   └── 执行计划生成
├── 智能执行器
│   ├── 自动执行（safe + suspicious）
│   ├── 人工确认（dangerous）
│   └── 容错重试机制
└── 结果报告
    ├── 清理统计
    ├── 失败项列表
    └── 操作日志
```

### 2.2 核心功能模块

#### 2.2.1 智能扫描选择器 (SmartScanSelector)

**功能**: 根据用户选择的扫描类型和目标，自动选择最优扫描策略

| 扫描类型 | 推荐扫描器 | 场景说明 |
|---------|-----------|---------|
| 系统垃圾 | SystemScanner | Windows临时文件、日志、预取 |
| 浏览器缓存 | BrowserScanner | Chrome/Edge/Firefox缓存 |
| AppData | AppDataScanner + 深度扫描 | 应用数据目录，深度分析 |
| 自定义路径 | DepthDiskScanner | WinDrat风格的完整遍历 |
| 整个磁盘 | DepthDiskScanner | NTFS MFT快速扫描 |

#### 2.2.2 AI智能分析器 (AIAnalyzer)

**功能**: 对扫描结果进行智能分析，生成清理执行计划

**输入**:
- 扫描结果列表 (List[ScanItem])
- 扫描类型和上下文信息

**输出**:
```python
class CleanupPlan:
    plan_id: str                    # 计划ID
    safe_items: List[CleanupItem]   # 可安全删除项
    suspicious_items: List[CleanupItem]  # 需确认项
    dangerous_items: List[CleanupItem]   # 高危项
    estimated_freed: int            # 预计释放空间（字节）
    ai_summary: str                 # AI汇总说明
    created_at: datetime
```

**AI提示词策略**:
```
# 角色：Windows磁盘空间优化专家

## 任务
分析以下扫描结果，制定智能清理计划。

## 评估标准
- safe: 明确的缓存、临时文件、日志
- suspicious: 应用数据、配置文件、可重建的数据
- dangerous: 用户文档、重要数据、系统关键文件

## 输出格式（JSON）
{
  "safe_items": [
    {
      "path": "文件路径",
      "reason": "清理原因",
      "confidence": 0.9
    }
  ],
  "suspicious_items": [...],
  "dangerous_items": [...],
  "summary": "清理方案概述",
  "estimated_freed_bytes": 1024000000
}
```

#### 2.2.3 智能执行器 (SmartExecutor)

**功能**: 根据AI生成的清理计划，执行清理操作

**执行策略**:
- **安全项**: 直接删除（带回滚记录）
- **疑似项**: 根据用户配置，自动执行或等待确认
- **高危项**: 强制弹出确认对话框

**容错机制**:
```python
class SmartExecutor:
    max_retries = 3              # 最大重试次数
    retry_delay = 2              # 重试间隔(秒)
    
    def execute_plan(self, plan: CleanupPlan):
        for item in plan.safe_items + plan.suspicious_items:
            for attempt in range(self.max_retries):
                try:
                    self._delete_with_backup(item)
                    break
                except Exception:
                    if attempt == self.max_retries - 1:
                        self._log_failure(item)
                    else:
                        time.sleep(self.retry_delay)
```

#### 2.2.4 清理报告生成器 (CleanupReportGenerator)

**功能**: 生成详细的清理报告

**报告内容**:
- 扫描统计（总项数、总大小）
- AI分析结果（各风险等级分布）
- 清理执行结果（成功/失败/跳过）
- 释放空间统计
- 操作时间线
- 失败项详情（带重试建议）

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      PurifyAI 主应用                          │
│                         (app.py)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   UI层 (ui/)                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ SmartCleanPage   │  │ ConfirmDialog    │  │ ReportPage   │ │
│  │ 智能清理页面      │  │ 确认对话框        │  │ 报告页面     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 核心业务层 (core/)                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │          SmartCleanWorkflow (智能清理工作流)              │  │
│  │  扫描 → AI分析 → 生成计划 → 执行 → 生成报告                │  │
│  └───────────────────────────────────────────────────────────┘  │
│        │          │          │          │          │           │
│        ▼          ▼          ▼          ▼          ▼           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │扫描器    │ │AI分析器  │ │执行器    │ │报告生成器 │          │
│  │(混合)    │ │          │ │          │ │          │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              基础设施层                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ConfigManager│  │  Database   │  │   Logger    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 模块依赖关系

```
SmartCleanWorkflow
  ├─ SmartScanSelector
  │   ├─ SystemScanner
  │   ├─ BrowserScanner
  │   ├─ AppDataScanner
  │   └─ DepthDiskScanner (新增)
  │
  ├─ AIAnalyzer
  │   ├─ AIClient
  │   ├─ ResponseParser
  │   └─ AIPromptBuilder (增强版)
  │
  ├─ SmartExecutor
  │   ├─ Cleaner
  │   ├─ CustomRecycleBin
  │   └─ BackupManager (新增)
  │
  └─ CleanupReportGenerator
      └─ Database
```

---

## 4. 数据模型设计

### 4.1 核心数据模型

#### 4.1.1 CleanupItem (清理项)

```python
@dataclass
class CleanupItem:
    """清理项数据模型"""
    path: str                    # 文件/文件夹路径
    size: int                    # 大小（字节）
    item_type: str              # 'file' 或 'directory'
    original_risk: RiskLevel    # 原始风险等级
    ai_risk: RiskLevel          # AI评估风险等级
    ai_reason: str             # AI判断原因
    confidence: float          # AI置信度 (0-1)
    cleanup_suggestion: str    # 清理建议
    software_name: str = ""    # 所属软件名称
    function_description: str = ""  # 功能描述
    
    # 执行状态
    status: CleanupStatus = CleanupStatus.PENDING
    retry_count: int = 0
    error_message: str = ""
    cleaned_at: Optional[datetime] = None
```

#### 4.1.2 CleanupPlan (清理计划)

```python
@dataclass
class CleanupPlan:
    """清理执行计划"""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scan_type: str = ""           # 扫描类型
    scan_target: str = ""         # 扫描目标
    
    # 分项列表
    safe_items: List[CleanupItem] = field(default_factory=list)
    suspicious_items: List[CleanupItem] = field(default_factory=list)
    dangerous_items: List[CleanupItem] = field(default_factory=list)
    
    # 统计信息
    total_items: int = 0
    total_size: int = 0
    estimated_freed: int = 0
    
    # AI分析结果
    ai_summary: str = ""
    ai_model: str = ""
    analyzed_at: Optional[datetime] = None
    
    # 执行结果
    execution_result: Optional['ExecutionResult'] = None
```

#### 4.1.3 ExecutionResult (执行结果)

```python
@dataclass
class ExecutionResult:
    """清理执行结果"""
    plan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # 执行统计
    total_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    
    # 空间统计
    total_size: int = 0
    freed_size: int = 0
    failed_size: int = 0
    
    # 失败项详情
    failures: List['FailureInfo'] = field(default_factory=list)
    
    # 执行状态
    status: ExecutionStatus = ExecutionStatus.RUNNING
    error_message: str = ""
```

#### 4.1.4 FailureInfo (失败信息)

```python
@dataclass
class FailureInfo:
    """失败项信息"""
    item: CleanupItem
    error_type: str           # 'permission', 'file_in_use', 'disk_full', etc.
    error_message: str
    retry_count: int
    suggested_action: str     # 'retry', 'skip', 'admin_privilege', etc.
```

### 4.2 枚举定义

```python
class CleanupStatus(Enum):
    """清理项状态"""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    SUCCESS = "success"         # 成功
    FAILED = "failed"           # 失败
    SKIPPED = "skipped"         # 跳过
    CANCELLED = "cancelled"     # 已取消
    AWAITING_CONFIRM = "awaiting_confirm"  # 等待用户确认


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    PARTIAL_SUCCESS = "partial_success"  # 部分成功
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
```

---

## 5. 核心流程设计

### 5.1 智能清理主流程

```python
class SmartCleanWorkflow:
    """智能清理工作流"""
    
    async def工作流执行流程(self, scan_type: str, scan_target: str):
        """
        步骤1: 智能扫描
           - 根据scan_type选择扫描器
           - 执行扫描并收集结果
           - 实时更新进度
           
        步骤2: AI智能分析
           - 将扫描结果发送给AI
           - AI评估每项的风险等级
           - 生成清理执行计划
           
        步骤3: 确认高危项
           - 如果有dangerous项，弹出确认对话框
           - 用户可选择保留或删除
           
        步骤4: 智能执行
           - 执行safe和suspicious项
           - 每项执行失败自动重试
           - 记录执行结果
           
        步骤5: 生成报告
           - 汇总统计信息
           - 生成详细报告
           - 保存到数据库
        """
```

### 5.2 详细流程图

```
用户点击"智能清理"
    │
    ├─→ [扫描选择对话框]
    │     ├─ 选择扫描类型（系统/浏览器/AppData/自定义/磁盘）
    │     └─ 选择扫描目标（路径）
    │
    ├─→ 开始扫描
    │     ├─ SmartScanSelector选择扫描器
    │     ├─ 执行扫描 (多线程)
    │     ├─ 实时更新进度条
    │     └─ 收集扫描结果
    │
    ├─→ AI分析
    │     ├─ 构建AI提示词 (AIPromptBuilder)
    │     ├─ 调用AI API
    │     ├─ ResponseParser解析响应
    │     └─ 生成CleanupPlan
    │
    ├─→ [高危确认对话框]
    │     ├─ 显示dangerous项列表
    │     ├─ 显示AI评估原因
    │     └─ 用户选择删除/保留
    │
    ├─→ 执行清理
    │     ├─ SmartExecutor执行计划
    │     ├─ for each item in (safe + suspicious):
    │     │     ├─ 尝试删除（最多3次）
    │     │     ├─ 成功 → 记录
    │     │     └─ 失败 → 重试/跳过
    │     ├─ 执行用户确认的高危项
    │     └─ 实时更新进度
    │
    ├─→ 生成报告
    │     ├─ 汇总统计
    │     ├─ CleanupReportGenerator生成报告
    │     └─ 保存到数据库
    │
    └─→ [清理报告页面]
          ├─ 显示统计摘要
          ├─ 显示成功/失败项
          ├─ 提供失败项重试按钮
          └─ 导出报告功能
```

---

## 6. AI交互设计

### 6.1 AI提示词增强

#### 6.1.1 批量评估提示词

```python
def build_batch_assessment_prompt(items: List[ScanItem]) -> str:
    """构建批量评估提示词"""
    
    items_info = []
    for item in items[:50]:  # 限制批处理数量
        items_info.append({
            "path": item.path,
            "size": format_size(item.size),
            "type": item.item_type,
            "original_risk": item.risk_level.value
        })
    
    return f"""# 角色：Windows磁盘空间优化专家

## 任务
分析以下文件/文件夹列表，制定智能清理计划。

## 文件列表
{json.dumps(items_info, indent=2, ensure_ascii=False)}

## 评估标准

### Safe（可直接删除）
- 明确的缓存文件（.cache, .tmp, cache/, temp/）
- 系统临时文件
- 日志文件（.log, logs/）
- 浏览器缓存
- 预取数据

### Suspicious（需谨慎）
- 应用数据文件夹
- 配置文件（.config, .ini, settings/）
- 数据库文件
- 可重建的数据
- 用户缓存但非关键数据

### Dangerous（不建议删除）
- 用户文档（Documents/）
- 用户桌面
- 图片、视频、音乐等媒体文件
- 系统关键文件
- 重要的用户数据

## 输出格式（纯JSON，不要其他文字）
{{
  "safe_items": [
    {{"path": "完整路径", "reason": "清理原因（30字以内）", "confidence": 0.95}}
  ],
  "suspicious_items": [...],
  "dangerous_items": [...],
  "summary": "清理方案概述（100字以内）",
  "estimated_freed_bytes": 估算释放空间
}}

## 要求
1. 只输出JSON，不要包含任何其他文字
2. path必须完全匹配输入中的path
3. confidence为0-1之间的数值
4. estimated_freed_bytes为字节数
"""
```

#### 6.1.2 单项确认提示词

```python
def build_item_confirmation_prompt(item: CleanupItem) -> str:
    """构建单项确认提示词"""
    
    return f"""# 角色：Windows文件安全评估专家

## 任务
用户想要删除以下文件/文件夹，请评估风险。

## 文件信息
- 路径: {item.path}
- 大小: {format_size(item.size)}
- 类型: {item.item_type}
- 原始风险等级: {item.original_risk.value}
- 修改时间: {get_last_modified(item.path)}

## 评估维度
1. 删除此文件是否会导致应用无法运行？
2. 此文件是否是用户重要数据？
3. 此文件是否可以自动重建？
4. 此文件是否明显是缓存或临时文件？

## 输出格式（JSON）
{{
  "risk_level": "safe|suspicious|dangerous",
  "reason": "评估原因（50字以内）",
  "confidence": 0.95,
  "suggestion": "建议操作（删除/保留）",
  "impact": "删除后的影响（30字以内）"
}}
"""
```

### 6.2 AI响应解析增强

基于现有的 `ai_response_parser.py`，新增字段：

```python
class CleanupPlanParser(ResponseParser):
    """清理计划专用解析器"""
    
    REQUIRED_FIELDS = {
        'safe_items', 'suspicious_items', 'dangerous_items',
        'summary', 'estimated_freed_bytes'
    }
    
    def parse_cleanup_plan(self, response: str) -> Optional[CleanupPlan]:
        """解析清理计划"""
        data = super().parse(response)
        
        if not data:
            return None
        
        # 解析各项列表
        safe_items = [self._parse_cleanup_item(d) for d in data.get('safe_items', [])]
        suspicious_items = [self._parse_cleanup_item(d) for d in data.get('suspicious_items', [])]
        dangerous_items = [self._parse_cleanup_item(d) for d in data.get('dangerous_items', [])]
        
        return CleanupPlan(
            safe_items=safe_items,
            suspicious_items=suspicious_items,
            dangerous_items=dangerous_items,
            ai_summary=data.get('summary', ''),
            estimated_freed=int(data.get('estimated_freed_bytes', 0)),
            analyzed_at=datetime.now()
        )
```

---

## 7. UI设计

### 7.1 新增页面：智能清理页面 (SmartCleanPage)

**位置**: `src/ui/smart_cleaner.py`

**布局**:
```
┌─────────────────────────────────────────────────────────┐
│  智能清理                                                │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 扫描设置                                        │    │
│  │  扫描类型: [下拉选择]                          │    │
│  │  扫描目标: [浏览按钮 / 文本框]                 │    │
│  │                                                  │    │
│  │  [开始智能清理]                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  进度显示区域                                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │ 当前步骤: [扫描中 → AI分析中 → 执行清理中]    │    │
│  │  ████████████░░░░  60%                           │    │
│  │  已处理: 1,234 项 / 2,000 项                   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  实时统计                                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                │    │
│  │安全  │ │疑似  │ │高危  │ │总计  │                │    │
│  │ 856  │ │ 340  │ │ 38   │ │1234  │                │    │
│  └──────┘ └──────┘ └──────┘ └──────┘                │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 7.2 确认对话框 (HighRiskConfirmDialog)

```python
class HighRiskConfirmDialog(QDialog):
    """高危项确认对话框"""
    
    def __init__(self, dangerous_items: List[CleanupItem]):
        # 显示列表表格
        # 路径 | 大小 | AI风险等级 | AI评估原因
        # 全选/全不选按钮
        # 确认删除 / 全部保留
```

### 7.3 清理报告页面 (CleanupReportPage)

```python
class CleanupReportPage(QWidget):
    """清理报告页面"""
    
    def __init__(self, execution_result: ExecutionResult):
        # 统计摘要卡片
        # - 扫描统计（总项数、总大小）
        # - 执行结果（成功/失败/跳过）
        # - 释放空间（已释放、失败释放）
        # - 执行时间
        
        # 详细统计图表（饼图：各风险等级分布）
        
        # 失败项列表
        # - 可重试项（提供重试按钮）
        # - 权限错误项（提示提升权限）
        # - 文件占用项（提示关闭应用）
        
        # 导出报告按钮
```

---

## 8. 实现方案

### 8.1 文件结构

```
src/
├── ui/
│   ├── smart_cleaner.py          # 智能清理页面 (新增)
│   ├── high_risk_dialog.py       # 高危确认对话框 (新增)
│   └── cleanup_report_page.py   # 清理报告页面 (新增)
│
└── core/
    ├── smart_clean_workflow.py   # 智能清理工作流 (新增)
    ├── smart_scan_selector.py    # 智能扫描选择器 (新增)
    ├── ai_analyzer.py            # AI分析器 (新增)
    ├── smart_executor.py         # 智能执行器 (新增)
    ├── cleanup_report_generator.py # 报告生成器 (新增)
    ├── depth_disk_scanner.py     # 深度磁盘扫描器 (新增)
    ├── models_smart.py           # 智能清理数据模型 (新增)
    └── backup_manager.py         # 备份管理器 (新增)
```

### 8.2 实现优先级

#### Phase 1: 基础架构（1-2天）
- [ ] 创建数据模型 (`models_smart.py`)
- [ ] 创建智能扫描选择器 (`smart_scan_selector.py`)
- [ ] 集成到导航栏和主应用
- [ ] 基础UI框架 (`smart_cleaner.py`)

#### Phase 2: 扫描功能（2-3天）
- [ ] 实现深度磁盘扫描器 (`depth_disk_scanner.py`)
- [ ] 复用现有扫描器
- [ ] 实集混合扫描策略
- [ ] 进度显示和取消功能

#### Phase 3: AI分析（2-3天）
- [ ] 实现AI分析器 (`ai_analyzer.py`)
- [ ] 增强提示词构建器
- [ ] 增强响应解析器
- [ ] 生成清理计划模型

#### Phase 4: 执行器（2-3天）
- [ ] 实现智能执行器 (`smart_executor.py`)
- [ ] 实现容错重试机制
- [ ] 实现备份管理器 (`backup_manager.py`)
- [ ] 高危确认对话框

#### Phase 5: 报告生成（1-2天）
- [ ] 实现报告生成器 (`cleanup_report_generator.py`)
- [ ] 清理报告页面
- [ ] 失败项重试功能
- [ ] 报告导出功能

#### Phase 6: 集成测试（1-2天）
- [ ] 端到端测试
- [ ] 边界情况测试
- [ ] 性能优化
- [ ] 文档更新

### 8.3 关键代码示例

#### 8.3.1 智能扫描选择器

```python
# src/core/smart_scan_selector.py

class SmartScanSelector:
    """智能扫描选择器"""
    
    def __init__(self):
        self.scanners = {
            'system': SystemScanner(),
            'browser': BrowserScanner(),
            'appdata': AppDataScanner(),
            'custom': DepthDiskScanner(),
            'disk': DepthDiskScanner()
        }
    
    def select_scanner(self, scan_type: str, scan_target: str) -> QObjectScanner:
        """选择合适的扫描器"""
        
        if scan_type in ['custom', 'disk']:
            return DepthDiskScanner()
        else:
            return self.scanners.get(scan_type)
    
    def get_scan_config(self, scan_type: str) -> dict:
        """获取扫描配置"""
        configs = {
            'system': {
                'depth': 'shallow',
                'filters': ['temp', 'cache', 'log']
            },
            'disk': {
                'depth': 'full',
                'use_mft': True,
                'exclude_system': False
            },
            'appdata': {
                'depth': 'medium',
                'ai_assessment': True
            }
        }
        return configs.get(scan_type, {})
```

#### 8.3.2 AI分析器

```python
# src/core/ai_analyzer.py

class AIAnalyzer:
    """AI智能分析器"""
    
    def __init__(self):
        self.ai_client = get_ai_enhancer()
        self.parser = CleanupPlanParser()
    
    def analyze_scan_results(
        self,
        items: List[ScanItem],
        scan_type: str
    ) -> CleanupPlan:
        """分析扫描结果"""
        
        # 分批处理（每批50项）
        batch_size = 50
        batches = [items[i:i+batch_size] 
                   for i in range(0, len(items), batch_size)]
        
        all_safe = []
        all_suspicious = []
        all_dangerous = []
        total_freed = 0
        
        for batch in batches:
            # 构建提示词
            prompt = build_batch_assessment_prompt(batch)
            
            # 调用AI
            success, response = self.ai_client.ai_client.chat([
                {'role': 'user', 'content': prompt}
            ])
            
            if success:
                # 解析响应
                plan = self.parser.parse_cleanup_plan(response)
                
                if plan:
                    all_safe.extend(plan.safe_items)
                    all_suspicious.extend(plan.suspicious_items)
                    all_dangerous.extend(plan.dangerous_items)
                    total_freed += plan.estimated_freed
            else:
                # AI失败，使用原始风险等级
                for item in batch:
                    if item.risk_level == RiskLevel.SAFE:
                        all_safe.append(self._scan_to_cleanup(item))
                    elif item.risk_level == RiskLevel.SUSPICIOUS:
                        all_suspicious.append(self._scan_to_cleanup(item))
                    else:
                        all_dangerous.append(self._scan_to_cleanup(item))
        
        return CleanupPlan(
            scan_type=scan_type,
            safe_items=all_safe,
            suspicious_items=all_suspicious,
            dangerous_items=all_dangerous,
            estimated_freed=total_freed,
            analyzed_at=datetime.now()
        )
```

#### 8.3.3 智能执行器

```python
# src/core/smart_executor.py

class SmartExecutor(QObject):
    """智能执行器"""
    
    progress = pyqtSignal(str)  # 进度信号
    item_completed = pyqtSignal(str, bool)  # path, success
    complete = pyqtSignal(ExecutionResult)
    
    def __init__(self):
        super().__init__()
        self.cleaner = Cleaner()
        self.backup_manager = BackupManager()
        self.max_retries = 3
        self.retry_delay = 2
    
    def execute_plan(self, plan: CleanupPlan) -> ExecutionResult:
        """执行清理计划"""
        
        result = ExecutionResult(
            plan_id=plan.plan_id,
            started_at=datetime.now(),
            status=ExecutionStatus.RUNNING,
            total_items=len(plan.safe_items) + len(plan.suspicious_items)
        )
        
        # 合并要执行的项目
        items_to_execute = plan.safe_items + plan.suspicious_items
        
        for i, item in enumerate(items_to_execute):
            self.progress.emit(f"正在清理 ({i+1}/{len(items_to_execute)}): {item.path}")
            
            # 尝试执行（带重试）
            success = self._execute_with_retry(item, result)
            
            if success:
                result.success_items += 1
                result.freed_size += item.size
            else:
                result.failed_items += 1
                result.failed_size += item.size
            
            self.item_completed.emit(item.path, success)
        
        result.completed_at = datetime.now()
        
        if result.failed_items == 0:
            result.status = ExecutionStatus.COMPLETED
        elif result.success_items > 0:
            result.status = ExecutionStatus.PARTIAL_SUCCESS
        else:
            result.status = ExecutionStatus.FAILED
        
        self.complete.emit(result)
        return result
    
    def _execute_with_retry(
        self,
        item: CleanupItem,
        result: ExecutionResult
    ) -> bool:
        """执行清理（带重试）"""
        
        for attempt in range(self.max_retries):
            try:
                # 创建备份
                backup_path = self.backup_manager.create_backup(item.path)
                
                # 执行删除
                success = self.cleaner.clean([item], clean_type='auto')
                
                if success:
                    item.status = CleanupStatus.SUCCESS
                    item.cleaned_at = datetime.now()
                    return True
                else:
                    raise Exception("删除失败")
                    
            except PermissionError:
                item.error_message = "权限不足"
                item.retry_count = attempt + 1
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    result.failures.append(FailureInfo(
                        item=item,
                        error_type='permission',
                        error_message='权限不足，需要管理员权限',
                        retry_count=attempt + 1,
                        suggested_action='retry_with_admin'
                    ))
                    return False
                    
            except Exception as e:
                item.error_message = str(e)
                item.retry_count = attempt + 1
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    result.failures.append(FailureInfo(
                        item=item,
                        error_type='unknown',
                        error_message=str(e),
                        retry_count=attempt + 1,
                        suggested_action='skip'
                    ))
                    return False
        
        return False
```

---

## 9. WinDirStat功能融合策略



### 9.1 可融合功能

| WinDirStat功能 | 融合方式 | 价值 |
|---------------|---------|------|
| NTFS MFT快速扫描 | 移植为DepthDiskScanner | 大幅提升整盘扫描速度 |
| Treemap可视化 | 新增可视化组件 | 直观展示空间占用 |
| 硬链接处理 | 集成到扫描器 | 避免重复计算 |
| 文件扩展名统计 | 集成到扫描结果 | 帮助AI更准确判断 |
| 文件压缩检测 | 集成到扫描器 | 区分物理/逻辑大小 |

### 9.2 深度磁盘扫描器设计

基于WinDirStat的FinderNtfs和FinderBasic实现：

```python
# src/core/depth_disk_scanner.py

class DepthDiskScanner(QObjectScanner):
    """深度磁盘扫描器 - 融合WinDirStat能力"""
    
    def __init__(self):
        super().__init__()
        self.use_mft = True  # 默认使用NTFS MFT
        self.follow_junctions = False
        self.follow_symlinks = False
    
    def start_scan(self, paths: List[str]):
        """启动扫描"""
        
        for path in paths:
            if self._is_ntfs_drive(path):
                self._scan_with_mft(path)
            else:
                self._scan_with_basic(path)
    
    def _scan_with_mft(self, root_path: str):
        """使用NTFS MFT扫描"""
        
        try:
            # 使用ctypes调用Windows API
            # 或使用pywin32读取MFT
            
            # 这里简化示意
            from ctypes import windll
            
            # 创建设备句柄
            device_path = f"\\\\.\\{root_path[0]}:"
            handle = windll.kernel32.CreateFileW(
                device_path,
                0x80000000,  # GENERIC_READ
                1,           # FILE_SHARE_READ
                None,
                3,           # OPEN_EXISTING
                0,           # FILE_FLAG_BACKUP_SEMANTICS
                None
            )
            
            if handle == -1:
                self._scan_with_basic(root_path)
                return
            
            # 读取MFT记录
            # ... (详细的MFT解析逻辑)
            
        except Exception as e:
            logger.error(f"MFT扫描失败: {e}")
            self._scan_with_basic(root_path)
    
    def _scan_with_basic(self, root_path: str):
        """使用基础API扫描（复用现有逻辑）"""
        
        for root, dirs, files in os.walk(root_path):
            # 排除特殊目录
            dirs[:] = [d for d in dirs if not self._should_skip(d)]
            
            # 处理文件
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    stat = os.stat(file_path)
                    item = ScanItem(
                        path=file_path,
                        size=stat.st_size,
                        item_type='file',
                        last_modified=datetime.fromtimestamp(stat.st_mtime)
                    )
                    
                    self.item_found.emit(item)
                    
                except Exception:
                    continue
    
    def _is_ntfs_drive(self, path: str) -> bool:
        """检查是否为NTFS驱动器"""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            volume_name = ctypes.create_unicode_buffer(1024)
            fs_name = ctypes.create_unicode_buffer(1024)
            
            kernel32.GetVolumeInformationW(
                path[:3],  # e.g., "C:\\"
                volume_name,
                1024,
                None,
                None,
                None,
                fs_name,
                1024
            )
            
            return fs_name.value.upper() == 'NTFS'
            
        except Exception:
            return False
    
    def _should_skip(self, dir_name: str) -> bool:
        """判断是否跳过该目录"""
        skip_dirs = {
            '$RECYCLE.BIN', 'System Volume Information',
            '$Recycle.Bin', 'Windows', 'Program Files',
            'Program Files (x86)', 'ProgramData'
        }
        return dir_name in skip_dirs
```

### 9.3 文件扩展名统计融合

```python
class ExtensionStatsCollector:
    """文件扩展名统计收集器"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {
            'count': 0,
            'total_size': 0,
            'avg_size': 0
        })
    
    def add_file(self, path: str, size: int):
        """添加文件统计"""
        ext = os.path.splitext(path)[1].lower()
        
        self.stats[ext]['count'] += 1
        self.stats[ext]['total_size'] += size
        self.stats[ext]['avg_size'] = (
            self.stats[ext]['total_size'] / 
            self.stats[ext]['count']
        )
    
    def get_top_extensions(self, n: int = 10) -> List[dict]:
        """获取占用空间最大的扩展名"""
        sorted_ext = sorted(
            self.stats.items(),
            key=lambda x: x[1]['total_size'],
            reverse=True
        )
        return sorted_ext[:n]
```

---

## 10. 测试与验收

### 10.1 测试计划

#### 10.1.1 单元测试

| 模块 | 测试内容 |
|------|---------|
| SmartScanSelector | 扫描器选择逻辑正确性 |
| AIAnalyzer | AI调用、响应解析、错误处理 |
| SmartExecutor | 重试机制、失败处理、备份功能 |
| DepthDiskScanner | MFT扫描、基础扫描、跳过逻辑 |
| CleanupReportGenerator | 报告生成、统计计算 |

#### 10.1.2 集成测试

| 测试场景 | 验证点 |
|---------|-------|
| 系统垃圾扫描+AI+执行 | 全流程正常完成 |
| AppData扫描+AI+执行 | 高危项正确弹出确认 |
| 大型磁盘扫描 | 性能可接受、内存合理 |
| 权限错误场景 | 正确提示提升权限 |
| 文件占用场景 | 正确提示关闭应用 |
| AI调用失败 | 优雅降级到规则引擎 |

#### 10.1.3 性能测试

| 测试项 | 目标指标 |
|-------|---------|
| 100GB磁盘扫描 | < 30秒（使用MFT） |
| 10万项AI分析 | < 5分钟 |
| 清理执行速度 | > 100项/秒 |
| 内存占用 | < 500MB |

### 10.2 验收标准

- [ ] 所有Phase功能已完成
- [ ] 单元测试通过率 > 95%
- [ ] 集成测试全部通过
- [ ] 性能指标达标
- [ ] 无内存泄漏
- [ ] 错误处理完善
- [ ] 用户文档完整

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
    "use_mft": true,
    "backup_enabled": true,
    "backup_retention_days": 7
  }
}
```

### B. 数据库表扩展

```sql
-- 清理计划表
CREATE TABLE cleanup_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT UNIQUE NOT NULL,
    scan_type TEXT NOT NULL,
    scan_target TEXT NOT NULL,
    total_items INTEGER,
    total_size INTEGER,
    estimated_freed INTEGER,
    ai_summary TEXT,
    ai_model TEXT,
    analyzed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 清理项表
CREATE TABLE cleanup_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
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

**文档完成时间**: 2026-02-21  
**预计总开发时间**: 10-14天  
**建议团队规模**: 1-2名开发者