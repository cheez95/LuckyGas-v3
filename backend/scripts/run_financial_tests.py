#!/usr/bin/env python
"""
Run all financial module unit tests
"""
import subprocess
import sys
import os

def run_tests():
    """Run all financial module tests and display results"""
    print("=" * 60)
    print("Lucky Gas Financial Module Test Suite")
    print("=" * 60)
    
    # Change to backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(backend_dir)
    
    # Test files
    test_files = [
        "tests/services/test_invoice_service.py",
        "tests/services/test_payment_service.py",
        "tests/services/test_financial_report_service.py",
        "tests/services/test_einvoice_service.py"
    ]
    
    # Run pytest with coverage for financial modules
    cmd = [
        "uv", "run", "pytest",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--cov=app.services.invoice_service",
        "--cov=app.services.payment_service",
        "--cov=app.services.financial_report_service",
        "--cov=app.services.einvoice_service",
        "--cov=app.models.invoice",
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov/financial",  # HTML report
        "--cov-fail-under=80",  # Fail if coverage < 80%
        *test_files
    ]
    
    print("\nRunning financial module tests...\n")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ All financial module tests passed!")
            print("=" * 60)
            print("\n📊 Coverage report generated at: htmlcov/financial/index.html")
        else:
            print("\n" + "=" * 60)
            print("❌ Some tests failed. Please check the output above.")
            print("=" * 60)
            sys.exit(1)
            
    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install test dependencies:")
        print("   uv pip install pytest pytest-asyncio pytest-cov")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()