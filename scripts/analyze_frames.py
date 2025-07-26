#!/usr/bin/env python3
"""
Analyze the frame-based structure of Lucky Gas system
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from datetime import datetime

class FrameAnalyzer:
    def __init__(self):
        self.base_url = "https://www.renhongtech2.com.tw/luckygas_97420648"
        self.session = None
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'frames': {},
            'menu_items': [],
            'features': []
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            cookie_jar=aiohttp.CookieJar()
        )
        # Login first
        await self.login()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self):
        """Quick login to establish session"""
        login_url = f"{self.base_url}/index.aspx"
        
        # Get login page
        async with self.session.get(login_url) as response:
            content = await response.read()
            html = content.decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract hidden fields
            form_data = {}
            for hidden in soup.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value', '')
                if name:
                    form_data[name] = value
            
            # Add credentials
            form_data['txtTAXNO'] = '97420648'
            form_data['txtCUST_ID'] = '7001'
            form_data['txtPASSWORD'] = '0000'
            form_data['Button1'] = '登入'
            
            # Login
            await self.session.post(login_url, data=form_data)
    
    async def analyze_left_menu(self):
        """Analyze the left navigation menu (Left.aspx)"""
        print("\n=== Analyzing Left Menu ===")
        url = f"{self.base_url}/Left.aspx"
        
        try:
            async with self.session.get(url) as response:
                content = await response.read()
                # Try different encodings
                for encoding in ['utf-8', 'big5', 'cp950']:
                    try:
                        html = content.decode(encoding)
                        break
                    except:
                        continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find all links in the menu
                menu_items = []
                links = soup.find_all('a')
                
                for link in links:
                    href = link.get('href', '')
                    text = link.text.strip()
                    onclick = link.get('onclick', '')
                    
                    if text and (href or onclick):
                        item = {
                            'text': text,
                            'href': href,
                            'onclick': onclick,
                            'target': link.get('target', '')
                        }
                        menu_items.append(item)
                        print(f"  - {text}")
                        if href and href != '#':
                            print(f"    URL: {href}")
                        if onclick:
                            print(f"    Action: {onclick[:50]}...")
                
                self.analysis_results['menu_items'] = menu_items
                
                # Save the menu HTML
                with open('left_menu.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                
        except Exception as e:
            print(f"Error analyzing left menu: {e}")
    
    async def analyze_main_content(self):
        """Analyze the main content frame (main.aspx)"""
        print("\n=== Analyzing Main Content ===")
        url = f"{self.base_url}/main.aspx"
        
        try:
            async with self.session.get(url) as response:
                content = await response.read()
                html = content.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for key elements
                print("\nMain page elements:")
                
                # Forms
                forms = soup.find_all('form')
                if forms:
                    print(f"  Forms found: {len(forms)}")
                
                # Tables (often used for data display)
                tables = soup.find_all('table')
                if tables:
                    print(f"  Tables found: {len(tables)}")
                    for i, table in enumerate(tables[:3]):
                        rows = len(table.find_all('tr'))
                        print(f"    Table {i+1}: {rows} rows")
                
                # Input elements
                inputs = soup.find_all(['input', 'select', 'textarea'])
                if inputs:
                    print(f"  Input elements: {len(inputs)}")
                
                # Save the main content
                with open('main_content.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                    
        except Exception as e:
            print(f"Error analyzing main content: {e}")
    
    async def explore_common_pages(self):
        """Try to access common pages based on typical patterns"""
        print("\n=== Exploring Common Pages ===")
        
        # Common page patterns in Traditional Chinese systems
        common_pages = {
            'Customer Management': ['Customer', 'Cust', 'Client', '客戶', 'khxx'],
            'Order Management': ['Order', 'Sales', '訂單', 'ddgl'],
            'Delivery': ['Delivery', 'Ship', '配送', 'psgl'],
            'Inventory': ['Inventory', 'Stock', '庫存', 'kcgl'],
            'Reports': ['Report', 'Query', '報表', 'bbcx'],
            'Gas Cylinder': ['Cylinder', 'Gas', '瓦斯', 'gpgl']
        }
        
        found_features = []
        
        for feature, patterns in common_pages.items():
            print(f"\nSearching for {feature}:")
            for pattern in patterns:
                # Try different extensions and paths
                urls_to_try = [
                    f"{self.base_url}/{pattern}.aspx",
                    f"{self.base_url}/{pattern}/List.aspx",
                    f"{self.base_url}/{pattern}/Index.aspx",
                    f"{self.base_url}/Pages/{pattern}.aspx"
                ]
                
                for url in urls_to_try:
                    try:
                        async with self.session.get(url, allow_redirects=False) as response:
                            if response.status == 200:
                                print(f"  ✓ Found: {url}")
                                found_features.append({
                                    'feature': feature,
                                    'url': url,
                                    'pattern': pattern
                                })
                                break
                    except:
                        pass
        
        self.analysis_results['features'] = found_features
    
    async def generate_analysis_report(self):
        """Generate comprehensive analysis report"""
        print("\n=== Generating Analysis Report ===")
        
        # Save the complete analysis
        with open('luckygas_current_system_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
        
        # Create a markdown report
        report = f"""# Lucky Gas Current Management System Analysis

**Analysis Date**: {self.analysis_results['timestamp']}
**System URL**: {self.base_url}

## System Architecture

The system uses a classic ASP.NET WebForms architecture with a frameset layout:

1. **Top Frame (banner)**: Portal/Phone.aspx - Contains header/phone information
2. **Left Frame (contents)**: Left.aspx - Navigation menu
3. **Main Frame (xxx)**: main.aspx - Main content area

## Navigation Menu Items

Found {len(self.analysis_results['menu_items'])} menu items:

"""
        for item in self.analysis_results['menu_items']:
            report += f"- **{item['text']}**"
            if item['href'] and item['href'] != '#':
                report += f" - Links to: {item['href']}"
            report += "\n"
        
        report += f"""
## Discovered Features

{len(self.analysis_results['features'])} features found:

"""
        for feature in self.analysis_results['features']:
            report += f"- **{feature['feature']}**: {feature['url']}\n"
        
        report += """
## Technical Details

- **Platform**: ASP.NET WebForms (classic .aspx pages)
- **Encoding**: Traditional Chinese (Big5/UTF-8)
- **Authentication**: Form-based with Tax ID + Customer ID + Password
- **Session Management**: ASP.NET Session State
- **UI Framework**: Frame-based layout (outdated)

## Key Observations

1. **Legacy Technology**: The system uses frames, which is a very outdated web technology
2. **Traditional Chinese**: All interfaces are in Traditional Chinese
3. **Tax ID Based**: Uses Taiwan tax ID (統一編號) as primary identifier
4. **Limited Mobile Support**: Frame-based design is not mobile-friendly

## Files Generated

- `current_system_login.html` - Login page structure
- `main_page.html` - Main frameset page
- `left_menu.html` - Navigation menu
- `main_content.html` - Main content area
- `luckygas_current_system_analysis.json` - Complete analysis data
"""
        
        with open('CURRENT_SYSTEM_ANALYSIS.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("\nAnalysis report saved to: CURRENT_SYSTEM_ANALYSIS.md")

async def main():
    """Run the frame-based analysis"""
    async with FrameAnalyzer() as analyzer:
        await analyzer.analyze_left_menu()
        await analyzer.analyze_main_content()
        await analyzer.explore_common_pages()
        await analyzer.generate_analysis_report()

if __name__ == "__main__":
    print("Lucky Gas Frame-Based System Analyzer")
    print("=" * 50)
    asyncio.run(main())