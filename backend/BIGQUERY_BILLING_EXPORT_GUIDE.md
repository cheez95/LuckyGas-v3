# BigQuery Billing Export Implementation Guide

## Overview

This guide provides comprehensive instructions for implementing detailed cost analysis using BigQuery billing export for the Lucky Gas GCP project. This implementation enables granular cost tracking, optimization opportunities, and automated alerting.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GCP Billing    │────▶│   BigQuery       │────▶│ Cost Analysis   │
│  Export Service │     │   Dataset        │     │ Tools & Scripts │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │   Cost Views     │     │  Alert System   │
                        │   & Queries      │     │  & Monitoring   │
                        └──────────────────┘     └─────────────────┘
```

## Components Implemented

### 1. **Setup Script** (`setup-billing-export.sh`)
- Automated BigQuery dataset creation
- API enablement and permissions
- Cost analysis views generation
- Sample queries creation

**Key Features:**
- Dry-run mode for testing
- Idempotent operations
- Comprehensive error handling
- Progress tracking

### 2. **Cost Analysis Tool** (`cost-analysis-python.py`)
- Real-time cost analysis
- Anomaly detection
- Forecast generation
- JSON export capability

**Analysis Capabilities:**
- Current month spending
- Daily cost trends
- Service breakdown
- Location-based costs
- Cost anomalies detection

### 3. **Advanced Queries** (`cost_analysis_queries/`)
- Growth rate analysis
- Hourly usage patterns
- Unused resource detection
- Egress cost tracking
- AI/ML service costs

### 4. **Alert System** (`cost-alerts-config.yaml`)
- Budget configuration
- Multi-channel alerting
- Automated actions
- Optimization rules

### 5. **Monitoring Scripts**
- `check-costs.sh` - Quick cost summary
- `monitor-cost-alerts.sh` - Alert checking
- Automated anomaly detection

## Setup Instructions

### Step 1: Enable BigQuery Billing Export

1. **Run the setup script:**
   ```bash
   chmod +x setup-billing-export.sh
   ./setup-billing-export.sh
   ```

2. **Manual Configuration Required:**
   - Go to [Billing Export](https://console.cloud.google.com/billing/011479-B04C2D-B0F925/export)
   - Enable both Standard and Detailed usage cost export
   - Select dataset: `vast-tributary-466619-m8.billing_export`
   - Table prefix: `gcp_billing_export_`

### Step 2: Install Dependencies

```bash
# For Python analysis tools
cd backend
uv pip install google-cloud-bigquery pyyaml

# For Terraform (optional)
brew install terraform  # macOS
```

### Step 3: Configure Cost Alerts

1. **Using Python script:**
   ```bash
   python3 setup-cost-alerts.py
   ```

2. **Or manually via Console:**
   - Navigate to Billing Budgets
   - Create budgets as defined in `cost-alerts-config.yaml`

### Step 4: Set Up Monitoring

1. **Schedule daily checks:**
   ```bash
   # Add to crontab
   0 9 * * * /path/to/backend/check-costs.sh
   ```

2. **Configure alert channels:**
   - Email: Already included in budgets
   - Slack: Add webhook URL to config
   - PagerDuty: Add integration key

## Usage Guide

### Running Cost Analysis

1. **Quick cost check:**
   ```bash
   ./check-costs.sh
   ```

2. **Detailed Python analysis:**
   ```bash
   python3 cost-analysis-python.py
   
   # Export to JSON
   python3 cost-analysis-python.py --export
   ```

3. **Run specific queries:**
   ```bash
   bq query --use_legacy_sql=false < cost_analysis_queries/current_month_costs.sql
   ```

### Understanding the Output

**Cost Analysis Output:**
- **Current Month Costs**: Total spending with budget percentage
- **Daily Costs**: Recent daily spending with trend indicators
- **Top Services**: Services consuming most budget
- **Cost by Location**: Regional cost distribution
- **Forecast**: Projected monthly spending
- **Anomalies**: Unusual spending patterns

**Status Indicators:**
- ✓ Green: Within budget/normal
- ⚠ Yellow: Warning threshold
- ✗ Red: Critical/over budget

### Cost Optimization Workflow

1. **Weekly Review:**
   ```bash
   # Run unused resources check
   bq query --use_legacy_sql=false < cost_analysis_queries/advanced_cost_analysis.sql
   ```

2. **Identify Opportunities:**
   - Unused resources with costs
   - Off-hours usage patterns
   - Regional optimization
   - Commitment discounts

3. **Implement Changes:**
   - Remove unused resources
   - Set up scheduling for non-critical workloads
   - Move to optimal regions
   - Purchase committed use contracts

## BigQuery Views Created

### 1. `daily_cost_summary`
Provides daily breakdown of costs by service and SKU.

### 2. `monthly_cost_by_service`
Monthly aggregation of costs by service.

### 3. `cost_forecast`
Projects monthly costs based on recent usage.

## Alert Configuration

### Budget Thresholds:
- 50% - Email notification
- 75% - Email + Slack
- 90% - Email + Slack + PagerDuty
- 100% - All channels + critical alert

### Service-Specific Budgets:
- Vertex AI: $300/month
- Cloud Storage: $100/month
- Routes API: $200/month

## Troubleshooting

### Common Issues:

1. **No billing data available:**
   - Wait 24 hours after enabling export
   - Verify export is configured correctly
   - Check BigQuery permissions

2. **Query errors:**
   - Ensure dataset exists: `billing_export`
   - Check table prefix matches: `gcp_billing_export_`
   - Verify date partitioning

3. **Alert not firing:**
   - Check notification channel configuration
   - Verify budget thresholds
   - Review IAM permissions

### Debug Commands:

```bash
# Check if dataset exists
bq ls -d --project_id=vast-tributary-466619-m8

# List billing tables
bq ls vast-tributary-466619-m8:billing_export

# Test query
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`vast-tributary-466619-m8.billing_export.gcp_billing_export_*\`"
```

## Best Practices

1. **Regular Monitoring:**
   - Check costs daily during initial setup
   - Weekly reviews once stable
   - Monthly optimization sessions

2. **Alert Tuning:**
   - Start with conservative thresholds
   - Adjust based on usage patterns
   - Don't ignore repeated alerts

3. **Cost Attribution:**
   - Use labels for resource grouping
   - Implement project hierarchy
   - Track by environment (dev/staging/prod)

4. **Optimization Priority:**
   - Focus on top 5 services first
   - Address anomalies immediately
   - Implement gradual changes

## Security Considerations

1. **Access Control:**
   - Limit BigQuery dataset access
   - Use service accounts for automation
   - Audit query access regularly

2. **Data Retention:**
   - Set appropriate retention policies
   - Archive old data to reduce costs
   - Comply with data regulations

3. **Alert Security:**
   - Secure webhook URLs
   - Rotate API keys regularly
   - Monitor for unauthorized access

## Next Steps

1. **Complete manual billing export setup**
2. **Wait 24 hours for first data**
3. **Run initial cost analysis**
4. **Configure alert channels**
5. **Set up automated monitoring**
6. **Create custom dashboards**
7. **Implement optimization recommendations**

## Support Resources

- [BigQuery Billing Export Docs](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)
- [Cloud Billing API](https://cloud.google.com/billing/docs/reference/rest)
- [Cost Optimization Best Practices](https://cloud.google.com/architecture/framework/cost-optimization)

---

**Note**: This implementation provides comprehensive cost visibility and control for the Lucky Gas project. Regular monitoring and optimization can reduce costs by 20-30% on average.