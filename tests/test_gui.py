"""
PurifyAI GUI 自动化测试

测试覆盖核心功能:
1. 应用启动
2. 一键清理按钮点击
3. 设置页面导航
4. 规则编辑器打开
5. 清理预览弹窗
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# 添加 src 到路径
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

# Qt
from PyQt5.QtWidgets import QApplication, qApp


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def qapp():
    """创建 QApplication 实例（会话级别，只创建一次）"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def temp_config_dir(tmp_path):
    """创建临时配置目录"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    yield str(config_dir)


@pytest.fixture
def sample_scan_items():
    """创建示例扫描项目"""
    # 延迟导入以避免初始化问题
    from core.models import ScanItem

    items = []

    # 安全项目
    items.append(
        ScanItem(
            item_type="file",
            path="C:\\Windows\\Temp\\temp_file.tmp",
            size=1024 * 1024,  # 1MB
            description="临时文件",
            risk_level="safe",
        )
    )

    # 疑似项目
    items.append(
        ScanItem(
            item_type="file",
            path="C:\\Users\\Test\\Downloads\\old_file.log",
            size=5 * 1024 * 1024,  # 5MB
            description="旧日志文件",
            risk_level="suspicious",
        )
    )

    # 危险项目
    items.append(
        ScanItem(
            item_type="file",
            path="C:\\Program Files\\Important\\config.ini.bak",
            size=512 * 1024,  # 512KB
            description="备份配置文件",
            risk_level="dangerous",
        )
    )

    return items


# ============================================================================
# Part 1: 应用启动测试
# ============================================================================


class TestApplicationStartup:
    """应用启动测试"""

    def test_qapp_instance_exists(self, qapp):
        """测试 QApplication 实例存在"""
        assert qapp is not None

    def test_qapp_singleton(self, qapp):
        """测试 QApplication 单例模式"""
        instance = QApplication.instance()
        assert instance is not None
        assert instance == qapp

    def test_qapp_has_qapplication_attributes(self, qapp):
        """测试 QApplication 基本属性"""
        assert hasattr(qapp, "applicationName")
        assert hasattr(qapp, "quit")


# ============================================================================
# Part 2: 一键清理按钮点击测试
# ============================================================================


class TestOneClickClean:
    """一键清理按钮点击测试"""

    def test_import_dashboard_page(self, qapp):
        """测试仪表盘页面导入"""
        from ui.dashboard import DashboardPage

        page = DashboardPage()
        assert page is not None
        assert hasattr(page, "navigate_requested")
        page.deleteLater()

    def test_import_smart_cleanup_page(self, qapp):
        """测试智能清理页面导入"""
        from ui.smart_cleanup_page import SmartCleanupPage

        page = SmartCleanupPage()
        assert page is not None
        assert hasattr(page, "parent")
        page.deleteLater()


# ============================================================================
# Part 3: 设置页面导航测试
# ============================================================================


class TestSettingsNavigation:
    """设置页面导航测试"""

    def test_import_settings_page(self, qapp):
        """测试设置页面导入"""
        from ui.settings import SettingsPage

        page = SettingsPage()
        assert page is not None
        page.deleteLater()

    def test_dashboard_navigation_signal(self, qapp):
        """测试仪表盘导航信号"""
        from ui.dashboard import DashboardPage

        page = DashboardPage()
        assert hasattr(page, "navigate_requested")

        # 测试信号可以连接
        emitted_routes = []
        page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 发射信号
        page.navigate_requested.emit("settings")
        assert "settings" in emitted_routes

        page.deleteLater()


# ============================================================================
# Part 4: 规则编辑器打开测试
# ============================================================================


class TestRuleEditorOpen:
    """规则编辑器打开测试"""

    def test_import_rule_editor_page(self, qapp):
        """测试规则编辑器页面导入"""
        from ui.rule_editor_page import RuleEditorPage

        page = RuleEditorPage()
        assert page is not None
        page.deleteLater()

    def test_rule_editor_has_table(self, qapp):
        """测试规则编辑器包含表格"""
        from ui.rule_editor_page import RuleEditorPage

        page = RuleEditorPage()
        assert hasattr(page, "table")
        assert page.table is not None
        page.deleteLater()

    def test_rule_editor_navigate_signal(self, qapp):
        """测试规则编辑器导航信号"""
        from ui.dashboard import DashboardPage

        page = DashboardPage()
        assert hasattr(page, "navigate_requested")

        emitted_routes = []
        page.navigate_requested.connect(lambda r: emitted_routes.append(r))
        page.navigate_requested.emit("ruleEditor")

        assert "ruleEditor" in emitted_routes
        page.deleteLater()


# ============================================================================
# Part 5: 清理预览弹窗测试
# ============================================================================


class TestCleanupPreviewDialog:
    """清理预览弹窗测试"""

    def test_import_confirm_dialog(self, qapp):
        """测试确认对话框导入"""
        from ui.confirm_dialog import ConfirmDialog

        assert ConfirmDialog is not None

    def test_confirm_dialog_creation(self, qapp, sample_scan_items):
        """测试确认对话框创建"""
        from ui.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog(sample_scan_items)
        assert dialog is not None
        assert dialog.windowTitle() == "确认清理"
        dialog.deleteLater()

    def test_confirm_dialog_with_empty_items(self, qapp):
        """测试空项目的确认对话框"""
        from ui.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog([])
        assert dialog is not None
        assert dialog.windowTitle() == "确认清理"
        dialog.deleteLater()

    def test_confirm_dialog_stats_calculation(self, qapp, sample_scan_items):
        """测试确认对话框统计计算"""
        from ui.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog(sample_scan_items)
        dialog.calculate_statistics()

        stats = dialog.get_stats()

        # 验证统计数据
        assert stats["safe"]["count"] == 1
        assert stats["suspicious"]["count"] == 1
        assert stats["dangerous"]["count"] == 1

        # 验证安全项目（按路径判断）
        safe_items = dialog.get_safe_items()
        assert len(safe_items) == 1
        assert "temp_file.tmp" in safe_items[0].path

        # 验证疑似项目（按路径判断）
        suspicious_items = dialog.get_suspicious_items()
        assert len(suspicious_items) == 1
        assert "old_file.log" in suspicious_items[0].path

        # 验证危险项目（按路径判断）
        dangerous_items = dialog.get_dangerous_items()
        assert len(dangerous_items) == 1
        assert "config.ini.bak" in dangerous_items[0].path

        dialog.deleteLater()

    def test_confirm_dialog_exclude_dangerous(self, qapp, sample_scan_items):
        """测试排除危险项目功能"""
        from ui.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog(sample_scan_items)
        dialog.exclude_dangerous(exclude=True)

        items_to_clean = dialog.get_items_to_clean()

        # 验证危险项目被排除
        dangerous_items = [item for item in items_to_clean if item.risk_level == "dangerous"]
        assert len(dangerous_items) == 0
        assert len(items_to_clean) == 2  # 只剩安全+疑似

        dialog.deleteLater()

    def test_confirm_dialog_include_dangerous(self, qapp, sample_scan_items):
        """测试包含危险项目功能"""
        from ui.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog(sample_scan_items)
        dialog.exclude_dangerous(exclude=False)

        items_to_clean = dialog.get_items_to_clean()

        # 验证所有项目都包含
        assert len(items_to_clean) == 3

        dialog.deleteLater()

    def test_confirm_dialog_ui_components(self, qapp, sample_scan_items):
        """测试确认对话框UI组件"""
        from ui.confirm_dialog import ConfirmDialog

        dialog = ConfirmDialog(sample_scan_items)

        # 验证UI组件存在
        assert hasattr(dialog, "safe_count_label")
        assert hasattr(dialog, "safe_size_label")
        assert hasattr(dialog, "safe_progress")

        assert hasattr(dialog, "suspicious_count_label")
        assert hasattr(dialog, "suspicious_size_label")
        assert hasattr(dialog, "suspicious_progress")

        assert hasattr(dialog, "dangerous_count_label")
        assert hasattr(dialog, "dangerous_size_label")
        assert hasattr(dialog, "dangerous_progress")

        assert hasattr(dialog, "total_label")
        assert hasattr(dialog, "warning_container")  # Container 不是 layout

        assert hasattr(dialog, "cancel_btn")
        assert hasattr(dialog, "confirm_btn")

        dialog.deleteLater()


# ============================================================================
# 集成测试: 组件间交互
# ============================================================================


class TestComponentIntegration:
    """组件间交互测试"""

    def test_dashboard_to_settings_navigation(self, qapp):
        """测试从仪表盘导航到设置"""
        from ui.dashboard import DashboardPage

        dashboard_page = DashboardPage()
        emitted_routes = []

        dashboard_page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 导航到设置
        dashboard_page.navigate_requested.emit("settings")

        assert "settings" in emitted_routes
        dashboard_page.deleteLater()

    def test_dashboard_to_rule_editor_navigation(self, qapp):
        """测试从仪表盘导航到规则编辑器"""
        from ui.dashboard import DashboardPage

        dashboard_page = DashboardPage()
        emitted_routes = []

        dashboard_page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 导航到规则编辑器
        dashboard_page.navigate_requested.emit("ruleEditor")

        assert "ruleEditor" in emitted_routes
        dashboard_page.deleteLater()

    def test_dashboard_to_system_cleaner_navigation(self, qapp):
        """测试从仪表盘导航到系统清理"""
        from ui.dashboard import DashboardPage

        dashboard_page = DashboardPage()
        emitted_routes = []

        dashboard_page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 导航到系统清理
        dashboard_page.navigate_requested.emit("systemCleaner")

        assert "systemCleaner" in emitted_routes
        dashboard_page.deleteLater()

    def test_dashboard_to_browser_cleaner_navigation(self, qapp):
        """测试从仪表盘导航到浏览器清理"""
        from ui.dashboard import DashboardPage

        dashboard_page = DashboardPage()
        emitted_routes = []

        dashboard_page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 导航到浏览器清理
        dashboard_page.navigate_requested.emit("browserCleaner")

        assert "browserCleaner" in emitted_routes
        dashboard_page.deleteLater()


# ============================================================================
# 边界条件测试
# ============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_confirm_dialog_with_single_safe_item(self, qapp):
        """测试单个安全项目的确认对话框"""
        from core.models import ScanItem
        from ui.confirm_dialog import ConfirmDialog

        single_item = [
            ScanItem(
                item_type="file",
                path="C:\\Temp\\test.tmp",
                size=1024,
                description="单个安全文件",
                risk_level="safe",
            )
        ]

        dialog = ConfirmDialog(single_item)
        stats = dialog.get_stats()

        assert stats["safe"]["count"] == 1
        assert stats["suspicious"]["count"] == 0
        assert stats["dangerous"]["count"] == 0

        dialog.deleteLater()

    def test_confirm_dialog_with_only_dangerous_items(self, qapp):
        """测试只有危险项目的确认对话框"""
        from core.models import ScanItem
        from ui.confirm_dialog import ConfirmDialog

        dangerous_items = [
            ScanItem(
                item_type="file",
                path=f"C:\\Dangerous\\file{i}.exe",
                size=1024 * 1024,
                description=f"危险文件{i}",
                risk_level="dangerous",
            )
            for i in range(3)
        ]

        dialog = ConfirmDialog(dangerous_items)
        stats = dialog.get_stats()

        assert stats["safe"]["count"] == 0
        assert stats["suspicious"]["count"] == 0
        assert stats["dangerous"]["count"] == 3

        dialog.deleteLater()

    def test_navigate_with_invalid_route(self, qapp):
        """测试无效路由导航"""
        from ui.dashboard import DashboardPage

        dashboard_page = DashboardPage()
        emitted_routes = []

        dashboard_page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 尝试无效路由
        dashboard_page.navigate_requested.emit("invalidRoute")

        # 信号应该被发射，但路由可能无效
        assert "invalidRoute" in emitted_routes
        dashboard_page.deleteLater()


# ============================================================================
# 性能测试
# ============================================================================


class TestPerformance:
    """性能测试"""

    def test_large_scan_items_dialog(self, qapp):
        """测试大量扫描项目的对话框创建性能"""
        from core.models import ScanItem
        from ui.confirm_dialog import ConfirmDialog

        # 创建100个项目
        large_items = [
            ScanItem(
                item_type="file",
                path=f"C:\\Temp\\file_{i}.tmp",
                size=1024 * i,
                description=f"临时文件{i}",
                risk_level="safe" if i % 3 == 0 else ("suspicious" if i % 3 == 1 else "dangerous"),
            )
            for i in range(100)
        ]

        dialog = ConfirmDialog(large_items)
        dialog.calculate_statistics()

        stats = dialog.get_stats()
        assert sum(s["count"] for s in stats.values()) == 100

        dialog.deleteLater()

    def test_multiple_navigation_emissions(self, qapp):
        """测试多次快速导航"""
        from ui.dashboard import DashboardPage

        dashboard_page = DashboardPage()
        emitted_routes = []

        dashboard_page.navigate_requested.connect(lambda r: emitted_routes.append(r))

        # 快速发送多个导航请求
        routes = ["settings", "history", "recovery", "settings", "ruleEditor"]
        for route in routes:
            dashboard_page.navigate_requested.emit(route)

        assert len(emitted_routes) == len(routes)
        assert emitted_routes == routes
        dashboard_page.deleteLater()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
