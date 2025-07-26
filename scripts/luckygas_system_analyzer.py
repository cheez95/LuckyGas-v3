#!/usr/bin/env python3
"""
Comprehensive analyzer for Lucky Gas current management system
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

class LuckyGasSystemAnalyzer:
    def __init__(self):
        self.base_url = "https://www.renhongtech2.com.tw/luckygas_97420648"
        self.login_url = f"{self.base_url}/index.aspx"
        self.session = None
        self.logged_in = False
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            cookie_jar=aiohttp.CookieJar()
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self, tax_no='97420648', cust_id='7001', password='0000'):
        """Login to the Lucky Gas system"""
        print("=== Attempting Login ===")
        
        try:
            # First, get the login page to extract ASP.NET fields
            async with self.session.get(self.login_url) as response:
                # Try different encodings
                content = await response.read()
                for encoding in ['big5', 'cp950', 'utf-8', 'gbk']:
                    try:
                        html = content.decode(encoding)
                        print(f"Successfully decoded with {encoding}")
                        break
                    except:
                        continue
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract hidden fields
                form_data = {}
                for hidden in soup.find_all('input', type='hidden'):
                    name = hidden.get('name')
                    value = hidden.get('value', '')
                    if name:
                        form_data[name] = value
                
                # Add login credentials
                form_data['txtTAXNO'] = tax_no
                form_data['txtCUST_ID'] = cust_id
                form_data['txtPASSWORD'] = password
                form_data['Button1'] = '登入'  # Submit button
                
                print(f"Logging in with TAX NO: {tax_no}, CUST ID: {cust_id}")
                
                # Submit login form
                async with self.session.post(self.login_url, data=form_data) as login_response:
                    # Handle encoding
                    content = await login_response.read()
                    login_html = None
                    for encoding in ['big5', 'cp950', 'utf-8', 'gbk']:
                        try:
                            login_html = content.decode(encoding)
                            break
                        except:
                            continue
                    
                    if not login_html:
                        print("Could not decode response")
                        return False
                    
                    # Check if login was successful
                    if 'index.aspx' in str(login_response.url) or '登入' in login_html:
                        print("Login might have failed - still on login page")
                        # Save response for debugging
                        with open('login_response.html', 'w', encoding='utf-8') as f:
                            f.write(login_html)
                        return False
                    else:
                        print(f"Login successful! Redirected to: {login_response.url}")
                        self.logged_in = True
                        
                        # Save the main page
                        with open('main_page.html', 'w', encoding='utf-8') as f:
                            f.write(login_html)
                        
                        await self.analyze_main_page(login_html)
                        return True
                        
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def analyze_main_page(self, html):
        """Analyze the main page after login"""
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n=== Main Page Analysis ===")
        
        # Look for navigation menu items
        print("\nNavigation/Menu Items:")
        links = soup.find_all('a')
        menu_items = []
        for link in links:
            href = link.get('href', '')
            text = link.text.strip()
            if text and href and not href.startswith('#'):
                menu_items.append({'text': text, 'href': href})
                print(f"  - {text}: {href}")
        
        # Look for frames or iframes
        frames = soup.find_all(['frame', 'iframe'])
        if frames:
            print(f"\nFrames found: {len(frames)}")
            for frame in frames:
                src = frame.get('src', '')
                name = frame.get('name', 'unnamed')
                print(f"  - Frame '{name}': {src}")
        
        # Look for main content areas
        print("\nMain Content Areas:")
        for tag in ['div', 'table', 'section']:
            elements = soup.find_all(tag, class_=True)
            for elem in elements[:5]:  # Limit to first 5
                classes = ' '.join(elem.get('class', []))
                if classes:
                    print(f"  - {tag}.{classes}")
        
        # Save menu structure
        self.save_analysis('menu_structure.json', menu_items)
        
        # Try to access key pages
        await self.explore_system_features()
    
    async def explore_system_features(self):
        """Explore different features of the system"""
        print("\n=== Exploring System Features ===")
        
        # Common page patterns to try
        common_pages = [
            'customer.aspx',
            'order.aspx',
            'delivery.aspx',
            'report.aspx',
            'inventory.aspx',
            'main.aspx',
            'home.aspx',
            'menu.aspx'
        ]
        
        found_pages = []
        
        for page in common_pages:
            url = f"{self.base_url}/{page}"
            try:
                async with self.session.get(url, allow_redirects=False) as response:
                    if response.status == 200:
                        print(f"  ✓ Found: {page}")
                        found_pages.append(page)
                        
                        # Save a sample of each page
                        html = await response.text()
                        filename = f"page_{page.replace('.aspx', '')}.html"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(html[:10000])  # Save first 10KB
                    elif response.status == 302:
                        print(f"  → Redirect: {page} -> {response.headers.get('Location', 'unknown')}")
                    else:
                        print(f"  ✗ Not found: {page} (Status: {response.status})")
            except Exception as e:
                print(f"  ! Error accessing {page}: {e}")
        
        self.save_analysis('found_pages.json', found_pages)
        
        # Try to find API endpoints or AJAX calls
        await self.analyze_ajax_endpoints()
    
    async def analyze_ajax_endpoints(self):
        """Look for AJAX/API endpoints"""
        print("\n=== Searching for API Endpoints ===")
        
        # Read main page to look for AJAX calls
        if os.path.exists('main_page.html'):
            with open('main_page.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for common AJAX patterns
            import re
            
            # ASP.NET WebMethods
            webmethods = re.findall(r'([\w]+\.aspx/[\w]+)', content)
            if webmethods:
                print("\nWebMethods found:")
                for method in set(webmethods):
                    print(f"  - {method}")
            
            # JavaScript AJAX calls
            ajax_urls = re.findall(r'url:\s*["\']([^"\']+)["\']', content)
            if ajax_urls:
                print("\nAJAX URLs found:")
                for url in set(ajax_urls):
                    print(f"  - {url}")
    
    def save_analysis(self, filename, data):
        """Save analysis data to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nSaved: {filename}")
    
    async def generate_report(self):
        """Generate a comprehensive analysis report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_url': self.base_url,
            'login_successful': self.logged_in,
            'analysis_complete': True
        }
        
        # Read saved data
        if os.path.exists('menu_structure.json'):
            with open('menu_structure.json', 'r') as f:
                report['menu_items'] = json.load(f)
        
        if os.path.exists('found_pages.json'):
            with open('found_pages.json', 'r') as f:
                report['accessible_pages'] = json.load(f)
        
        self.save_analysis('luckygas_system_analysis.json', report)
        
        print("\n=== Analysis Complete ===")
        print("Files generated:")
        print("  - current_system_login.html (Login page)")
        print("  - main_page.html (Main page after login)")
        print("  - menu_structure.json (Navigation menu)")
        print("  - found_pages.json (Accessible pages)")
        print("  - luckygas_system_analysis.json (Complete report)")

async def main():
    """Main analysis function"""
    async with LuckyGasSystemAnalyzer() as analyzer:
        # Try to login
        login_success = await analyzer.login()
        
        if login_success:
            # Generate final report
            await analyzer.generate_report()
        else:
            print("\nLogin failed. Please check credentials or try manual access.")
            print("The login response has been saved to 'login_response.html' for debugging.")

if __name__ == "__main__":
    print("Lucky Gas Management System Analyzer")
    print("=" * 50)
    asyncio.run(main())