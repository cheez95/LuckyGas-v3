# IAM Configuration

# Application Service Account
resource "google_service_account" "app_identity" {
  account_id   = "${var.project_name}-app-${var.environment}"
  display_name = "Application Service Account for ${var.environment}"
  description  = "Service account for the LuckyGas application in ${var.environment}"
}

# Grant necessary permissions to app service account
resource "google_project_iam_member" "app_permissions" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudtrace.agent",
    "roles/clouddebugger.agent",
    "roles/cloudprofiler.agent",
    "roles/errorreporting.writer",
    "roles/aiplatform.user",
    "roles/redis.editor",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app_identity.email}"
}

# Workload Identity binding
resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = google_service_account.app_identity.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.kubernetes_namespace}/luckygas-backend]"
}

# Cloud Build Service Account (for CI/CD)
resource "google_service_account" "cloud_build" {
  account_id   = "${var.project_name}-cloudbuild-${var.environment}"
  display_name = "Cloud Build Service Account for ${var.environment}"
  description  = "Service account for Cloud Build CI/CD in ${var.environment}"
}

# Grant Cloud Build permissions
resource "google_project_iam_member" "cloud_build_permissions" {
  for_each = toset([
    "roles/container.developer",
    "roles/artifactregistry.writer",
    "roles/storage.admin",
    "roles/cloudbuild.builds.builder",
    "roles/run.admin",
    "roles/iam.serviceAccountUser",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

# Monitoring Service Account
resource "google_service_account" "monitoring" {
  account_id   = "${var.project_name}-monitoring-${var.environment}"
  display_name = "Monitoring Service Account for ${var.environment}"
  description  = "Service account for monitoring and alerting in ${var.environment}"
}

# Grant monitoring permissions
resource "google_project_iam_member" "monitoring_permissions" {
  for_each = toset([
    "roles/monitoring.viewer",
    "roles/logging.viewer",
    "roles/cloudtrace.user",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.monitoring.email}"
}

# Create custom role for least privilege
resource "google_project_iam_custom_role" "app_custom_role" {
  role_id     = "luckygas_app_${var.environment}"
  title       = "LuckyGas App Custom Role ${var.environment}"
  description = "Custom role with minimal permissions for LuckyGas app"
  
  permissions = [
    # Cloud SQL
    "cloudsql.instances.connect",
    "cloudsql.instances.get",
    
    # Storage
    "storage.buckets.get",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
    
    # Secret Manager
    "secretmanager.versions.access",
    "secretmanager.versions.list",
    
    # Vertex AI
    "aiplatform.endpoints.predict",
    "aiplatform.models.get",
    
    # Redis
    "redis.instances.get",
    "redis.instances.getAuthString",
  ]
}

# Assign custom role
resource "google_project_iam_member" "app_custom_role_binding" {
  project = var.project_id
  role    = google_project_iam_custom_role.app_custom_role.id
  member  = "serviceAccount:${google_service_account.app_identity.email}"
}