#!/usr / bin / env python3
"""
Run Epic 7 Integration Tests for Lucky Gas v3
"""
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Test configuration
TEST_FILES = [
    "tests / integration / test_epic7_complete_flow.py",
    "tests / integration / test_route_optimization_integration.py",
    "tests / integration / test_websocket_realtime.py",
    "tests / integration / test_analytics_flow.py",
    "tests / integration / test_story_3_3_realtime_adjustment.py",
]


def run_test(test_file):
    """Run a single test file and return results"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print(f"{'='*60}")

    start_time = time.time()

    # Run pytest with coverage
    cmd = [
        "uv",
        "run",
        "pytest",
        test_file,
        "-v",
        "--tb=short",
        "--cov=app",
        "--cov - report=term - missing",
        "--junit - xml=test - results.xml",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    end_time = time.time()
    duration = end_time - start_time

    return {
        "file": test_file,
        "duration": duration,
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "passed": result.returncode == 0,
    }


def main():
    """Run all Epic 7 integration tests"""
    print("🚀 Lucky Gas v3 - Epic 7 Integration Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Set environment variables
    os.environ["TESTING"] = "True"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = (
        "postgresql + asyncpg://luckygas_test:luckygas_test_password@localhost:5433 / luckygas_test"
    )
    os.environ["REDIS_URL"] = "redis://localhost:6380 / 0"

    results = []
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    total_duration = 0

    # Run each test file
    for test_file in TEST_FILES:
        if Path(test_file).exists():
            result = run_test(test_file)
            results.append(result)
            total_duration += result["duration"]

            # Parse test counts from stdout
            if "passed" in result["stdout"]:
                # Extract test counts from pytest output
                import re

                match = re.search(r"(\d+) passed", result["stdout"])
                if match:
                    test_count = int(match.group(1))
                    total_tests += test_count
                    if result["passed"]:
                        passed_tests += test_count

            if not result["passed"]:
                # Count failed tests
                match = re.search(r"(\d+) failed", result["stdout"])
                if match:
                    failed_tests += int(match.group(1))
        else:
            print(f"⚠️ Test file not found: {test_file}")

    # Generate summary report
    print(f"\n{'='*60}")
    print("📊 TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total test files: {len(TEST_FILES)}")
    print(f"Files executed: {len(results)}")
    print(f"Total duration: {total_duration:.2f} seconds")
    print("\nTest Results:")
    print(f"  ✅ Passed: {passed_tests}")
    print(f"  ❌ Failed: {failed_tests}")
    print(f"  📋 Total: {total_tests}")

    # Save detailed results
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_duration": total_duration,
        "test_summary": {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
        },
        "test_files": results,
    }

    with open("epic7_test_report.json", "w") as f:
        json.dump(report_data, f, indent=2)

    print("\n📝 Detailed report saved to: epic7_test_report.json")

    # Exit with appropriate code
    exit_code = 0 if failed_tests == 0 else 1
    return exit_code


if __name__ == "__main__":
    exit(main())
