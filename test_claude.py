#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 claude 命令查找
"""

import subprocess
import shutil
import os
import sys

# 强制 UTF-8 输出
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_find_claude():
    """测试查找 claude 命令"""
    print("="*80)
    print("Test: Find claude command")
    print("="*80)

    # 方法 1: shutil.which
    print("\nMethod 1: shutil.which")
    path = shutil.which('claude')
    print(f"  Result: {path}")
    print(f"  Exists: {os.path.exists(path) if path else False}")

    # 方法 2: npm root
    print("\nMethod 2: npm root -g")
    try:
        result = subprocess.run(
            ['npm', 'root', '-g'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            npm_root = result.stdout.strip()
            print(f"  npm root: {npm_root}")

            expected = os.path.join(os.path.dirname(npm_root), 'node_modules', '.bin', 'claude.cmd')
            print(f"  Expected path: {expected}")
            print(f"  Exists: {os.path.exists(expected)}")
    except Exception as e:
        print(f"  Error: {e}")

    print()


def test_decode():
    """测试解码功能"""
    print("="*80)
    print("Test: Decode output")
    print("="*80)

    test_strings = [
        "This is ASCII text",
        "中文测试文本",
        "Emoji: 🎉",
        "Mixed: ABC中文123",
    ]

    for s in test_strings:
        try:
            encoded = s.encode('utf-8')
            decoded = encoded.decode('utf-8', errors='ignore')
            print(f"  {s!r:30} -> {decoded!r}")
        except Exception as e:
            print(f"  {s!r:30} -> Error: {e}")

    print()


def test_simple_task():
    """测试简单的 claude 任务"""
    print("="*80)
    print("Test: Simple claude task")
    print("="*80)

    claude_path = shutil.which('claude')
    if not claude_path:
        print("[ERROR] claude not found")
        return

    print(f"\nFound claude: {claude_path}")

    # 简单任务
    prompt = "Say 'Hello' in one line."

    print(f"\nPrompt: {prompt}")
    print("Running (timeout 30s)...")

    try:
        process = subprocess.Popen(
            [claude_path, '-p', '--dangerously-skip-permissions', prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            cwd="G:/docker/diskclean"
        )

        stdout, _ = process.communicate(timeout=30)

        print(f"Return code: {process.returncode}")

        # 解码
        try:
            output = stdout.decode('utf-8', errors='ignore')
            print(f"Output:\n{output[:500]}")
        except Exception as e:
            print(f"Decode error: {e}")

    except subprocess.TimeoutExpired:
        process.kill()
        print("[TIMEOUT] Task exceeded 30s")
    except Exception as e:
        print(f"[ERROR] {e}")

    print()


if __name__ == "__main__":
    test_find_claude()
    test_decode()
    test_simple_task()

    print("="*80)
    print("All tests completed")
    print("="*80)
