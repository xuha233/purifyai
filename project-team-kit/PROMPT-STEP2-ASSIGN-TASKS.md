================================================================================
【Step 2】任务分配提示（复制这段到 Claude Code）
================================================================================

首先，请所有队员阅读交接协议：
cat project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

然后，请开始认领以下任务（优先级：P0-4 > P0-5）：

### P0-4-1: 实现 last_cleanup_files.json 存储
- 团队：dev
- 负责人：dev-1
- 优先级：高
- 预计时间：0.5 小时

任务描述：

实现两个方法：

1. SmartRecommender.load_last_cleanup_files()
   - 从 data/last_cleanup_files.json 读取上次清理的文件列表
   - 如果文件不存在，返回空列表
   - 返回 List[str]

2. SmartRecommender.save_last_cleanup_files(files)
   - 将当前清理的文件列表保存到 data/last_cleanup_files.json
   - 参数: files: List[str]
   - 无返回值

文件路径检查：
- src/agent/smart_recommender.py

### P0-4-2: 完善增量清理推荐逻辑
- 团队：dev
- 负责人：dev-2
- 优先级：高
- 预计时间：0.5 小时
- 依赖任务：P0-4-1

任务描述：

完善 SmartRecommender.recommend_incremental() 方法：

1. 加载上次清理的文件列表（调用 load_last_cleanup_files()）
2. 对比当前扫描结果和上次清理文件
3. 过滤出新文件（last_cleanup_files.json 中不存在的文件）
4. 返回只包含新文件的 CleanupPlan

文件路径检查：
- src/agent/smart_recommender.py

需要处理边界情况：
- last_cleanup_files.json 不存在（全部文件都是新文件）
- 某些上次清理的文件已删除（忽略这些文件）

注意：此任务依赖 P0-4-1 完成

### P0-4-3: agent_hub_page.py 添加增量清理按钮
- 团队：frontend
- 负责人：frontend-1
- 优先级：高
- 预计时间：0.5 小时

任务描述：

在 AgentHubPage 中添加"增量清理"按钮：

1. 在界面顶部或工具栏添加"增量清理"按钮
2. 按钮点击时调用 recommend_incremental() 获取增量清理推荐
3. 显示增量清理的文件列表
4. 集成到现有的清理流程中

文件路径检查：
- src/ui/agent_hub_page.py

参考：
- 现有的"一键清理"按钮实现
- CleanupPreviewCard 和 CleanupProgressWidget 的使用

### P0-4-4: 增量清理预览 UI 集成
- 团队：frontend
- 负责人：frontend-2
- 优先级：高
- 预计时间：0.5 小时
- 依赖任务：P0-4-3

任务描述：

将增量清理功能集成到现有的 UI 组件中：

1. 更新 CleanupPreviewCard，显示增量清理的统计信息
2. 更新 CleanupProgressWidget，处理增量清理完成后的逻辑
3. 确保增量清理完成后调用 save_last_cleanup_files() 保存文件列表

文件路径检查：
- src/ui/cleanup_preview_card.py
- src/ui/cleanup_progress_widget.py

需要集成：
- SmartRecommender.recommend_incremental()
- CleanupOrchestrator.execute_incremental_cleanup()
- CleanupOrchestrator 完成后保存文件列表

注意：此任务依赖 P0-4-3 完成

### P0-4-5: 单元测试和集成测试
- 团队：testing
- 负责人：testing-1
- 优先级：高
- 预计时间：1.0 小时
- 依赖任务：P0-4-1, P0-4-2, P0-4-3, P0-4-4

任务描述：

为增量清理功能编写测试：

1. 单元测试
   - 测试 load_last_cleanup_files() 方法
   - 测试 save_last_cleanup_files() 方法
   - 测试 recommend_incremental() 方法
   - 测试边界条件（文件不存在、文件已删除等）

2. 集成测试
   - 测试完整的增量清理流程
   - 测试 UI 按钮点击和响应
   - 测试文件列表保存和加载

测试文件路径：
- tests/unit/test_smart_recommender.py
- tests/integration/test_incremental_cleanup.py
- tests/ui/test_incremental_cleanup_ui.py

注意：此任务依赖 P0-4-1, P0-4-2, P0-4-3, P0-4-4 完成

---

### P0-5-1: 分析 AgentHubPage 结构
- 团队：docs
- 负责人：docs-1
- 优先级：中
- 预计时间：0.5 小时

任务描述：

分析现有的 AgentHubPage 结构：

1. 阅读 src/ui/agent_hub_page.py
2. 分析布局结构（哪些组件，如何组织）
3. 识别可简化的部分
4. 提出重新设计方案

输出：
- AgentHubPage 结构分析文档
- 可简化的组件列表
- 新布局设计方案

文件路径：
- project-team-kit/P0-AGENT-HUB-ANALYSIS.md（新建）

### P0-5-2: 设计新的页面布局
- 团队：docs
- 负责人：docs-2
- 优先级：中
- 预计时间：0.5 小时
- 依赖任务：P0-5-1

任务描述：

设计新的 AgentHubPage 布局：

1. 基于分析结果（P0-5-1），设计新布局
2. 确定选项卡精简方案（保留哪些，删除哪些）
3. 设计导航栏优化方案
4. 绘制 UI 布局图（可以使用文字描述）

输出：
- 新布局设计方案
- 选项卡精简列表
- 导航栏优化方案

文件路径：
- project-team-kit/P0-AGENT-HUB-LAYOUT-DESIGN.md（新建）

注意：此任务依赖 P0-5-1 完成

### P0-5-3: 重构 AgentHubPage 主布局
- 团队：frontend
- 负责人：frontend-3
- 优先级：中
- 预计时间：1.5 小时
- 依赖任务：P0-5-2

任务描述：

重构 AgentHubPage 的主布局：

1. 按照新布局方案（P0-5-2）重构布局
2. 优化组件排列和间距
3. 确保视觉层次清晰

文件路径：
- src/ui/agent_hub_page.py

注意事项：
- 保持核心功能不变
- 确保性能不受影响
- 使用 qfluentwidgets 组件保持一致性

注意：此任务依赖 P0-5-2 完成

### P0-5-4: 精简选项卡
- 团队：frontend
- 负责人：frontend-1
- 优先级：中
- 预计时间：1.0 小时
- 依赖任务：P0-5-3

任务描述：

精简 AgentHubPage 的选项卡：

1. 根据精简方案删除不必要的选项卡
2. 将重要功能整合到主界面
3. 简化导航逻辑

文件路径：
- src/ui/agent_hub_page.py

注意事项：
- 删除前确认功能是否有其他入口
- 保留核心清理功能（一键清理、增量清理）
- 保留撤销功能

注意：此任务依赖 P0-5-3 完成

### P0-5-5: 优化导航栏
- 团队：frontend
- 负责人：frontend-2
- 优先级：中
- 预计时间：1.0 小时
- 依赖任务：P0-5-4

任务描述：

优化 AgentHubPage 的导航栏：

1. 重新设计导航栏布局
2. 添加快速访问按钮（一键清理、增量清理、撤销）
3. 优化图标和标签

文件路径：
- src/ui/agent_hub_page.py

注意事项：
- 保持简洁，避免过度设计
- 使用 qfluentwidgets 的导航组件
- 确保可访问性

注意：此任务依赖 P0-5-4 完成

### P0-5-6: UI 测试
- 团队：testing
- 负责人：testing-1
- 优先级：中
- 预计时间：1.0 小时
- 依赖任务：P0-5-3, P0-5-4, P0-5-5

任务描述：

测试重新设计的 UI：

1. 测试所有 UI 组件是否正常显示
2. 测试按钮响应
3. 测试选项卡切换
4. 测试导航栏功能
5. 测试响应式布局（如果支持）

测试文件路径：
- tests/ui/test_agent_hub_page_redesign.py（新建）

注意：此任务依赖 P0-5-3, P0-5-4, P0-5-5 完成

### P0-5-7: 用户体验测试
- 团队：testing
- 负责人：testing-2
- 优先级：中
- 预计时间：1.0 小时
- 依赖任务：P0-5-6

任务描述：

测试用户体验：

1. 测试完整用户流程（从打开应用到执行清理）
2. 测试错误处理和提示
3. 测试性能（页面加载、组件响应）
4. 收集用户体验反馈

输出：
- 用户体验测试报告
- 发现的问题列表
- 改进建议

文件路径：
- tests/ux/user_experience_test_report.md（新建）

注意：此任务依赖 P0-5-6 完成

---

任务认领规则：
- 每个任务必须由指定的负责人认领
- 依赖任务未完成时，后续任务无法开始
- 认领后将任务状态改为 "in progress"
- 完成后将任务状态改为 "completed"

消息协议：
- 完成任务后，发送 handoff 消息给下一个团队
- 遇到阻塞时，立即发送 blocker 消息
- 使用标准的 JSON 消息格式

示例 handoff 消息：

```json
{
  "sender": "dev-1",
  "recipient": "frontend-1",
  "message_type": "handoff",
  "timestamp": "2026-02-24T18:30:00Z",
  "task_id": "P0-4-1",
  "content": {
    "status": "completed",
    "changed_files": ["src/agent/smart_recommender.py"],
    "api_changes": {
      "new_methods": [
        "SmartRecommender.load_last_cleanup_files()",
        "SmartRecommender.save_last_cleanup_files(files)"
      ]
    },
    "requirements": [
      "前端需要集成新的 API 方法"
    ]
  }
}
```

请开始认领任务！

================================================================================
