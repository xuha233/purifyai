#!/usr/bin/env python3
"""
Claude Code Agent Teams 自动化启动脚本

这个脚本会自动调用 Claude Code 并创建 Agent Teams。

使用方法：
1. 确保已安装 Claude Code CLI
2. 运行此脚本

注意事项：
- 需要网络连接
- Claude Code 会创建新的会话
"""

import subprocess
import sys

# 步骤 1: 创建团队的提示
CREATE_TEAMS_PROMPT = """请为 PurifyAI v1.0 项目创建 4 个 Agent Teams 团队：

团队 1: dev
- 队友数量：3 名
- 专长：后端 Python 开发、智能推荐算法、清理编排逻辑
- 可修改文件：src/agent/, src/core/
- 禁止修改：src/ui/, tests/, project-team-kit/

团队 2: frontend
- 队友数量：3 名
- 专长：PyQt5 + qfluentwidgets UI 开发、组件设计、用户体验优化
- 可修改文件：src/ui/
- 可读文件（了解接口）：src/agent/, src/core/
- 禁止修改：src/agent/, src/core/, tests/, project-team-kit/

团队 3: testing
- 队友数量：2 名
- 专长：单元测试、集成测试、边界条件测试
- 可修改文件：tests/
- 可读文件：所有代码文件（了解被测试的代码）
- 禁止修改：src/, project-team-kit/

团队 4: docs
- 队友数量：2 名
- 专长：任务文件编写、开发文档维护、迭代计划更新
- 可修改文件：project-team-kit/
- 可读文件：所有代码和文档
- 禁止修改：src/, tests/

当前项目信息：
- 项目路径：G:/docker/diskclean
- 分支：feature/v1.0-refactor
- 交接协议：project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

请设置为 Delegate 模式（只协调，不直接写代码）。
"""

# 步骤 2: 分配任务的提示
ASSIGN_TASKS_PROMPT = """请先阅读交接协议：
cat project-team-kit/AGENT-TEAMS-HANDOFF-v2.0.md

然后分配以下 P0-4 任务给相应团队的队友：

P0-4-1（dev-1）：实现 last_cleanup_files.json 存储
- 实现 SmartRecommender.load_last_cleanup_files() 方法
- 实现 SmartRecommender.save_last_cleanup_files(files) 方法
- 文件路径：src/agent/smart_recommender.py
- 预计时间：0.5 小时

P0-4-2（dev-2）：完善增量清理推荐逻辑
- 完善 SmartRecommender.recommend_incremental() 方法
- 对比当前扫描结果和上次清理文件
- 过滤出新文件
- 文件路径：src/agent/smart_recommender.py
- 预计时间：0.5 小时
- 依赖：P0-4-1

P0-4-3（frontend-1）：agent_hub_page.py 添加增量清理按钮
- 添加"增量清理"按钮
- 连接 recommend_incremental() 方法
- 显示增量清理文件列表
- 文件路径：src/ui/agent_hub_page.py
- 预计时间：0.5 小时

P0-4-4（frontend-2）：增量清理预览 UI 集成
- 更新 CleanupPreviewCard 显示增量清理统计
- 更新 CleanupProgressWidget 处理清理完成后逻辑
- 完成后调用 save_last_cleanup_files() 保存文件列表
- 文件路径：src/ui/cleanup_preview_card.py, src/ui/cleanup_progress_widget.py
- 预计时间：0.5 小时
- 依赖：P0-4-3

P0-4-5（testing-1）：单元测试和集成测试
- 测试 load_last_cleanup_files() 和 save_last_cleanup_files()
- 测试 recommend_incremental() 方法
- 测试完整的增量清理流程
- 测试 UI 按钮和响应
- 测试文件路径：tests/unit/, tests/integration/, tests/ui/
- 预计时间：1.0 小时
- 依赖：P0-4-1, P0-4-2, P0-4-3, P0-4-4

任务分配规则：
- 每个任务由指定负责人认领
- 前置任务完成后才能开始后续任务
- 使用 handoff 消息传递任务完成信息

请立即开始创建团队并分配任务！
"""

def main():
    """主函数"""
    print("=" * 80)
    print("Claude Code Agent Teams 自动化启动")
    print("=" * 80)
    print()

    # 方法 1: 直接调用 claude 命令（如果支持 pipeline）
    try:
        print("尝试方法 1: 通过 pipeline 传递提示...")

        # 将提示写入临时文件
        with open("temp_teams_prompt.txt", "w", encoding="utf-8") as f:
            f.write(CREATE_TEAMS_PROMPT + "\n\n" + ASSIGN_TASKS_PROMPT)

        # 尝试调用 claude
        result = subprocess.run(
            ["claude", "--input-file", "temp_teams_prompt.txt"],
            cwd="G:/docker/diskclean",
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ 成功！")
            print(result.stdout)
        else:
            print("❌ 失败")
            print(result.stderr)

    except Exception as e:
        print(f"方法 1 失败: {e}")
        print()

    # 方法 2: 使用 echo 管道
    try:
        print("尝试方法 2: 使用 echo 管道...")

        prompt = CREATE_TEAMS_PROMPT + "\n\n" + ASSIGN_TASKS_PROMPT

        result = subprocess.run(
            f'echo "{prompt}" | claude',
            cwd="G:/docker/diskclean",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ 成功！")
            print(result.stdout)
        else:
            print("❌ 失败")
            print(result.stderr)

    except Exception as e:
        print(f"方法 2 失败: {e}")
        print()

    # 方法 3: 生成可复制的提示
    print()
    print("=" * 80)
    print("方法 3: 生成可复制的提示")
    print("=" * 80)
    print()
    print("请复制以下内容到 Claude Code：")
    print()
    print("-" * 80)
    print(CREATE_TEAMS_PROMPT)
    print()
    print(ASSIGN_TASKS_PROMPT)
    print("-" * 80)
    print()
    print("或者，复制以下文件内容：")
    print("  - project-team-kit/PROMPT-STEP1-CREATE-TEAMS.md")
    print("  - project-team-kit/PROMPT-STEP2-ASSIGN-TASKS.md")

if __name__ == "__main__":
    main()
