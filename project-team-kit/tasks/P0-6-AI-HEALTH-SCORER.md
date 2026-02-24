# Phase 2: Week 2 P0 任务 - AI 健康评分

**任务 ID：** P0-6
**优先级：** 🔴 P0
**预计时间：** 6 小时
**开发者：** Claude Code（dev 团队）
**任务类型：** 产品功能后端开发

---

## 🎯 任务目标

实现 AI 健康评分系统，让用户能够直观地了解磁盘健康状况和清理价值。

---

## 📋 核心功能

### Part 1: AIHealthScorer 实现（2 小时）

**文件：** `src/agent/ai_health_scorer.py`

**新增类：**

#### AIHealthScorer

主要方法：
- `analyze_disk_health()` - 分析磁盘健康状况
- `calculate_health_score()` - 计算健康评分（0-100）
- `generate_health_report()` - 生成健康报告
- `recommend_cleanup_priority()` - 推荐清理优先级

**评分维度：**

1. **磁盘空间占用**（40%）
   - 使用率评分：100 - (使用率 - 30) × 1.5
   - 阈值：<30% (优秀), 30-60% (良好), 60-80% (一般), >80% (差)

2. **可清理空间**（30%）
   - 可清理空间评分：min(100, 可清理MB / 5000 × 100)
   - 阈值：<1GB (优秀), 1-3GB (良好), 3-5GB (一般), >5GB (差)

3. **文件碎片度**（15%）
   - 碎片文件占比评分：100 - (碎片占比 × 2)
   - 阈值：<5% (优秀), 5-15% (良好), 15-30% (一般), >30% (差)

4. **系统性能影响**（15%）
   - 垃圾文件增长速度评分：100 - (增长速度MB/天 × 5)
   - 阈值：<5MB/天 (优秀), 5-20MB/天 (良好), 20-50MB/天 (一般), >50MB/天 (差)

#### HealthReport

数据结构：
- `score` - 总分（0-100）
- `disk_usage_score` - 磁盘空间评分
- `cleanable_space_score` - 可清理空间评分
- `fragmentation_score` - 文件碎片度评分
- `performance_score` - 系统性能评分
- `recommendations` - 改进建议列表
- `priority` - 清理优先级（high/medium/low）

#### HealthRecommendation

数据结构：
- `category` - 类别（disk_space/cleanable_space/fragmentation/performance）
- `issue` - 问题描述
- `solution` - 解决方案
- `potential_save` - 预计节省空间（MB）

---

### Part 2: 集成到 SmartRecommender（1 小时）

**修改文件：** `src/agent/smart_recommender.py`

**新增方法：**

```python
def recommend_with_health_score(self, scan_results: List[ScanItem]) -> Tuple[CleanupPlan, HealthReport]:
    """
    结合健康评分的智能推荐

    Args:
        scan_results: 扫描结果列表

    Returns:
        (CleanupPlan, HealthReport) - 清理计划和健康报告
    """
```

---

### Part 3: 数据层支持（1 小时）

**文件：** `src/data/health_history.py`

**新增类：**

#### HealthHistoryManager

主要方法：
- `save_health_report()` - 保存健康报告
- `get_health_history()` - 获取健康历史
- `calculate_health_trend()` - 计算健康趋势
- `get_health_comparison()` - 获取对比数据

**数据存储：** `data/health_history.json`

数据结构：
```json
{
  "reports": [
    {
      "timestamp": 1714080000000,
      "score": 85,
      "disk_usage_score": 90,
      "cleanable_space_score": 80,
      "fragmentation_score": 85,
      "performance_score": 90
    }
  ]
}
```

---

### Part 4: 单元测试（1 小时）

**文件：** `tests/test_ai_health_scorer.py`

**测试用例：**
1. 测试磁盘使用率评分
2. 测试可清理空间评分
3. 测试文件碎片度评分
4. 测试系统性能评分
5. 测试总分计算
6. 测试健康报告生成
7. 测试清理优先级推荐
8. 测试健康趋势计算

---

### Part 5: 后备方案文件保存（1 小时）

**修改文件：** `src/agent/smart_recommender.py`

**新增方法：**
```python
def save_health_report(self, report: HealthReport) -> bool:
    """
    保存健康报告到文件（后备方案，独立于 HealthHistoryManager）

    Args:
        report: 健康报告

    Returns:
        是否保存成功
    """
```

**文件路径：** `data/last_health_report.json`

---

## 🎨 UI 层（由 OpenCode 负责，下一任务 Part A）

### 任务：集成健康评分到 UI（2 小时）

**任务文件：** `P0-7-UI.AI_HEALTH_DISPLAY.md`

**目标：** 将 AI 健康评分显示在 Agent Hub 页面的 Overview Tab 中

**实现内容：**
1. 健康评分卡片（HealthScoreCard）
2. 健康趋势图
3. 改进建议列表
4. 健康评分颜色编码（>80 绿色, 60-80 黄色, <60 红色）

---

## ✅ 验收标准

- [ ] Part 1: AIHealthScorer 类实现完成
- [ ] 4 个评分维度正确实现（磁盘空间、可清理空间、文件碎片、系统性能）
- [ ] 健康评分计算准确（0-100 分）
- [ ] 健康报告包含所有必要字段
- [ ] 清理优先级推荐合理
- [ ] Part 2: 集成到 SmartRecommender 完成
- [ ] `recommend_with_health_score()` 方法正常工作
- [ ] Part 3: HealthHistoryManager 实现
- [ ] 健康报告持久化（health_history.json）
- [ ] 健康趋势计算正确
- [ ] Part 4: 单元测试通过（8/8）
- [ ] Part 5: 后备方案文件保存实现
- [ ] 所有文件编译通过
- [ ] 代码符合 PEP8 规范
- [ ] 文档字符串齐全

---

## 📝 实施提示

### 评分算法示例

```python
def calculate_health_score(self, disk_usage_percent: float,
                          cleanable_space_mb: float,
                          fragmentation_percent: float,
                          growth_speed_mb_per_day: float) -> int:
    """
    计算健康评分

    Args:
        disk_usage_percent: 磁盘使用率（0-100）
        cleanable_space_mb: 可清理空间（MB）
        fragmentation_percent: 碎片文件百分比（0-100）
        growth_speed_mb_per_day: 垃圾文件增长速度（MB/天）

    Returns:
        健康评分（0-100）
    """
    # 磁盘空间评分（40%）
    if disk_usage_percent < 30:
        disk_score = 100
    elif disk_usage_percent < 60:
        disk_score = 100 - (disk_usage_percent - 30) * 1.5
    elif disk_usage_percent < 80:
        disk_score = 70 - (disk_usage_percent - 60) * 2.5
    else:
        disk_score = 20 - (disk_usage_percent - 80) * 1

    # 可清理空间评分（30%）
    cleanable_score = min(100, cleanable_space_mb / 5000 * 100)

    # 文件碎片评分（15%）
    frag_score = max(0, 100 - fragmentation_percent * 2)

    # 系统性能评分（15%）
    perf_score = max(0, 100 - growth_speed_mb_per_day * 5)

    # 加权总分
    total_score = (
        disk_score * 0.4 +
        cleanable_score * 0.3 +
        frag_score * 0.15 +
        perf_score * 0.15
    )

    return round(total_score)
```

### 改进建议示例

```python
def generate_recommendations(self, report: HealthReport) -> List[HealthRecommendation]:
    """
    生成改进建议

    Args:
        report: 健康报告

    Returns:
        改进建议列表
    """
    recommendations = []

    # 磁盘空间建议
    if report.disk_usage_score < 70:
        recommendations.append(HealthRecommendation(
            category="disk_space",
            issue=f"磁盘使用率 {disk_usage_percent}%，建议清理",
            solution="执行一键清理，释放磁盘空间",
            potential_save=cleanable_space_mb
        ))

    # 可清理空间建议
    if report.cleanable_space_score < 60:
        recommendations.append(HealthRecommendation(
            category="cleanable_space",
            issue=f"可清理空间 {cleanable_space_mb} MB",
            solution="增量清理模式可以快速释放空间",
            potential_save=cleanable_space_mb * 0.8
        ))

    return recommendations
```

---

## 🔗 依赖关系

- 依赖于：`SmartRecommender`（已实现）
- 依赖数据：`last_cleanup_files.json`（如有）
- 输出到：HealthReport 数据结构

---

## 📚 参考资料

- `src/agent/smart_recommender.py` - SmartRecommender 类
- `src/models.py` - ScanItem 模型
- 项目设计文档：`PRODUCT-OPTIMIZATION.md`

---

## 📊 预期产出

**新增文件：**
1. `src/agent/ai_health_scorer.py` (~400 行)
2. `src/data/health_history.py` (~300 行)
3. `tests/test_ai_health_scorer.py` (~300 行)

**修改文件：**
1. `src/agent/smart_recommender.py` (新增 `recommend_with_health_score()`, `save_health_report()`)

**总计：** ~1000 行新增代码

---

**更新时间：** 2026-02-24 19:10
**任务创建者：** 小午 🦁
**状态：** 准备就绪，等待 Agent Teams 执行
