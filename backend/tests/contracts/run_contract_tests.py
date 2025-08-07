#!/usr / bin / env python
"""
Script to run contract tests for Lucky Gas API

This script handles both consumer and provider contract testing,
including publishing to Pact Broker if configured.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_consumer_tests():
    """Run consumer contract tests to generate pacts."""
    print("Running consumer contract tests...")

    cmd = [
        "pytest",
        "tests / contracts / consumer/",
        "-v",
        "--tb=short",
        "--no - header",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Consumer contract tests failed!")
        print(result.stderr)
        return False

    print("Consumer contract tests passed!")
    print("Pact files generated in: tests / contracts / pacts/")
    return True


def run_provider_tests():
    """Run provider verification tests."""
    print("\nRunning provider verification tests...")

    # Start the backend server first
    print("Starting backend server...")
    server_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    import time

    time.sleep(5)

    try:
        cmd = [
            "pytest",
            "tests / contracts / provider/",
            "-v",
            "--tb=short",
            "--no - header",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("Provider verification tests failed!")
            print(result.stderr)
            return False

        print("Provider verification tests passed!")
        return True

    finally:
        # Stop the server
        server_process.terminate()
        server_process.wait()


def publish_pacts():
    """Publish pact files to Pact Broker."""
    broker_url = os.environ.get("PACT_BROKER_URL")
    if not broker_url:
        print("\nPact Broker URL not configured, skipping publish")
        return True

    print(f"\nPublishing pacts to broker: {broker_url}")

    pact_dir = Path("tests / contracts / pacts")
    pact_files = list(pact_dir.glob("*.json"))

    if not pact_files:
        print("No pact files found to publish")
        return False

    for pact_file in pact_files:
        cmd = [
            "pact - broker",
            "publish",
            str(pact_file),
            "--consumer - app - version",
            "1.0.0",
            "--broker - base - url",
            broker_url,
        ]

        # Add authentication if configured
        username = os.environ.get("PACT_BROKER_USERNAME")
        password = os.environ.get("PACT_BROKER_PASSWORD")

        if username and password:
            cmd.extend(
                ["--broker - username", username, "--broker - password", password]
            )

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Failed to publish {pact_file.name}")
            print(result.stderr)
            return False

        print(f"Successfully published {pact_file.name}")

    return True


def verify_can_i_deploy():
    """Check if it's safe to deploy using can - i - deploy."""
    broker_url = os.environ.get("PACT_BROKER_URL")
    if not broker_url:
        print("\nPact Broker URL not configured, skipping can - i - deploy check")
        return True

    print("\nChecking if it's safe to deploy...")

    cmd = [
        "pact - broker",
        "can - i - deploy",
        "--pacticipant",
        "lucky - gas - frontend",
        "--version",
        "1.0.0",
        "--pacticipant",
        "lucky - gas - backend",
        "--version",
        "1.0.0",
        "--broker - base - url",
        broker_url,
    ]

    # Add authentication if configured
    username = os.environ.get("PACT_BROKER_USERNAME")
    password = os.environ.get("PACT_BROKER_PASSWORD")

    if username and password:
        cmd.extend(["--broker - username", username, "--broker - password", password])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Can - i - deploy check failed! It's not safe to deploy.")
        print(result.stdout)
        return False

    print("Can - i - deploy check passed! It's safe to deploy.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run contract tests for Lucky Gas API")
    parser.add_argument(
        "--consumer - only", action="store_true", help="Run only consumer tests"
    )
    parser.add_argument(
        "--provider - only", action="store_true", help="Run only provider tests"
    )
    parser.add_argument(
        "--skip - publish", action="store_true", help="Skip publishing pacts to broker"
    )
    parser.add_argument(
        "--check - deploy", action="store_true", help="Check if it's safe to deploy"
    )

    args = parser.parse_args()

    # Run tests based on arguments
    if args.provider_only:
        success = run_provider_tests()
    elif args.consumer_only:
        success = run_consumer_tests()
        if success and not args.skip_publish:
            success = publish_pacts()
    else:
        # Run both consumer and provider tests
        success = run_consumer_tests()
        if success:
            success = run_provider_tests()
            if success and not args.skip_publish:
                success = publish_pacts()

    # Check if deployment is safe
    if success and args.check_deploy:
        success = verify_can_i_deploy()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
