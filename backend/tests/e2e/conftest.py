"""
Configuration and fixtures for E2E tests using Playwright
"""
import pytest
import asyncio
from typing import Dict, Generator
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import os
from datetime import datetime

# Test configuration
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000")
API_URL = os.getenv("E2E_API_URL", "http://localhost:8000")
HEADLESS = os.getenv("E2E_HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("E2E_SLOW_MO", "0"))  # Milliseconds to slow down operations


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO
        )
        yield browser
        await browser.close()


@pytest.fixture(scope="function")
async def context(browser: Browser) -> BrowserContext:
    """Create browser context for each test"""
    context = await browser.new_context(
        base_url=BASE_URL,
        viewport={"width": 1280, "height": 720},
        locale="zh-TW",  # Traditional Chinese locale
        timezone_id="Asia/Taipei"
    )
    
    # Add auth state if exists
    auth_file = "tests/e2e/.auth/state.json"
    if os.path.exists(auth_file):
        await context.add_cookies(auth_file)
    
    yield context
    await context.close()


@pytest.fixture(scope="function")
async def page(context: BrowserContext) -> Page:
    """Create page for each test"""
    page = await context.new_page()
    yield page
    await page.close()


# Test user credentials
@pytest.fixture
def test_credentials() -> Dict[str, str]:
    """Test user credentials"""
    return {
        "email": "test@example.com",
        "password": "testpass123",
        "role": "office_staff"
    }


@pytest.fixture
def admin_credentials() -> Dict[str, str]:
    """Admin user credentials"""
    return {
        "email": "admin@example.com",
        "password": "adminpass123",
        "role": "super_admin"
    }


@pytest.fixture
def driver_credentials() -> Dict[str, str]:
    """Driver user credentials"""
    return {
        "email": "driver@example.com",
        "password": "driverpass123",
        "role": "driver"
    }


@pytest.fixture
def office_credentials() -> Dict[str, str]:
    """Office staff credentials"""
    return {
        "email": "office@example.com",
        "password": "officepass123",
        "role": "office_staff"
    }


# Authenticated page fixtures
@pytest.fixture
async def authenticated_page(page: Page, test_credentials: Dict[str, str]) -> Page:
    """Create authenticated page for office staff"""
    # Login
    await page.goto(f"{BASE_URL}/login")
    await page.fill('input[name="email"]', test_credentials["email"])
    await page.fill('input[name="password"]', test_credentials["password"])
    await page.click('button[type="submit"]')
    
    # Wait for redirect
    await page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
    
    return page


@pytest.fixture
async def admin_authenticated_page(page: Page, admin_credentials: Dict[str, str]) -> Page:
    """Create authenticated page for admin"""
    # Login
    await page.goto(f"{BASE_URL}/login")
    await page.fill('input[name="email"]', admin_credentials["email"])
    await page.fill('input[name="password"]', admin_credentials["password"])
    await page.click('button[type="submit"]')
    
    # Wait for redirect
    await page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
    
    return page


@pytest.fixture
async def driver_authenticated_page(page: Page, driver_credentials: Dict[str, str]) -> Page:
    """Create authenticated page for driver"""
    # Login
    await page.goto(f"{BASE_URL}/driver/login")
    await page.fill('input[name="email"]', driver_credentials["email"])
    await page.fill('input[name="password"]', driver_credentials["password"])
    await page.click('button[type="submit"]')
    
    # Wait for redirect
    await page.wait_for_url(f"{BASE_URL}/driver/dashboard", timeout=5000)
    
    return page


# Helper functions
@pytest.fixture
def format_date():
    """Helper to format dates in Taiwan format"""
    def _format_date(date: datetime) -> str:
        return date.strftime("%Y/%m/%d")
    return _format_date


@pytest.fixture
def format_currency():
    """Helper to format currency in TWD"""
    def _format_currency(amount: float) -> str:
        return f"NT${amount:,.0f}"
    return _format_currency


# Screenshot helper
@pytest.fixture
async def take_screenshot(page: Page):
    """Helper to take screenshots during tests"""
    async def _take_screenshot(name: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = "tests/e2e/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        
        await page.screenshot(
            path=f"{screenshot_dir}/{timestamp}_{name}.png",
            full_page=True
        )
    return _take_screenshot


# API helper for test data setup
@pytest.fixture
async def api_client():
    """Create API client for test data setup"""
    import httpx
    
    async with httpx.AsyncClient(base_url=API_URL) as client:
        yield client


@pytest.fixture
async def create_test_customer(api_client, admin_credentials):
    """Helper to create test customers via API"""
    async def _create_customer(customer_data: Dict) -> Dict:
        # Login first
        login_response = await api_client.post(
            "/api/v1/auth/login",
            data={
                "username": admin_credentials["email"],
                "password": admin_credentials["password"]
            }
        )
        token = login_response.json()["access_token"]
        
        # Create customer
        response = await api_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
    
    return _create_customer


@pytest.fixture
async def create_test_order(api_client, admin_credentials):
    """Helper to create test orders via API"""
    async def _create_order(order_data: Dict) -> Dict:
        # Login first
        login_response = await api_client.post(
            "/api/v1/auth/login",
            data={
                "username": admin_credentials["email"],
                "password": admin_credentials["password"]
            }
        )
        token = login_response.json()["access_token"]
        
        # Create order
        response = await api_client.post(
            "/api/v1/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
    
    return _create_order


# Cleanup fixture
@pytest.fixture(autouse=True)
async def cleanup_screenshots():
    """Clean up old screenshots before tests"""
    screenshot_dir = "tests/e2e/screenshots"
    if os.path.exists(screenshot_dir):
        # Remove screenshots older than 7 days
        import time
        now = time.time()
        for filename in os.listdir(screenshot_dir):
            filepath = os.path.join(screenshot_dir, filename)
            if os.path.getmtime(filepath) < now - 7 * 86400:
                os.remove(filepath)


# Test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "mobile: mark test as mobile-specific test"
    )
    config.addinivalue_line(
        "markers", "desktop: mark test as desktop-specific test"
    )
    config.addinivalue_line(
        "markers", "critical: mark test as critical path test"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as smoke test"
    )