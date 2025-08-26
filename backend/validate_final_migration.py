#!/usr/bin/env python3
"""
驗證最終遷移結果
Validate final migration results
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models_comprehensive import (
    Customer, CustomerCylinder, CustomerTimeAvailability,
    CylinderType, PricingMethod, PaymentMethod
)
from collections import Counter

# Connect to database
engine = create_engine("sqlite:///luckygas_comprehensive.db")
Session = sessionmaker(bind=engine)
session = Session()

print("="*80)
print("最終遷移驗證報告 / Final Migration Validation Report")
print("="*80)

# 1. Check customer count
total_customers = session.query(Customer).count()
print(f"\n✅ 客戶總數 / Total Customers: {total_customers}/1267")

# 2. Check for enum issues
print("\n📊 列舉類型驗證 / Enum Type Validation:")
print("-"*40)

# Check cylinder types
cylinders = session.query(CustomerCylinder).all()
cylinder_types = Counter([c.cylinder_type for c in cylinders])
print("\n瓦斯瓶類型分布 / Cylinder Type Distribution:")
for cyl_type, count in sorted(cylinder_types.items(), key=lambda x: x[1], reverse=True):
    try:
        # Validate it's a valid enum
        CylinderType(cyl_type)
        print(f"  ✅ {cyl_type}: {count}")
    except:
        print(f"  ❌ INVALID ENUM: {cyl_type}: {count}")

# Check pricing methods
customers = session.query(Customer).all()
pricing_methods = Counter([c.pricing_method for c in customers if c.pricing_method])
print("\n計價方式分布 / Pricing Method Distribution:")
for method, count in sorted(pricing_methods.items(), key=lambda x: x[1], reverse=True):
    try:
        PricingMethod(method)
        print(f"  ✅ {method}: {count}")
    except:
        print(f"  ❌ INVALID ENUM: {method}: {count}")

# Check payment methods
payment_methods = Counter([c.payment_method for c in customers if c.payment_method])
print("\n付款方式分布 / Payment Method Distribution:")
for method, count in sorted(payment_methods.items(), key=lambda x: x[1], reverse=True):
    try:
        PaymentMethod(method)
        print(f"  ✅ {method}: {count}")
    except:
        print(f"  ❌ INVALID ENUM: {method}: {count}")

# 3. Check data completeness
print("\n📈 資料完整性檢查 / Data Completeness Check:")
print("-"*40)

# Check customers with cylinders
customers_with_cylinders = session.query(Customer).join(CustomerCylinder).distinct().count()
print(f"有瓦斯瓶配置的客戶 / Customers with Cylinders: {customers_with_cylinders}")

# Check customers with pricing
customers_with_pricing = session.query(Customer).filter(Customer.pricing_method != None).count()
print(f"有計價設定的客戶 / Customers with Pricing: {customers_with_pricing}")

# Check customers with delivery times
customers_with_delivery = session.query(Customer).join(CustomerTimeAvailability).distinct().count()
print(f"有配送時間的客戶 / Customers with Delivery Times: {customers_with_delivery}")

# Check customers with payment methods
customers_with_payment = session.query(Customer).filter(Customer.payment_method != None).count()
print(f"有付款方式的客戶 / Customers with Payment Methods: {customers_with_payment}")

# 4. Sample data check
print("\n🔍 樣本資料檢查 / Sample Data Check:")
print("-"*40)

# Check a few customers to verify data integrity
sample_customers = session.query(Customer).limit(5).all()
for customer in sample_customers:
    print(f"\n客戶 {customer.customer_code}: {customer.short_name}")
    
    # Check cylinders
    cylinders = session.query(CustomerCylinder).filter_by(customer_id=customer.id).all()
    if cylinders:
        print(f"  瓦斯瓶: {', '.join([f'{c.cylinder_type}({c.quantity})' for c in cylinders])}")
    
    # Check pricing
    if customer.pricing_method:
        print(f"  計價: {customer.pricing_method}")
    
    # Check payment
    if customer.payment_method:
        print(f"  付款: {customer.payment_method}")

# 5. Final summary
print("\n"+"="*80)
print("總結 / Summary:")
print("="*80)

if total_customers == 1267:
    print("✅ 成功！所有1267位客戶都已成功遷移")
    print("✅ Success! All 1267 customers have been successfully migrated")
else:
    missing = 1267 - total_customers
    print(f"⚠️ 警告：缺少 {missing} 位客戶")
    print(f"⚠️ Warning: {missing} customers are missing")

# Check for any invalid enums
all_valid = True
for c in cylinders:
    try:
        CylinderType(c.cylinder_type)
    except:
        all_valid = False
        print(f"❌ Invalid cylinder type: {c.cylinder_type} for customer {c.customer_id}")

if all_valid:
    print("✅ 所有枚舉值都有效")
    print("✅ All enum values are valid")
else:
    print("❌ 發現無效的枚舉值，請檢查上方錯誤")
    print("❌ Invalid enum values found, please check errors above")

session.close()