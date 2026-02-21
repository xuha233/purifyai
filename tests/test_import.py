#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单导入测试"""

import sys
import os

# 添加 src 到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from core.models_smart import (
        CleanupItem,
        RiskLevel
    )
    print("[OK] Imports successful")
    print(f"CleanupItem: {CleanupItem.__name__}")
    print(f"RiskLevel: {RiskLevel.__name__}")
    print(f"RiskLevel.SAFE: {RiskLevel.SAFE.value}")
    print(f"RiskLevel.DANGEROUS: {RiskLevel.DANGEROUS.value}")
    print(f"RiskLevel.SAFE.display_name: {RiskLevel.SAFE.get_display_name()}")

except ImportError as e:
    print(f"[ERROR] ImportError: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
