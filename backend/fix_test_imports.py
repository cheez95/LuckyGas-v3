#!/usr/bin/env python3
"""
Fix common test import and configuration issues
"""
import os
import re
import sys
from typing import List, Tuple


class TestImportFixer:
    """Fixes common import issues in test files"""
    
    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.errors = []
    
    def fix_google_maps_import(self, content: str) -> str:
        """Fix deprecated maps_api_key access"""
        # Old pattern: settings.maps_api_key
        # New pattern: settings.GOOGLE_MAPS_API_KEY or getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        
        patterns = [
            (r'settings\.maps_api_key', 'getattr(settings, "GOOGLE_MAPS_API_KEY", "")'),
            (r'config\.maps_api_key', 'getattr(config, "GOOGLE_MAPS_API_KEY", "")'),
        ]
        
        for old, new in patterns:
            if re.search(old, content):
                content = re.sub(old, new, content)
                self.fixes_applied += 1
        
        return content
    
    def fix_async_fixtures(self, content: str) -> str:
        """Fix async fixture declarations"""
        # Ensure pytest_asyncio is used for async fixtures
        if '@pytest.fixture' in content and 'async def' in content:
            if 'import pytest_asyncio' not in content:
                # Add import
                import_line = "import pytest_asyncio\n"
                if 'import pytest' in content:
                    content = content.replace('import pytest\n', f'import pytest\n{import_line}')
                else:
                    content = import_line + content
            
            # Replace @pytest.fixture with @pytest_asyncio.fixture for async functions
            lines = content.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if '@pytest.fixture' in line and i + 1 < len(lines) and 'async def' in lines[i + 1]:
                    new_lines.append(line.replace('@pytest.fixture', '@pytest_asyncio.fixture'))
                    self.fixes_applied += 1
                else:
                    new_lines.append(line)
                i += 1
            
            content = '\n'.join(new_lines)
        
        return content
    
    def fix_event_loop_scope(self, content: str) -> str:
        """Fix event loop scope issues"""
        # Remove duplicate event_loop fixtures
        if content.count('def event_loop') > 1:
            # Keep only the first one
            parts = content.split('def event_loop')
            if len(parts) > 2:
                # Find the end of the first event_loop function
                first_part = parts[0] + 'def event_loop' + parts[1]
                # Remove subsequent definitions
                remaining = ''.join(parts[2:])
                remaining = re.sub(r'@pytest\.fixture.*?\ndef event_loop.*?(?=\n@|\nclass|\ndef|\n\n|\Z)', '', remaining, flags=re.DOTALL)
                content = first_part + remaining
                self.fixes_applied += 1
        
        return content
    
    def fix_import_paths(self, content: str) -> str:
        """Fix common import path issues"""
        # Fix relative imports in tests
        patterns = [
            (r'from \.\. import', 'from app import'),
            (r'from \.\.\.', 'from app.'),
            (r'from tests\.fixtures import', 'from tests.fixtures.test_data import'),
        ]
        
        for old, new in patterns:
            if re.search(old, content):
                content = re.sub(old, new, content)
                self.fixes_applied += 1
        
        return content
    
    def add_missing_markers(self, filepath: str, content: str) -> str:
        """Add missing test markers based on file location"""
        if 'pytest.mark' not in content:
            marker = None
            
            if '/e2e/' in filepath:
                marker = '@pytest.mark.e2e'
            elif '/chaos/' in filepath:
                marker = '@pytest.mark.chaos'
            elif '/integration/' in filepath:
                marker = '@pytest.mark.integration'
            elif '/unit/' in filepath:
                marker = '@pytest.mark.unit'
            
            if marker:
                # Add marker to test classes and functions
                lines = content.split('\n')
                new_lines = []
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if line.strip().startswith('class Test') or line.strip().startswith('def test_'):
                        # Insert marker before the class/function
                        new_lines.insert(-1, marker)
                        self.fixes_applied += 1
                
                content = '\n'.join(new_lines)
        
        return content
    
    def process_file(self, filepath: str) -> bool:
        """Process a single test file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply fixes
            content = self.fix_google_maps_import(content)
            content = self.fix_async_fixtures(content)
            content = self.fix_event_loop_scope(content)
            content = self.fix_import_paths(content)
            content = self.add_missing_markers(filepath, content)
            
            # Write back if changed
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Fixed: {filepath}")
                return True
            
            return False
            
        except Exception as e:
            self.errors.append((filepath, str(e)))
            return False
    
    def fix_all_tests(self, test_dir: str = "tests") -> None:
        """Fix all test files in the directory"""
        test_files = []
        
        # Find all test files
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        
        print(f"Found {len(test_files)} test files to process")
        
        # Process each file
        for filepath in test_files:
            self.files_processed += 1
            self.process_file(filepath)
        
        # Summary
        print(f"\n{'='*50}")
        print("IMPORT FIX SUMMARY")
        print(f"{'='*50}")
        print(f"Files processed: {self.files_processed}")
        print(f"Fixes applied: {self.fixes_applied}")
        print(f"Errors: {len(self.errors)}")
        
        if self.errors:
            print("\nErrors encountered:")
            for filepath, error in self.errors:
                print(f"  - {filepath}: {error}")


def main():
    """Main entry point"""
    print("🔧 Lucky Gas v3 - Test Import Fixer\n")
    
    fixer = TestImportFixer()
    fixer.fix_all_tests()
    
    # Additional quick fixes
    print("\n🔧 Applying additional fixes...")
    
    # Ensure test environment is set
    env_file = ".env.test"
    if not os.path.exists(env_file):
        print(f"Creating {env_file}...")
        with open(env_file, 'w') as f:
            f.write("""# Test environment configuration
ENVIRONMENT=test
TESTING=true
DISABLE_GOOGLE_APIS=true
DATABASE_URL=postgresql://test:test@localhost:5432/luckygas_test
REDIS_URL=redis://localhost:6379/1
JWT_SECRET_KEY=test-secret-key-for-testing-only
GOOGLE_MAPS_API_KEY=test-key
""")
        print(f"✅ Created {env_file}")
    
    print("\n✅ Test import fixes complete!")
    print("Run './run_all_tests.sh' to execute the test suite")


if __name__ == "__main__":
    main()