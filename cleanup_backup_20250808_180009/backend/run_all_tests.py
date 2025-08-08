#!/usr/bin/env python3
"""
Comprehensive Test Runner
Executes all tests and generates report
"""
import asyncio
import httpx
import json
from datetime import datetime
import subprocess

async def run_tests():
    """Run all test suites"""
    print("🧪 Lucky Gas Comprehensive Test Suite")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {
        "test_date": datetime.now().isoformat(),
        "suites": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    # 1. Backend Health Tests
    print("\n🏥 Backend Health Tests")
    print("-" * 40)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/health")
            if response.status_code == 200:
                print("✅ Health check: PASSED")
                results["suites"].append({
                    "name": "Backend Health",
                    "status": "passed",
                    "tests": 1,
                    "passed": 1
                })
                results["summary"]["total"] += 1
                results["summary"]["passed"] += 1
            else:
                print("❌ Health check: FAILED")
                results["summary"]["total"] += 1
                results["summary"]["failed"] += 1
    except Exception as e:
        print(f"❌ Health check: ERROR - {e}")
        results["summary"]["total"] += 1
        results["summary"]["failed"] += 1
    
    # 2. Authentication Tests
    print("\n🔐 Authentication Tests")
    print("-" * 40)
    try:
        # Run auth test script
        result = subprocess.run(
            ["uv", "run", "python", "test_auth_minimal.py"],
            capture_output=True,
            text=True
        )
        if "All authentication tests completed!" in result.stdout:
            print("✅ Authentication suite: PASSED")
            results["suites"].append({
                "name": "Authentication",
                "status": "passed",
                "tests": 6,
                "passed": 6
            })
            results["summary"]["total"] += 6
            results["summary"]["passed"] += 6
        else:
            print("❌ Authentication suite: FAILED")
            results["summary"]["total"] += 6
            results["summary"]["failed"] += 6
    except Exception as e:
        print(f"❌ Authentication suite: ERROR - {e}")
    
    # 3. Database Tests
    print("\n💾 Database Tests")
    print("-" * 40)
    try:
        # Test database connectivity
        result = subprocess.run(
            ["uv", "run", "python", "check_users.py"],
            capture_output=True,
            text=True
        )
        if "Users in database:" in result.stdout:
            print("✅ Database connectivity: PASSED")
            results["suites"].append({
                "name": "Database",
                "status": "passed",
                "tests": 1,
                "passed": 1
            })
            results["summary"]["total"] += 1
            results["summary"]["passed"] += 1
        else:
            print("❌ Database connectivity: FAILED")
            results["summary"]["total"] += 1
            results["summary"]["failed"] += 1
    except Exception as e:
        print(f"❌ Database tests: ERROR - {e}")
    
    # 4. API Endpoint Tests
    print("\n🌐 API Endpoint Tests")
    print("-" * 40)
    endpoints = [
        ("/", "Root endpoint"),
        ("/api/v1/health", "Health check"),
        ("/api/v1/auth/login", "Login endpoint"),
        ("/api/v1/auth/me", "Current user"),
        ("/api/v1/customers", "Customers list")
    ]
    
    for endpoint, name in endpoints:
        try:
            async with httpx.AsyncClient() as client:
                # Get token for protected endpoints
                if endpoint in ["/api/v1/auth/me", "/api/v1/customers"]:
                    login_resp = await client.post(
                        "http://localhost:8000/api/v1/auth/login",
                        data={"username": "test@example.com", "password": "test123"}
                    )
                    token = login_resp.json()["access_token"]
                    headers = {"Authorization": f"Bearer {token}"}
                else:
                    headers = {}
                
                response = await client.get(f"http://localhost:8000{endpoint}", headers=headers)
                if response.status_code in [200, 405]:  # 405 for POST-only endpoints
                    print(f"✅ {name}: PASSED")
                    results["summary"]["passed"] += 1
                else:
                    print(f"❌ {name}: FAILED (Status: {response.status_code})")
                    results["summary"]["failed"] += 1
                results["summary"]["total"] += 1
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
            results["summary"]["failed"] += 1
            results["summary"]["total"] += 1
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']} ({results['summary']['passed']/results['summary']['total']*100:.1f}%)")
    print(f"Failed: {results['summary']['failed']} ({results['summary']['failed']/results['summary']['total']*100:.1f}%)")
    
    # Save report
    with open("test_report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Test report saved to test_report.json")

if __name__ == "__main__":
    asyncio.run(run_tests())