"""Fix relative imports in src/agent/*.py"""
from pathlib import Path

# Fix src/agent/*.py
agent_dir = Path("G:/docker/diskclean/src/agent")
for py_file in agent_dir.rglob("*.py"):
    content = py_file.read_text(encoding="utf-8")
    # Fix ..utils to utils
    new_content = content.replace("..utils.logger", "utils.logger")
    new_content = new_content.replace("..utils.debug_monitor", "utils.debug_monitor")
    new_content = new_content.replace("..utils.debug_tracker", "utils.debug_tracker")

    if new_content != content:
        py_file.write_text(new_content, encoding="utf-8")
        print(f"Fixed: {py_file}")

print("Done!")
