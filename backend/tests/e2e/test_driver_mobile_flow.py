"""
End-to-end tests for driver mobile app flow using Playwright
"""
import os
from datetime import datetime
from typing import Dict

import pytest
from playwright.async_api import BrowserContext, Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")


@pytest.mark.e2e
class TestDriverMobileFlow:
    """Test driver mobile app workflows"""
    
    @pytest.fixture
    async def mobile_context(self, browser) -> BrowserContext:
        """Create mobile browser context"""
        context = await browser.new_context(
            viewport={"width": 375, "height": 812},  # iPhone X viewport
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            has_touch=True,
            is_mobile=True
        )
        return context
        
    @pytest.mark.asyncio
    async def test_driver_login_mobile(self, mobile_context: BrowserContext, driver_credentials: Dict[str, str]):
        """Test driver login on mobile device"""
        page = await mobile_context.new_page()
        
        await page.goto(f"{BASE_URL}/driver/login")
        
        # Check mobile-optimized login
        await expect(page.locator('[data-testid="mobile-driver-login"]')).to_be_visible()
        
        # Fill credentials
        await page.fill('[name="email"]', driver_credentials["email"])
        await page.fill('[name="password"]', driver_credentials["password"])
        
        # Login
        await page.tap('[data-testid="login-button"]')
        
        # Wait for redirect to driver dashboard
        await page.wait_for_url(f"{BASE_URL}/driver/dashboard")
        
        # Verify mobile UI elements
        await expect(page.locator('[data-testid="mobile-nav"]')).to_be_visible()
        await expect(page.locator('[data-testid="today-routes"]')).to_be_visible()
        
    @pytest.mark.asyncio
    async def test_view_assigned_routes(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test viewing assigned delivery routes"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/routes")
        
        # Check today's routes
        await expect(page.locator('[data-testid="route-list"]')).to_be_visible()
        
        # Get route count
        route_cards = page.locator('[data-testid="route-card"]')
        count = await route_cards.count()
        
        if count > 0:
            # Click first route
            await route_cards.first.tap()
            
            # Wait for route detail
            await expect(page.locator('[data-testid="route-detail"]')).to_be_visible()
            
            # Verify route information
            await expect(page.locator('[data-testid="route-map"]')).to_be_visible()
            await expect(page.locator('[data-testid="stop-list"]')).to_be_visible()
            await expect(page.locator('[data-testid="route-stats"]')).to_be_visible()
            
    @pytest.mark.asyncio
    async def test_start_delivery_route(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test starting a delivery route"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/routes")
        
        # Find route to start
        start_button = page.locator('[data-testid="start-route-button"]').first
        
        if await start_button.is_visible():
            # Start route
            await start_button.tap()
            
            # Confirm start
            await expect(page.locator('[data-testid="confirm-start-dialog"]')).to_be_visible()
            await page.tap('[data-testid="confirm-start"]')
            
            # Wait for route to activate
            await expect(page.locator('[data-testid="active-route-banner"]')).to_be_visible()
            
            # Verify navigation buttons appear
            await expect(page.locator('[data-testid="navigate-button"]')).to_be_visible()
            await expect(page.locator('[data-testid="next-stop-button"]')).to_be_visible()
            
    @pytest.mark.asyncio
    async def test_delivery_completion_flow(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test completing a delivery"""
        page = driver_authenticated_page
        
        # Assume we're on an active route
        await page.goto(f"{BASE_URL}/driver/active-route")
        
        # Click on current stop
        await page.tap('[data-testid="current-stop-card"]')
        
        # Wait for delivery form
        await expect(page.locator('[data-testid="delivery-form"]')).to_be_visible()
        
        # Verify customer info
        await expect(page.locator('[data-testid="customer-name"]')).to_be_visible()
        await expect(page.locator('[data-testid="delivery-address"]')).to_be_visible()
        await expect(page.locator('[data-testid="order-items"]')).to_be_visible()
        
        # Mark items as delivered
        await page.check('[data-testid="delivered-50kg"]')
        await page.fill('[data-testid="delivered-50kg-qty"]', "2")
        
        await page.check('[data-testid="delivered-20kg"]')
        await page.fill('[data-testid="delivered-20kg-qty"]', "1")
        
        # Collect payment
        await page.select_option('[data-testid="payment-method"]', "cash")
        await page.fill('[data-testid="payment-amount"]', "8700")
        
        # Take photo of delivery
        await page.tap('[data-testid="take-photo-button"]')
        
        # Mock camera permission and photo capture
        if await page.locator('[data-testid="camera-permission"]').is_visible():
            await page.tap('[data-testid="allow-camera"]')
        
        # Simulate photo taken
        await page.tap('[data-testid="capture-photo"]')
        await page.tap('[data-testid="use-photo"]')
        
        # Get customer signature
        await page.tap('[data-testid="get-signature-button"]')
        
        # Draw signature (simulate touch events)
        signature_pad = page.locator('[data-testid="signature-pad"]')
        box = await signature_pad.bounding_box()
        
        if box:
            # Simulate drawing signature
            await page.mouse.move(box['x'] + 50, box['y'] + 50)
            await page.mouse.down()
            await page.mouse.move(box['x'] + 150, box['y'] + 100)
            await page.mouse.move(box['x'] + 100, box['y'] + 150)
            await page.mouse.up()
        
        await page.tap('[data-testid="save-signature"]')
        
        # Complete delivery
        await page.tap('[data-testid="complete-delivery"]')
        
        # Wait for confirmation
        await expect(page.locator('[data-testid="delivery-success"]')).to_be_visible()
        
        # Auto-navigate to next stop
        await expect(page.locator('[data-testid="next-stop-info"]')).to_be_visible()
        
    @pytest.mark.asyncio
    async def test_handle_delivery_issues(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test handling delivery issues"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/active-route")
        
        # Click on problem stop
        await page.tap('[data-testid="current-stop-card"]')
        
        # Report issue
        await page.tap('[data-testid="report-issue-button"]')
        
        # Select issue type
        await page.select_option('[data-testid="issue-type"]', "customer_not_home")
        
        # Add notes
        await page.fill('[data-testid="issue-notes"]', "按門鈴多次無人應答")
        
        # Take photo of situation
        await page.tap('[data-testid="take-issue-photo"]')
        await page.tap('[data-testid="capture-photo"]')
        await page.tap('[data-testid="use-photo"]')
        
        # Submit issue
        await page.tap('[data-testid="submit-issue"]')
        
        # Wait for confirmation
        await expect(page.locator('[data-testid="issue-reported"]')).to_be_visible()
        
        # Verify stop marked as issue
        await expect(page.locator('[data-testid="stop-status"]')).to_contain_text("有問題")
        
    @pytest.mark.asyncio
    async def test_offline_mode_sync(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test offline mode and data sync"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/active-route")
        
        # Simulate offline mode
        await page.context.set_offline(True)
        
        # Verify offline indicator
        await expect(page.locator('[data-testid="offline-indicator"]')).to_be_visible()
        
        # Complete a delivery while offline
        await page.tap('[data-testid="current-stop-card"]')
        await page.check('[data-testid="delivered-50kg"]')
        await page.fill('[data-testid="delivered-50kg-qty"]', "1")
        await page.select_option('[data-testid="payment-method"]', "cash")
        await page.fill('[data-testid="payment-amount"]', "2500")
        await page.tap('[data-testid="complete-delivery"]')
        
        # Verify saved locally
        await expect(page.locator('[data-testid="pending-sync-badge"]')).to_be_visible()
        
        # Go back online
        await page.context.set_offline(False)
        
        # Wait for sync
        await expect(page.locator('[data-testid="syncing-indicator"]')).to_be_visible()
        await expect(page.locator('[data-testid="sync-complete"]')).to_be_visible(timeout=10000)
        
        # Verify pending sync cleared
        await expect(page.locator('[data-testid="pending-sync-badge"]')).not_to_be_visible()
        
    @pytest.mark.asyncio
    async def test_route_navigation(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test route navigation features"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/active-route")
        
        # Open navigation
        await page.tap('[data-testid="navigate-button"]')
        
        # Choose navigation app
        if await page.locator('[data-testid="nav-app-chooser"]').is_visible():
            await page.tap('[data-testid="use-google-maps"]')
        
        # Verify navigation started (would open external app in real scenario)
        
        # Test route optimization request
        await page.tap('[data-testid="route-options"]')
        await page.tap('[data-testid="optimize-remaining"]')
        
        # Wait for optimization
        await expect(page.locator('[data-testid="optimizing-route"]')).to_be_visible()
        await expect(page.locator('[data-testid="route-optimized"]')).to_be_visible(timeout=5000)
        
        # Check new route order
        await expect(page.locator('[data-testid="route-updated-notice"]')).to_be_visible()
        
    @pytest.mark.asyncio
    async def test_end_of_day_summary(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test end of day summary and reporting"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/active-route")
        
        # Complete all deliveries (mock)
        # Assume we're at the last stop
        
        # Complete route
        await page.tap('[data-testid="complete-route-button"]')
        
        # Confirm completion
        await expect(page.locator('[data-testid="route-summary"]')).to_be_visible()
        
        # Verify summary stats
        await expect(page.locator('[data-testid="total-deliveries"]')).to_be_visible()
        await expect(page.locator('[data-testid="total-collected"]')).to_be_visible()
        await expect(page.locator('[data-testid="delivery-time"]')).to_be_visible()
        await expect(page.locator('[data-testid="issues-count"]')).to_be_visible()
        
        # Add end of day notes
        await page.fill('[data-testid="day-notes"]', "路況良好，所有配送順利完成")
        
        # Submit summary
        await page.tap('[data-testid="submit-summary"]')
        
        # Wait for confirmation
        await expect(page.locator('[data-testid="day-complete"]')).to_be_visible()
        
        # Verify redirected to dashboard
        await page.wait_for_url(f"{BASE_URL}/driver/dashboard")
        
    @pytest.mark.asyncio
    async def test_emergency_contact(self, mobile_context: BrowserContext, driver_authenticated_page: Page):
        """Test emergency contact features"""
        page = driver_authenticated_page
        
        await page.goto(f"{BASE_URL}/driver/dashboard")
        
        # Access emergency contacts
        await page.tap('[data-testid="emergency-button"]')
        
        # Verify emergency options
        await expect(page.locator('[data-testid="call-office"]')).to_be_visible()
        await expect(page.locator('[data-testid="call-manager"]')).to_be_visible()
        await expect(page.locator('[data-testid="send-sos"]')).to_be_visible()
        
        # Test SOS with location
        await page.tap('[data-testid="send-sos"]')
        
        # Confirm SOS
        await expect(page.locator('[data-testid="confirm-sos-dialog"]')).to_be_visible()
        await page.tap('[data-testid="confirm-sos"]')
        
        # Verify SOS sent
        await expect(page.locator('[data-testid="sos-sent"]')).to_be_visible()
        await expect(page.locator('[data-testid="sos-tracking"]')).to_contain_text("位置已分享")