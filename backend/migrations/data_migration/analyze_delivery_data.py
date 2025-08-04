#!/usr/bin/env python3
"""
Delivery History Data Analysis Script
Analyzes the delivery history Excel file to prepare for migration
Author: Devin (Data Migration Specialist)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
from collections import Counter
import json

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle numpy types"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class DeliveryDataAnalyzer:
    """Analyzes delivery history data for migration preparation"""
    
    def __init__(self, excel_file: str):
        self.excel_file = excel_file
        self.df = None
        self.analysis_results = {
            'file_info': {},
            'data_quality': {},
            'column_analysis': {},
            'business_insights': {},
            'migration_recommendations': {}
        }
    
    def analyze(self):
        """Run complete analysis"""
        print("🔍 Starting Delivery History Analysis...")
        print("=" * 60)
        
        # Load data
        self.load_data()
        
        # Run analyses
        self.analyze_file_info()
        self.analyze_columns()
        self.analyze_data_quality()
        self.analyze_business_patterns()
        self.generate_recommendations()
        
        # Save results
        self.save_results()
        self.print_summary()
    
    def load_data(self):
        """Load Excel data with proper encoding"""
        print("📂 Loading Excel file...")
        self.df = pd.read_excel(self.excel_file)
        print(f"✅ Loaded {len(self.df)} records")
    
    def analyze_file_info(self):
        """Analyze basic file information"""
        self.analysis_results['file_info'] = {
            'total_records': len(self.df),
            'columns': list(self.df.columns),
            'memory_usage_mb': self.df.memory_usage(deep=True).sum() / 1024 / 1024,
            'estimated_migration_time_minutes': len(self.df) / 5000 * 2  # 2 min per 5K records
        }
    
    def analyze_columns(self):
        """Analyze each column for data types and patterns"""
        print("\n📊 Analyzing columns...")
        
        for col in self.df.columns:
            col_analysis = {
                'data_type': str(self.df[col].dtype),
                'null_count': self.df[col].isna().sum(),
                'null_percentage': (self.df[col].isna().sum() / len(self.df)) * 100,
                'unique_values': self.df[col].nunique(),
                'sample_values': list(self.df[col].dropna().head(5))
            }
            
            # Special analysis for specific columns
            if '日期' in col or 'date' in col.lower():
                col_analysis['date_format'] = self.detect_date_format(self.df[col])
            
            if '客戶' in col:
                col_analysis['client_code_format'] = self.analyze_client_codes(self.df[col])
            
            if '金額' in col or '價' in col:
                col_analysis['numeric_stats'] = {
                    'min': float(self.df[col].min()) if pd.api.types.is_numeric_dtype(self.df[col]) else None,
                    'max': float(self.df[col].max()) if pd.api.types.is_numeric_dtype(self.df[col]) else None,
                    'mean': float(self.df[col].mean()) if pd.api.types.is_numeric_dtype(self.df[col]) else None
                }
            
            self.analysis_results['column_analysis'][col] = col_analysis
    
    def detect_date_format(self, date_column):
        """Detect date format (Taiwan or Western)"""
        sample = date_column.dropna().head(100)
        taiwan_count = 0
        western_count = 0
        
        for date_val in sample:
            if isinstance(date_val, (int, float)):
                # Likely Taiwan date (e.g., 1130520)
                if 1000000 <= date_val <= 9999999:
                    taiwan_count += 1
            elif isinstance(date_val, str):
                if '/' in date_val or '-' in date_val:
                    western_count += 1
            elif pd.api.types.is_datetime64_any_dtype(type(date_val)):
                western_count += 1
        
        if taiwan_count > western_count:
            return 'taiwan_minguo'
        else:
            return 'western'
    
    def analyze_client_codes(self, client_column):
        """Analyze client code patterns"""
        sample = client_column.dropna().head(100)
        lengths = [len(str(code)) for code in sample]
        most_common_length = Counter(lengths).most_common(1)[0][0]
        
        return {
            'most_common_length': most_common_length,
            'all_numeric': all(str(code).isdigit() for code in sample),
            'sample_codes': list(sample.head(5))
        }
    
    def analyze_data_quality(self):
        """Analyze data quality issues"""
        print("\n🔍 Analyzing data quality...")
        
        quality_issues = []
        
        # Check for duplicate records
        duplicate_count = self.df.duplicated().sum()
        if duplicate_count > 0:
            quality_issues.append(f"Found {duplicate_count} duplicate records")
        
        # Check for missing critical fields
        critical_fields = ['客戶編號', '日期']
        for field in critical_fields:
            if field in self.df.columns:
                missing = self.df[field].isna().sum()
                if missing > 0:
                    quality_issues.append(f"Missing {field}: {missing} records")
        
        # Check for invalid amounts
        amount_fields = [col for col in self.df.columns if '金額' in col or '價' in col]
        for field in amount_fields:
            if pd.api.types.is_numeric_dtype(self.df[field]):
                negative = (self.df[field] < 0).sum()
                if negative > 0:
                    quality_issues.append(f"Negative amounts in {field}: {negative} records")
        
        self.analysis_results['data_quality'] = {
            'issues': quality_issues,
            'quality_score': 100 - (len(quality_issues) * 5),  # Deduct 5% per issue
            'duplicate_records': duplicate_count
        }
    
    def analyze_business_patterns(self):
        """Analyze business patterns in the data"""
        print("\n📈 Analyzing business patterns...")
        
        insights = {}
        
        # Analyze delivery frequency by client
        if '客戶編號' in self.df.columns:
            client_frequency = self.df['客戶編號'].value_counts()
            insights['top_clients'] = {
                'most_deliveries': str(client_frequency.index[0]),
                'delivery_count': int(client_frequency.iloc[0]),
                'unique_clients': len(client_frequency)
            }
        
        # Analyze date range
        date_cols = [col for col in self.df.columns if '日期' in col]
        if date_cols:
            date_col = date_cols[0]
            if pd.api.types.is_numeric_dtype(self.df[date_col]):
                insights['date_range'] = {
                    'min': int(self.df[date_col].min()),
                    'max': int(self.df[date_col].max())
                }
        
        # Analyze product types
        product_cols = [col for col in self.df.columns if '瓦斯' in col or '類型' in col]
        if product_cols:
            product_col = product_cols[0]
            product_dist = self.df[product_col].value_counts()
            insights['product_distribution'] = {
                str(k): int(v) for k, v in product_dist.head(10).items()
            }
        
        self.analysis_results['business_insights'] = insights
    
    def generate_recommendations(self):
        """Generate migration recommendations"""
        print("\n💡 Generating recommendations...")
        
        recommendations = []
        
        # Batch size recommendation
        total_records = len(self.df)
        if total_records > 100000:
            recommendations.append("Use batch size of 5000 for optimal performance")
        elif total_records > 50000:
            recommendations.append("Use batch size of 2000 for optimal performance")
        else:
            recommendations.append("Can process in single batch")
        
        # Memory recommendation
        memory_mb = self.analysis_results['file_info']['memory_usage_mb']
        if memory_mb > 100:
            recommendations.append(f"Implement chunked reading - data uses {memory_mb:.2f} MB")
        
        # Date conversion recommendation
        date_formats = []
        for col, analysis in self.analysis_results['column_analysis'].items():
            if 'date_format' in analysis:
                date_formats.append(analysis['date_format'])
        
        if 'taiwan_minguo' in date_formats:
            recommendations.append("Implement Taiwan date converter for 民國年 dates")
        
        # Data quality recommendations
        quality_score = self.analysis_results['data_quality']['quality_score']
        if quality_score < 90:
            recommendations.append("Implement robust error handling for data quality issues")
        
        self.analysis_results['migration_recommendations'] = {
            'recommendations': recommendations,
            'estimated_complexity': 'high' if total_records > 100000 else 'medium',
            'suggested_approach': 'batch_processing' if total_records > 50000 else 'bulk_insert'
        }
    
    def save_results(self):
        """Save analysis results to JSON"""
        output_file = 'delivery_data_analysis.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        print(f"\n💾 Analysis saved to {output_file}")
    
    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "=" * 60)
        print("DELIVERY DATA ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\n📊 File Information:")
        print(f"  - Total Records: {self.analysis_results['file_info']['total_records']:,}")
        print(f"  - Columns: {len(self.analysis_results['file_info']['columns'])}")
        print(f"  - Memory Usage: {self.analysis_results['file_info']['memory_usage_mb']:.2f} MB")
        print(f"  - Est. Migration Time: {self.analysis_results['file_info']['estimated_migration_time_minutes']:.0f} minutes")
        
        print(f"\n🔍 Data Quality:")
        print(f"  - Quality Score: {self.analysis_results['data_quality']['quality_score']}%")
        print(f"  - Issues Found: {len(self.analysis_results['data_quality']['issues'])}")
        for issue in self.analysis_results['data_quality']['issues'][:5]:
            print(f"    • {issue}")
        
        print(f"\n💡 Recommendations:")
        for rec in self.analysis_results['migration_recommendations']['recommendations']:
            print(f"  • {rec}")
        
        print(f"\n🎯 Migration Approach: {self.analysis_results['migration_recommendations']['suggested_approach'].upper()}")
        print(f"📈 Complexity: {self.analysis_results['migration_recommendations']['estimated_complexity'].upper()}")


def main():
    """Main entry point"""
    excel_file = 'raw/2025-05 commercial deliver history.xlsx'
    
    if not os.path.exists(excel_file):
        print(f"❌ Error: File not found: {excel_file}")
        sys.exit(1)
    
    analyzer = DeliveryDataAnalyzer(excel_file)
    analyzer.analyze()


if __name__ == "__main__":
    main()