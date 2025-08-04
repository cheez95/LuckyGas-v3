# Least Privilege IAM Configuration
# Implements fine-grained permissions for all service accounts and users

# Custom IAM roles with minimal permissions
resource "google_project_iam_custom_role" "backend_api_role" {
  role_id     = "luckyGasBackendAPI"
  title       = "Lucky Gas Backend API Role"
  description = "Minimal permissions for backend API service"
  
  permissions = [
    # Cloud SQL
    "cloudsql.instances.connect",
    "cloudsql.instances.get",
    
    # Secret Manager (read-only)
    "secretmanager.versions.access",
    "secretmanager.versions.get",
    
    # Cloud Storage (specific buckets)
    "storage.buckets.get",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
    
    # Vertex AI (predictions only)
    "aiplatform.endpoints.predict",
    "aiplatform.models.get",
    
    # Redis
    "redis.instances.get",
    "redis.instances.executeCommand",
    
    # Pub/Sub (publishing only)
    "pubsub.topics.publish",
    
    # Monitoring & Logging
    "logging.logEntries.create",
    "monitoring.metricDescriptors.create",
    "monitoring.metricDescriptors.list",
    "monitoring.timeSeries.create",
    "cloudtrace.traces.patch"
  ]
}

resource "google_project_iam_custom_role" "frontend_static_role" {
  role_id     = "luckyGasFrontendStatic"
  title       = "Lucky Gas Frontend Static Role"
  description = "Minimal permissions for frontend static serving"
  
  permissions = [
    # Logging only
    "logging.logEntries.create",
    "monitoring.metricDescriptors.create",
    "monitoring.timeSeries.create",
    "cloudtrace.traces.patch"
  ]
}

resource "google_project_iam_custom_role" "worker_batch_role" {
  role_id     = "luckyGasWorkerBatch"
  title       = "Lucky Gas Worker Batch Role"
  description = "Permissions for batch processing workers"
  
  permissions = [
    # Cloud SQL
    "cloudsql.instances.connect",
    "cloudsql.instances.get",
    
    # Secret Manager (read-only)
    "secretmanager.versions.access",
    
    # Cloud Storage (full access to specific buckets)
    "storage.buckets.get",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
    
    # Vertex AI (training and predictions)
    "aiplatform.batchPredictionJobs.create",
    "aiplatform.batchPredictionJobs.get",
    "aiplatform.endpoints.predict",
    "aiplatform.models.get",
    "aiplatform.models.upload",
    "aiplatform.trainingJobs.create",
    "aiplatform.trainingJobs.get",
    
    # Redis
    "redis.instances.get",
    "redis.instances.executeCommand",
    
    # Pub/Sub (both publish and subscribe)
    "pubsub.subscriptions.consume",
    "pubsub.subscriptions.get",
    "pubsub.topics.publish",
    
    # Cloud Tasks
    "cloudtasks.queues.get",
    "cloudtasks.tasks.create",
    "cloudtasks.tasks.delete",
    "cloudtasks.tasks.get",
    
    # Monitoring & Logging
    "logging.logEntries.create",
    "monitoring.metricDescriptors.create",
    "monitoring.timeSeries.create"
  ]
}

resource "google_project_iam_custom_role" "ci_cd_deploy_role" {
  role_id     = "luckyGasCICDDeploy"
  title       = "Lucky Gas CI/CD Deploy Role"
  description = "Permissions for CI/CD pipeline deployments"
  
  permissions = [
    # Cloud Run
    "run.services.create",
    "run.services.get",
    "run.services.update",
    "run.services.delete",
    "run.operations.get",
    
    # Artifact Registry
    "artifactregistry.dockerimages.get",
    "artifactregistry.dockerimages.list",
    "artifactregistry.repositories.uploadArtifacts",
    
    # Service Account impersonation (limited)
    "iam.serviceAccounts.actAs",
    
    # Cloud Build
    "cloudbuild.builds.create",
    "cloudbuild.builds.get"
  ]
}

# Assign custom roles to service accounts
resource "google_project_iam_member" "backend_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.backend_api_role.id
  member  = "serviceAccount:${google_service_account.backend_workload_identity.email}"
}

resource "google_project_iam_member" "frontend_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.frontend_static_role.id
  member  = "serviceAccount:${google_service_account.frontend_workload_identity.email}"
}

resource "google_project_iam_member" "worker_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.worker_batch_role.id
  member  = "serviceAccount:${google_service_account.worker_workload_identity.email}"
}

# Storage bucket IAM with least privilege
resource "google_storage_bucket_iam_member" "media_bucket_backend" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend_workload_identity.email}"
  
  condition {
    title       = "Only media files"
    description = "Restrict to media file operations"
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.media.name}/objects/media/\")"
  }
}

resource "google_storage_bucket_iam_member" "backup_bucket_worker" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.worker_workload_identity.email}"
  
  condition {
    title       = "Only backup files"
    description = "Restrict to backup operations"
    expression  = "resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.backups.name}/objects/backups/\")"
  }
}

# Secret Manager IAM with least privilege
resource "google_secret_manager_secret_iam_member" "db_password_backend" {
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_workload_identity.email}"
}

resource "google_secret_manager_secret_iam_member" "jwt_secret_backend" {
  secret_id = google_secret_manager_secret.jwt_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_workload_identity.email}"
}

# Cloud SQL IAM with database-specific permissions
resource "google_sql_database_instance_iam_member" "backend_sql_client" {
  instance = google_sql_database_instance.main.name
  role     = "roles/cloudsql.client"
  member   = "serviceAccount:${google_service_account.backend_workload_identity.email}"
}

resource "google_sql_database_instance_iam_member" "worker_sql_client" {
  instance = google_sql_database_instance.main.name
  role     = "roles/cloudsql.client"
  member   = "serviceAccount:${google_service_account.worker_workload_identity.email}"
}

# Organization policies for additional security
resource "google_project_organization_policy" "disable_service_account_key_creation" {
  project    = var.project_id
  constraint = "iam.disableServiceAccountKeyCreation"
  
  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "disable_service_account_key_upload" {
  project    = var.project_id
  constraint = "iam.disableServiceAccountKeyUpload"
  
  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "allowed_policy_member_domains" {
  project    = var.project_id
  constraint = "iam.allowedPolicyMemberDomains"
  
  list_policy {
    allow {
      values = [
        "luckygas.tw",
        var.project_id + ".iam.gserviceaccount.com"
      ]
    }
  }
}

# IAM conditions for time-based access
resource "google_project_iam_member" "developer_time_limited" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "group:developers@luckygas.tw"
  
  condition {
    title       = "Business hours only"
    description = "Access only during business hours (8 AM - 8 PM Taiwan time)"
    expression  = "request.time.getHours(\"Asia/Taipei\") >= 8 && request.time.getHours(\"Asia/Taipei\") <= 20"
  }
}

# Audit configuration for IAM changes
resource "google_project_iam_audit_config" "iam_audit" {
  project = var.project_id
  service = "iam.googleapis.com"
  
  audit_log_config {
    log_type = "ADMIN_READ"
  }
  
  audit_log_config {
    log_type = "DATA_READ"
  }
  
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}

# Monitoring alert for privilege escalation attempts
resource "google_monitoring_alert_policy" "privilege_escalation" {
  display_name = "IAM Privilege Escalation Attempt"
  combiner     = "OR"
  
  conditions {
    display_name = "IAM role grant with admin permissions"
    
    condition_threshold {
      filter = "protoPayload.methodName=\"SetIamPolicy\" AND protoPayload.request.policy.bindings.role:(\"roles/owner\" OR \"roles/editor\" OR \"roles/iam.securityAdmin\")"
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.security_team.id]
  
  alert_strategy {
    notification_rate_limit {
      period = "300s"
    }
  }
}

# Outputs
output "backend_custom_role" {
  value       = google_project_iam_custom_role.backend_api_role.id
  description = "Custom IAM role for backend service"
}

output "frontend_custom_role" {
  value       = google_project_iam_custom_role.frontend_static_role.id
  description = "Custom IAM role for frontend service"
}

output "worker_custom_role" {
  value       = google_project_iam_custom_role.worker_batch_role.id
  description = "Custom IAM role for worker service"
}