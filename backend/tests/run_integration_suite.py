#!/usr/bin/env python3
"""
Run Integration Test Suite for Lucky Gas v3

This script sets up the proper test environment and runs all integration tests.
"""
import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

# Set up test environment variables BEFORE any imports
os.environ.update({
    "TESTING": "True",
    "ENVIRONMENT": "test",
    "DATABASE_URL": "postgresql+asyncpg://luckygas_test:test_password_secure_123@localhost:5433/luckygas_test",
    "POSTGRES_SERVER": "localhost",
    "POSTGRES_USER": "luckygas_test",
    "POSTGRES_PASSWORD": "test_password_secure_123",
    "POSTGRES_DB": "luckygas_test",
    "POSTGRES_PORT": "5433",
    "REDIS_URL": "redis://:test_redis_password_123@localhost:6380/1",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6380",
    "REDIS_PASSWORD": "test_redis_password_123",
    "REDIS_DB": "1",
    "SECRET_KEY": "test-secret-key-min-32-chars-required-for-testing-only",
    "JWT_SECRET_KEY": "test-jwt-secret-key-min-32-chars-for-testing-only",
    "FIRST_SUPERUSER": "admin@test.luckygas.tw",
    "FIRST_SUPERUSER_PASSWORD": "TestAdmin123!",
    "GCP_PROJECT_ID": "test-lucky-gas",
    "GOOGLE_MAPS_API_KEY": "AIzaSyD-test-key-for-testing-only123456",
    "STORAGE_ENDPOINT": "http://localhost:9000",
    "STORAGE_ACCESS_KEY": "minioadmin",
    "STORAGE_SECRET_KEY": "minioadmin123",
    "GCS_BUCKET": "lucky-gas-storage",
    "TWILIO_ACCOUNT_SID": "test_account_sid",
    "TWILIO_AUTH_TOKEN": "test_auth_token",
    "TWILIO_PHONE_NUMBER": "+1234567890",
    "EINVOICE_API_URL": "http://localhost:8003",
    "EINVOICE_API_KEY": "test_einvoice_key"
})

# Test suite configuration
TEST_SUITES = {
    "Epic 7 Integration": [
        "tests/integration/test_epic7_complete_flow.py",
        "tests/integration/test_route_optimization_integration.py",
        "tests/integration/test_websocket_realtime.py",
        "tests/integration/test_analytics_flow.py",
        "tests/integration/test_story_3_3_realtime_adjustment.py"
    ],
    "Core API": [
        "tests/test_auth.py",
        "tests/test_customers.py",
        "tests/test_orders.py",
        "tests/test_routes.py"
    ],
    "Advanced Features": [
        "tests/test_credit_limit.py",
        "tests/test_order_templates.py",
        "tests/test_data_validator.py"
    ]
}

class TestRunner:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
    def run_test_file(self, test_file: str) -> dict:
        """Run a single test file and return results"""
        print(f"\n{'='*60}")
        print(f"📄 Running: {test_file}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Run pytest
        cmd = [
            sys.executable, "-m", "pytest", test_file,
            "-v", "--tb=short",
            "--json-report", "--json-report-file=test_result.json",
            "-q"  # Quiet mode for cleaner output
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        
        # Parse test results
        test_summary = self.parse_test_output(result.stdout)
        
        return {
            "file": test_file,
            "duration": duration,
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "summary": test_summary
        }
    
    def parse_test_output(self, output: str) -> dict:
        """Parse pytest output to extract test counts"""
        import re
        
        summary = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Look for pytest summary line
        patterns = {
            "passed": r"(\d+) passed",
            "failed": r"(\d+) failed",
            "skipped": r"(\d+) skipped",
            "errors": r"(\d+) error"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                summary[key] = int(match.group(1))
        
        return summary
    
    def run_suite(self, suite_name: str, test_files: list):
        """Run a test suite"""
        print(f"\n{'#'*60}")
        print(f"🧪 Running Suite: {suite_name}")
        print(f"{'#'*60}")
        
        suite_results = []
        suite_start = time.time()
        
        for test_file in test_files:
            if Path(test_file).exists():
                result = self.run_test_file(test_file)
                suite_results.append(result)
                
                # Update totals
                summary = result["summary"]
                self.total_tests += sum(summary.values())
                self.passed_tests += summary["passed"]
                self.failed_tests += summary["failed"]
                self.skipped_tests += summary["skipped"]
            else:
                print(f"⚠️  Test file not found: {test_file}")
        
        suite_duration = time.time() - suite_start
        
        self.results[suite_name] = {
            "duration": suite_duration,
            "test_files": suite_results
        }
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print("📊 INTEGRATION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Execution Time: {total_duration:.2f} seconds")
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n📈 Test Summary:")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  ✅ Passed: {self.passed_tests}")
        print(f"  ❌ Failed: {self.failed_tests}")
        print(f"  ⏭️  Skipped: {self.skipped_tests}")
        
        if self.total_tests > 0:
            pass_rate = (self.passed_tests / self.total_tests) * 100
            print(f"  📊 Pass Rate: {pass_rate:.1f}%")
        
        print(f"\n🔍 Suite Results:")
        for suite_name, suite_data in self.results.items():
            print(f"\n  {suite_name}:")
            print(f"    Duration: {suite_data['duration']:.2f}s")
            
            for test_file in suite_data["test_files"]:
                status = "✅" if test_file["passed"] else "❌"
                summary = test_file["summary"]
                print(f"    {status} {Path(test_file['file']).name}: "
                      f"{summary['passed']} passed, {summary['failed']} failed")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": total_duration,
            "summary": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "skipped": self.skipped_tests,
                "pass_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            "suites": self.results
        }
        
        with open("integration_test_results.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📝 Detailed report saved to: integration_test_results.json")
        
        # Create markdown report
        self.create_markdown_report(report_data)
        
        return self.failed_tests == 0
    
    def create_markdown_report(self, report_data: dict):
        """Create markdown report for documentation"""
        md_content = f"""# Integration Test Results

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Total Tests**: {report_data['summary']['total']}
- **Passed**: {report_data['summary']['passed']} ✅
- **Failed**: {report_data['summary']['failed']} ❌
- **Skipped**: {report_data['summary']['skipped']} ⏭️
- **Pass Rate**: {report_data['summary']['pass_rate']:.1f}%
- **Total Duration**: {report_data['total_duration']:.2f} seconds

## Test Results by Suite

"""
        
        for suite_name, suite_data in report_data['suites'].items():
            md_content += f"\n### {suite_name}\n\n"
            md_content += f"**Duration**: {suite_data['duration']:.2f} seconds\n\n"
            md_content += "| Test File | Status | Passed | Failed | Duration |\n"
            md_content += "|-----------|--------|--------|--------|----------|\n"
            
            for test in suite_data['test_files']:
                status = "✅ Pass" if test['passed'] else "❌ Fail"
                summary = test['summary']
                file_name = Path(test['file']).name
                md_content += f"| {file_name} | {status} | {summary['passed']} | {summary['failed']} | {test['duration']:.2f}s |\n"
        
        md_content += """
## Test Environment

- **Database**: PostgreSQL 15 with PostGIS (Test instance on port 5433)
- **Cache**: Redis 7 (Test instance on port 6380)
- **Storage**: MinIO (S3-compatible, port 9000)
- **Email**: MailHog (SMTP testing, port 1025)

## Coverage Report

Coverage data available in `htmlcov/index.html` after running with coverage enabled.

## Recommendations

1. **Failed Tests**: Review and fix any failing tests before deployment
2. **Performance**: Monitor test execution times for regression
3. **Coverage**: Aim for >80% code coverage on critical paths
4. **Integration**: Ensure all external service mocks are properly configured
"""
        
        with open("INTEGRATION_TEST_RESULTS.md", "w") as f:
            f.write(md_content)
        
        print("📄 Markdown report saved to: INTEGRATION_TEST_RESULTS.md")

def main():
    """Main entry point"""
    print("🚀 Lucky Gas v3 - Integration Test Suite")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'test')}")
    print(f"Database: {os.environ.get('POSTGRES_SERVER', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5433')}")
    
    runner = TestRunner()
    
    # Run only Epic 7 Integration tests as requested
    runner.run_suite("Epic 7 Integration", TEST_SUITES["Epic 7 Integration"])
    
    # Generate report
    success = runner.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()