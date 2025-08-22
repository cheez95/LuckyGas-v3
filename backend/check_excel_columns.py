#!/usr/bin/env python
"""
Check the columns in the Excel files
"""

import pandas as pd

# Check client list columns
client_file = "/Users/lgee258/Desktop/LuckyGas-v3/raw/2025-05 commercial client list.xlsx"
df_clients = pd.read_excel(client_file)
print("=" * 60)
print("CLIENT LIST COLUMNS:")
print("=" * 60)
for col in df_clients.columns:
    print(f"  - {col}")
print(f"\nTotal rows: {len(df_clients)}")
print("\nFirst 3 rows:")
print(df_clients.head(3))

# Check delivery history columns
delivery_file = "/Users/lgee258/Desktop/LuckyGas-v3/raw/2025-05 commercial deliver history.xlsx"
df_delivery = pd.read_excel(delivery_file)
print("\n" + "=" * 60)
print("DELIVERY HISTORY COLUMNS:")
print("=" * 60)
for col in df_delivery.columns:
    print(f"  - {col}")
print(f"\nTotal rows: {len(df_delivery)}")
print("\nFirst 3 rows:")
print(df_delivery.head(3))