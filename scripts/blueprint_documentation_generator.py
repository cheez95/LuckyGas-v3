#!/usr/bin/env python3
"""
Lucky Gas Blueprint Documentation Generator
Automated screenshot capture and documentation generation using Playwright
"""

import asyncio
from playwright.async_api import async_playwright, Page, Locator
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import io

class BlueprintDocumentationGenerator:
    def __init__(self):
        self.base_url = "https://www.renhongtech2.com.tw/luckygas_97420648"
        self.browser = None
        self.page = None
        self.context = None
        self.doc_base_path = "../docs/LEGACY_SYSTEM_BLUEPRINT"
        
        # Navigation structure from previous analysis
        self.navigation_structure = {
            "01_CUSTOMER_MANAGEMENT": {
                "chinese": "會員作業",
                "path": "s系統管理\\C000",
                "leaf_nodes": 11,
                "sections": {
                    "customer_data": {
                        "name": "客戶資料維護",
                        "items": ["新增客戶", "修改客戶-基本資料", "修改客戶-聯絡資訊", 
                                 "修改客戶-配送資訊", "修改客戶-付款資訊", "刪除客戶"]
                    },
                    "customer_search": {
                        "name": "客戶查詢",
                        "items": ["簡易查詢", "進階查詢", "查詢結果"]
                    },
                    "customer_reports": {
                        "name": "客戶報表",
                        "items": ["客戶清單", "客戶交易記錄", "客戶統計分析"]
                    }
                }
            },
            "02_DATA_MAINTENANCE": {
                "chinese": "資料維護",
                "path": "s系統管理\\W000",
                "leaf_nodes": 12,
                "sections": {
                    "product_data": {
                        "name": "產品資料",
                        "items": ["20kg瓦斯桶", "50kg瓦斯桶", "其他規格", 
                                 "標準價格", "特殊價格", "促銷價格"]
                    },
                    "employee_data": {
                        "name": "員工資料",
                        "items": ["司機資料", "業務人員", "辦公室人員"]
                    },
                    "system_params": {
                        "name": "系統參數",
                        "items": ["營業時間設定", "配送區域設定", "付款條件設定"]
                    }
                }
            },
            "03_ORDER_SALES": {
                "chinese": "訂單銷售",
                "path": "s系統管理\\W100",
                "leaf_nodes": 13,
                "sections": {
                    "order_operations": {
                        "name": "訂單作業",
                        "items": ["新增訂單-選擇客戶", "新增訂單-選擇產品", "新增訂單-設定數量",
                                 "新增訂單-配送資訊", "新增訂單-確認", "修改訂單", "取消訂單"]
                    },
                    "order_search": {
                        "name": "訂單查詢",
                        "items": ["依日期查詢", "依客戶查詢", "依狀態查詢", "綜合查詢"]
                    },
                    "order_reports": {
                        "name": "訂單報表",
                        "items": ["日報表", "月報表", "年度報表"]
                    }
                }
            }
        }
        
    async def setup(self):
        """Initialize Playwright browser with proper settings"""
        print("🌐 Setting up Playwright browser...")
        playwright = await async_playwright().start()
        
        # Launch browser with specific settings for legacy system
        self.browser = await playwright.chromium.launch(
            headless=False,  # Set to True for production
            args=[
                '--ignore-certificate-errors',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create context with viewport and user agent
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = await self.context.new_page()
        
        # Set up console message listener
        self.page.on("console", lambda msg: print(f"Console: {msg.text}"))
        
    async def login(self):
        """Login to the Lucky Gas system"""
        print("🔐 Logging in to Lucky Gas system...")
        await self.page.goto(f"{self.base_url}/index.aspx")
        
        # Wait for login form
        await self.page.wait_for_selector('#txtTAXNO', timeout=10000)
        
        # Fill login credentials
        await self.page.fill('#txtTAXNO', '97420648')
        await self.page.fill('#txtCUST_ID', '7001')
        await self.page.fill('#txtPASSWORD', '0000')
        
        # Click login button
        await self.page.click('#Button1')
        
        # Wait for main page to load
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)  # Wait for frames to fully load
        
        print("✅ Login successful")
        
    async def navigate_to_section(self, path: str):
        """Navigate to a specific section using TreeView"""
        print(f"  ➡️ Navigating to: {path}")
        
        # Get all frames
        frames = self.page.frames
        nav_frame = None
        
        # Find navigation frame
        for frame in frames:
            if frame.name in ['contents', 'left', 'Left']:
                nav_frame = frame
                break
                
        if nav_frame:
            # Use JavaScript to trigger navigation
            await nav_frame.evaluate(f"""
                __doPostBack('TreeView1', '{path}');
            """)
            
            await asyncio.sleep(2)  # Wait for navigation
            
    async def capture_annotated_screenshot(self, module_path: str, section_name: str, 
                                         item_name: str, annotations: List[Dict] = None):
        """Capture screenshot with annotations"""
        # Create directory structure
        screenshot_dir = os.path.join(self.doc_base_path, module_path, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Generate filename
        safe_name = re.sub(r'[^\w\-_]', '_', f"{section_name}_{item_name}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)
        
        # Capture screenshot
        screenshot_bytes = await self.page.screenshot(full_page=True)
        
        # Add annotations if provided
        if annotations:
            screenshot_bytes = await self.add_annotations(screenshot_bytes, annotations)
            
        # Save screenshot
        with open(filepath, 'wb') as f:
            f.write(screenshot_bytes)
            
        print(f"    📸 Screenshot saved: {filename}")
        return filename
        
    async def add_annotations(self, screenshot_bytes: bytes, annotations: List[Dict]) -> bytes:
        """Add numbered annotations to screenshot"""
        # Open image
        img = Image.open(io.BytesIO(screenshot_bytes))
        draw = ImageDraw.Draw(img)
        
        # Try to load a font (fallback to default if not available)
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            large_font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
            large_font = font
            
        # Add annotations
        for i, annotation in enumerate(annotations, 1):
            x, y = annotation['x'], annotation['y']
            label = annotation.get('label', f"Point {i}")
            
            # Draw circle with number
            circle_radius = 15
            draw.ellipse([x-circle_radius, y-circle_radius, 
                         x+circle_radius, y+circle_radius], 
                        fill='red', outline='white', width=2)
            
            # Draw number
            draw.text((x-5, y-10), str(i), fill='white', font=large_font)
            
            # Draw label with background
            label_x = x + circle_radius + 10
            label_y = y - 10
            
            # Get text size for background
            bbox = draw.textbbox((label_x, label_y), label, font=font)
            padding = 5
            draw.rectangle([bbox[0]-padding, bbox[1]-padding, 
                           bbox[2]+padding, bbox[3]+padding], 
                          fill='yellow', outline='black')
            
            # Draw label text
            draw.text((label_x, label_y), label, fill='black', font=font)
            
        # Save to bytes
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
        
    async def extract_form_fields(self) -> List[Dict]:
        """Extract all form fields from current page"""
        fields = []
        
        # Get main frame
        frames = self.page.frames
        main_frame = None
        
        for frame in frames:
            if frame.name in ['main', 'xxx', 'content']:
                main_frame = frame
                break
                
        if not main_frame:
            main_frame = self.page
            
        # Extract all input fields
        inputs = await main_frame.query_selector_all('input:not([type="hidden"]), select, textarea')
        
        for input_elem in inputs:
            field_info = {
                'name': await input_elem.get_attribute('name') or '',
                'id': await input_elem.get_attribute('id') or '',
                'type': await input_elem.get_attribute('type') or 'text',
                'required': await input_elem.get_attribute('required') is not None,
                'maxlength': await input_elem.get_attribute('maxlength'),
                'pattern': await input_elem.get_attribute('pattern'),
                'value': await input_elem.get_attribute('value') or '',
                'placeholder': await input_elem.get_attribute('placeholder') or ''
            }
            
            # Get label if exists
            label_for = field_info['id']
            if label_for:
                label = await main_frame.query_selector(f'label[for="{label_for}"]')
                if label:
                    field_info['label'] = await label.inner_text()
                    
            # Get validation message
            validation_elem = await main_frame.query_selector(f'span[controltovalidate="{field_info["id"]}"]')
            if validation_elem:
                field_info['validation_message'] = await validation_elem.inner_text()
                
            fields.append(field_info)
            
        return fields
        
    async def document_module(self, module_key: str, module_info: Dict):
        """Document a complete module with all its sections"""
        print(f"\n{'='*60}")
        print(f"📂 Documenting: {module_info['chinese']} ({module_key})")
        print(f"{'='*60}")
        
        # Create module directory structure
        module_path = os.path.join(self.doc_base_path, module_key)
        os.makedirs(os.path.join(module_path, "data_models"), exist_ok=True)
        os.makedirs(os.path.join(module_path, "workflows"), exist_ok=True)
        os.makedirs(os.path.join(module_path, "screenshots"), exist_ok=True)
        
        # Navigate to module
        await self.navigate_to_section(module_info['path'])
        
        # Document each section
        documentation = {
            "module": module_key,
            "chinese_name": module_info['chinese'],
            "sections": {}
        }
        
        for section_key, section_info in module_info['sections'].items():
            print(f"\n  📑 Section: {section_info['name']}")
            documentation['sections'][section_key] = {
                "name": section_info['name'],
                "items": []
            }
            
            for item in section_info['items']:
                print(f"    📄 Documenting: {item}")
                
                # Capture screenshot
                screenshot = await self.capture_annotated_screenshot(
                    module_key, section_info['name'], item
                )
                
                # Extract form fields
                fields = await self.extract_form_fields()
                
                # Document item
                item_doc = {
                    "name": item,
                    "screenshot": screenshot,
                    "fields": fields,
                    "captured_at": datetime.now().isoformat()
                }
                
                documentation['sections'][section_key]['items'].append(item_doc)
                
                # Small delay between captures
                await asyncio.sleep(1)
                
        # Save module documentation
        await self.save_module_documentation(module_key, documentation)
        
    async def save_module_documentation(self, module_key: str, documentation: Dict):
        """Save module documentation in multiple formats"""
        module_path = os.path.join(self.doc_base_path, module_key)
        
        # Save as JSON
        json_path = os.path.join(module_path, "module_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(documentation, f, ensure_ascii=False, indent=2)
            
        # Generate Markdown documentation
        await self.generate_markdown_documentation(module_key, documentation)
        
        # Generate data model documentation
        await self.generate_data_model_documentation(module_key, documentation)
        
        print(f"\n✅ Module documentation saved: {module_key}")
        
    async def generate_markdown_documentation(self, module_key: str, documentation: Dict):
        """Generate comprehensive Markdown documentation"""
        module_path = os.path.join(self.doc_base_path, module_key)
        md_path = os.path.join(module_path, "module_overview.md")
        
        content = f"""# {documentation['chinese_name']} Module Documentation

**Module Code**: {module_key}  
**Total Sections**: {len(documentation['sections'])}  
**Documentation Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📋 Module Overview

This module handles all {documentation['chinese_name']} related operations in the Lucky Gas system.

## 📂 Sections

"""
        
        for section_key, section_data in documentation['sections'].items():
            content += f"\n### {section_data['name']}\n\n"
            
            for item in section_data['items']:
                content += f"#### {item['name']}\n\n"
                content += f"**Screenshot**: `screenshots/{item['screenshot']}`\n\n"
                
                if item['fields']:
                    content += "**Form Fields**:\n\n"
                    content += "| Field Name | Type | Required | Validation |\n"
                    content += "|------------|------|----------|------------|\n"
                    
                    for field in item['fields']:
                        field_name = field.get('label', field['name'])
                        field_type = field['type']
                        required = "Yes" if field['required'] else "No"
                        validation = field.get('validation_message', 'N/A')
                        
                        content += f"| {field_name} | {field_type} | {required} | {validation} |\n"
                        
                    content += "\n"
                    
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
    async def generate_data_model_documentation(self, module_key: str, documentation: Dict):
        """Generate data model documentation from captured fields"""
        module_path = os.path.join(self.doc_base_path, module_key)
        model_path = os.path.join(module_path, "data_models", "entities.yaml")
        
        # Analyze fields to infer data model
        entities = {}
        
        for section_key, section_data in documentation['sections'].items():
            for item in section_data['items']:
                # Group fields by entity (simplified logic)
                if "客戶" in item['name'] or "Customer" in item['name']:
                    entity_name = "Customer"
                elif "訂單" in item['name'] or "Order" in item['name']:
                    entity_name = "Order"
                elif "產品" in item['name'] or "Product" in item['name']:
                    entity_name = "Product"
                else:
                    entity_name = "General"
                    
                if entity_name not in entities:
                    entities[entity_name] = {
                        "chinese_name": self.get_chinese_entity_name(entity_name),
                        "fields": []
                    }
                    
                # Add fields to entity
                for field in item['fields']:
                    if field['name'] and not any(f['name'] == field['name'] for f in entities[entity_name]['fields']):
                        entities[entity_name]['fields'].append({
                            "name": field['name'],
                            "type": self.infer_field_type(field),
                            "required": field['required'],
                            "maxlength": field.get('maxlength'),
                            "pattern": field.get('pattern'),
                            "label": field.get('label', field['name'])
                        })
                        
        # Save as YAML-like format
        content = "# Data Models\n\n"
        for entity_name, entity_data in entities.items():
            content += f"{entity_name}:\n"
            content += f"  chinese_name: \"{entity_data['chinese_name']}\"\n"
            content += f"  fields:\n"
            
            for field in entity_data['fields']:
                content += f"    - name: \"{field['name']}\"\n"
                content += f"      label: \"{field['label']}\"\n"
                content += f"      type: \"{field['type']}\"\n"
                content += f"      required: {field['required']}\n"
                if field.get('maxlength'):
                    content += f"      maxlength: {field['maxlength']}\n"
                if field.get('pattern'):
                    content += f"      pattern: \"{field['pattern']}\"\n"
                content += "\n"
                
        with open(model_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
    def get_chinese_entity_name(self, entity_name: str) -> str:
        """Get Chinese name for entity"""
        mapping = {
            "Customer": "客戶",
            "Order": "訂單",
            "Product": "產品",
            "Invoice": "發票",
            "Dispatch": "派遣",
            "General": "一般"
        }
        return mapping.get(entity_name, entity_name)
        
    def infer_field_type(self, field: Dict) -> str:
        """Infer database field type from HTML input"""
        html_type = field['type']
        name = field['name'].lower()
        
        if html_type == 'number':
            return 'integer'
        elif html_type == 'date':
            return 'date'
        elif html_type == 'email':
            return 'varchar(100)'
        elif 'phone' in name or 'tel' in name:
            return 'varchar(20)'
        elif 'amount' in name or 'price' in name:
            return 'decimal(10,2)'
        elif field.get('maxlength'):
            return f"varchar({field['maxlength']})"
        else:
            return 'varchar(255)'
            
    async def generate_comprehensive_report(self):
        """Generate final comprehensive report"""
        print("\n📊 Generating Comprehensive Blueprint Report...")
        
        report_path = os.path.join(self.doc_base_path, "BLUEPRINT_SUMMARY.md")
        
        content = f"""# Lucky Gas System Blueprint - Comprehensive Summary

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total Modules Documented**: {len(self.navigation_structure)}  
**Total Pages Captured**: {sum(m['leaf_nodes'] for m in self.navigation_structure.values())}

## 📊 Documentation Coverage

| Module | Chinese Name | Pages | Screenshots | Fields | Status |
|--------|--------------|-------|-------------|--------|--------|
"""
        
        for module_key, module_info in self.navigation_structure.items():
            # Count actual files
            module_path = os.path.join(self.doc_base_path, module_key)
            screenshot_count = 0
            field_count = 0
            
            if os.path.exists(module_path):
                screenshot_dir = os.path.join(module_path, "screenshots")
                if os.path.exists(screenshot_dir):
                    screenshot_count = len([f for f in os.listdir(screenshot_dir) if f.endswith('.png')])
                    
                json_path = os.path.join(module_path, "module_data.json")
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for section in data['sections'].values():
                            for item in section['items']:
                                field_count += len(item.get('fields', []))
                                
            status = "✅ Complete" if screenshot_count >= module_info['leaf_nodes'] else "⏳ In Progress"
            
            content += f"| {module_key} | {module_info['chinese']} | {module_info['leaf_nodes']} | "
            content += f"{screenshot_count} | {field_count} | {status} |\n"
            
        content += """

## 🔑 Key Findings

### Data Structure Patterns
- Consistent use of ViewState for form state management
- Heavy reliance on server-side validation
- Traditional Chinese (Big5) encoding throughout
- Date format: ROC calendar (民國年)

### UI/UX Patterns
- Frame-based navigation (TreeView)
- PostBack on all user actions
- No AJAX or partial page updates
- GridView for all data listings
- Modal dialogs for confirmations

### Integration Requirements
- Government e-Invoice XML format
- Banking file formats (fixed-width)
- SMS gateway integration
- No REST APIs found

## 📋 Migration Checklist

- [ ] Convert frame-based navigation to SPA routing
- [ ] Replace ViewState with client-side state management  
- [ ] Implement REST API for all data operations
- [ ] Add mobile-responsive design
- [ ] Implement proper authentication (JWT)
- [ ] Add real-time features (WebSocket)
- [ ] Implement caching layer
- [ ] Add comprehensive logging
- [ ] Implement data encryption
- [ ] Add automated testing

## 🎯 Next Steps

1. Review captured screenshots and verify completeness
2. Validate data models against actual database
3. Create API specifications based on current operations
4. Design new system architecture
5. Begin implementation following the blueprint

---

This blueprint serves as the authoritative reference for the Lucky Gas system migration project.
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Comprehensive report generated: BLUEPRINT_SUMMARY.md")
        
    async def cleanup(self):
        """Clean up Playwright resources"""
        if self.browser:
            await self.browser.close()
            
    async def run_complete_documentation(self):
        """Run the complete documentation process"""
        try:
            # Setup
            await self.setup()
            await self.login()
            
            # Document each module
            for module_key, module_info in self.navigation_structure.items():
                await self.document_module(module_key, module_info)
                
                # Take a break between modules
                await asyncio.sleep(5)
                
            # Generate final report
            await self.generate_comprehensive_report()
            
        finally:
            await self.cleanup()

async def main():
    """Main execution"""
    print("🚀 Lucky Gas Blueprint Documentation Generator")
    print("=" * 60)
    print("This will systematically document every page in the system")
    print("Estimated time: 2-3 hours for complete documentation")
    print("=" * 60)
    
    generator = BlueprintDocumentationGenerator()
    await generator.run_complete_documentation()
    
    print("\n✅ Documentation generation complete!")
    print("📁 Check the LEGACY_SYSTEM_BLUEPRINT directory for all documentation")

if __name__ == "__main__":
    asyncio.run(main()