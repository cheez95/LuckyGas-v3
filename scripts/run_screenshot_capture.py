#!/usr/bin/env python3
"""
Simplified screenshot capture script for Lucky Gas Customer Management module
"""

import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime

class ScreenshotCapture:
    def __init__(self):
        self.base_url = "https://www.renhongtech2.com.tw/luckygas_97420648"
        self.browser = None
        self.page = None
        self.screenshot_dir = "../docs/LEGACY_SYSTEM_BLUEPRINT/01_CUSTOMER_MANAGEMENT/screenshots"
        
    async def setup(self):
        """Setup browser"""
        print("🌐 Setting up browser...")
        playwright = await async_playwright().start()
        
        # Launch in headless mode for automation
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--ignore-certificate-errors']
        )
        
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        
    async def login(self):
        """Login to system"""
        print("🔐 Logging in...")
        try:
            await self.page.goto(f"{self.base_url}/index.aspx", timeout=30000)
            await self.page.wait_for_selector('#txtTAXNO', timeout=10000)
            
            await self.page.fill('#txtTAXNO', '97420648')
            await self.page.fill('#txtCUST_ID', '7001')
            await self.page.fill('#txtPASSWORD', '0000')
            
            await self.page.click('#Button1')
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            print("✅ Login successful")
            return True
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
            
    async def capture_main_page(self):
        """Capture main navigation page"""
        print("📸 Capturing main page...")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"00_main_navigation_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        await self.page.screenshot(path=filepath, full_page=True)
        print(f"✅ Saved: {filename}")
        
    async def capture_customer_module_overview(self):
        """Try to capture customer module screens"""
        print("📸 Attempting to capture Customer Management screens...")
        
        # Try to get frames
        frames = self.page.frames
        print(f"Found {len(frames)} frames")
        
        # Capture current state
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Main page
        filename = f"01_customer_module_main_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        await self.page.screenshot(path=filepath, full_page=True)
        print(f"✅ Saved: {filename}")
        
        # Try to navigate to customer module
        try:
            # Look for navigation frame
            nav_frame = None
            for frame in frames:
                if frame.name in ['contents', 'left', 'Left']:
                    nav_frame = frame
                    break
                    
            if nav_frame:
                print("📍 Found navigation frame")
                # Try to click customer management
                try:
                    await nav_frame.evaluate("""
                        __doPostBack('TreeView1', 's系統管理\\\\C000');
                    """)
                    await asyncio.sleep(3)
                    
                    # Capture after navigation
                    filename = f"02_customer_management_page_{timestamp}.png"
                    filepath = os.path.join(self.screenshot_dir, filename)
                    await self.page.screenshot(path=filepath, full_page=True)
                    print(f"✅ Saved: {filename}")
                except Exception as e:
                    print(f"⚠️ Navigation error: {e}")
                    
        except Exception as e:
            print(f"⚠️ Frame navigation error: {e}")
            
    async def cleanup(self):
        """Cleanup browser"""
        if self.browser:
            await self.browser.close()
            
    async def run(self):
        """Run the screenshot capture"""
        try:
            await self.setup()
            
            # Login
            if await self.login():
                # Capture screenshots
                await self.capture_main_page()
                await self.capture_customer_module_overview()
                
                print("\n✅ Screenshot capture completed!")
                print(f"📁 Screenshots saved to: {self.screenshot_dir}")
            else:
                print("❌ Cannot proceed without successful login")
                
        finally:
            await self.cleanup()

async def main():
    print("🚀 Lucky Gas Screenshot Capture Tool")
    print("=" * 50)
    
    capture = ScreenshotCapture()
    await capture.run()

if __name__ == "__main__":
    asyncio.run(main())