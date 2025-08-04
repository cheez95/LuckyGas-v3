#!/usr/bin/env python3
"""
Comprehensive Mock Services Validation Script
Tests health checks and actual API functionality for all mock services
"""

import requests
import sys
import time
import json
from typing import Dict, Tuple, List, Any
from datetime import datetime

# Service test configurations
SERVICE_TESTS = {
    "mock-sms": {
        "url": "http://localhost:8001",
        "health_endpoint": "/health",
        "api_tests": [
            {
                "name": "Send SMS",
                "method": "POST",
                "path": "/api/sms/send",
                "headers": {"Content-Type": "application/json"},
                "data": {
                    "to": "0912345678",
                    "message": "Test message from Lucky Gas",
                    "from_number": "+886900000000"
                },
                "expected_status": 200,
                "expected_fields": ["message_id", "status", "to", "message"]
            },
            {
                "name": "Get Sent Messages",
                "method": "GET",
                "path": "/api/sms/sent",
                "expected_status": 200,
                "expected_fields": ["total", "messages"]
            }
        ]
    },
    "mock-einvoice": {
        "url": "http://localhost:8002",
        "health_endpoint": "/health",
        "api_tests": [
            {
                "name": "Issue E-Invoice",
                "method": "POST",
                "path": "/api/einvoice/issue",
                "headers": {"Content-Type": "application/json"},
                "data": {
                    "buyer_name": "測試客戶",
                    "buyer_address": "台北市中正區測試路123號",
                    "items": [
                        {
                            "description": "瓦斯桶 20KG",
                            "quantity": 2,
                            "unit_price": 800.0,
                            "amount": 1600.0
                        }
                    ],
                    "total_amount": 1680.0,
                    "tax_amount": 80.0,
                    "sales_amount": 1600.0,
                    "invoice_type": "07"
                },
                "expected_status": 200,
                "expected_fields": ["invoice_number", "invoice_date", "qr_code_left", "bar_code"]
            }
        ]
    },
    "mock-banking": {
        "url": "http://localhost:8003",
        "health_endpoint": "/health",
        "api_tests": [
            {
                "name": "Check Account Balance",
                "method": "GET",
                "path": "/api/banking/account/1234567890/balance",
                "expected_status": 200,
                "expected_fields": ["account_number", "balance", "available_balance", "currency"]
            },
            {
                "name": "Validate Account",
                "method": "POST",
                "path": "/api/banking/validate-account",
                "params": {
                    "account_number": "1234567890",
                    "bank_code": "013",
                    "account_name": "Test Company"
                },
                "expected_status": 200,
                "expected_fields": ["is_valid", "bank_name"]
            }
        ]
    },
    "mock-gcp": {
        "url": "http://localhost:8085",
        "health_endpoint": "/health",
        "api_tests": [
            {
                "name": "Geocode Address",
                "method": "GET",
                "path": "/maps/api/geocode/json",
                "params": {
                    "address": "台北市中正區重慶南路一段122號",
                    "key": "test_api_key"
                },
                "expected_status": 200,
                "expected_fields": ["results", "status"]
            },
            {
                "name": "Compute Routes",
                "method": "POST",
                "path": "/routes/v2:computeRoutes",
                "headers": {"Content-Type": "application/json"},
                "data": {
                    "origin": {
                        "location": {
                            "latLng": {
                                "latitude": 25.0330,
                                "longitude": 121.5654
                            }
                        }
                    },
                    "destination": {
                        "location": {
                            "latLng": {
                                "latitude": 25.0475,
                                "longitude": 121.5173
                            }
                        }
                    },
                    "travelMode": "DRIVE"
                },
                "expected_status": 200,
                "expected_fields": ["routes"]
            }
        ]
    }
}

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

def check_health(service_name: str, config: Dict) -> Tuple[bool, str]:
    """Check if a service health endpoint is responding correctly"""
    try:
        url = f"{config['url']}{config['health_endpoint']}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                return True, f"Service is healthy"
            else:
                return False, f"Service reports unhealthy status: {data.get('status')}"
        else:
            return False, f"Health check returned status code: {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - service may not be running"
    except requests.exceptions.Timeout:
        return False, "Request timeout - service may be unresponsive"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def test_api_endpoint(service_name: str, base_url: str, test: Dict) -> Tuple[bool, str]:
    """Test a specific API endpoint"""
    try:
        url = f"{base_url}{test['path']}"
        method = test.get("method", "GET").upper()
        
        # Prepare request parameters
        kwargs = {"timeout": 5}
        if "headers" in test:
            kwargs["headers"] = test["headers"]
        if "params" in test:
            kwargs["params"] = test["params"]
        if "data" in test and method in ["POST", "PUT", "PATCH"]:
            kwargs["json"] = test["data"]
        
        # Make request
        response = requests.request(method, url, **kwargs)
        
        # Check status code
        if response.status_code != test["expected_status"]:
            return False, f"Expected status {test['expected_status']}, got {response.status_code}"
        
        # Check response fields if specified
        if "expected_fields" in test and response.status_code == 200:
            try:
                data = response.json()
                missing_fields = []
                
                # For nested responses, check the appropriate level
                if isinstance(data, dict):
                    if "results" in test["expected_fields"] and "results" in data:
                        # Special case for geocoding results
                        pass
                    else:
                        missing_fields = [field for field in test["expected_fields"] if field not in data]
                
                if missing_fields:
                    return False, f"Missing fields in response: {missing_fields}"
                    
            except json.JSONDecodeError:
                return False, "Invalid JSON response"
        
        return True, f"Status: {response.status_code}"
        
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"

def print_header():
    """Print script header"""
    print(f"\n{Colors.BOLD}🔍 Comprehensive Mock Services Validation{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def print_service_results(service_name: str, health_ok: bool, health_msg: str, api_results: List[Tuple[str, bool, str]]):
    """Print results for a single service"""
    status_icon = "✅" if health_ok else "❌"
    status_color = Colors.GREEN if health_ok else Colors.RED
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}{service_name}:{Colors.ENDC}")
    print(f"  {Colors.BOLD}Health Check:{Colors.ENDC} {status_icon} {status_color}{health_msg}{Colors.ENDC}")
    
    if api_results:
        print(f"  {Colors.BOLD}API Tests:{Colors.ENDC}")
        for test_name, ok, msg in api_results:
            test_icon = "✅" if ok else "❌"
            test_color = Colors.GREEN if ok else Colors.RED
            print(f"    • {test_name}: {test_icon} {test_color}{msg}{Colors.ENDC}")

def print_summary(results: Dict[str, Tuple[bool, str, List]]):
    """Print summary of all tests"""
    total_services = len(results)
    healthy_services = sum(1 for _, (health_ok, _, _) in results.items() if health_ok)
    
    total_api_tests = sum(len(api_results) for _, (_, _, api_results) in results.items())
    passed_api_tests = sum(
        sum(1 for _, ok, _ in api_results if ok) 
        for _, (_, _, api_results) in results.items()
    )
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  Services: {healthy_services}/{total_services} healthy")
    print(f"  API Tests: {passed_api_tests}/{total_api_tests} passed")
    
    if healthy_services == total_services and passed_api_tests == total_api_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ All tests passed! Mock services are fully functional.{Colors.ENDC}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Some tests failed!{Colors.ENDC}")
        
        # Show specific failures
        failed_services = []
        failed_tests = []
        
        for service, (health_ok, health_msg, api_results) in results.items():
            if not health_ok:
                failed_services.append(service)
            for test_name, ok, msg in api_results:
                if not ok:
                    failed_tests.append(f"{service}: {test_name} - {msg}")
        
        if failed_services:
            print(f"\n{Colors.YELLOW}Failed Services:{Colors.ENDC}")
            for service in failed_services:
                print(f"  • {service}")
        
        if failed_tests:
            print(f"\n{Colors.YELLOW}Failed API Tests:{Colors.ENDC}")
            for test in failed_tests:
                print(f"  • {test}")
        
        return False

def wait_for_services(max_wait: int = 60, check_interval: int = 5):
    """Wait for services to become healthy"""
    print(f"{Colors.YELLOW}⏳ Waiting for services to become healthy (max {max_wait}s)...{Colors.ENDC}")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        all_healthy = True
        
        for service_name, config in SERVICE_TESTS.items():
            health_ok, _ = check_health(service_name, config)
            if not health_ok:
                all_healthy = False
                break
        
        if all_healthy:
            print(f"{Colors.GREEN}✅ All services are ready!{Colors.ENDC}")
            return True
        
        time.sleep(check_interval)
        print(".", end="", flush=True)
    
    print(f"\n{Colors.RED}❌ Services did not become healthy within {max_wait}s{Colors.ENDC}")
    return False

def main():
    """Main validation function"""
    print_header()
    
    # Optional: Wait for services to be ready
    if "--wait" in sys.argv:
        if not wait_for_services():
            sys.exit(1)
    
    # Test all services
    results = {}
    
    for service_name, config in SERVICE_TESTS.items():
        # Check health
        health_ok, health_msg = check_health(service_name, config)
        
        # Test API endpoints
        api_results = []
        if health_ok and "api_tests" in config:
            for test in config["api_tests"]:
                test_name = test.get("name", test["path"])
                test_ok, test_msg = test_api_endpoint(service_name, config["url"], test)
                api_results.append((test_name, test_ok, test_msg))
        
        results[service_name] = (health_ok, health_msg, api_results)
        print_service_results(service_name, health_ok, health_msg, api_results)
    
    # Print summary
    all_passed = print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()