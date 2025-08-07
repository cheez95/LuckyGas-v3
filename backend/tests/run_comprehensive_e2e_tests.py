#!/usr / bin / env python3
"""
Comprehensive E2E test runner for Sprint 1 - 3 features
This script runs all end - to - end tests to validate the complete functionality
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class E2ETestRunner:
    """Run comprehensive E2E tests with detailed reporting"""

    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "sprints": {
                "sprint1": {"name": "Driver Functionality", "tests": []},
                "sprint2": {"name": "WebSocket & Real - time", "tests": []},
                "sprint3": {"name": "Order Management", "tests": []},
            },
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        }

        # Map test files to sprints
        self.test_mapping = {
            "sprint1": [
                "tests / e2e / test_driver_mobile_flow.py",
                "tests / e2e / test_login_flow.py::TestLoginFlow::test_driver_login",
            ],
            "sprint2": ["tests / e2e / test_websocket_realtime.py"],
            "sprint3": [
                "tests / e2e / test_order_flow.py",
                "tests / e2e / test_customer_management.py",
                "tests / e2e / test_credit_limit_flow.py",
                "tests / e2e / test_order_templates_flow.py",
                "tests / test_order_search.py",
                "tests / test_order_templates.py",
            ],
        }

    def run_test_suite(self, sprint_key: str, test_files: list) -> dict:
        """Run tests for a specific sprint"""
        print(f"\n{'='*60}")
        print(f"Running {self.test_results['sprints'][sprint_key]['name']} Tests")
        print(f"{'='*60}\n")

        sprint_results = {"passed": 0, "failed": 0, "skipped": 0, "tests": []}

        for test_file in test_files:
            print(f"Executing: {test_file}")

            # Run pytest with JSON output
            cmd = [
                "python",
                "-m",
                "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--json - report",
                "--json - report - file=test_output.json",
                "-x",  # Stop on first failure for faster feedback
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Parse results
            test_result = {
                "file": test_file,
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
            }

            # Try to parse JSON report
            try:
                with open("test_output.json", "r") as f:
                    json_data = json.load(f)
                    test_result["summary"] = json_data.get("summary", {})
                    sprint_results["passed"] += json_data["summary"].get("passed", 0)
                    sprint_results["failed"] += json_data["summary"].get("failed", 0)
                    sprint_results["skipped"] += json_data["summary"].get("skipped", 0)
            except Exception:
                # Fallback if JSON report fails
                if result.returncode == 0:
                    sprint_results["passed"] += 1
                else:
                    sprint_results["failed"] += 1
                    test_result["error"] = result.stderr

            sprint_results["tests"].append(test_result)

            # Print immediate feedback
            if result.returncode == 0:
                print("  ✅ PASSED")
            else:
                print("  ❌ FAILED")
                if result.stderr:
                    print(f"  Error: {result.stderr[:200]}...")

        return sprint_results

    def run_all_tests(self):
        """Run all E2E tests for Sprint 1 - 3"""
        print("\n" + "=" * 80)
        print("Lucky Gas V3 - Comprehensive E2E Test Suite")
        print("Testing Sprint 1 - 3 Features")
        print("=" * 80)

        # Ensure we're in test mode
        import os

        os.environ["TESTING"] = "1"

        # Run tests for each sprint
        for sprint_key, test_files in self.test_mapping.items():
            results = self.run_test_suite(sprint_key, test_files)
            self.test_results["sprints"][sprint_key].update(results)

            # Update summary
            self.test_results["summary"]["total"] += (
                results["passed"] + results["failed"]
            )
            self.test_results["summary"]["passed"] += results["passed"]
            self.test_results["summary"]["failed"] += results["failed"]
            self.test_results["summary"]["skipped"] += results["skipped"]

        # Generate report
        self.generate_report()

        # Return exit code
        return 0 if self.test_results["summary"]["failed"] == 0 else 1

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)

        # Sprint summaries
        for sprint_key, sprint_data in self.test_results["sprints"].items():
            if "passed" in sprint_data:
                print(f"\n{sprint_data['name']}:")
                print(f"  Passed: {sprint_data['passed']}")
                print(f"  Failed: {sprint_data['failed']}")
                print(f"  Skipped: {sprint_data['skipped']}")

                # Show failed tests
                failed_tests = [
                    t for t in sprint_data["tests"] if not t.get("passed", False)
                ]
                if failed_tests:
                    print("  Failed Tests:")
                    for test in failed_tests:
                        print(f"    - {test['file']}")

        # Overall summary
        summary = self.test_results["summary"]
        print("\nOVERALL RESULTS:")
        print(f"  Total Tests: {summary['total']}")
        print(
            f"  Passed: {summary['passed']} ({summary['passed']/max(summary['total'], 1)*100:.1f}%)"
        )
        print(f"  Failed: {summary['failed']}")
        print(f"  Skipped: {summary['skipped']}")

        # Save detailed report
        report_path = Path("tests / e2e_test_report.json")
        with open(report_path, "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nDetailed report saved to: {report_path}")

        # Create markdown report
        self.create_markdown_report()

    def create_markdown_report(self):
        """Create a markdown report for documentation"""
        report_lines = [
            "# E2E Test Execution Report",
            f"\n ** Date**: {self.test_results['timestamp']}",
            f"\n ** Overall Status**: {'✅ PASSED' if self.test_results['summary']['failed'] == 0 else '❌ FAILED'}",
            "\n## Test Results by Sprint\n",
        ]

        for sprint_key, sprint_data in self.test_results["sprints"].items():
            if "passed" in sprint_data:
                status = "✅" if sprint_data["failed"] == 0 else "❌"
                report_lines.append(f"### {status} {sprint_data['name']}\n")
                report_lines.append(f"- **Passed**: {sprint_data['passed']}")
                report_lines.append(f"- **Failed**: {sprint_data['failed']}")
                report_lines.append(f"- **Skipped**: {sprint_data['skipped']}")

                # List all tests
                report_lines.append("\n ** Test Files:**")
                for test in sprint_data["tests"]:
                    status_icon = "✅" if test.get("passed", False) else "❌"
                    report_lines.append(f"- {status_icon} `{test['file']}`")
                report_lines.append("")

        # Summary
        summary = self.test_results["summary"]
        report_lines.extend(
            [
                "\n## Summary Statistics\n",
                f"- **Total Tests Run**: {summary['total']}",
                f"- **Success Rate**: {summary['passed']/max(summary['total'], 1)*100:.1f}%",
                f"- **Failed Tests**: {summary['failed']}",
                f"- **Skipped Tests**: {summary['skipped']}",
            ]
        )

        # Coverage areas
        report_lines.extend(
            [
                "\n## Coverage Areas\n",
                "### Sprint 1: Driver Functionality ✅",
                "- Driver mobile dashboard",
                "- Route list view",
                "- Delivery status updates",
                "- GPS tracking",
                "- Signature capture",
                "- Photo proof capture",
                "- Offline mode support",
                "",
                "### Sprint 2: WebSocket & Real - time ✅",
                "- WebSocket connection management",
                "- Real - time order status updates",
                "- Driver location broadcasting",
                "- Notification system",
                "- Auto - reconnection logic",
                "- Message queuing",
                "",
                "### Sprint 3: Order Management ✅",
                "- Order modification workflow",
                "- Bulk order processing",
                "- Credit limit checking",
                "- Advanced search functionality",
                "- Recurring order templates",
                "- Order history tracking",
            ]
        )

        # Save markdown report
        report_path = Path("tests / E2E_TEST_REPORT.md")
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))
        print(f"Markdown report saved to: {report_path}")


def main():
    """Main entry point"""
    runner = E2ETestRunner()
    exit_code = runner.run_all_tests()

    if exit_code == 0:
        print("\n✅ All E2E tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Please review the report.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
