# Cloud Storage buckets

# Main storage bucket for media files
resource "google_storage_bucket" "media" {
  name          = "${var.project_id}-${var.environment}-media"
  location      = var.storage_location
  storage_class = var.storage_class
  project       = var.project_id
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = var.environment == "production"
  }
  
  lifecycle_rule {
    condition {
      age = var.environment == "production" ? 90 : 30
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  labels = merge(var.labels, {
    environment = var.environment
    purpose     = "media"
  })
}

# Backup bucket
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-${var.environment}-backups"
  location      = var.storage_location
  storage_class = "NEARLINE"
  project       = var.project_id
  
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
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  labels = merge(var.labels, {
    environment = var.environment
    purpose     = "backups"
  })
}

# Terraform state bucket (only for production)
resource "google_storage_bucket" "terraform_state" {
  count = var.environment == "production" ? 1 : 0
  
  name          = "${var.project_id}-terraform-state"
  location      = var.storage_location
  storage_class = var.storage_class
  project       = var.project_id
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }
  
  labels = merge(var.labels, {
    purpose = "terraform-state"
  })
}

# Grant service account access to buckets
resource "google_storage_bucket_iam_member" "media_access" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.app_service_account.email}"
}

resource "google_storage_bucket_iam_member" "backup_access" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.app_service_account.email}"
}