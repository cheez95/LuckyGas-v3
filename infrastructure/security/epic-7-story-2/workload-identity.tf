# Workload Identity Configuration for Cloud Run Services
# This enables Cloud Run services to authenticate as Google Service Accounts without keys

# Enable Workload Identity Pool
resource "google_iam_workload_identity_pool" "lucky_gas_pool" {
  provider                  = google-beta
  workload_identity_pool_id = "lucky-gas-pool"
  display_name              = "Lucky Gas Workload Identity Pool"
  description               = "Workload identity pool for Lucky Gas Cloud Run services"
  disabled                  = false
}

# Backend Service Account with Workload Identity
resource "google_service_account" "backend_workload_identity" {
  account_id   = "luckygas-backend-wi"
  display_name = "Lucky Gas Backend (Workload Identity)"
  description  = "Service account for backend with workload identity binding"
}

# Frontend Service Account with Workload Identity
resource "google_service_account" "frontend_workload_identity" {
  account_id   = "luckygas-frontend-wi"
  display_name = "Lucky Gas Frontend (Workload Identity)"
  description  = "Service account for frontend with workload identity binding"
}

# Worker Service Account with Workload Identity
resource "google_service_account" "worker_workload_identity" {
  account_id   = "luckygas-worker-wi"
  display_name = "Lucky Gas Worker (Workload Identity)"
  description  = "Service account for background workers with workload identity binding"
}

# Allow Cloud Run to use the backend service account
resource "google_service_account_iam_member" "backend_workload_identity_user" {
  service_account_id = google_service_account.backend_workload_identity.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/luckygas-backend]"
}

# Allow Cloud Run to use the frontend service account
resource "google_service_account_iam_member" "frontend_workload_identity_user" {
  service_account_id = google_service_account.frontend_workload_identity.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/luckygas-frontend]"
}

# Allow Cloud Run to use the worker service account
resource "google_service_account_iam_member" "worker_workload_identity_user" {
  service_account_id = google_service_account.worker_workload_identity.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/luckygas-worker]"
}

# Backend IAM roles (least privilege)
resource "google_project_iam_member" "backend_wi_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/storage.objectUser",
    "roles/aiplatform.user",
    "roles/redis.editor",
    "roles/datastore.user",
    "roles/pubsub.publisher"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.backend_workload_identity.email}"
}

# Frontend IAM roles (least privilege)
resource "google_project_iam_member" "frontend_wi_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.frontend_workload_identity.email}"
}

# Worker IAM roles (least privilege)
resource "google_project_iam_member" "worker_wi_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/storage.objectAdmin",
    "roles/aiplatform.user",
    "roles/redis.editor",
    "roles/datastore.user",
    "roles/pubsub.subscriber",
    "roles/cloudscheduler.jobRunner",
    "roles/cloudtasks.enqueuer"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.worker_workload_identity.email}"
}

# Cloud Run Service configurations with Workload Identity
resource "google_cloud_run_service" "backend_with_wi" {
  name     = "luckygas-backend"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.backend_workload_identity.email
      
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/luckygas/backend:latest"
        
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        
        # Remove GOOGLE_APPLICATION_CREDENTIALS - not needed with Workload Identity
        
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service" "frontend_with_wi" {
  name     = "luckygas-frontend"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.frontend_workload_identity.email
      
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/luckygas/frontend:latest"
        
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

# Outputs
output "backend_service_account" {
  value       = google_service_account.backend_workload_identity.email
  description = "Backend service account email for Workload Identity"
}

output "frontend_service_account" {
  value       = google_service_account.frontend_workload_identity.email
  description = "Frontend service account email for Workload Identity"
}

output "worker_service_account" {
  value       = google_service_account.worker_workload_identity.email
  description = "Worker service account email for Workload Identity"
}