# Context Bridge / 上下文桥梁

MCP-like universal interface for project context sharing and agent communication.

---

## Purpose / 目的

Context Bridge provides a standardized interface for exchanging project context and messages between agents and between projects. Similar to MCP (Model Context Protocol), it enables:

- Fast project migration
- Consistent context sharing
- Inter-agent communication
- Status synchronization

---

## Context Schema / 上下文结构

### Project Context Structure / 项目上下文结构

```json
{
  "version": "1.0.0",
  "project_id": "unique-project-id",
  "project_name": "Project Name",
  "scenario": "new|ongoing|completed",
  "last_updated": "YYYY-MM-DDTHH:mm:ssZ",
  "context": {
    "identity": {
      "file": "PROJECT-IDENTITY.md",
      "summary": "Brief one-line project summary",
      "type": "web-app|api|library|tool"
    },
    "team": {
      "file": "TEAM-CONFIG.md",
      "agents": [
        {
          "name": "OpenClaw",
          "role": "Project Manager & Technical Lead",
          "capabilities": [
            "requirements_analysis",
            "architecture_design",
            "task_assignment",
            "deployment"
          ]
        },
        {
          "name": "OpenCode",
          "role": "Frontend Developer",
          "capabilities": [
            "ui_implementation",
            "frontend_logic",
            "api_integration"
          ]
        },
        {
          "name": "Claude Code",
          "role": "Backend Developer",
          "capabilities": [
            "api_implementation",
            "database_design",
            "server_logic"
          ]
        },
        {
          "name": "Kimi Code",
          "role": "QA Engineer",
          "capabilities": [
            "testing",
            "bug_reporting",
            "quality_assurance",
            "documentation"
          ]
        }
      ]
    },
    "tech_stack": {
      "file": "TECH-STACK.md",
      "frontend": ["React", "TypeScript", "Tailwind"],
      "backend": ["Node.js", "Express", "PostgreSQL"],
      "tools": ["Git", "Docker", "GitHub Actions"]
    },
    "architecture": {
      "file": "ARCHITECTURE.md",
      "pattern": "mvc|microservices|serverless",
      "key_components": ["auth", "database", "api", "frontend"]
    },
    "status": {
      "file": "PROJECT-STATUS.md",
      "overall_status": "in_progress|testing|completed",
      "current_phase": "development",
      "percent_complete": 75
    },
    "current_work": {
      "file": "CURRENT-WORK.md",
      "active_tasks": {
        "OpenClaw": ["task_1", "task_2"],
        "OpenCode": ["frontend_task_1"],
        "Claude Code": ["backend_task_1"],
        "Kimi Code": ["testing_task_1"]
      }
    },
    "backlog": {
      "file": "TASK-BACKLOG.md",
      "total_tasks": 25,
      "completed": 15,
      "in_progress": 5,
      "pending": 5
    }
  }
}
```

---

## Message Protocol / 消息协议

### Standard Message Format / 标准消息格式

```json
{
  "version": "1.0",
  "message_id": "msg_XXXXXXXXXXXXXXXX",
  "timestamp": "YYYY-MM-DDTHH:mm:ssZ",
  "sender": "OpenClaw|OpenCode|Claude Code|Kimi Code",
  "recipient": "agent_name|broadcast",
  "message_type": "task|status|query|response|alert",
  "priority": "critical|high|medium|low",
  "content": {
    "subject": "Message subject",
    "body": "Message body",
    "attachments": ["file1.md", "file2.ts"],
    "metadata": {
      "task_id": "TASK-XXX",
      "milestone": "Milestone X",
      "related_bugs": ["BUG-001"]
    }
  }
}
```

### Message Types / 消息类型

| Type | Description | Use Case |
|------|-------------|----------|
| **task** | Task assignment or update | OpenClaw → OpenCode/Claude Code |
| **status** | Status update or report | Any agent → OpenClaw |
| **query** | Request for information | Any agent → Any agent |
| **response** | Response to query | Any agent → Any agent |
| **alert** | Critical issue notification | Kimi Code → All agents |
| **approval** | Approval for handoff or deployment | Kimi Code → OpenClaw |
| **handoff** | Task handoff between agents | OpenCode/Kimi Code, Claude Code/Kimi Code |

---

## Inter-Agent Communication / Agent 间通信

### Task Assignment / 任务分配

**From:** OpenClaw
**To:** OpenCode or Claude Code

```json
{
  "message_type": "task",
  "content": {
    "subject": "Implement User Authentication",
    "task_id": "TASK-015",
    "requirements": [
      "Implement login form",
      "Connect to authentication API",
      "Handle error states"
    ],
    "acceptance_criteria": [
      "User can log in with valid credentials",
      "Error messages are displayed for invalid credentials",
      "Loading state during authentication"
    ],
    "deadline": "YYYY-MM-DD",
    "dependencies": ["TASK-010"]
  }
}
```

### Status Update / 状态更新

**From:** OpenCode or Claude Code
**To:** OpenClaw

```json
{
  "message_type": "status",
  "content": {
    "subject": "Progress Update on TASK-015",
    "task_id": "TASK-015",
    "percent_complete": 60,
    "completed_items": [
      "Login form UI complete",
      "Authentication API integration done"
    ],
    "remaining_items": [
      "Error handling implementation",
      "Loading state implementation"
    ],
    "blockers": [],
    "estimated_completion": "YYYY-MM-DD"
  }
}
```

### Bug Report / Bug 报告

**From:** Kimi Code
**To:** OpenCode or Claude Code

```json
{
  "message_type": "alert",
  "priority": "critical",
  "content": {
    "subject": "CRITICAL BUG: Login fails with valid credentials",
    "bug_id": "BUG-003",
    "severity": "critical",
    "component": "auth/login",
    "steps_to_reproduce": [
      "Navigate to login page",
      "Enter valid email and password",
      "Click login button"
    ],
    "expected_behavior": "User should be logged in",
    "actual_behavior": "Error message: 'Invalid credentials'",
    "environment": {
      "browser": "Chrome 120",
      "testing_session": "session_abc123"
    },
    "attachments": ["screenshots/error.png", "logs/auth.log"]
  }
}
```

### Handoff for Testing / 交接测试

**From:** OpenCode or Claude Code
**To:** Kimi Code

```json
{
  "message_type": "handoff",
  "content": {
    "subject": "TASK-015 ready for testing",
    "task_id": "TASK-015",
    "changed_files": [
      "src/components/LoginForm.tsx",
      "src/api/auth.ts"
    ],
    "test_requirements": [
      "Test with valid credentials",
      "Test with invalid credentials",
      "Test loading state"
    ],
    "notes": "API endpoints are documented in API-SPEC.md"
  }
}
```

---

## Project Migration Protocol / 项目迁移协议

### Export Project Context / 导出项目上下文

**Script:** `context-bridge export`

**Output:** `project-context.json`

**Usage:**

```bash
# Export current project context
context-bridge export

# Export with filter
context-bridge export --include status,currentwork

# Export to specific file
context-bridge export --output /path/to/context.json
```

---

### Import Project Context / 导入项目上下文

**Script:** `context-bridge import`

**Usage:**

```bash
# Import project context and initialize agents
context-bridge import project-context.json

# Import in specific mode (new/ongoing/completed)
context-bridge import project-context.json --mode ongoing

# Import with dry run (preview changes)
context-bridge import project-context.json --dry-run
```

---

### Context Bridging Between Projects / 项目间上下文交接

**Use Case:** Migrating work from one project to another

```json
{
  "source_project": {
    "id": "project-a",
    "context": { /* source context */ }
  },
  "target_project": {
    "id": "project-b",
    "context": { /* updated context */ }
  },
  "migration_notes": [
    "Copied authentication module from Project A",
    "Updated API-SPEC.md for new project requirements",
    "Migrated task backlog (TASK-A001 → TASK-B015)"
  ]
}
```

---

## Integration with OpenClaw / 与 OpenClaw 集成

### OpenClaw Role in Context Bridge / OpenClaw 在上下文桥梁中的角色

1. **Context Orchestrator / 上下文协调者**
   - Maintains project context
   - Coordinates context updates
   - Manages context versioning

2. **Message Hub / 消息中心**
   - Routes messages between agents
   - Prioritizes messages based on urgency
   - Logs all communication

3. **Migration Facilitator / 迁移促进者**
   - Handles project imports/exports
   - Validates context completeness
   - Ensures smooth transitions

---

## Implementation Guide / 实现指南

### For OpenClaw (Implementor) / 给 OpenClaw（实现者）

1. **Initialize Context Bridge / 初始化上下文桥梁**
   ```javascript
   // Initialize with project context
   const bridge = new ContextBridge({
     projectId: "my-project",
     scenario: "new",
     contextFiles: [
       "PROJECT-IDENTITY.md",
       "TEAM-CONFIG.md",
       // ... other files
     ]
   });
   ```

2. **Send Message / 发送消息**
   ```javascript
   bridge.send({
     recipient: "OpenCode",
     messageType: "task",
     content: { /* task details */ }
   });
   ```

3. **Receive Message / 接收消息**
   ```javascript
   bridge.on("message", (msg) => {
     if (msg.sender === "OpenCode" && msg.messageType === "status") {
       // Handle status update
     }
   });
   ```

4. **Export Context / 导出上下文**
   ```javascript
   const context = bridge.exportContext();
   fs.writeFileSync("project-context.json", JSON.stringify(context, null, 2));
   ```

---

### For Other Agents / 给其他 Agent（OpenCode, Claude Code, Kimi Code）

1. **Read Context / 读取上下文**
   ```javascript
   // Read specific context file
   const context = bridge.readContext("PROJECT-IDENTITY.md");
   ```

2. **Report Status / 报告状态**
   ```javascript
   bridge.send({
     recipient: "OpenClaw",
     messageType: "status",
     content: { /* status details */ }
   });
   ```

3. **Query Context / 查询上下文**
   ```javascript
   const techStack = bridge.query("tech_stack");
   ```

---

## Version History / 版本历史

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | YYYY-MM-DD | Initial release |

---

## Future Enhancements / 未来增强

- [ ] Support for event-based messaging (pub/sub)
- [ ] Context diff and delta updates
- [ ] Real-time context synchronization
- [ ] Agent capability discovery
- [ ] Context validation rules

---

*Last updated: YYYY-MM-DD*
