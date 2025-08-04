#!/usr/bin/env python3
"""Check delivery history Excel file structure"""
from pathlib import Path

import pandas as pd

# File path
DELIVERY_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "raw"
    / "2025-05 deliver history.xlsx"
)

print(f"Checking file: {DELIVERY_FILE}")

# Read all sheets
xl_file = pd.ExcelFile(DELIVERY_FILE)
print(f"\nSheets in file: {xl_file.sheet_names}")

# Check first sheet
df = pd.read_excel(DELIVERY_FILE, sheet_name="Sheet1")
print(f"\nSheet1 shape: {df.shape}")
print(f"\nColumns: {list(df.columns)}")
print(f"\nFirst 10 rows:")
print(df.head(10))

# Check for non-null data
print(f"\nNon-null counts:")
print(df.count())
