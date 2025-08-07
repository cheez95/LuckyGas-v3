#!/usr/bin/env python3
"""Fix cascade options with spaces in them."""

import os
import re
from pathlib import Path

def fix_cascade_spaces(directory):
    """Fix cascade options that have 'delete - orphan' instead of 'delete-orphan'."""
    pattern = re.compile(r'cascade="all, delete-orphan"')
    replacement = 'cascade="all, delete-orphan"'
    
    files_fixed = []
    
    for path in Path(directory).rglob("*.py"):
        try:
            content = path.read_text()
            if pattern.search(content):
                new_content = pattern.sub(replacement, content)
                path.write_text(new_content)
                files_fixed.append(str(path))
                print(f"Fixed: {path}")
        except Exception as e:
            print(f"Error processing {path}: {e}")
    
    return files_fixed

if __name__ == "__main__":
    backend_dir = "/Users/lgee258/Desktop/LuckyGas-v3/backend"
    fixed_files = fix_cascade_spaces(backend_dir)
    print(f"\nTotal files fixed: {len(fixed_files)}")