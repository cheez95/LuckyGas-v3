"""
End-to-end tests for login flow using Playwright
"""
import os
from typing import Dict

import pytest
from playwright.async_api import Page, expect

# Base URL for tests
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")
API_URL = os.getenv("E2E_API_URL", "http://localhost:8000")


@pytest.mark.e2e
class TestLoginFlow:
    """Test complete login flow from UI perspective"""
    
    @pytest.mark.asyncio
    async def test_successful_login(self, page: Page, test_credentials: Dict[str, str]):
        """Test successful login flow"""
        # Navigate to login page
        await page.goto(f"{BASE_URL}/login")
        
        # Wait for login form to be visible
        await expect(page.locator("form")).to_be_visible()
        
        # Fill in credentials
        await page.fill('input[name="email"]', test_credentials["email"])
        await page.fill('input[name="password"]', test_credentials["password"])
        
        # Submit form
        await page.click('button[type="submit"]')
        
        # Wait for redirect to dashboard
        await page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
        
        # Verify user is logged in
        await expect(page.locator('[data-testid="user-menu"]')).to_be_visible()
        await expect(page.locator('[data-testid="user-name"]')).to_contain_text("測試使用者")
        
        # Verify JWT token is stored
        cookies = await page.context.cookies()
        auth_cookie = next((c for c in cookies if c["name"] == "auth_token"), None)
        assert auth_cookie is not None
        assert auth_cookie["httpOnly"] is True
        
    @pytest.mark.asyncio
    async def test_failed_login_invalid_password(self, page: Page, test_credentials: Dict[str, str]):
        """Test login with invalid password"""
        await page.goto(f"{BASE_URL}/login")
        
        # Fill in credentials with wrong password
        await page.fill('input[name="email"]', test_credentials["email"])
        await page.fill('input[name="password"]', "wrongpassword")
        
        # Submit form
        await page.click('button[type="submit"]')
        
        # Wait for error message
        await expect(page.locator('[data-testid="error-message"]')).to_be_visible()
        await expect(page.locator('[data-testid="error-message"]')).to_contain_text("密碼錯誤")
        
        # Verify still on login page
        assert page.url == f"{BASE_URL}/login"
        
    @pytest.mark.asyncio
    async def test_logout_flow(self, page: Page, authenticated_page: Page):
        """Test logout flow"""
        # Use pre-authenticated page
        page = authenticated_page
        
        # Click user menu
        await page.click('[data-testid="user-menu"]')
        
        # Click logout
        await page.click('[data-testid="logout-button"]')
        
        # Confirm logout dialog if present
        if await page.locator('[data-testid="confirm-logout"]').is_visible():
            await page.click('[data-testid="confirm-logout"]')
        
        # Wait for redirect to login
        await page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        
        # Verify auth cookie is removed
        cookies = await page.context.cookies()
        auth_cookie = next((c for c in cookies if c["name"] == "auth_token"), None)
        assert auth_cookie is None
        
    @pytest.mark.asyncio
    async def test_session_persistence(self, page: Page, test_credentials: Dict[str, str]):
        """Test that session persists across page reloads"""
        # Login first
        await page.goto(f"{BASE_URL}/login")
        await page.fill('input[name="email"]', test_credentials["email"])
        await page.fill('input[name="password"]', test_credentials["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        
        # Reload page
        await page.reload()
        
        # Verify still logged in
        await expect(page.locator('[data-testid="user-menu"]')).to_be_visible()
        assert page.url == f"{BASE_URL}/dashboard"
        
    @pytest.mark.asyncio
    async def test_protected_route_redirect(self, page: Page):
        """Test that protected routes redirect to login when not authenticated"""
        # Try to access protected route directly
        await page.goto(f"{BASE_URL}/customers")
        
        # Should redirect to login
        await page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        
        # Verify redirect message if shown
        if await page.locator('[data-testid="redirect-message"]').is_visible():
            await expect(page.locator('[data-testid="redirect-message"]')).to_contain_text("請先登入")
            
    @pytest.mark.asyncio
    async def test_role_based_access(self, page: Page, admin_credentials: Dict[str, str], office_credentials: Dict[str, str]):
        """Test role-based access control"""
        # Test admin access
        await page.goto(f"{BASE_URL}/login")
        await page.fill('input[name="email"]', admin_credentials["email"])
        await page.fill('input[name="password"]', admin_credentials["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        
        # Admin should see admin menu
        await expect(page.locator('[data-testid="admin-menu"]')).to_be_visible()
        
        # Logout
        await page.click('[data-testid="user-menu"]')
        await page.click('[data-testid="logout-button"]')
        await page.wait_for_url(f"{BASE_URL}/login")
        
        # Test office staff access
        await page.fill('input[name="email"]', office_credentials["email"])
        await page.fill('input[name="password"]', office_credentials["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        
        # Office staff should not see admin menu
        await expect(page.locator('[data-testid="admin-menu"]')).not_to_be_visible()
        
    @pytest.mark.asyncio
    async def test_mobile_responsive_login(self, page: Page, test_credentials: Dict[str, str]):
        """Test login on mobile viewport"""
        # Set mobile viewport
        await page.set_viewport_size({"width": 375, "height": 667})
        
        await page.goto(f"{BASE_URL}/login")
        
        # Verify mobile-optimized layout
        await expect(page.locator('[data-testid="mobile-login-form"]')).to_be_visible()
        
        # Fill and submit
        await page.fill('input[name="email"]', test_credentials["email"])
        await page.fill('input[name="password"]', test_credentials["password"])
        await page.click('button[type="submit"]')
        
        # Wait for redirect
        await page.wait_for_url(f"{BASE_URL}/dashboard")
        
        # Verify mobile menu is visible
        await expect(page.locator('[data-testid="mobile-menu-toggle"]')).to_be_visible()