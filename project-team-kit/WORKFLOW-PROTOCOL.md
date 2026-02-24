# Workflow Protocol / 协作流程协议

Standardized workflow for different project scenarios.

---

## Scenario-Based Workflows / 基于场景的工作流

This document provides workflows for three scenarios:
- New Project (新项目)
- Ongoing Project (进行中的项目)
- Completed Project (完成的项目)

---

## Scenario 1: New Project / 新项目

**When / 使用时机：** Starting a project from scratch

### Phase 1: Initialization / 初始化阶段

**Owner:** OpenClaw

**Steps:**

1. **Read Project Context**
   ```
   Read PROJECT-IDENTITY.md
   Read TECH-STACK.md (if exists)
   Read STANDARDS.md (if exists)
   ```

2. **Define Architecture**
   ```
   Create ARCHITECTURE.md:
   - System architecture diagram
   - Module breakdown
   - Data flow
   - Tech stack choices (if not in TECH-STACK.md)
   ```

3. **Define API Interface**
   ```
   Create API-SPEC.md:
   - API endpoints list
   - Request/response schema
   - Authentication requirements
   ```

4. **Plan Milestones**
   ```
   Create TASK-BACKLOG.md:
   - Break down features into tasks
   - Prioritize tasks (MoSCoW: Must/Should/Could/Won't)
   - Estimate effort
   - Define dependencies
   ```

5. **Assign Initial Tasks**
   ```
   - Assign backend tasks to Claude Code
   - Assign frontend tasks to OpenCode
   - Define deliverables and deadlines
   ```

**Deliverable / 交付物：**
- ARCHITECTURE.md created
- API-SPEC.md created
- TASK-BACKLOG.md created
- Initial tasks assigned

---

### Phase 2: Parallel Development / 并行开发阶段

**Owners:** OpenCode (frontend) + Claude Code (backend)

**Sync Mechanism:** OpenClaw coordinates

**Workflow:**

```
OpenClaw assigns tasks
    ↓
[Parallel Execution]
    ├─ OpenCode (frontend):
    │   - Implements UI components
    │   - Connects to backend APIs
    │   - Reports progress to OpenClaw
    │
    ├─ Claude Code (backend):
    │   - Implements APIs
    │   - Creates database schema
    │   - Reports progress to OpenClaw
    │
    └─ OpenClaw:
        - Monitors progress
        - Coordinates API requirements
        - Resolves blockers
```

**Deliverable / 交付物：**
- Frontend code commits
- Backend API implementations
- Regular progress reports

---

### Phase 3: Integration Testing / 集成测试阶段

**Owner:** Kimi Code

**Workflow:**

```
Frontend & Backend ready for integration
    ↓
Notify OpenClaw
    ↓
OpenClaw forwards to Kimi Code
    ↓
Kimi Code performs:
    - Unit tests (from frontend/backend)
    - Integration tests
    - User acceptance tests
    - Performance tests
    ↓
Kimi Code reports results
    ↓
If failed:
    - Report bugs to responsible agent
    - Agent fixes → re-test
    - Loop until pass
    ↓
If passed:
    - Kimi Code approves
    - Notify OpenClaw
    ↓
OpenClaw integrates and validates
```

**Deliverable / 交付物：**
- Test report
- Bug list (if any)
- Quality metrics (coverage, pass rate)

---

### Phase 4: Deployment / 部署阶段

**Owner:** OpenClaw

**Workflow:**

```
Kimi Code approves testing
    ↓
OpenClaw reviews code
    ↓
OpenClaw creates deployment plan
    ↓
OpenClaw executes deployment
    ↓
OpenClaw validates deployment
    ↓
OpenClaw updates PROJECT-STATUS.md
```

**Deliverable / 交付物：**
- Deployed system
- Deployment documentation
- Updated PROJECT-STATUS.md

---

## Scenario 2: Ongoing Project / 进行中的项目

**When / 使用时机：** Taking over an existing project

### Phase 1: Context Gathering / 上下文收集

**Owner:** OpenClaw

**Steps:**

1. **Read Existing Documentation**
   ```
   Read all .md files in project
   - PROJECT-IDENTITY.md (project overview)
   - ARCHITECTURE.md (system design)
   - API-SPEC.md (interface definitions)
   - TASK-BACKLOG.md (pending tasks)
   - CURRENT-WORK.md (what's being worked on)
   - STANDARDS.md (coding standards)
   - TECH-STACK.md (technology choices)
   ```

2. **Understand Current Status**
   ```
   Read PROJECT-STATUS.md:
   - Current stage
   - Completed features
   - Pending issues
   - blockers
   ```

3. **Analyze Codebase**
   ```
   - Review existing code structure
   - Identify patterns and conventions
   - Understand dependencies
   - Identify technical debt
   ```

4. **Create Handoff Summary**
   ```
   Update CURRENT-WORK.md:
   - What's completed
   - What's in progress
   - What needs attention
   - Roadmap for next steps
   ```

**Deliverable / 交付物：**
- Context understanding
- CURRENT-WORK.md updated
- Risk assessment

---

### Phase 2: Continue Development / 继续开发

**Owners:** OpenCode + Claude Code (based on work from CURRENT-WORK.md)

**Workflow:**

```
OpenClaw reviews CURRENT-WORK.md
    ↓
Pick up where previous team left off
    ↓
Continue standard development workflow (from Scenario 1 Phase 2)
```

**Deliverable / 交付物：**
- Continue feature development
- Fix bugs from bug backlog
- Update CURRENT-WORK.md regularly

---

### Phase 3: Stabilization / 稳定化阶段

**Owner:** Kimi Code

**Workflow:**

```
Integration testing (same as Scenario 1 Phase 3)
    ↓
Kimi Code identifies legacy bugs
    ↓
Report to responsible agent
    ↓
Fix cycles → re-test
    ↓
Deploy when stable
```

**Deliverable / 交付物：**
- Bug reports fixed
- System stable
- Ready for production

---

## Scenario 3: Completed Project / 完成的项目

**When / 使用时机：** Maintaining or iterating on a completed project

### Phase 1: Maintenance Mode / 维护模式

**Owners:** All agents (as needed)

**Workflow:**

```
New issue or feature request
    ↓
OpenClaw prioritizes
    ↓
Assign to appropriate agent:
    - Bug fix → OpenCode/Claude Code
    - New feature → OpenClaw plans → assign
    - Documentation → Kimi Code
    ↓
Implement → Test → Deploy
```

**Deliverable / 交付物：**
- Issues resolved
- Features added
- Documentation updated

---

### Phase 2: Iteration / 迭代开发

**Owner:** OpenClaw

**Workflow:**

```
OpenClaw reviews completed project
    ↓
Plan iteration (new features, refactoring)
    ↓
Create new milestone in TASK-BACKLOG.md
    ↓
Execute standard development workflow (from Scenario 1)
```

**Deliverable / 交付物：**
- New features released
- Code refactored
- Performance improved

---

## General Workflow Standards / 通用工作流标准

### Daily Sync / 每日同步

```
Initiated by: OpenClaw
Frequency: Daily (or per milestone)
Format:
  1. What did you complete today?
  2. What will you work on tomorrow?
  3. Any blockers?
```

### Task Acceptance Criteria / 任务验收标准

```
Before handing off to Kimi Code:
- Code is self-tested (unit tests)
- Code follows STANDARDS.md
- Documentation is updated (if needed)
- No obvious bugs or issues
```

### Quality Gate / 质量把关标准

```
Before deployment (OpenClaw approval):
- All tests pass (from Kimi Code)
- No known critical bugs
- Code reviewed (manual or automated)
- Documentation updated
```

---

## Emergency Workflow / 紧急工作流

### Critical Bug / 关键 Bug

```
Kimi Code reports critical bug
    ↓
Notify OpenClaw immediately
    ↓
OpenClaw assigns hotfix
    ↓
Responsible (OpenCode/Claude Code) fixes
    ↓
Kimi Code tests hotfix
    ↓
OpenClaw deploys hotfix immediately
```

### Production Down / 生产环境故障

```
Alert received
    ↓
OpenClaw triggers emergency protocol
    ↓
All agents prioritize this issue
    ↓
Fix → Test → Deploy (minimal approval process)
```

---

*Last updated: YYYY-MM-DD*
