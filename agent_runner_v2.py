#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的 Agent 自动化执行器 v2.0

改进：
1. 直接使用 claude -p 命令串行执行（避免编码问题）
2. 显示实时进度
3. 自动等待任务完成
4. 重试机制

作者：小午 🦁
"""

import subprocess
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# 项目配置
PROJECT_PATH = "G:/docker/diskclean"
CLAUDE_CMD = "claude"  # 可以改为完整路径如 "C:/path/to/claude.exe"

# 任务配置（串行执行，避免多线程编码问题）
TASKS = [
    {
        "id": "P0-4-4-test",
        "name": "验证 P0-4-4 增量清理 UI 集成",
        "timeout": 90,  # seconds
        "prompt": """请验证以下功能是否正确实现：

1. CleanupPreviewCard 支持：
   - 显示"增量清理"徽章（is_incremental=True 时）
   - 显示"本次新增文件"统计卡片

2. CleanupProgressWidget 支持：
   - start_cleanup() 接收 cleanup_plan 参数
   - _on_cleanup_completed() 中检查 is_incremental
   - 调用 _save_incremental_files() 保存文件列表

3. agent_hub_page.py：
   - _start_incremental_cleanup() 传递 cleanup_plan 参数

请检查以上三个方面是否都已正确实现。如果有问题，列出问题清单。如果没有问题，告诉我"验证通过"。

文件：
- src/ui/cleanup_preview_card.py
- src/ui/cleanup_progress_widget.py
- src/ui/agent_hub_page.py
"""
    },
    {
        "id": "P0-4-summary",
        "name": "P0-4 完成度总结",
        "timeout": 60,
        "prompt": """请总结 P0-4（增量清理功能）的完成情况：

已完成：
- P0-4-1: load_last_cleanup_files() 和 save_last_cleanup_files() ✅
- P0-4-2: recommend_incremental() 方法 ✅
- P0-4-3: 增量清理按钮和流程 ✅
- P0-4-4: UI 组件集成 ✅

任务：
1. 验证 P0-4 所有子任务是否完成
2. 列出完成度百分比
3. 列出可能存在的问题或待优化项
4. 给出是否可以开始 P0-5 的建议

直接给出总结，不要问任何问题。
"""
    },
]


class OptimizedTaskRunner:
    """优化的任务执行器"""

    def run_task(self, task):
        """运行单个任务"""
        print(f"\n{'='*80}")
        print(f"任务: [{task['id']}] {task['name']}")
        print(f"{'='*80}")
        print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"预计超时: {task['timeout']} 秒\n")

        prompt = task["prompt"]
        timeout = task["timeout"]

        start_time = time.time()

        try:
            # 直接启动 claude -p 命令
            cmd = [
                CLAUDE_CMD,
                "-p",
                "--dangerously-skip-permissions",
                prompt
            ]

            print(f"启动 Claude Code...")
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,  # 二进制模式避免编码问题
            )

            # 等待完成
            try:
                stdout, _ = process.communicate(timeout=timeout)
                elapsed = time.time() - start_time

                # 解码输出（尝试多种编码）
                output = self._decode_output(stdout)

                print(f"\n完成时间: {datetime.now().strftime('%H:%M:%S')}")
                print(f"耗时: {elapsed:.2f} 秒")
                print(f"返回码: {process.returncode}")

                if output:
                    # 显示输出（限制长度）
                    display_output = output[:1000] if len(output) > 1000 else output
                    print(f"\n输出:\n{display_output}")
                    if len(output) > 1000:
                        print(f"\n... (输出已截断，共 {len(output)} 字符)")

                if process.returncode == 0:
                    print(f"\n✅ 任务 [{task['id']}] 成功完成")
                    return True, output
                else:
                    print(f"\n❌ 任务 [{task['id']}] 失败 (返回码: {process.returncode})")
                    return False, output

            except subprocess.TimeoutExpired:
                process.kill()
                elapsed = time.time() - start_time
                print(f"\n⏰ 任务 [{task['id']}] 超时 (超过 {timeout} 秒)")
                return False, "TIMEOUT"

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ 任务 [{task['id']}] 异常: {e}")
            return False, str(e)

    def _decode_output(self, raw_bytes):
        """尝试多种编码解码输出"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']

        for encoding in encodings:
            try:
                return raw_bytes.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        # 如果所有编码都失败，使用 errors='ignore'
        return raw_bytes.decode('utf-8', errors='ignore')

    def run_all(self):
        """运行所有任务（串行）"""
        print("="*80)
        print("  优化的 Agent 自动化执行器 v2.0")
        print("  串行执行 + 实时进度自动等待")
        print("  作者：小午")
        print("="*80)

        results = []
        total_time = 0
        success_count = 0

        for i, task in enumerate(TASKS, 1):
            print(f"\n进度: {i}/{len(TASKS)}\n")

            success, output = self.run_task(task)

            results.append({
                "id": task["id"],
                "name": task["name"],
                "success": success,
                "output": output[:500] if output else ""
            })

            if success:
                success_count += 1

            if i < len(TASKS):
                print(f"\n等待 3 秒后继续...")
                time.sleep(3)

        # 打印摘要
        print("\n" + "="*80)
        print("  执行摘要")
        print("="*80)

        for result in results:
            status = "[OK]" if result["success"] else "[FAIL]"
            print(f"{status} [{result['id']}] {result['name']}")

        print(f"\n成功率: {success_count}/{len(TASKS)} ({success_count/len(TASKS)*100:.1f}%)")

        if success_count == len(TASKS):
            print("\n[SUCCESS] 所有任务成功完成！")
        else:
            print(f"\n[WARNING] 有 {len(TASKS) - success_count} 个任务失败")

        print("="*80)


def main():
    """主函数"""
    runner = OptimizedTaskRunner()
    runner.run_all()


if __name__ == "__main__":
    main()
