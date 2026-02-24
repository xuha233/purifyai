# PurifyAI v1.0 Agent Teams 配置

**项目：** PurifyAI v1.0 开发
**版本：** v1.0-refactor
**团队主管：** 小午 🦁（产品经理 + 项目经理）

---

## 团队设计

### 团队 1: dev（开发团队）

**职责：** 后端开发、代码编写

**队友配置：**
- 队友数量：3 名
- 模型：Sonnet
- 专长：
  - 后端 Python 开发
  - 智能推荐算法
  - 清理编排逻辑

---

### 团队 2: frontend（前端团队）

**职责：** 前端开发、UI 组件

**队友配置：**
- 队友数量：3 名
- 模型：Sonnet
- 专长：
  - PyQt5 + qfluentwidgets UI 开发
  - 组件设计与集成
  - 用户体验优化

---

### 团队 3: testing（测试团队）

**职责：** 测试执行、Bug 发现

**队友配置：**
- 队友数量：2 名
- 模型：Sonnet
- 专长：
  - 单元测试编写
  - 集成测试执行
  - 边界条件测试

---

### 团队 4: docs（文档团队）

**职责：** 文档编写、任务规划

**队友配置：**
- 队友数量：2 名
- 模型：Sonnet
- 专长：
  - 任务文件编写
  - 开发文档维护
  - 迭代计划更新

---

## 任务列表（P0-4 + P0-5）

### P0-4: 增量清理模式（3 小时）

任务：
1. [dev] 实现 last_cleanup_files.json 存储
2. [dev] 实现 SmartRecommender.recommend_incremental()（已部分实现）
3. [dev] 实现 CleanupOrchestrator.execute_incremental_cleanup()（已部分实现）
4. [frontend] agent_hub_page.py 添加增量清理按钮
5. [frontend] 增量清理预览 UI 集成
6. [testing] 单元测试编写
7. [testing] 集成测试执行

---

### P0-5: 智能体页面重新设计（6 小时）

任务：
1. [docs] 分析当前 AgentHubPage 结构
2. [docs] 设计新的页面布局
3. [frontend] 重构 AgentHubPage 主布局
4. [frontend] 精简选项卡（只保留核心功能）
5. [frontend] 优化导航栏
6. [frontend] 集成所有清理功能入口
7. [testing] UI 测试执行
8. [testing] 用户体验测试

---

## 启动指南

### Step 1: 启动 Claude Code

```bash
cd G:/docker/diskclean
claude --team
```

### Step 2: 创建队友

在 Claude Code 中执行：

```
我需要搭建 PurifyAI 的 Agent Teams，请创建以下团队：

1. dev（开发团队）- 3 名队友，专长：后端 Python 开发、智能推荐算法、清理编排逻辑
2. frontend（前端团队）- 3 名队友，专长：PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
3. testing（测试团队）- 2 名队友，专长：单元测试、集成测试、边界条件测试
4. docs（文档团队）- 2 名队友，专长：任务文件编写、开发文档维护、迭代计划更新

当前目录：G:/docker/diskclean
当前分支：feature/v1.0-refactor
开发进度报告：project-team-kit/DEV-PROGRESS-REPORT-v1.0.md

请设置为 Delegate 模式，我只负责协调和任务分配。
```

### Step 3: 分配任务

```
首先，请阅读开发进度报告：
cat project-team-kit/DEV-PROGRESS-REPORT-v1.0.md

然后，根据任务列表认领任务：

P0-4 任务（优先级：高）：
1. [dev] 实现 last_cleanup_files.json 存储
2. [dev] 完善增量清理推荐逻辑
3. [frontend] agent_hub_page.py 添加增量清理按钮
4. [frontend] 增量清理预览 UI 集成
5. [testing] 单元测试和集成测试

P0-5 任务（优先级：中）：
6. [docs] 分析 AgentHubPage 结构
7. [frontend] 重构 AgentHubPage 主布局
8. [frontend] 精简选项卡
9. [frontend] 优化导航栏
10. [testing] UI 测试

开始吧！
```

---

## 最佳实践

### 防止文件冲突
- 明确划分每个队友的目录/文件职责
- dev 队友只修改 src/agent/ 和 src/core/
- frontend 队友只修改 src/ui/
- testing 队友只修改 tests/
- docs 队友只修改 project-team-kit/

### 上下文传递
- 在任务描述中包含足够的上下文
- 明确指定相关文件路径
- 队友自动加载 CLAUDE.md、任务文件和项目上下文

### 任务依赖
- 前置任务未完成时，后续任务无法被认领
- 通过任务依赖确保协作顺序

---

## 预期结果

### P0-4（预计 3 小时）
- ✅ 后端增量清理逻辑完善
- ✅ 前端增量清理 UI 集成
- ✅ 测试通过

### P0-5（预计 6 小时）
- ✅ AgentHubPage 重新设计
- ✅ UI 更新、选项卡精简
- ✅ 用户体验优化
- ✅ 测试通过

---

## 备注信息

- 当前时间：2026-02-24 17:45
- 当前状态：准备启动 Agent Teams
- 已完成任务：P0-1、P0-2、P0-3
- 下一个里程碑：v1.0 Alpha 版本（P0-4 + P0-5 完成后）

---

**团队主管：** 小午 🦁
**配置文件版本：** 1.0
**创建时间：** 2026-02-24 17:45
