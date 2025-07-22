#!/usr/bin/env python3
"""
GCP Cost Analysis with BigQuery
Analyzes billing data exported to BigQuery for Lucky Gas project
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Import Google Cloud libraries
try:
    from google.cloud import bigquery
    from google.cloud.exceptions import GoogleCloudError
except ImportError:
    print("Error: Google Cloud BigQuery library not installed")
    print("Install with: uv pip install google-cloud-bigquery")
    sys.exit(1)

# Configuration
PROJECT_ID = "vast-tributary-466619-m8"
DATASET_NAME = "billing_export"
BILLING_TABLE_PREFIX = "gcp_billing_export_"

# Cost thresholds
DAILY_COST_WARNING = 50  # USD
DAILY_COST_CRITICAL = 100  # USD
MONTHLY_BUDGET = 1000  # USD

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'  # No Color


class CostAnalyzer:
    """Analyzes GCP billing data from BigQuery"""
    
    def __init__(self, project_id: str = PROJECT_ID):
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = f"{project_id}.{DATASET_NAME}"
        
    def check_dataset_exists(self) -> bool:
        """Check if billing dataset exists"""
        try:
            self.client.get_dataset(self.dataset_id)
            return True
        except Exception:
            return False
    
    def get_current_month_cost(self) -> Dict[str, float]:
        """Get current month total cost"""
        query = f"""
        SELECT
            SUM(cost) as total_cost,
            currency
        FROM
            `{self.dataset_id}.{BILLING_TABLE_PREFIX}*`
        WHERE
            DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
            AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY currency
        """
        
        try:
            results = self.client.query(query).result()
            costs = {}
            for row in results:
                costs[row.currency] = row.total_cost or 0
            return costs
        except Exception as e:
            print(f"{RED}Error querying current month costs: {e}{NC}")
            return {}
    
    def get_daily_costs(self, days: int = 7) -> List[Dict]:
        """Get daily costs for the last N days"""
        query = f"""
        SELECT
            DATE(usage_start_time) as usage_date,
            SUM(cost) as daily_cost,
            currency
        FROM
            `{self.dataset_id}.{BILLING_TABLE_PREFIX}*`
        WHERE
            DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
            AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        GROUP BY usage_date, currency
        ORDER BY usage_date DESC
        """
        
        try:
            results = self.client.query(query).result()
            daily_costs = []
            for row in results:
                daily_costs.append({
                    'date': row.usage_date.strftime('%Y-%m-%d'),
                    'cost': row.daily_cost or 0,
                    'currency': row.currency
                })
            return daily_costs
        except Exception as e:
            print(f"{RED}Error querying daily costs: {e}{NC}")
            return []
    
    def get_top_services(self, limit: int = 10) -> List[Dict]:
        """Get top services by cost for current month"""
        query = f"""
        SELECT
            service.description as service_name,
            SUM(cost) as total_cost,
            currency
        FROM
            `{self.dataset_id}.{BILLING_TABLE_PREFIX}*`
        WHERE
            DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
            AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY service_name, currency
        ORDER BY total_cost DESC
        LIMIT {limit}
        """
        
        try:
            results = self.client.query(query).result()
            services = []
            for row in results:
                services.append({
                    'service': row.service_name,
                    'cost': row.total_cost or 0,
                    'currency': row.currency
                })
            return services
        except Exception as e:
            print(f"{RED}Error querying top services: {e}{NC}")
            return []
    
    def get_cost_by_location(self) -> List[Dict]:
        """Get cost breakdown by location"""
        query = f"""
        SELECT
            location.location as region,
            SUM(cost) as total_cost,
            currency
        FROM
            `{self.dataset_id}.{BILLING_TABLE_PREFIX}*`
        WHERE
            DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
            AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY region, currency
        ORDER BY total_cost DESC
        """
        
        try:
            results = self.client.query(query).result()
            locations = []
            for row in results:
                locations.append({
                    'location': row.region or 'Global',
                    'cost': row.total_cost or 0,
                    'currency': row.currency
                })
            return locations
        except Exception as e:
            print(f"{RED}Error querying costs by location: {e}{NC}")
            return []
    
    def get_cost_forecast(self) -> Dict[str, float]:
        """Forecast monthly cost based on recent usage"""
        query = f"""
        WITH daily_avg AS (
            SELECT
                AVG(daily_cost) as avg_daily_cost,
                currency
            FROM (
                SELECT
                    DATE(usage_start_time) as usage_date,
                    SUM(cost) as daily_cost,
                    currency
                FROM
                    `{self.dataset_id}.{BILLING_TABLE_PREFIX}*`
                WHERE
                    DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
                    AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
                GROUP BY usage_date, currency
            )
            GROUP BY currency
        )
        SELECT
            currency,
            avg_daily_cost,
            avg_daily_cost * EXTRACT(DAY FROM DATE_SUB(DATE_ADD(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH), INTERVAL 1 DAY)) as projected_monthly
        FROM daily_avg
        """
        
        try:
            results = self.client.query(query).result()
            forecast = {}
            for row in results:
                forecast[row.currency] = {
                    'daily_avg': row.avg_daily_cost or 0,
                    'monthly_projection': row.projected_monthly or 0
                }
            return forecast
        except Exception as e:
            print(f"{RED}Error calculating forecast: {e}{NC}")
            return {}
    
    def check_anomalies(self) -> List[Dict]:
        """Check for cost anomalies"""
        query = f"""
        WITH daily_costs AS (
            SELECT
                DATE(usage_start_time) as usage_date,
                SUM(cost) as daily_cost
            FROM
                `{self.dataset_id}.{BILLING_TABLE_PREFIX}*`
            WHERE
                DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            GROUP BY usage_date
        ),
        cost_stats AS (
            SELECT
                AVG(daily_cost) as avg_cost,
                STDDEV(daily_cost) as stddev_cost
            FROM daily_costs
        )
        SELECT
            dc.usage_date,
            dc.daily_cost,
            cs.avg_cost,
            cs.stddev_cost,
            (dc.daily_cost - cs.avg_cost) / cs.stddev_cost as z_score
        FROM daily_costs dc
        CROSS JOIN cost_stats cs
        WHERE ABS((dc.daily_cost - cs.avg_cost) / cs.stddev_cost) > 2
        ORDER BY dc.usage_date DESC
        """
        
        try:
            results = self.client.query(query).result()
            anomalies = []
            for row in results:
                anomalies.append({
                    'date': row.usage_date.strftime('%Y-%m-%d'),
                    'cost': row.daily_cost,
                    'avg_cost': row.avg_cost,
                    'z_score': row.z_score
                })
            return anomalies
        except Exception as e:
            print(f"{RED}Error checking anomalies: {e}{NC}")
            return []


def print_cost_summary(analyzer: CostAnalyzer):
    """Print comprehensive cost summary"""
    print(f"\n{BLUE}=== Lucky Gas GCP Cost Analysis ==={NC}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Current month costs
    print(f"{MAGENTA}▶ Current Month Costs:{NC}")
    month_costs = analyzer.get_current_month_cost()
    for currency, cost in month_costs.items():
        status_color = GREEN if cost < MONTHLY_BUDGET * 0.7 else (YELLOW if cost < MONTHLY_BUDGET else RED)
        print(f"  Total: {status_color}${cost:.2f} {currency}{NC}")
        print(f"  Budget: ${MONTHLY_BUDGET:.2f} ({cost/MONTHLY_BUDGET*100:.1f}% used)")
    
    # Daily costs
    print(f"\n{MAGENTA}▶ Recent Daily Costs:{NC}")
    daily_costs = analyzer.get_daily_costs(7)
    for day_cost in daily_costs[:5]:
        cost = day_cost['cost']
        status = "✓" if cost < DAILY_COST_WARNING else ("⚠" if cost < DAILY_COST_CRITICAL else "✗")
        status_color = GREEN if cost < DAILY_COST_WARNING else (YELLOW if cost < DAILY_COST_CRITICAL else RED)
        print(f"  {day_cost['date']}: {status_color}{status} ${cost:.2f}{NC}")
    
    # Top services
    print(f"\n{MAGENTA}▶ Top Services This Month:{NC}")
    services = analyzer.get_top_services(5)
    for i, service in enumerate(services, 1):
        print(f"  {i}. {service['service']}: ${service['cost']:.2f}")
    
    # Cost by location
    print(f"\n{MAGENTA}▶ Cost by Location:{NC}")
    locations = analyzer.get_cost_by_location()
    for location in locations[:5]:
        print(f"  {location['location']}: ${location['cost']:.2f}")
    
    # Forecast
    print(f"\n{MAGENTA}▶ Cost Forecast:{NC}")
    forecast = analyzer.get_cost_forecast()
    for currency, data in forecast.items():
        projected = data['monthly_projection']
        status_color = GREEN if projected < MONTHLY_BUDGET * 0.8 else (YELLOW if projected < MONTHLY_BUDGET else RED)
        print(f"  Daily Average: ${data['daily_avg']:.2f}")
        print(f"  Monthly Projection: {status_color}${projected:.2f}{NC}")
        if projected > MONTHLY_BUDGET:
            overage = projected - MONTHLY_BUDGET
            print(f"  {RED}⚠ Warning: Projected to exceed budget by ${overage:.2f}{NC}")
    
    # Anomalies
    print(f"\n{MAGENTA}▶ Cost Anomalies:{NC}")
    anomalies = analyzer.check_anomalies()
    if anomalies:
        print(f"  {YELLOW}Found {len(anomalies)} anomalous days:{NC}")
        for anomaly in anomalies[:3]:
            z_score = anomaly['z_score']
            direction = "above" if z_score > 0 else "below"
            print(f"  {anomaly['date']}: ${anomaly['cost']:.2f} ({abs(z_score):.1f}σ {direction} average)")
    else:
        print(f"  {GREEN}No significant anomalies detected{NC}")


def export_to_json(analyzer: CostAnalyzer, filename: str = "cost_analysis.json"):
    """Export cost analysis to JSON file"""
    data = {
        'generated': datetime.now().isoformat(),
        'project_id': analyzer.project_id,
        'current_month_costs': analyzer.get_current_month_cost(),
        'daily_costs': analyzer.get_daily_costs(30),
        'top_services': analyzer.get_top_services(20),
        'cost_by_location': analyzer.get_cost_by_location(),
        'forecast': analyzer.get_cost_forecast(),
        'anomalies': analyzer.check_anomalies()
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n{GREEN}✓ Cost analysis exported to {filename}{NC}")


def main():
    """Main execution"""
    # Check if BigQuery dataset exists
    analyzer = CostAnalyzer()
    
    if not analyzer.check_dataset_exists():
        print(f"{RED}Error: BigQuery dataset {DATASET_NAME} not found{NC}")
        print(f"\nPlease run: {BLUE}./setup-billing-export.sh{NC}")
        print("Then configure billing export in Cloud Console")
        sys.exit(1)
    
    # Run cost analysis
    try:
        print_cost_summary(analyzer)
        
        # Export to JSON if requested
        if len(sys.argv) > 1 and sys.argv[1] == '--export':
            export_to_json(analyzer)
        
        print(f"\n{BLUE}For more detailed analysis, use BigQuery directly or Data Studio{NC}")
        
    except GoogleCloudError as e:
        print(f"{RED}Google Cloud Error: {e}{NC}")
        print("\nPossible issues:")
        print("1. Billing export not yet configured")
        print("2. No billing data available yet (wait 24 hours after setup)")
        print("3. Missing BigQuery permissions")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Unexpected error: {e}{NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()