# Cost Optimization and Monitoring for Lucky Gas
# Implements intelligent caching, usage dashboards, and automatic cost alerts

variable "monthly_budget_ntd" {
  description = "Monthly budget in New Taiwan Dollars"
  default     = 3000
}

variable "exchange_rate_usd_to_ntd" {
  description = "Exchange rate from USD to NTD"
  default     = 31.5  # Approximate rate, update as needed
}

locals {
  monthly_budget_usd = var.monthly_budget_ntd / var.exchange_rate_usd_to_ntd
  
  # Alert thresholds as percentage of monthly budget
  alert_thresholds = {
    "50_percent"  = local.monthly_budget_usd * 0.5
    "80_percent"  = local.monthly_budget_usd * 0.8
    "100_percent" = local.monthly_budget_usd
  }
}

# Enable required APIs
resource "google_project_service" "billing_api" {
  project = var.project_id
  service = "cloudbilling.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "budget_api" {
  project = var.project_id
  service = "billingbudgets.googleapis.com"
  disable_on_destroy = false
}

# Budget configuration
resource "google_billing_budget" "monthly_budget" {
  billing_account = data.google_billing_account.account.id
  display_name    = "Lucky Gas Monthly Budget"
  
  budget_filter {
    projects = ["projects/${var.project_id}"]
    
    # Only track actual costs (not credits)
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
    
    # Track specific services to control costs
    services = [
      "services/9812-67FB-5337",  # Routes API
      "services/84E0-FE5D-5F87",  # Vertex AI
      "services/24E6-581D-38E5",  # Cloud Run
      "services/95FF-2EF5-5EA1",  # Cloud Storage
      "services/50D3-8F5B-7B94",  # Cloud SQL
    ]
  }
  
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(floor(local.monthly_budget_usd))
      nanos         = tonumber((local.monthly_budget_usd - floor(local.monthly_budget_usd)) * 1000000000)
    }
  }
  
  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }
  
  threshold_rules {
    threshold_percent = 0.8
    spend_basis       = "CURRENT_SPEND"
  }
  
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }
  
  threshold_rules {
    threshold_percent = 1.2
    spend_basis       = "CURRENT_SPEND"
  }
  
  all_updates_rule {
    pubsub_topic = google_pubsub_topic.budget_alerts.id
    schema_version = "1.0"
  }
}

# Get billing account
data "google_billing_account" "account" {
  billing_account = "billingAccounts/01A34B-5C6D7E-8F9G0H"  # Replace with actual billing account
}

# Pub/Sub topic for budget alerts
resource "google_pubsub_topic" "budget_alerts" {
  name    = "lucky-gas-budget-alerts"
  project = var.project_id
}

# Cloud Function for budget alert processing
resource "google_cloud_run_service" "budget_processor" {
  name     = "lucky-gas-budget-processor"
  location = var.region
  project  = var.project_id
  
  template {
    spec {
      service_account_name = google_service_account.cost_monitor_sa.email
      
      containers {
        image = "gcr.io/${var.project_id}/budget-processor:latest"
        
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "MONTHLY_BUDGET_NTD"
          value = var.monthly_budget_ntd
        }
        
        env {
          name  = "SLACK_WEBHOOK_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.cost_alerts_webhook.secret_id
              key  = "latest"
            }
          }
        }
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Service account for cost monitoring
resource "google_service_account" "cost_monitor_sa" {
  account_id   = "lucky-gas-cost-monitor"
  display_name = "Lucky Gas Cost Monitor"
  description  = "Service account for cost monitoring and optimization"
  project      = var.project_id
}

# Permissions for cost monitor
resource "google_project_iam_member" "cost_monitor_permissions" {
  for_each = toset([
    "roles/billing.viewer",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cost_monitor_sa.email}"
}

# Secret for Slack webhook
resource "google_secret_manager_secret" "cost_alerts_webhook" {
  secret_id = "cost-alerts-webhook"
  project   = var.project_id
  
  replication {
    automatic = true
  }
}

# BigQuery dataset for billing export
resource "google_bigquery_dataset" "billing_export" {
  dataset_id                  = "billing_export"
  friendly_name               = "Billing Export Data"
  description                 = "GCP billing data export for cost analysis"
  location                    = "asia-east1"
  default_table_expiration_ms = 7776000000  # 90 days
  project                     = var.project_id
}

# Scheduled queries for cost analysis
resource "google_bigquery_data_transfer_config" "daily_cost_analysis" {
  display_name           = "Daily Cost Analysis"
  location              = "asia-east1"
  data_source_id        = "scheduled_query"
  schedule              = "every day 09:00"
  destination_dataset_id = google_bigquery_dataset.billing_export.dataset_id
  project               = var.project_id
  
  params = {
    query = templatefile("${path.module}/queries/daily_cost_analysis.sql", {
      project_id = var.project_id
      dataset_id = google_bigquery_dataset.billing_export.dataset_id
    })
    
    destination_table_name_template = "daily_costs_{run_date}"
    write_disposition = "WRITE_TRUNCATE"
  }
}

# Cost monitoring dashboard
resource "google_monitoring_dashboard" "cost_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Lucky Gas Cost Monitoring"
    
    gridLayout = {
      widgets = [
        {
          title = "Monthly Spend vs Budget (NT$)"
          scorecard = {
            timeSeriesQuery = {
              timeSeriesFilter = {
                filter = "metric.type=\"billing.googleapis.com/project/costs\""
                aggregation = {
                  alignmentPeriod = "2592000s"  # 30 days
                  perSeriesAligner = "ALIGN_SUM"
                }
              }
            }
            sparkChartView = {
              sparkChartType = "SPARK_LINE"
            }
            thresholds = [
              {
                value = local.alert_thresholds["50_percent"]
                color = "YELLOW"
              },
              {
                value = local.alert_thresholds["80_percent"]
                color = "RED"
              }
            ]
          }
        },
        {
          title = "Daily Spend Trend"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"billing.googleapis.com/project/costs\""
                  aggregation = {
                    alignmentPeriod = "86400s"  # 1 day
                    perSeriesAligner = "ALIGN_SUM"
                  }
                }
              }
            }]
            yAxis = {
              label = "Cost (USD)"
              scale = "LINEAR"
            }
          }
        },
        {
          title = "Cost by Service"
          pieChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"billing.googleapis.com/project/costs\""
                  aggregation = {
                    alignmentPeriod = "2592000s"  # 30 days
                    perSeriesAligner = "ALIGN_SUM"
                    groupByFields = ["resource.label.service"]
                  }
                }
              }
            }]
          }
        },
        {
          title = "Routes API Usage"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"serviceruntime.googleapis.com/api/request_count\" AND resource.label.service=\"routes.googleapis.com\""
                  aggregation = {
                    alignmentPeriod = "3600s"  # 1 hour
                    perSeriesAligner = "ALIGN_SUM"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Vertex AI Predictions"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"aiplatform.googleapis.com/prediction/online/request_count\""
                  aggregation = {
                    alignmentPeriod = "3600s"  # 1 hour
                    perSeriesAligner = "ALIGN_SUM"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Cache Hit Rate"
          scorecard = {
            timeSeriesQuery = {
              timeSeriesFilter = {
                filter = "metric.type=\"custom.googleapis.com/luckygas/cache_hit_rate\""
                aggregation = {
                  alignmentPeriod = "3600s"  # 1 hour
                  perSeriesAligner = "ALIGN_MEAN"
                }
              }
            }
            sparkChartView = {
              sparkChartType = "SPARK_LINE"
            }
            thresholds = [
              {
                value = 0.8
                color = "GREEN"
              },
              {
                value = 0.5
                color = "YELLOW"
              }
            ]
          }
        }
      ]
    }
  })
  
  project = var.project_id
}

# Alert policies for cost optimization
resource "google_monitoring_alert_policy" "daily_cost_exceeded" {
  display_name = "Daily Cost Exceeded NT$${floor(local.monthly_budget_usd * 31.5 / 30)}"
  project      = var.project_id
  
  conditions {
    display_name = "Daily cost threshold exceeded"
    
    condition_threshold {
      filter          = "metric.type=\"billing.googleapis.com/project/costs\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = local.monthly_budget_usd / 30  # Daily budget
      
      aggregations {
        alignment_period   = "86400s"  # 1 day
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.cost_alerts.name,
  ]
  
  documentation {
    content = "Daily cost has exceeded NT$${floor(local.monthly_budget_usd * 31.5 / 30)}. Review usage and consider optimization."
  }
}

resource "google_monitoring_alert_policy" "api_quota_approaching" {
  display_name = "API Quota Approaching Limit"
  project      = var.project_id
  
  conditions {
    display_name = "API quota usage > 80%"
    
    condition_threshold {
      filter          = "metric.type=\"serviceruntime.googleapis.com/quota/exceeded\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.cost_alerts.name,
  ]
  
  documentation {
    content = "API quota usage is approaching limits. Enable caching or reduce request rate."
  }
}

# Notification channel for cost alerts
resource "google_monitoring_notification_channel" "cost_alerts" {
  display_name = "Lucky Gas Cost Alerts"
  type         = "email"
  project      = var.project_id
  
  labels = {
    email_address = "finance@luckygas.com.tw"
  }
}

# Redis instance for caching (saves API costs)
resource "google_redis_instance" "cache" {
  name           = "lucky-gas-cache"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  project        = var.project_id
  
  redis_version = "REDIS_7_0"
  display_name  = "Lucky Gas API Response Cache"
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }
  
  lifecycle {
    prevent_destroy = true
  }
}

# Cloud Scheduler for cost optimization tasks
resource "google_cloud_scheduler_job" "cache_cleanup" {
  name        = "lucky-gas-cache-cleanup"
  description = "Clean up expired cache entries"
  schedule    = "0 2 * * *"  # Daily at 2 AM
  project     = var.project_id
  region      = var.region
  
  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.backend.status[0].url}/api/v1/internal/cache/cleanup"
    
    oidc_token {
      service_account_email = google_service_account.backend_service.email
    }
  }
}

resource "google_cloud_scheduler_job" "cost_report" {
  name        = "lucky-gas-daily-cost-report"
  description = "Generate daily cost report"
  schedule    = "0 9 * * *"  # Daily at 9 AM
  project     = var.project_id
  region      = var.region
  
  http_target {
    http_method = "POST"
    uri         = google_cloud_run_service.budget_processor.status[0].url
    
    body = base64encode(jsonencode({
      action = "generate_report"
      type   = "daily"
    }))
    
    headers = {
      "Content-Type" = "application/json"
    }
    
    oidc_token {
      service_account_email = google_service_account.cost_monitor_sa.email
    }
  }
}

# Outputs
output "monthly_budget_ntd" {
  value       = var.monthly_budget_ntd
  description = "Monthly budget in New Taiwan Dollars"
}

output "monthly_budget_usd" {
  value       = local.monthly_budget_usd
  description = "Monthly budget in US Dollars"
}

output "cost_dashboard_url" {
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.cost_dashboard.id}?project=${var.project_id}"
  description = "Cost monitoring dashboard URL"
}

output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis cache host for API response caching"
}

output "budget_id" {
  value       = google_billing_budget.monthly_budget.id
  description = "Budget ID for cost tracking"
}