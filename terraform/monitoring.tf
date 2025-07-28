# Monitoring and Alerting Configuration

# Notification channels
resource "google_monitoring_notification_channel" "email" {
  display_name = "${var.project_name} Email Alerts ${var.environment}"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
  
  enabled = true
}

resource "google_monitoring_notification_channel" "slack" {
  count        = var.slack_webhook_url != "" ? 1 : 0
  display_name = "${var.project_name} Slack Alerts ${var.environment}"
  type         = "slack"
  
  labels = {
    url = var.slack_webhook_url
  }
  
  enabled = true
}

# Uptime checks
resource "google_monitoring_uptime_check_config" "https" {
  display_name = "${var.project_name} HTTPS Check ${var.environment}"
  timeout      = "10s"
  period       = "60s"
  
  http_check {
    path         = "/api/v1/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }
  
  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.environment == "production" ? "luckygas.com.tw" : "staging.luckygas.com.tw"
    }
  }
  
  content_matchers {
    content = "healthy"
    matcher = "CONTAINS_STRING"
  }
}

# Alert policies
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "${var.project_name} High Error Rate ${var.environment}"
  combiner     = "OR"
  
  conditions {
    display_name = "Error rate above 5%"
    
    condition_threshold {
      filter = <<-EOT
        resource.type = "k8s_container"
        AND resource.labels.namespace_name = "${var.kubernetes_namespace}"
        AND metric.type = "logging.googleapis.com/user/http_request_error_rate"
      EOT
      
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.id,
  ]
  
  alert_strategy {
    auto_close = "86400s"
  }
  
  documentation {
    content = "Error rate is above 5% for ${var.project_name} in ${var.environment}. Check application logs for details."
  }
}

resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "${var.project_name} High Latency ${var.environment}"
  combiner     = "OR"
  
  conditions {
    display_name = "95th percentile latency above 1s"
    
    condition_threshold {
      filter = <<-EOT
        resource.type = "k8s_container"
        AND resource.labels.namespace_name = "${var.kubernetes_namespace}"
        AND metric.type = "kubernetes.io/container/request_latency"
      EOT
      
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1000  # milliseconds
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.pod_name"]
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.id,
  ]
  
  alert_strategy {
    auto_close = "86400s"
  }
}

resource "google_monitoring_alert_policy" "database_connection_pool" {
  display_name = "${var.project_name} Database Connection Pool ${var.environment}"
  combiner     = "OR"
  
  conditions {
    display_name = "Connection pool usage above 80%"
    
    condition_threshold {
      filter = <<-EOT
        resource.type = "cloudsql_database"
        AND resource.labels.database_id = "${var.project_id}:${google_sql_database_instance.postgres.name}"
        AND metric.type = "cloudsql.googleapis.com/database/postgresql/num_backends"
      EOT
      
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 160  # 80% of 200 max connections
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "86400s"
  }
}

resource "google_monitoring_alert_policy" "pod_restart" {
  display_name = "${var.project_name} Pod Restarts ${var.environment}"
  combiner     = "OR"
  
  conditions {
    display_name = "Pod restarting frequently"
    
    condition_threshold {
      filter = <<-EOT
        resource.type = "k8s_pod"
        AND resource.labels.namespace_name = "${var.kubernetes_namespace}"
        AND metric.type = "kubernetes.io/pod/restart_count"
      EOT
      
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "86400s"
  }
  
  documentation {
    content = "Pod ${var.project_name} is restarting frequently in ${var.environment}. This may indicate application crashes or resource constraints."
  }
}

# Create a dashboard
resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "${var.project_name} Dashboard ${var.environment}"
    gridLayout = {
      widgets = [
        {
          title = "Request Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"k8s_container\" resource.labels.namespace_name=\"${var.kubernetes_namespace}\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Error Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"k8s_container\" resource.labels.namespace_name=\"${var.kubernetes_namespace}\" metric.type=\"logging.googleapis.com/user/http_request_error_rate\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Database Connections"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloudsql_database\" resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.postgres.name}\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MAX"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Pod Memory Usage"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"k8s_container\" resource.labels.namespace_name=\"${var.kubernetes_namespace}\" metric.type=\"kubernetes.io/container/memory/used_bytes\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        }
      ]
    }
  })
}