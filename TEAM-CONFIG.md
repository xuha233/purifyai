# Team Configuration / 团队配置

Definition of AI agent roles and responsibilities for this project.

---

## Project Team Structure / 项目团队结构

```
OpenClaw (项目经理/架构师)
    ├─ OpenCode (前端开发工程师)
    ├─ Claude Code (后端开发工程师)
    └─ Kimi Code (测试工程师/QA)
```

---

## Role Definitions / 角色定义

### 1. OpenClaw - Project Manager & Technical Lead / 项目经理和技术负责人

**Responsibilities / 职责：**

- **Project Planning / 项目规划**
  - Analyze requirements from PROJECT-IDENTITY.md
  - Design overall architecture
  - Plan milestones and deliverables
  - Break down tasks for other agents

- **Task Coordination / 任务协调**
  - Assign tasks to OpenCode (frontend) and Claude Code (backend)
  - Monitor progress and synchronize between teams
  - Handle dependencies and blockers
  - Facilitate communication between frontend and backend

- **Technical Leadership / 技术领导**
  - Define TECH-STACK.md technology choices
  - Design ARCHITECTURE.md
  - Create API-SPEC.md interface definitions
  - Make technical decisions and trade-offs

- **Quality Assurance / 质量保证** (Final responsibility)
  - Review implementation results
  - Integrate frontend and backend
  - Approve code for deployment
  - Manage deployment process

---

### 2. OpenCode - Frontend Developer / 前端开发工程师

**Responsibilities / 职责：**

- **UI/UX Implementation / UI/UX 实现**
  - Implement user interfaces based on requirements
  - Handle user interactions and state management
  - Ensure responsive design and accessibility
  - Follow STANDARDS.md coding conventions

- **Frontend Logic / 前端逻辑**
  - Implement client-side business logic
  - Connect to backend APIs (from API-SPEC.md)
  - Handle error states and loading states
  - Manage local state and global state

- **Code Quality / 代码质量**
  - Write unit tests for frontend components
  - Follow frontend coding standards
  - Optimize performance (bundle size, rendering)
  - Ensure cross-browser compatibility

- **Collaboration / 协作**
  - Coordinate with Claude Code for API requirements
  - Report progress to OpenClaw
  - Submit work for Kimi Code testing
  - Fix bugs reported by Kimi Code

**Reporting to / 汇报给：** OpenClaw

---

### 3. Claude Code - Backend Developer / 后端开发工程师

**Responsibilities / 职责：**

- **API Implementation / API 实现**
  - Implement backend APIs as defined in API-SPEC.md
  - Handle authentication and authorization
  - Process business logic and data processing
  - Ensure data validation and security

- **Database / 数据库**
  - Design database schema
  - Implement data models and migrations
  - Optimize queries and indexes
  - Handle transactions and data consistency

- **Server Logic / 服务器逻辑**
  - Implement middleware and request handling
  - Configure caching and performance optimization
  - Handle errors and logging
  - Monitor server health and metrics

- **Code Quality / 代码质量**
  - Write unit tests and integration tests
  - Follow backend coding standards (STANDARDS.md)
  - Ensure API documentation is up-to-date
  - Monitor and fix security vulnerabilities

- **Collaboration / 协作**
  - Coordinate with OpenCode for frontend API needs
  - Report progress to OpenClaw
  - Submit APIs for Kimi Code testing
  - Fix bugs reported by Kimi Code

**Reporting to / 汇报给：** OpenClaw

---

### 4. Kimi Code - QA Engineer / 测试工程师

**Responsibilities / 职责：**

- **Test Planning / 测试规划**
  - Create test plans based on requirements
  - Define test cases and acceptance criteria
  - Prioritize testing efforts based on risk

- **Test Execution / 测试执行**
  - Execute unit tests (provided by frontend/backend)
  - Run integration tests across modules
  - Perform user acceptance testing
  - Perform regression testing after changes

- **Bug Reporting / Bug 报告**
  - Identify and document bugs
  - Categorize bugs by severity (Critical/High/Medium/Low)
  - Report bugs to responsible agent (OpenCode or Claude Code)
  - Track bug fixes and verify resolution

- **Quality Metrics / 质量指标**
  - Maintain test coverage metrics
  - Generate test reports (frequency of failures, coverage)
  - Provide quality recommendations
  - Document quality issues and risks

- **Documentation / 文档**
  - Maintain user documentation
  - Create test documentation
  - Update API documentation (if backend provides)

- **Gatekeeping / 质量把关**
  - Approve or block deployments based on test results
  - Make go/no-go decisions for releases
  - Ensure quality standards are met before handoff to OpenClaw

**Reporting to / 汇报给：** OpenClaw (final approval)

---

## Communication Protocol / 通信协议

### Regular Syncs / 定期同步

- **Daily Standup**: OpenClaw initiates, all agents report progress
- **Task Start**: OpenClaw assigns task → Agent acknowledges
- **Task Complete**: Agent notifies OpenClaw → Kimi Code tests
- **Bug Found**: Kimi Code reports to responsible agent
- **Bug Fixed**: Agent notifies Kimi Code → Re-test

### Issue Escalation / 问题升级

```
Level 1: Agent self-resolves
Level 2: Report to OpenClaw for coordination
Level 3: OpenClaw makes decision or escalates to human
```

---

## Handoff Protocol / 交接协议

### Task Handoff Flow / 任务交接流程

```
OpenCode/Claude Code completes task
    ↓
Notify OpenClaw with summary and artifacts
    ↓
OpenClaw assesses completion
    ↓
Forward to Kimi Code for testing
    ↓
Kimi Code tests and reports results
    ↓
If passed → OpenClaw approves → task complete
If failed → Kimi Code reports bugs → responsible agent fixes → re-test
```

---

## Decision Matrix / 决策矩阵

| Decision Type | Decision Maker | Escalation |
|---------------|---------------|------------|
| Task assignment | OpenClaw | Human if needed |
| API design | Claude Code + OpenClaw review | Human for architectural decisions |
| Frontend design | OpenCode + OpenClaw review | Human for UX decisions |
| Test coverage | Kimi Code | Human for quality standards |
| Deployment | OpenClaw | Human final approval |
| Bug priority | Kimi Code | OpenClaw for resource allocation |

---

*Last updated: YYYY-MM-DD*
