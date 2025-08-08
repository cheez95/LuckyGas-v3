# Cloud Security Command Center Configuration for Lucky Gas
# Provides centralized security monitoring and threat detection

# Enable Security Command Center API
resource "google_project_service" "scc_api" {
  project = var.project_id
  service = "securitycenter.googleapis.com"
  
  disable_on_destroy = false
}

# Enable Container Analysis API for vulnerability scanning
resource "google_project_service" "container_analysis_api" {
  project = var.project_id
  service = "containeranalysis.googleapis.com"
  
  disable_on_destroy = false
}

# Enable Binary Authorization for container security
resource "google_project_service" "binary_authorization_api" {
  project = var.project_id
  service = "binaryauthorization.googleapis.com"
  
  disable_on_destroy = false
}

# Security Command Center Service Account
resource "google_service_account" "scc_service_account" {
  account_id   = "lucky-gas-scc"
  display_name = "Lucky Gas Security Command Center"
  description  = "Service account for Security Command Center operations"
  project      = var.project_id
}

# Grant necessary permissions to SCC service account
resource "google_project_iam_member" "scc_permissions" {
  for_each = toset([
    "roles/securitycenter.admin",
    "roles/cloudkms.cryptoKeyDecrypter",
    "roles/logging.viewer",
    "roles/monitoring.viewer",
    "roles/compute.viewer",
    "roles/iam.securityReviewer",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.scc_service_account.email}"
}

# Security Command Center Notification Config
resource "google_scc_notification_config" "high_severity_findings" {
  config_id    = "lucky-gas-high-severity"
  organization = var.organization_id
  description  = "Notify on high severity security findings"
  
  pubsub_topic = google_pubsub_topic.security_alerts.id
  
  streaming_config {
    filter = "severity=\"HIGH\" OR severity=\"CRITICAL\""
  }
  
  depends_on = [google_project_service.scc_api]
}

# Pub/Sub Topic for Security Alerts
resource "google_pubsub_topic" "security_alerts" {
  name    = "lucky-gas-security-alerts"
  project = var.project_id
  
  labels = {
    environment = "production"
    purpose     = "security-monitoring"
  }
}

# Pub/Sub Subscription for Alert Processing
resource "google_pubsub_subscription" "security_alerts_sub" {
  name    = "lucky-gas-security-alerts-sub"
  topic   = google_pubsub_topic.security_alerts.name
  project = var.project_id
  
  ack_deadline_seconds = 60
  
  push_config {
    push_endpoint = google_cloud_run_service.security_processor.status[0].url
    
    oidc_token {
      service_account_email = google_service_account.scc_service_account.email
    }
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Cloud Function for Security Alert Processing
resource "google_cloud_run_service" "security_processor" {
  name     = "lucky-gas-security-processor"
  location = var.region
  project  = var.project_id
  
  template {
    spec {
      service_account_name = google_service_account.scc_service_account.email
      
      containers {
        image = "gcr.io/${var.project_id}/security-processor:latest"
        
        env {
          name  = "SLACK_WEBHOOK_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.slack_webhook.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Secret for Slack Webhook
resource "google_secret_manager_secret" "slack_webhook" {
  secret_id = "slack-security-webhook"
  project   = var.project_id
  
  replication {
    automatic = true
  }
}

# Binary Authorization Policy
resource "google_binary_authorization_policy" "policy" {
  project = var.project_id
  
  global_policy_evaluation_mode = "ENABLE"
  
  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"
    
    require_attestations_by = [
      google_binary_authorization_attestor.prod_attestor.name,
    ]
  }
  
  # Allow Google-provided images
  admission_whitelist_patterns {
    name_pattern = "gcr.io/google_containers/*"
  }
  
  admission_whitelist_patterns {
    name_pattern = "gcr.io/google-containers/*"
  }
  
  admission_whitelist_patterns {
    name_pattern = "k8s.gcr.io/*"
  }
}

# Binary Authorization Attestor
resource "google_binary_authorization_attestor" "prod_attestor" {
  name    = "lucky-gas-prod-attestor"
  project = var.project_id
  
  attestation_authority_note {
    note_reference = google_container_analysis_note.attestation_note.name
    
    public_keys {
      id = "prod-key"
      pkix_public_key {
        public_key_pem     = file("${path.module}/keys/attestor-public.pem")
        signature_algorithm = "RSA_PSS_4096_SHA512"
      }
    }
  }
}

# Container Analysis Note for Binary Authorization
resource "google_container_analysis_note" "attestation_note" {
  name    = "lucky-gas-attestation-note"
  project = var.project_id
  
  attestation_authority {
    hint {
      human_readable_name = "Lucky Gas Production Attestor"
    }
  }
}

# Security Health Analytics Custom Module
resource "google_scc_source" "custom_detections" {
  display_name = "Lucky Gas Custom Security Detections"
  organization = var.organization_id
  description  = "Custom security detection rules for Lucky Gas"
  
  depends_on = [google_project_service.scc_api]
}

# Cloud Security Scanner (Web Security Scanner)
resource "google_security_scanner_scan_config" "web_scan" {
  display_name = "Lucky Gas Web Security Scan"
  project      = var.project_id
  
  starting_urls = [
    google_cloud_run_service.frontend.status[0].url,
  ]
  
  authentication {
    google_account {
      username = "scanner@${var.project_id}.iam.gserviceaccount.com"
      password = "dummy" # Uses service account auth
    }
  }
  
  schedule {
    schedule_time = "2024-01-23T03:00:00Z"
    interval_duration_days = 7
  }
  
  export_to_security_command_center = true
}

# Custom Monitoring Dashboard for Security
resource "google_monitoring_dashboard" "security_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Lucky Gas Security Dashboard"
    
    gridLayout = {
      widgets = [
        {
          title = "Security Findings by Severity"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"securitycenter.googleapis.com/finding/count\""
                  aggregation = {
                    groupByFields = ["metric.label.severity"]
                  }
                }
              }
            }]
          }
        },
        {
          title = "Failed Authentication Attempts"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class=\"4xx\""
                }
              }
            }]
          }
        },
        {
          title = "Suspicious API Activity"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"consumed_api\" AND metric.type=\"serviceruntime.googleapis.com/api/request_count\""
                  aggregation = {
                    groupByFields = ["resource.label.service"]
                  }
                }
              }
            }]
          }
        }
      ]
    }
  })
  
  project = var.project_id
}

# Alert Policies for Security Events
resource "google_monitoring_alert_policy" "high_severity_findings" {
  display_name = "High Severity Security Findings"
  project      = var.project_id
  
  conditions {
    display_name = "High/Critical severity findings detected"
    
    condition_threshold {
      filter          = "metric.type=\"securitycenter.googleapis.com/finding/count\" AND metric.label.severity=\"HIGH\" OR metric.label.severity=\"CRITICAL\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.security_team.name,
  ]
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Notification Channel for Security Team
resource "google_monitoring_notification_channel" "security_team" {
  display_name = "Lucky Gas Security Team"
  type         = "email"
  project      = var.project_id
  
  labels = {
    email_address = "security@luckygas.com.tw"
  }
}

# Outputs
output "security_topic_id" {
  value       = google_pubsub_topic.security_alerts.id
  description = "Security alerts Pub/Sub topic"
}

output "security_processor_url" {
  value       = google_cloud_run_service.security_processor.status[0].url
  description = "Security processor Cloud Run URL"
}

output "attestor_name" {
  value       = google_binary_authorization_attestor.prod_attestor.name
  description = "Binary Authorization attestor name"
}

output "security_dashboard_url" {
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.security_dashboard.id}?project=${var.project_id}"
  description = "Security monitoring dashboard URL"
}