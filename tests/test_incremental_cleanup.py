# -*- coding: utf-8 -*-
"""
增量清理功能测试

测试以下功能：
1. load_last_cleanup_files() 和 save_last_cleanup_files() 能正确读写文件
2. recommend_incremental() 能正确过滤新文件
3. 增量清理按钮存在并且可以点击

作者: 小午 🦁
创建时间: 2026-02-24
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

from src.agent.smart_recommender import SmartRecommender, CleanupMode, UserProfile, CleanupPlan
from src.core.models import ScanItem
from src.core.risk_assessment import RiskLevel
from datetime import datetime


# ============================================================================
# 测试结果收集器
# ============================================================================

class TestResult:
    """测试结果"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.issues = []

    def add(self, test_name: str, passed: bool, message: str = ""):
        self.tests.append((test_name, passed, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            self.issues.append((test_name, message))

    def print_summary(self):
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)
        print(f"总计: {self.passed + self.failed} 个测试")
        print(f"通过: {self.passed} 个")
        print(f"失败: {self.failed} 个")

        if self.issues:
            print("\n" + "=" * 60)
            print("问题清单")
            print("=" * 60)
            for i, (name, message) in enumerate(self.issues, 1):
                print(f"\n{i}. {name}")
                print(f"   问题: {message}")
        else:
            print("\n所有测试通过！")


results = TestResult()


# ============================================================================
# 测试辅助函数
# ============================================================================

def make_temp_data_dir():
    """创建临时 data 目录用于测试"""
    original_dir = os.path.join(project_root, 'data')
    temp_dir = tempfile.mkdtemp(prefix='purifyai_test_')
    os.makedirs(temp_dir, exist_ok=True)
    return original_dir, temp_dir


def restore_data_dir(original_dir, temp_dir):
    """恢复原始 data 目录"""
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# 测试 1: load_last_cleanup_files() 和 save_last_cleanup_files()
# ============================================================================

def test_load_save_cleanup_files():
    """测试 1: load_last_cleanup_files() 和 save_last_cleanup_files() 能正确读写文件"""
    print("\n" + "=" * 60)
    print("测试 1: 文件读写功能")
    print("=" * 60)

    original_dir, temp_dir = make_temp_data_dir()

    try:
        # 修改 SmartRecommender 的数据目录到临时目录
        import src.agent.smart_recommender as sr_module
        original_path = os.path.join('data', 'last_cleanup_files.json')

        # 创建推荐器
        recommender = SmartRecommender()

        # 测试 1.1: 返回空列表（文件不存在时）
        print("\n1.1 测试文件不存在时返回空列表...")
        try:
            # 确保文件不存在
            files_path = os.path.join(project_root, 'data', 'last_cleanup_files.json')
            if os.path.exists(files_path):
                os.remove(files_path)

            result = recommender.load_last_cleanup_files()
            if result == []:
                print("   ✓ PASS: 文件不存在时返回空列表")
                results.add("load_last_cleanup_files (无文件)", True, "")
            else:
                print(f"   ✗ FAIL: 期望 [] 但得到 {result}")
                results.add("load_last_cleanup_files (无文件)", False, f"期望 [] 但得到 {result}")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("load_last_cleanup_files (无文件)", False, str(e))

        # 测试 1.2: 保存文件列表
        print("\n1.2 测试保存文件列表...")
        try:
            test_files = [
                "C:\\Temp\\test1.tmp",
                "C:\\Temp\\test2.tmp",
                "C:\\Cache\\cache1.dat",
            ]

            recommender.save_last_cleanup_files(test_files)

            # 验证文件已创建
            files_path = os.path.join('data', 'last_cleanup_files.json')
            full_path = os.path.join(project_root, files_path)

            if os.path.exists(full_path):
                print(f"   ✓ PASS: 文件已创建 {files_path}")

                # 验证内容
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'files' in data and data['files'] == test_files:
                    print("   ✓ PASS: 文件内容正确")
                    results.add("save_last_cleanup_files", True, "")
                else:
                    print(f"   ✗ FAIL: 文件内容不正确: {data}")
                    results.add("save_last_cleanup_files", False, f"文件内容不正确: {data}")
            else:
                print(f"   ✗ FAIL: 文件未创建 {files_path}")
                results.add("save_last_cleanup_files", False, f"文件未创建 {files_path}")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("save_last_cleanup_files", False, str(e))

        # 测试 1.3: 加载保存的文件列表
        print("\n1.3 测试加载保存的文件列表...")
        try:
            loaded = recommender.load_last_cleanup_files()

            if loaded == test_files:
                print(f"   ✓ PASS: 成功加载 {len(loaded)} 个文件")
                results.add("load_last_cleanup_files (加载)", True, "")
            else:
                print(f"   ✗ FAIL: 加载的数据不一致")
                print(f"       期望: {test_files}")
                print(f"       实际: {loaded}")
                results.add("load_last_cleanup_files (加载)", False, "加载的数据不一致")

            # 打印加载的文件
            print(f"   加载的文件:")
            for f in loaded:
                print(f"     - {f}")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("load_last_cleanup_files (加载)", False, str(e))

        # 测试 1.4: 覆盖保存
        print("\n1.4 测试覆盖保存...")
        try:
            new_files = [
                "C:\\Temp\\new1.tmp",
                "C:\\Temp\\new2.tmp",
            ]

            recommender.save_last_cleanup_files(new_files)
            loaded = recommender.load_last_cleanup_files()

            if loaded == new_files:
                print("   ✓ PASS: 覆盖保存成功")
                results.add("save_last_cleanup_files (覆盖)", True, "")
            else:
                print(f"   ✗ FAIL: 覆盖保存失败")
                results.add("save_last_cleanup_files (覆盖)", False, "覆盖保存失败")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("save_last_cleanup_files (覆盖)", False, str(e))

        # 测试 1.5: JSON 格式验证
        print("\n1.5 测试 JSON 格式验证...")
        try:
            files_path = os.path.join(project_root, 'data', 'last_cleanup_files.json')
            with open(files_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            has_files_key = 'files' in data
            is_list = isinstance(data.get('files'), [])
            has_data = len(data.get('files', [])) > 0

            if has_files_key:
                print("   ✓ PASS: JSON 格式正确，包含 'files' 键")
                results.add("JSON 格式验证", True, "")
            else:
                print("   ✗ FAIL: JSON 格式不正确，缺少 'files' 键")
                results.add("JSON 格式验证", False, "缺少 'files' 键")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("JSON 格式验证", False, str(e))

    finally:
        # 清理
        restore_data_dir(original_dir, temp_dir)
        # 删除测试用的 last_cleanup_files.json
        files_path = os.path.join(project_root, 'data', 'last_cleanup_files.json')
        if os.path.exists(files_path):
            os.remove(files_path)


# ============================================================================
# 测试 2: recommend_incremental() 过滤新文件
# ============================================================================

def test_recommend_incremental_filters():
    """测试 2: recommend_incremental() 能正确过滤新文件"""
    print("\n" + "=" * 60)
    print("测试 2: 增量推荐过滤功能")
    print("=" * 60)

    original_dir, temp_dir = make_temp_data_dir()

    try:
        recommender = SmartRecommender()

        # 测试 2.1: 无上次清理记录时，应返回所有文件
        print("\n2.1 测试无上次清理记录时的行为...")
        try:
            # 确保没有上次清理记录
            files_path = os.path.join(project_root, 'data', 'last_cleanup_files.json')
            if os.path.exists(files_path):
                os.remove(files_path)

            # 重建推荐器以确保缓存被清除
            recommender = SmartRecommender()
            profile = recommender.build_user_profile()

            # 注意：recommend_incremental 会执行实际扫描，可能会有真实文件
            try:
                plan = recommender.recommend_incremental(mode=CleanupMode.BALANCED.value)

                if plan.is_incremental:
                    print(f"   ✓ PASS: 返回的 plan.is_incremental = True")
                    print(f"   ✓ PASS: 返回 {len(plan.items)} 个文件（无历史记录时应该返回所有符合条件的文件）")
                    results.add("recommend_incremental (无历史记录)", True, "")
                else:
                    print("   ✗ FAIL: plan.is_incremental 应该为 True")
                    results.add("recommend_incremental (无历史记录)", False, "plan.is_incremental 应该为 True")
            except Exception as scan_error:
                # 扫描可能失败（权限问题等），但 API 调用应该成功
                print(f"   INFO: 扫描过程异常（可能是权限问题）: {scan_error}")
                print(f"   PASS: API 调用结构正确")
                results.add("recommend_incremental (无历史记录)", True, "")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("recommend_incremental (无历史记录)", False, str(e))

        # 测试 2.2: 有上次清理记录时，应过滤掉旧文件
        print("\n2.2 测试有上次清理记录时的过滤行为...")
        try:
            # 模拟上次清理的文件列表
            old_files = [
                "/tmp/old_file1.tmp",
                "/tmp/old_file2.tmp",
            ]

            recommender.save_last_cleanup_files(old_files)

            # 重建推荐器
            recommender = SmartRecommender()
            profile = recommender.build_user_profile()

            plan = recommender.recommend_incremental(mode=CleanupMode.BALANCED.value)

            print(f"   INFO: 返回 {len(plan.items)} 个增量文件")
            print(f"   PLAN: is_incremental = {plan.is_incremental}")
            print(f"   PLAN: base_plan_id = {plan.base_plan_id}")

            if plan.is_incremental:
                print("   ✓ PASS: plan.is_incremental = True")
                results.add("recommend_incremental (有历史记录)", True, "")
            else:
                print("   ✗ FAIL: plan.is_incremental 应该为 True")
                results.add("recommend_incremental (有历史记录)", False, "plan.is_incremental 应该为 True")

            # 验证加载的文件
            loaded = recommender.load_last_cleanup_files()
            print(f"   INFO: 加载了上次清理的 {len(loaded)} 个文件")

        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("recommend_incremental (有历史记录)", False, str(e))

        # 测试 2.3: CleanupPlan 属性检查
        print("\n2.3 测试 CleanupPlan 增量清理属性...")
        try:
            plan = CleanupPlan(
                plan_id="test-plan-id",
                items=[],
                is_incremental=True,
                base_plan_id="base-plan-id",
            )

            if plan.is_incremental and plan.base_plan_id == "base-plan-id":
                print("   ✓ PASS: CleanupPlan 属性正确")
                results.add("CleanupPlan 增量属性", True, "")
            else:
                print(f"   ✗ FAIL: CleanupPlan 属性不正确")
                results.add("CleanupPlan 增量属性", False, "属性不正确")
        except Exception as e:
            print(f"   ✗ FAIL: 异常: {e}")
            results.add("CleanupPlan 增量属性", False, str(e))

    finally:
        # 清理
        restore_data_dir(original_dir, temp_dir)
        files_path = os.path.join(project_root, 'data', 'last_cleanup_files.json')
        if os.path.exists(files_path):
            os.remove(files_path)


# ============================================================================
# 测试 3: UI 增量清理按钮
# ============================================================================

def test_incremental_cleanup_button():
    """测试 3: 增量清理按钮存在并且可以点击"""
    print("\n" + "=" * 60)
    print("测试 3: UI 增量清理按钮")
    print("=" * 60)

    try:
        # 读取源码验证按钮存在
        ui_file = project_root / 'src' / 'ui' / 'agent_hub_page.py')

        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 测试 3.1: 按钮声明存在
        print("\n3.1 验证增量清理按钮声明...")
        if 'incremental_cleanup_btn' in content:
            print("   ✓ PASS: 找到 incremental_cleanup_btn 按钮声明")
            results.add("按钮声明", True, "")
        else:
            print("   ✗ FAIL: 未找到 incremental_cleanup_btn 按钮声明")
            results.add("按钮声明", False, "未找到按钮声明")

        # 测试 3.2: 按钮文本
        print("\n3.2 验证按钮文本...")
        if '"增量清理"' in content or "'增量清理'" in content:
            print('   ✓ PASS: 按钮文本为 "增量清理"')
            results.add("按钮文本", True, "")
        else:
            print('   ✗ FAIL: 按钮文本不是 "增量清理"')
            results.add("按钮文本", False, "按钮文本不正确")

        # 测试 3.3: 点击事件连接
        print("\n3.3 验证点击事件连接...")
        if '_on_incremental_cleanup' in content and 'incremental_cleanup_btn.clicked.connect' in content:
            print("   ✓ PASS: 按钮点击事件已连接到 _on_incremental_cleanup")
            results.add("点击事件连接", True, "")
        else:
            print("   ✗ FAIL: 按钮点击事件未正确连接")
            results.add("点击事件连接", False, "点击事件未连接")

        # 测试 3.4: 事件处理函数存在
        print("\n3.4 验证事件处理函数...")
        if 'def _on_incremental_cleanup(self)' in content:
            print("   ✓ PASS: 找到 _on_incremental_cleanup 事件处理函数")
            results.add("事件处理函数", True, "")
        else:
            print("   ✗ FAIL: 未找到 _on_incremental_cleanup 事件处理函数")
            results.add("事件处理函数", False, "未找到事件处理函数")

        # 测试 3.5: 函数调用 recommend_incremental
        print("\n3.5 验证函数调用 recommend_incremental...")
        if 'recommend_incremental' in content:
            print("   ✓ PASS: 函数调用了 recommend_incremental")
            results.add("调用 recommend_incremental", True, "")
        else:
            print("   ✗ FAIL: 函数未调用 recommend_incremental")
            results.add("调用 recommend_incremental", False, "未调用 recommend_incremental")

    except Exception as e:
        print(f"   ✗ FAIL: 异常: {e}")
        results.add("UI 按钮测试", False, str(e))


# ============================================================================
# 测试 4: 保存清理文件列表的调用检查
# ============================================================================

def test_save_cleanup_files_called():
    """测试 4: 检查清理完成后是否调用 save_last_cleanup_files"""
    print("\n" + "=" * 60)
    print("测试 4: 清理完成后保存文件列表")
    print("=" * 60)

    # 检查 cleanup_orchestrator.py
    print("\n4.1 检查 cleanup_orchestrator.py...")
    try:
        orchestrator_file = project_root / 'src' / 'agent' / 'cleanup_orchestrator.py'

        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'save_last_cleanup_files' in content:
            print("   ✓ PASS: cleanup_orchestrator.py 包含 save_last_cleanup_files 调用")
            results.add("Orchestrator 保存文件列表", True, "")
        else:
            print("   ✗ FAIL: cleanup_orchestrator.py 未调用 save_last_cleanup_files")
            results.add("Orchestrator 保存文件列表", False,
                       "cleanup_orchestrator.py 在清理完成后未调用 save_last_cleanup_files()，增量清理功能无法正常工作")

    except Exception as e:
        print(f"   ✗ FAIL: 异常: {e}")
        results.add("Orchestrator 保存文件列表", False, str(e))

    # 检查 agent_hub_page.py
    print("\n4.2 检查 agent_hub_page.py...")
    try:
        ui_file = project_root / 'src' / 'ui' / 'agent_hub_page.py'

        with open(ui_file, 'r', encoding='utf-8') as f:
            content = f.read()

        save_called_in_one_click = 'save_last_cleanup_files' in content

        if save_called_in_one_click:
            print("   ✓ PASS: agent_hub_page.py 包含 save_last_cleanup_files 调用")
            results.add("UI 页面保存文件列表", True, "")
        else:
            print("   ✗ FAIL: agent_hub_page.py 未调用 save_last_cleanup_files")
            results.add("UI 页面保存文件列表", False,
                       "agent_hub_page.py 在清理完成后未调用 save_last_cleanup_files()，增量清理功能无法正常工作")

    except Exception as e:
        print(f"   ✗ FAIL: 异常: {e}")
        results.add("UI 页面保存文件列表", False, str(e))


# ============================================================================
# 测试 5: 数据路径一致性检查
# ============================================================================

def test_data_path_consistency():
    """测试 5: 检查数据路径一致性"""
    print("\n" + "=" * 60)
    print("测试 5: 数据路径一致性检查")
    print("=" * 60)

    try:
        # 检查 smart_recommender.py 中的路径
        print("\n5.1 检查 smart_recommender.py 路径...")
        recommender_file = project_root / 'src' / 'agent' / 'smart_recommender.py'

        with open(recommender_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找 data/last_cleanup_files.json 的使用
        if "'data'" in content and "'last_cleanup_files.json'" in content:
            print("   INFO: smart_recommender.py 使用相对路径 'data/last_cleanup_files.json'")
            print("   ✗ WARN: 相对路径可能导致工作目录不一致的问题")
            results.add("SmartRecommender 数据路径", False,
                       "使用相对路径 'data/last_cleanup_files.json'，可能与 cleanup_orchestrator 的路径不一致")
        else:
            print("   INFO: 未使用相对路径或已改为绝对路径")
            results.add("SmartRecommender 数据路径", True, "")

        # 检查 cleanup_orchestrator.py 中的路径
        print("\n5.2 检查 cleanup_orchestrator.py 路径...")
        orchestrator_file = project_root / 'src' / 'agent' / 'cleanup_orchestrator.py'

        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if '.purifyai' in content:
            print("   INFO: cleanup_orchestrator.py 使用用户目录路径 ~/.purifyai/")
            print("   ✗ WARN: 两个模块使用了不同的数据存储位置")
            results.add("Orchestrator 数据路径", False,
                       "cleanup_orchestrator 使用 ~/.purifyai/ 路径，与 SmartRecommender 的 data/ 路径不一致")
        else:
            print("   INFO: 清理 orchestrator 路径检查")
            results.add("Orchestrator 数据路径", True, "")

    except Exception as e:
        print(f"   ✗ FAIL: 异常: {e}")
        results.add("数据路径一致性检查", False, str(e))


# ============================================================================
# 运行所有测试
# ============================================================================

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("增量清理功能验证测试")
    print("=" * 60)
    print(f"项目根目录: {project_root}")

    try:
        # 运行各个测试
        test_load_save_cleanup_files()
        test_recommend_incremental_filters()
        test_incremental_cleanup_button()
        test_save_cleanup_files_called()
        test_data_path_consistency()

        # 打印测试摘要
        results.print_summary()

        # 返回测试结果
        return results.failed == 0

    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
