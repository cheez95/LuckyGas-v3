#!/usr/bin/env python3
"""
Script to analyze the current Lucky Gas management system
Portal: https://www.renhongtech2.com.tw/luckygas_97420648/index.aspx
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from datetime import datetime

async def analyze_login_page():
    """Analyze the login page structure"""
    url = "https://www.renhongtech2.com.tw/luckygas_97420648/index.aspx"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, ssl=False) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                print("=== Lucky Gas Current System Analysis ===")
                print(f"URL: {url}")
                print(f"Status Code: {response.status}")
                print(f"Timestamp: {datetime.now()}")
                print()
                
                # Find form elements
                forms = soup.find_all('form')
                print(f"Number of forms found: {len(forms)}")
                
                # Look for input fields
                inputs = soup.find_all('input')
                print(f"\nInput fields found: {len(inputs)}")
                for inp in inputs:
                    field_type = inp.get('type', 'text')
                    field_name = inp.get('name', 'unnamed')
                    field_id = inp.get('id', 'no-id')
                    placeholder = inp.get('placeholder', '')
                    print(f"  - Type: {field_type}, Name: {field_name}, ID: {field_id}, Placeholder: {placeholder}")
                
                # Look for labels or text that might indicate field purposes
                labels = soup.find_all('label')
                print(f"\nLabels found: {len(labels)}")
                for label in labels:
                    print(f"  - {label.text.strip()}")
                
                # Look for any visible text that might help identify fields
                print("\nVisible text elements:")
                for text in soup.find_all(text=True):
                    cleaned = text.strip()
                    if cleaned and len(cleaned) > 2 and cleaned not in ['\\n', '\\r', '\\t']:
                        parent = text.parent.name
                        if parent in ['p', 'div', 'span', 'td', 'th', 'label', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            print(f"  - {parent}: {cleaned[:100]}")
                
                # Save the HTML for manual inspection
                with open('current_system_login.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("\nHTML saved to: current_system_login.html")
                
        except Exception as e:
            print(f"Error accessing the system: {e}")
            print("This might be due to SSL certificate issues or network restrictions")

async def attempt_login():
    """Attempt to login with provided credentials"""
    login_url = "https://www.renhongtech2.com.tw/luckygas_97420648/index.aspx"
    
    # Credentials provided
    credentials = {
        'field1': '97420648',
        'field2': '7001', 
        'field3': '0000'
    }
    
    print("\n=== Login Attempt ===")
    print(f"Credentials: {credentials}")
    
    async with aiohttp.ClientSession() as session:
        try:
            # First get the login page to extract any tokens or session info
            async with session.get(login_url, ssl=False) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for hidden fields (like VIEWSTATE in ASP.NET)
                hidden_fields = {}
                for hidden in soup.find_all('input', type='hidden'):
                    name = hidden.get('name')
                    value = hidden.get('value', '')
                    if name:
                        hidden_fields[name] = value
                
                print(f"\nHidden fields found: {len(hidden_fields)}")
                for k, v in hidden_fields.items():
                    print(f"  - {k}: {v[:50]}..." if len(v) > 50 else f"  - {k}: {v}")
                
                # Try to identify the actual field names
                # Common patterns: username/password, user/pass, account/password, etc.
                possible_username_fields = ['username', 'user', 'account', 'login', 'id', 'userid', 'txt_user']
                possible_password_fields = ['password', 'pass', 'pwd', 'txt_pass', 'txt_password']
                
                # Check actual input names
                actual_fields = []
                for inp in soup.find_all('input', type=['text', 'password']):
                    name = inp.get('name')
                    if name:
                        actual_fields.append(name)
                
                print(f"\nActual input field names: {actual_fields}")
                
        except Exception as e:
            print(f"Error during login attempt: {e}")

if __name__ == "__main__":
    print("Starting analysis of Lucky Gas current management system...")
    asyncio.run(analyze_login_page())
    asyncio.run(attempt_login())