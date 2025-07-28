"""
Tests for security middleware
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.middleware.security import SecurityMiddleware, SecurityValidation


class TestSecurityValidation:
    """Test input validation"""
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection"""
        validator = SecurityValidation()
        
        # Test various SQL injection attempts
        assert validator.is_sql_injection_attempt("'; DROP TABLE users; --") is True
        assert validator.is_sql_injection_attempt("1' OR '1'='1") is True
        assert validator.is_sql_injection_attempt("admin' --") is True
        assert validator.is_sql_injection_attempt("1 UNION SELECT * FROM users") is True
        assert validator.is_sql_injection_attempt("normal input") is False
        assert validator.is_sql_injection_attempt("user@example.com") is False
    
    def test_xss_detection(self):
        """Test XSS pattern detection"""
        validator = SecurityValidation()
        
        # Test various XSS attempts
        assert validator.is_xss_attempt("<script>alert('XSS')</script>") is True
        assert validator.is_xss_attempt("<img src=x onerror=alert('XSS')>") is True
        assert validator.is_xss_attempt("javascript:alert('XSS')") is True
        assert validator.is_xss_attempt("<iframe src='evil.com'></iframe>") is True
        assert validator.is_xss_attempt("normal text") is False
        assert validator.is_xss_attempt("<p>This is a paragraph</p>") is False
    
    def test_path_traversal_detection(self):
        """Test path traversal detection"""
        validator = SecurityValidation()
        
        # Test various path traversal attempts
        assert validator.is_path_traversal_attempt("../../etc/passwd") is True
        assert validator.is_path_traversal_attempt("..\\..\\windows\\system32") is True
        assert validator.is_path_traversal_attempt("%2e%2e/config") is True
        assert validator.is_path_traversal_attempt("normal/path/file.txt") is False
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        validator = SecurityValidation()
        
        # Test sanitization
        assert validator.sanitize_input("<script>alert('XSS')</script>") == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;&#x2F;script&gt;"
        assert validator.sanitize_input("normal text") == "normal text"
        assert validator.sanitize_input("user's input") == "user&#x27;s input"


class TestSecurityMiddleware:
    """Test security middleware integration"""
    
    @pytest.fixture
    def app(self):
        """Create test app with security middleware"""
        app = FastAPI()
        app.add_middleware(SecurityMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        @app.get("/test-params")
        async def test_with_params(query: str):
            return {"query": query}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)
    
    def test_security_headers_added(self, client):
        """Test security headers are added to response"""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in response.headers
    
    def test_sql_injection_blocked(self, client):
        """Test SQL injection attempts are blocked"""
        response = client.get("/test-params?query=' OR 1=1 --")
        
        assert response.status_code == 400
        assert "無效的請求參數" in response.json()["detail"]
    
    def test_xss_blocked(self, client):
        """Test XSS attempts are blocked"""
        response = client.get("/test-params?query=<script>alert('XSS')</script>")
        
        assert response.status_code == 400
        assert "無效的請求參數" in response.json()["detail"]
    
    def test_normal_request_allowed(self, client):
        """Test normal requests are allowed"""
        response = client.get("/test-params?query=normal query")
        
        assert response.status_code == 200
        assert response.json()["query"] == "normal query"
    
    def test_large_url_blocked(self, client):
        """Test excessively long URLs are blocked"""
        long_path = "a" * 3000
        response = client.get(f"/test?param={long_path}")
        
        assert response.status_code == 414
        assert "請求 URL 過長" in response.json()["detail"]