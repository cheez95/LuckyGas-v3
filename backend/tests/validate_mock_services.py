#!/usr/bin/env python3
"""
Validate Mock Services Health Check Script
Checks all mock services are healthy and responding correctly
"""

import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests

# Service configuration
SERVICES = {
    "mock-sms": {
        "url": "http://localhost:8001",
        "health_endpoint": "/health",
        "test_endpoints": [
            {"method": "GET", "path": "/docs"},
        ],
    },
    "mock-einvoice": {
        "url": "http://localhost:8002",
        "health_endpoint": "/health",
        "test_endpoints": [
            {"method": "GET", "path": "/docs"},
        ],
    },
    "mock-banking": {
        "url": "http://localhost:8003",
        "health_endpoint": "/health",
        "test_endpoints": [
            {"method": "GET", "path": "/docs"},
        ],
    },
    "mock-gcp": {
        "url": "http://localhost:8085",
        "health_endpoint": "/health",
        "test_endpoints": [
            {"method": "GET", "path": "/docs"},
        ],
    },
}


# Color codes for output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def check_health(service_name: str, config: Dict) -> Tuple[bool, str]:
    """Check if a service health endpoint is responding correctly"""
    try:
        url = f"{config['url']}{config['health_endpoint']}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            expected_fields = ["status", "service", "timestamp"]

            # Validate response structure
            missing_fields = [field for field in expected_fields if field not in data]
            if missing_fields:
                return False, f"Missing fields in response: {missing_fields}"

            if data.get("status") != "healthy":
                return False, f"Service reports unhealthy status: {data.get('status')}"

            return True, f"Service is healthy (timestamp: {data.get('timestamp')})"
        else:
            return False, f"Health check returned status code: {response.status_code}"

    except requests.exceptions.ConnectionError:
        return False, "Connection refused - service may not be running"
    except requests.exceptions.Timeout:
        return False, "Request timeout - service may be unresponsive"
    except json.JSONDecodeError:
        return False, "Invalid JSON response from health endpoint"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def check_endpoints(service_name: str, config: Dict) -> List[Tuple[str, bool, str]]:
    """Check additional endpoints for the service"""    for endpoint in config.get("test_endpoints", []):
        try:
            url = f"{config['url']}{endpoint['path']}"
            method = endpoint.get("method", "GET").lower()

            if method == "get":
                response = requests.get(url, timeout=5)
            else:
                results.append(
                    (endpoint["path"], False, f"Unsupported method: {method}")
                )
                continue

            if response.status_code in [200, 301, 302]:  # Allow redirects for docs
                results.append(
                    (endpoint["path"], True, f"Status: {response.status_code}")
                )
            else:
                results.append(
                    (endpoint["path"], False, f"Status: {response.status_code}")
                )

        except Exception as e:
            results.append((endpoint["path"], False, str(e)))

    return results


def print_header():
    """Print script header"""
    print(f"\n{Colors.BOLD}🔍 Mock Services Health Check Validation{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def print_service_status(
    service_name: str, health_ok: bool, health_msg: str, endpoint_results: List
):
    """Print status for a single service"""
    status_icon = "✅" if health_ok else "❌"
    status_color = Colors.GREEN if health_ok else Colors.RED

    print(f"{Colors.BOLD}{service_name}:{Colors.ENDC}")
    print(f"  Health Check: {status_icon} {status_color}{health_msg}{Colors.ENDC}")

    if endpoint_results:
        print("  Additional Endpoints:")
        for endpoint, ok, msg in endpoint_results:
            endpoint_icon = "✅" if ok else "❌"
            endpoint_color = Colors.GREEN if ok else Colors.RED
            print(f"    {endpoint}: {endpoint_icon} {endpoint_color}{msg}{Colors.ENDC}")
    print()


def print_summary(results: Dict[str, Tuple[bool, str, List]]):
    """Print summary of all checks"""
    total_services = len(results)
    healthy_services = sum(1 for _, (health_ok, _, _) in results.items() if health_ok)

    print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  Total Services: {total_services}")
    print(f"  Healthy: {Colors.GREEN}{healthy_services}{Colors.ENDC}")
    print(f"  Unhealthy: {Colors.RED}{total_services - healthy_services}{Colors.ENDC}")

    if healthy_services == total_services:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ All services are healthy!{Colors.ENDC}")
        return True
    else:
        print(
            f"\n{Colors.RED}{Colors.BOLD}❌ Some services are unhealthy!{Colors.ENDC}"
        )
        print(f"\n{Colors.YELLOW}Troubleshooting Tips:{Colors.ENDC}")
        print(
            "  1. Check if Docker containers are running: docker-compose -f docker-compose.test.yml ps"
        )
        print(
            "  2. Check container logs: docker-compose -f docker-compose.test.yml logs [service-name]"
        )
        print(
            "  3. Restart services: docker-compose -f docker-compose.test.yml restart"
        )
        print(
            "  4. Rebuild services: docker-compose -f docker-compose.test.yml build --no-cache"
        )
        return False


def wait_for_services(max_wait: int = 60, check_interval: int = 5):
    """Wait for services to become healthy"""
    print(
        f"{Colors.YELLOW}⏳ Waiting for services to become healthy (max {max_wait}s)...{Colors.ENDC}"
    )

    start_time = time.time()
    all_healthy = False

    while time.time() - start_time < max_wait:        all_healthy = True

        for service_name, config in SERVICES.items():
            health_ok, _ = check_health(service_name, config)
            if not health_ok:
                all_healthy = False
                break

        if all_healthy:
            print(f"{Colors.GREEN}✅ All services are ready!{Colors.ENDC}")
            return True

        time.sleep(check_interval)
        print(".", end="", flush=True)

    print(
        f"\n{Colors.RED}❌ Services did not become healthy within {max_wait}s{Colors.ENDC}"
    )
    return False


def main():
    """Main validation function"""
    results = {}
    endpoint_results = []
    print_header()

    # Optional: Wait for services to be ready
    if "--wait" in sys.argv:
        if not wait_for_services():
            sys.exit(1)

    # Check all services    for service_name, config in SERVICES.items():
        health_ok, health_msg = check_health(service_name, config)    endpoint_results = check_endpoints(service_name, config)
        results[service_name] = (health_ok, health_msg, endpoint_results)
        print_service_status(service_name, health_ok, health_msg, endpoint_results)

    # Print summary
    all_healthy = print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
