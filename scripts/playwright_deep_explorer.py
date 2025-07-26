#!/usr/bin/env python3
"""
Deep System Explorer using Playwright for complete navigation
Handles dynamic content, AJAX, and JavaScript-rendered pages
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime
from typing import Dict, List, Set
import re

class PlaywrightDeepExplorer:
    def __init__(self):
        self.base_url = "https://www.renhongtech2.com.tw/luckygas_97420648"
        self.browser = None
        self.page = None
        self.visited_urls = set()
        self.navigation_map = {
            "main_sections": {},
            "sub_pages": {},
            "leaf_nodes": [],
            "interactive_elements": {}
        }
        self.screenshot_count = 0
        
    async def setup(self):
        """Setup Playwright browser"""
        print("🌐 Setting up browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # Set to True for production
            args=['--ignore-certificate-errors']
        )
        self.page = await self.browser.new_page()
        
        # Set viewport for consistent screenshots
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        
    async def cleanup(self):
        """Cleanup browser resources"""
        if self.browser:
            await self.browser.close()
    
    async def login(self):
        """Login to the system"""
        print("🔐 Logging in...")
        await self.page.goto(f"{self.base_url}/index.aspx")
        
        # Fill login form
        await self.page.fill('input#txtTAXNO', '97420648')
        await self.page.fill('input#txtCUST_ID', '7001')
        await self.page.fill('input#txtPASSWORD', '0000')
        
        # Click login button
        await self.page.click('input#Button1')
        
        # Wait for navigation
        await self.page.wait_for_load_state('networkidle')
        print("✅ Login successful")
        
        # Take screenshot of main page
        await self.take_screenshot("00_main_page")
    
    async def explore_complete_system(self):
        """Main exploration function"""
        print("\n🔍 Starting Deep System Exploration...")
        
        # Wait for frames to load
        await asyncio.sleep(3)
        
        # Get all frames
        frames = self.page.frames
        print(f"Found {len(frames)} frames")
        
        # Find the navigation frame (usually named 'contents' or 'left')
        nav_frame = None
        main_frame = None
        
        for frame in frames:
            frame_name = frame.name
            print(f"  Frame: {frame_name}")
            if frame_name in ['contents', 'left', 'Left']:
                nav_frame = frame
            elif frame_name in ['main', 'xxx', 'content']:
                main_frame = frame
        
        if nav_frame:
            print("\n📑 Analyzing navigation menu...")
            await self.analyze_navigation_frame(nav_frame)
        
        if main_frame:
            print("\n📄 Analyzing main content...")
            await self.analyze_main_frame(main_frame)
        
        # Explore each section systematically
        await self.explore_all_sections(nav_frame, main_frame)
    
    async def analyze_navigation_frame(self, nav_frame):
        """Analyze the navigation tree"""
        # Wait for TreeView to load
        await nav_frame.wait_for_selector('#TreeView1', timeout=5000)
        
        # Get all navigation links
        nav_links = await nav_frame.query_selector_all('#TreeView1 a')
        
        print(f"Found {len(nav_links)} navigation items")
        
        for i, link in enumerate(nav_links):
            text = await link.inner_text()
            href = await link.get_attribute('href')
            onclick = await link.get_attribute('onclick')
            
            if text.strip():
                self.navigation_map["main_sections"][i] = {
                    "text": text.strip(),
                    "href": href,
                    "onclick": onclick,
                    "index": i
                }
                print(f"  {i}: {text.strip()}")
    
    async def analyze_main_frame(self, main_frame):
        """Analyze the main content frame"""
        # Take screenshot
        await self.take_screenshot("main_frame_initial")
        
        # Find all interactive elements
        elements = {
            "forms": await main_frame.query_selector_all('form'),
            "inputs": await main_frame.query_selector_all('input:not([type="hidden"])'),
            "buttons": await main_frame.query_selector_all('button, input[type="button"], input[type="submit"]'),
            "links": await main_frame.query_selector_all('a[href]:not([href="#"])'),
            "selects": await main_frame.query_selector_all('select'),
            "tables": await main_frame.query_selector_all('table')
        }
        
        print(f"\nMain frame elements:")
        print(f"  Forms: {len(elements['forms'])}")
        print(f"  Input fields: {len(elements['inputs'])}")
        print(f"  Buttons: {len(elements['buttons'])}")
        print(f"  Links: {len(elements['links'])}")
        print(f"  Dropdowns: {len(elements['selects'])}")
        print(f"  Tables: {len(elements['tables'])}")
    
    async def explore_all_sections(self, nav_frame, main_frame):
        """Systematically explore each section"""
        if not nav_frame or not main_frame:
            print("⚠️ Cannot explore - frames not found")
            return
        
        # Get all navigation items
        nav_items = self.navigation_map["main_sections"]
        
        # Define the sections we want to explore in detail
        key_sections = [
            '會員作業', '資料維護', '訂單銷售', '報表作業',
            '派遣作業', '發票作業', '帳務管理', 'CSV匯出'
        ]
        
        for idx, nav_item in nav_items.items():
            if any(section in nav_item['text'] for section in key_sections):
                print(f"\n{'='*60}")
                print(f"📂 Exploring: {nav_item['text']}")
                print(f"{'='*60}")
                
                # Click the navigation item
                await self.click_nav_item(nav_frame, idx)
                
                # Wait for content to load
                await asyncio.sleep(2)
                
                # Explore the loaded content
                await self.explore_section_content(main_frame, nav_item['text'])
    
    async def click_nav_item(self, nav_frame, index):
        """Click a navigation item by index"""
        try:
            # Find the specific link by index
            links = await nav_frame.query_selector_all('#TreeView1 a')
            if index < len(links):
                await links[index].click()
                await asyncio.sleep(1)
        except Exception as e:
            print(f"  ⚠️ Error clicking nav item: {e}")
    
    async def explore_section_content(self, main_frame, section_name):
        """Explore all content within a section"""
        print(f"\n🔍 Analyzing {section_name} content...")
        
        # Take screenshot
        safe_name = re.sub(r'[^\w\-]', '_', section_name)
        await self.take_screenshot(f"section_{safe_name}")
        
        # Look for tabs
        tabs = await self.find_tabs(main_frame)
        if tabs:
            print(f"  📑 Found {len(tabs)} tabs")
            for tab in tabs:
                await self.explore_tab(main_frame, tab)
        
        # Look for data grids
        grids = await main_frame.query_selector_all('table[id*="GridView"], table[id*="DataGrid"]')
        if grids:
            print(f"  📊 Found {len(grids)} data grids")
            for i, grid in enumerate(grids):
                await self.analyze_grid(grid, f"{section_name}_grid_{i}")
        
        # Look for forms
        forms = await main_frame.query_selector_all('form')
        if forms:
            print(f"  📝 Found {len(forms)} forms")
            for i, form in enumerate(forms):
                await self.analyze_form(form, f"{section_name}_form_{i}")
        
        # Look for action buttons
        buttons = await main_frame.query_selector_all('input[type="button"], input[type="submit"], button')
        action_buttons = []
        for button in buttons:
            text = await self.get_button_text(button)
            if text and any(keyword in text for keyword in ['新增', '查詢', '編輯', '刪除', '匯出', '列印']):
                action_buttons.append((button, text))
        
        if action_buttons:
            print(f"  🔘 Found {len(action_buttons)} action buttons:")
            for button, text in action_buttons:
                print(f"    • {text}")
                # Try clicking to see what happens
                await self.test_button(main_frame, button, text)
        
        # Check if this is a leaf node
        if not tabs and not action_buttons and len(forms) <= 1:
            self.navigation_map["leaf_nodes"].append({
                "name": section_name,
                "type": "section",
                "has_data": len(grids) > 0
            })
            print(f"  🍃 LEAF NODE: {section_name}")
    
    async def find_tabs(self, frame):
        """Find tab controls in the frame"""
        tabs = []
        
        # Common tab selectors
        tab_selectors = [
            'ul.nav-tabs li a',
            'div[role="tablist"] button',
            'div.tabs a',
            'table.tabstrip td',
            'div.tabcontainer a'
        ]
        
        for selector in tab_selectors:
            found_tabs = await frame.query_selector_all(selector)
            if found_tabs:
                for tab in found_tabs:
                    text = await tab.inner_text()
                    if text.strip():
                        tabs.append({
                            'element': tab,
                            'text': text.strip()
                        })
        
        return tabs
    
    async def explore_tab(self, frame, tab):
        """Click and explore a tab"""
        print(f"    📑 Exploring tab: {tab['text']}")
        try:
            await tab['element'].click()
            await asyncio.sleep(1)
            
            # Take screenshot of tab content
            safe_name = re.sub(r'[^\w\-]', '_', tab['text'])
            await self.take_screenshot(f"tab_{safe_name}")
            
            # Check for sub-elements in this tab
            sub_buttons = await frame.query_selector_all('input[value*="新增"], input[value*="查詢"]')
            if sub_buttons:
                print(f"      Found {len(sub_buttons)} sub-actions in tab")
        
        except Exception as e:
            print(f"      ⚠️ Error exploring tab: {e}")
    
    async def analyze_grid(self, grid, name):
        """Analyze a data grid"""
        # Count rows
        rows = await grid.query_selector_all('tr')
        headers = await grid.query_selector_all('th')
        
        print(f"    📊 Grid analysis:")
        print(f"      Headers: {len(headers)}")
        print(f"      Data rows: {len(rows) - 1}")
        
        # Check for pagination
        pager = await grid.query_selector('tr.pager, div.pagination')
        if pager:
            print(f"      Has pagination")
    
    async def analyze_form(self, form, name):
        """Analyze a form"""
        inputs = await form.query_selector_all('input:not([type="hidden"]), select, textarea')
        print(f"    📝 Form has {len(inputs)} input fields")
    
    async def get_button_text(self, button):
        """Get text from a button element"""
        # Try value attribute first
        value = await button.get_attribute('value')
        if value:
            return value.strip()
        
        # Then try inner text
        text = await button.inner_text()
        return text.strip() if text else ""
    
    async def test_button(self, frame, button, text):
        """Test clicking a button to see what it does"""
        if '新增' in text or 'Add' in text:
            print(f"      🆕 Testing 'Add' functionality: {text}")
            # Don't actually click to avoid creating test data
            # Just note that this functionality exists
            self.navigation_map["interactive_elements"][text] = "add_function"
        elif '查詢' in text or 'Search' in text:
            print(f"      🔍 Testing 'Search' functionality: {text}")
            # Could click and see search options
        elif '匯出' in text or 'Export' in text:
            print(f"      💾 Found 'Export' functionality: {text}")
            self.navigation_map["interactive_elements"][text] = "export_function"
    
    async def take_screenshot(self, name):
        """Take a screenshot with a descriptive name"""
        self.screenshot_count += 1
        filename = f"screenshots/{self.screenshot_count:03d}_{name}.png"
        
        # Create directory if needed
        os.makedirs("screenshots", exist_ok=True)
        
        await self.page.screenshot(path=filename)
        print(f"  📸 Screenshot: {filename}")
    
    async def generate_complete_report(self):
        """Generate the final exploration report"""
        print("\n📊 Generating Complete Navigation Report...")
        
        report = f"""# Lucky Gas System - Complete Navigation Analysis

**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Screenshots Taken**: {self.screenshot_count}
**Using**: Playwright Browser Automation

## Navigation Structure

### Main Sections Found
"""
        
        for idx, section in self.navigation_map["main_sections"].items():
            report += f"- **{section['text']}**\n"
        
        report += f"\n### Leaf Nodes (End Points)\n"
        report += f"Found {len(self.navigation_map['leaf_nodes'])} endpoints with no further navigation:\n\n"
        
        for leaf in self.navigation_map["leaf_nodes"]:
            report += f"- {leaf['name']} (Type: {leaf['type']})\n"
        
        report += f"\n### Interactive Elements\n"
        for element, type in self.navigation_map["interactive_elements"].items():
            report += f"- {element}: {type}\n"
        
        # Save report
        with open('PLAYWRIGHT_EXPLORATION_REPORT.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Save structured data
        with open('playwright_navigation_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.navigation_map, f, ensure_ascii=False, indent=2)
        
        print("\n✅ Exploration complete!")
        print("📁 Generated files:")
        print("  - PLAYWRIGHT_EXPLORATION_REPORT.md")
        print("  - playwright_navigation_data.json")
        print(f"  - {self.screenshot_count} screenshots in screenshots/ folder")

async def main():
    explorer = PlaywrightDeepExplorer()
    
    try:
        await explorer.setup()
        await explorer.login()
        await explorer.explore_complete_system()
        await explorer.generate_complete_report()
    finally:
        await explorer.cleanup()

if __name__ == "__main__":
    print("🚀 Lucky Gas Deep System Explorer (Playwright)")
    print("=" * 60)
    asyncio.run(main())