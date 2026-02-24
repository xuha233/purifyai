#!/usr/bin/env python3
"""
PurifyAI v1.0 Agent Teams 启动脚本

这个脚本用于启动和协调 PurifyAI 项目的 Agent Teams。

使用方法：
- 在项目目录下运行：python agent_teams_launcher.py

作者：小午 🦁
创建时间：2026-02-24
"""

import os
import subprocess
import json
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path("G:/docker/diskclean")
CONFIG_FILE = PROJECT_ROOT / "project-team-kit" / "AGENT-TEAMS-CONFIG.md"
PROGRESS_FILE = PROJECT_ROOT / "project-team-kit" / "DEV-PROGRESS-REPORT-v1.0.md"

# 团队定义
TEAMS = {
    "dev": {
        "description": "开发团队 - 后端 Python 开发、智能推荐算法、清理编排逻辑",
        "count": 3,
        "skills": ["backend", "python", "algorithm", "orchestration"]
    },
    "frontend": {
        "description": "前端团队 - PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化",
        "count": 3,
        "skills": ["frontend", "pyqt5", "qfluentwidgets", "ui-design", "ux"]
    },
    "testing": {
        "description": "测试团队 - 单元测试、集成测试、边界条件测试",
        "count": 2,
        "skills": ["testing", "unit-test", "integration-test", "edge-case"]
    },
    "docs": {
        "description": "文档团队 - 任务文件编写、开发文档维护、迭代计划更新",
        "count": 2,
        "skills": ["documentation", "task-planning", "iteration-planning"]
    }
}

# 任务列表
TASKS = {
    "P0-4": {
        "name": "增量清理模式",
        "estimated_time": "3 小时",
        "priority": "高",
        "tasks": [
            {"id": "P0-4-1", "team": "dev", "title": "实现 last_cleanup_files.json 存储"},
            {"id": "P0-4-2", "team": "dev", "title": "完善增量清理推荐逻辑"},
            {"id": "P0-4-3", "team": "frontend", "title": "agent_hub_page.py 添加增量清理按钮"},
            {"id": "P0-4-4", "team": "frontend", "title": "增量清理预览 UI 集成"},
            {"id": "P0-4-5", "team": "testing", "title": "单元测试和集成测试"}
        ]
    },
    "P0-5": {
        "name": "智能体页面重新设计",
        "estimated_time": "6 小时",
        "priority": "中",
        "tasks": [
            {"id": "P0-5-1", "team": "docs", "title": "分析 AgentHubPage 结构"},
            {"id": "P0-5-2", "team": "docs", "title": "设计新的页面布局"},
            {"id": "P0-5-3", "team": "frontend", "title": "重构 AgentHubPage 主布局"},
            {"id": "P0-5-4", "team": "frontend", "title": "精简选项卡"},
            {"id": "P0-5-5", "team": "frontend", "title": "优化导航栏"},
            {"id": "P0-5-6", "team": "testing", "title": "UI 测试"},
            {"id": "P0-5-7", "team": "testing", "title": "用户体验测试"}
        ]
    }
}


def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("  PurifyAI v1.0 Agent Teams 启动器")
    print("  作者：小午 🦁")
    print("=" * 60)
    print()


def print_team_info():
    """打印团队信息"""
    print("团队配置：")
    print("-" * 60)
    for team_name, team_config in TEAMS.items():
        print(f"\n【{team_name}】 - {team_config['description']}")
        print(f"  队友数量: {team_config['count']} 名")
        print(f"  技能: {', '.join(team_config['skills'])}")


def print_tasks_info():
    """打印任务信息"""
    print("\n\n任务列表：")
    print("-" * 60)
    for task_group_id, task_group in TASKS.items():
        print(f"\n【{task_group_id}】{task_group['name']} (预计 {task_group['estimated_time']}, 优先级: {task_group['priority']})")
        for task in task_group["tasks"]:
            print(f"  [{task['id']}] {task['title']} - {task['team']}")


def check_project_files():
    """检查项目文件"""
    print("\n\n检查项目文件：")
    print("-" * 60)

    files_to_check = [
        (CONFIG_FILE, "Agent Teams 配置文件"),
        (PROGRESS_FILE, "开发进度报告"),
        (PROJECT_ROOT / "src" / "agent" / "smart_recommender.py", "SmartRecommender"),
        (PROJECT_ROOT / "src" / "agent" / "cleanup_orchestrator.py", "CleanupOrchestrator"),
        (PROJECT_ROOT / "src" / "core" / "backup_manager.py", "BackupManager"),
        (PROJECT_ROOT / "src" / "core" / "restore_manager.py", "RestoreManager"),
    ]

    all_exist = True
    for file_path, description in files_to_check:
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {description}: {file_path}")
        if not exists:
            all_exist = False

    return all_exist


def print_launch_instructions():
    """打印启动指令"""
    print("\n\n启动指令：")
    print("-" * 60)
    print("\n方式一：手动启动 Claude Code Agent Teams")
    print("=" * 60)
    print("\n在项目目录下运行：")
    print("  cd G:/docker/diskclean")
    print("  claude")
    print("\n然后在 Claude Code 中输入：")
    print("""
我需要搭建 PurifyAI 的 Agent Teams，请创建以下团队：

1. dev（开发团队）- 3 名队友，专长：后端 Python 开发、智能推荐算法、清理编排逻辑
2. frontend（前端团队）- 3 名队友，专长：PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
3. testing（测试团队）- 2 名队友，专长：单元测试、集成测试、边界条件测试
4. docs（文档团队）- 2 名队友，专长：任务文件编写、开发文档维护、迭代计划更新

当前目录：G:/docker/diskclean
当前分支：feature/v1.0-refactor

请设置为 Delegate 模式，我只负责协调和任务分配。
""")

    print("\n方式二：自动执行 P0-4 任务")
    print("=" * 60)
    print("\n执行以下命令：")
    print("  cd G:/docker/diskclean")
    print("  python agent_teams_launcher.py --task P0-4")


def main():
    """主函数"""
    print_banner()

    # 打印团队信息
    print_team_info()

    # 打印任务信息
    print_tasks_info()

    # 检查项目文件
    files_ok = check_project_files()

    # 打印启动指令
    print_launch_instructions()

    # 总结
    print("\n\n总结：")
    print("-" * 60)
    if files_ok:
        print("✅ 项目文件检查通过，可以开始启动 Agent Teams")
        print("\n当前状态：")
        print("  - 已完成: P0-1、P0-2、P0-3")
        print("  - 待开始: P0-4（增量清理模式）、P0-5（智能体页面重新设计）")
        print("  - 总体进度: ~45%")
    else:
        print("❌ 项目文件检查失败，请先完成前置任务")


if __name__ == "__main__":
    main()
