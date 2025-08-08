# Automated Service Account Key Rotation for Lucky Gas
# Rotates keys every 30 days and stores them securely in Secret Manager

# Cloud Scheduler for Key Rotation
resource "google_cloud_scheduler_job" "key_rotation" {
  name        = "lucky-gas-key-rotation"
  description = "Rotate service account keys every 30 days"
  schedule    = "0 2 1 * *" # Run at 2 AM on the 1st of every month
  project     = var.project_id
  region      = var.region
  
  http_target {
    http_method = "POST"
    uri         = google_cloud_run_service.key_rotator.status[0].url
    
    oidc_token {
      service_account_email = google_service_account.key_rotation_sa.email
    }
  }
  
  retry_config {
    retry_count = 3
    min_backoff_duration = "5s"
    max_backoff_duration = "60s"
    max_doublings = 2
  }
}

# Service Account for Key Rotation
resource "google_service_account" "key_rotation_sa" {
  account_id   = "lucky-gas-key-rotation"
  display_name = "Lucky Gas Key Rotation Service"
  description  = "Automated service account key rotation"
  project      = var.project_id
}

# Permissions for Key Rotation Service Account
resource "google_project_iam_member" "key_rotation_permissions" {
  for_each = toset([
    "roles/iam.serviceAccountKeyAdmin",  # Manage service account keys
    "roles/secretmanager.admin",         # Store keys in Secret Manager
    "roles/logging.logWriter",           # Write logs
    "roles/monitoring.metricWriter",     # Write metrics
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.key_rotation_sa.email}"
}

# Cloud Run Service for Key Rotation Logic
resource "google_cloud_run_service" "key_rotator" {
  name     = "lucky-gas-key-rotator"
  location = var.region
  project  = var.project_id
  
  template {
    spec {
      service_account_name = google_service_account.key_rotation_sa.email
      timeout_seconds      = 300 # 5 minutes timeout
      
      containers {
        image = "gcr.io/${var.project_id}/key-rotator:latest"
        
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "ROTATION_DAYS"
          value = "30"
        }
        
        env {
          name  = "SERVICE_ACCOUNTS"
          value = jsonencode([
            google_service_account.backend_service.email,
            google_service_account.worker_service.email,
            # Don't rotate frontend service account (uses Workload Identity only)
          ])
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
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

# Secret Manager Secrets for Rotated Keys
resource "google_secret_manager_secret" "service_account_keys" {
  for_each = toset([
    "backend-service-key",
    "worker-service-key",
  ])
  
  secret_id = "lucky-gas-${each.value}"
  project   = var.project_id
  
  replication {
    automatic = true
  }
  
  rotation {
    next_rotation_time = "2024-02-01T02:00:00Z"
    rotation_period    = "2592000s" # 30 days
  }
}

# IAM binding to allow services to access their keys
resource "google_secret_manager_secret_iam_member" "backend_key_access" {
  secret_id = google_secret_manager_secret.service_account_keys["backend-service-key"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_service.email}"
  project   = var.project_id
}

resource "google_secret_manager_secret_iam_member" "worker_key_access" {
  secret_id = google_secret_manager_secret.service_account_keys["worker-service-key"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker_service.email}"
  project   = var.project_id
}

# Monitoring Alert for Key Rotation Failures
resource "google_monitoring_alert_policy" "key_rotation_failure" {
  display_name = "Service Account Key Rotation Failure"
  project      = var.project_id
  
  conditions {
    display_name = "Key rotation job failed"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_scheduler_job\" AND metric.type=\"cloudscheduler.googleapis.com/job/attempt_count\" AND resource.label.job_id=\"key_rotation\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_COUNT"
      }
      
      trigger {
        count = 1
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.security_team.name,
  ]
  
  documentation {
    content = "Service account key rotation has failed. Manual intervention may be required. Check Cloud Run logs for details."
  }
}

# Key Age Monitoring
resource "google_monitoring_alert_policy" "old_keys" {
  display_name = "Service Account Keys Older Than 45 Days"
  project      = var.project_id
  
  conditions {
    display_name = "Old service account keys detected"
    
    condition_threshold {
      filter          = "metric.type=\"iam.googleapis.com/service_account/key/age\" AND metric.label.key_age_days > 45"
      duration        = "3600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 45
      
      aggregations {
        alignment_period   = "3600s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.security_team.name,
  ]
  
  documentation {
    content = "Service account keys older than 45 days detected. This indicates key rotation may have failed or been disabled."
  }
}

# Pub/Sub Topic for Key Rotation Events
resource "google_pubsub_topic" "key_rotation_events" {
  name    = "lucky-gas-key-rotation-events"
  project = var.project_id
  
  labels = {
    purpose = "audit-trail"
  }
}

# Log Sink for Key Rotation Audit Trail
resource "google_logging_project_sink" "key_rotation_audit" {
  name        = "lucky-gas-key-rotation-audit"
  destination = "pubsub.googleapis.com/${google_pubsub_topic.key_rotation_events.id}"
  project     = var.project_id
  
  filter = "resource.type=\"service_account\" AND (protoPayload.methodName=\"google.iam.admin.v1.CreateServiceAccountKey\" OR protoPayload.methodName=\"google.iam.admin.v1.DeleteServiceAccountKey\")"
  
  unique_writer_identity = true
}

# Grant publishing permissions to the log sink
resource "google_pubsub_topic_iam_member" "log_sink_publisher" {
  topic  = google_pubsub_topic.key_rotation_events.name
  role   = "roles/pubsub.publisher"
  member = google_logging_project_sink.key_rotation_audit.writer_identity
}

# BigQuery Dataset for Key Rotation History
resource "google_bigquery_dataset" "key_rotation_history" {
  dataset_id                  = "lucky_gas_key_rotation"
  friendly_name               = "Service Account Key Rotation History"
  description                 = "Historical data for service account key rotations"
  location                    = "asia-east1"
  default_table_expiration_ms = 7776000000 # 90 days
  project                     = var.project_id
  
  labels = {
    purpose = "security-audit"
  }
}

# BigQuery Table for Key Rotation Events
resource "google_bigquery_table" "rotation_events" {
  dataset_id = google_bigquery_dataset.key_rotation_history.dataset_id
  table_id   = "rotation_events"
  project    = var.project_id
  
  schema = jsonencode([
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "service_account"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "action"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "key_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "status"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "details"
      type = "JSON"
      mode = "NULLABLE"
    }
  ])
}

# Outputs
output "key_rotation_schedule" {
  value       = google_cloud_scheduler_job.key_rotation.schedule
  description = "Key rotation schedule"
}

output "key_rotator_url" {
  value       = google_cloud_run_service.key_rotator.status[0].url
  description = "Key rotator service URL"
}

output "rotation_events_topic" {
  value       = google_pubsub_topic.key_rotation_events.id
  description = "Key rotation events topic"
}