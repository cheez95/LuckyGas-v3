#!/usr/bin/env python
"""
Standalone test runner for financial module unit tests
"""
import subprocess
import sys
import os

def run_unit_tests():
    """Run unit tests in isolation without loading the full app"""
    print("=" * 60)
    print("Running Financial Module Unit Tests")
    print("=" * 60)
    
    # Set environment variables to disable app loading
    env = os.environ.copy()
    env['TESTING'] = 'true'
    env['SKIP_APP_IMPORT'] = 'true'
    
    # Test files that can run independently
    test_files = [
        "tests/services/test_invoice_service.py",
        "tests/services/test_payment_service.py", 
        "tests/services/test_financial_report_service.py",
        "tests/services/test_einvoice_service.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")
        print("-" * 40)
        
        # Run pytest for each file separately to isolate issues
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--no-header",
            "--no-summary",
            "-q"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                # Count passed tests
                passed = result.stdout.count(" PASSED")
                results[test_file] = {"status": "✅", "passed": passed}
                print(f"✅ {passed} tests passed")
            else:
                # Extract error info
                results[test_file] = {"status": "❌", "error": result.stderr[:200]}
                print(f"❌ Tests failed")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}...")
                    
        except Exception as e:
            results[test_file] = {"status": "❌", "error": str(e)}
            print(f"❌ Error running tests: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for test_file, result in results.items():
        if result["status"] == "✅":
            total_passed += 1
            print(f"✅ {test_file}: {result['passed']} tests passed")
        else:
            total_failed += 1
            print(f"❌ {test_file}: Failed")
    
    print(f"\nTotal: {total_passed} passed, {total_failed} failed")
    
    # Try to run without app imports
    if total_failed > 0:
        print("\n💡 Note: These are unit tests that should run independently.")
        print("   Import errors indicate the tests need to be run differently.")
        print("   Consider using: pytest --no-cov -k 'test_' directly")

if __name__ == "__main__":
    run_unit_tests()