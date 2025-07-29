#!/usr/bin/env python
import requests
import json

# Create admin user
user_data = {
    "username": "admin",
    "email": "admin@luckygas.tw",
    "password": "admin123",
    "full_name": "系統管理員",
    "role": "super_admin"
}

# Register the user
response = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    json=user_data
)

if response.status_code == 200:
    print("✅ Admin user created successfully!")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
else:
    print(f"❌ Failed to create admin user: {response.status_code}")
    print(response.text)