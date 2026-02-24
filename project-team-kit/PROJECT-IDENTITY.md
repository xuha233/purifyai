# Project Identity / 项目的身份

---

## Project Name / 项目名称

PurifyAI - 智能磁盘清理工具

## Description / 项目描述

基于 PyQt5 开发的 Windows 系统清理工具，集成 AI 智能评估功能。

**主要功能：**
- 系统扫描：扫描临时文件、预取文件、日志等
- 浏览器清理：支持 Chrome、Edge、Firefox
- AppData 扫描：智能风险评估的 AppData 数据扫描
- 自定义扫描：用户自定义路径扫描
- AppData 迁移：大型文件夹迁移工具（Demo版本）
- 系统托盘：后台运行和快速清理
- 自动清理：定时清理和磁盘空间阈值触发
- 回收功能：可选的自定义回收站

**核心特性：**
- 集成 OpenCode 风格的智能体系统（Agent System）
- 支持 3 种运行模式：传统模式 / 混合模式 / 完全智能体模式
- 完整的扫描-审查-清理-报告工作流
- AI 智能评估（需配置 API 密钥）
- 模拟模式：无 API 密钥时自动使用预设响应

## Project Goals / 项目目标

**短期目标（当前版本）：**
- 完成智能体系统的核心实现 ✅
- 完成与现有 SmartCleaner 的适配器集成 ✅
- 通过核心功能测试 ✅
- ~~完成 UI 组件集成待办
- ~~添加用户模式切换 UI 控件
- ~~实现报告查看功能

**中期目标：**
- 完整的 UI 集成和用户体验优化
- 更稳健的错误处理和回退机制
- 更全面的集成测试和单元测试

**长期目标：**
- 添加更多智能体工具（网络扫描、注册表清理等）
- 实现智能体学习功能
- 添加历史数据分析和趋势预测

## Project Type / 项目类型

- [ ] New Project (新项目 - 从零开始)
- [x] Ongoing Project (进行中的项目 - 接手现有项目)
- [ ] Completed Project (完成的项目 - 维护/迭代)

## Created Date / 创建日期

2026-02-21

## Status / 项目状态

| Field | Value |
|-------|-------|
| Status | In Progress |
| Version | v1.0 |
| Last Updated | 2026-02-24 |

## Stakeholders / 利益相关者

| Role | Name/Role |
|------|-----------|
| Product Manager | 言午间（个人项目） |
| Tech Lead | 言午间 |
| Frontend Lead | 待分配（OpenCode） |
| Backend Lead | 言午间 → 待交接给 Claude Code |
| QA Lead | 待分配（Kimi Code） |

## Key Requirements / 关键需求

### 1. 智能体系统必需功能
- 4 个智能体（扫描 / 审查 / 清理 / 报告）正常工作，并能够执行各自的任务。需要完成智能体编排器（AgentOrchestrator）的协调与控制。
- 工具层：Read / Write / Edit / Glob / Grep 文件系统工具正常工作，为智能体提供服务。
- Adapter 模式：AgentAdapter 兼容 SmartCleaner 接口，确保前后端无缝集成。
- 3 种运行模式：禁止使用传统模式（Disabled）/ 混合模式（Hybrid）/ 完全智能体模式（Full）。

### 2. UI 集成必需功能
- AgentStatusWidget：状态显示组件，实时反馈智能体和工作进度。
- 智能体模式切换 UI 控件：用户可以在传统模式 / 混合模式 / 完全智能体模式之间切换。
- 报告查看功能：查看智能体生成的清理报告。

### 3. 测试必需功能
- 集成测试：与现有 PurifyAI 功能的完整集成测试。
- UI 组件交互测试：状态组件和模式切换控件的测试。
- 实际文件扫描测试：在真实环境中验证扫描和清理功能。
- 性能压力测试：验证系统在高负载下的稳定性。

### 4. 兼容性需求
- 向后兼容：所有传统功能保持不变，智能体为可选扩展。
- 自动回退：当智能体不可用时自动使用传统系统。
- 接口统一：AgentAdapter 保持与 ScannerAdapter 相同的信号接口。

## Technical Constraints / 技术约束

### 环境要求
- Python 3.14+
- Windows 7/8/10/11
- PyQt5

### 开发工具
- 智能体编排器和工具层已使用 Python 编写。
  后续 UI 集成使用 OpenCode（PyQt5）。
  后端完善和 Bug 修复使用 Claude Code。
  测试使用 Kimi Code（但需手动粘贴指令）。

### API 要求
- AI 功能需配置 Anthropic API 密钥（Claude Opus 4.6 或以上版本）。
- 如果没有 API 密钥，系统自动进入模拟模式。

### 兼容性要求
- Python 3.x（测试已通过）
- PyQt5（测试已通过）
- 数据库模块（测试已通过）
- 现有 SmartCleaner（测试已通过）

### 性能要求
- API 响应时间（如使用真实 API）：目标 < 2 秒
- 文件扫描速度：保持与传统系统同等水平
- 用户体验：模式切换和状态更新应流畅

### 安全要求
- 用户数据隐私：扫描和清理过程中不应泄露用户隐私
- 错误处理：智能体误判时的安全保障和用户确认机制
- 数据备份：可选的回收站机制防止误删

## Next Steps / 下一步行动

### 优先级高（P0）
1. [ ] 集成 AgentStatusWidget 到 SmartCleanupPage
2. [ ] 添加智能体模式切换 UI 控件
3. [ ] 实现报告查看功能

### 优先级中（P1）
4. [ ] 编写单元测试（覆盖 4 个智能体）
5. [ ] 验证与现有功能的兼容性（完整的集成测试）
6. [ ] UI 组件交互测试

### 优先级低（P2）
7. [ ] 性能压力测试
8. [ ] 添加更多智能体工具（网络扫描、注册表清理等）
9. [ ] 实现智能体学习功能

---

*Last updated: 2026-02-24*
