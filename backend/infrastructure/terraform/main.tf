terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    # Backend configuration will be provided during initialization
    # terraform init -backend-config="bucket=BUCKET_NAME" -backend-config="prefix=terraform/state"
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset(var.gcp_apis)
  
  project = var.project_id
  service = each.key
  
  disable_on_destroy = false
}

# Create service account for the application
resource "google_service_account" "app_service_account" {
  account_id   = "${var.environment}-luckygas-app"
  display_name = "Lucky Gas Application Service Account (${var.environment})"
  description  = "Service account for Lucky Gas application in ${var.environment}"
  project      = var.project_id
}

# IAM roles for the service account
resource "google_project_iam_member" "app_roles" {
  for_each = toset(var.app_service_account_roles)
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.app_service_account.email}"
}

# Create VPC network
resource "google_compute_network" "vpc" {
  name                    = "${var.environment}-luckygas-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
  
  depends_on = [google_project_service.apis["compute.googleapis.com"]]
}

# Create subnet for the application
resource "google_compute_subnetwork" "app_subnet" {
  name          = "${var.environment}-luckygas-app-subnet"
  ip_cidr_range = var.app_subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  project       = var.project_id
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router for NAT
resource "google_compute_router" "router" {
  name    = "${var.environment}-luckygas-router"
  region  = var.region
  network = google_compute_network.vpc.id
  project = var.project_id
}

# Cloud NAT for outbound internet access
resource "google_compute_router_nat" "nat" {
  name                               = "${var.environment}-luckygas-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  project                            = var.project_id
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.environment}-allow-internal"
  network = google_compute_network.vpc.name
  project = var.project_id
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = [var.app_subnet_cidr]
}

resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.environment}-allow-health-checks"
  network = google_compute_network.vpc.name
  project = var.project_id
  
  allow {
    protocol = "tcp"
    ports    = ["8000", "9090"]  # App port and metrics port
  }
  
  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]  # Google health check IPs
  target_tags   = ["luckygas-app"]
}