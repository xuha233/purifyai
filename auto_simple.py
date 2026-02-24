#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PurifyAI 任务自动化执行器

最终修复版：处理编码问题

作者：小午
"""

import subprocess
import json
import time
import threading
from datetime import datetime
import sys
import locale

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
        "timeout": 90,  # seconds
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
}


class TaskRunner:
    """任务执行器"""

    def __init__(self):
        self.results = {}
        self.lock = threading.Lock()

    def run_claude_task(self, task_id, task_info):
        """运行 Claude Code 任务 - 使用 cmd.exe 而不是 PowerShell"""
        prompt = task_info["prompt"]
        timeout = task_info["timeout"]

        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动任务 {task_id}: {task_info['name']}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 团队: {task_info['team']}")

            # 使用 cmd.exe 调用 claude 命令，添加 UTF-8 编码
            cmd_script = f'chcp 65001 >nul 2>&1 && cd /d {PROJECT_PATH} && claude -p --output-format json --dangerously-skip-permissions "{prompt}"'

            result = subprocess.run(
                ["cmd.exe", "/c", cmd_script],
                cwd=PROJECT_PATH,
                capture_output=False,  # 不捕获，直接输出到 stdout
                text=False,
                timeout=timeout
            )

            print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 任务 {task_id} 完成 (returncode: {result.returncode})")

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
        """串行执行任务（避免编码问题）"""
        print("=" * 80)
        print(f"开始执行 {len(task_ids)} 个任务（串行 - 为了避免编码问题）")
        print("=" * 80)
        print()

        for task_id in task_ids:
            task = TASKS[task_id]
            self.run_claude_task(task_id, task)
            print()

        print("=" * 80)
        print("所有任务执行完成！")
        print("=" * 80)


def main():
    """主函数"""
    print("=" * 80)
    print("  PurifyAI 任务自动化执行器 (最终修复版)")
    print("  使用 Claude Code CLI 执行任务（串行模式）")
    print("  作者：小午")
    print("=" * 80)
    print()

    # 创建任务执行器
    runner = TaskRunner()

    # 第一批：后端任务（串行 - 避免编码问题）
    print("第一批：后端任务（串行）\n")
    runner.run_parallel_tasks(["P0-4-1", "P0-4-2"])

    print("\n第一阶段完成，请稍候...")


if __name__ == "__main__":
    main()
