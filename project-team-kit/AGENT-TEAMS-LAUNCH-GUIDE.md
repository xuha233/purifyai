# PurifyAI v1.0 Agent Teams 启动指南

**项目：** PurifyAI v1.0
**当前分支：** feature/v1.0-refactor
**负责人：** 小午

---

## 状态检查

### 已完成任务
- [x] P0-1: 一键清理 + 智能推荐
- [x] P0-2: 自动备份系统
- [x] P0-3: 一键撤销功能

### 待开始任务
- [ ] P0-4: 增量清理模式（约 3 小时）
- [ ] P0-5: 智能体页面重新设计（约 6 小时）

**整体进度：** ~45%

---

## Agent Teams 团队配置

### 1. dev（开发团队）
**职责：** 后端 Python 开发、智能推荐算法、清理编排逻辑
**队友：** 3 名
**模型：** Sonnet

**任务：**
- P0-4-1: 实现 last_cleanup_files.json 存储
- P0-4-2: 完善增量清理推荐逻辑
- P0-5-3: 分析 AgentHubPage 后端逻辑

### 2. frontend（前端团队）
**职责：** PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
**队友：** 3 名
**模型：** Sonnet

**任务：**
- P0-4-3: agent_hub_page.py 添加增量清理按钮
- P0-4-4: 增量清理预览 UI 集成
- P0-5-3: 重构 AgentHubPage 主布局
- P0-5-4: 精简选项卡
- P0-5-5: 优化导航栏

### 3. testing（测试团队）
**职责：** 单元测试、集成测试、边界条件测试
**队友：** 2 名
**模型：** Sonnet

**任务：**
- P0-4-5: 单元测试和集成测试
- P0-5-6: UI 测试
- P0-5-7: 用户体验测试

### 4. docs（文档团队）
**职责：** 任务文件编写、开发文档维护、迭代计划更新
**队友：** 2 名
**模型：** Sonnet

**任务：**
- P0-5-1: 分析 AgentHubPage 结构
- P0-5-2: 设计新的页面布局

---

## 启动 Agent Teams

### Step 1: 启动 Claude Code

在项目目录下启动 Claude Code：

```bash
cd G:/docker/diskclean
claude
```

### Step 2: 创建队友

在 Claude Code 中输入以下提示：

```
我需要为 PurifyAI v1.0 项目搭建 Agent Teams，请创建以下团队：

团队 1: dev（开发团队）
- 队友数量：3 名
- 专长：后端 Python 开发、智能推荐算法、清理编排逻辑
- 负责：P0-4-1、P0-4-2

团队 2: frontend（前端团队）
- 队友数量：3 名
- 专长：PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
- 负责：P0-4-3、P0-4-4、P0-5-3、P0-5-4、P0-5-5

团队 3: testing（测试团队）
- 队友数量：2 名
- 专长：单元测试、集成测试、边界条件测试
- 负责：P0-4-5、P0-5-6、P0-5-7

团队 4: docs（文档团队）
- 队友数量：2 名
- 专长：任务文件编写、开发文档维护、迭代计划更新
- 负责：P0-5-1、P0-5-2

当前项目信息：
- 项目路径：G:/docker/diskclean
- 分支：feature/v1.0-refactor
- 开发进度报告：project-team-kit/DEV-PROGRESS-REPORT-v1.0.md

请设置为 Delegate 模式，我只负责协调和任务分配，不直接写代码。
```

### Step 3: 分配任务

创建完团队后，输入以下提示：

```
首先，请阅读开发进度报告：
cat project-team-kit/DEV-PROGRESS-REPORT-v1.0.md

然后，请队友开始认领以下任务（优先级：P0-4 > P0-5）：

P0-4 任务（增量清理模式，约 3 小时）：
1. [dev] P0-4-1: 实现 last_cleanup_files.json 存储
2. [dev] P0-4-2: 完善增量清理推荐逻辑
3. [frontend] P0-4-3: agent_hub_page.py 添加增量清理按钮
4. [frontend] P0-4-4: 增量清理预览 UI 集成
5. [testing] P0-4-5: 单元测试和集成测试

P0-5 任务（智能体页面重新设计，约 6 小时）：
6. [docs] P0-5-1: 分析 AgentHubPage 结构
7. [docs] P0-5-2: 设计新的页面布局
8. [frontend] P0-5-3: 重构 AgentHubPage 主布局
9. [frontend] P0-5-4: 精简选项卡
10. [frontend] P0-5-5: 优化导航栏
11. [testing] P0-5-6: UI 测试
12. [testing] P0-5-7: 用户体验测试

请开始认领任务！
```

---

## 文件职责划分

### dev 团队可修改的文件
- `src/agent/smart_recommender.py` (增量推荐逻辑)
- `src/agent/cleanup_orchestrator.py` (清理编排逻辑)
- `src/core/backup_manager.py` (备份扩展)
- `src/core/restore_manager.py` (恢复扩展)

### frontend 团队可修改的文件
- `src/ui/agent_hub_page.py` (主页面布局)
- `src/ui/cleanup_preview_card.py` (预览卡片)
- `src/ui/cleanup_progress_widget.py` (进度组件)
- `src/ui/*.py` (其他 UI 组件)

### testing 团队可修改的文件
- `tests/` (测试目录，需创建)
- `tests/unit/` (单元测试)
- `tests/integration/` (集成测试)
- `tests/ui/` (UI 测试)

### docs 团队可修改的文件
- `project-team-kit/tasks/P0-INCREMENTAL-CLEANUP.md` (任务书)
- `project-team-kit/tasks/P0-AGENT-HUB-REDESIGN.md` (任务书)
- `project-team-kit/ITERATION-PLAN-v1.0.md` (迭代计划更新)
- `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md` (进度更新)

---

## 协作模式

### 避免文件冲突
- 明确划分每个团队的文件职责
- 通过任务依赖确保共享文件只有一个写入者
- 在 `.claude/teams/` 目录中查看团队配置

### 上下文传递
- 队友会自动加载 CLAUDE.md、MCP 服务器
- 在任务描述中包含充足的上下文
- 明确指定相关文件路径

### Token 管理
- 每个队友使用独立的上下文窗口
- 简单任务用单个队友完成
- Agent Teams 聚焦于讨论、审查和并行探索

---

## 预期结果

### P0-4 完成后（Day 3 下午）
- 增量清理功能可用
- 用户可以选择只清理新文件
- 测试通过

### P0-5 完成后（Day 4 晚上）
- AgentHubPage 重新设计完成
- UI 更新、选项卡精简
- 用户体验优化
- 测试通过

### v1.0 Alpha 版本
- 所有 P0 功能完成
- 稳定性 85%+
- 准备内部测试

---

## 备注

- **模式：** Delegate 模式（主管只协调，不写代码）
- **显示模式：** tmux（建议多团队同时运行时使用）
- **预计完成：** Day 4 晚上约 20:00
- **当前里程碑：** P0-4 + P0-5 → v1.0 Alpha

---

**准备时间：** 2026-02-24 18:00
**准备人：** 小午 🦁
