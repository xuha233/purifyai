#!/usr/bin/env python3
"""
PurifyAI Agent Teams 任务分配脚本

这个脚本用于生成 Agent Teams的任务分配提示，让用户可以复制粘贴到 Claude Code 中。

使用方法：
- 运行脚本：python agent_task_dispatcher.py
- 复制输出，粘贴到 Claude Code 中

作者：小午
创建时间：2026-02-24
"""

import json
from datetime import datetime

# 队友和任务配置
TEAMS = {
    "dev": {
        "count": 3,
        "members": ["dev-1", "dev-2", "dev-3"],
        "specialty": "后端 Python 开发、智能推荐算法、清理编排逻辑",
        "writable_paths": ["src/agent/", "src/core/"],
        "readable_paths": [],
        "forbidden_paths": ["src/ui/", "tests/", "project-team-kit/"]
    },
    "frontend": {
        "count": 3,
        "members": ["frontend-1", "frontend-2", "frontend-3"],
        "specialty": "PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化",
        "writable_paths": ["src/ui/"],
        "readable_paths": ["src/agent/", "src/core/"],
        "forbidden_paths": ["src/agent/", "src/core/", "tests/", "project-team-kit/"]
    },
    "testing": {
        "count": 2,
        "members": ["testing-1", "testing-2"],
        "specialty": "单元测试、集成测试、边界条件测试",
        "writable_paths": ["tests/"],
        "readable_paths": ["src/agent/", "src/core/", "src/ui/"],
        "forbidden_paths": ["src/", "project-team-kit/"]
    },
    "docs": {
        "count": 2,
        "members": ["docs-1", "docs-2"],
        "specialty": "任务文件编写、开发文档维护、迭代计划更新",
        "writable_paths": ["project-team-kit/"],
        "readable_paths": ["src/agent/", "src/core/", "src/ui/", "tests/"],
        "forbidden_paths": ["src/", "tests/"]
    }
}

# 任务列表
TASKS = [
    {
        "task_id": "P0-4-1",
        "name": "实现 last_cleanup_files.json 存储",
        "team": "dev",
        "assignee": "dev-1",
        "priority": "高",
        "estimated_hours": 0.5,
        "dependencies": [],
        "description": """
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
"""
    },
    {
        "task_id": "P0-4-2",
        "name": "完善增量清理推荐逻辑",
        "team": "dev",
        "assignee": "dev-2",
        "priority": "高",
        "estimated_hours": 0.5,
        "dependencies": ["P0-4-1"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-4-3",
        "name": "agent_hub_page.py 添加增量清理按钮",
        "team": "frontend",
        "assignee": "frontend-1",
        "priority": "高",
        "estimated_hours": 0.5,
        "dependencies": [],
        "description": """
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
"""
    },
    {
        "task_id": "P0-4-4",
        "name": "增量清理预览 UI 集成",
        "team": "frontend",
        "assignee": "frontend-2",
        "priority": "高",
        "estimated_hours": 0.5,
        "dependencies": ["P0-4-3"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-4-5",
        "name": "单元测试和集成测试",
        "team": "testing",
        "assignee": "testing-1",
        "priority": "高",
        "estimated_hours": 1.0,
        "dependencies": ["P0-4-1", "P0-4-2", "P0-4-3", "P0-4-4"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-5-1",
        "name": "分析 AgentHubPage 结构",
        "team": "docs",
        "assignee": "docs-1",
        "priority": "中",
        "estimated_hours": 0.5,
        "dependencies": [],
        "description": """
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
"""
    },
    {
        "task_id": "P0-5-2",
        "name": "设计新的页面布局",
        "team": "docs",
        "assignee": "docs-2",
        "priority": "中",
        "estimated_hours": 0.5,
        "dependencies": ["P0-5-1"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-5-3",
        "name": "重构 AgentHubPage 主布局",
        "team": "frontend",
        "assignee": "frontend-3",
        "priority": "中",
        "estimated_hours": 1.5,
        "dependencies": ["P0-5-2"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-5-4",
        "name": "精简选项卡",
        "team": "frontend",
        "assignee": "frontend-1",
        "priority": "中",
        "estimated_hours": 1.0,
        "dependencies": ["P0-5-3"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-5-5",
        "name": "优化导航栏",
        "team": "frontend",
        "assignee": "frontend-2",
        "priority": "中",
        "estimated_hours": 1.0,
        "dependencies": ["P0-5-4"],
        "description": """
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
"""
    },
    {
        "task_id": "P0-5-6",
        "name": "UI 测试",
        "team": "testing",
        "assignee": "testing-1",
        "priority": "中",
        "estimated_hours": 1.0,
        "dependencies": ["P0-5-3", "P0-5-4", "P0-5-5"],
        "description": """
测试重新设计的 UI：

1. 测试所有 UI 组件是否正常显示
2. 测试按钮响应
3. 测试选项卡切换
4. 测试导航栏功能
5. 测试响应式布局（如果支持）

测试文件路径：
- tests/ui/test_agent_hub_page_redesign.py（新建）
"""
    },
    {
        "task_id": "P0-5-7",
        "name": "用户体验测试",
        "team": "testing",
        "assignee": "testing-2",
        "priority": "中",
        "estimated_hours": 1.0,
        "dependencies": ["P0-5-6"],
        "description": """
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
"""
    }
]


def generate_team_creation_prompt():
    """生成团队创建提示"""
    prompt = """我需要为 PurifyAI v1.0 项目搭建 Agent Teams，请创建以下团队：

"""

    for team_name, team_config in TEAMS.items():
        prompt += f"\n团队 {team_name}（{team_name}）\n"
        prompt += f"- 队友数量：{team_config['count']} 名\n"
        prompt += f"- 专长：{team_config['specialty']}\n"
        prompt += f"- 可修改文件：{', '.join(team_config['writable_paths'])}\n"
        if team_config['readable_paths']:
            prompt += f"- 可读文件（了解接口）：{', '.join(team_config['readable_paths'])}\n"
        if team_config['forbidden_paths']:
            prompt += f"- 禁止修改：{', '.join(team_config['forbidden_paths'])}\n"

    prompt += """
当前项目信息：
- 项目路径：G:/docker/diskclean
- 分支：feature/v1.0-refactor
- 开发进度报告：project-team-kit/DEV-PROGRESS-REPORT-v1.0.md
- 交接协议：project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

请设置为 Delegate 模式，我只负责协调和任务分配，不直接写代码。
"""

    return prompt


def generate_task_assignment_prompt():
    """生成任务分配提示"""
    prompt = """首先，请所有队员阅读交接协议：
cat project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

然后，请开始认领以下任务（优先级：P0-4 > P0-5）：

"""

    # 按 task_id 排序
    sorted_tasks = sorted(TASKS, key=lambda t: (t['task_id'].split('-')[1], len(t['task_id'].split('-')), t['task_id']))

    for task in sorted_tasks:
        prompt += f"\n### {task['task_id']}: {task['name']}\n"
        prompt += f"- 团队：{task['team']}\n"
        prompt += f"- 负责人：{task['assignee']}\n"
        prompt += f"- 优先级：{task['priority']}\n"
        prompt += f"- 预计时间：{task['estimated_hours']} 小时\n"

        if task['dependencies']:
            prompt += f"- 依赖任务：{', '.join(task['dependencies'])}\n"

        prompt += f"""任务描述：
{task['description']}
"""
        # 添加任务依赖消息
        if task['dependencies']:
            prompt += f"\n注意：此任务依赖 {', '.join(task['dependencies'])} 完成\n"

    prompt += """
任务认领规则：
- 每个任务必须由指定的负责人认领
- 依赖任务未完成时，后续任务无法开始
- 认领后将任务状态改为 "in progress"
- 完成后将任务状态改为 "completed"

消息协议：
- 完成任务后，发送 handoff 消息给下一个团队
- 遇到阻塞时，立即发送 blocker 消息
- 使用标准的 JSON 消息格式

请开始认领任务！
"""

    return prompt


def generate_handoff_message(task):
    """生成 handoff 消息示例"""
    message = {
        "sender": task['assignee'],
        "recipient": "小午",
        "message_type": "handoff",
        "timestamp": datetime.now().isoformat() + "Z",
        "task_id": task['task_id'],
        "content": {
            "status": "completed",
            "estimated_hours": task['estimated_hours'],
            "dependencies": task['dependencies'],
            "description": task['description']
        }
    }

    return json.dumps(message, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    print("=" * 80)
    print("  PurifyAI Agent Teams 任务分配提示生成器")
    print("  作者：小午 🦁")
    print("=" * 80)
    print()

    # 生成团队创建提示
    print("\n" + "=" * 80)
    print("【Step 1】团队创建提示（复制这段到 Claude Code）")
    print("=" * 80)
    print()
    print(generate_team_creation_prompt())

    # 生成任务分配提示
    print("\n" + "=" * 80)
    print("【Step 2】任务分配提示（复制这段到 Claude Code）")
    print("=" * 80)
    print()
    print(generate_task_assignment_prompt())

    # 统计信息
    print("\n" + "=" * 80)
    print("【统计信息】")
    print("=" * 80)
    print(f"总团队数：{len(TEAMS)}")
    print(f"总队友数：{sum(team['count'] for team in TEAMS.values())}")
    print(f"总任务数：{len(TASKS)}")

    print("\n按团队统计：")
    for team_name, team_config in TEAMS.items():
        team_tasks = [t for t in TASKS if t['team'] == team_name]
        print(f"  {team_name}: {len(team_tasks)} 个任务，预计 {sum(t['estimated_hours'] for t in team_tasks)} 小时")

    print("\n按优先级统计：")
    priority_tasks = {}
    for task in TASKS:
        priority = task['priority']
        if priority not in priority_tasks:
            priority_tasks[priority] = []
        priority_tasks[priority].append(task)

    for priority in ["高", "中", "低"]:
        if priority in priority_tasks:
            tasks = priority_tasks[priority]
            print(f"  {priority}: {len(tasks)} 个任务，预计 {sum(t['estimated_hours'] for t in tasks)} 小时")

    print()
    print("=" * 80)
    print("准备好了！请复制上述提示到 Claude Code 中，开始分配任务。")
    print("=" * 80)


if __name__ == "__main__":
    main()
