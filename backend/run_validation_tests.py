#!/usr/bin/env python3
"""
Validation Sprint Test Runner
Runs various tests for Lucky Gas v3 pilot certification
"""
import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ValidationTestRunner:
    """Orchestrates validation testing for pilot certification"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        
    def setup_environment(self):
        """Set up test environment variables"""
        os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
        os.environ["ENVIRONMENT"] = "test"
        os.environ["TESTING"] = "true"
        os.environ["DISABLE_GOOGLE_APIS"] = "true"
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/luckygas_test"
        print("✅ Environment configured for testing")
        
    def run_unit_tests(self):
        """Run unit tests"""
        print("\n🧪 Running Unit Tests...")
        cmd = [
            "uv", "run", "pytest",
            "tests/unit",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=unit_test_report.json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.results["tests"]["unit"] = {
            "status": "passed" if result.returncode == 0 else "failed",
            "return_code": result.returncode
        }
        
        return result.returncode == 0
        
    def run_integration_tests(self):
        """Run integration tests"""
        print("\n🧪 Running Integration Tests...")
        
        # Test specific integration points
        test_files = [
            "tests/test_main.py::test_health_check",
            "tests/test_auth.py",
            "tests/test_customers.py",
            "tests/test_orders.py"
        ]
        
        passed = 0
        failed = 0
        
        for test_file in test_files:
            cmd = [
                "uv", "run", "pytest",
                test_file,
                "-v",
                "--tb=short"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                passed += 1
                print(f"  ✅ {test_file}")
            else:
                failed += 1
                print(f"  ❌ {test_file}")
                
        self.results["tests"]["integration"] = {
            "status": "passed" if failed == 0 else "failed",
            "passed": passed,
            "failed": failed,
            "total": len(test_files)
        }
        
        return failed == 0
        
    def run_api_tests(self):
        """Run API endpoint tests"""
        print("\n🧪 Running API Tests...")
        
        # Start test server in background
        print("  Starting test server...")
        server_process = subprocess.Popen(
            ["uv", "run", "uvicorn", "app.main:app", "--port", "8001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        import time
        time.sleep(5)
        
        try:
            # Test health endpoint
            import httpx
            client = httpx.Client(base_url="http://localhost:8001")
            
            # Health check
            response = client.get("/health")
            health_ok = response.status_code == 200
            
            # API docs
            response = client.get("/docs")
            docs_ok = response.status_code == 200
            
            self.results["tests"]["api"] = {
                "status": "passed" if health_ok and docs_ok else "failed",
                "health_check": health_ok,
                "api_docs": docs_ok
            }
            
            print(f"  Health Check: {'✅' if health_ok else '❌'}")
            print(f"  API Docs: {'✅' if docs_ok else '❌'}")
            
            return health_ok and docs_ok
            
        finally:
            # Stop server
            server_process.terminate()
            server_process.wait()
            
    def run_security_tests(self):
        """Run security validation tests"""
        print("\n🧪 Running Security Tests...")
        
        security_tests = [
            "tests/security/test_password_policy.py",
            "tests/security/test_account_lockout.py",
            "tests/security/test_security_middleware.py"
        ]
        
        passed = 0
        failed = 0
        
        for test_file in security_tests:
            if os.path.exists(test_file):
                cmd = [
                    "uv", "run", "pytest",
                    test_file,
                    "-v",
                    "--tb=short"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    passed += 1
                    print(f"  ✅ {test_file}")
                else:
                    failed += 1
                    print(f"  ❌ {test_file}")
            else:
                print(f"  ⚠️  {test_file} not found")
                
        self.results["tests"]["security"] = {
            "status": "passed" if failed == 0 else "failed",
            "passed": passed,
            "failed": failed,
            "total": len(security_tests)
        }
        
        return failed == 0
        
    def generate_report(self):
        """Generate validation test report"""
        print("\n📊 Generating Validation Report...")
        
        # Calculate summary
        for test_suite, results in self.results["tests"].items():
            self.results["summary"]["total"] += 1
            if results["status"] == "passed":
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1
                
        # Save JSON report
        with open("validation_test_report.json", "w") as f:
            json.dump(self.results, f, indent=2)
            
        # Create markdown report
        report_lines = [
            "# Validation Test Report",
            f"\n**Date**: {self.results['timestamp']}",
            f"\n**Overall Status**: {'✅ PASSED' if self.results['summary']['failed'] == 0 else '❌ FAILED'}",
            "\n## Test Results\n"
        ]
        
        for suite, results in self.results["tests"].items():
            status = "✅" if results["status"] == "passed" else "❌"
            report_lines.append(f"### {suite.title()} Tests {status}")
            report_lines.append(f"- Status: {results['status']}")
            
            if "passed" in results:
                report_lines.append(f"- Passed: {results['passed']}")
                report_lines.append(f"- Failed: {results['failed']}")
                
            report_lines.append("")
            
        # Summary
        report_lines.extend([
            "\n## Summary",
            f"- Total Test Suites: {self.results['summary']['total']}",
            f"- Passed: {self.results['summary']['passed']}",
            f"- Failed: {self.results['summary']['failed']}",
            f"- Success Rate: {(self.results['summary']['passed'] / max(self.results['summary']['total'], 1)) * 100:.1f}%"
        ])
        
        with open("VALIDATION_TEST_RESULTS.md", "w") as f:
            f.write("\n".join(report_lines))
            
        print("✅ Reports generated:")
        print("  - validation_test_report.json")
        print("  - VALIDATION_TEST_RESULTS.md")
        
def main():
    """Main entry point"""
    print("🚀 Lucky Gas v3 Validation Test Runner")
    print("=" * 50)
    
    runner = ValidationTestRunner()
    
    # Setup environment
    runner.setup_environment()
    
    # Run test suites
    test_suites = [
        ("Unit Tests", runner.run_unit_tests),
        ("Integration Tests", runner.run_integration_tests),
        ("API Tests", runner.run_api_tests),
        ("Security Tests", runner.run_security_tests)
    ]
    
    all_passed = True
    
    for suite_name, test_func in test_suites:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"  ❌ {suite_name} failed with error: {e}")
            all_passed = False
            runner.results["tests"][suite_name.lower().replace(" ", "_")] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Generate report
    runner.generate_report()
    
    # Final summary
    print("\n" + "=" * 50)
    print("VALIDATION TEST SUMMARY")
    print("=" * 50)
    
    if all_passed:
        print("✅ All validation tests passed!")
        sys.exit(0)
    else:
        print("❌ Some validation tests failed.")
        print("   See reports for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()