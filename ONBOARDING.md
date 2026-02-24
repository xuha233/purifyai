# Agent Onboarding Guide / Agent 上手指南

Quick start guide for each agent to join a new project.

---

## Quick Start / 快速开始

### Step 1: Read Project Context / 读取项目上下文

```markdown
Read these files in order:
1. PROJECT-IDENTITY.md - What is this project?
2. TEAM-CONFIG.md - Who is on the team?
3. PROJECT-STATUS.md - What is the current status?
4. CURRENT-WORK.md - What is being worked on now?
```

### Step 2: Understand Your Role / 理解你的角色

```markdown
OpenClaw:
- Read your role in TEAM-CONFIG.md
- Coordinate with other agents
- Start by reading all status files

OpenCode:
- Read your role in TEAM-CONFIG.md
- Check CURRENT-WORK.md for current frontend tasks
- Read ARCHITECTURE.md for system design
- Read API-SPEC.md for backend APIs

Claude Code:
- Read your role in TEAM-CONFIG.md
- Check CURRENT-WORK.md for current backend tasks
- Read ARCHITECTURE.md for system design
- Read API-SPEC.md to implement APIs

Kimi Code:
- Read your role in TEAM-CONFIG.md
- Check CURRENT-WORK.md for testing tasks
- Read PROJECT-STATUS.md for quality metrics
- Read TASK-BACKLOG.md for test requirements
```

### Step 3: Start Working / 开始工作

```markdown
Refer to WORKFLOW-PROTOCOL.md for your scenario:
- New project? → Follow Scenario 1
- Ongoing project? → Follow Scenario 2
- Completed project? → Follow Scenario 3
```

---

## Agent-Specific Onboarding / 专属 Agent 上手指南

### OpenClaw Onboarding / OpenClaw 上手

**First Actions / 首要行动：**

1. **Read All Context / 读取所有上下文**
   ```
   PROJECT-IDENTITY.md
   TEAM-CONFIG.md
   PROJECT-STATUS.md
   CURRENT-WORK.md
   TASK-BACKLOG.md
   ```

2. **Assess Project State / 评估项目状态**
   ```
   Check PROJECT-STATUS.md:
   - Is this a new project?
   - Is this ongoing?
   - What's the current phase?
   - Any blockers?

   Check CURRENT-WORK.md:
   - What's each agent working on?
   - Any dependencies?
   - Any handoffs in progress?
   ```

3. **Determine Next Actions / 确定下一步行动**
   ```
   Based on scenario (from WORKFLOW-PROTOCOL.md):
   - New project? → Initialize architecture and tasks
   - Ongoing project? → Continue from where left off
   - Completed project? → Enter maintenance mode
   ```

**Key Responsibilities / 主要职责：**

- [ ] Coordinate between agents
- [ ] Assign tasks and monitor progress
- [ ] Make technical decisions
- [ ] Deploy and validate systems

**Communication Channel / 通信渠道：**

- Receive status updates from OpenCode, Claude Code, Kimi Code
- Send task assignments to agents
- Coordinate handoffs between agents
- Report progress or escalate issues to user

---

### OpenCode Onboarding / OpenCode 上手

**First Actions / 首要行动：**

1. **Read Frontend Context / 读取前端上下文**
   ```
   PROJECT-IDENTITY.md
   TEAM-CONFIG.md (your role)
   ARCHITECTURE.md (frontend components)
   STANDARDS.md (coding standards)
   ```

2. **Check Current Tasks / 检查当前任务**
   ```
   CURRENT-WORK.md:
   - What am I working on now?
   - Are there backend APIs I'm waiting for?

   TASK-BACKLOG.md:
   - What are my assigned tasks?
   - What's the priority?
   ```

3. **Coordinate with Claude Code / 与 Claude Code 协调**
   ```
   Check API-SPEC.md:
   - What APIs are available?
   - What's the endpoint format?

   If APIs are missing:
   - Notify OpenClaw
   - Ask OpenClaw to coordinate with Claude Code
   ```

**Key Responsibilities / 主要职责：**

- [ ] Implement frontend UI and interactions
- [ ] Connect to backend APIs
- [ ] Write unit tests for frontend
- [ ] Follow STANDARDS.md conventions
- [ ] Report progress to OpenClaw

**Communication Channel / 通信渠道：**

- Receive task assignments from OpenClaw
- Request APIs from Claude Code (via OpenClaw)
- Submit completed work to Kimi Code for testing
- Report bugs (fixed or found) to Kimi Code

---

### Claude Code Onboarding / Claude Code 上手

**First Actions / 首要行动：**

1. **Read Backend Context / 读取后端上下文**
   ```
   PROJECT-IDENTITY.md
   TEAM-CONFIG.md (your role)
   ARCHITECTURE.md (backend components)
   STANDARDS.md (coding standards)
   API-SPEC.md (API requirements)
   ```

2. **Check Current Tasks / 检查当前任务**
   ```
   CURRENT-WORK.md:
   - What am I working on now?
   - Are there frontend components waiting for my APIs?

   TASK-BACKLOG.md:
   - What are my assigned tasks?
   - What's the priority?
   ```

3. **Coordinate with OpenCode / 与 OpenCode 协调**
   ```
   Check CURRENT-WORK.md:
   - Which frontend components need my APIs?

   If APIs are needed:
   - Implement required endpoints
   - Update API-SPEC.md
   - Notify OpenClaw of completion
   ```

**Key Responsibilities / 主要职责：**

- [ ] Implement backend APIs
- [ ] Design database schema
- [ ] Write unit tests for backend
- [ ] Follow STANDARDS.md conventions
- [ ] Report progress to OpenClaw

**Communication Channel / 通信渠道：**

- Receive task assignments from OpenClaw
- Implement APIs (based on API-SPEC.md or requests)
- Submit completed work to Kimi Code for testing
- Report bugs (fixed or found) to Kimi Code

---

### Kimi Code Onboarding / Kimi Code 上手

**First Actions / 首要行动：**

1. **Read Quality Context / 读取质量上下文**
   ```
   PROJECT-IDENTITY.md
   TEAM-CONFIG.md (your role)
   STANDARDS.md
   PROJECT-STATUS.md (quality metrics)
   ```

2. **Check Testing Tasks / 检查测试任务**
   ```
   CURRENT-WORK.md:
   - What's being tested now?
   - Any bugs already reported?

   TASK-BACKLOG.md:
   - What testing is required?
   - Are there critical bugs to fix?
   ```

3. **Review Handoffs / 审查交接**
   ```
   Check CURRENT-WORK.md:
   - Are there any tasks ready for testing?
   - Who submitted them? (OpenCode or Claude Code)
   ```

**Key Responsibilities / 主要职责：**

- [ ] Test all completed work
- [ ] Report bugs to responsible agents
- [ ] Maintain test coverage metrics
- [ ] Approve or block deploys
- [ ] Update quality documentation

**Communication Channel / 通信渠道：**

- Receive handoffs from OpenCode and Claude Code
- Report bugs to responsible agents
- Send approval to OpenClaw for deployment
- Provide quality metrics to OpenClaw

---

## Scenario-Based Onboarding / 基于场景的上手

### Scenario 1: New Project / 新项目

**For All Agents / 所有 Agent：**

1. **OpenClaw:**
   - Initialize architecture
   - Create TASK-BACKLOG.md
   - Assign initial tasks

2. **OpenCode & Claude Code:**
   - Wait for task assignments
   - Read ARCHITECTURE.md
   - Start development when assigned

3. **Kimi Code:**
   - Wait for first handoff
   - Prepare test plan
   - Review STANDARDS.md

---

### Scenario 2: Ongoing Project / 进行中的项目

**For All Agents / 所有 Agent：**

1. **OpenClaw:**
   - Read CURRENT-WORK.md
   - Understand what was in progress
   - Continue coordination

2. **OpenCode & Claude Code:**
   - Check CURRENT-WORK.md for their tasks
   - Continue from where left off
   - Resume normal workflow

3. **Kimi Code:**
   - Check PROJECT-STATUS.md for quality metrics
   - Review outstanding bugs
   - Continue testing workflow

---

### Scenario 3: Completed Project / 完成的项目

**For All Agents / 所有 Agent：**

1. **OpenClaw:**
   - Review completed project
   - Enter maintenance mode
   - Handle new issues as they arise

2. **OpenCode & Claude Code:**
   - Be ready for bug fixes
   - Be ready for new feature requests
   - Maintain code quality

3. **Kimi Code:**
   - Monitor for production issues
   - Test bug fixes
   - Update documentation

---

## Communication Best Practices / 通信最佳实践

### Status Updates / 状态更新

```
When: Daily or at milestone completion
Format: To OpenClaw
Content:
- What I completed
- What I'm working on next
- Any blockers or issues
```

### Task Handoffs / 任务交接

```
From: OpenCode/Claude Code
To: Kimi Code
Via: OpenClaw (for verification)
Required Information:
- Task ID
- Changed files
- Test requirements
- Known issues
```

### Bug Reporting / Bug 报告

```
From: Kimi Code
To: OpenCode/Claude Code
Format: Use CONTEXT-BRIDGE.md alert message type
Required Information:
- Bug ID
- Severity
- Steps to reproduce
- Expected vs actual behavior
```

---

## FAQ / 常见问题

### Q: What if I don't have enough context to start?
**A:** Ask OpenClaw. OpenClaw is the context orchestrator.

### Q: What if I'm blocked by another agent?
**A:** Notify OpenClaw. OpenClaw will coordinate and unblock you.

### Q: What's the difference between reporting to OpenClaw vs. directly to other agents?
**A:**
- **To OpenClaw:** For status updates and coordination
- **To other agents:** For specific queries (e.g., "Is API X ready?")

### Q: Can I make technical decisions?
**A:**
- **OpenClaw:** Yes, architectural and project decisions
- **OpenCode/Claude Code:** Yes, implementation decisions (e.g., how to implement a component)
- **Kimi Code:** Yes, quality and testing decisions

### Q: What if I encounter a critical bug?
**A:**
1. Report immediately to OpenClaw
2. OpenClaw prioritizes and assigns
3. If critical, all agents focus on fixing it

---

*Last updated: YYYY-MM-DD*
