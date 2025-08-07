# Workload Identity Configuration for Lucky Gas Cloud Run Services
# This eliminates the need for service account keys by using Google-managed identities

variable "project_id" {
  description = "GCP Project ID"
  default     = "vast-tributary-466619-m8"
}

variable "region" {
  description = "GCP Region"
  default     = "asia-east1"
}

# Backend Service Account with Workload Identity
resource "google_service_account" "backend_service" {
  account_id   = "lucky-gas-backend"
  display_name = "Lucky Gas Backend Service"
  description  = "Service account for Cloud Run backend with Workload Identity"
  project      = var.project_id
}

# Frontend Service Account
resource "google_service_account" "frontend_service" {
  account_id   = "lucky-gas-frontend"
  display_name = "Lucky Gas Frontend Service"
  description  = "Service account for Cloud Run frontend"
  project      = var.project_id
}

# Worker Service Account (for batch jobs)
resource "google_service_account" "worker_service" {
  account_id   = "lucky-gas-worker"
  display_name = "Lucky Gas Worker Service"
  description  = "Service account for batch processing and scheduled jobs"
  project      = var.project_id
}

# Backend Service IAM Bindings (Least Privilege)
resource "google_project_iam_member" "backend_bindings" {
  for_each = toset([
    "roles/cloudsql.client",              # Cloud SQL access
    "roles/storage.objectViewer",         # Read from Cloud Storage
    "roles/storage.objectCreator",        # Write to Cloud Storage
    "roles/secretmanager.secretAccessor", # Access secrets
    "roles/logging.logWriter",            # Write logs
    "roles/cloudtrace.agent",             # Write traces
    "roles/monitoring.metricWriter",      # Write metrics
    "roles/aiplatform.user",              # Use Vertex AI
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.backend_service.email}"
}

# Routes API specific permission for backend
resource "google_project_iam_member" "backend_routes_api" {
  project = var.project_id
  role    = "roles/routes.viewer"
  member  = "serviceAccount:${google_service_account.backend_service.email}"
}

# Frontend Service IAM Bindings (Minimal)
resource "google_project_iam_member" "frontend_bindings" {
  for_each = toset([
    "roles/logging.logWriter",       # Write logs
    "roles/cloudtrace.agent",        # Write traces
    "roles/monitoring.metricWriter", # Write metrics
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.frontend_service.email}"
}

# Worker Service IAM Bindings
resource "google_project_iam_member" "worker_bindings" {
  for_each = toset([
    "roles/cloudsql.client",              # Cloud SQL access
    "roles/storage.objectAdmin",          # Full storage access for batch processing
    "roles/secretmanager.secretAccessor", # Access secrets
    "roles/logging.logWriter",            # Write logs
    "roles/aiplatform.user",              # Use Vertex AI for predictions
    "roles/bigquery.dataEditor",          # Write to BigQuery for analytics
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.worker_service.email}"
}

# Cloud Run Service Configuration with Workload Identity
resource "google_cloud_run_service" "backend" {
  name     = "lucky-gas-backend"
  location = var.region
  project  = var.project_id

  template {
    spec {
      service_account_name = google_service_account.backend_service.email
      
      containers {
        image = "gcr.io/${var.project_id}/lucky-gas-backend:latest"
        
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }
        
        # No GOOGLE_APPLICATION_CREDENTIALS needed!
        # Workload Identity handles authentication automatically
      }
    }
    
    metadata {
      annotations = {
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/startup-cpu-boost"     = "true"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Cloud Run Service for Frontend
resource "google_cloud_run_service" "frontend" {
  name     = "lucky-gas-frontend"
  location = var.region
  project  = var.project_id

  template {
    spec {
      service_account_name = google_service_account.frontend_service.email
      
      containers {
        image = "gcr.io/${var.project_id}/lucky-gas-frontend:latest"
      }
    }
    
    metadata {
      annotations = {
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Allow public access to frontend (with Cloud Armor protection)
resource "google_cloud_run_service_iam_member" "frontend_public" {
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Backend only accessible via frontend or authenticated requests
resource "google_cloud_run_service_iam_member" "backend_frontend_access" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend_service.email}"
}

# Cloud Scheduler can invoke backend for scheduled tasks
resource "google_cloud_run_service_iam_member" "backend_scheduler_access" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.worker_service.email}"
}

# Workload Identity Binding for GKE (if using Kubernetes)
resource "google_service_account_iam_binding" "workload_identity_backend" {
  service_account_id = google_service_account.backend_service.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[default/lucky-gas-backend]"
  ]
}

# Output the service account emails for application configuration
output "backend_service_account" {
  value       = google_service_account.backend_service.email
  description = "Backend service account email"
}

output "frontend_service_account" {
  value       = google_service_account.frontend_service.email
  description = "Frontend service account email"
}

output "worker_service_account" {
  value       = google_service_account.worker_service.email
  description = "Worker service account email"
}

output "backend_service_url" {
  value       = google_cloud_run_service.backend.status[0].url
  description = "Backend Cloud Run service URL"
}

output "frontend_service_url" {
  value       = google_cloud_run_service.frontend.status[0].url
  description = "Frontend Cloud Run service URL"
}