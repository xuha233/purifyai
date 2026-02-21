#!/usr/bin/env python
"""Debug script to investigate config_manager issue"""
import json
import os

# Clear any cached modules
import sys
modules_to_clear = [k for k in sys.modules.keys() if k.startswith('core')]
for m in modules_to_clear:
    del sys.modules[m]

# Now import and test
from core.config_manager import get_config_manager

print("=" * 60)
print("DEBUG: Config Manager Investigation")
print("=" * 60)

cm = get_config_manager()

# Track file access
print(f"1. config_file: {cm.config_file}")
print(f"2. config_file exists: {os.path.exists(cm.config_file)}")

# Read file directly
with open(cm.config_file, 'r', encoding='utf-8') as f:
    file_contents = json.load(f)
print(f"3. File content ai_url: {file_contents.get('ai_url', 'NOT FOUND')}")

# Check internal config before get_ai_config
print(f"4. _config['ai_url'] before get_ai_config(): {cm._config.get('ai_url', 'NOT FOUND')}")

# Call get_ai_config
cfg = cm.get_ai_config()
print(f"5. get_ai_config()['api_url']: {cfg['api_url']}")

# Check internal config after get_ai_config
print(f"6. _config['ai_url'] after get_ai_config(): {cm._config.get('ai_url', 'NOT FOUND')}")

# Try direct get() calls
print(f"7. cm.get('ai_url', 'DEFAULT'): {cm.get('ai_url', 'DEFAULT')}")
print(f"8. cm.get('ai_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions'): {cm.get('ai_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')}")

# Check if there's another config file or cached data
print(f"9. cm id: {id(cm)}")

# Try creating a new config manager to test singleton
cm2 = get_config_manager()
print(f"10. Same instance (cm is cm2): {cm is cm2}")
print(f"11. cm2.get_ai_config()['api_url']: {cm2.get_ai_config()['api_url']}")

print("=" * 60)
