# Service Account Key Rotation Automation
# Automatically rotates service account keys every 30 days

# Cloud Scheduler for key rotation
resource "google_cloud_scheduler_job" "key_rotation" {
  name             = "service-account-key-rotation"
  description      = "Rotate service account keys every 30 days"
  schedule         = "0 0 1 * *" # First day of every month at midnight
  time_zone        = "Asia/Taipei"
  attempt_deadline = "600s"
  
  pubsub_target {
    topic_name = google_pubsub_topic.key_rotation.id
    data       = base64encode(jsonencode({
      action = "rotate_keys"
      service_accounts = [
        "lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com"
      ]
    }))
  }
}

# Pub/Sub topic for key rotation
resource "google_pubsub_topic" "key_rotation" {
  name = "service-account-key-rotation"
  
  message_retention_duration = "86400s" # 1 day
}

# Cloud Function for key rotation
resource "google_cloudfunctions_function" "key_rotation" {
  name        = "service-account-key-rotation"
  description = "Automated service account key rotation"
  runtime     = "python39"
  
  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.functions.name
  source_archive_object = google_storage_bucket_object.key_rotation_function.name
  entry_point           = "rotate_keys"
  timeout               = 540 # 9 minutes
  
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.key_rotation.name
  }
  
  environment_variables = {
    PROJECT_ID = var.project_id
    KEY_AGE_DAYS = "30"
    NOTIFICATION_TOPIC = google_pubsub_topic.key_rotation_notifications.name
  }
  
  service_account_email = google_service_account.key_rotation_sa.email
}

# Service account for key rotation function
resource "google_service_account" "key_rotation_sa" {
  account_id   = "key-rotation-automation"
  display_name = "Service Account Key Rotation Automation"
}

# IAM roles for key rotation service account
resource "google_project_iam_member" "key_rotation_roles" {
  for_each = toset([
    "roles/iam.serviceAccountKeyAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/secretmanager.admin",
    "roles/pubsub.publisher",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.key_rotation_sa.email}"
}

# Notification topic for key rotation events
resource "google_pubsub_topic" "key_rotation_notifications" {
  name = "key-rotation-notifications"
  
  message_retention_duration = "604800s" # 7 days
}

# Notification subscription
resource "google_pubsub_subscription" "key_rotation_notifications_sub" {
  name  = "key-rotation-notifications-sub"
  topic = google_pubsub_topic.key_rotation_notifications.name
  
  push_config {
    push_endpoint = "https://app.luckygas.tw/api/v1/security/key-rotation-webhook"
    
    oidc_token {
      service_account_email = google_service_account.backend_workload_identity.email
    }
  }
}

# Upload key rotation function
resource "google_storage_bucket_object" "key_rotation_function" {
  name   = "key-rotation-function.zip"
  bucket = google_storage_bucket.functions.name
  source = "${path.module}/functions/key-rotation.zip"
}

# Cloud Monitoring alert for key rotation failures
resource "google_monitoring_alert_policy" "key_rotation_failure" {
  display_name = "Service Account Key Rotation Failure"
  combiner     = "OR"
  
  conditions {
    display_name = "Key rotation function error rate"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_function\" AND resource.labels.function_name=\"service-account-key-rotation\" AND metric.type=\"cloudfunctions.googleapis.com/function/error_count\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.security_team.id]
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Monitoring dashboard for key age
resource "google_monitoring_dashboard" "key_rotation_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Service Account Key Rotation"
    gridLayout = {
      widgets = [
        {
          title = "Service Account Key Age"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/security/service_account_key_age\" resource.type=\"global\""
                }
              }
            }]
          }
        },
        {
          title = "Key Rotation Events"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/security/key_rotation_events\" resource.type=\"global\""
                }
              }
            }]
          }
        },
        {
          title = "Rotation Failures"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_function\" AND resource.labels.function_name=\"service-account-key-rotation\" AND metric.type=\"cloudfunctions.googleapis.com/function/error_count\""
                }
              }
            }]
          }
        }
      ]
    }
  })
}

# Notification channel for security team
resource "google_monitoring_notification_channel" "security_team" {
  display_name = "Security Team"
  type         = "email"
  
  labels = {
    email_address = "security@luckygas.tw"
  }
}

# Outputs
output "key_rotation_schedule" {
  value       = google_cloud_scheduler_job.key_rotation.schedule
  description = "Schedule for automatic key rotation"
}

output "key_rotation_topic" {
  value       = google_pubsub_topic.key_rotation.name
  description = "Pub/Sub topic for key rotation events"
}