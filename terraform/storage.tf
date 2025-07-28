# Storage Buckets

# Main storage bucket for application data
resource "google_storage_bucket" "app_data" {
  name          = "${var.project_id}-app-data-${var.environment}"
  location      = var.region
  storage_class = var.environment == "production" ? "STANDARD" : "NEARLINE"
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = var.environment == "production" ? 90 : 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
  
  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }
  
  cors {
    origin          = var.environment == "production" ? ["https://luckygas.com.tw"] : ["https://staging.luckygas.com.tw"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  labels = {
    environment = var.environment
    purpose     = "app-data"
  }
}

# Backup bucket
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-backups-${var.environment}"
  location      = var.region
  storage_class = "NEARLINE"
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = var.environment == "production" ? 365 : 90
    }
    action {
      type = "Delete"
    }
  }
  
  labels = {
    environment = var.environment
    purpose     = "backups"
  }
}

# Static assets bucket (for CDN)
resource "google_storage_bucket" "static_assets" {
  name          = "${var.project_id}-static-${var.environment}"
  location      = var.region
  storage_class = "STANDARD"
  
  uniform_bucket_level_access = false
  
  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  labels = {
    environment = var.environment
    purpose     = "static-assets"
  }
}

# Make static assets publicly readable
resource "google_storage_bucket_iam_member" "static_public_read" {
  bucket = google_storage_bucket.static_assets.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Grant app service account access to buckets
resource "google_storage_bucket_iam_member" "app_data_access" {
  bucket = google_storage_bucket.app_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_identity.email}"
}

resource "google_storage_bucket_iam_member" "backup_access" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_identity.email}"
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "${var.project_name}-docker-${var.environment}"
  description   = "Docker repository for ${var.project_name} ${var.environment}"
  format        = "DOCKER"
  
  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"
    
    most_recent_versions {
      keep_count = var.environment == "production" ? 10 : 5
    }
  }
  
  cleanup_policies {
    id     = "delete-old-versions"
    action = "DELETE"
    
    condition {
      older_than = var.environment == "production" ? "2592000s" : "604800s" # 30 days : 7 days
    }
  }
  
  depends_on = [
    google_project_service.required_apis["artifactregistry.googleapis.com"],
  ]
}

# Grant GKE nodes access to pull images
resource "google_artifact_registry_repository_iam_member" "gke_pull" {
  repository = google_artifact_registry_repository.docker.id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.kubernetes.email}"
}