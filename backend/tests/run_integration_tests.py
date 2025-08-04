#!/usr/bin/env python
"""
Run integration tests with proper test environment setup
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def check_docker_services():
    """Check if Docker test services are running"""
    print("Checking Docker test services...")
    
    required_services = [
        ("PostgreSQL", "5433"),
        ("Redis", "6380"),
        ("Mock GCP", "8080"),
        ("Mock SMS", "8001"),
        ("Mock E-Invoice", "8002"),
        ("Mock Banking", "8003")
    ]
    
    all_running = True
    for service, port in required_services:
        result = subprocess.run(
            ["nc", "-z", "localhost", port],
            capture_output=True
        )
        if result.returncode == 0:
            print(f"✅ {service} is running on port {port}")
        else:
            print(f"❌ {service} is NOT running on port {port}")
            all_running = False
    
    return all_running


def start_docker_services():
    """Start Docker test services"""
    print("\nStarting Docker test services...")
    
    docker_compose_path = Path(__file__).parent / "docker-compose.test.yml"
    
    # Check if docker-compose file exists
    if not docker_compose_path.exists():
        print(f"❌ Docker compose file not found at {docker_compose_path}")
        return False
    
    # Start services
    cmd = [
        "docker-compose",
        "-f", str(docker_compose_path),
        "up", "-d"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed to start Docker services: {result.stderr}")
        return False
    
    print("✅ Docker services started")
    
    # Wait for services to be ready
    print("Waiting for services to be ready...")
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        time.sleep(2)
        if check_docker_services():
            print("✅ All services are ready!")
            return True
        retry_count += 1
    
    print("❌ Services failed to start within timeout")
    return False


def setup_test_database():
    """Initialize test database"""
    print("\nSetting up test database...")
    
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TESTING"] = "1"
    
    # Load test environment
    from dotenv import load_dotenv
    env_test_path = backend_dir / ".env.test"
    if env_test_path.exists():
        load_dotenv(env_test_path)
    
    # Run migrations
    print("Running database migrations...")
    from app.core.database import engine
    from app.core.database import Base
    import asyncio
    
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(create_tables())
    print("✅ Database setup complete")


def run_integration_tests(test_path=None, verbose=False):
    """Run integration tests"""
    print("\nRunning integration tests...")
    
    # Prepare pytest command
    cmd = ["pytest", "-v" if verbose else "-q"]
    
    # Add specific test path if provided
    if test_path:
        cmd.append(test_path)
    else:
        cmd.extend([
            "tests/integration/",
            "-m", "not slow",  # Skip slow tests by default
            "--tb=short",
            "--maxfail=5"
        ])
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    # Run tests
    result = subprocess.run(cmd, env={**os.environ})
    
    return result.returncode == 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("test_path", nargs="?", help="Specific test file or directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-docker", action="store_true", help="Skip Docker service check")
    parser.add_argument("--skip-setup", action="store_true", help="Skip database setup")
    
    args = parser.parse_args()
    
    # Check/start Docker services
    if not args.no_docker:
        if not check_docker_services():
            print("\n⚠️  Some Docker services are not running.")
            response = input("Start Docker services? (y/n): ")
            if response.lower() == 'y':
                if not start_docker_services():
                    print("❌ Failed to start Docker services")
                    sys.exit(1)
            else:
                print("⚠️  Running tests without all services may cause failures")
    
    # Setup database
    if not args.skip_setup:
        setup_test_database()
    
    # Run tests
    if run_integration_tests(args.test_path, args.verbose):
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()