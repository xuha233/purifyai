================================================================================
【Step 1】团队创建提示（复制这段到 Claude Code）
================================================================================

我需要为 PurifyAI v1.0 项目搭建 Agent Teams，请创建以下团队：

团队 dev（dev）
- 队友数量：3 名
- 专长：后端 Python 开发、智能推荐算法、清理编排逻辑
- 可修改文件：src/agent/, src/core/
- 禁止修改：src/ui/, tests/, project-team-kit/

团队 frontend（frontend）
- 队友数量：3 名
- 专长：PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
- 可修改文件：src/ui/
- 可读文件（了解接口）：src/agent/, src/core/
- 禁止修改：src/agent/, src/core/, tests/, project-team-kit/

团队 testing（testing）
- 队友数量：2 名
- 专长：单元测试、集成测试、边界条件测试
- 可修改文件：tests/
- 可读文件（了解接口）：src/agent/, src/core/, src/ui/
- 禁止修改：src/, project-team-kit/

团队 docs（docs）
- 队友数量：2 名
- 专长：任务文件编写、开发文档维护、迭代计划更新
- 可修改文件：project-team-kit/
- 可读文件（了解接口）：src/agent/, src/core/, src/ui/, tests/
- 禁止修改：src/, tests/

当前项目信息：
- 项目路径：G:/docker/diskclean
- 分支：feature/v1.0-refactor
- 开发进度报告：project-team-kit/DEV-PROGRESS-REPORT-v1.0.md
- 交接协议：project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

请设置为 Delegate 模式，我只负责协调和任务分配，不直接写代码。

================================================================================
