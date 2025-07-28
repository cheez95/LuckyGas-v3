# VPC Network Configuration

resource "google_compute_network" "vpc" {
  name                            = "${var.project_name}-vpc-${var.environment}"
  auto_create_subnetworks         = false
  delete_default_routes_on_create = false
  mtu                             = 1460
  routing_mode                    = "REGIONAL"
  
  depends_on = [
    google_project_service.required_apis["compute.googleapis.com"],
  ]
}

# Subnet for GKE
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_name}-subnet-${var.environment}"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  
  # Secondary ranges for GKE
  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = var.pods_cidr
  }
  
  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = var.services_cidr
  }
  
  # Enable VPC flow logs
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
  
  private_ip_google_access = true
}

# Cloud Router
resource "google_compute_router" "router" {
  name    = "${var.project_name}-router-${var.environment}"
  region  = var.region
  network = google_compute_network.vpc.id
}

# NAT Gateway for outbound traffic
resource "google_compute_router_nat" "nat" {
  name                               = "${var.project_name}-nat-${var.environment}"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall Rules

# Allow internal communication
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project_name}-allow-internal-${var.environment}"
  network = google_compute_network.vpc.name
  
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
  
  source_ranges = [
    var.subnet_cidr,
    var.pods_cidr,
    var.services_cidr,
  ]
}

# Allow health checks
resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.project_name}-allow-health-checks-${var.environment}"
  network = google_compute_network.vpc.name
  
  allow {
    protocol = "tcp"
  }
  
  source_ranges = [
    "35.191.0.0/16",  # Google Cloud health check IPs
    "130.211.0.0/22", # Google Cloud health check IPs
  ]
  
  target_tags = ["gke-node"]
}

# Reserve static IP for Ingress
resource "google_compute_global_address" "ingress_ip" {
  name         = "${var.project_name}-ingress-ip-${var.environment}"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
}

# Private Service Connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.project_name}-private-ip-${var.environment}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
  
  depends_on = [
    google_project_service.required_apis["servicenetworking.googleapis.com"],
  ]
}

# Serverless VPC Access Connector (for Cloud Run if needed)
resource "google_vpc_access_connector" "connector" {
  name          = "${var.project_name}-connector-${var.environment}"
  region        = var.region
  ip_cidr_range = var.serverless_vpc_connector_cidr
  network       = google_compute_network.vpc.name
  
  min_instances = 2
  max_instances = var.environment == "production" ? 10 : 3
  
  depends_on = [
    google_project_service.required_apis["vpcaccess.googleapis.com"],
  ]
}