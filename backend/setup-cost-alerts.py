#!/usr/bin/env python3
"""
Setup Cost Alerts for Lucky Gas GCP Project
Configures budget alerts and monitoring using Cloud Billing API
"""

import os
import sys
import yaml
from typing import Dict, List
from datetime import datetime

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'  # No Color


def print_status(status: str, message: str):
    """Print colored status messages"""
    symbols = {
        "success": f"{GREEN}✓{NC}",
        "error": f"{RED}✗{NC}",
        "warning": f"{YELLOW}⚠{NC}",
        "info": f"{BLUE}ℹ{NC}",
        "step": f"{MAGENTA}▶{NC}"
    }
    print(f"{symbols.get(status, '')} {message}")


def load_config(config_file: str = "cost-alerts-config.yaml") -> Dict:
    """Load alert configuration from YAML file"""
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print_status("error", f"Configuration file {config_file} not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        print_status("error", f"Error parsing YAML: {e}")
        sys.exit(1)


def generate_terraform_config(config: Dict) -> str:
    """Generate Terraform configuration for budget alerts"""
    terraform_config = '''# Terraform configuration for Lucky Gas GCP Budget Alerts
# Generated from cost-alerts-config.yaml

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "asia-east1"
}

variable "project_id" {
  default = "''' + config['project_id'] + '''"
}

variable "billing_account" {
  default = "''' + config['billing_account'] + '''"
}

# Notification channels
resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notification Channel"
  type         = "email"
  
  labels = {
    email_address = "admin@luckygas.com"
  }
}

'''
    
    # Add monthly budget
    monthly_budget = config['budgets']['monthly_total']
    terraform_config += f'''
# Monthly Total Budget
resource "google_billing_budget" "monthly_total" {{
  billing_account = var.billing_account
  display_name    = "{monthly_budget['name']}"
  
  budget_filter {{
    projects = ["projects/${{var.project_id}}"]
  }}
  
  amount {{
    specified_amount {{
      currency_code = "{monthly_budget['currency']}"
      units         = "{monthly_budget['amount']}"
    }}
  }}
'''
    
    # Add thresholds
    for threshold in monthly_budget['thresholds']:
        terraform_config += f'''
  threshold_rules {{
    threshold_percent = {threshold['percent'] / 100.0}
    spend_basis      = "CURRENT_SPEND"
  }}
'''
    
    terraform_config += '''
  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.id,
    ]
  }
}
'''
    
    # Add service-specific budgets
    for service_budget in config['service_budgets']:
        service_id = service_budget['service'].replace('.', '_')
        terraform_config += f'''
# {service_budget['name']}
resource "google_billing_budget" "{service_id}_budget" {{
  billing_account = var.billing_account
  display_name    = "{service_budget['name']}"
  
  budget_filter {{
    projects = ["projects/${{var.project_id}}"]
    services = ["{service_budget['service']}"]
  }}
  
  amount {{
    specified_amount {{
      currency_code = "USD"
      units         = "{service_budget['monthly_amount']}"
    }}
  }}
  
  threshold_rules {{
    threshold_percent = 0.5
  }}
  
  threshold_rules {{
    threshold_percent = 0.8
  }}
  
  threshold_rules {{
    threshold_percent = 1.0
  }}
  
  all_updates_rule {{
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.id,
    ]
  }}
}}
'''
    
    return terraform_config


def generate_monitoring_script(config: Dict) -> str:
    """Generate monitoring script for cost alerts"""
    script = '''#!/bin/bash
# Cost Alert Monitoring Script
# Checks for budget alerts and anomalies

set -euo pipefail

# Configuration
PROJECT_ID="''' + config['project_id'] + '''"
DATASET_NAME="billing_export"

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

echo -e "${BLUE}=== Lucky Gas Cost Alert Check ===${NC}"
echo "Date: $(date)"
echo

# Function to check budget status
check_budget_status() {
    echo -e "${BLUE}Checking budget status...${NC}"
    
    # Get current month spend
    current_spend=$(bq query --use_legacy_sql=false --format=csv --max_rows=1 << SQL
SELECT ROUND(SUM(cost), 2) as total_cost
FROM \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
SQL
    | tail -1)
    
    echo "Current month spend: \\$$current_spend"
    
    # Check against thresholds
'''
    
    # Add threshold checks
    for threshold in config['budgets']['monthly_total']['thresholds']:
        threshold_amount = config['budgets']['monthly_total']['amount'] * threshold['percent'] / 100
        script += f'''
    if (( $(echo "$current_spend > {threshold_amount}" | bc -l) )); then
        echo -e "${{YELLOW}}⚠ Alert: Spending exceeded {threshold['percent']}% of budget (\\${threshold_amount})${{NC}}"
        echo "Message: {threshold['message']}"
    fi
'''
    
    script += '''
}

# Function to check for anomalies
check_anomalies() {
    echo -e "\\n${BLUE}Checking for cost anomalies...${NC}"
    
    # Query for anomalies
    anomalies=$(bq query --use_legacy_sql=false --format=pretty --max_rows=5 << SQL
WITH daily_costs AS (
  SELECT
    DATE(usage_start_time) as usage_date,
    SUM(cost) as daily_cost
  FROM \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
  WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY usage_date
),
stats AS (
  SELECT
    AVG(daily_cost) as avg_cost,
    STDDEV(daily_cost) as stddev_cost
  FROM daily_costs
)
SELECT
  d.usage_date,
  ROUND(d.daily_cost, 2) as daily_cost,
  ROUND((d.daily_cost - s.avg_cost) / s.stddev_cost, 1) as z_score
FROM daily_costs d
CROSS JOIN stats s
WHERE ABS((d.daily_cost - s.avg_cost) / s.stddev_cost) > 2
ORDER BY d.usage_date DESC
LIMIT 5
SQL
    )
    
    if [ -n "$anomalies" ]; then
        echo -e "${YELLOW}Found cost anomalies:${NC}"
        echo "$anomalies"
    else
        echo -e "${GREEN}No anomalies detected${NC}"
    fi
}

# Function to check unused resources
check_unused_resources() {
    echo -e "\\n${BLUE}Checking for unused resources...${NC}"
    
    unused=$(bq query --use_legacy_sql=false --format=pretty --max_rows=10 << SQL
SELECT
  service.description as service,
  sku.description as sku,
  ROUND(SUM(cost), 2) as total_cost
FROM \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE 
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND cost > 0
  AND (usage.amount = 0 OR usage.amount IS NULL)
GROUP BY service, sku
HAVING total_cost > 10
ORDER BY total_cost DESC
SQL
    )
    
    if [ -n "$unused" ]; then
        echo -e "${YELLOW}Potentially unused resources:${NC}"
        echo "$unused"
    else
        echo -e "${GREEN}No significant unused resources found${NC}"
    fi
}

# Main execution
check_budget_status
check_anomalies
check_unused_resources

echo -e "\\n${BLUE}Alert check complete${NC}"
'''
    
    return script


def generate_setup_instructions(config: Dict) -> str:
    """Generate setup instructions for manual configuration"""
    instructions = f'''# Lucky Gas Cost Alerts Setup Instructions

## Overview
This guide helps you set up comprehensive cost alerts for the Lucky Gas GCP project.

**Project ID**: {config['project_id']}
**Billing Account**: {config['billing_account']}

## 1. Manual Budget Alert Setup

### Via Cloud Console:
1. Go to [Billing Budgets & Alerts](https://console.cloud.google.com/billing/{config['billing_account'][8:]}/budgets)
2. Click "CREATE BUDGET"
3. Configure the following budgets:

#### Monthly Total Budget:
- **Name**: {config['budgets']['monthly_total']['name']}
- **Amount**: ${config['budgets']['monthly_total']['amount']} USD
- **Projects**: Select "{config['project_id']}"
- **Thresholds**:
'''
    
    for threshold in config['budgets']['monthly_total']['thresholds']:
        instructions += f"  - {threshold['percent']}%: {threshold['message']}\n"
    
    instructions += '''
#### Service-Specific Budgets:
'''
    
    for service_budget in config['service_budgets']:
        instructions += f'''
**{service_budget['name']}**:
- Amount: ${service_budget['monthly_amount']} USD
- Service: {service_budget['service']}
- Thresholds: {', '.join(map(str, service_budget['thresholds']))}%
'''
    
    instructions += '''
## 2. Using Terraform (Recommended)

```bash
# Install Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# Initialize Terraform
cd terraform/
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

## 3. Using gcloud CLI

```bash
# Create a budget with gcloud (basic example)
gcloud billing budgets create \\
  --billing-account={config['billing_account']} \\
  --display-name="Lucky Gas Monthly Budget" \\
  --budget-amount=1000 \\
  --threshold-rule=percent=0.5 \\
  --threshold-rule=percent=0.75 \\
  --threshold-rule=percent=0.9 \\
  --threshold-rule=percent=1.0
```

## 4. Setting Up Alert Channels

### Email Alerts:
Already configured in the budgets

### Slack Integration:
1. Create a Slack Webhook:
   - Go to your Slack workspace settings
   - Add an Incoming Webhook
   - Copy the webhook URL
2. Update the webhook URL in cost-alerts-config.yaml
3. Test with: `curl -X POST -H 'Content-type: application/json' --data '{{"text":"Test alert"}}' YOUR_WEBHOOK_URL`

### PagerDuty Integration:
1. Create a PagerDuty service
2. Get the integration key
3. Update the key in cost-alerts-config.yaml

## 5. Monitoring Dashboard

Create a custom dashboard:
1. Go to [Cloud Monitoring](https://console.cloud.google.com/monitoring/dashboards)
2. Create new dashboard
3. Add widgets for:
   - Current month spend
   - Daily cost trend
   - Service breakdown
   - Budget utilization

## 6. Regular Monitoring

Run the monitoring script:
```bash
./monitor-cost-alerts.sh
```

Or schedule with cron:
```bash
# Add to crontab for daily checks at 9 AM
0 9 * * * /path/to/monitor-cost-alerts.sh
```

## 7. Cost Optimization Tips

1. **Review unused resources weekly**
2. **Set up committed use discounts** for predictable workloads
3. **Use preemptible VMs** for non-critical workloads
4. **Implement storage lifecycle policies**
5. **Monitor and optimize network egress**

## Important Notes

- Budget alerts typically have a delay of 1-2 hours
- Alerts are based on actual spend, not projected
- Set conservative thresholds to avoid surprises
- Review and adjust budgets monthly
'''
    
    return instructions


def main():
    """Main execution"""
    print(f"{BLUE}=== Lucky Gas Cost Alerts Setup ==={NC}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load configuration
    print_status("step", "Loading configuration...")
    config = load_config()
    print_status("success", "Configuration loaded")
    
    # Generate Terraform configuration
    print_status("step", "Generating Terraform configuration...")
    terraform_dir = "./terraform"
    os.makedirs(terraform_dir, exist_ok=True)
    
    terraform_config = generate_terraform_config(config)
    with open(f"{terraform_dir}/budgets.tf", 'w') as f:
        f.write(terraform_config)
    print_status("success", f"Terraform configuration saved to {terraform_dir}/budgets.tf")
    
    # Generate monitoring script
    print_status("step", "Generating monitoring script...")
    monitoring_script = generate_monitoring_script(config)
    
    script_path = "./monitor-cost-alerts.sh"
    with open(script_path, 'w') as f:
        f.write(monitoring_script)
    os.chmod(script_path, 0o755)
    print_status("success", f"Monitoring script saved to {script_path}")
    
    # Generate setup instructions
    print_status("step", "Generating setup instructions...")
    instructions = generate_setup_instructions(config)
    
    with open("COST_ALERTS_SETUP.md", 'w') as f:
        f.write(instructions)
    print_status("success", "Setup instructions saved to COST_ALERTS_SETUP.md")
    
    # Summary
    print(f"\n{GREEN}✓ Cost alerts configuration complete!{NC}")
    print("\nNext steps:")
    print("1. Review the generated configuration files")
    print("2. Choose setup method: Manual, Terraform, or gcloud")
    print("3. Configure alert channels (Slack, PagerDuty)")
    print("4. Set up the monitoring dashboard")
    print("5. Schedule regular monitoring checks")
    
    print(f"\n{YELLOW}Important:{NC}")
    print("- Manual configuration is required for billing export")
    print("- Terraform requires appropriate IAM permissions")
    print("- Test alerts after configuration")


if __name__ == "__main__":
    main()