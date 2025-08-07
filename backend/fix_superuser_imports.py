#!/usr/bin/env python3
"""Fix incorrect imports of get_current_active_superuser."""

import os
import re
from pathlib import Path

def fix_superuser_imports(directory):
    """Fix incorrect imports of get_current_active_superuser."""
    
    files_fixed = []
    
    for path in Path(directory).rglob("*.py"):
        try:
            content = path.read_text()
            original_content = content
            
            # Pattern to find imports from auth_deps.security that include get_current_active_superuser
            pattern = re.compile(
                r'from app\.api\.auth_deps\.security import (.*?)(?=\n)',
                re.MULTILINE
            )
            
            def process_import(match):
                imports = match.group(1)
                import_list = [imp.strip() for imp in imports.split(',')]
                
                # Separate the imports
                auth_deps_imports = []
                deps_imports = []
                
                for imp in import_list:
                    if 'get_current_active_superuser' in imp or 'get_current_user' in imp:
                        deps_imports.append(imp)
                    else:
                        auth_deps_imports.append(imp)
                
                # Build the new import statements
                result = ""
                if auth_deps_imports:
                    result = f"from app.api.auth_deps.security import {', '.join(auth_deps_imports)}"
                if deps_imports:
                    if result:
                        result += "\n"
                    result += f"from app.api.deps import {', '.join(deps_imports)}"
                
                return result if result else match.group(0)
            
            # Apply the fix
            new_content = pattern.sub(process_import, content)
            
            if new_content != original_content:
                path.write_text(new_content)
                files_fixed.append(str(path))
                print(f"Fixed: {path}")
                
        except Exception as e:
            print(f"Error processing {path}: {e}")
    
    return files_fixed

if __name__ == "__main__":
    backend_dir = "/Users/lgee258/Desktop/LuckyGas-v3/backend"
    fixed_files = fix_superuser_imports(backend_dir)
    print(f"\nTotal files fixed: {len(fixed_files)}")