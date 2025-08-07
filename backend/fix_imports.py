#!/usr/bin/env python3
"""Fix incorrect imports in backend code."""

import os
import re
from pathlib import Path

def fix_imports(directory):
    """Fix incorrect imports throughout the codebase."""
    replacements = [
        # Fix get_db imports from wrong location
        (
            r'from app\.core\.database import get_db',
            'from app.api.deps import get_db'
        ),
        # Fix get_db_session references (they should be get_db)
        (
            r'get_db_session\(\)',
            'get_db()'
        ),
        # Fix async with get_db_session() pattern
        (
            r'async with get_db_session\(\) as db:',
            'async for db in get_db():'
        ),
        # Fix imports that include get_db with other imports from database
        (
            r'from app\.core\.database import get_db,\s*([^)]+)',
            r'from app.core.database import \1\nfrom app.api.deps import get_db'
        ),
        (
            r'from app\.core\.database import ([^,]+),\s*get_db',
            r'from app.core.database import \1\nfrom app.api.deps import get_db'
        ),
    ]
    
    files_fixed = []
    
    for path in Path(directory).rglob("*.py"):
        # Skip the fix script itself and the deps.py file
        if path.name == 'fix_imports.py' or path.name == 'deps.py':
            continue
            
        try:
            content = path.read_text()
            original_content = content
            
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
            
            if content != original_content:
                path.write_text(content)
                files_fixed.append(str(path))
                print(f"Fixed: {path}")
        except Exception as e:
            print(f"Error processing {path}: {e}")
    
    return files_fixed

if __name__ == "__main__":
    backend_dir = "/Users/lgee258/Desktop/LuckyGas-v3/backend"
    fixed_files = fix_imports(backend_dir)
    print(f"\nTotal files fixed: {len(fixed_files)}")