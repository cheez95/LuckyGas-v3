"""
Comprehensive E2E test for driver daily workflow
"""
import asyncio
import json
import os
from datetime import datetime, timedelta

import pytest
from playwright.async_api import BrowserContext, Page, expect

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")


@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.mobile
class TestDriverWorkflowComplete:
    """Test complete driver workflow including mobile experience"""
    
    @pytest.mark.asyncio
    async def test_driver_daily_workflow(
        self,
        browser,
        create_test_order,
        take_screenshot
    ):
        """
        Test complete driver daily workflow:
        1. Driver login on mobile
        2. View assigned routes
        3. Start route and navigation
        4. Deliver orders with real-time updates
        5. Handle special situations
        6. Complete route and report
        """
        
        # Create mobile context
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},  # iPhone 14 Pro
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            has_touch=True,
            is_mobile=True,
            locale="zh-TW"
        )
        
        driver_page = await mobile_context.new_page()
        
        # === Phase 1: Driver Login (Mobile) ===
        await driver_page.goto(f"{BASE_URL}/driver/login")
        await expect(driver_page.locator('[data-testid="driver-login-form"]')).to_be_visible()
        
        # Login with driver credentials
        await driver_page.fill('[name="username"]', "driver1")
        await driver_page.fill('[name="password"]', "driver123")
        await driver_page.tap('[data-testid="login-button"]')
        
        # Wait for dashboard
        await driver_page.wait_for_url(f"{BASE_URL}/driver/dashboard")
        await expect(driver_page.locator('[data-testid="driver-dashboard"]')).to_be_visible()
        await take_screenshot("driver_01_dashboard")
        
        # Check today's summary
        today_orders = await driver_page.locator('[data-testid="today-orders-count"]').text_content()
        today_stops = await driver_page.locator('[data-testid="today-stops-count"]').text_content()
        
        # === Phase 2: View Assigned Routes ===
        await driver_page.tap('[data-testid="view-routes-button"]')
        await expect(driver_page.locator('[data-testid="routes-list"]')).to_be_visible()
        
        # Find today's route
        today_route = driver_page.locator('[data-testid="route-card"]').filter(has_text=datetime.now().strftime("%Y-%m-%d"))
        await expect(today_route).to_be_visible()
        
        # View route details
        await today_route.tap()
        await expect(driver_page.locator('[data-testid="route-detail"]')).to_be_visible()
        
        # Check route information
        total_stops = await driver_page.locator('[data-testid="total-stops"]').text_content()
        estimated_time = await driver_page.locator('[data-testid="estimated-time"]').text_content()
        total_cylinders = await driver_page.locator('[data-testid="total-cylinders"]').text_content()
        
        await take_screenshot("driver_02_route_detail")
        
        # === Phase 3: Start Route ===
        await driver_page.tap('[data-testid="start-route-button"]')
        
        # Confirm vehicle check
        await expect(driver_page.locator('[data-testid="vehicle-check-dialog"]')).to_be_visible()
        await driver_page.check('[data-testid="vehicle-check-safety"]')
        await driver_page.check('[data-testid="vehicle-check-cylinders"]')
        await driver_page.check('[data-testid="vehicle-check-tools"]')
        await driver_page.tap('[data-testid="confirm-vehicle-check"]')
        
        # Route started
        await expect(driver_page.locator('[data-testid="route-status"]')).to_contain_text("進行中")
        await expect(driver_page.locator('[data-testid="navigation-map"]')).to_be_visible()
        
        # === Phase 4: First Delivery ===
        # Navigate to first stop
        await driver_page.tap('[data-testid="stop-0"]')
        await expect(driver_page.locator('[data-testid="stop-detail"]')).to_be_visible()
        
        # Customer information
        customer_name = await driver_page.locator('[data-testid="customer-name"]').text_content()
        customer_phone = await driver_page.locator('[data-testid="customer-phone"]').text_content()
        delivery_address = await driver_page.locator('[data-testid="delivery-address"]').text_content()
        
        # Start navigation (mock)
        await driver_page.tap('[data-testid="navigate-button"]')
        await driver_page.wait_for_timeout(1000)  # Simulate navigation
        
        # Arrive at location
        await driver_page.tap('[data-testid="arrive-button"]')
        await expect(driver_page.locator('[data-testid="delivery-form"]')).to_be_visible()
        
        await take_screenshot("driver_03_delivery_form")
        
        # === Phase 5: Complete Delivery ===
        # Fill delivery details
        await driver_page.fill('[data-testid="delivered-50kg"]', "2")
        await driver_page.fill('[data-testid="collected-50kg-empty"]', "2")
        await driver_page.fill('[data-testid="delivered-20kg"]', "1")
        await driver_page.fill('[data-testid="collected-20kg-empty"]', "1")
        
        # Customer signature
        await driver_page.tap('[data-testid="signature-button"]')
        await expect(driver_page.locator('[data-testid="signature-pad"]')).to_be_visible()
        
        # Simulate drawing signature
        signature_pad = driver_page.locator('[data-testid="signature-pad"]')
        box = await signature_pad.bounding_box()
        if box:
            await driver_page.mouse.move(box['x'] + 50, box['y'] + 50)
            await driver_page.mouse.down()
            await driver_page.mouse.move(box['x'] + 150, box['y'] + 100)
            await driver_page.mouse.move(box['x'] + 100, box['y'] + 150)
            await driver_page.mouse.up()
        
        await driver_page.tap('[data-testid="confirm-signature"]')
        
        # Take delivery photo
        await driver_page.tap('[data-testid="take-photo-button"]')
        # Mock photo capture
        await driver_page.set_input_files('[data-testid="photo-input"]', 'tests/e2e/fixtures/delivery-photo.jpg')
        
        # Add delivery note
        await driver_page.fill('[data-testid="delivery-note"]', "順利送達，客戶簽收")
        
        # Submit delivery
        await driver_page.tap('[data-testid="submit-delivery"]')
        await expect(driver_page.locator('[data-testid="success-toast"]')).to_contain_text("送達完成")
        
        await take_screenshot("driver_04_delivery_complete")
        
        # === Phase 6: Handle Special Situation - Customer Not Home ===
        # Navigate to second stop
        await driver_page.tap('[data-testid="stop-1"]')
        await driver_page.tap('[data-testid="navigate-button"]')
        await driver_page.wait_for_timeout(1000)
        await driver_page.tap('[data-testid="arrive-button"]')
        
        # Customer not home
        await driver_page.tap('[data-testid="customer-not-home-button"]')
        await expect(driver_page.locator('[data-testid="not-home-dialog"]')).to_be_visible()
        
        # Call customer
        await driver_page.tap('[data-testid="call-customer-button"]')
        await driver_page.wait_for_timeout(2000)  # Simulate call
        
        # Leave with neighbor
        await driver_page.tap('[data-testid="leave-with-neighbor"]')
        await driver_page.fill('[data-testid="neighbor-name"]', "王先生 (隔壁)")
        await driver_page.fill('[data-testid="neighbor-unit"]', "5樓")
        
        # Take photo of location
        await driver_page.set_input_files('[data-testid="location-photo"]', 'tests/e2e/fixtures/location-photo.jpg')
        
        await driver_page.tap('[data-testid="confirm-neighbor-delivery"]')
        await expect(driver_page.locator('[data-testid="success-toast"]')).to_contain_text("已託付鄰居")
        
        await take_screenshot("driver_05_neighbor_delivery")
        
        # === Phase 7: Emergency Gas Request ===
        # Receive emergency request notification
        await driver_page.evaluate("""
            window.dispatchEvent(new CustomEvent('emergency-order', {
                detail: {
                    customer: '緊急客戶',
                    address: '台北市信義區緊急路99號',
                    phone: '0911-222-333',
                    distance: '0.5km'
                }
            }));
        """)
        
        await expect(driver_page.locator('[data-testid="emergency-notification"]')).to_be_visible()
        await driver_page.tap('[data-testid="view-emergency-order"]')
        
        # Accept emergency delivery
        await driver_page.tap('[data-testid="accept-emergency"]')
        await expect(driver_page.locator('[data-testid="route-updated-toast"]')).to_contain_text("緊急訂單已加入路線")
        
        # === Phase 8: Complete Remaining Deliveries ===
        # Fast forward through remaining stops
        remaining_stops = await driver_page.locator('[data-testid^="stop-"][data-status="pending"]').count()
        
        for i in range(remaining_stops):
            await driver_page.tap(f'[data-testid="stop-{i + 2}"]')
            await driver_page.tap('[data-testid="quick-complete-button"]')
            await driver_page.fill('[data-testid="quick-delivered-50kg"]', "1")
            await driver_page.tap('[data-testid="quick-submit"]')
            await driver_page.wait_for_timeout(500)
        
        # === Phase 9: Complete Route ===
        await driver_page.tap('[data-testid="complete-route-button"]')
        await expect(driver_page.locator('[data-testid="route-summary"]')).to_be_visible()
        
        # Review route summary
        completed_stops = await driver_page.locator('[data-testid="completed-stops"]').text_content()
        total_delivered = await driver_page.locator('[data-testid="total-cylinders-delivered"]').text_content()
        total_collected = await driver_page.locator('[data-testid="total-cylinders-collected"]').text_content()
        route_duration = await driver_page.locator('[data-testid="route-duration"]').text_content()
        
        await take_screenshot("driver_06_route_summary")
        
        # Submit route completion
        await driver_page.tap('[data-testid="submit-route-completion"]')
        await expect(driver_page.locator('[data-testid="success-message"]')).to_contain_text("路線完成")
        
        # Return to dashboard
        await expect(driver_page).to_have_url(f"{BASE_URL}/driver/dashboard")
        
        # Cleanup
        await mobile_context.close()
    
    @pytest.mark.asyncio
    async def test_driver_gps_tracking(
        self,
        browser,
        office_authenticated_page: Page,
        take_screenshot
    ):
        """Test real-time GPS tracking of driver"""
        
        # Create mobile driver context
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            geolocation={"latitude": 25.0330, "longitude": 121.5654},
            permissions=["geolocation"],
            is_mobile=True,
            locale="zh-TW"
        )
        
        driver_page = await mobile_context.new_page()
        
        # Driver login and start route
        await driver_page.goto(f"{BASE_URL}/driver/login")
        await driver_page.fill('[name="username"]', "driver1")
        await driver_page.fill('[name="password"]', "driver123")
        await driver_page.tap('[data-testid="login-button"]')
        
        # Start route with GPS
        await driver_page.goto(f"{BASE_URL}/driver/routes/today")
        await driver_page.tap('[data-testid="start-route-button"]')
        await driver_page.tap('[data-testid="enable-gps-tracking"]')
        
        # Office staff monitors driver
        office_page = office_authenticated_page
        await office_page.goto(f"{BASE_URL}/dispatch/live-tracking")
        await expect(office_page.locator('[data-testid="live-tracking-map"]')).to_be_visible()
        
        # Simulate driver movement
        locations = [
            {"latitude": 25.0340, "longitude": 121.5664},
            {"latitude": 25.0350, "longitude": 121.5674},
            {"latitude": 25.0360, "longitude": 121.5684}
        ]
        
        for location in locations:
            await driver_page.context.set_geolocation(location)
            await driver_page.wait_for_timeout(2000)
            
            # Verify location update on office side
            driver_marker = office_page.locator('[data-testid="driver-marker-driver1"]')
            await expect(driver_marker).to_be_visible()
        
        await take_screenshot("driver_07_gps_tracking")
        
        # Check driver route history
        await office_page.click('[data-testid="view-route-history"]')
        await expect(office_page.locator('[data-testid="route-playback"]')).to_be_visible()
        
        await mobile_context.close()
    
    @pytest.mark.asyncio
    async def test_driver_offline_mode(
        self,
        browser,
        take_screenshot
    ):
        """Test driver app offline functionality"""
        
        # Create mobile context
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            locale="zh-TW"
        )
        
        driver_page = await mobile_context.new_page()
        
        # Login and cache route data
        await driver_page.goto(f"{BASE_URL}/driver/login")
        await driver_page.fill('[name="username"]', "driver1")
        await driver_page.fill('[name="password"]', "driver123")
        await driver_page.tap('[data-testid="login-button"]')
        
        # Load today's route
        await driver_page.goto(f"{BASE_URL}/driver/routes/today")
        await expect(driver_page.locator('[data-testid="route-detail"]')).to_be_visible()
        
        # Download offline data
        await driver_page.tap('[data-testid="download-offline-data"]')
        await expect(driver_page.locator('[data-testid="offline-ready"]')).to_be_visible()
        
        # Go offline
        await driver_page.context.set_offline(True)
        await expect(driver_page.locator('[data-testid="offline-indicator"]')).to_be_visible()
        
        # Test offline delivery
        await driver_page.tap('[data-testid="stop-0"]')
        await driver_page.tap('[data-testid="arrive-button"]')
        
        # Complete delivery offline
        await driver_page.fill('[data-testid="delivered-50kg"]', "2")
        await driver_page.tap('[data-testid="submit-delivery"]')
        
        # Check offline queue
        await expect(driver_page.locator('[data-testid="offline-queue-badge"]')).to_contain_text("1")
        
        await take_screenshot("driver_08_offline_mode")
        
        # Go back online
        await driver_page.context.set_offline(False)
        await driver_page.wait_for_timeout(2000)
        
        # Verify sync
        await expect(driver_page.locator('[data-testid="sync-success"]')).to_be_visible()
        await expect(driver_page.locator('[data-testid="offline-queue-badge"]')).not.to_be_visible()
        
        await mobile_context.close()
    
    @pytest.mark.asyncio
    async def test_driver_performance_metrics(
        self,
        driver_authenticated_page: Page,
        take_screenshot  
    ):
        """Test driver performance tracking and metrics"""
        
        driver_page = driver_authenticated_page
        
        # View performance dashboard
        await driver_page.goto(f"{BASE_URL}/driver/performance")
        await expect(driver_page.locator('[data-testid="performance-dashboard"]')).to_be_visible()
        
        # Check monthly metrics
        deliveries_count = await driver_page.locator('[data-testid="monthly-deliveries"]').text_content()
        on_time_rate = await driver_page.locator('[data-testid="on-time-rate"]').text_content()
        customer_rating = await driver_page.locator('[data-testid="customer-rating"]').text_content()
        
        assert int(deliveries_count) > 0
        assert "%" in on_time_rate
        assert float(customer_rating.replace("★", "")) >= 0
        
        # View detailed metrics
        await driver_page.click('[data-testid="view-details"]')
        
        # Check delivery history
        await expect(driver_page.locator('[data-testid="delivery-history-table"]')).to_be_visible()
        delivery_rows = driver_page.locator('[data-testid="delivery-row"]')
        assert await delivery_rows.count() > 0
        
        # Check route efficiency
        await driver_page.click('[data-testid="efficiency-tab"]')
        await expect(driver_page.locator('[data-testid="efficiency-chart"]')).to_be_visible()
        
        avg_stops_per_hour = await driver_page.locator('[data-testid="avg-stops-per-hour"]').text_content()
        avg_distance_per_stop = await driver_page.locator('[data-testid="avg-distance-per-stop"]').text_content()
        
        await take_screenshot("driver_09_performance_metrics")