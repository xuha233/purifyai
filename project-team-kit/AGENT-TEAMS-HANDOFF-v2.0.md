# PurifyAI Agent Teams - 智能体交接方案 v2.0

**项目：** PurifyAI v1.0
**当前分支：** feature/v1.0-refactor
**负责人：** 小午 🦁（团队主管 + 项目经理）
**版本：** 2.0（适配 Claude Code Agent Teams）

---

## 团队概览

### 团队结构

| 团队 | 成员数 | 模型 | 专长 | 负责文件 |
|------|--------|------|------|---------|
| **dev** | 3 名 | Sonnet | 后端 Python、智能推荐、清理编排逻辑 | `src/agent/`, `src/core/` |
| **frontend** | 3 名 | Sonnet | PyQt5 + qfluentwidgets UI、组件设计、UX | `src/ui/` |
| **testing** | 2 名 | Sonnet | 单元测试、集成测试、边界条件测试 | `tests/` |
| **docs** | 2 名 | Sonnet | 任务规划、文档编写、迭代计划 | `project-team-kit/` |

**总计：** 10 名队友

---

### 角色定义

#### 团队主管 - 小午 🦁

**职责：**
- 创建任务文件（.md）
- 协调团队工作
- 审核队友计划
- 分配任务给团队成员
- 不直接编写代码（Delegate 模式）

**工具：**
- Claude Code Agent Teams
- PowerShell
- Git

#### dev（开发团队）

**队长：** dev-1（3 名队友）

**职责：**
- 实现后端逻辑
- 开发智能推荐算法
- 实现清理编排逻辑
- 数据模型设计

**技术栈：**
- Python 3.7+
- dataclass
- PyQt5 signals/slots

**文件权限：**
- ✅ 读/写：`src/agent/`、`src/core/`
- 🚫 禁止写：`src/ui/`、`tests/`、`project-team-kit/`

---

#### frontend（前端团队）

**队长：** frontend-1（3 名队友）

**职责：**
- 实现 UI 组件
- 设计用户界面
- 集成后端接口
- 优化用户体验

**技术栈：**
- PyQt5
- qfluentwidgets
- Qt signals/slots

**文件权限：**
- ✅ 读/写：`src/ui/`
- ✅ 读：`src/agent/`、`src/core/`（了解接口）
- 🚫 禁止写：`src/agent/`、`src/core/`、`tests/`、`project-team-kit/`

---

#### testing（测试团队）

**队长：** testing-1（2 名队友）

**职责：**
- 编写单元测试
- 执行集成测试
- 测试边界条件
- 报告 Bug 和质量指标

**技术栈：**
- pytest
- unittest
- PyQt5 Test Framework

**文件权限：**
- ✅ 读：所有代码文件
- ✅ 读/写：`tests/`
- 🚫 禁止写：`src/`、`project-team-kit/`

---

#### docs（文档团队）

**队长：** docs-1（2 名队友）

**职责：**
- 编写任务文件
- 维护迭代计划
- 更新开发进度
- 文档化接口规范

**文件权限：**
- ✅ 读：所有代码和文档
- ✅ 读/写：`project-team-kit/`
- 🚫 禁止写：`src/`、`tests/`

---

## 交接协议

### 文件读取顺序

#### 团队主管 - 小午 🦁

1. `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md` - 开发进度
2. `project-team-kit/AGENT-TEAMS-CONFIG.md` - 团队配置
3. `project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md` - 本文件
4. `project-team-kit/ITERATION-PLAN-v1.0.md` - 迭代计划

---

#### dev（开发团队）

1. `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md`（了解整体进度）
2. `project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md`（本文件 - dev 部分）
3. `src/agent/smart_recommender.py`（智能推荐器）
4. `src/agent/cleanup_orchestrator.py`（清理编排器）
5. `src/core/backup_manager.py`（备份管理器）
6. `src/core/restore_manager.py`（恢复管理器）

---

#### frontend（前端团队）

1. `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md`（了解整体进度）
2. `project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md`（本文件 - frontend 部分）
3. `src/ui/agent_hub_page.py`（主页面）
4. `src/ui/cleanup_preview_card.py`（预览卡片）
5. `src/ui/cleanup_progress_widget.py`（进度组件）
6. `src/ui/restore_dialog.py`（恢复对话框）

---

#### testing（测试团队）

1. `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md`（了解整体进度）
2. `project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md`（本文件 - testing 部分）
3. `src/agent/`、`src/core/`（了解后端逻辑）
4. `src/ui/`（了解 UI 组件）
5. `tests/`（测试目录）

---

#### docs（文档团队）

1. `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md`（当前进度）
2. `project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md`（本文件 - docs 部分）
3. `project-team-kit/ITERATION-PLAN-v1.0.md`（迭代计划）
4. `project-team-kit/DEVELOPMENT-GUIDE-v1.0.md`（开发指南）
5. `project-team-kit/PRODUCT-ANALYSIS-v1.0.md`（产品分析）

---

## 消息协议（Context Bridge v2.0）

### 消息格式

```json
{
  "sender": "dev-1",
  "recipient": "frontend-1",
  "message_type": "handoff",
  "timestamp": "2026-02-24T18:30:00Z",
  "task_id": "P0-4-1",
  "content": {
    "status": "completed",
    "changed_files": [
      "src/agent/smart_recommender.py"
    ],
    "api_changes": {
      "new_methods": [
        "SmartRecommender.get_incremental_files()",
        "SmartRecommender.load_last_cleanup_files()"
      ],
      "method_signatures": {
        "SmartRecommender.get_incremental_files": "(current_scan: List[ScanItem]) -> List[ScanItem]",
        "SmartRecommender.load_last_cleanup_files": "() -> List[str]"
      }
    },
    "requirements": [
      "Frontend needs to call get_incremental_files() for incremental cleanup",
      "Frontend needs to clean up old files when incremental cleanup completes"
    ],
    "deadline": "2026-02-24T21:00:00Z"
  }
}
```

---

### 消息类型

| 类型 | 用途 | 示例 |
|------|------|------|
| **handoff** | 任务完成交接 | dev 完成后端逻辑，通知 frontend 集成 |
| **task** | 分配新任务 | 团队主管分配任务给 teammates |
| **blocker** | 报告阻塞 | 队友报告任务阻塞，需要协调 |
| **report** | 进度报告 | 队友报告当前进度 |
| **review** | 代码审查请求 | 请求其他团队审查代码 |

---

## 工作流程

### 场景 1: 新功能开发（P0-4 增量清理）

**第一阶段：需求分析（docs）**
1. docs 阅读迭代计划和产品分析
2. docs 创建任务文件 `P0-INCREMENTAL-CLEANUP.md`
3. docs 通知团队主管任务已准备

---

**第二阶段：后端实现（dev）**
1. dev-1 认领任务 "P0-4-1: 实现 last_cleanup_files.json 存储"
2. dev-1 实现 `load_last_cleanup_files()` 和 `save_last_cleanup_files()`
3. dev-1 发送 handoff 消息给 frontend
4. dev-2 认领任务 "P0-4-2: 完善增量清理推荐逻辑"
5. dev-2 实现增量清理推荐算法
6. dev-2 发送 handoff 消息给 frontend

---

**第三阶段：前端集成（frontend）**
1. frontend-1 认领任务 "P0-4-3: agent_hub_page.py 添加增量清理按钮"
2. frontend-1 阅读后端 API 接口
3. frontend-1 实现增量清理按钮和 UI
4. frontend-1 发送 handoff 消息给 frontend-2
5. frontend-2 认领任务 "P0-4-4: 增量清理预览 UI 集成"
6. frontend-2 实现增量清理预览 UI
7. frontend-2 发送 handoff 消息给 testing

---

**第四阶段：测试验证（testing）**
1. testing-1 认领任务 "P0-4-5: 单元测试和集成测试"
2. testing-1 编写单元测试
3. testing-1 执行集成测试
4. testing-1 报告测试结果
5. 如果有 Bug，发送 report 消息给 dev/frontend
6. 修复后重新测试

---

**第五阶段：完成验证（团队主管）**
1. 团队主管审核所有代码
2. 团队主管运行编译检查
3. 团队主管更新开发进度报告
4. 团队主管提交代码到 Git
5. P0-4 完成 ✅

---

### 场景 2: Bug 修复

**第一阶段：Bug 报告（testing）**
1. testing 发现 Bug
2. testing 发送 report 消息给团队主管
3. 团队主管判断 Bug 类型（前端/后端）

---

**第二阶段：Bug 分析（dev/frontend）**
1. dev 或 frontend 认领 Bug 任务
2. 分析问题根源
3. 制定修复计划
4. 发送 review 消息给其他团队成员

---

**第三阶段：Bug 修复**
1. 其他团队成员 review 修复方案
2. 实施修复
3. 运行测试验证

---

**第四阶段：验证完成**
1. testing 再次测试
2. 如果通过，Bug 关闭 ✅
3. 如果失败，返回第二阶段

---

## 协作规则

### 防止文件冲突

#### 规则 1: 明确的文件职责

| 文件类型 | 负责团队 | 说明 |
|---------|----------|------|
| `src/agent/*.py` | dev | 后端逻辑 |
| `src/core/*.py` | dev | 核心模块 |
| `src/ui/*.py` | frontend | UI 组件 |
| `tests/*.py` | testing | 测试代码 |
| `project-team-kit/*.md` | docs | 文档 |

---

#### 规则 2: 接口优先

- **后端优先定义接口**
- frontend 只能读后端文件，不能写
- 如果需要修改后端接口，发送 review 消息

---

#### 规则 3: 任务依赖

- 通过任务依赖确保执行顺序
- 前置任务未完成时，后续任务无法被认领
- 例如：`P0-4-2` 依赖 `P0-4-1`

---

### 消息传递

#### 规则 4: 使用标准消息格式

- 所有消息必须使用 JSON 格式
- 包含必需字段：sender、recipient、message_type、task_id、content
- 发送后等待对方确认

---

#### 规则 5: 及时响应

- 收到消息后尽快回应
- 如果被阻塞，立即发送 blocker 消息
- 不要让任务停滞超过 30 分钟

---

### 代码质量

#### 规则 6: 编译检查

- 提交代码前必须运行编译检查
- 所有文件必须编译通过
- 类型注解必须完整

---

#### 规则 7: 文档完整

- 新增方法必须包含文档字符串
- 复杂逻辑需要注释
- 数据结构必须说明

---

## 当前任务分配

### P0-4: 增量清理模式（优先级：高，预计 3 小时）

| 任务 ID | 团队 | 队友 | 状态 |
|---------|------|------|------|
| P0-4-1 | dev | dev-1 | ⚪ 待认领 |
| P0-4-2 | dev | dev-2 | ⚪ 待认领 |
| P0-4-3 | frontend | frontend-1 | ⚪ 待认领 |
| P0-4-4 | frontend | frontend-2 | ⚪ 待认领 |
| P0-4-5 | testing | testing-1 | ⚪ 待认领 |

---

### P0-5: 智能体页面重新设计（优先级：中，预计 6 小时）

| 任务 ID | 团队 | 队友 | 状态 |
|---------|------|------|------|
| P0-5-1 | docs | docs-1 | ⚪ 待认领 |
| P0-5-2 | docs | docs-2 | ⚪ 待认领 |
| P0-5-3 | frontend | frontend-3 | ⚪ 待认领 |
| P0-5-4 | frontend | frontend-1 | ⚪ 待认领 |
| P0-5-5 | frontend | frontend-2 | ⚪ 待认领 |
| P0-5-6 | testing | testing-1 | ⚪ 待认领 |
| P0-5-7 | testing | testing-2 | ⚪ 待认领 |

---

## 启动指南

### Step 1: 启动 Claude Code

```bash
cd G:/docker/diskclean
claude
```

### Step 2: 创建队友

在 Claude Code 中输入：

```
我需要为 PurifyAI v1.0 项目搭建 Agent Teams，请创建以下团队：

团队 1: dev（开发团队）
- 队友数量：3 名
- 专长：后端 Python 开发、智能推荐算法、清理编排逻辑
- 可修改文件：src/agent/、src/core/

团队 2: frontend（前端团队）
- 队友数量：3 名
- 专长：PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
- 可修改文件：src/ui/
- 可读文件：src/agent/、src/core/（了解接口）

团队 3: testing（测试团队）
- 队友数量：2 名
- 专长：单元测试、集成测试、边界条件测试
- 可修改文件：tests/
- 可读文件：所有代码

团队 4: docs（文档团队）
- 队友数量：2 名
- 专长：任务文件编写、开发文档维护、迭代计划更新
- 可修改文件：project-team-kit/

当前项目信息：
- 项目路径：G:/docker/diskclean
- 分支：feature/v1.0-refactor
- 开发进度报告：project-team-kit/DEV-PROGRESS-REPORT-v1.0.md

请设置为 Delegate 模式，我只负责协调和任务分配，不直接写代码。
```

### Step 3: 分配任务

```
首先，请阅读交接协议：
cat project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

然后，请队友按照消息协议开始认领以下任务（优先级：P0-4 > P0-5）：

P0-4 任务（增量清理模式，约 3 小时）：
1. [dev] P0-4-1: 实现 last_cleanup_files.json 存储
2. [dev] P0-4-2: 完善增量清理推荐逻辑
3. [frontend] P0-4-3: agent_hub_page.py 添加增量清理按钮
4. [frontend] P0-4-4: 增量清理预览 UI 集成
5. [testing] P0-4-5: 单元测试和集成测试

请开始认领任务！
```

---

## 附录: 队友列表

### dev（开发团队）

| 队友 ID | 角色 | 当前任务 |
|---------|------|----------|
| dev-1 | 队长 | P0-4-1（待认领） |
| dev-2 | 成员 | P0-4-2（待认领） |
| dev-3 | 成员 | 待命 |

---

### frontend（前端团队）

| 队友 ID | 角色 | 当前任务 |
|---------|------|----------|
| frontend-1 | 队长 | P0-4-3（待认领） |
| frontend-2 | 成员 | P0-4-4（待认领） |
| frontend-3 | 成员 | P0-5-3（待认领） |

---

### testing（测试团队）

| 队友 ID | 角色 | 当前任务 |
|---------|------|----------|
| testing-1 | 队长 | P0-4-5（待认领） |
| testing-2 | 成员 | P0-5-6（待认领） |

---

### docs（文档团队）

| 队友 ID | 角色 | 当前任务 |
|---------|------|----------|
| docs-1 | 队长 | P0-5-1（待认领） |
| docs-2 | 成员 | P0-5-2（待认领） |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-02-24 | 重新设计，适配 Claude Code Agent Teams（4 个团队：dev/frontend/testing/docs） |
| 1.0 | 2026-02-24 | 初始版本（4-Agent Team：OpenClaw/OpenCode/Claude Code/Kimi Code） |

---

**团队主管：** 小午 🦁
**创建时间：** 2026-02-24 18:30
**当前版本：** 2.0
