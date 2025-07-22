-- Advanced Cost Analysis Queries for Lucky Gas GCP Project
-- These queries provide deeper insights into billing data

-- 1. Cost Growth Rate Analysis
-- Shows month-over-month growth rate
WITH monthly_costs AS (
  SELECT
    DATE_TRUNC(DATE(usage_start_time), MONTH) as month,
    SUM(cost) as total_cost
  FROM
    `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
  WHERE
    _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  GROUP BY month
),
cost_growth AS (
  SELECT
    month,
    total_cost,
    LAG(total_cost) OVER (ORDER BY month) as prev_month_cost,
    ROUND((total_cost - LAG(total_cost) OVER (ORDER BY month)) / LAG(total_cost) OVER (ORDER BY month) * 100, 2) as growth_rate
  FROM monthly_costs
)
SELECT * FROM cost_growth
WHERE prev_month_cost IS NOT NULL
ORDER BY month DESC;

-- 2. Hourly Usage Pattern Analysis
-- Identifies peak usage hours to optimize costs
SELECT
  EXTRACT(HOUR FROM usage_start_time) as hour_of_day,
  service.description as service_name,
  COUNT(*) as usage_count,
  SUM(cost) as total_cost,
  AVG(cost) as avg_cost_per_usage
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
WHERE
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY hour_of_day, service_name
ORDER BY hour_of_day, total_cost DESC;

-- 3. Unused Resources Detection
-- Finds resources with costs but minimal or no usage
SELECT
  service.description as service_name,
  sku.description as sku_description,
  SUM(cost) as total_cost,
  SUM(usage.amount) as total_usage,
  usage.unit as usage_unit,
  COUNT(*) as billing_records
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
WHERE
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND cost > 0
  AND (usage.amount = 0 OR usage.amount IS NULL)
GROUP BY service_name, sku_description, usage_unit
HAVING total_cost > 1
ORDER BY total_cost DESC;

-- 4. Project-wise Cost Distribution
-- Shows cost distribution across different projects (if multiple)
SELECT
  project.id as project_id,
  project.name as project_name,
  service.description as service_name,
  SUM(cost) as total_cost,
  ROUND(SUM(cost) / (SELECT SUM(cost) FROM `vast-tributary-466619-m8.billing_export.gcp_billing_export_*` 
    WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)) * 100, 2) as percentage_of_total
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY project_id, project_name, service_name
ORDER BY total_cost DESC;

-- 5. Commitment Utilization Analysis
-- Checks if committed use discounts are being utilized
SELECT
  service.description as service_name,
  sku.description as sku_description,
  pricing.pricing_category as pricing_category,
  SUM(CASE WHEN pricing.pricing_category = 'OnDemand' THEN cost ELSE 0 END) as on_demand_cost,
  SUM(CASE WHEN pricing.pricing_category = 'Commitment' THEN cost ELSE 0 END) as commitment_cost,
  SUM(cost) as total_cost
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`,
  UNNEST(pricing) as pricing
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY service_name, sku_description, pricing_category
HAVING total_cost > 10
ORDER BY total_cost DESC;

-- 6. Top Cost Drivers by Label
-- Analyzes costs by resource labels for better allocation
SELECT
  labels.key as label_key,
  labels.value as label_value,
  service.description as service_name,
  SUM(cost) as total_cost
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`,
  UNNEST(labels) as labels
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY label_key, label_value, service_name
HAVING total_cost > 5
ORDER BY total_cost DESC;

-- 7. Weekend vs Weekday Cost Comparison
-- Identifies if costs can be reduced during off-hours
SELECT
  CASE 
    WHEN EXTRACT(DAYOFWEEK FROM usage_start_time) IN (1, 7) THEN 'Weekend'
    ELSE 'Weekday'
  END as day_type,
  service.description as service_name,
  COUNT(DISTINCT DATE(usage_start_time)) as days_count,
  SUM(cost) as total_cost,
  AVG(cost) as avg_daily_cost
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
WHERE
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY day_type, service_name
ORDER BY service_name, day_type;

-- 8. Egress Cost Analysis
-- Tracks network egress costs which can be significant
SELECT
  location.location as source_location,
  sku.description as sku_description,
  SUM(cost) as total_cost,
  SUM(usage.amount) as total_gb,
  CASE 
    WHEN SUM(usage.amount) > 0 THEN SUM(cost) / SUM(usage.amount)
    ELSE 0
  END as cost_per_gb
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
WHERE
  DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND _PARTITIONDATE >= DATE_TRUNC(CURRENT_DATE(), MONTH)
  AND (
    LOWER(sku.description) LIKE '%egress%'
    OR LOWER(sku.description) LIKE '%network%'
    OR LOWER(sku.description) LIKE '%bandwidth%'
  )
  AND cost > 0
GROUP BY source_location, sku_description
ORDER BY total_cost DESC;

-- 9. AI/ML Service Cost Breakdown
-- Specific analysis for Vertex AI and related services
SELECT
  service.description as service_name,
  sku.description as sku_description,
  DATE(usage_start_time) as usage_date,
  SUM(cost) as daily_cost,
  SUM(usage.amount) as usage_amount,
  usage.unit as usage_unit
FROM
  `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
WHERE
  DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (
    service.description LIKE '%AI Platform%'
    OR service.description LIKE '%Vertex AI%'
    OR service.description LIKE '%Machine Learning%'
  )
GROUP BY service_name, sku_description, usage_date, usage_unit
ORDER BY usage_date DESC, daily_cost DESC;

-- 10. Cost Optimization Opportunities
-- Identifies potential cost savings
WITH resource_costs AS (
  SELECT
    service.description as service_name,
    sku.description as sku_description,
    location.location as location,
    SUM(cost) as total_cost,
    COUNT(DISTINCT DATE(usage_start_time)) as active_days,
    SUM(cost) / COUNT(DISTINCT DATE(usage_start_time)) as avg_daily_cost
  FROM
    `vast-tributary-466619-m8.billing_export.gcp_billing_export_*`
  WHERE
    DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    AND _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY service_name, sku_description, location
)
SELECT
  service_name,
  sku_description,
  location,
  total_cost,
  active_days,
  avg_daily_cost,
  CASE
    WHEN active_days < 15 AND total_cost > 10 THEN 'Consider on-demand or removal'
    WHEN avg_daily_cost < 1 AND total_cost > 30 THEN 'Consider consolidation'
    WHEN location != 'asia-east1' AND total_cost > 50 THEN 'Consider region optimization'
    ELSE 'OK'
  END as optimization_suggestion
FROM resource_costs
WHERE total_cost > 5
ORDER BY total_cost DESC
LIMIT 50;