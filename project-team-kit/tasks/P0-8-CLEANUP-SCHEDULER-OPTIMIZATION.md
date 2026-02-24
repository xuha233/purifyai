# Phase 2: Week 2 P0 任务 - 定时清理优化

**任务 ID：** P0-8
**优先级：** 🔴 P0
**预计时间：** 3 小时
**开发者：** Claude Code（dev 团队）
**任务类型：** 产品功能后端开发

---

## 🎯 任务目标

优化定时清理功能，支持灵活的调度策略、智能时机选择和后台静默执行。

---

## 📋 核心功能

### Part 1: CleanupScheduler 重构（1.5 小时）

**文件：** `src/agent/cleanup_scheduler.py`（重新设计）

**新增类：**

#### ScheduleConfig

调度配置数据结构：

```python
@dataclass
class ScheduleConfig:
    """调度配置"""

    schedule_id: str  # 调度 ID
    name: str  # 调度名称

    # 调度类型
    schedule_type: str  # "daily"/"weekly"/"monthly"/"manual"
    interval_days: Optional[int]  # 间隔天数

    # 时间设置
    time_of_day: Optional[str]  # 每天执行时间（HH:MM 格式）
    day_of_week: Optional[int]  # 每周执行日期（0-6，0=周一）
    day_of_month: Optional[int]  # 每月执行日期（1-31）

    # 执行条件
    min_space_threshold: int = 5  # 最小磁盘空间阈值（GB）
    max_age_days: int = 30  # 最大文件年龄（天）

    # 用户策略
    strategy_id: Optional[str]  # 关联的清理策略 ID

    # 执行选项
    skip_on_battery: bool = True  # 电池模式下跳过
    skip_on_fullscreen: bool = False  # 全屏模式下跳过
    allow_background: bool = True  # 允许后台静默执行
```

#### CleanupScheduler

主要方法（重写）：
- `create_schedule()` - 创建定时清理任务
- `update_schedule()` - 更新定时清理配置
- `delete_schedule()` - 删除定时清理任务
- `get_schedules()` - 获取所有定时清理任务
- `get_next_run_time()` - 获取下次执行时间
- `is_schedule_due()` - 检查是否该执行清理

---

### Part 2: 智能时机选择（1 小时）

**新增方法（CleanupScheduler）：**

#### calculate_optimal_time()

计算最佳执行时机：

```python
def calculate_optimal_time(self, schedule: ScheduleConfig) -> datetime:
    """
    计算最佳执行时机

    考虑因素：
    1. 用户使用模式（空闲时段）
    2. 系统负载（后台执行）
    3. 磁盘空间需求
    4. 策略偏好时间

    Args:
        schedule: 调度配置

    Returns:
        最佳执行时间
    """
```

**时机选择策略：**

1. **每日调度**
   - 首选：18:00-20:00（工作日下班）
   - 备选：21:00-23:00（晚间休闲）
   - 避免：9:00-12:00，14:00-17:00（工作时间）

2. **每周调度**
   - 首选：周六或周日下午
   - 备选：周五晚上
   - 避免：周一至周五工作日

3. **智能空闲检测**
   - 检测用户空闲时间（无鼠标键盘操作 > 15 分钟）
   - 检测后台资源可用性（CPU < 50%，内存 < 70%）
   - 检测全屏应用（游戏、视频播放）

---

### Part 3: 后台静默执行（30 分钟）

**新增方法（CleanupScheduler）：**

#### execute_background_cleanup()

后台静默执行清理：

```python
def execute_background_cleanup(self, schedule: ScheduleConfig) -> bool:
    """
    后台静默执行清理

    特性：
    - 最小化 UI 干扰（不弹出对话框）
    - 使用系统托盘通知
    - 支持静默备份
    - 生成清理报告（可选邮件通知）

    Args:
        schedule: 调度配置

    Returns:
        是否执行成功
    """
```

**静默执行特性：**

1. **无 UI 干扰**
   - 不弹出预览对话框
   - 不显示进度条
   - 最小化到系统托盘

2. **托盘通知**
   - 清理完成后显示通知
   - 显示清理结果摘要
   - 点击查看详细报告

3. **日志记录**
   - 记录到 `logs/scheduler_log.json`
   - 包含执行时间、清理结果、错误信息

---

### Part 4: 单元测试（30 分钟）

**文件：** `tests/test_cleanup_scheduler.py`

**测试用例：**
1. 测试创建每日调度
2. 测试创建每周调度
3. 测试创建每月调度
4. 测试获取下次执行时间
5. 测试检查是否该执行
6. 测试最佳时机计算
7. 测试后台清理执行
8. 测试跳过条件（电池/全屏）

---

## 🎯 调度预置模板

**文件：** `src/config/schedule_presets.json`

```json
{
  "presets": {
    "daily_work": {
      "schedule_id": "daily_work_standard",
      "name": "工作日每日清理",
      "schedule_type": "daily",
      "interval_days": 1,
      "time_of_day": "18:30",
      "min_space_threshold": 5,
      "allow_background": true
    },
    "weekly_home": {
      "schedule_id": "weekly_home_optimal",
      "name": "家庭电脑每周清理",
      "schedule_type": "weekly",
      "day_of_week": 5,
      "time_of_day": "20:00",
      "min_space_threshold": 5,
      "allow_background": true
    },
    "monthly_deep": {
      "schedule_id": "monthly_deep_clean",
      "name": "每月深度清理",
      "schedule_type": "monthly",
      "day_of_month": 1,
      "time_of_day": "21:00",
      "max_age_days": 30,
      "allow_background": false
    },
    "idle_detect": {
      "schedule_id": "idle_based",
      "name": "空闲时清理",
      "schedule_type": "manual",
      "min_space_threshold": 2,
      "skip_on_battery": true,
      "skip_on_fullscreen": true,
      "allow_background": true
    }
  }
}
```

---

## ✅ 验收标准

- [ ] Part 1: CleanupScheduler 重构完成
- [ ] ScheduleConfig 数据结构定义完整
- [ ] 4 种调度类型支持（daily/weekly/monthly/manual）
- [ ] 3 个执行条件（最小空间/最大年龄/策略）
- [ ] Part 2: 智能时机选择实现
- [ ] calculate_optimal_time() 方法正常工作
- [ ] 工作日/周末策略正确
- [ ] 空闲检测功能正常
- [ ] Part 3: 后台静默执行实现
- [ ] execute_background_cleanup() 方法正常工作
- [ ] 托盘通知正常
- [ ] 日志记录完整
- [ ] Part 4: 单元测试通过（8/8）
- [ ] 调度预置配置文件创建完成
- [ ] 所有文件编译通过
- [ ] 代码符合 PEP8 规范
- [ ] 文档字符串齐全

---

## 📝 实施提示

### 最佳时机计算示例

```python
def calculate_optimal_time(self, schedule: ScheduleConfig) -> datetime:
    """计算最佳执行时机"""
    now = datetime.now()

    # 获取用户空闲时段（从历史记录分析）
    idle_periods = self._analyze_idle_periods()

    # 基础时间：根据调度类型确定
    if schedule.schedule_type == "daily":
        if schedule.time_of_day:
            base_time = datetime.combine(now.date(),
                                         datetime.strptime(schedule.time_of_day, "%H:%M").time())
        else:
            base_time = datetime.combine(now.date(), datetime(18, 0))
    elif schedule.schedule_type == "weekly":
        if schedule.day_of_week is not None:
            days_until_run = (schedule.day_of_week - now.weekday()) % 7 or 7
            base_date = now + timedelta(days=days_until_run)
            base_time = datetime.combine(base_date, datetime(20, 0))
        else:
            base_time = now + timedelta(days=7)
    else:
        base_time = now

    # 检查是否为工作日/周末
    is_weekday = 0 <= now.weekday() <= 4

    # 调整到空闲时段
    if idle_periods:
        best_idle = self._find_best_idle_period(base_time, idle_periods)
        if best_idle:
            return best_idle

    return base_time
```

---

## 🔗 依赖关系

- 依赖于：`CleanupStrategy`（P0-7 已实现）
- 依赖于：`CleanupOrchestrator`（P0-1 已实现）
- 输出到：ScheduleConfig 数据结构

---

## 📚 参考资料

- `src/agent/cleanup_orchestrator.py` - 清理流程编排
- `src/agent/cleanup_strategy_manager.py` - 策略管理
- 项目设计文档：`PRODUCT-OPTIMIZATION.md`
- Phase 2 前置任务：P0-6 AI 健康评分、P0-7 智能策略推荐

---

## 📊 预期产出

**新增文件：**
1. `src/agent/cleanup_scheduler.py` (~500 行，重构)
2. `src/config/schedule_presets.json` (~120 行)
3. `tests/test_cleanup_scheduler.py` (~400 行)

**修改文件：**
1. `src/agent/cleanup_orchestrator.py` (支持后台执行参数)

**总计：** ~1,020 行新增/重构代码

---

**更新时间：** 2026-02-24 20:10
**任务创建者：** 小午 🦁
**状态：** 准备就绪，等待 Claude Code 执行
