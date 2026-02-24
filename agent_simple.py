#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的 Agent 自动化执行器

作者：小午
"""

import subprocess
import time
import sys

# 强制 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 项目配置
PROJECT_PATH = "G:/docker/diskclean"


def run_task(task_name, prompt, timeout=90):
    """运行单个任务"""
    print(f"\n{'='*80}")
    print(f"Task: {task_name}")
    print(f"{'='*80}")
    print(f"Timeout: {timeout}s\n")

    try:
        # 启动 claude 命令
        process = subprocess.Popen(
            ["claude", "-p", "--dangerously-skip-permissions", prompt],
            cwd=PROJECT_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
        )

        try:
            stdout, _ = process.communicate(timeout=timeout)

            # 解码输出
            try:
                output = stdout.decode('utf-8', errors='ignore')
            except:
                output = str(stdout)

            print(f"Return code: {process.returncode}")

            if output:
                display = output[:500] if len(output) > 500 else output
                print(f"Output:\n{display}")

            if process.returncode == 0:
                print(f"\n[OK] Task completed")
                return True
            else:
                print(f"\n[FAIL] Task failed (code: {process.returncode})")
                return False

        except subprocess.TimeoutExpired:
            process.kill()
            print(f"\n[TIMEOUT] Task exceeded {timeout}s")
            return False

    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False


def main():
    """主函数"""
    print("="*80)
    print("  Simplified Agent Task Runner")
    print("="*80)

    # 任务 1: 验证 P0-4-4
    task1_prompt = """请验证以下功能是否正确实现：

1. CleanupPreviewCard 支持：
   - 显示"增量清理"徽章
   - 显示"本次新增文件"统计卡片

2. CleanupProgressWidget 支持：
   - start_cleanup() 接收 cleanup_plan 参数
   - _on_cleanup_completed() 检查 is_incremental
   - 调用 _save_incremental_files()

检查以上是否正确实现，简单验证即可。"""

    success1 = run_task("Verify P0-4-4 UI Integration", task1_prompt, 60)

    print("\nDone.")
    print(f"Result: {'PASS' if success1 else 'FAIL'}")


if __name__ == "__main__":
    main()
