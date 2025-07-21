#!/usr/bin/env python3
"""
Verify security changes have been properly implemented
"""
import os
import sys
import re
from pathlib import Path

def check_file_for_pattern(file_path: Path, pattern: str, should_exist: bool = False) -> tuple[bool, str]:
    """Check if a file contains a pattern"""
    try:
        content = file_path.read_text()
        found = bool(re.search(pattern, content, re.MULTILINE | re.IGNORECASE))
        
        if should_exist and not found:
            return False, f"Pattern '{pattern}' NOT FOUND in {file_path}"
        elif not should_exist and found:
            return False, f"Pattern '{pattern}' FOUND in {file_path} (should not exist)"
        else:
            return True, f"✓ {file_path.name}"
    except Exception as e:
        return False, f"Error reading {file_path}: {e}"

def main():
    print("🔍 Verifying Security Changes...\n")
    
    backend_dir = Path(__file__).parent
    all_passed = True
    
    # 1. Check config.py for removed hardcoded credentials
    print("1. Checking config.py for hardcoded credentials:")
    config_file = backend_dir / "app/core/config.py"
    
    # Should NOT have hardcoded passwords
    checks = [
        (r'FIRST_SUPERUSER_PASSWORD:\s*str\s*=\s*"admin123"', False, "No hardcoded admin password"),
        (r'POSTGRES_PASSWORD:\s*str\s*=\s*"luckygas123"', False, "No hardcoded DB password"),
        (r'SECRET_KEY:\s*str\s*=\s*secrets\.token_urlsafe', False, "No runtime SECRET_KEY generation"),
    ]
    
    # Should have proper validation
    checks.extend([
        (r'SECRET_KEY:\s*str\s*=\s*Field\(\.\.\..*min_length=32', True, "SECRET_KEY requires min length"),
        (r'POSTGRES_PASSWORD:\s*str\s*=\s*Field\(\.\.\.', True, "POSTGRES_PASSWORD is required"),
        (r'FIRST_SUPERUSER_PASSWORD:\s*str\s*=\s*Field\(\.\.\..*min_length=8', True, "Admin password requires min length"),
        (r'POSTGRES_PORT:\s*int\s*=\s*Field\(5433', True, "Database port is configurable"),
    ])
    
    for pattern, should_exist, desc in checks:
        passed, msg = check_file_for_pattern(config_file, pattern, should_exist)
        print(f"  {'✅' if passed else '❌'} {desc}")
        if not passed:
            print(f"     {msg}")
            all_passed = False
    
    # 2. Check .env.example exists
    print("\n2. Checking .env.example:")
    env_example = backend_dir / ".env.example"
    if env_example.exists():
        print("  ✅ .env.example exists")
        # Check it has proper placeholders
        content = env_example.read_text()
        if "your-secret-key-here" in content and "your-secure-database-password" in content:
            print("  ✅ Contains proper placeholder values")
        else:
            print("  ❌ Missing proper placeholders")
            all_passed = False
    else:
        print("  ❌ .env.example NOT FOUND")
        all_passed = False
    
    # 3. Check main.py for CORS and HTTPS
    print("\n3. Checking main.py for security middleware:")
    main_file = backend_dir / "app/main.py"
    
    main_checks = [
        (r'allow_methods=\["GET",\s*"POST",\s*"PUT",\s*"DELETE",\s*"OPTIONS"\]', True, "CORS methods restricted"),
        (r'allow_headers=\["Authorization",\s*"Content-Type",\s*"X-Request-ID"\]', True, "CORS headers restricted"),
        (r'allow_methods=\["\*"\]', False, "No wildcard CORS methods"),
        (r'allow_headers=\["\*"\]', False, "No wildcard CORS headers"),
        (r'HTTPSRedirectMiddleware', True, "HTTPS redirect imported"),
        (r'app\.add_middleware\(HTTPSRedirectMiddleware\)', True, "HTTPS redirect middleware added"),
    ]
    
    for pattern, should_exist, desc in main_checks:
        passed, msg = check_file_for_pattern(main_file, pattern, should_exist)
        print(f"  {'✅' if passed else '❌'} {desc}")
        if not passed:
            print(f"     {msg}")
            all_passed = False
    
    # 4. Check google_cloud_config.py
    print("\n4. Checking google_cloud_config.py:")
    gcp_config = backend_dir / "app/core/google_cloud_config.py"
    
    gcp_checks = [
        (r'async def get_maps_api_key', True, "Async API key method exists"),
        (r'get_api_key_manager', True, "Uses API Key Manager"),
        (r'self\.maps_api_key = settings\.GOOGLE_MAPS_API_KEY', False, "No direct API key storage"),
    ]
    
    for pattern, should_exist, desc in gcp_checks:
        passed, msg = check_file_for_pattern(gcp_config, pattern, should_exist)
        print(f"  {'✅' if passed else '❌'} {desc}")
        if not passed:
            print(f"     {msg}")
            all_passed = False
    
    # 5. Check .gitignore
    print("\n5. Checking .gitignore:")
    gitignore = backend_dir.parent / ".gitignore"
    
    gitignore_checks = [
        (r'^\.env$', True, ".env is ignored"),
        (r'^\.env\.\*$', True, ".env.* files are ignored"),
        (r'^!\.env\.example$', True, ".env.example is NOT ignored"),
    ]
    
    for pattern, should_exist, desc in gitignore_checks:
        passed, msg = check_file_for_pattern(gitignore, pattern, should_exist)
        print(f"  {'✅' if passed else '❌'} {desc}")
        if not passed:
            print(f"     {msg}")
            all_passed = False
    
    # 6. Environment validation
    print("\n6. Testing environment validation:")
    try:
        # Set minimal required env vars for testing
        test_env = {
            'SECRET_KEY': 'test-key-that-is-at-least-32-chars-long',
            'POSTGRES_PASSWORD': 'test-password',
            'FIRST_SUPERUSER_PASSWORD': 'test-admin-password'
        }
        
        # Only set if not already set (don't override real values)
        for key, value in test_env.items():
            if not os.getenv(key):
                os.environ[key] = value
        
        # Try to import and validate
        from app.core.env_validation import validate_environment
        try:
            validate_environment()
            print("  ✅ Environment validation passes")
        except SystemExit:
            print("  ❌ Environment validation failed")
            all_passed = False
    except Exception as e:
        print(f"  ❌ Could not test environment validation: {e}")
        all_passed = False
    
    # Final summary
    print("\n" + "="*50)
    if all_passed:
        print("✅ ALL SECURITY CHECKS PASSED!")
        print("\nNext steps:")
        print("1. Create a real .env file based on .env.example")
        print("2. Generate a strong SECRET_KEY:")
        print("   python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        print("3. Set all required environment variables")
        print("4. Test the application startup")
        return 0
    else:
        print("❌ SOME SECURITY CHECKS FAILED!")
        print("\nPlease fix the issues above before adding API keys.")
        return 1

if __name__ == "__main__":
    sys.exit(main())