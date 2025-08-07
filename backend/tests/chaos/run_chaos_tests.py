#!/usr / bin / env python3
"""
Chaos Engineering Test Runner
Orchestrates the execution of chaos tests with proper setup and reporting
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional


class ChaosTestRunner:
    """Orchestrates chaos engineering test execution"""

    def __init__(self, test_env: str = "test", output_dir: str = "chaos_results"):
        self.test_env = test_env
        self.output_dir = output_dir
        self.results = {
            "start_time": datetime.now().isoformat(),
            "environment": test_env,
            "tests": {},
            "summary": {},
        }

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def setup_environment(self) -> bool:
        """Set up test environment"""
        print("🔧 Setting up chaos test environment...")

        # Set environment variables
        os.environ["ENVIRONMENT"] = self.test_env
        os.environ["DISABLE_GOOGLE_APIS"] = "true"
        os.environ["CHAOS_TESTING"] = "true"

        # Run setup script
        setup_script = "./setup_tests.sh"
        if os.path.exists(setup_script):
            try:
                subprocess.run([setup_script], check=True)
                print("✅ Environment setup complete")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Setup failed: {e}")
                return False
        else:
            print("⚠️  No setup script found, continuing...")
            return True

    def run_test_suite(self, suite: str, tests: Optional[List[str]] = None) -> Dict:
        """Run a specific chaos test suite"""
        print(f"\n🧪 Running {suite} chaos tests...")

        suite_start = time.time()
        test_file = f"tests / chaos / test_{suite}.py"

        # Build pytest command
        cmd = ["uv", "run", "pytest", test_file, "-v", "--tb=short"]

        # Add specific tests if provided
        if tests:
            for test in tests:
                cmd.extend(["-k", test])

        # Add chaos marker
        cmd.extend(["-m", "chaos"])

        # Add JSON report
        report_file = os.path.join(self.output_dir, f"{suite}_report.json")
        cmd.extend(["--json - report", f"--json - report - file={report_file}"])

        # Run tests
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = time.time() - suite_start

            # Parse results
            suite_results = {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            # Try to load JSON report
            if os.path.exists(report_file):
                with open(report_file, "r") as f:
                    suite_results["detailed_results"] = json.load(f)

            return suite_results

        except Exception as e:
            return {
                "status": "error",
                "duration": time.time() - suite_start,
                "error": str(e),
            }

    def run_all_suites(self) -> None:
        """Run all chaos test suites"""
        suites = [
            (
                "pod_failure",
                ["test_single_pod_termination", "test_rolling_restart_availability"],
            ),
            (
                "network_chaos",
                [
                    "test_network_latency_100ms",
                    "test_network_latency_500ms",
                    "test_intermittent_network_failures",
                ],
            ),
            (
                "database_chaos",
                [
                    "test_connection_pool_exhaustion",
                    "test_database_connection_failure_recovery",
                ],
            ),
            (
                "external_api_chaos",
                [
                    "test_einvoice_api_failure",
                    "test_sms_gateway_timeout",
                    "test_multiple_external_api_failures",
                ],
            ),
            (
                "resource_exhaustion",
                ["test_memory_exhaustion_handling", "test_cpu_throttling_behavior"],
            ),
        ]

        for suite_name, priority_tests in suites:
            # Run priority tests first
            results = self.run_test_suite(suite_name, priority_tests)
            self.results["tests"][suite_name] = results

            # Print summary
            status_emoji = "✅" if results["status"] == "passed" else "❌"
            print(
                f"{status_emoji} {suite_name}: {results['status']} ({results['duration']:.2f}s)"
            )

            # If critical suite fails, optionally stop
            if (
                suite_name in ["pod_failure", "database_chaos"]
                and results["status"] != "passed"
            ):
                print(
                    f"⚠️  Critical suite {suite_name} failed. Continuing with remaining tests..."
                )

    def generate_report(self) -> None:
        """Generate comprehensive chaos test report"""
        print("\n📊 Generating chaos test report...")

        # Calculate summary statistics
        total_tests = len(self.results["tests"])
        passed_tests = sum(
            1 for r in self.results["tests"].values() if r["status"] == "passed"
        )
        failed_tests = sum(
            1 for r in self.results["tests"].values() if r["status"] == "failed"
        )
        error_tests = sum(
            1 for r in self.results["tests"].values() if r["status"] == "error"
        )

        self.results["summary"] = {
            "total_suites": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": (
                (passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
            "end_time": datetime.now().isoformat(),
            "total_duration": sum(
                r.get("duration", 0) for r in self.results["tests"].values()
            ),
        }

        # Write JSON report
        report_path = os.path.join(self.output_dir, "chaos_test_summary.json")
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)

        # Generate markdown report
        self.generate_markdown_report()

        print(f"✅ Reports generated in {self.output_dir}/")

    def generate_markdown_report(self) -> None:
        """Generate human - readable markdown report"""
        md_path = os.path.join(self.output_dir, "CHAOS_TEST_REPORT.md")

        with open(md_path, "w") as f:
            f.write("# Chaos Engineering Test Report\n\n")
            f.write(f"**Date**: {self.results['start_time']}\n")
            f.write(f"**Environment**: {self.results['environment']}\n")
            f.write(
                f"**Duration**: {self.results['summary']['total_duration']:.2f}s\n\n"
            )

            f.write("## Summary\n\n")
            f.write(
                f"- **Total Test Suites**: {self.results['summary']['total_suites']}\n"
            )
            f.write(f"- **Passed**: {self.results['summary']['passed']} ✅\n")
            f.write(f"- **Failed**: {self.results['summary']['failed']} ❌\n")
            f.write(f"- **Errors**: {self.results['summary']['errors']} ⚠️\n")
            f.write(
                f"- **Success Rate**: {self.results['summary']['success_rate']:.1f}%\n\n"
            )

            f.write("## Test Suite Results\n\n")
            for suite_name, results in self.results["tests"].items():
                status_emoji = "✅" if results["status"] == "passed" else "❌"
                f.write(f"### {suite_name} {status_emoji}\n\n")
                f.write(f"- **Status**: {results['status']}\n")
                f.write(f"- **Duration**: {results['duration']:.2f}s\n")

                if (
                    "detailed_results" in results
                    and "tests" in results["detailed_results"]
                ):
                    f.write(
                        f"- **Test Count**: {len(results['detailed_results']['tests'])}\n"
                    )

                    # Show failed tests
                    failed_tests = [
                        t
                        for t in results["detailed_results"]["tests"]
                        if t.get("outcome") != "passed"
                    ]
                    if failed_tests:
                        f.write("\n ** Failed Tests**:\n")
                        for test in failed_tests:
                            f.write(f"- `{test['nodeid']}`: {test.get('outcome')}\n")

                f.write("\n")

            f.write("## Recommendations\n\n")
            if self.results["summary"]["failed"] > 0:
                f.write("### Failed Tests\n")
                f.write("- Review failed test logs for root cause analysis\n")
                f.write("- Ensure test environment is properly configured\n")
                f.write("- Check for resource constraints in test environment\n\n")

            if self.results["summary"]["success_rate"] < 80:
                f.write("### Low Success Rate\n")
                f.write("- System may not be resilient enough for production\n")
                f.write(
                    "- Consider implementing additional fault tolerance mechanisms\n"
                )
                f.write("- Review circuit breakers and retry policies\n\n")

            f.write("## Next Steps\n\n")
            f.write("1. Address any failed chaos tests\n")
            f.write("2. Review system logs during chaos test execution\n")
            f.write("3. Update runbooks based on failure scenarios\n")
            f.write("4. Consider adding more chaos scenarios\n")
            f.write("5. Run chaos tests regularly in staging environment\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run chaos engineering tests")
    parser.add_argument("--env", default="test", help="Test environment")
    parser.add_argument("--suite", help="Run specific test suite")
    parser.add_argument("--output", default="chaos_results", help="Output directory")
    parser.add_argument(
        "--no - setup", action="store_true", help="Skip environment setup"
    )

    args = parser.parse_args()

    # Create runner
    runner = ChaosTestRunner(test_env=args.env, output_dir=args.output)

    # Setup environment
    if not args.no_setup:
        if not runner.setup_environment():
            print("❌ Environment setup failed")
            sys.exit(1)

    # Run tests
    try:
        if args.suite:
            # Run specific suite
            results = runner.run_test_suite(args.suite)
            runner.results["tests"][args.suite] = results
        else:
            # Run all suites
            runner.run_all_suites()

        # Generate report
        runner.generate_report()

        # Print summary
        print("\n" + "=" * 50)
        print("CHAOS TEST SUMMARY")
        print("=" * 50)
        print(f"Success Rate: {runner.results['summary']['success_rate']:.1f}%")
        print(f"Total Duration: {runner.results['summary']['total_duration']:.2f}s")

        # Exit with appropriate code
        if runner.results["summary"]["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
