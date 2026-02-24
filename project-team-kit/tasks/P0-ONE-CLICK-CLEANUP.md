# P0-1: 一键清理 + 智能推荐功能

**任务类型：** P0 核心功能
**开发者：** Claude Code
**预计时间：** 2 天
**依赖：** 无
**优先级：** 最高

---

## 任务目标

实现 PurifyAI 的核心功能 —— 一键清理 + 智能推荐，让用户无需手动选择即可启动智能清理流程。

---

## 任务分解

### Part 1: 智能推荐算法

**文件：** `src/agent/smart_recommender.py`

**需求：**

1. **UserProfile 类** - 用户画像
   ```python
   @dataclass
   class UserProfile:
       """用户画像"""
       user_id: str
       installed_packages: List[str]  # 用户安装的软件列表
       disk_usage: Dict[str, float]   # 磁盘使用情况 {path: usage_percent}
       cleanup_history: List[str]     # 清理历史记录
       last_cleanup_time: Optional[datetime]
       preferred_mode: str  # 'conservative', 'balanced', 'aggressive'
   ```

2. **CleanupPlan 类** - 清理计划
   ```python
   @dataclass
   class CleanupPlan:
       """清理计划"""
       plan_id: str
       items: List[ScanItem]
       estimated_space: int  # 估计释放空间（字节）
       risk_percentage: float  # 风险百分比
       high_risk_count: int  # 高风险文件数量
       medium_risk_count: int
       low_risk_count: int
       recommended: bool  # 是否为推荐清理
       created_at: datetime
   ```

3. **SmartRecommender 类** - 智能推荐器
   ```python
   class SmartRecommender:
       """智能推荐器"""

       def build_user_profile(self) -> UserProfile:
           """构建用户画像"""
           # 1. 扫描常用软件目录
           # 2. 识别用户场景（游戏/办公/开发）
           # 3. 分析磁盘使用情况
           # 4. 加载清理历史
           pass

       def detect_user_scenario(self, profile: UserProfile) -> str:
           """检测用户场景"""
           # 基于安装的软件识别：
           # - 游戏玩家: 'Steam', 'Epic Games', 'Ubisoft'
           # - 办公电脑: 'Office', 'WPS', 'Notion'
           # - 开发环境: 'Python', 'Node.js', 'Docker', 'Git'
           # - 普通用户: 其他
           pass

       def recommend(self, profile: UserProfile, mode: str = 'balanced') -> CleanupPlan:
           """推荐清理计划"""
           # 1. 扫描系统
           # 2. 根据用户场景过滤文件
           # 3. 计算风险等级
           # 4. 生成清理计划
           pass

       def recommend_incremental(self, since: datetime, mode: str = 'balanced') -> CleanupPlan:
           """增量推荐（只清理新文件）"""
           # 1. 只扫描 since 时间后的新文件
           # 2. 应用风险过滤
           # 3. 生成清理计划
           pass

       def filter_by_profile(self, items: List[ScanItem], profile: str) -> List[ScanItem]:
           """根据用户场景过滤文件"""
           # 预设过滤规则：
           filters = {
               'gaming': [lambda x: 'Games' in x.path, lambda x: 'Cache' in x.path],
               'office': [lambda x: 'Office' in x.path, lambda x: '.tmp' in x.path],
               'developer': [lambda x: 'node_modules' in x.path, lambda x: '__pycache__' in x.path],
               'general': [lambda x: 'Temp' in x.path, lambda x: 'Cache' in x.path]
           }
           pass
   ```

4. **用户场景识别规则**

   **游戏玩家场景：**
   - 精确规则：扫描 `C:\Program Files (x86)\Steam\steamapps\downloading\`
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Local\Temp\`（游戏缓存）

   **办公电脑场景：**
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Roaming\Microsoft\Word\`（Word 缓存）
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Local\Temp\`（临时文件）

   **开发环境场景：**
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Local\Temp\pip\`（Python 缓存）
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Local\Temp\npm\`（Node.js 缓存）
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Local\Temp\__pycache__\`（Python 字节码）

   **普通用户场景：**
   - 精确规则：扫描 `C:\Windows\Temp\`（系统临时文件）
   - 精确规则：扫描 `C:\Users\<用户>\AppData\Local\Temp\`（用户临时文件）

5. **清理策略（不同模式）**

   **保守模式（Conservative）：**
   - 只删除低风险文件（风险值 < 10）
   - 跳过所有系统文件
   - 跳过超过 50MB 的文件

   **平衡模式（Balanced）：**
   - 删除低风险和中低风险（风险值 < 30）
   - 保留高风险文件
   - 保留系统文件

   **激进模式（Aggressive）：**
   - 删除所有中以下风险的文件（风险值 < 70）
   - 跳过高风险文件
   - 跳过系统关键文件

---

### Part 2: 清理流程编排

**文件：** `src/agent/cleanup_orchestrator.py`

**需求：**

1. **CleanupOrchestrator 类** - 清理流程编排器
   ```python
   class CleanupOrchestrator:
       """清理流程编排器"""

       def __init__(self, profile: UserProfile):
           self.profile = profile
           self.recommender = SmartRecommender()
           self.backup_manager = BackupManager()

       def execute_one_click_cleanup(self, mode: str = 'balanced') -> CleanupReport:
           """执行一键清理"""
           # 步骤：
           # 1. 生成清理计划
           # 2. 显示预览
           # 3. 自动备份
           # 4. 执行清理
           # 5. 生成报告
           pass

       def generate_cleanup_plan(self, mode: str = 'balanced') -> CleanupPlan:
           """生成清理计划（预览用）"""
           return self.recommender.recommend(self.profile, mode)

       def preview_cleanup(self, plan: CleanupPlan) -> dict:
           """生成清理预览"""
           return {
               'plan_id': plan.plan_id,
               'total_items': len(plan.items),
               'estimated_space': format_size(plan.estimated_space),
               'high_risk_count': plan.high_risk_count,
               'medium_risk_count': plan.medium_risk_count,
               'low_risk_count': plan.low_risk_count,
               'risk_percentage': plan.risk_percentage,
               'recommended': plan.recommended
           }

       def backup_before_cleanup(self, items: List[ScanItem]) -> BackupInfo:
           """清理前自动备份"""
           return self.backup_manager.backup(items)

       def execute_cleanup(self, plan: CleanupPlan, backup_id: str) -> CleanupReport:
           """执行清理"""
           # 使用 cleaner 批量删除
           from purifyai_cleaner import Cleaner
           cleaner = Cleaner()
           results = []

           for item in plan.items:
               try:
                   cleaner.delete_secure(item.path, backup=True)
                   results.append({'path': item.path, 'success': True})
               except Exception as e:
                   results.append({'path': item.path, 'success': False, 'error': str(e)})

           return CleanupReport(
               plan_id=plan.plan_id,
               total_items=len(plan.items),
               success_items=sum(1 for r in results if r['success']),
               failed_items=sum(1 for r in results if not r['success']),
               freed_size=sum(item.size for item in plan.items if any(r['path'] == item.path and r['success'] for r in results)),
               details=results
           )
   ```

2. **CleanupReport 类** - 清理报告
   ```python
   @dataclass
   class CleanupReport:
       """清理报告"""
       report_id: str
       plan_id: str
       started_at: datetime
       completed_at: datetime
       duration_seconds: float
       total_items: int
       success_items: int
       failed_items: int
       freed_size: int
       success_rate: float
       details: List[dict]
   ```

3. **CleanupSignal 类** - 清理信号
   ```python
   class CleanupSignal(QObject):
       """清理信号（用于更新 UI）"""
       progress_updated = pyqtSignal(int, str)  # (百分比, 当前状态)
       phase_changed = pyqtSignal(str)  # 阶段变化：'scanning', 'analyzing', 'cleaning', 'completed'
       cleanup_completed = pyqtSignal(CleanupReport)
       cleanup_failed = pyqtSignal(str)
   ```

---

### Part 3: 前端集成（OpenCode 负责此部分）

**文件：**
- `src/ui/agent_hub_page.py` - 集成一键清理按钮
- `src/ui/components/cleanup_preview_card.py` - 清理预览卡片（新建）

**需求：**

1. **一键清理按钮**
   ```python
   # agent_hub_page.py
   self.cleanup_start_btn = ActionButton(FIF.SEND, "一键清理", self, FilledPushButton)
   self.cleanup_start_btn.clicked.connect(self.on_one_click_cleanup)
   ```

2. **清理预览弹窗**
   ```python
   def show_cleanup_preview(self, plan: CleanupPlan):
       """显示清理预览"""
       preview_dialog = CleanupPreviewDialog(plan)
       if preview_dialog.exec_():
           # 用户确认，执行清理
           self.start_cleanup(plan)
   ```

3. **清理预览卡片**
   ```python
   # cleanup_preview_card.py
   class CleanupPreviewCard(InfoCard):
       """清理预览卡片"""

       def __init__(self, plan: CleanupPlan):
           super().__init__()
           self.plan = plan

           # 显示:
           # - 预计释放空间
           # - 高/中/低风险文件数量
           # - 智能推荐说明
           # - 一键开始按钮
           pass
   ```

4. **清理进度显示**
   ```python
   # 使用 CleanupSignal 更新进度
   def on_progress_update(self, percent: int, status: str):
       self.progress_bar.setValue(percent)
       self.status_label.setText(status)

   def on_cleanup_completed(self, report: CleanupReport):
       self.show_report(report)
       # 撤销按钮
       self.undo_btn.setEnabled(True)
   ```

---

## 实现步骤

### Day 1: 智能推荐算法
1. ✅ 创建 `SmartRecommender` 类（`src/agent/smart_recommender.py`）
2. ✅ 实现 `UserProfile` 类
3. ✅ 实现 `CleanupPlan` 类
4. ✅ 实现 `detect_user_scenario` 方法
5. ✅ 实现 `filter_by_profile` 方法
6. ✅ 实现 `recommend` 方法
7. ✅ 实现用户场景识别规则（游戏/办公/开发/普通）
8. ✅ 实现清理策略（保守/平衡/激进）

### Day 2: 清理流程编排
1. ✅ 创建 `CleanupOrchestrator` 类（`src/agent/cleanup_orchestrator.py`）
2. ✅ 实现 `CleanupReport` 类
3. ✅ 实现 `CleanupSignal` 类
4. ✅ 实现 `generate_cleanup_plan` 方法
5. ✅ 实现 `preview_cleanup` 方法
6. ✅ 实现 `execute_cleanup` 方法
7. ✅ 集成备份功能
8. ✅ 测试完整流程

---

## 验收标准

### 功能验收

1. ✅ 新用户首次打开应用，自动扫描并生成推荐清理内容
2. ✅ 用户点击"一键清理"按钮，弹出预览弹窗
3. ✅ 预览弹窗显示预计释放空间、风险文件数量、智能推荐说明
4. ✅ 用户确认后开始清理，显示实时进度
5. ✅ 清理前自动备份所有待删除文件
6. ✅ 清理完成后显示清理报告（成功/失败/释放空间）
7. ✅ 撤销按钮在 30 天内可点击，可撤销清理

### 性能验收

1. ✅ 用户场景识别 < 1 秒
2. ✅ 生成清理计划 < 2 秒
3. ✅ 清理预览显示 < 0.5 秒（本地数据）

### 代码质量

1. ✅ 单元测试覆盖率 >80%
2. ✅ 所有公共函数有文档字符串
3. ✅ 通过 `flake8` 代码检查
4. ✅ Git 提交符合规范（`feat: 实现...`）

---

## 依赖模块

- `src/agent/backup_manager.py` - 备份管理器（后续任务实现）
- `src/core/cleaner.py` - 清理器（使用 Rust 模块）
- `src/core/scanner.py` - 扫描器（使用 Rust 模块）
- `src/core/rule_engine.py` - 规则引擎（使用 Rust 模块）

---

## 备注

1. 备份功能将在下一个任务 `P0-2: 自动备份系统` 中实现
2. Rust 模块将在 Week 3-4 实现，当前使用 Python 版本
3. UI 集成由 OpenCode 负责（单独的 UI 任务）

---

**任务创建时间：** 2026-02-24 12:25
**预计完成时间：** 2026-02-26
