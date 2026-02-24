"""Search for mouseReleaseEvent usage"""
from pathlib import Path

src_dir = Path("G:/docker/diskclean/src")

for py_file in src_dir.rglob("*.py"):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if "mouseReleaseEvent" in line or "mousePressEvent" in line:
                    # Show context
                    start = max(0, i - 3)
                    end = min(len(lines), i + 3)
                    print(f"\n--- {py_file}:{i} ---")
                    for j in range(start, end):
                        print(f"{j+1:4d}: {lines[j]}", end='')
    except Exception as e:
        pass

print("\nSearch completed!")
