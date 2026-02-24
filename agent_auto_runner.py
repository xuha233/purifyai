#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PurifyAI Agent 自动化执行器 - 方案 A（完全自动化）

编码问题解决方案：
- Binary 模式 + 手动解码（尝试多种编码）

路径问题解决方案：
- 自动查找 claude 路径（使用多种方法）

作者：小午
"""

import subprocess
import shutil
import os
import sys
import time
from datetime import datetime

# 强制 UTF-8 输出（避免中文乱码）
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 项目配置
PROJECT_PATH = "G:/docker/diskclean"


def find_claude_path():
    """查找 claude 命令路径（自动查找，多种方法）

    Returns:
        str: claude 命令路径，未找到返回 None
    """
    claude_paths = []

    # 方法 1: shutil.which（最可靠）
    try:
        path = shutil.which('claude')
        if path:
            claude_paths.append(('shutil.which', path))
    except Exception as e:
        print(f"[DEBUG] shutil.which 失败: {e}")

    # 方法 2: npm root -g（查找 npm 全局安装路径）
    try:
        result = subprocess.run(
            ['npm', 'root', '-g'],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        if result.returncode == 0:
            npm_root = result.stdout.strip()

            # claude 可能在 node_modules/.bin/
            if os.name == 'nt':  # Windows
                expected_path = os.path.join(
                    os.path.dirname(npm_root),
                    'node_modules',
                    '.bin',
                    'claude.cmd'
                )
            else:  # Linux/Mac
                expected_path = os.path.join(
                    npm_root,
                    'node_modules',
                    '.bin',
                    'claude'
                )

            if os.path.exists(expected_path):
                claude_paths.append(('npm root', expected_path))
    except Exception as e:
        print(f"[DEBUG] npm root 失败: {e}")

    # 方法 3: 直接测试常用路径
    common_paths = [
        # Windows npm 全局路径
        os.path.expanduser(r"~\AppData\Roaming\npm\claude.cmd"),
        os.path.expanduser(r"~\AppData\Roaming\node_modules\.bin\claude.cmd"),
        r"C:\Program Files\nodejs\claude.cmd",
        # Linux/Mac 路径
        os.path.expanduser("~/.npm-global/bin/claude"),
        os.path.expanduser("~/node_modules/.bin/claude"),
        "/usr/local/bin/claude",
    ]

    for path in common_paths:
        if os.path.exists(path):
            claude_paths.append(('common_path', path))
            break

    # 返回第一个找到的路径
    if claude_paths:
        source, path = claude_paths[0]
        print(f"[INFO] 找到 claude: {source} -> {path}")
        return path

    print("[ERROR] 未找到 claude 命令")
    print("[HINT] 请确保已安装 claude-code: npm install -g @anthropic-ai/claude-code")
    return None


def decode_output(raw_bytes):
    """尝试多种编码解码输出

    Args:
        raw_bytes: 原始字节流

    Returns:
        str: 解码后的字符串
    """
    # 按优先级尝试编码
    encodings = [
        'utf-8',          # 优先 UTF-8
        'gb18030',        # Windows 中文扩展
        'gbk',            # Windows 默认中文
        'gb2312',         # Windows 简体中文
        'latin-1',        # ASCII 扩展（不会失败）
    ]

    for encoding in encodings:
        try:
            text = raw_bytes.decode(encoding)
            # 简单验证：如果包含大量乱码字符，可能是错误的编码
            if encoding in ['gbk', 'gb2312', 'gb18030']:
                # 检查是否有过多的替换字符
                if text.count('\ufffd') > len(text) * 0.01:
                    continue  # 可能是错误的编码
            return text
        except (UnicodeDecodeError, LookupError):
            continue

    # 所有编码都失败，使用 errors='ignore'
    print("[WARNING] 所有编码都失败，使用 ignore 模式")
    return raw_bytes.decode('utf-8', errors='ignore')


def run_task(task_id, task_name, prompt, timeout=90):
    """运行单个任务

    Args:
        task_id: 任务 ID
        task_name: 任务名称
        prompt: Prompt 内容
        timeout: 超时时间（秒）

    Returns:
        (bool, str): (是否成功, 输出内容)
    """
    print(f"\n{'='*80}")
    print(f"Task: [{task_id}] {task_name}")
    print(f"{'='*80}")
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Timeout: {timeout}s\n")

    # 查找 claude 路径
    claude_path = find_claude_path()
    if not claude_path:
        return False, "Claude command not found"

    # 启动进程
    start_time = time.time()

    try:
        process = subprocess.Popen(
            [claude_path, '-p', '--dangerously-skip-permissions', prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,  # 使用 binary 模式
        )

        try:
            stdout, _ = process.communicate(timeout=timeout)
            elapsed = time.time() - start_time

            # 手动解码输出
            output = decode_output(stdout)

            print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Elapsed: {elapsed:.2f}s")
            print(f"Return code: {process.returncode}")

            if output:
                # 显示输出（限制长度）
                display_length = 800
                if len(output) > display_length:
                    display = output[:display_length]
                    truncated = True
                else:
                    display = output
                    truncated = False

                print(f"\nOutput:")
                print(display)
                if truncated:
                    print(f"\n... (Output truncated, total {len(output)} characters)")

            if process.returncode == 0:
                print(f"\n[OK] Task completed successfully")
                return True, output
            else:
                print(f"\n[FAIL] Task failed (return code: {process.returncode})")
                return False, output

        except subprocess.TimeoutExpired:
            process.kill()
            elapsed = time.time() - start_time
            print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
            print(f"Elapsed: {elapsed:.2f}s")
            print(f"\n[TIMEOUT] Task exceeded {timeout}s")
            return False, "TIMEOUT"

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")
        print(f"Elapsed: {elapsed:.2f}s")
        print(f"\n[ERROR] {e}")
        return False, str(e)


def main():
    """主函数"""
    print("="*80)
    print("  PurifyAI Agent Auto-Runner - Plan A (Fully Automated)")
    print("  Encoding: Binary mode + manual decode")
    print("  Path: Auto-detect multiple methods")
    print("  Author: Xiao Wu")
    print("="*80)

    # 任务列表（示例：验证 P0-4 完成）
    tasks = [
        {
            "id": "P0-verify",
            "name": "Verify P0-4 Completion",
            "timeout": 90,
            "prompt": """请验证 P0-4（增量清理功能）是否完整实现：

1. 后端方法是否完整：
   - load_last_cleanup_files()
   - save_last_cleanup_files()
   - recommend_incremental()

2. 前端 UI 是否完整：
   - agent_hub_page.py 增量清理按钮及流程
   - CleanupPreviewCard 增量清理徽章和统计
   - CleanupProgressWidget 保存文件列表

请简要验证，告诉我：
- 哪些部分已实现
- 是否有遗漏或问题
- 总体完成度百分比
"""
        },
        {
            "id": "P0-4-summary",
            "name": "P0-4 Summary",
            "timeout": 60,
            "prompt": """总结 P0-4（增量清理功能）的开发完成情况：

请列出：
1. 已完成的功能清单
2. 技术亮点
3. 可能存在的问题或待优化项
4. 是否可以开始 P0-5

直接给出总结，不要问任何问题。
"""
        },
    ]

    results = []
    success_count = 0
    fail_count = 0
    start_time = time.time()

    for i, task in enumerate(tasks, 1):
        print(f"\nProgress: {i}/{len(tasks)}")

        success, output = run_task(
            task_id=task["id"],
            task_name=task["name"],
            prompt=task["prompt"],
            timeout=task.get("timeout", 90),
        )

        results.append({
            "id": task["id"],
            "name": task["name"],
            "success": success,
            "output": output[:500] if output else ""
        })

        if success:
            success_count += 1
        else:
            fail_count += 1

        # 任务间等待（避免快速连续调用）
        if i < len(tasks):
            print(f"\nWaiting 3 seconds...")
            time.sleep(3)

    # 摘要
    total_time = time.time() - start_time

    print("\n" + "="*80)
    print("  Execution Summary")
    print("="*80)
    print(f"Total elapsed: {total_time:.2f}s")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {len(tasks)}")
    print()

    for result in results:
        status = "[OK]" if result["success"] else "[FAIL]"
        print(f"{status} [{result['id']}] {result['name']}")

    print()
    if success_count == len(tasks):
        print("[SUCCESS] All tasks completed!")
    else:
        print(f"[WARNING] {fail_count} task(s) failed")

    print("="*80)

    return success_count == len(tasks)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
