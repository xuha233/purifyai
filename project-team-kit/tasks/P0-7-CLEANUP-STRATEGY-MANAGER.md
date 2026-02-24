# Phase 2: Week 2 P0 任务 - 智能策略推荐

**任务 ID：** P0-7
**优先级：** 🔴 P0
**预计时间：** 6 小时
**开发者：** Claude Code（dev 团队）
**任务类型：** 产品功能后端开发

---

## 🎯 任务目标

实现智能策略推荐系统，根据用户场景和使用习惯，推荐最优的清理策略。

---

## 📋 核心功能

### Part 1: CleanupStrategyManager 实现（2 小时）

**文件：** `src/agent/cleanup_strategy_manager.py`

**新增类：**

#### CleanupStrategy

清理策略数据结构：

```python
@dataclass
class CleanupStrategy:
    """清理策略"""

    strategy_id: str  # 策略 ID
    name: str  # 策略名称
    description: str  # 策略描述

    # 清理规则
    mode: str  # 清理模式（conservative/balanced/aggressive）
    risk_threshold: int  # 风险阈值（0-100）
    priority_categories: List[str]  # 优先清理的类别

    # 时间策略
    schedule: Optional[str]  # 调度计划（daily/weekly/manual）
    preferred_time: Optional[str]  # 偏好时间

    # 性能偏好
    prioritize_size: bool  # 优先处理大文件
    prioritize_recency: bool  # 优先处理最近文件
```

#### CleanupStrategyManager

主要方法：
- `analyze_user_behavior()` - 分析用户行为模式
- `generate_strategy_profile()` - 生成策略画像
- `recommend_strategy()` - 推荐最优策略
- `save_user_strategy()` - 保存用户采用的策略
- `get_strategy_history()` - 获取策略历史

**用户行为分析维度：**

1. **清理频率分析**
   - 用户清理频率（天/周/月）
   - 清理时机偏好（工作日/周末）
   - 清理时间偏好（上午/下午/晚）

2. **清理内容分析**
   - 用户最常清理的类别
   - 用户接受的风险水平
   - 清理空间偏好（小/中/大）

3. **系统使用模式**
   - 磁盘增长速度
   - 系统性能影响
   - 应用使用习惯

---

### Part 2: 策略推荐算法（2 小时）

**新增方法（CleanupStrategyManager）：**

#### recommend_based_on_scenario()

根据用户场景推荐策略：

```python
def recommend_based_on_scenario(self, scenario: UserScenario) -> CleanupStrategy:
    """
    根据用户场景推荐策略

    Args:
        scenario: 用户场景（gamer/office/developer/normal）

    Returns:
        推荐的清理策略
    """
```

**场景策略映射：**

1. **游戏玩家**
   - 优先清理：游戏缓存、临时文件、下载文件夹
   - 模式：激进模式（保留系统文件）
   - 调度：每周
   - 风险阈值：50

2. **办公电脑**
   - 优先清理：浏览器缓存、临时文件、日志文件
   - 模式：平衡模式
   - 调度：每日
   - 风险阈值：30

3. **开发环境**
   - 优先清理：构建缓存、临时文件、日志文件
   - 模式：保守模式（保护开发文件）
   - 调度：手动
   - 风险阈值：20

4. **普通用户**
   - 优先清理：浏览器缓存、临时文件
   - 模式：平衡模式
   - 调度：每周
   - 风险阈值：30

#### recommend_based_on_behavior()

根据用户行为历史推荐策略：

```python
def recommend_based_on_behavior(self, behavior_history: List[CleanupReport]) -> CleanupStrategy:
    """
    根据用户行为历史推荐策略

    Args:
        behavior_history: 清理历史记录列表

    Returns:
        推荐的清理策略
    """
```

**行为分析逻辑：**

1. 分析用户清理频率 → 推荐调度计划
2. 分析用户清理时机 → 推荐偏好时间
3. 分析用户清理内容 → 推荐优先类别
4. 分析用户接受的风险 → 推荐风险阈值

---

### Part 3: 集成到 SmartRecommender（1 小时）

**修改文件：** `src/agent/smart_recommender.py`

**新增方法：**

```python
def recommend_with_strategy(self, scan_results: List[ScanItem],
                          strategy: Optional[CleanupStrategy] = None) -> Tuple[CleanupPlan, CleanupStrategy]:
    """
    使用指定策略进行推荐

    Args:
        scan_results: 扫描结果列表
        strategy: 清理策略（可选，如果为 None 则自动推荐）

    Returns:
        (CleanupPlan, CleanupStrategy) - 清理计划和使用的策略
    """
```

---

### Part 4: 单元测试（1 小时）

**文件：** `tests/test_cleanup_strategy_manager.py`

**测试用例：**
1. 测试游戏玩家策略推荐
2. 测试办公电脑策略推荐
3. 测试开发环境策略推荐
4. 测试普通用户策略推荐
5. 测试用户行为分析
6. 测试策略画像生成
7. 测试策略推荐算法
8. 测试策略历史保存

---

## 🎯 预置策略配置

**文件：** `src/config/strategy_presets.json`

```json
{
  "presets": {
    "gamer": {
      "strategy_id": "gamer_preferred",
      "name": "游戏玩家优化",
      "description": "为游戏玩家优化的清理策略",
      "mode": "aggressive",
      "risk_threshold": 50,
      "priority_categories": [
        "game_cache",
        "temp_files",
        "downloads"
      ],
      "schedule": "weekly",
      "prioritize_size": true,
      "prioritize_recency": false
    },
    "office": {
      "strategy_id": "office_standard",
      "name": "办公电脑标准",
      "description": "适合办公环境的标准清理策略",
      "mode": "balanced",
      "risk_threshold": 30,
      "priority_categories": [
        "browser_cache",
        "temp_files",
        "logs"
      ],
      "schedule": "daily",
      "prioritize_size": false,
      "prioritize_recency": false
    },
    "developer": {
      "strategy_id": "dev_conservative",
      "name": "开发者保守",
      "description": "保护开发文件的保守清理策略",
      "mode": "conservative",
      "risk_threshold": 20,
      "priority_categories": [
        "build_cache",
        "temp_files",
        "logs"
      ],
      "schedule": "manual",
      "prioritize_size": false,
      "prioritize_recency": false
    },
    "normal": {
      "strategy_id": "normal_balanced",
      "name": "普通用户平衡",
      "description": "适合普通用户的平衡清理策略",
      "mode": "balanced",
      "risk_threshold": 30,
      "priority_categories": [
        "browser_cache",
        "temp_files"
      ],
      "schedule": "weekly",
      "prioritize_size": false,
      "prioritize_recency": false
    }
  }
}
```

---

## ✅ 验收标准

- [ ] Part 1: CleanupStrategyManager 类实现完成
- [ ] CleanupStrategy 数据结构定义完整
- [ ] 用户行为分析功能正常（3 个维度）
- [ ] 策略画像生成正确
- [ ] Part 2: 策略推荐算法实现
- [ ] recommend_based_on_scenario() 方法正常工作
- [ ] recommend_based_on_behavior() 方法正常工作
- [ ] 4 个预置策略配置正确
- [ ] Part 3: 集成到 SmartRecommender 完成
- [ ] recommend_with_strategy() 方法正常工作
- [ ] Part 4: 单元测试通过（8/8）
- [ ] 策略配置文件创建完成
- [ ] 所有文件编译通过
- [ ] 代码符合 PEP8 规范
- [ ] 文档字符串齐全

---

## 📝 实施提示

### 用户行为分析示例

```python
def analyze_user_behavior(self, cleanup_history: List[CleanupReport]) -> Dict:
    """
    分析用户行为模式

    Args:
        cleanup_history: 清理历史记录列表

    Returns:
        行为模式字典
    """
    if not cleanup_history:
        return {
            "frequency": "unknown",
            "timing_preference": "unknown",
            "content_preference": "unknown",
            "risk_tolerance": "medium"
        }

    # 计算平均清理频率（天）
    sorted_reports = sorted(cleanup_history, key=lambda r: r.created_at)
    if len(sorted_reports) >= 2:
        avg_interval_days = (
            sorted_reports[-1].created_at - sorted_reports[0].created_at
        ) / (len(sorted_reports) - 1) / 86400
    else:
        avg_interval_days = 7  # 默认值

    # 分析清理时机偏好
    weekday_cleanups = sum(1 for r in cleanup_history if r.created_at.weekday() < 5)
    weekend_cleanups = len(cleanup_history) - weekday_cleanups

    # 分析清理内容偏好
    category_counts = {}
    for report in cleanup_history:
        for detail in report.details:
            category = detail.get('category', 'unknown')
            category_counts[category] = category_counts.get(category, 0) + 1

    top_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else "unknown"

    return {
        "frequency": "daily" if avg_interval_days < 2 else "weekly" if avg_interval_days < 7 else "monthly",
        "timing_preference": "weekday" if weekday_cleanups > weekend_cleanups else "weekend",
        "content_preference": top_category,
        "risk_tolerance": "low" if avg_interval_days > 14 else "medium" if avg_interval_days > 7 else "high"
    }
```

---

## 🔗 依赖关系

- 依赖于：`SmartRecommender`（已实现）
- 依赖于：`CleanupReport`（已实现）
- 输出到：CleanupStrategy 数据结构

---

## 📚 参考资料

- `src/agent/smart_recommender.py` - SmartRecommender 类
- `src/agent/cleanup_orchestrator.py` - CleanupReport 类
- 项目设计文档：`PRODUCT-OPTIMIZATION.md`
- Phase 1 任务：P0-1 一键清理 + 智能推荐

---

## 📊 预期产出

**新增文件：**
1. `src/agent/cleanup_strategy_manager.py` (~400 行)
2. `src/config/strategy_presets.json` (~100 行)
3. `tests/test_cleanup_strategy_manager.py` (~350 行)

**修改文件：**
1. `src/agent/smart_recommender.py` (新增 `recommend_with_strategy()`)

**总计：** ~850 行新增代码

---

**更新时间：** 2026-02-24 20:15
**任务创建者：** 小午 🦁
**状态：** 准备就绪，等待 Claude Code 执行
