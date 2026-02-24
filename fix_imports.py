"""Fix relative imports in src/core"""
import os

files = [
    "src/core/database.py",
    "src/core/agent_adapter.py",
    "src/core/ai_analyzer.py",
    "src/core/ai_client.py",
    "src/core/appdata_migration.py",
    "src/core/backup_manager.py",
    "src/core/cleaner.py",
    "src/core/cleanup_report_generator.py",
    "src/core/cost_controller.py",
    "src/core/database_migration.py",
    "src/core/depth_disk_scanner.py",
    "src/core/execution_engine.py",
    "src/core/recovery_manager.py",
    "src/core/restore_manager.py",
    "src/core/scanner.py",
    "src/core/smart_cleaner.py",
    "src/core/smart_scan_selector.py",
]

for file_path in files:
    if not os.path.exists(file_path):
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("from utils.logger", "from ..utils.logger")
    content = content.replace("from utils.debug_monitor", "from ..utils.debug_monitor")
    content = content.replace("from utils.debug_tracker", "from ..utils.debug_tracker")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] Fixed: {file_path}")

print("\n[OK] All imports fixed")
