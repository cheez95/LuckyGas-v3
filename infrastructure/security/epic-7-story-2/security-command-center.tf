# Cloud Security Command Center Configuration
# Enables security monitoring, vulnerability scanning, and compliance checking

# Enable Security Command Center API
resource "google_project_service" "security_center_api" {
  service = "securitycenter.googleapis.com"
  
  disable_on_destroy = false
}

# Enable Container Analysis API for vulnerability scanning
resource "google_project_service" "container_analysis_api" {
  service = "containeranalysis.googleapis.com"
  
  disable_on_destroy = false
}

# Enable Binary Authorization API
resource "google_project_service" "binary_authorization_api" {
  service = "binaryauthorization.googleapis.com"
  
  disable_on_destroy = false
}

# Security Command Center Custom Module for Lucky Gas specific checks
resource "google_scc_source" "lucky_gas_custom" {
  display_name = "Lucky Gas Security Monitoring"
  organization = var.organization_id
  description  = "Custom security monitoring for Lucky Gas application"
  
  depends_on = [google_project_service.security_center_api]
}

# Binary Authorization Policy
resource "google_binary_authorization_policy" "policy" {
  admission_whitelist_patterns {
    name_pattern = "${var.region}-docker.pkg.dev/${var.project_id}/luckygas/*"
  }
  
  default_admission_rule {
    evaluation_mode  = "REQUIRE_ATTESTATION"
    enforcement_mode = "ENFORCED_BLOCK_AND_AUDIT_LOG"
    
    require_attestations_by = [
      google_binary_authorization_attestor.prod_attestor.name
    ]
  }
  
  global_policy_evaluation_mode = "ENABLE"
  
  depends_on = [google_project_service.binary_authorization_api]
}

# Binary Authorization Attestor
resource "google_binary_authorization_attestor" "prod_attestor" {
  name = "prod-attestor"
  attestation_authority_note {
    note_reference = google_container_analysis_note.attestor_note.name
    public_keys {
      id = data.google_kms_crypto_key_version.attestor_key_version.id
      pkix_public_key {
        public_key_pem      = data.google_kms_crypto_key_version.attestor_key_version.public_key[0].pem
        signature_algorithm = data.google_kms_crypto_key_version.attestor_key_version.public_key[0].algorithm
      }
    }
  }
  
  depends_on = [google_project_service.binary_authorization_api]
}

# Container Analysis Note for attestation
resource "google_container_analysis_note" "attestor_note" {
  name = "prod-attestor-note"
  
  attestation_authority {
    hint {
      human_readable_name = "Production Attestor"
    }
  }
  
  depends_on = [google_project_service.container_analysis_api]
}

# KMS key for signing attestations
resource "google_kms_key_ring" "attestor_key_ring" {
  name     = "attestor-key-ring"
  location = "global"
}

resource "google_kms_crypto_key" "attestor_key" {
  name            = "attestor-key"
  key_ring        = google_kms_key_ring.attestor_key_ring.id
  rotation_period = "2592000s" # 30 days
  
  version_template {
    algorithm = "RSA_SIGN_PKCS1_2048_SHA256"
  }
}

data "google_kms_crypto_key_version" "attestor_key_version" {
  crypto_key = google_kms_crypto_key.attestor_key.id
}

# Security Health Analytics custom config
resource "google_project_organization_policy" "require_os_login" {
  project    = var.project_id
  constraint = "compute.requireOsLogin"
  
  boolean_policy {
    enforced = true
  }
}

resource "google_project_organization_policy" "require_shielded_vm" {
  project    = var.project_id
  constraint = "compute.requireShieldedVm"
  
  boolean_policy {
    enforced = true
  }
}

# Cloud Asset Inventory for compliance monitoring
resource "google_project_service" "cloud_asset_api" {
  service = "cloudasset.googleapis.com"
  
  disable_on_destroy = false
}

# Export asset inventory to BigQuery for analysis
resource "google_bigquery_dataset" "security_inventory" {
  dataset_id                  = "security_inventory"
  friendly_name               = "Security Asset Inventory"
  description                 = "Cloud Asset Inventory data for security analysis"
  location                    = var.region
  default_table_expiration_ms = 2592000000 # 30 days
  
  access {
    role          = "OWNER"
    user_by_email = "lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com"
  }
}

# Scheduled export of asset inventory
resource "google_cloud_asset_project_feed" "security_feed" {
  billing_project = var.project_id
  project         = var.project_id
  feed_id         = "security-inventory-feed"
  content_type    = "RESOURCE"
  
  asset_types = [
    "compute.googleapis.com/Instance",
    "iam.googleapis.com/ServiceAccount",
    "storage.googleapis.com/Bucket",
    "sqladmin.googleapis.com/Instance",
    "run.googleapis.com/Service",
    "redis.googleapis.com/Instance"
  ]
  
  feed_output_config {
    bigquery_destination {
      dataset = "projects/${var.project_id}/datasets/${google_bigquery_dataset.security_inventory.dataset_id}"
      table   = "asset_inventory"
    }
  }
  
  depends_on = [google_project_service.cloud_asset_api]
}

# Security Command Center notification config
resource "google_scc_notification_config" "high_severity_findings" {
  config_id    = "high-severity-findings"
  organization = var.organization_id
  description  = "Notify on high severity security findings"
  
  pubsub_topic = google_pubsub_topic.security_alerts.id
  
  streaming_config {
    filter = "category=\"VULNERABILITY\" AND state=\"ACTIVE\" AND (severity=\"HIGH\" OR severity=\"CRITICAL\")"
  }
  
  depends_on = [google_project_service.security_center_api]
}

# Pub/Sub topic for security alerts
resource "google_pubsub_topic" "security_alerts" {
  name = "security-alerts"
  
  message_retention_duration = "604800s" # 7 days
}

# Pub/Sub subscription for security alerts
resource "google_pubsub_subscription" "security_alerts_sub" {
  name  = "security-alerts-sub"
  topic = google_pubsub_topic.security_alerts.name
  
  message_retention_duration = "604800s"
  
  push_config {
    push_endpoint = "https://app.luckygas.tw/api/v1/security/alerts"
    
    oidc_token {
      service_account_email = google_service_account.backend_workload_identity.email
    }
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Cloud Function for processing security alerts
resource "google_cloudfunctions_function" "security_alert_processor" {
  name        = "security-alert-processor"
  description = "Process security alerts from Security Command Center"
  runtime     = "python39"
  
  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.functions.name
  source_archive_object = google_storage_bucket_object.security_function.name
  entry_point           = "process_alert"
  
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.security_alerts.name
  }
  
  environment_variables = {
    PROJECT_ID = var.project_id
    SLACK_WEBHOOK_SECRET = "security-alerts-webhook"
  }
  
  service_account_email = google_service_account.security_processor.email
}

# Service account for security alert processor
resource "google_service_account" "security_processor" {
  account_id   = "security-alert-processor"
  display_name = "Security Alert Processor"
}

resource "google_project_iam_member" "security_processor_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.security_processor.email}"
}

# Storage bucket for Cloud Functions
resource "google_storage_bucket" "functions" {
  name          = "${var.project_id}-functions"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
}

# Upload security alert processor function
resource "google_storage_bucket_object" "security_function" {
  name   = "security-alert-processor.zip"
  bucket = google_storage_bucket.functions.name
  source = "${path.module}/functions/security-alert-processor.zip"
}

# Outputs
output "security_alerts_topic" {
  value       = google_pubsub_topic.security_alerts.name
  description = "Pub/Sub topic for security alerts"
}

output "attestor_name" {
  value       = google_binary_authorization_attestor.prod_attestor.name
  description = "Binary Authorization attestor name"
}