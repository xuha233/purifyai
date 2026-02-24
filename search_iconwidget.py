"""Search for IconWidget usage"""
from pathlib import Path
import re

src_dir = Path("G:/docker/diskclean/src")
py_files = list(src_dir.rglob("*.py"))

pattern1 = re.compile(r"IconWidget\(\)")
pattern2 = re.compile(r"\.setIcon\(.*IconWidget")

for py_file in py_files:
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "IconWidget" in content:
                print(f"\n--- {py_file} ---")
                for line_num, line in enumerate(content.split('\n'), 1):
                    if "IconWidget" in line:
                        print(f"{line_num:4d}: {line}")
    except Exception as e:
        pass

print("\nSearch completed!")
