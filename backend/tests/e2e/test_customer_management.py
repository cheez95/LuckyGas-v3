"""
End-to-end tests for customer management using Playwright
"""
import os
from typing import Dict

import pytest
from playwright.async_api import Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")


@pytest.mark.e2e
class TestCustomerManagement:
    """Test complete customer management flow"""
    
    @pytest.mark.asyncio
    async def test_create_customer_flow(self, authenticated_page: Page):
        """Test creating a new customer through the UI"""
        page = authenticated_page
        
        # Navigate to customers page
        await page.goto(f"{BASE_URL}/customers")
        
        # Click add customer button
        await page.click('[data-testid="add-customer-button"]')
        
        # Wait for modal/form to appear
        await expect(page.locator('[data-testid="customer-form"]')).to_be_visible()
        
        # Fill in customer details
        await page.fill('[name="customer_code"]', "C-TEST-001")
        await page.fill('[name="short_name"]', "測試客戶 E2E")
        await page.fill('[name="invoice_title"]', "測試公司 E2E")
        await page.fill('[name="tax_id"]', "12345678")
        await page.fill('[name="address"]', "台北市信義區測試路123號")
        await page.fill('[name="phone1"]', "0912-345-678")
        await page.fill('[name="contact_person"]', "王小明")
        
        # Select area
        await page.select_option('[name="area"]', "信義區")
        
        # Check corporate customer
        await page.check('[name="is_corporate"]')
        
        # Submit form
        await page.click('[data-testid="submit-customer"]')
        
        # Wait for success message
        await expect(page.locator('[data-testid="success-message"]')).to_be_visible()
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("客戶新增成功")
        
        # Verify customer appears in list
        await expect(page.locator('text="測試客戶 E2E"')).to_be_visible()
        
    @pytest.mark.asyncio
    async def test_search_customers(self, authenticated_page: Page):
        """Test searching for customers"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Wait for customer list to load
        await expect(page.locator('[data-testid="customer-list"]')).to_be_visible()
        
        # Search by customer code
        await page.fill('[data-testid="search-input"]', "C-TEST")
        await page.click('[data-testid="search-button"]')
        
        # Wait for filtered results
        await page.wait_for_timeout(500)  # Wait for debounce
        
        # Verify search results
        customer_cards = page.locator('[data-testid="customer-card"]')
        count = await customer_cards.count()
        assert count > 0
        
        # Verify all results contain search term
        for i in range(count):
            card_text = await customer_cards.nth(i).text_content()
            assert "C-TEST" in card_text
            
    @pytest.mark.asyncio
    async def test_filter_by_area(self, authenticated_page: Page):
        """Test filtering customers by area"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Select area filter
        await page.select_option('[data-testid="area-filter"]', "信義區")
        
        # Wait for filtered results
        await page.wait_for_timeout(500)
        
        # Verify all customers are from selected area
        area_tags = page.locator('[data-testid="customer-area"]')
        count = await area_tags.count()
        
        for i in range(count):
            area_text = await area_tags.nth(i).text_content()
            assert "信義區" in area_text
            
    @pytest.mark.asyncio
    async def test_edit_customer(self, authenticated_page: Page):
        """Test editing an existing customer"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Click edit on first customer
        await page.click('[data-testid="customer-card"]:first-child [data-testid="edit-button"]')
        
        # Wait for form to load with data
        await expect(page.locator('[data-testid="customer-form"]')).to_be_visible()
        
        # Verify form is pre-filled
        short_name_input = page.locator('[name="short_name"]')
        existing_value = await short_name_input.input_value()
        assert existing_value != ""
        
        # Update phone number
        await page.fill('[name="phone1"]', "0987-654-321")
        
        # Add delivery notes
        await page.fill('[name="delivery_notes"]', "請按門鈴，勿按電鈴")
        
        # Submit changes
        await page.click('[data-testid="submit-customer"]')
        
        # Wait for success message
        await expect(page.locator('[data-testid="success-message"]')).to_be_visible()
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("客戶更新成功")
        
    @pytest.mark.asyncio
    async def test_customer_detail_view(self, authenticated_page: Page):
        """Test viewing customer details"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Click on customer to view details
        await page.click('[data-testid="customer-card"]:first-child')
        
        # Wait for detail view
        await expect(page.locator('[data-testid="customer-detail"]')).to_be_visible()
        
        # Verify sections are present
        await expect(page.locator('[data-testid="basic-info-section"]')).to_be_visible()
        await expect(page.locator('[data-testid="contact-info-section"]')).to_be_visible()
        await expect(page.locator('[data-testid="delivery-info-section"]')).to_be_visible()
        
        # Check for order history tab
        await page.click('[data-testid="order-history-tab"]')
        await expect(page.locator('[data-testid="order-history-list"]')).to_be_visible()
        
        # Check for inventory tab
        await page.click('[data-testid="inventory-tab"]')
        await expect(page.locator('[data-testid="inventory-list"]')).to_be_visible()
        
    @pytest.mark.asyncio
    async def test_deactivate_customer(self, authenticated_page: Page, admin_authenticated_page: Page):
        """Test deactivating a customer (admin only)"""
        page = admin_authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Find an active customer
        first_customer = page.locator('[data-testid="customer-card"]:first-child')
        customer_name = await first_customer.locator('[data-testid="customer-name"]').text_content()
        
        # Click more options
        await first_customer.locator('[data-testid="more-options"]').click()
        
        # Click deactivate
        await page.click('[data-testid="deactivate-customer"]')
        
        # Confirm deactivation
        await expect(page.locator('[data-testid="confirm-dialog"]')).to_be_visible()
        await page.click('[data-testid="confirm-deactivate"]')
        
        # Wait for success message
        await expect(page.locator('[data-testid="success-message"]')).to_be_visible()
        await expect(page.locator('[data-testid="success-message"]')).to_contain_text("客戶已停用")
        
        # Verify customer shows as inactive
        await expect(first_customer.locator('[data-testid="inactive-badge"]')).to_be_visible()
        
    @pytest.mark.asyncio
    async def test_bulk_import_customers(self, admin_authenticated_page: Page):
        """Test bulk importing customers from Excel"""
        page = admin_authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Click import button
        await page.click('[data-testid="import-customers-button"]')
        
        # Wait for import dialog
        await expect(page.locator('[data-testid="import-dialog"]')).to_be_visible()
        
        # Upload file
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files("tests/fixtures/sample_customers.xlsx")
        
        # Preview data
        await page.click('[data-testid="preview-import"]')
        
        # Wait for preview table
        await expect(page.locator('[data-testid="import-preview-table"]')).to_be_visible()
        
        # Verify preview shows data
        preview_rows = page.locator('[data-testid="preview-row"]')
        count = await preview_rows.count()
        assert count > 0
        
        # Confirm import
        await page.click('[data-testid="confirm-import"]')
        
        # Wait for progress bar
        await expect(page.locator('[data-testid="import-progress"]')).to_be_visible()
        
        # Wait for completion
        await expect(page.locator('[data-testid="import-complete"]')).to_be_visible(timeout=30000)
        
        # Check import results
        results_text = await page.locator('[data-testid="import-results"]').text_content()
        assert "成功" in results_text
        
    @pytest.mark.asyncio
    async def test_customer_pagination(self, authenticated_page: Page):
        """Test customer list pagination"""
        page = authenticated_page
        
        await page.goto(f"{BASE_URL}/customers")
        
        # Wait for customer list
        await expect(page.locator('[data-testid="customer-list"]')).to_be_visible()
        
        # Check pagination controls
        await expect(page.locator('[data-testid="pagination"]')).to_be_visible()
        
        # Get first page customer
        first_page_customer = await page.locator('[data-testid="customer-card"]:first-child [data-testid="customer-name"]').text_content()
        
        # Go to next page
        await page.click('[data-testid="next-page"]')
        
        # Wait for new data
        await page.wait_for_timeout(500)
        
        # Get new first customer
        second_page_customer = await page.locator('[data-testid="customer-card"]:first-child [data-testid="customer-name"]').text_content()
        
        # Verify different customer
        assert first_page_customer != second_page_customer
        
        # Go back to first page
        await page.click('[data-testid="prev-page"]')
        
        # Verify back on first page
        current_first_customer = await page.locator('[data-testid="customer-card"]:first-child [data-testid="customer-name"]').text_content()
        assert current_first_customer == first_page_customer