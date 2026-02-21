# 测试配置文件


"""
PurifyAI 项目 pytest 配置
"""

import os
import sys
import pytest

# 添加 src 目录到 Python 路径
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_dir)


@pytest.fixture
def setup_test_database(tmp_path):
    """测试数据库 fixture"""
    from core.database import get_database
    db_path = os.path.join(tmp_path, 'test_purifyai.db')
    # 这里可以设置测试数据库路径
    return db_path


@pytest.fixture
def sample_cleanup_items():
    """示例清理项 fixture"""
    from core.models_smart import CleanupItem

    return [
        CleanupItem(
            item_id=1,
            path="C:/Temp/Cache/file1.tmp",
            size=1024,
            item_type="file",
            original_risk="suspicious",
            ai_risk="safe"
        ),
        CleanupItem(
            item_id=2,
            path="C:/Temp/Logs/app.log",
            size=2048,
            item_type="file",
            original_risk="safe",
            ai_risk="safe"
        ),
        CleanupItem(
            item_id=3,
            path="C:/Users/test/Documents/report.docx",
            size=5242880,
            item_type="file",
            original_risk="dangerous",
            ai_risk="dangerous"
        )
    ]


@pytest.fixture
def mock_scan_result_factory():
    """模拟扫描结果工厂"""
    from core.models_smart import CleanupPlan

    def _create(scan_type='system', scan_target='C:/Temp', num_items=10):
        items = []
        for i in range(num_items):
            items.append(
                CleanupItem(
                    item_id=i + 1,
                    path=f"C:/Temp/test{i}.tmp",
                    size=1024 * (i + 1),
                    item_type='file',
                    original_risk='suspicious',
                    ai_risk='safe' if i < 8 else 'suspicious'
                )
            )
        return CleanupPlan.create(scan_type, scan_target, items)

    return _create


@pytest.fixture
def test_logger(caplog):
    """测试日志 fixture"""
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    yield caplog
    caplog.clear()
