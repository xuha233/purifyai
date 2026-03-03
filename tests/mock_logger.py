# Mock logger for testing
import sys
from unittest.mock import MagicMock

class MockLogger:
    def __init__(self, name):
        self.name = name
    
    def info(self, msg, *args, **kwargs):
        pass
    
    def warning(self, msg, *args, **kwargs):
        pass
    
    def error(self, msg, *args, **kwargs):
        pass
    
    def debug(self, msg, *args, **kwargs):
        pass
    
    def critical(self, msg, *args, **kwargs):
        pass

def get_logger(name):
    return MockLogger(name)

# Mock utils.logger module
sys.modules['utils.logger'] = MagicMock()
sys.modules['utils'].logger = MagicMock()
sys.modules['utils'].logger.get_logger = get_logger
