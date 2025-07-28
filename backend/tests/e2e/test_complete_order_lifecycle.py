"""
End-to-end test for complete order lifecycle from creation to payment
"""
import pytest
from playwright.async_api import Page, expect
from datetime import datetime, timedelta
import asyncio
import os

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")
API_URL = os.getenv("E2E_API_URL", "http://localhost:8000")


@pytest.mark.e2e
@pytest.mark.critical
class TestCompleteOrderLifecycle:
    """Test the complete order lifecycle from creation to payment completion"""
    
    @pytest.mark.asyncio
    async def test_full_order_lifecycle(
        self, 
        authenticated_page: Page,
        admin_authenticated_page: Page,
        driver_authenticated_page: Page,
        take_screenshot
    ):
        """
        Test complete order flow:
        1. Office staff creates order
        2. Office staff confirms order
        3. Office staff assigns to route/driver
        4. Driver views and accepts route
        5. Driver delivers order
        6. Office staff generates invoice
        7. Office staff records payment
        """
        
        # === Phase 1: Order Creation (Office Staff) ===
        office_page = authenticated_page
        await office_page.goto(f"{BASE_URL}/orders")
        await take_screenshot("01_orders_page")
        
        # Create new order
        await office_page.click('[data-testid="create-order-button"]')
        await expect(office_page.locator('[data-testid="order-form"]')).to_be_visible()
        
        # Select customer
        await office_page.click('[data-testid="select-customer"]')
        await office_page.fill('[data-testid="customer-search"]', "測試客戶")
        await office_page.wait_for_timeout(500)
        await office_page.click('[data-testid="customer-option"]:first-child')
        
        # Set delivery date (tomorrow)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await office_page.fill('[name="scheduled_date"]', tomorrow)
        
        # Add products
        await office_page.fill('[data-testid="qty-50kg"]', "2")
        await office_page.fill('[data-testid="qty-20kg"]', "1")
        await office_page.fill('[data-testid="qty-10kg"]', "3")
        
        # Add delivery notes
        await office_page.fill('[name="delivery_notes"]', "請於下午送達，需電話聯絡")
        
        # Submit order
        await office_page.click('[data-testid="submit-order"]')
        await expect(office_page.locator('[data-testid="success-message"]')).to_contain_text("訂單建立成功")
        
        # Get order number from URL or success message
        await office_page.wait_for_url_pattern(f"{BASE_URL}/orders/*")
        order_url = office_page.url
        order_id = order_url.split('/')[-1]
        await take_screenshot("02_order_created")
        
        # === Phase 2: Order Confirmation ===
        await office_page.click('[data-testid="confirm-order-button"]')
        await office_page.click('[data-testid="confirm-action"]')
        await expect(office_page.locator('[data-testid="success-message"]')).to_contain_text("訂單已確認")
        await expect(office_page.locator('[data-testid="current-status"]')).to_contain_text("已確認")
        await take_screenshot("03_order_confirmed")
        
        # === Phase 3: Route Assignment ===
        await office_page.goto(f"{BASE_URL}/routes/planning")
        await expect(office_page.locator('[data-testid="route-planning"]')).to_be_visible()
        
        # Find our order in unassigned list
        await office_page.fill('[data-testid="order-search"]', order_id)
        await office_page.wait_for_timeout(500)
        
        # Select the order
        await office_page.check(f'[data-testid="order-checkbox-{order_id}"]')
        
        # Create new route
        await office_page.click('[data-testid="create-route-button"]')
        
        # Select driver
        await office_page.select_option('[data-testid="select-driver"]', {"index": 1})
        
        # Optimize route
        await office_page.click('[data-testid="optimize-route"]')
        await expect(office_page.locator('[data-testid="optimization-complete"]')).to_be_visible(timeout=10000)
        
        # Save route
        await office_page.click('[data-testid="save-route"]')
        await expect(office_page.locator('[data-testid="success-message"]')).to_contain_text("路線已建立")
        
        # Get route ID
        route_id = await office_page.locator('[data-testid="route-id"]').text_content()
        await take_screenshot("04_route_assigned")
        
        # === Phase 4: Driver Accepts and Delivers (Driver Interface) ===
        driver_page = driver_authenticated_page
        await driver_page.goto(f"{BASE_URL}/driver/routes")
        await expect(driver_page.locator('[data-testid="driver-routes"]')).to_be_visible()
        
        # Find assigned route
        await driver_page.click(f'[data-testid="route-{route_id}"]')
        await expect(driver_page.locator('[data-testid="route-detail"]')).to_be_visible()
        
        # Start route
        await driver_page.click('[data-testid="start-route-button"]')
        await expect(driver_page.locator('[data-testid="route-status"]')).to_contain_text("進行中")
        await take_screenshot("05_route_started")
        
        # Navigate to first delivery (our order)
        await driver_page.click('[data-testid="delivery-stop-0"]')
        await expect(driver_page.locator('[data-testid="delivery-detail"]')).to_be_visible()
        
        # Complete delivery
        await driver_page.click('[data-testid="complete-delivery-button"]')
        
        # Fill delivery details
        await driver_page.fill('[data-testid="delivered-50kg"]', "2")
        await driver_page.fill('[data-testid="delivered-20kg"]', "1") 
        await driver_page.fill('[data-testid="delivered-10kg"]', "3")
        
        # Add signature (simulate)
        await driver_page.click('[data-testid="signature-pad"]')
        await driver_page.mouse.move(100, 100)
        await driver_page.mouse.down()
        await driver_page.mouse.move(200, 150)
        await driver_page.mouse.move(150, 200)
        await driver_page.mouse.up()
        
        # Take delivery photo (mock)
        await driver_page.set_input_files('[data-testid="delivery-photo"]', 'tests/e2e/fixtures/test-delivery-photo.jpg')
        
        # Submit delivery
        await driver_page.click('[data-testid="submit-delivery"]')
        await expect(driver_page.locator('[data-testid="success-message"]')).to_contain_text("送達完成")
        await take_screenshot("06_delivery_completed")
        
        # === Phase 5: Invoice Generation (Back to Office Staff) ===
        await office_page.goto(f"{BASE_URL}/orders/{order_id}")
        await expect(office_page.locator('[data-testid="current-status"]')).to_contain_text("已送達")
        
        # Generate invoice
        await office_page.click('[data-testid="generate-invoice-button"]')
        await expect(office_page.locator('[data-testid="invoice-form"]')).to_be_visible()
        
        # Confirm invoice details
        await office_page.click('[data-testid="confirm-invoice"]')
        await expect(office_page.locator('[data-testid="success-message"]')).to_contain_text("發票已開立")
        
        # Get invoice number
        invoice_number = await office_page.locator('[data-testid="invoice-number"]').text_content()
        await take_screenshot("07_invoice_generated")
        
        # === Phase 6: Payment Recording ===
        await office_page.goto(f"{BASE_URL}/invoices")
        await office_page.fill('[data-testid="invoice-search"]', invoice_number)
        await office_page.wait_for_timeout(500)
        
        # Click on the invoice
        await office_page.click(f'[data-testid="invoice-{invoice_number}"]')
        await expect(office_page.locator('[data-testid="invoice-detail"]')).to_be_visible()
        
        # Record payment
        await office_page.click('[data-testid="record-payment-button"]')
        await expect(office_page.locator('[data-testid="payment-form"]')).to_be_visible()
        
        # Fill payment details
        await office_page.select_option('[data-testid="payment-method"]', "cash")
        await office_page.fill('[data-testid="payment-amount"]', await office_page.locator('[data-testid="invoice-total"]').text_content())
        await office_page.fill('[data-testid="payment-date"]', datetime.now().strftime("%Y-%m-%d"))
        await office_page.fill('[data-testid="payment-notes"]', "現金收款")
        
        # Submit payment
        await office_page.click('[data-testid="submit-payment"]')
        await expect(office_page.locator('[data-testid="success-message"]')).to_contain_text("付款已記錄")
        await expect(office_page.locator('[data-testid="invoice-status"]')).to_contain_text("已付款")
        await take_screenshot("08_payment_recorded")
        
        # === Phase 7: Verify Complete Lifecycle ===
        # Check order shows as completed with payment
        await office_page.goto(f"{BASE_URL}/orders/{order_id}")
        await expect(office_page.locator('[data-testid="order-status"]')).to_contain_text("已完成")
        await expect(office_page.locator('[data-testid="payment-status"]')).to_contain_text("已付款")
        
        # Verify timeline shows all steps
        timeline_items = office_page.locator('[data-testid="timeline-item"]')
        timeline_count = await timeline_items.count()
        assert timeline_count >= 6  # Created, Confirmed, Assigned, Delivered, Invoiced, Paid
        
        await take_screenshot("09_complete_lifecycle")
    
    @pytest.mark.asyncio
    async def test_order_with_route_optimization(
        self, 
        authenticated_page: Page,
        create_test_customer,
        take_screenshot
    ):
        """Test order creation with route optimization for multiple orders"""
        
        # Create test customers in different areas
        customers = []
        for i in range(3):
            customer = await create_test_customer({
                "customer_code": f"TEST_ROUTE_{i}",
                "short_name": f"路線測試客戶{i}",
                "address": f"台北市信義區測試路{(i+1)*100}號",
                "area": "信義區",
                "latitude": 25.0330 + (i * 0.01),
                "longitude": 121.5654 + (i * 0.01)
            })
            customers.append(customer)
        
        # Create orders for each customer
        office_page = authenticated_page
        order_ids = []
        
        for i, customer in enumerate(customers):
            await office_page.goto(f"{BASE_URL}/orders/new")
            
            # Quick order creation
            await office_page.fill('[data-testid="customer-code"]', customer["customer_code"])
            await office_page.fill('[name="scheduled_date"]', (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))
            await office_page.fill('[data-testid="qty-50kg"]', str(i + 1))
            await office_page.click('[data-testid="submit-order"]')
            
            # Get order ID
            await office_page.wait_for_url_pattern(f"{BASE_URL}/orders/*")
            order_id = office_page.url.split('/')[-1]
            order_ids.append(order_id)
        
        # Go to route planning
        await office_page.goto(f"{BASE_URL}/routes/planning")
        
        # Select all orders
        for order_id in order_ids:
            await office_page.check(f'[data-testid="order-checkbox-{order_id}"]')
        
        # Create optimized route
        await office_page.click('[data-testid="create-route-button"]')
        await office_page.select_option('[data-testid="select-driver"]', {"index": 1})
        await office_page.click('[data-testid="optimize-route"]')
        
        # Wait for optimization
        await expect(office_page.locator('[data-testid="optimization-progress"]')).to_be_visible()
        await expect(office_page.locator('[data-testid="optimization-complete"]')).to_be_visible(timeout=15000)
        
        # Verify optimized order
        optimized_stops = office_page.locator('[data-testid="route-stop"]')
        stop_count = await optimized_stops.count()
        assert stop_count == 3
        
        # Check optimization metrics
        total_distance = await office_page.locator('[data-testid="total-distance"]').text_content()
        estimated_time = await office_page.locator('[data-testid="estimated-time"]').text_content()
        
        assert "km" in total_distance
        assert "分鐘" in estimated_time
        
        await take_screenshot("10_optimized_route")
    
    @pytest.mark.asyncio
    async def test_urgent_order_handling(
        self, 
        authenticated_page: Page,
        driver_authenticated_page: Page,
        take_screenshot
    ):
        """Test urgent order creation and priority handling"""
        
        office_page = authenticated_page
        
        # Create urgent order
        await office_page.goto(f"{BASE_URL}/orders/new")
        
        # Fill urgent order details
        await office_page.click('[data-testid="select-customer"]')
        await office_page.fill('[data-testid="customer-search"]', "緊急")
        await office_page.wait_for_timeout(500)
        await office_page.click('[data-testid="customer-option"]:first-child')
        
        await office_page.fill('[name="scheduled_date"]', datetime.now().strftime("%Y-%m-%d"))  # Today
        await office_page.fill('[data-testid="qty-50kg"]', "5")
        await office_page.check('[name="is_urgent"]')
        await office_page.fill('[name="delivery_notes"]', "緊急！客戶瓦斯用完")
        
        await office_page.click('[data-testid="submit-order"]')
        await expect(office_page.locator('[data-testid="urgent-badge"]')).to_be_visible()
        
        # Verify urgent order appears at top of list
        await office_page.goto(f"{BASE_URL}/orders")
        first_order = office_page.locator('[data-testid="order-card"]').first
        await expect(first_order.locator('[data-testid="urgent-badge"]')).to_be_visible()
        
        # Check notification was sent
        await expect(office_page.locator('[data-testid="notification-toast"]')).to_contain_text("緊急訂單")
        
        await take_screenshot("11_urgent_order")
    
    @pytest.mark.asyncio 
    async def test_order_cancellation_flow(
        self,
        authenticated_page: Page,
        take_screenshot
    ):
        """Test order cancellation at different stages"""
        
        office_page = authenticated_page
        
        # Create a test order
        await office_page.goto(f"{BASE_URL}/orders/new")
        await office_page.click('[data-testid="select-customer"]')
        await office_page.fill('[data-testid="customer-search"]', "取消測試")
        await office_page.wait_for_timeout(500)
        await office_page.click('[data-testid="customer-option"]:first-child')
        await office_page.fill('[name="scheduled_date"]', (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
        await office_page.fill('[data-testid="qty-20kg"]', "2")
        await office_page.click('[data-testid="submit-order"]')
        
        # Cancel before confirmation
        await office_page.click('[data-testid="cancel-order-button"]')
        await office_page.fill('[data-testid="cancel-reason"]', "客戶改變主意")
        await office_page.click('[data-testid="confirm-cancel"]')
        
        await expect(office_page.locator('[data-testid="order-status"]')).to_contain_text("已取消")
        await expect(office_page.locator('[data-testid="cancel-reason-display"]')).to_contain_text("客戶改變主意")
        
        # Verify cannot perform actions on cancelled order
        await expect(office_page.locator('[data-testid="confirm-order-button"]')).not.to_be_visible()
        await expect(office_page.locator('[data-testid="generate-invoice-button"]')).not.to_be_visible()
        
        await take_screenshot("12_cancelled_order")