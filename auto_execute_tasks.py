#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PurifyAI 任务自动化执行器

修复版：使用 PowerShell 包装 claude 命令

作者：小午
"""

import subprocess
import json
import time
import threading
from datetime import datetime
import sys

# 强制 UTF-8 输出
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 项目配置
PROJECT_PATH = "G:/docker/diskclean"
BRANCH = "feature/v1.0-refactor"

# 任务配置
TASKS = {
    "P0-4-1": {
        "name": "实现 last_cleanup_files.json 存储",
        "team": "dev",
        "timeout": 90,  # seconds (increased)
        "prompt": """请实现 SmartRecommender 中的两个方法：

1. SmartRecommender.load_last_cleanup_files()
   - 从 data/last_cleanup_files.json 读取上次清理的文件列表
   - 如果文件不存在，返回空 []
   - 返回 List[str]

2. SmartRecommender.save_last_cleanup_files(files)
   - 将文件列表保存到 data/last_cleanup_files.json
   - 参数: files: List[str]
   - 无返回值
   - 自动创建 data/ 目录（如果不存在）

文件：src/agent/smart_recommender.py

直接实现，不要问任何问题。完成后告诉我：
1. 新增或修改了哪些文件
2. API 签名是什么
3. 有什么注意事项
"""
    },
    "P0-4-2": {
        "name": "完善增量清理推荐逻辑",
        "team": "dev",
        "timeout": 90,
        "prompt": """请完善 SmartRecommender.recommend_incremental() 方法：

需求：
1. 调用 load_last_cleanup_files() 加载上次清理的文件
2. 对比当前扫描结果和上次清理文件
3. 只返回新文件（上次清理后新增的文件）
4. 返回 CleanupPlan 对象

边界情况：
- last_cleanup_files.json 不存在：全部文件都是新文件
- 某些文件已删除：忽略这些文件

文件：src/agent/smart_recommender.py

直接实现，不要问任何问题。完成后告诉我：
1. 增量清理的算法逻辑
2. 返回的 CleanupPlan 有什么特点
"""
    },
    "P0-4-3": {
        "name": "agent_hub_page.py 添加增量清理按钮",
        "team": "frontend",
        "timeout": 90,
        "prompt": """请在 AgentHubPage 中添加"增量清理"按钮：

需求：
1. 在界面顶部（标题下方或工具栏）添加"增量清理"按钮
2. 按钮点击时调用 smart_recommender.recommend_incremental()
3. 显示增量清理的文件列表
4. 集成到现有的清理流程中

参考：
- 现有的"一键清理"按钮实现（_on_one_click_cleanup 方法）
- CleanupPreviewCard 显示预览
- CleanupProgressWidget 执行清理

文件：src/ui/agent_hub_page.py

直接实现，不要问任何问题。完成后告诉我：
1. 按钮位置和样式
2. 点击后的流程
"""
    },
    "P0-4-4": {
        "name": "增量清理预览 UI 集成",
        "team": "frontend",
        "timeout": 90,
        "prompt": """请将增量清理功能集成到现有 UI 组件中：

需求：
1. 更新 CleanupPreviewCard，显示增量清理的统计信息
2. 更新 CleanupProgressWidget，处理增量清理完成
3. 确保完成后调用 save_last_cleanup_files() 保存文件列表

文件：
- src/ui/cleanup_preview_card.py
- src/ui/cleanup_progress_widget.py

直接实现，不要问任何问题。完成后告诉我：
1. 哪些文件被修改
2. 增量清理完成后的流程
"""
    },
    "P0-4-5": {
        "name": "单元测试和集成测试",
        "team": "testing",
        "timeout": 180,  # seconds (increased)
        "prompt": """请为增量清理功能编写测试：

需求：
1. 单元测试
   - 测试 load_last_cleanup_files()
   - 测试 save_last_cleanup_files()
   - 测试 recommend_incremental()
   - 测试边界条件

2. 集成测试
   - 测试完整的增量清理流程
   - 测试 UI 按钮点击和响应
   - 测试文件列表保存和加载

文件：
- tests/unit/test_smart_recommender.py（新建）
- tests/integration/test_incremental_cleanup.py（新建）
- tests/ui/test_incremental_cleanup_ui.py（新建）

直接实现，不要问任何问题。完成后告诉我：
1. 所有测试是否通过
2. 测试覆盖率是多少
3. 发现了什么问题
"""
    }
}


class TaskRunner:
    """任务执行器"""

    def __init__(self):
        self.results = {}
        self.lock = threading.Lock()

    def run_claude_task(self, task_id, task_info):
        """运行 Claude Code 任务 - 使用 PowerShell 包装"""
        prompt = task_info["prompt"]
        timeout = task_info["timeout"]

        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动任务 {task_id}: {task_info['name']}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 团队: {task_info['team']}")

            # 使用 PowerShell 调用 claude 命令
            powershell_script = f'cd {PROJECT_PATH}; claude -p --output-format json --dangerously-skip-permissions "{prompt}" 2>&1'

            result = subprocess.run(
                ["powershell", "-Command", powershell_script],
                cwd=PROJECT_PATH,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # 解析输出（从 stderr 中提取，因为 PowerShell 的 2>&1 重定向）
            output_text = result.stderr if result.stderr else result.stdout

            if result.returncode == 0 and output_text:
                # 解析 JSON 输出
                try:
                    # 查找 JSON 部分
                    lines = output_text.split('\n')
                    json_text = None
                    for line in lines:
                        line = line.strip()
                        if line.startswith('{') or line.startswith('['):
                            json_text = line
                            break

                    if json_text:
                        output = json.loads(json_text)
                        with self.lock:
                            self.results[task_id] = {
                                "status": "completed",
                                "name": task_info["name"],
                                "team": task_info["team"],
                                "result": output.get("result", ""),
                                "session_id": output.get("session_id", ""),
                                "duration_ms": output.get("duration_ms", 0),
                                "cost_usd": output.get("total_cost_usd", 0)
                            }

                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 任务 {task_id} 完成")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}]     耗时: {output.get('duration_ms', 0)/1000:.2f} 秒")
                        print(f"[{datetime.now().strftime('%H:%M:%S')}]     成本: ${output.get('total_cost_usd', 0):.4f}")
                        if output.get("result"):
                            print(f"[{datetime.now().strftime('%H:%M:%S')}]     结果: {output.get('result')[:100]}...")
                    else:
                        raise ValueError("无法找到 JSON 输出")

                except (json.JSONDecodeError, ValueError) as e:
                    with self.lock:
                        self.results[task_id] = {
                            "status": "error",
                            "name": task_info["name"],
                            "team": task_info["team"],
                            "error": f"JSON 解析失败: {e}",
                            "stdout": output_text[:500]
                        }

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 任务 {task_id} 失败: JSON 解析失败")

            else:
                with self.lock:
                    self.results[task_id] = {
                        "status": "error",
                        "name": task_info["name"],
                        "team": task_info["team"],
                        "error": output_text if output_text else result.stderr,
                        "returncode": result.returncode
                    }

                print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 任务 {task_id} 失败: {result.returncode}")

        except subprocess.TimeoutExpired:
            with self.lock:
                self.results[task_id] = {
                    "status": "timeout",
                    "name": task_info["name"],
                    "team": task_info["team"],
                    "timeout": timeout
                }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] [TIMEOUT] 任务 {task_id} 超时（{timeout} 秒）")

        except Exception as e:
            with self.lock:
                self.results[task_id] = {
                    "status": "error",
                    "name": task_info["name"],
                    "team": task_info["team"],
                    "error": str(e)
                }

            print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 任务 {task_id} 异常: {e}")

    def run_parallel_tasks(self, task_ids):
        """并行运行多个任务"""
        threads = []

        print("=" * 80)
        print(f"开始执行 {len(task_ids)} 个任务（并行）")
        print("=" * 80)
        print()

        for task_id in task_ids:
            task = TASKS[task_id]
            thread = threading.Thread(
                target=self.run_claude_task,
                args=(task_id, task)
            )
            threads.append(thread)
            thread.start()

        # 等待所有任务完成
        for thread in threads:
            thread.join()

        print()
        print("=" * 80)
        print("所有任务执行完成！")
        print("=" * 80)
        print()

        self.print_summary()

    def print_summary(self):
        """打印任务执行摘要"""
        print("\n任务执行摘要：\n")
        print(f"{'任务 ID':<15} {'名称':<30} {'团队':<10} {'状态':<10} {'成本':<10}")
        print("-" * 75)

        total_cost = 0
        total_duration = 0

        for task_id, task_info in TASKS.items():
            result = self.results.get(task_id, {"status": "pending"})

            status = result["status"]
            cost = result.get("cost_usd", 0)
            duration = result.get("duration_ms", 0)

            total_cost += cost
            total_duration += duration

            status_emoji = {
                "completed": "[OK]",
                "error": "[X]",
                "timeout": "[TIMEOUT]",
                "pending": "[...]"
            }.get(status, "[?]")

            print(f"{task_id:<15} {task_info['name']:<28} {task_info['team']:<10} {status_emoji} {status:<8} ${cost:.4f}")

        print("-" * 75)
        print(f"{'':<56} {'总计:':<10} ${total_cost:.4f}")
        print(f"{'':<56} {'平均耗时:':<10} {total_duration/1000/len(TASKS):.2f} 秒")
        print()

        # 详细结果
        print("\n详细结果：\n")
        for task_id, result in self.results.items():
            if result["status"] == "completed":
                print(f"[OK] {task_id}: {result['name']}")
                print(f"    结果: {result['result'][:200]}...")
                print()


def main():
    """主函数"""
    print("=" * 80)
    print("  PurifyAI 任务自动化执行器 (修复版)")
    print("  使用 Claude Code CLI 并行执行任务")
    print("  作者：小午")
    print("=" * 80)
    print()

    # 创建任务执行器
    runner = TaskRunner()

    # 第一批：后端任务（并行）
    print("第一批：后端任务（并行）\n")
    runner.run_parallel_tasks(["P0-4-1", "P0-4-2"])

    # 检查后端任务是否都成功
    backend_success = all(
        runner.results.get(tid, {}).get("status") == "completed"
        for tid in ["P0-4-1", "P0-4-2"]
    )

    if backend_success:
        # 第二批：前端任务（并行）
        print("第二批：前端任务（并行）\n")
        runner.run_parallel_tasks(["P0-4-3", "P0-4-4"])

        # 检查前端任务是否都成功
        frontend_success = all(
            runner.results.get(tid, {}).get("status") == "completed"
            for tid in ["P0-4-3", "P0-4-4"]
        )

        if frontend_success:
            # 第三批：测试任务
            print("第三批：测试任务\n")
            runner.run_parallel_tasks(["P0-4-5"])

            # 最终汇总
            print()
            print("=" * 80)
            print("P0-4 任务全部完成！")
            print("=" * 80)
            print()

            # 显示下一行命令
            print("下一步，请运行以下命令提交代码：")
            print(f"  cd {PROJECT_PATH}")
            print(f"  git add .")
            print(f"  git commit -m \"feat: implement P0-4 incremental cleanup\"")
            print(f"  git push origin {BRANCH}")

        else:
            print("\n[!] 前端任务有失败，请手动检查错误")
    else:
        print("\n[!] 后端任务有失败，前端任务未执行，请手动检查错误")

    print()


if __name__ == "__main__":
    main()
