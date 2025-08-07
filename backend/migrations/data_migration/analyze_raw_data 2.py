#!/usr/bin/env python3
"""
Analyze raw data files for Lucky Gas data migration.
This script examines the structure of Excel files and SQLite database
to prepare for migration to PostgreSQL.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class DataAnalyzer:
    def __init__(self, raw_data_path: str = "../../../raw"):
        self.raw_data_path = raw_data_path
        self.analysis_results = {}
        
    def analyze_all(self):
        """Analyze all data sources."""
        print("Starting data analysis for Lucky Gas migration...")
        print("=" * 60)
        
        # Analyze Excel files
        self.analyze_excel_file("2025-05 commercial client list.xlsx", "Commercial Clients")
        self.analyze_excel_file("2025-05 commercial deliver history.xlsx", "Delivery History")
        self.analyze_excel_file("2025-07 residential client delivery plan.xlsx", "Residential Delivery Plan")
        
        # Analyze SQLite database
        self.analyze_sqlite_database("luckygas.db")
        
        # Save analysis results
        self.save_analysis_results()
        
    def analyze_excel_file(self, filename: str, description: str):
        """Analyze Excel file structure and data."""
        filepath = os.path.join(self.raw_data_path, filename)
        print(f"\nAnalyzing {description}: {filename}")
        print("-" * 60)
        
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(filepath)
            
            file_analysis = {
                "filename": filename,
                "description": description,
                "sheets": {}
            }
            
            # Analyze each sheet
            for sheet_name in excel_file.sheet_names:
                print(f"\n  Sheet: {sheet_name}")
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                
                sheet_analysis = {
                    "rows": len(df),
                    "columns": [str(col) for col in df.columns],
                    "column_types": {str(col): str(df[col].dtype) for col in df.columns},
                    "null_counts": {str(col): int(count) for col, count in df.isnull().sum().items()},
                    "sample_data": df.head(3).to_dict(orient="records") if len(df) > 0 else [],
                    "unique_counts": {}
                }
                
                # Get unique value counts for key columns
                for col in df.columns:
                    # Convert column name to string to avoid datetime key issues
                    col_str = str(col)
                    if df[col].dtype == 'object':  # String columns
                        unique_count = df[col].nunique()
                        if unique_count < 100:  # Only show if reasonable number
                            sheet_analysis["unique_counts"][col_str] = unique_count
                
                file_analysis["sheets"][sheet_name] = sheet_analysis
                
                # Print summary
                print(f"    - Rows: {len(df)}")
                print(f"    - Columns: {len(df.columns)}")
                print(f"    - Column names: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}")
                
            self.analysis_results[filename] = file_analysis
            
        except Exception as e:
            print(f"  ERROR: Failed to analyze {filename}: {str(e)}")
            self.analysis_results[filename] = {"error": str(e)}
    
    def analyze_sqlite_database(self, filename: str):
        """Analyze SQLite database structure and data."""
        filepath = os.path.join(self.raw_data_path, filename)
        print(f"\nAnalyzing SQLite Database: {filename}")
        print("-" * 60)
        
        try:
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            
            db_analysis = {
                "filename": filename,
                "description": "SQLite Database",
                "tables": {}
            }
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"  Found {len(tables)} tables")
            
            for table_name in tables:
                table_name = table_name[0]
                print(f"\n  Table: {table_name}")
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                schema = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                row_count = cursor.fetchone()[0]
                
                # Get sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                sample_data = cursor.fetchall()
                
                table_analysis = {
                    "row_count": row_count,
                    "columns": [
                        {
                            "name": col[1],
                            "type": col[2],
                            "nullable": not col[3],
                            "default": col[4],
                            "primary_key": bool(col[5])
                        }
                        for col in schema
                    ],
                    "sample_data": sample_data[:3] if sample_data else []
                }
                
                db_analysis["tables"][table_name] = table_analysis
                
                # Print summary
                print(f"    - Rows: {row_count}")
                print(f"    - Columns: {len(schema)}")
                column_names = [col[1] for col in schema]
                print(f"    - Column names: {', '.join(column_names[:5])}{'...' if len(column_names) > 5 else ''}")
            
            self.analysis_results[filename] = db_analysis
            conn.close()
            
        except Exception as e:
            print(f"  ERROR: Failed to analyze {filename}: {str(e)}")
            self.analysis_results[filename] = {"error": str(e)}
    
    def save_analysis_results(self):
        """Save analysis results to JSON file."""
        output_file = "data_analysis_results.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n\nAnalysis complete! Results saved to: {output_file}")
        print("=" * 60)
        
        # Print summary
        print("\nSummary:")
        for source, data in self.analysis_results.items():
            if "error" not in data:
                if source.endswith('.xlsx'):
                    total_rows = sum(sheet["rows"] for sheet in data["sheets"].values())
                    print(f"  - {source}: {len(data['sheets'])} sheets, {total_rows:,} total rows")
                elif source.endswith('.db'):
                    total_rows = sum(table["row_count"] for table in data["tables"].values())
                    print(f"  - {source}: {len(data['tables'])} tables, {total_rows:,} total rows")


if __name__ == "__main__":
    analyzer = DataAnalyzer()
    analyzer.analyze_all()