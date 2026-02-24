"""Search for .isNull() usage in Python files"""
from pathlib import Path
import re

src_dir = Path("G:/docker/diskclean/src")
py_files = list(src_dir.rglob("*.py"))

pattern = re.compile(r"\.isNull\(\)")

for py_file in py_files:
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if pattern.search(line):
                    print(f"{py_file}:{line_num}\t{line.strip()}")
    except Exception as e:
        pass

print("Search completed!")
