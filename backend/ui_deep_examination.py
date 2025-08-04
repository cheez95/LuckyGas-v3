#!/usr/bin/env python3
"""
Deep UI Examination Script
Examines all UI components and functionality
"""
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

async def examine_ui():
    """Examine UI functionality with Playwright"""
    print("🖥️ Lucky Gas UI Deep Examination")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    findings = {
        "pages": {},
        "components": [],
        "interactions": [],
        "accessibility": [],
        "responsive": [],
        "errors": []
    }
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Monitor console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        # Monitor network errors
        network_errors = []
        page.on("requestfailed", lambda request: network_errors.append({
            "url": request.url,
            "failure": request.failure
        }))
        
        # 1. Login Page Examination
        print("\n📄 Examining Login Page...")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_load_state("networkidle")
        
        # Check page title
        title = await page.title()
        print(f"  Title: {title}")
        findings["pages"]["login"] = {"title": title}
        
        # Find all interactive elements
        print("\n🔍 Finding Interactive Elements...")
        
        # Username input
        username_input = await page.query_selector('[data-testid="username-input"]')
        if username_input:
            print("  ✅ Username input found")
            findings["components"].append("username-input")
        else:
            # Try alternative selectors
            username_input = await page.query_selector('input[type="text"]')
            if username_input:
                print("  ⚠️ Username input found (no data-testid)")
                findings["components"].append("username-input-generic")
        
        # Password input
        password_input = await page.query_selector('[data-testid="password-input"]')
        if password_input:
            print("  ✅ Password input found")
            findings["components"].append("password-input")
        else:
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                print("  ⚠️ Password input found (no data-testid)")
                findings["components"].append("password-input-generic")
        
        # Login button
        login_button = await page.query_selector('[data-testid="login-button"]')
        if login_button:
            print("  ✅ Login button found")
            findings["components"].append("login-button")
        else:
            login_button = await page.query_selector('button:has-text("登")')
            if login_button:
                print("  ⚠️ Login button found by text")
                findings["components"].append("login-button-text")
        
        # Check for other UI elements
        print("\n🎨 Checking UI Components...")
        
        # Logo/Branding
        logo = await page.query_selector('h2:has-text("幸福氣")')
        if logo:
            print("  ✅ Company branding found")
            findings["components"].append("branding")
        
        # Language check
        chinese_text = await page.query_selector('text=/.*[\u4e00-\u9fa5]+.*/')
        if chinese_text:
            print("  ✅ Traditional Chinese interface confirmed")
            findings["components"].append("chinese-interface")
        
        # Check form validation
        print("\n📝 Testing Form Validation...")
        if login_button:
            await login_button.click()
            await page.wait_for_timeout(1000)
            
            # Check for validation messages
            validation_msg = await page.query_selector('.ant-form-item-explain')
            if validation_msg:
                print("  ✅ Form validation messages present")
                findings["interactions"].append("form-validation")
        
        # Test login flow
        print("\n🔐 Testing Login Flow...")
        if username_input and password_input and login_button:
            await username_input.fill("test@example.com")
            await password_input.fill("test123")
            await login_button.click()
            
            # Wait for navigation or error
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            if "login" not in current_url:
                print("  ✅ Login successful - redirected")
                findings["interactions"].append("login-success")
                
                # Check dashboard
                print("\n📊 Examining Dashboard...")
                findings["pages"]["dashboard"] = {"url": current_url}
                
                # Look for dashboard elements
                sidebar = await page.query_selector('.ant-layout-sider')
                if sidebar:
                    print("  ✅ Sidebar navigation found")
                    findings["components"].append("sidebar")
                
                header = await page.query_selector('.ant-layout-header')
                if header:
                    print("  ✅ Header found")
                    findings["components"].append("header")
                
                # Check for menu items
                menu_items = await page.query_selector_all('.ant-menu-item')
                if menu_items:
                    print(f"  ✅ {len(menu_items)} menu items found")
                    findings["components"].append(f"menu-items-{len(menu_items)}")
            else:
                # Check for error message
                error_msg = await page.query_selector('.ant-alert-error')
                if error_msg:
                    print("  ❌ Login failed - error message shown")
                    findings["errors"].append("login-error")
        
        # Check responsive design
        print("\n📱 Testing Responsive Design...")
        viewports = [
            {"name": "Mobile", "width": 375, "height": 667},
            {"name": "Tablet", "width": 768, "height": 1024},
            {"name": "Desktop", "width": 1920, "height": 1080}
        ]
        
        for viewport in viewports:
            await page.set_viewport_size(
                width=viewport["width"],
                height=viewport["height"]
            )
            await page.wait_for_timeout(500)
            
            # Check if elements are visible
            is_responsive = await page.is_visible('body')
            if is_responsive:
                print(f"  ✅ {viewport['name']} view working")
                findings["responsive"].append(viewport["name"])
        
        # Check accessibility
        print("\n♿ Checking Accessibility...")
        
        # Check for ARIA labels
        aria_elements = await page.query_selector_all('[aria-label]')
        if aria_elements:
            print(f"  ✅ {len(aria_elements)} ARIA labels found")
            findings["accessibility"].append(f"aria-labels-{len(aria_elements)}")
        
        # Check for alt text on images
        images = await page.query_selector_all('img')
        images_with_alt = await page.query_selector_all('img[alt]')
        if images:
            print(f"  ℹ️ {len(images_with_alt)}/{len(images)} images have alt text")
            findings["accessibility"].append(f"alt-text-{len(images_with_alt)}/{len(images)}")
        
        # Analyze console messages
        print("\n📋 Console Analysis...")
        errors = [m for m in console_messages if m["type"] == "error"]
        warnings = [m for m in console_messages if m["type"] == "warning"]
        
        print(f"  Errors: {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        
        if errors:
            for error in errors[:3]:  # Show first 3 errors
                print(f"    ❌ {error['text'][:80]}...")
        
        # Check PWA features
        print("\n📱 Checking PWA Features...")
        
        # Service Worker
        sw_registered = await page.evaluate("""
            () => 'serviceWorker' in navigator && navigator.serviceWorker.controller !== null
        """)
        if sw_registered:
            print("  ✅ Service Worker active")
            findings["components"].append("service-worker")
        
        # Check manifest
        manifest = await page.evaluate("""
            () => {
                const link = document.querySelector('link[rel="manifest"]');
                return link ? link.href : null;
            }
        """)
        if manifest:
            print("  ✅ Web App Manifest present")
            findings["components"].append("manifest")
        
        await browser.close()
        
        # Generate report
        print("\n" + "=" * 60)
        print("📊 UI EXAMINATION SUMMARY")
        print("=" * 60)
        print(f"Pages Found: {len(findings['pages'])}")
        print(f"Components: {len(findings['components'])}")
        print(f"Interactions: {len(findings['interactions'])}")
        print(f"Responsive Views: {len(findings['responsive'])}")
        print(f"Accessibility Features: {len(findings['accessibility'])}")
        print(f"Errors: {len(findings['errors'])}")
        
        # Save detailed findings
        with open("ui_examination_report.json", "w") as f:
            json.dump(findings, f, indent=2)
        
        print("\n✅ Detailed report saved to ui_examination_report.json")

if __name__ == "__main__":
    asyncio.run(examine_ui())