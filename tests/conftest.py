# -*- coding: utf-8 -*-
import sys
import os
import pytest
from unittest.mock import MagicMock, Mock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Mock PyQt5 before any imports
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()

# Mock all utils modules
utils_modules = [
    'utils.logger',
    'utils.debug_tracker', 
    'utils.debug_monitor',
    'utils.progress_bar',
    'utils.progress_estimator',
    'utils.realtime_logger',
    'utils.scan_prechecker',
    'utils.scan_result_exporter',
    'utils.startup',
    'utils.time_utils'
]

for module_name in utils_modules:
    sys.modules[module_name] = MagicMock()
    # Add get_logger function
    if module_name == 'utils.logger':
        sys.modules[module_name].get_logger = lambda name: Mock()
