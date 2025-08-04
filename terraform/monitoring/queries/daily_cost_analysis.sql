-- Daily Cost Analysis Query for Lucky Gas
-- Analyzes daily costs by service and provides optimization insights

WITH daily_costs AS (
  SELECT
    DATE(usage_start_time) AS usage_date,
    service.description AS service_name,
    sku.description AS sku_description,
    location.location AS location,
    project.id AS project_id,
    SUM(cost) AS total_cost_usd,
    SUM(cost) * 31.5 AS total_cost_ntd,  -- Convert to NTD
    SUM(usage.amount) AS usage_amount,
    usage.unit AS usage_unit
  FROM
    `${project_id}.${dataset_id}.gcp_billing_export_v1_*`
  WHERE
    DATE(usage_start_time) = CURRENT_DATE() - 1  -- Yesterday's data
    AND project.id = '${project_id}'
  GROUP BY
    usage_date,
    service_name,
    sku_description,
    location,
    project_id,
    usage_unit
),

service_summary AS (
  SELECT
    usage_date,
    service_name,
    SUM(total_cost_usd) AS service_cost_usd,
    SUM(total_cost_ntd) AS service_cost_ntd,
    RANK() OVER (PARTITION BY usage_date ORDER BY SUM(total_cost_usd) DESC) AS cost_rank
  FROM
    daily_costs
  GROUP BY
    usage_date,
    service_name
),

api_usage AS (
  SELECT
    usage_date,
    CASE
      WHEN service_name LIKE '%Routes%' THEN 'Routes API'
      WHEN service_name LIKE '%Vertex%' THEN 'Vertex AI'
      WHEN service_name LIKE '%Cloud Run%' THEN 'Cloud Run'
      WHEN service_name LIKE '%Cloud SQL%' THEN 'Cloud SQL'
      WHEN service_name LIKE '%Storage%' THEN 'Cloud Storage'
      ELSE 'Other Services'
    END AS service_category,
    SUM(total_cost_usd) AS category_cost_usd,
    SUM(total_cost_ntd) AS category_cost_ntd
  FROM
    daily_costs
  GROUP BY
    usage_date,
    service_category
),

cost_trends AS (
  SELECT
    usage_date,
    service_name,
    service_cost_usd,
    service_cost_ntd,
    LAG(service_cost_usd, 1) OVER (PARTITION BY service_name ORDER BY usage_date) AS prev_day_cost,
    CASE
      WHEN LAG(service_cost_usd, 1) OVER (PARTITION BY service_name ORDER BY usage_date) > 0
      THEN (service_cost_usd - LAG(service_cost_usd, 1) OVER (PARTITION BY service_name ORDER BY usage_date)) / LAG(service_cost_usd, 1) OVER (PARTITION BY service_name ORDER BY usage_date) * 100
      ELSE 0
    END AS daily_change_percent
  FROM
    service_summary
),

monthly_projection AS (
  SELECT
    usage_date,
    SUM(service_cost_usd) AS daily_total_usd,
    SUM(service_cost_ntd) AS daily_total_ntd,
    SUM(service_cost_usd) * 30 AS projected_monthly_usd,
    SUM(service_cost_ntd) * 30 AS projected_monthly_ntd,
    3000.0 AS budget_ntd,  -- Monthly budget in NTD
    (SUM(service_cost_ntd) * 30) / 3000.0 * 100 AS budget_utilization_percent
  FROM
    service_summary
  GROUP BY
    usage_date
)

SELECT
  -- Date and totals
  mp.usage_date,
  mp.daily_total_usd,
  mp.daily_total_ntd,
  mp.projected_monthly_usd,
  mp.projected_monthly_ntd,
  mp.budget_ntd,
  mp.budget_utilization_percent,
  
  -- Top cost services
  ARRAY_AGG(
    STRUCT(
      ct.service_name,
      ct.service_cost_usd,
      ct.service_cost_ntd,
      ct.daily_change_percent
    )
    ORDER BY ct.service_cost_usd DESC
    LIMIT 5
  ) AS top_cost_services,
  
  -- Service category breakdown
  ARRAY_AGG(
    STRUCT(
      au.service_category,
      au.category_cost_usd,
      au.category_cost_ntd
    )
    ORDER BY au.category_cost_usd DESC
  ) AS service_categories,
  
  -- Cost optimization recommendations
  CASE
    WHEN mp.budget_utilization_percent > 100 THEN 'CRITICAL: Monthly projection exceeds budget!'
    WHEN mp.budget_utilization_percent > 80 THEN 'WARNING: Approaching monthly budget limit'
    WHEN mp.budget_utilization_percent > 50 THEN 'INFO: Monitor usage closely'
    ELSE 'OK: Within budget parameters'
  END AS budget_status,
  
  -- Specific recommendations
  ARRAY_AGG(
    CASE
      WHEN ct.service_name LIKE '%Routes%' AND ct.service_cost_usd > 5 
        THEN 'Consider implementing route caching to reduce Routes API calls'
      WHEN ct.service_name LIKE '%Vertex%' AND ct.service_cost_usd > 3
        THEN 'Review AI prediction frequency and implement result caching'
      WHEN ct.service_name LIKE '%Cloud Run%' AND ct.service_cost_usd > 10
        THEN 'Optimize Cloud Run scaling settings and request handling'
      WHEN ct.daily_change_percent > 50
        THEN CONCAT('Investigate ', ct.service_name, ' - cost increased ', CAST(ct.daily_change_percent AS STRING), '%')
      ELSE NULL
    END
    IGNORE NULLS
  ) AS optimization_recommendations,
  
  -- Metadata
  CURRENT_TIMESTAMP() AS analysis_timestamp,
  '${project_id}' AS project_id

FROM
  monthly_projection mp
  LEFT JOIN cost_trends ct ON mp.usage_date = ct.usage_date
  LEFT JOIN api_usage au ON mp.usage_date = au.usage_date
GROUP BY
  mp.usage_date,
  mp.daily_total_usd,
  mp.daily_total_ntd,
  mp.projected_monthly_usd,
  mp.projected_monthly_ntd,
  mp.budget_ntd,
  mp.budget_utilization_percent