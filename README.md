# Project Team Kit / 项目团队套件

A complete, context-aware project handoff and agent team collaboration system.

---

## What is This? / 这是什么？

The **Project Team Kit** is a collection of standardized markdown files that:

- ✅ **Quickly onboard** your 4-member AI agent team to any project
- ✅ **Smooth handoffs** between projects (like MCP context transfer)
- ✅ **Standardize workflows** for new, ongoing, and completed projects
- ✅ **Enable cross-project migration** of agents and work

**The 4-Agent Team:**
1. **OpenClaw** - Project Manager & Technical Lead (orchestrates everything)
2. **OpenCode** - Frontend Developer (UI/UX, client-side logic)
3. **Claude Code** - Backend Developer (APIs, database, server logic)
4. **Kimi Code** - QA Engineer (testing, bug reporting, quality assurance)

---

## Quick Start / 快速开始

### For Single Agent → 4-Agent Team Handoff / 单个 Agent 移交给 4 人团队

**Use Case / 使用场景：** You (single agent) have developed part of a project and now need to hand it off to the 4-agent team.

**Recommended Guide / 推荐指南：** Read **HANDOFF-GUIDE.md** first! It provides step-by-step instructions for filling out all handoff documents.

```bash
# 1. Copy the kit to your project
cp -r ~/.openclaw/templates/project-team-kit/* /path/to/project/

# 2. Read HANDOFF-GUIDE.md carefully
# - Contains detailed examples for every field
# - Includes checklists to verify completeness
# - Walks through common scenarios

# 3. Fill in all .md files following the guide
# - PROJECT-IDENTITY.md
# - PROJECT-STATUS.md
# - CURRENT-WORK.md
# - TASK-BACKLOG.md

# 4. Verify with checklists in HANDOFF-GUIDE.md

# 5. Notify OpenClaw to start the handoff
# "OpenClaw, please read all .md files and begin collaboration."
```

---

### For New Project / 新项目

```bash
# 1. Copy the kit to your project root
cp -r ~/.openclaw/templates/project-team-kit/* /path/to/project/

# 2. Fill in PROJECT-IDENTITY.md
# - Project name, description, goals
# - Project type: [x] New Project

# 3. OpenClaw reads all files and initializes

# 4. OpenClaw creates missing files:
#    - ARCHITECTURE.md
#    - API-SPEC.md
#    - TASK-BACKLOG.md

# 5. Start development workflow
```

### For Ongoing Project / 进行中的项目

```bash
# 1. Copy the kit to your existing project
cp -r ~/.openclaw/templates/project-team-kit/* /path/to/project/

# 2. Agent team reads context:
#    - OpenClaw reads all files
#    - OpenCode reads frontend context
#    - Claude Code reads backend context
#    - Kimi Code reads quality context

# 3. Update CURRENT-WORK.md with current state

# 4. Continue workflow from where left off
```

### For Completed Project / 完成的项目

```bash
# 1. Copy the kit to the project
cp -r ~/.openclaw/templates/project-team-kit/* /path/to/project/

# 2. Update PROJECT-IDENTITY.md:
#    - Project type: [x] Completed Project

# 3. Update PROJECT-STATUS.md:
#    - Overall status: "Completed"
#    - Record all milestones

# 4. Agents enter maintenance mode:
#    - OpenClaw handles new issues
#    - OpenCode/Claude Code fix bugs
#    - Kimi Code monitors quality
```

---

## Files Overview / 文件概览

| File | Purpose | Who Reads First |
|------|---------|-----------------|
| **PROJECT-IDENTITY.md** | Project overview, goals, type | All agents |
| **TEAM-CONFIG.md** | Agent roles, responsibilities | All agents |
| **WORKFLOW-PROTOCOL.md** | Scenario-based workflows | All agents |
| **PROJECT-STATUS.md** | Current status, metrics, bugs | OpenClaw (primary), all agents |
| **CURRENT-WORK.md** | What each agent is doing now | All agents (update regularly) |
| **TASK-BACKLOG.md** | All tasks, features, bugs | OpenClaw (assigns), all agents |
| **CONTEXT-BRIDGE.md** | MCP-like messaging protocol | All agents for communication |
| **ONBOARDING.md** | Quick start for each agent | New agents joining |
| **HANDOFF-GUIDE.md** | Detailed guide for manual handoffs | Single agents handing off to team |

**Required Optional Files / 必需的可选文件：**

| File | Purpose | When Created |
|------|---------|--------------|
| **ARCHITECTURE.md** | System architecture | By OpenClaw (new projects) |
| **API-SPEC.md** | API interface definition | By OpenClaw + Claude Code |
| **STANDARDS.md** | Coding conventions | By OpenClaw or existing |
| **TECH-STACK.md** | Technology choices | By OpenClaw (new projects) |

---

## File Reading Order / 文件读取顺序

### For OpenClaw (First to Read / 第一个读取)

```markdown
1. PROJECT-IDENTITY.md
2. TEAM-CONFIG.md
3. PROJECT-STATUS.md
4. CURRENT-WORK.md
5. TASK-BACKLOG.md
6. WORKFLOW-PROTOCOL.md
7. CONTEXT-BRIDGE.md
```

### For OpenCode (Frontend / 前端)

```markdown
1. PROJECT-IDENTITY.md
2. TEAM-CONFIG.md (your role)
3. ARCHITECTURE.md (frontend components)
4. API-SPEC.md (backend APIs)
5. CURRENT-WORK.md (your tasks)
6. STANDARDS.md (coding conventions)
7. ONBOARDING.md (quick start)
```

### For Claude Code (Backend / 后端)

```markdown
1. PROJECT-IDENTITY.md
2. TEAM-CONFIG.md (your role)
3. ARCHITECTURE.md (backend components)
4. API-SPEC.md (API requirements)
5. CURRENT-WORK.md (your tasks)
6. STANDARDS.md (coding conventions)
7. ONBOARDING.md (quick start)
```

### For Kimi Code (QA / 测试)

```markdown
1. PROJECT-IDENTITY.md
2. TEAM-CONFIG.md (your role)
3. PROJECT-STATUS.md (quality metrics)
4. CURRENT-WORK.md (testing tasks)
5. TASK-BACKLOG.md (bugs to fix)
6. ONBOARDING.md (quick start)
```

---

## Workflow Scenarios / 工作流场景

### Scenario 1: New Project / 新项目

Follow `WORKFLOW-PROTOCOL.md` → "Scenario 1: New Project"

**Phases:**
1. Initialization (OpenClaw creates architecture, tasks)
2. Parallel Development (OpenCode + Claude Code work together)
3. Integration Testing (Kimi Code tests)
4. Deployment (OpenClaw integrates and deploys)

---

### Scenario 2: Ongoing Project / 进行中的项目

Follow `WORKFLOW-PROTOCOL.md` → "Scenario 2: Ongoing Project"

**Phases:**
1. Context Gathering (agents read existing files)
2. Continue Development (resume from where left off)
3. Stabilization (Kimi Code tests legacy bugs)

---

### Scenario 3: Completed Project / 完成的项目

Follow `WORKFLOW-PROTOCOL.md` → "Scenario 3: Completed Project"

**Phases:**
1. Maintenance Mode (handle issues)
2. Iteration (plan new features)

---

## Context Bridge (MCP-like Interface) / 上下文桥梁

The `CONTEXT-BRIDGE.md` file provides a standardized interface for:

- **Project migration** (export/import context)
- **Inter-agent messaging** (standard message format)
- **Status synchronization** (real-time context updates)

**Example message:**

```json
{
  "sender": "OpenClaw",
  "recipient": "OpenCode",
  "message_type": "task",
  "content": {
    "task_id": "TASK-015",
    "requirements": ["Implement login form"],
    "deadline": "2026-03-01"
  }
}
```

See `CONTEXT-BRIDGE.md` for full protocol details.

---

## Example Usage / 使用示例

### Example 1: Start a New Web App Project / 开始一个新 Web 应用项目

```markdown
# Step 1: Copy kit to project
cp -r ~/.openclaw/templates/project-team-kit/* ~/projects/my-webapp/

# Step 2: Edit PROJECT-IDENTITY.md
Project Name: My Awesome E-commerce App
Description: A modern e-commerce platform
Goals:
  - User authentication
  - Product catalog
  - Shopping cart
  - Payment integration
Type: [x] New Project

# Step 3: OpenClaw reads files and creates:
- ARCHITECTURE.md (client-server architecture)
- API-SPEC.md (auth, products, cart, payment APIs)
- TASK-BACKLOG.md (breakdown into tasks)
- STANDARDS.md (React + TypeScript + Node.js conventions)
```

---

### Example 2: Handoff Between Agents / Agent 间交接

```markdown
# OpenCode completes login form
# OpenCode sends message via CONTEXT-BRIDGE:
{
  "sender": "OpenCode",
  "recipient": "Kimi Code",
  "message_type": "handoff",
  "content": {
    "task_id": "TASK-015",
    "changed_files": ["src/components/Login.tsx"],
    "test_requirements": ["Test valid credentials", "Test error handling"]
  }
}

# Kimi Code receives, tests, and reports results
```

---

### Example 3: Project Migration (MCP Context Transfer) / 项目迁移

```bash
# Export context from Project A
context-bridge export --project ~/projects/project-a/ > project-a-context.json

# Import to Project B
context-bridge import --input project-a-context.json --project ~/projects/project-b/

# Agents now understand Project B's context and can continue work instantly
```

---

## Workflow Diagram / 工作流图

```
New Project Start
    ↓
OpenClaw initializes (reads PROJECT-IDENTITY.md)
    ↓
OpenClaw creates ARCHITECTURE.md, API-SPEC.md, TASK-BACKLOG.md
    ↓
OpenClaw assigns tasks
    ↓
[Parallel]
    ├─ OpenCode (frontend) → IMPLEMENT
    └─ Claude Code (backend) → IMPLEMENT
        ↓
    OpenClaw coordinates
        ↓
Frontend + Backend Ready
    ↓
Handoff to Kimi Code (via CONTEXT-BRIDGE)
    ↓
Kimi Code Tests
    ↓
If Bugs → Report → Fix → Re-Test (loop)
    ↓
If Clean → Approve → OpenClaw
    ↓
OpenClaw Deploys
    ↓
Project Complete
```

---

## Best Practices / 最佳实践

### For OpenClaw (Project Manager) / 给 OpenClaw

1. **Always read context first / 先读取上下文**
   - Read all relevant .md files before making decisions

2. **Coordinate before assigning / 分配前协调**
   - Check dependencies before assigning tasks
   - Ensure agents have what they need

3. **Regular syncs / 定期同步**
   - Initiate daily or per-milestone status updates

4. **Balance work / 平衡工作**
   - Monitor OpenCode and Claude Code progress
   - Prevent burnout or bottlenecks

---

### For OpenCode & Claude Code (Developers) / 给开发者

1. **Read specs first / 先阅读规范**
   - Read ARCHITECTURE.md and API-SPEC.md before starting

2. **Report blockers / 报告阻塞**
   - Notify OpenClaw if you're blocked

3. **Write tests / 编写测试**
   - Unit tests before handoff to Kimi Code

4. **Follow standards / 遵循标准**
   - Read and follow STANDARDS.md

---

### For Kimi Code (QA) / 给测试工程师

1. **Test thoroughly / 彻底测试**
   - Don't skip edge cases

2. **Report clearly / 清晰报告**
   - Use CONTEXT-BRIDGE message format for bug reports

3. **Prioritize bugs / 优先级排序**
   - Critical bugs get immediate attention

4. **Document quality / 记录质量**
   - Update quality metrics in PROJECT-STATUS.md

---

## Customization / 自定义

### Add Your Own Files / 添加自定义文件

You can add files to the kit based on your needs:

- `MEETING_NOTES.md` - Meeting summaries and decisions
- `API-MIGRATION.md` - API change log
- `PERFORMANCE-REPORT.md` - Performance optimization notes
- `SECURITY-REPORT.md` - Security audits

Just have agents read them in the appropriate order.

---

## Version History / 版本历史

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-24 | Initial release |

---

## Contributing / 贡献

To improve this kit:

1. Update or add new .md files
2. Test with your project workflows
3. Share with the community
4. Document lessons learned

---

## Credits / 致谢

**Author:** 言午间

**Design Philosophy:** Standardized, context-aware, MCP-like interface for seamless agent team collaboration across projects.

---

## Support / 支持

- **Documentation:** All .md files in this kit
- **Handoff Guide:** HANDOFF-GUIDE.md ⭐ (detailed guide for single-agent → team handoff)
- **Onboarding Guide:** ONBOARDING.md (quick start for agents)
- **Context Bridge:** CONTEXT-BRIDGE.md (messaging protocol)
- **Workflow Protocols:** WORKFLOW-PROTOCOL.md (scenario-based workflows)

---

**🚀 Quick Start:** Copy to your project and read `PROJECT-IDENTITY.md`!

---

*Last updated: 2026-02-24*
