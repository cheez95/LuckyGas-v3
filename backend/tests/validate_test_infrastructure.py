#!/usr/bin/env python3
"""
Test Infrastructure Validation Script
Validates that all test infrastructure is properly configured
"""
import json
import os
import subprocess
import sys
from datetime import datetime


class TestInfrastructureValidator:
    """Validates test infrastructure setup"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {},
        }
        self.passed = 0
        self.failed = 0

    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        print("🔍 Checking dependencies...")

        required_packages = [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-mock",
            "pytest-json-report",
            "httpx",
            "faker",
            "playwright",
            "jinja2",
            "aiofiles",
            "beautifulsoup4",
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if missing:
            self.results["checks"]["dependencies"] = {
                "status": "failed",
                "missing_packages": missing,
            }
            print(f"❌ Missing packages: {', '.join(missing)}")
            self.failed += 1
            return False
        else:
            self.results["checks"]["dependencies"] = {"status": "passed"}
            print("✅ All dependencies installed")
            self.passed += 1
            return True

    def check_environment_variables(self) -> bool:
        """Check if environment variables are properly set"""
        print("\n🔍 Checking environment variables...")

        required_vars = ["ENVIRONMENT", "DATABASE_URL", "REDIS_URL"]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.results["checks"]["environment"] = {
                "status": "failed",
                "missing_vars": missing_vars,
            }
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            self.failed += 1
            return False
        else:
            self.results["checks"]["environment"] = {"status": "passed"}
            print("✅ Environment variables configured")
            self.passed += 1
            return True

    def check_test_database(self) -> bool:
        """Check if test database is accessible"""
        print("\n🔍 Checking test database...")

        try:
            import asyncio

            from sqlalchemy.ext.asyncio import create_async_engine

            async def test_connection():
                db_url = os.getenv(
                    "DATABASE_URL",
                    "postgresql://test:test@localhost:5432/luckygas_test",
                )
                engine = create_async_engine(db_url)
                try:
                    async with engine.connect() as conn:
                        result = await conn.execute("SELECT 1")
                        return result.scalar() == 1
                finally:
                    await engine.dispose()

            connected = asyncio.run(test_connection())

            if connected:
                self.results["checks"]["database"] = {"status": "passed"}
                print("✅ Test database accessible")
                self.passed += 1
                return True
            else:
                raise Exception("Database query failed")

        except Exception as e:
            self.results["checks"]["database"] = {"status": "failed", "error": str(e)}
            print(f"❌ Database connection failed: {e}")
            self.failed += 1
            return False

    def check_redis(self) -> bool:
        """Check if Redis is accessible"""
        print("\n🔍 Checking Redis...")

        try:
            import asyncio

            import redis.asyncio as redis

            async def test_redis():
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
                client = await redis.from_url(redis_url)
                try:
                    await client.ping()
                    return True
                finally:
                    await client.close()

            connected = asyncio.run(test_redis())

            if connected:
                self.results["checks"]["redis"] = {"status": "passed"}
                print("✅ Redis accessible")
                self.passed += 1
                return True
            else:
                raise Exception("Redis ping failed")

        except Exception as e:
            self.results["checks"]["redis"] = {"status": "failed", "error": str(e)}
            print(f"❌ Redis connection failed: {e}")
            self.failed += 1
            return False

    def check_test_files(self) -> bool:
        """Check if all test files are present"""
        print("\n🔍 Checking test files...")

        required_files = [
            "tests/conftest.py",
            "tests/e2e/conftest.py",
            "tests/chaos/__init__.py",
            "tests/fixtures/test_data.py",
            "pytest.ini",
            "setup_tests.sh",
        ]

        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)

        # Count test files
        test_counts = {
            "unit": len(
                [
                    f
                    for f in os.listdir("tests")
                    if f.startswith("test_") and f.endswith(".py")
                ]
            ),
            "e2e": len(
                [
                    f
                    for f in os.listdir("tests/e2e")
                    if f.startswith("test_") and f.endswith(".py")
                ]
            ),
            "chaos": len(
                [
                    f
                    for f in os.listdir("tests/chaos")
                    if f.startswith("test_") and f.endswith(".py")
                ]
            ),
            "integration": len(
                [
                    f
                    for f in os.listdir("tests/integration")
                    if f.startswith("test_") and f.endswith(".py")
                ]
            ),
        }

        if missing_files:
            self.results["checks"]["test_files"] = {
                "status": "failed",
                "missing_files": missing_files,
                "test_counts": test_counts,
            }
            print(f"❌ Missing files: {', '.join(missing_files)}")
            self.failed += 1
            return False
        else:
            self.results["checks"]["test_files"] = {
                "status": "passed",
                "test_counts": test_counts,
            }
            print(
                f"✅ Test files present - Unit: {test_counts['unit']}, E2E: {test_counts['e2e']}, "
                f"Chaos: {test_counts['chaos']}, Integration: {test_counts['integration']}"
            )
            self.passed += 1
            return True

    def run_sample_tests(self) -> bool:
        """Run a few sample tests to verify setup"""
        print("\n🔍 Running sample tests...")

        # Run a simple unit test
        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "pytest",
                    "tests/test_main.py",
                    "-v",
                    "-k",
                    "test_health_check",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.results["checks"]["sample_tests"] = {"status": "passed"}
                print("✅ Sample tests passed")
                self.passed += 1
                return True
            else:
                self.results["checks"]["sample_tests"] = {
                    "status": "failed",
                    "output": result.stdout + result.stderr,
                }
                print("❌ Sample tests failed")
                self.failed += 1
                return False

        except Exception as e:
            self.results["checks"]["sample_tests"] = {
                "status": "error",
                "error": str(e),
            }
            print(f"❌ Error running tests: {e}")
            self.failed += 1
            return False

    def generate_report(self) -> None:
        """Generate validation report"""
        self.results["summary"] = {
            "total_checks": self.passed + self.failed,
            "passed": self.passed,
            "failed": self.failed,
            "success_rate": (
                (self.passed / (self.passed + self.failed) * 100)
                if (self.passed + self.failed) > 0
                else 0
            ),
        }

        # Write JSON report
        with open("test_infrastructure_validation.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Write markdown report
        with open("TEST_INFRASTRUCTURE_REPORT.md", "w") as f:
            f.write("# Test Infrastructure Validation Report\n\n")
            f.write(f"**Date**: {self.results['timestamp']}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Checks**: {self.results['summary']['total_checks']}\n")
            f.write(f"- **Passed**: {self.results['summary']['passed']} ✅\n")
            f.write(f"- **Failed**: {self.results['summary']['failed']} ❌\n")
            f.write(
                f"- **Success Rate**: {self.results['summary']['success_rate']:.1f}%\n\n"
            )

            f.write("## Check Results\n\n")
            for check_name, result in self.results["checks"].items():
                status_emoji = "✅" if result["status"] == "passed" else "❌"
                f.write(
                    f"### {check_name.replace('_', ' ').title()} {status_emoji}\n\n"
                )
                f.write(f"- **Status**: {result['status']}\n")
                if "error" in result:
                    f.write(f"- **Error**: {result['error']}\n")
                if "missing_packages" in result:
                    f.write(
                        f"- **Missing Packages**: {', '.join(result['missing_packages'])}\n"
                    )
                if "missing_vars" in result:
                    f.write(
                        f"- **Missing Variables**: {', '.join(result['missing_vars'])}\n"
                    )
                if "test_counts" in result:
                    f.write(f"- **Test Counts**: {result['test_counts']}\n")
                f.write("\n")

            if self.failed > 0:
                f.write("## Action Items\n\n")
                f.write("1. Fix all failed checks above\n")
                f.write("2. Run `./setup_tests.sh` to set up environment\n")
                f.write("3. Install missing dependencies with `uv sync`\n")
                f.write("4. Ensure Docker containers are running\n")
                f.write("5. Re-run this validation script\n")


def main():
    """Main entry point"""
    print("🚀 Lucky Gas v3 Test Infrastructure Validator\n")

    validator = TestInfrastructureValidator()

    # Run all checks
    validator.check_dependencies()
    validator.check_environment_variables()
    validator.check_test_database()
    validator.check_redis()
    validator.check_test_files()
    validator.run_sample_tests()

    # Generate report
    validator.generate_report()

    # Print summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Total Checks: {validator.passed + validator.failed}")
    print(f"Passed: {validator.passed} ✅")
    print(f"Failed: {validator.failed} ❌")
    print(
        f"Success Rate: {(validator.passed / (validator.passed + validator.failed) * 100):.1f}%"
    )
    print("\nReports generated:")
    print("- test_infrastructure_validation.json")
    print("- TEST_INFRASTRUCTURE_REPORT.md")

    # Exit with appropriate code
    sys.exit(0 if validator.failed == 0 else 1)


if __name__ == "__main__":
    main()
