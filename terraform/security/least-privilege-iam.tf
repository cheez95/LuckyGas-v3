# Least Privilege IAM Configuration for Lucky Gas
# Implements minimal required permissions for all service accounts and users

# Custom IAM Roles with Minimal Permissions

# Backend Service Custom Role
resource "google_project_iam_custom_role" "backend_minimal" {
  role_id     = "luckyGasBackendMinimal"
  title       = "Lucky Gas Backend Minimal Permissions"
  description = "Minimal permissions required for backend service operation"
  project     = var.project_id
  
  permissions = [
    # Cloud SQL - Read/Write only, no admin
    "cloudsql.instances.connect",
    "cloudsql.instances.get",
    
    # Storage - Object operations only
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    
    # Secret Manager - Read only
    "secretmanager.versions.access",
    
    # Vertex AI - Prediction only
    "aiplatform.endpoints.predict",
    
    # Routes API - Calculate routes only
    "routes.routes.compute",
    
    # Monitoring & Logging
    "monitoring.timeSeries.create",
    "logging.logEntries.create",
    
    # Service Account Token Creation (for Workload Identity)
    "iam.serviceAccounts.getAccessToken",
  ]
}

# Frontend Service Custom Role (Very Limited)
resource "google_project_iam_custom_role" "frontend_minimal" {
  role_id     = "luckyGasFrontendMinimal"
  title       = "Lucky Gas Frontend Minimal Permissions"
  description = "Minimal permissions for frontend service"
  project     = var.project_id
  
  permissions = [
    # Only logging and monitoring
    "logging.logEntries.create",
    "monitoring.timeSeries.create",
  ]
}

# Worker Service Custom Role
resource "google_project_iam_custom_role" "worker_minimal" {
  role_id     = "luckyGasWorkerMinimal"
  title       = "Lucky Gas Worker Minimal Permissions"
  description = "Minimal permissions for batch processing workers"
  project     = var.project_id
  
  permissions = [
    # Cloud SQL - Read/Write
    "cloudsql.instances.connect",
    "cloudsql.instances.get",
    
    # Storage - Full object operations for batch processing
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
    
    # BigQuery - Write for analytics
    "bigquery.tables.updateData",
    "bigquery.tables.get",
    
    # Vertex AI - Training and prediction
    "aiplatform.endpoints.predict",
    "aiplatform.models.upload",
    "aiplatform.trainingJobs.create",
    
    # Monitoring & Logging
    "monitoring.timeSeries.create",
    "logging.logEntries.create",
  ]
}

# Apply Custom Roles to Service Accounts
resource "google_project_iam_member" "backend_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.backend_minimal.id
  member  = "serviceAccount:${google_service_account.backend_service.email}"
}

resource "google_project_iam_member" "frontend_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.frontend_minimal.id
  member  = "serviceAccount:${google_service_account.frontend_service.email}"
}

resource "google_project_iam_member" "worker_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.worker_minimal.id
  member  = "serviceAccount:${google_service_account.worker_service.email}"
}

# Developer Access with Time Limits
resource "google_project_iam_binding" "developer_time_limited" {
  project = var.project_id
  role    = "roles/editor"
  
  members = []  # Will be populated by Cloud Function based on access requests
  
  condition {
    title       = "Time-limited developer access"
    description = "Developer access expires after 8 hours"
    expression  = "request.time < timestamp(\"2024-01-23T17:00:00Z\")"
  }
}

# Break-Glass Emergency Access (Highly Restricted)
resource "google_project_iam_custom_role" "break_glass" {
  role_id     = "luckyGasBreakGlass"
  title       = "Lucky Gas Break-Glass Emergency Access"
  description = "Emergency access for critical incidents only"
  project     = var.project_id
  
  permissions = [
    # Full permissions needed for emergency response
    "resourcemanager.projects.get",
    "iam.roles.get",
    "iam.roles.list",
    "iam.serviceAccounts.getIamPolicy",
    "logging.logs.list",
    "logging.logEntries.list",
    "monitoring.alertPolicies.list",
    "compute.instances.list",
    "run.services.list",
  ]
}

# Organization Policies for Security
resource "google_organization_policy" "disable_service_account_creation" {
  org_id     = var.organization_id
  constraint = "iam.disableServiceAccountCreation"
  
  boolean_policy {
    enforced = true
  }
}

resource "google_organization_policy" "disable_service_account_key_creation" {
  org_id     = var.organization_id
  constraint = "iam.disableServiceAccountKeyCreation"
  
  list_policy {
    allow {
      values = [
        "projects/${var.project_id}/serviceAccounts/${google_service_account.key_rotation_sa.email}",
      ]
    }
  }
}

resource "google_organization_policy" "restrict_vm_external_ips" {
  org_id     = var.organization_id
  constraint = "compute.vmExternalIpAccess"
  
  list_policy {
    deny {
      all = true
    }
  }
}

# Audit Logging Configuration
resource "google_project_iam_audit_config" "all_services" {
  project = var.project_id
  service = "allServices"
  
  # Admin Activity logs are always enabled
  
  # Data Access logs for security-critical services
  audit_log_config {
    log_type = "DATA_READ"
    
    exempted_members = [
      # Exclude service accounts from read logging to reduce noise
      "serviceAccount:${google_service_account.backend_service.email}",
      "serviceAccount:${google_service_account.worker_service.email}",
    ]
  }
  
  audit_log_config {
    log_type = "DATA_WRITE"
    # No exemptions - log all writes
  }
  
  audit_log_config {
    log_type = "ADMIN_READ"
    # No exemptions - log all admin reads
  }
}

# Specific audit configs for sensitive services
resource "google_project_iam_audit_config" "secret_manager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
  
  audit_log_config {
    log_type = "DATA_READ"
    # No exemptions - log all secret reads
  }
  
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

resource "google_project_iam_audit_config" "iam" {
  project = var.project_id
  service = "iam.googleapis.com"
  
  audit_log_config {
    log_type = "DATA_READ"
  }
  
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

# Log Sink for IAM Changes
resource "google_logging_project_sink" "iam_changes" {
  name        = "lucky-gas-iam-changes"
  destination = "bigquery.googleapis.com/${google_bigquery_dataset.security_audit.id}"
  project     = var.project_id
  
  filter = "protoPayload.serviceName=\"iam.googleapis.com\" AND (protoPayload.methodName=\"SetIamPolicy\" OR protoPayload.methodName=\"google.iam.admin.v1.CreateRole\" OR protoPayload.methodName=\"google.iam.admin.v1.UpdateRole\")"
  
  unique_writer_identity = true
}

# BigQuery Dataset for Security Audit
resource "google_bigquery_dataset" "security_audit" {
  dataset_id                  = "lucky_gas_security_audit"
  friendly_name               = "Security Audit Logs"
  description                 = "IAM changes and security events"
  location                    = "asia-east1"
  default_table_expiration_ms = 31536000000 # 365 days
  project                     = var.project_id
  
  access {
    role          = "OWNER"
    user_by_email = google_service_account.scc_service_account.email
  }
  
  access {
    role          = "READER"
    user_by_email = "security@luckygas.com.tw"
  }
}

# Monitoring Dashboard for IAM Activity
resource "google_monitoring_dashboard" "iam_activity" {
  dashboard_json = jsonencode({
    displayName = "Lucky Gas IAM Activity"
    
    gridLayout = {
      widgets = [
        {
          title = "IAM Policy Changes"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "protoPayload.serviceName=\"iam.googleapis.com\" AND protoPayload.methodName=\"SetIamPolicy\""
                }
              }
            }]
          }
        },
        {
          title = "Service Account Key Operations"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "protoPayload.serviceName=\"iam.googleapis.com\" AND (protoPayload.methodName=\"CreateServiceAccountKey\" OR protoPayload.methodName=\"DeleteServiceAccountKey\")"
                }
              }
            }]
          }
        },
        {
          title = "Failed Permission Checks"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "protoPayload.status.code=7" # Permission denied
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

# Alert for Unauthorized Access Attempts
resource "google_monitoring_alert_policy" "unauthorized_access" {
  display_name = "Unauthorized Access Attempts"
  project      = var.project_id
  
  conditions {
    display_name = "Multiple permission denied errors"
    
    condition_threshold {
      filter          = "protoPayload.status.code=7"
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_COUNT"
        group_by_fields    = ["protoPayload.authenticationInfo.principalEmail"]
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.security_team.name,
  ]
  
  documentation {
    content = "Multiple unauthorized access attempts detected. This could indicate a security breach attempt."
  }
}

# Outputs
output "backend_custom_role" {
  value       = google_project_iam_custom_role.backend_minimal.id
  description = "Backend service custom IAM role"
}

output "frontend_custom_role" {
  value       = google_project_iam_custom_role.frontend_minimal.id
  description = "Frontend service custom IAM role"
}

output "worker_custom_role" {
  value       = google_project_iam_custom_role.worker_minimal.id
  description = "Worker service custom IAM role"
}

output "iam_activity_dashboard" {
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.iam_activity.id}?project=${var.project_id}"
  description = "IAM activity monitoring dashboard URL"
}