"""
End-to-end tests for order management flow using Playwright
"""
import os
from datetime import datetime, timedelta
from typing import Dict

import pytest
from playwright.async_api import Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")


@pytest.mark.e2e
class TestOrderFlow:
    """Test complete order management flow"""
    
    @pytest.mark.asyncio
    async def test_create_order_flow(self, authenticated_page: Page):
        """Test creating a new order through the UI"""
        page = authenticated_page
        
        # Navigate to orders page
        await page.goto(f"{BASE_URL}/orders")
        
        # Click create order button
        await page.click('[data-testid="create-order-button"]')
        
        # Wait for order form
        await expect(page.locator('[data-testid="order-form"]')).to_be_visible()
        
        # Step 1: Select customer
        await page.click('[data-testid="select-customer"]')
        
        # Search for customer
        await page.fill('[data-testid="customer-search"]', "測試")
        await page.wait_for_timeout(500)  # Debounce
        
        # Select first customer from results
        await page.click('[data-testid="customer-option"]:first-child')
        
        # Step 2: Select delivery date
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await page.fill('[name="scheduled_date"]', tomorrow)
        
        # Step 3: Add products
        # Add 50kg cylinders
        await page.fill('[data-testid="qty-50kg"]', "2")
        
        # Add 20kg cylinders
        await page.fill('[data-testid="qty-20kg"]', "3")
        
        # Add 4kg cylinders
        await page.fill('[data-testid="qty-4kg"]', "1")
        
        # Check urgent delivery
        await page.check('[name="is_urgent"]')
        
        # Add delivery notes
        await page.fill('[name="delivery_notes"]', "請於下午2-4點送達")
        
        # Verify total amount is calculated
        total_amount = await page.locator('[data-testid="total-amount"]').text_content()
        assert "NT$" in total_amount
        assert int(total_amount.replace("NT$", "").replace(",", "")) > 0
        
        # Submit order
        await page.click('[data-testid="submit-order"]')
        
        # Wait for success message
        await expect(page.locator('[data-testid="success-message"]')).to_be_visible()
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("訂單建立成功")
        
        # Verify redirected to order detail
        await page.wait_for_url_pattern(f"{BASE_URL}/orders/*")
        
    @pytest.mark.asyncio
    async def test_order_list_view(self, authenticated_page: Page):
        """Test viewing and filtering order list"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders")
        
        # Wait for order list to load
        await expect(page.locator('[data-testid="order-list"]')).to_be_visible()
        
        # Test status filter
        await page.select_option('[data-testid="status-filter"]', "pending")
        await page.wait_for_timeout(500)
        
        # Verify filtered results
        status_badges = page.locator('[data-testid="order-status"]')
        count = await status_badges.count()
        
        for i in range(count):
            status = await status_badges.nth(i).text_content()
            assert "待處理" in status
            
        # Test date range filter
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        await page.fill('[data-testid="date-from"]', today)
        await page.fill('[data-testid="date-to"]', next_week)
        await page.click('[data-testid="apply-filters"]')
        
        # Wait for filtered results
        await page.wait_for_timeout(500)
        
        # Test urgent orders filter
        await page.check('[data-testid="urgent-only"]')
        await page.wait_for_timeout(500)
        
        # Verify all orders show urgent badge
        urgent_badges = page.locator('[data-testid="urgent-badge"]')
        urgent_count = await urgent_badges.count()
        orders_count = await page.locator('[data-testid="order-card"]').count()
        assert urgent_count == orders_count
        
    @pytest.mark.asyncio
    async def test_order_detail_view(self, authenticated_page: Page):
        """Test viewing order details"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders")
        
        # Click on first order
        await page.click('[data-testid="order-card"]:first-child')
        
        # Wait for detail view
        await expect(page.locator('[data-testid="order-detail"]')).to_be_visible()
        
        # Verify order information sections
        await expect(page.locator('[data-testid="customer-info"]')).to_be_visible()
        await expect(page.locator('[data-testid="product-list"]')).to_be_visible()
        await expect(page.locator('[data-testid="delivery-info"]')).to_be_visible()
        await expect(page.locator('[data-testid="payment-info"]')).to_be_visible()
        
        # Check order timeline
        await expect(page.locator('[data-testid="order-timeline"]')).to_be_visible()
        
        # Check action buttons based on status
        order_status = await page.locator('[data-testid="current-status"]').text_content()
        
        if "待處理" in order_status:
            await expect(page.locator('[data-testid="confirm-order-button"]')).to_be_visible()
            await expect(page.locator('[data-testid="cancel-order-button"]')).to_be_visible()
            
    @pytest.mark.asyncio
    async def test_confirm_order(self, authenticated_page: Page):
        """Test confirming a pending order"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders")
        
        # Find a pending order
        pending_order = page.locator('[data-testid="order-card"]:has-text("待處理")').first
        order_number = await pending_order.locator('[data-testid="order-number"]').text_content()
        
        # Click on the order
        await pending_order.click()
        
        # Wait for detail view
        await expect(page.locator('[data-testid="order-detail"]')).to_be_visible()
        
        # Click confirm button
        await page.click('[data-testid="confirm-order-button"]')
        
        # Handle confirmation dialog
        await expect(page.locator('[data-testid="confirm-dialog"]')).to_be_visible()
        await page.click('[data-testid="confirm-action"]')
        
        # Wait for success message
        await expect(page.locator('[data-testid="success-message"]')).to_be_visible()
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("訂單已確認")
        
        # Verify status changed
        await expect(page.locator('[data-testid="current-status"]')).to_contain_text("已確認")
        
    @pytest.mark.asyncio
    async def test_assign_to_route(self, authenticated_page: Page):
        """Test assigning orders to delivery routes"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders")
        
        # Switch to route planning view
        await page.click('[data-testid="route-planning-tab"]')
        
        # Wait for unassigned orders
        await expect(page.locator('[data-testid="unassigned-orders"]')).to_be_visible()
        
        # Select multiple orders
        await page.check('[data-testid="order-checkbox"]:nth-child(1)')
        await page.check('[data-testid="order-checkbox"]:nth-child(2)')
        await page.check('[data-testid="order-checkbox"]:nth-child(3)')
        
        # Click assign to route
        await page.click('[data-testid="assign-route-button"]')
        
        # Select driver
        await page.select_option('[data-testid="select-driver"]', {"index": 1})
        
        # Optimize route
        await page.click('[data-testid="optimize-route"]')
        
        # Wait for optimization
        await expect(page.locator('[data-testid="optimization-progress"]')).to_be_visible()
        await expect(page.locator('[data-testid="optimization-complete"]')).to_be_visible(timeout=10000)
        
        # Review optimized route
        await expect(page.locator('[data-testid="route-map"]')).to_be_visible()
        await expect(page.locator('[data-testid="route-stops"]')).to_be_visible()
        
        # Confirm route
        await page.click('[data-testid="confirm-route"]')
        
        # Wait for success
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("路線已建立")
        
    @pytest.mark.asyncio
    async def test_update_order_quantities(self, authenticated_page: Page):
        """Test updating order quantities"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders")
        
        # Find an editable order (pending or confirmed)
        editable_order = page.locator('[data-testid="order-card"]:has-text("待處理"), [data-testid="order-card"]:has-text("已確認")').first
        await editable_order.click()
        
        # Click edit button
        await page.click('[data-testid="edit-order-button"]')
        
        # Wait for edit form
        await expect(page.locator('[data-testid="order-edit-form"]')).to_be_visible()
        
        # Update quantities
        await page.fill('[data-testid="qty-50kg"]', "5")
        await page.fill('[data-testid="qty-20kg"]', "2")
        
        # Verify total recalculates
        await page.wait_for_timeout(500)  # Wait for calculation
        new_total = await page.locator('[data-testid="total-amount"]').text_content()
        assert "NT$" in new_total
        
        # Save changes
        await page.click('[data-testid="save-changes"]')
        
        # Wait for success
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("訂單已更新")
        
    @pytest.mark.asyncio
    async def test_cancel_order_flow(self, authenticated_page: Page):
        """Test cancelling an order"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders")
        
        # Find a cancellable order
        cancellable_order = page.locator('[data-testid="order-card"]:has-text("待處理"), [data-testid="order-card"]:has-text("已確認")').first
        order_number = await cancellable_order.locator('[data-testid="order-number"]').text_content()
        
        await cancellable_order.click()
        
        # Click cancel button
        await page.click('[data-testid="cancel-order-button"]')
        
        # Fill cancellation reason
        await expect(page.locator('[data-testid="cancel-dialog"]')).to_be_visible()
        await page.fill('[data-testid="cancel-reason"]', "客戶要求取消")
        
        # Confirm cancellation
        await page.click('[data-testid="confirm-cancel"]')
        
        # Wait for success
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("訂單已取消")
        
        # Verify status changed
        await expect(page.locator('[data-testid="current-status"]')).to_contain_text("已取消")
        
    @pytest.mark.asyncio
    async def test_order_statistics_dashboard(self, authenticated_page: Page):
        """Test order statistics dashboard"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/orders/statistics")
        
        # Wait for stats to load
        await expect(page.locator('[data-testid="stats-dashboard"]')).to_be_visible()
        
        # Verify stat cards
        await expect(page.locator('[data-testid="total-orders-stat"]')).to_be_visible()
        await expect(page.locator('[data-testid="pending-orders-stat"]')).to_be_visible()
        await expect(page.locator('[data-testid="revenue-stat"]')).to_be_visible()
        await expect(page.locator('[data-testid="delivery-rate-stat"]')).to_be_visible()
        
        # Check charts
        await expect(page.locator('[data-testid="orders-by-status-chart"]')).to_be_visible()
        await expect(page.locator('[data-testid="revenue-trend-chart"]')).to_be_visible()
        await expect(page.locator('[data-testid="orders-by-area-chart"]')).to_be_visible()
        
        # Test date range selector
        await page.select_option('[data-testid="stats-period"]', "last_30_days")
        await page.wait_for_timeout(1000)  # Wait for data refresh
        
        # Export report
        await page.click('[data-testid="export-report"]')
        await page.select_option('[data-testid="export-format"]', "excel")
        
        # Start download
        const [download] = await Promise.all([
            page.wait_for_event('download'),
            page.click('[data-testid="download-report"]')
        ])
        
        # Verify download
        assert download.suggested_filename.endswith('.xlsx')