#!/usr/bin/env python3
"""
Script to examine the structure of Excel files in the raw directory
"""
import os
from pathlib import Path

import pandas as pd

# Get the project root directory
project_root = Path(__file__).resolve().parent.parent.parent.parent
raw_dir = project_root / "raw"


def examine_excel_file(file_path):
    """Examine Excel file structure and contents"""
    print(f"\n{'='*60}")
    print(f"Examining: {file_path.name}")
    print(f"{'='*60}")

    try:
        # Read Excel file
        xl_file = pd.ExcelFile(file_path)

        print(f"\nSheets in file: {xl_file.sheet_names}")

        # Examine each sheet
        for sheet_name in xl_file.sheet_names:
            print(f"\n--- Sheet: {sheet_name} ---")
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            print(f"Shape: {df.shape} (rows: {len(df)}, columns: {len(df.columns)})")
            print(f"\nColumns: {list(df.columns)}")
            print(f"\nData types:")
            print(df.dtypes)

            print(f"\nFirst 5 rows:")
            print(df.head())

            print(f"\nNull values:")
            print(df.isnull().sum())

            # Show unique values for categorical columns
            for col in df.columns:
                if df[col].dtype == "object" and df[col].nunique() < 20:
                    print(f"\nUnique values in '{col}': {df[col].unique()[:10]}")

    except Exception as e:
        print(f"Error reading file: {e}")


def main():
    # List files in raw directory
    print(f"Raw directory: {raw_dir}")
    print(f"Files in raw directory:")
    for file in os.listdir(raw_dir):
        print(f"  - {file}")

    # Examine client list
    client_file = raw_dir / "2025-05 client liss.xlsx"
    if client_file.exists():
        examine_excel_file(client_file)
    else:
        print(f"\nClient file not found: {client_file}")

    # Examine delivery history
    delivery_file = raw_dir / "2025-05 deliver history.xlsx"
    if delivery_file.exists():
        examine_excel_file(delivery_file)
    else:
        print(f"\nDelivery history file not found: {delivery_file}")


if __name__ == "__main__":
    main()
