#!/bin/bash
# Setup BigQuery Billing Export for Lucky Gas GCP Project
# This script configures billing data export to BigQuery for detailed cost analysis

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
PROJECT_ID="vast-tributary-466619-m8"
BILLING_ACCOUNT="011479-B04C2D-B0F925"
REGION="asia-east1"
DATASET_NAME="billing_export"
DATASET_LOCATION="asia-east1"  # BigQuery dataset location
EXPORT_TABLE="gcp_billing_export"

# Dry run mode
DRY_RUN=${DRY_RUN:-false}

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $status in
        "success")
            echo -e "[$timestamp] ${GREEN}✓${NC} $message"
            ;;
        "error")
            echo -e "[$timestamp] ${RED}✗${NC} $message"
            ;;
        "warning")
            echo -e "[$timestamp] ${YELLOW}⚠${NC} $message"
            ;;
        "info")
            echo -e "[$timestamp] ${BLUE}ℹ${NC} $message"
            ;;
        "step")
            echo -e "[$timestamp] ${MAGENTA}▶${NC} $message"
            ;;
    esac
}

# Function to execute command with dry run support
execute_command() {
    local cmd=$1
    local description=${2:-"Executing command"}
    
    print_status "info" "$description"
    
    if [ "$DRY_RUN" = "true" ]; then
        print_status "info" "[DRY RUN] Would execute: $cmd"
        return 0
    else
        if eval "$cmd"; then
            print_status "success" "Command completed successfully"
            return 0
        else
            print_status "error" "Command failed: $cmd"
            return 1
        fi
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "step" "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_status "error" "gcloud CLI not found. Please install Google Cloud SDK"
        return 1
    fi
    
    # Check if bq is installed
    if ! command -v bq &> /dev/null; then
        print_status "error" "bq command not found. Please install BigQuery CLI"
        return 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_status "error" "No active gcloud authentication found"
        return 1
    fi
    
    # Set project
    execute_command "gcloud config set project $PROJECT_ID" "Setting current project"
    
    print_status "success" "Prerequisites check passed"
    return 0
}

# Function to enable required APIs
enable_apis() {
    print_status "step" "Enabling required APIs..."
    
    local apis=(
        "bigquery.googleapis.com"
        "bigquerydatatransfer.googleapis.com"
        "cloudresourcemanager.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_status "success" "API already enabled: $api"
        else
            execute_command "gcloud services enable $api" "Enabling $api"
        fi
    done
}

# Function to create BigQuery dataset
create_bigquery_dataset() {
    print_status "step" "Creating BigQuery dataset for billing data..."
    
    # Check if dataset exists
    if bq ls -d --project_id="$PROJECT_ID" | grep -q "^$DATASET_NAME$"; then
        print_status "warning" "Dataset $DATASET_NAME already exists"
    else
        # Create dataset with location
        execute_command "bq mk --dataset \
            --location=$DATASET_LOCATION \
            --description='GCP billing export data for cost analysis' \
            $PROJECT_ID:$DATASET_NAME" \
            "Creating BigQuery dataset"
    fi
    
    # Set dataset permissions (optional - add specific users/groups)
    print_status "info" "Dataset created with default permissions"
}

# Function to setup billing export
setup_billing_export() {
    print_status "step" "Configuring billing export to BigQuery..."
    
    # Note: This requires billing admin permissions and must be done via Console or API
    print_status "warning" "Billing export configuration requires manual setup in Cloud Console"
    
    cat << EOF

${YELLOW}Manual Steps Required:${NC}

1. Go to the Cloud Console Billing page:
   ${BLUE}https://console.cloud.google.com/billing/${BILLING_ACCOUNT:18}/export${NC}

2. Click on "BIGQUERY EXPORT" tab

3. Configure the following:
   - ${GREEN}Dataset:${NC} $PROJECT_ID.$DATASET_NAME
   - ${GREEN}Table name prefix:${NC} gcp_billing_export_
   - ${GREEN}Export type:${NC} Select both:
     ✓ Standard usage cost data
     ✓ Detailed usage cost data (recommended)

4. Click "Save"

5. Note: Export will start from the next day. Historical data is not exported.

EOF
    
    print_status "info" "Press Enter after completing manual setup..."
    if [ "$DRY_RUN" != "true" ]; then
        read -r
    fi
}

# Function to create cost analysis views
create_analysis_views() {
    print_status "step" "Creating cost analysis views..."
    
    # Create daily cost summary view
    local daily_cost_view=$(cat << 'EOF'
CREATE OR REPLACE VIEW `PROJECT_ID.DATASET_NAME.daily_cost_summary` AS
SELECT
  DATE(usage_start_time) as usage_date,
  service.description as service_name,
  sku.description as sku_description,
  project.id as project_id,
  location.location as location,
  SUM(cost) as total_cost,
  currency
FROM
  `PROJECT_ID.DATASET_NAME.gcp_billing_export_*`
WHERE
  _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY
  usage_date, service_name, sku_description, project_id, location, currency
ORDER BY
  usage_date DESC, total_cost DESC;
EOF
)
    
    # Create monthly cost by service view
    local monthly_service_view=$(cat << 'EOF'
CREATE OR REPLACE VIEW `PROJECT_ID.DATASET_NAME.monthly_cost_by_service` AS
SELECT
  DATE_TRUNC(DATE(usage_start_time), MONTH) as month,
  service.description as service_name,
  SUM(cost) as total_cost,
  currency
FROM
  `PROJECT_ID.DATASET_NAME.gcp_billing_export_*`
WHERE
  _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY
  month, service_name, currency
ORDER BY
  month DESC, total_cost DESC;
EOF
)
    
    # Create cost forecast view
    local forecast_view=$(cat << 'EOF'
CREATE OR REPLACE VIEW `PROJECT_ID.DATASET_NAME.cost_forecast` AS
WITH daily_costs AS (
  SELECT
    DATE(usage_start_time) as usage_date,
    SUM(cost) as daily_cost
  FROM
    `PROJECT_ID.DATASET_NAME.gcp_billing_export_*`
  WHERE
    _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY
    usage_date
),
avg_daily_cost AS (
  SELECT
    AVG(daily_cost) as avg_cost_per_day
  FROM
    daily_costs
  WHERE
    usage_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
)
SELECT
  CURRENT_DATE() as forecast_date,
  avg_cost_per_day,
  avg_cost_per_day * 30 as projected_monthly_cost,
  avg_cost_per_day * 365 as projected_annual_cost
FROM
  avg_daily_cost;
EOF
)
    
    # Replace placeholders
    daily_cost_view=${daily_cost_view//PROJECT_ID/$PROJECT_ID}
    daily_cost_view=${daily_cost_view//DATASET_NAME/$DATASET_NAME}
    
    monthly_service_view=${monthly_service_view//PROJECT_ID/$PROJECT_ID}
    monthly_service_view=${monthly_service_view//DATASET_NAME/$DATASET_NAME}
    
    forecast_view=${forecast_view//PROJECT_ID/$PROJECT_ID}
    forecast_view=${forecast_view//DATASET_NAME/$DATASET_NAME}
    
    # Create views
    execute_command "bq query --use_legacy_sql=false '$daily_cost_view'" \
        "Creating daily cost summary view"
    
    execute_command "bq query --use_legacy_sql=false '$monthly_service_view'" \
        "Creating monthly cost by service view"
    
    execute_command "bq query --use_legacy_sql=false '$forecast_view'" \
        "Creating cost forecast view"
}

# Function to create sample queries
create_sample_queries() {
    print_status "step" "Creating sample cost analysis queries..."
    
    local queries_dir="./cost_analysis_queries"
    mkdir -p "$queries_dir"
    
    # Query 1: Current month costs
    cat > "$queries_dir/current_month_costs.sql" << EOF
-- Current month total costs by service
SELECT
  service.description as service_name,
  SUM(cost) as total_cost,
  currency
FROM
  \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY
  service_name, currency
ORDER BY
  total_cost DESC;
EOF
    
    # Query 2: Top 10 most expensive SKUs
    cat > "$queries_dir/top_expensive_skus.sql" << EOF
-- Top 10 most expensive SKUs this month
SELECT
  sku.description as sku_description,
  service.description as service_name,
  SUM(cost) as total_cost,
  SUM(usage.amount) as total_usage,
  usage.unit as usage_unit
FROM
  \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY
  sku_description, service_name, usage_unit
ORDER BY
  total_cost DESC
LIMIT 10;
EOF
    
    # Query 3: Daily cost trend
    cat > "$queries_dir/daily_cost_trend.sql" << EOF
-- Daily cost trend for the last 30 days
SELECT
  DATE(usage_start_time) as usage_date,
  SUM(cost) as daily_cost,
  currency
FROM
  \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY
  usage_date, currency
ORDER BY
  usage_date;
EOF
    
    # Query 4: Cost by location
    cat > "$queries_dir/cost_by_location.sql" << EOF
-- Cost breakdown by location
SELECT
  location.location as region,
  service.description as service_name,
  SUM(cost) as total_cost,
  currency
FROM
  \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY
  region, service_name, currency
ORDER BY
  total_cost DESC;
EOF
    
    print_status "success" "Sample queries created in $queries_dir/"
}

# Function to setup cost alerts
setup_cost_alerts() {
    print_status "step" "Setting up cost monitoring and alerts..."
    
    cat << EOF

${YELLOW}Recommended Cost Alert Configuration:${NC}

1. Set up budget alerts in Cloud Console:
   ${BLUE}https://console.cloud.google.com/billing/${BILLING_ACCOUNT:18}/budgets${NC}

2. Create budgets for:
   - ${GREEN}Monthly total:${NC} \$500 (50%), \$750 (75%), \$1000 (100%)
   - ${GREEN}Daily spike:${NC} Alert if daily cost > 2x average
   - ${GREEN}Service-specific:${NC} Alert if any service > \$200/month

3. Configure alert channels:
   - Email notifications
   - Cloud Monitoring integration
   - Slack/PagerDuty webhook (optional)

4. Set up Cloud Monitoring dashboard:
   ${BLUE}https://console.cloud.google.com/monitoring/dashboards${NC}

EOF
}

# Function to create monitoring script
create_monitoring_script() {
    print_status "step" "Creating cost monitoring script..."
    
    cat > "./check-costs.sh" << 'EOF'
#!/bin/bash
# Quick cost check script using BigQuery

PROJECT_ID="vast-tributary-466619-m8"
DATASET_NAME="billing_export"

echo "=== GCP Cost Analysis ==="
echo "Date: $(date)"
echo

# Current month costs
echo "Current Month Costs:"
bq query --use_legacy_sql=false --format=pretty << SQL
SELECT
  ROUND(SUM(cost), 2) as total_cost,
  currency
FROM
  \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY currency;
SQL

echo -e "\nTop 5 Services This Month:"
bq query --use_legacy_sql=false --format=pretty << SQL
SELECT
  service.description as service,
  ROUND(SUM(cost), 2) as cost
FROM
  \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY service
ORDER BY cost DESC
LIMIT 5;
SQL

echo -e "\nProjected Monthly Cost:"
bq query --use_legacy_sql=false --format=pretty << SQL
WITH recent_daily AS (
  SELECT AVG(daily_cost) as avg_daily
  FROM (
    SELECT DATE(usage_start_time) as date, SUM(cost) as daily_cost
    FROM \`$PROJECT_ID.$DATASET_NAME.gcp_billing_export_*\`
    WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY date
  )
)
SELECT
  ROUND(avg_daily * EXTRACT(DAY FROM DATE_SUB(DATE_ADD(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH), INTERVAL 1 DAY)), 2) as projected_monthly_cost
FROM recent_daily;
SQL
EOF
    
    chmod +x ./check-costs.sh
    print_status "success" "Cost monitoring script created: ./check-costs.sh"
}

# Function to generate summary
generate_summary() {
    local summary_file="./billing-export-setup-summary.md"
    
    cat > "$summary_file" << EOF
# BigQuery Billing Export Setup Summary

**Generated**: $(date)
**Project ID**: $PROJECT_ID
**Dataset**: $DATASET_NAME
**Location**: $DATASET_LOCATION

## Setup Status

✅ Prerequisites checked
✅ Required APIs enabled
✅ BigQuery dataset created
⚠️  Billing export requires manual configuration
✅ Cost analysis views created
✅ Sample queries generated
✅ Monitoring script created

## Manual Configuration Required

1. **Enable Billing Export**:
   - Go to: https://console.cloud.google.com/billing/${BILLING_ACCOUNT:18}/export
   - Configure export to: $PROJECT_ID.$DATASET_NAME
   - Select both Standard and Detailed usage cost data

2. **Set Up Budget Alerts**:
   - Go to: https://console.cloud.google.com/billing/${BILLING_ACCOUNT:18}/budgets
   - Create monthly and daily budgets
   - Configure email notifications

## Available Views

- \`$PROJECT_ID.$DATASET_NAME.daily_cost_summary\`
- \`$PROJECT_ID.$DATASET_NAME.monthly_cost_by_service\`
- \`$PROJECT_ID.$DATASET_NAME.cost_forecast\`

## Sample Queries Location

\`\`\`
./cost_analysis_queries/
├── current_month_costs.sql
├── daily_cost_trend.sql
├── cost_by_location.sql
└── top_expensive_skus.sql
\`\`\`

## Quick Cost Check

Run: \`./check-costs.sh\`

## Important Notes

- Billing data export starts from the next day after configuration
- Historical data is not automatically exported
- Data is typically available within 24 hours
- Costs are in USD by default

## Next Steps

1. Complete manual billing export configuration
2. Wait 24 hours for first data export
3. Run \`./check-costs.sh\` to verify data
4. Set up automated cost monitoring
5. Create custom dashboards in Data Studio

EOF
    
    print_status "success" "Summary generated: $summary_file"
}

# Main execution
main() {
    echo -e "${BLUE}=== Lucky Gas BigQuery Billing Export Setup ===${NC}\n"
    
    if [ "$DRY_RUN" = "true" ]; then
        print_status "warning" "Running in DRY RUN mode - no changes will be made"
    fi
    
    # Run setup steps
    check_prerequisites || exit 1
    echo
    
    enable_apis
    echo
    
    create_bigquery_dataset
    echo
    
    setup_billing_export
    echo
    
    create_analysis_views
    echo
    
    create_sample_queries
    echo
    
    setup_cost_alerts
    echo
    
    create_monitoring_script
    echo
    
    generate_summary
    echo
    
    print_status "success" "BigQuery billing export setup completed!"
    print_status "warning" "Remember to complete manual configuration steps"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--help]"
            echo "  --dry-run  Run without making actual changes"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            print_status "error" "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"