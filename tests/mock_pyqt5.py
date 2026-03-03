# Mock PyQt5 for testing
import sys
from unittest.mock import MagicMock

# Mock PyQt5 modules
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()
