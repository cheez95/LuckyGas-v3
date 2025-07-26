#!/usr/bin/env python3
"""
Extract detailed page content from Lucky Gas system
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

class PageContentExtractor:
    def __init__(self):
        self.base_url = "https://www.renhongtech2.com.tw/luckygas_97420648"
        self.session = None
        self.page_contents = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            cookie_jar=aiohttp.CookieJar()
        )
        await self.login()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self):
        """Quick login"""
        login_url = f"{self.base_url}/index.aspx"
        
        async with self.session.get(login_url) as response:
            content = await response.read()
            html = content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            form_data = {inp.get('name'): inp.get('value', '') 
                        for inp in soup.find_all('input', type='hidden') 
                        if inp.get('name')}
            
            form_data.update({
                'txtTAXNO': '97420648',
                'txtCUST_ID': '7001',
                'txtPASSWORD': '0000',
                'Button1': '登入'
            })
            
            await self.session.post(login_url, data=form_data)
    
    async def extract_main_pages(self):
        """Extract content from key system pages"""
        print("\n📑 Extracting Page Content...")
        
        # Key pages to analyze based on menu structure
        key_pages = [
            ('會員作業', 'C000', 'Customer Management'),
            ('資料維護', 'W000', 'Data Maintenance'),
            ('訂單銷售', 'W100', 'Order Sales'),
            ('報表作業', 'W300', 'Reports'),
            ('派遣作業', 'Z200', 'Dispatch Operations'),
            ('發票作業', 'W700', 'Invoice Management'),
            ('帳務管理', 'W800', 'Account Management')
        ]
        
        for chinese_name, code, english_name in key_pages:
            print(f"\n🔍 Analyzing: {chinese_name} ({english_name})")
            
            # Navigate to the page
            nav_response = await self.navigate_to_page(code)
            if nav_response:
                # Get the main content
                await asyncio.sleep(1)  # Wait for frame to load
                
                async with self.session.get(f"{self.base_url}/main.aspx") as response:
                    content = await response.read()
                    html = content.decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Save the page
                    filename = f"page_{code}_{english_name.replace(' ', '_')}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    # Extract page structure
                    page_info = {
                        'chinese_name': chinese_name,
                        'english_name': english_name,
                        'code': code,
                        'ui_elements': self.analyze_page_ui(soup),
                        'data_fields': self.extract_data_fields(soup),
                        'actions': self.extract_page_actions(soup)
                    }
                    
                    self.page_contents[code] = page_info
                    
                    # Print summary
                    print(f"  ✓ Forms: {len(page_info['ui_elements']['forms'])}")
                    print(f"  ✓ Tables: {len(page_info['ui_elements']['tables'])}")
                    print(f"  ✓ Buttons: {len(page_info['ui_elements']['buttons'])}")
                    print(f"  ✓ Fields: {len(page_info['data_fields'])}")
    
    async def navigate_to_page(self, page_code):
        """Navigate to a specific page using TreeView postback"""
        try:
            # First, get the left menu to get viewstate
            async with self.session.get(f"{self.base_url}/Left.aspx") as response:
                content = await response.read()
                html = content.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract viewstate fields
                viewstate_data = {}
                for hidden in soup.find_all('input', type='hidden'):
                    name = hidden.get('name')
                    value = hidden.get('value', '')
                    if name:
                        viewstate_data[name] = value
                
                # Add navigation parameters
                viewstate_data['__EVENTTARGET'] = 'TreeView1'
                viewstate_data['__EVENTARGUMENT'] = f's系統管理\\{page_code}'
                
                # Post to navigate
                async with self.session.post(f"{self.base_url}/Left.aspx", data=viewstate_data) as nav_response:
                    return nav_response.status == 200
                    
        except Exception as e:
            print(f"  ⚠️  Navigation error: {e}")
            return False
    
    def analyze_page_ui(self, soup):
        """Analyze UI elements on the page"""
        ui_elements = {
            'forms': [],
            'tables': [],
            'buttons': [],
            'inputs': []
        }
        
        # Forms
        forms = soup.find_all('form')
        for form in forms:
            form_info = {
                'id': form.get('id', ''),
                'name': form.get('name', ''),
                'action': form.get('action', ''),
                'field_count': len(form.find_all(['input', 'select', 'textarea']))
            }
            ui_elements['forms'].append(form_info)
        
        # Tables (data grids)
        tables = soup.find_all('table')
        for table in tables:
            # Check if it's a data table
            headers = []
            ths = table.find_all('th')
            for th in ths:
                header_text = th.text.strip()
                if header_text:
                    headers.append(header_text)
            
            if headers:
                ui_elements['tables'].append({
                    'headers': headers,
                    'row_count': len(table.find_all('tr')) - 1,
                    'id': table.get('id', '')
                })
        
        # Buttons
        buttons = soup.find_all(['button', 'input'])
        for btn in buttons:
            if btn.name == 'input' and btn.get('type') not in ['button', 'submit']:
                continue
            
            btn_text = btn.text.strip() or btn.get('value', '')
            if btn_text:
                ui_elements['buttons'].append({
                    'text': btn_text,
                    'id': btn.get('id', ''),
                    'type': btn.get('type', 'button')
                })
        
        # Input fields
        inputs = soup.find_all(['input', 'select', 'textarea'])
        for inp in inputs:
            if inp.get('type') not in ['hidden', 'button', 'submit']:
                ui_elements['inputs'].append({
                    'name': inp.get('name', ''),
                    'id': inp.get('id', ''),
                    'type': inp.get('type', inp.name)
                })
        
        return ui_elements
    
    def extract_data_fields(self, soup):
        """Extract data field definitions"""
        fields = []
        
        # Look for form fields with labels
        labels = soup.find_all('label')
        for label in labels:
            label_text = label.text.strip()
            if label_text and label_text not in ['', ' ']:
                field_for = label.get('for', '')
                
                # Find associated input
                input_elem = None
                if field_for:
                    input_elem = soup.find(id=field_for)
                
                field_info = {
                    'label': label_text,
                    'field_id': field_for,
                    'type': 'text'
                }
                
                if input_elem:
                    field_info['type'] = input_elem.get('type', input_elem.name)
                    field_info['name'] = input_elem.get('name', '')
                
                fields.append(field_info)
        
        # Also look for table headers as potential fields
        tables = soup.find_all('table')
        for table in tables:
            ths = table.find_all('th')
            if len(ths) > 2:  # Likely a data table
                for th in ths:
                    header = th.text.strip()
                    if header and header not in ['選擇', '操作', '功能', '']:
                        fields.append({
                            'label': header,
                            'field_id': '',
                            'type': 'column',
                            'name': header
                        })
        
        # Remove duplicates
        seen = set()
        unique_fields = []
        for field in fields:
            key = field['label']
            if key not in seen:
                seen.add(key)
                unique_fields.append(field)
        
        return unique_fields
    
    def extract_page_actions(self, soup):
        """Extract available actions/operations"""
        actions = []
        
        # Look for buttons and links with onclick
        elements = soup.find_all(['button', 'input', 'a'])
        for elem in elements:
            onclick = elem.get('onclick', '')
            text = elem.text.strip() or elem.get('value', '')
            
            if onclick and text:
                actions.append({
                    'text': text,
                    'action': onclick[:100],  # First 100 chars
                    'type': elem.name
                })
        
        return actions
    
    async def generate_detailed_report(self):
        """Generate detailed page analysis report"""
        print("\n📝 Generating Detailed Report...")
        
        report = """# Lucky Gas System - Detailed Page Analysis

## Page-by-Page Breakdown

"""
        
        for code, page_info in self.page_contents.items():
            report += f"\n### {page_info['chinese_name']} ({page_info['english_name']})\n\n"
            report += f"**Page Code**: {code}\n\n"
            
            # UI Elements
            report += "**UI Components**:\n"
            report += f"- Forms: {len(page_info['ui_elements']['forms'])}\n"
            report += f"- Data Tables: {len(page_info['ui_elements']['tables'])}\n"
            report += f"- Action Buttons: {len(page_info['ui_elements']['buttons'])}\n"
            report += f"- Input Fields: {len(page_info['ui_elements']['inputs'])}\n\n"
            
            # Data Fields
            if page_info['data_fields']:
                report += "**Data Fields**:\n\n"
                report += "| Field Label | Type | Field ID |\n"
                report += "|-------------|------|----------|\n"
                for field in page_info['data_fields'][:20]:  # First 20 fields
                    report += f"| {field['label']} | {field['type']} | {field['field_id']} |\n"
                
                if len(page_info['data_fields']) > 20:
                    report += f"\n*... and {len(page_info['data_fields']) - 20} more fields*\n"
            
            # Tables
            if page_info['ui_elements']['tables']:
                report += "\n**Data Tables**:\n"
                for table in page_info['ui_elements']['tables']:
                    report += f"\n*Table Headers*: {', '.join(table['headers'][:10])}\n"
                    if len(table['headers']) > 10:
                        report += f"*... and {len(table['headers']) - 10} more columns*\n"
            
            report += "\n---\n"
        
        # Save report
        with open('DETAILED_PAGE_ANALYSIS.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Save JSON data
        with open('page_contents.json', 'w', encoding='utf-8') as f:
            json.dump(self.page_contents, f, ensure_ascii=False, indent=2)
        
        print("✅ Detailed analysis complete!")
        print("📄 Generated files:")
        print("  - DETAILED_PAGE_ANALYSIS.md")
        print("  - page_contents.json")

async def main():
    async with PageContentExtractor() as extractor:
        await extractor.extract_main_pages()
        await extractor.generate_detailed_report()

if __name__ == "__main__":
    print("🔍 Lucky Gas Page Content Extractor")
    print("=" * 50)
    asyncio.run(main())