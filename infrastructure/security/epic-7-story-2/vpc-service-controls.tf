# VPC Service Controls Configuration
# Restricts API access to specific VPC networks and authorized services

# Create Access Context Manager Access Policy
resource "google_access_context_manager_access_policy" "lucky_gas_policy" {
  parent = "organizations/${var.organization_id}"
  title  = "Lucky Gas Access Policy"
}

# Define Access Levels
resource "google_access_context_manager_access_level" "internal_access" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}/accessLevels/internal_access"
  title  = "Internal Network Access"
  
  basic {
    conditions {
      # Allow access from specific IP ranges (office, VPN)
      ip_subnetworks = [
        "203.0.113.0/24",    # Office IP range (replace with actual)
        "198.51.100.0/24",   # VPN IP range (replace with actual)
        "10.0.0.0/8"         # Internal VPC ranges
      ]
    }
    
    conditions {
      # Allow access from specific service accounts
      members = [
        "serviceAccount:${google_service_account.backend_workload_identity.email}",
        "serviceAccount:${google_service_account.frontend_workload_identity.email}",
        "serviceAccount:${google_service_account.worker_workload_identity.email}",
        "serviceAccount:lucky-gas-prod@vast-tributary-466619-m8.iam.gserviceaccount.com"
      ]
    }
    
    conditions {
      # Allow access from specific regions (Taiwan and backup)
      regions = [
        "TW",  # Taiwan
        "HK",  # Hong Kong (backup)
        "SG"   # Singapore (backup)
      ]
    }
    
    # Combine conditions with OR
    combining_function = "OR"
  }
}

# Define Service Perimeter
resource "google_access_context_manager_service_perimeter" "lucky_gas_perimeter" {
  parent = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}"
  name   = "accessPolicies/${google_access_context_manager_access_policy.lucky_gas_policy.name}/servicePerimeters/lucky_gas_perimeter"
  title  = "Lucky Gas Service Perimeter"
  
  # Perimeter type
  perimeter_type = "PERIMETER_TYPE_REGULAR"
  
  # Resources protected by this perimeter
  status {
    resources = [
      "projects/${var.project_number}"
    ]
    
    # Services restricted by this perimeter
    restricted_services = [
      "aiplatform.googleapis.com",
      "bigquery.googleapis.com",
      "cloudsql.googleapis.com",
      "compute.googleapis.com",
      "container.googleapis.com",
      "dataflow.googleapis.com",
      "pubsub.googleapis.com",
      "secretmanager.googleapis.com",
      "storage.googleapis.com",
      "redis.googleapis.com",
      "sqladmin.googleapis.com"
    ]
    
    # Access levels that can access the perimeter
    access_levels = [
      google_access_context_manager_access_level.internal_access.name
    ]
    
    # VPC accessible services configuration
    vpc_accessible_services {
      enable_restriction = true
      allowed_services   = [
        "aiplatform.googleapis.com",
        "bigquery.googleapis.com",
        "cloudsql.googleapis.com",
        "compute.googleapis.com",
        "container.googleapis.com",
        "dataflow.googleapis.com",
        "logging.googleapis.com",
        "monitoring.googleapis.com",
        "pubsub.googleapis.com",
        "secretmanager.googleapis.com",
        "storage.googleapis.com",
        "redis.googleapis.com"
      ]
    }
    
    # Ingress policies for external access
    ingress_policies {
      ingress_from {
        sources {
          access_level = google_access_context_manager_access_level.internal_access.name
        }
        
        identity_type = "ANY_SERVICE_ACCOUNT"
      }
      
      ingress_to {
        resources = ["*"]
        
        operations {
          service_name = "storage.googleapis.com"
          method_selectors {
            method = "*"
          }
        }
        
        operations {
          service_name = "secretmanager.googleapis.com"
          method_selectors {
            method = "google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion"
          }
        }
      }
    }
    
    # Egress policies for external services
    egress_policies {
      egress_from {
        identity_type = "ANY_SERVICE_ACCOUNT"
      }
      
      egress_to {
        resources = ["*"]
        
        operations {
          service_name = "maps-backend.googleapis.com"
          method_selectors {
            method = "*"
          }
        }
        
        operations {
          service_name = "routes.googleapis.com"
          method_selectors {
            method = "*"
          }
        }
        
        # Allow external API calls for e-invoice
        external_resources = [
          "https://api.einvoice.nat.gov.tw/*"
        ]
      }
    }
  }
}

# Private Google Access for subnets
resource "google_compute_subnetwork" "main_with_private_access" {
  name          = "luckygas-subnet-${var.region}-secure"
  ip_cidr_range = "10.1.0.0/24"
  network       = google_compute_network.main.id
  region        = var.region
  
  # Enable Private Google Access
  private_ip_google_access = true
  
  # Enable VPC Flow Logs for security monitoring
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 1.0
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud NAT for secure egress
resource "google_compute_router" "main" {
  name    = "luckygas-router"
  region  = var.region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  name                               = "luckygas-nat"
  router                             = google_compute_router.main.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  
  subnetwork {
    name                    = google_compute_subnetwork.main_with_private_access.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  
  # Log NAT events for security monitoring
  log_config {
    enable = true
    filter = "ALL"
  }
}

# Firewall rules for VPC Service Controls
resource "google_compute_firewall" "deny_all_ingress" {
  name    = "luckygas-deny-all-ingress"
  network = google_compute_network.main.name
  
  direction = "INGRESS"
  priority  = 1000
  
  deny {
    protocol = "all"
  }
  
  source_ranges = ["0.0.0.0/0"]
  
  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_firewall" "allow_internal" {
  name    = "luckygas-allow-internal"
  network = google_compute_network.main.name
  
  direction = "INGRESS"
  priority  = 900
  
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
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16"
  ]
}

resource "google_compute_firewall" "allow_google_apis" {
  name    = "luckygas-allow-google-apis"
  network = google_compute_network.main.name
  
  direction = "EGRESS"
  priority  = 900
  
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  
  destination_ranges = ["199.36.153.8/30"]  # Private Google Access IPs
}

# Variables required
variable "organization_id" {
  description = "Google Cloud Organization ID"
  type        = string
}

variable "project_number" {
  description = "Google Cloud Project Number"
  type        = string
}

# Outputs
output "service_perimeter_name" {
  value       = google_access_context_manager_service_perimeter.lucky_gas_perimeter.name
  description = "VPC Service Controls perimeter name"
}

output "access_level_name" {
  value       = google_access_context_manager_access_level.internal_access.name
  description = "Access level for internal access"
}