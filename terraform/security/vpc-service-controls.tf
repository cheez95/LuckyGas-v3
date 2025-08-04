# VPC Service Controls for Lucky Gas API Security
# Creates a security perimeter around sensitive Google Cloud APIs

# VPC Network for Lucky Gas
resource "google_compute_network" "lucky_gas_vpc" {
  name                    = "lucky-gas-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# Subnet for Cloud Run and other services
resource "google_compute_subnetwork" "lucky_gas_subnet" {
  name          = "lucky-gas-subnet-${var.region}"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.lucky_gas_vpc.id
  project       = var.project_id

  # Enable Private Google Access
  private_ip_google_access = true

  # Enable VPC Flow Logs for security monitoring
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router for NAT
resource "google_compute_router" "lucky_gas_router" {
  name    = "lucky-gas-router"
  region  = var.region
  network = google_compute_network.lucky_gas_vpc.id
  project = var.project_id
}

# Cloud NAT for outbound internet access
resource "google_compute_router_nat" "lucky_gas_nat" {
  name                               = "lucky-gas-nat"
  router                             = google_compute_router.lucky_gas_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  project                            = var.project_id

  log_config {
    enable = true
    filter = "ALL"
  }
}

# VPC Service Controls Perimeter
resource "google_access_context_manager_service_perimeter" "lucky_gas_perimeter" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}/servicePerimeters/lucky_gas_apis"
  title  = "Lucky Gas API Security Perimeter"

  # Regular perimeter (not dry-run)
  status {
    # Restricted services within the perimeter
    restricted_services = [
      "aiplatform.googleapis.com",
      "storage.googleapis.com",
      "secretmanager.googleapis.com",
      "sqladmin.googleapis.com",
      "sql-component.googleapis.com",
      "routes.googleapis.com",
      "compute.googleapis.com",
    ]

    # Resources within the perimeter
    resources = [
      "projects/${var.project_id}",
    ]

    # Access levels (defined below)
    access_levels = [
      google_access_context_manager_access_level.lucky_gas_access.name,
    ]

    # VPC accessible services
    vpc_accessible_services {
      enable_restriction = true
      allowed_services   = [
        "aiplatform.googleapis.com",
        "storage.googleapis.com",
        "secretmanager.googleapis.com",
        "sqladmin.googleapis.com",
        "routes.googleapis.com",
      ]
    }
  }
}

# Access Context Manager Policy
resource "google_access_context_manager_access_policy" "lucky_gas_policy" {
  parent = "organizations/${var.organization_id}"
  title  = "Lucky Gas Access Policy"
}

# Access Level Definition
resource "google_access_context_manager_access_level" "lucky_gas_access" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}/accessLevels/lucky_gas_secure"
  title  = "Lucky Gas Secure Access"

  basic {
    # Conditions for access
    conditions {
      # IP allowlist (office and Cloud NAT IPs)
      ip_subnetworks = [
        "203.0.113.0/24",  # Replace with actual office IP range
        "198.51.100.0/24", # Replace with actual Cloud NAT IP range
      ]

      # Required service accounts
      members = [
        "serviceAccount:${google_service_account.backend_service.email}",
        "serviceAccount:${google_service_account.worker_service.email}",
      ]

      # Restrict to specific regions
      regions = [
        "TW", # Taiwan
        "HK", # Hong Kong (for failover)
      ]
    }
  }
}

# Private Service Access for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "lucky-gas-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.lucky_gas_vpc.id
  project       = var.project_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.lucky_gas_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Firewall Rules
resource "google_compute_firewall" "deny_all_ingress" {
  name     = "lucky-gas-deny-all-ingress"
  network  = google_compute_network.lucky_gas_vpc.name
  project  = var.project_id
  priority = 1000

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
  
  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

# Allow internal communication
resource "google_compute_firewall" "allow_internal" {
  name     = "lucky-gas-allow-internal"
  network  = google_compute_network.lucky_gas_vpc.name
  project  = var.project_id
  priority = 100

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

  source_ranges = ["10.0.0.0/8"]
}

# Allow Google APIs
resource "google_compute_firewall" "allow_google_apis" {
  name     = "lucky-gas-allow-google-apis"
  network  = google_compute_network.lucky_gas_vpc.name
  project  = var.project_id
  priority = 200

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  direction          = "EGRESS"
  destination_ranges = ["199.36.153.8/30", "199.36.153.4/30"] # Google APIs IP ranges
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "lucky_gas_policy" {
  name    = "lucky-gas-security-policy"
  project = var.project_id

  # Default rule
  rule {
    action   = "allow"
    priority = "2147483647"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    description = "Default allow rule"
  }

  # Block known malicious IPs
  rule {
    action   = "deny(403)"
    priority = "1000"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = [
          "192.0.2.0/24",    # Example malicious range
          "198.51.100.0/24", # Example malicious range
        ]
      }
    }

    description = "Block known malicious IPs"
  }

  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = "2000"

    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }

    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      
      ban_duration_sec = 600
    }

    description = "Rate limiting - 100 requests per minute"
  }

  # Taiwan/Regional access (optional)
  rule {
    action   = "allow"
    priority = "3000"

    match {
      expr {
        expression = "origin.region_code == 'TW' || origin.region_code == 'HK'"
      }
    }

    description = "Allow Taiwan and Hong Kong traffic"
  }
}

# Outputs
output "vpc_network_name" {
  value       = google_compute_network.lucky_gas_vpc.name
  description = "VPC network name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.lucky_gas_subnet.name
  description = "Subnet name"
}

output "security_policy_id" {
  value       = google_compute_security_policy.lucky_gas_policy.id
  description = "Cloud Armor security policy ID"
}

output "service_perimeter_name" {
  value       = google_access_context_manager_service_perimeter.lucky_gas_perimeter.name
  description = "VPC Service Controls perimeter name"
}