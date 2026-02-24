# Task Backlog / 任务清单

---

## MoSCoW Prioritization / 优先级分类

| Priority | Description | Deadline |
|----------|-------------|----------|
| **Must Have** | MVP 必须的功能，UI 集成和基础测试 | v1.0（2026-02-28） |
| **Should Have** | 重要但非阻塞性的功能，更全面的测试 | v1.1（后续版本） |
| **Could Have** | 锦上添花的功能，高级特性 | 未来版本 |
| **Won't Have** | 不在此版本范围内 | N/A |

---

## Must Have / 必须有（Critical）

### [MH-001] 集成 AgentStatusWidget 到 SmartCleanupPage

**描述：**
将 AgentStatusWidget 集成到 SmartCleanupPage 中，显示智能体的实时状态和工作进度。

**类型：** Frontend（UI）

**分配给：** OpenCode

**状态：** Not Started

**优先级：** Critical

**工作量：** 4 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| AgentAdapter 完成 | MH-000 | Complete |

**验收标准：**

- [ ] 在 SmartCleanupPage 中添加 AgentStatusWidget 组件
- [ ] 实时显示智能体状态（空闲 / 扫描中 / 审查中 / 清理中 / 报告中）
- [ ] 显示当前进度百分比
- [ ] 显示当前任务描述（例如："扫描临时文件..."）
- [ ] 错误状态下显示错误信息

**备注：**
AgentStatusWidget 已经在 src/ui/agent_status_widgets.py 中定义，现在需要集成到主页面中。

---

### [MH-002] 添加智能体模式切换 UI 控件

**描述：**
在 SmartCleanupPage 中添加智能体模式切换控件，用户可以在以下模式之间切换：
- Disabled（传统模式）
- Hybrid（混合模式）
- Full（完全智能体模式）

**类型：** Frontend（UI）

**分配给：** OpenCode

**状态：** Not Started

**优先级：** Critical

**工作量：** 3 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| SmartCleaner.set_agent_mode() | MH-000 | Complete |

**验收标准：**

- [ ] 添加单选按钮组或下拉菜单（模式选择）
- [ ] 用户选择模式后，调用 SmartCleaner.set_agent_mode()
- [ ] 刷新 UI（禁用/启用相关控件）
- [ ] 在配置文件中持久化用户选择（保存到 config.json）
- [ ] 显示当前模式（例如："当前模式：混合模式"）

**备注：**
实现时要保证向后兼容，用户选择 Disabled 时应使用传统系统。

---

### [MH-003] 实现报告查看功能

**描述：**
在 SmartCleanupPage 中添加"查看报告"按钮，点击后弹出查看智能体生成的清理报告。

**类型：** Frontend（UI）

**分配给：** OpenCode

**状态：** Not Started

**优先级：** Critical

**工作量：** 3 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| ReportAgent.generate_report() | MH-000 | Complete |

**验收标准：**

- [ ] 添加"查看报告"按钮
- [ ] 按钮默认禁用，清理完成后启用
- [ ] 点击后弹出对话框（QDialog）
- [ ] 对话框中显示报告内容（包括：扫描项目、清理项目、风险项目、建议）
- [ ] 报告内容格式化展示（表格或列表）

---

### [MH-004] 完整集成测试

**描述：**
对智能体系统与现有 PurifyAI 功能进行完整的集成测试，确保各模块协同工作。

**类型：** Integration Test

**分配给：** Kimi Code

**状态：** Not Started

**优先级：** Critical

**工作量：** 6 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| UI 集成完成 | MH-001, MH-002, MH-003 | TBD |

**验收标准：**

- [ ] 测试传统模式（Disabled）与智能体模式的切换
- [ ] 测试混合模式（Hybrid）：传统扫描 + 智能体审查
- [ ] 测试完全智能体模式（Full）：智能体扫描 + 审查 + 清理 + 报告
- [ ] 测试模拟模式（无 API 密钥时）
- [ ] 测试 API 错误时的回退机制

---

### [MH-005] UI 交互测试

**描述：**
测试 UI 组件的用户交互，包括：
- AgentStatusWidget 的状态更新
- 模式切换控件的功能
- 报告查看功能

**类型：** UI Test

**分配给：** Kimi Code

**状态：** Not Started

**优先级：** High

**工作量：** 4 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| UI 集成完成 | MH-001, MH-002, MH-003 | TBD |

**验收标准：**

- [ ] AgentStatusWidget 状态正确更新（空闲 → 扫描中 → 完成）
- [ ] 模式切换后 UI 响应正确（禁用/启用控件）
- [ ] 报告查看对话框正确显示报告内容
- [ ] 用户操作流畅无卡顿

---

### [MH-006] 实际文件扫描测试

**描述：**
在真实环境中验证扫描和清理功能，确保系统在实际使用中的稳定性和准确性。

**类型：** Manual Test

**分配给：** Kimi Code

**状态：** Not Started

**优先级：** High

**工作量：** 4 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| 集成测试通过 | MH-004 | TBD |

**验收标准：**

- [ ] 测试系统扫描功能（临时文件、预取文件、日志等）
- [ ] 测试浏览器清理功能（Chrome、Edge、Firefox）
- [ ] 测试 AppData 扫描功能（智能风险评估）
- [ ] 测试自定义扫描功能（用户自定义路径）
- [ ] 验证扫描结果的准确性
- [ ] 验证清理的安全性（不误删用户重要文件）

---

## Should Have / 应该有（Important）

### [SH-001] 单元测试（覆盖 4 个智能体）

**描述：**
为 4 个智能体（ScanAgent, ReviewAgent, CleanupAgent, ReportAgent）编写单元测试。

**类型：** Unit Test

**分配给：** Kimi Code

**状态：** Not Started

**优先级：** High

**工作量：** 8 小时

---

### [SH-002] 性能压力测试

**描述：**
验证系统在高负载下的稳定性和性能。

**类型：** Performance Test

**分配给：** Kimi Code

**状态：** Not Started

**优先级：** Medium

**工作量：** 4 小时

---

### [SH-003] pytest 测试套件优化

**描述：**
简化 test_agent_system.py 以适配项目测试框架。

**类型：** Refactoring

**分配给：** OpenCode

**状态：** Not Started

**优先级：** Medium

**工作量：** 2 小时

---

## Could Have / 可以有（Nice-to-have）

### [CH-001] 添加更多智能体工具

**描述：**
扩展智能体工具层，添加更多工具（网络扫描、注册表清理等）。

**类型：** Backend

**分配给：** Claude Code

**状态：** Not Started

**优先级：** Low

**工作量：** 12 小时

---

### [CH-002] 实现智能体学习功能

**描述：**
让智能体根据历史数据学习和优化清理策略。

**类型：** Backend + AI

**分配给：** Claude Code

**状态：** Not Started

**优先级：** Low

**工作量：** 16 小时

---

### [CH-003] 添加历史数据分析和趋势预测

**描述：**
分析用户的历史扫描和清理数据，提供趋势预测和优化建议。

**类型：** Backend + AI

**分配给：** Claude Code

**状态：** Not Started

**优先级：** Low

**工作量：** 12 小时

---

## Bug Backlog / Bug 清单

无已知 Bug。

---

*Last updated: 2026-02-24*
