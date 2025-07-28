# GKE Cluster Configuration

resource "google_container_cluster" "primary" {
  name     = "${var.project_name}-cluster-${var.environment}"
  location = var.zone
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Network configuration
  network    = google_compute_network.vpc.self_link
  subnetwork = google_compute_subnetwork.subnet.self_link
  
  # Cluster configuration
  min_master_version = var.kubernetes_version
  
  # IP allocation policy for VPC-native cluster
  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }
  
  # Enable Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Security settings
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  
  # Enable network policy
  network_policy {
    enabled  = true
    provider = "CALICO"
  }
  
  # Enable Binary Authorization
  binary_authorization {
    evaluation_mode = var.environment == "production" ? "REQUIRE_ATTESTATION" : "PROJECT_SINGLETON_POLICY_ENFORCE"
  }
  
  # Cluster addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
    gcp_filestore_csi_driver_config {
      enabled = true
    }
  }
  
  # Maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"  # 3 AM Taiwan time (UTC+8)
    }
  }
  
  # Monitoring and logging
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
    managed_prometheus {
      enabled = true
    }
  }
  
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
  
  # Release channel
  release_channel {
    channel = var.environment == "production" ? "STABLE" : "REGULAR"
  }
  
  # Cost management
  cost_management_config {
    enabled = true
  }
  
  # Resource labels
  resource_labels = {
    environment = var.environment
    project     = var.project_name
    managed_by  = "terraform"
  }
  
  depends_on = [
    google_project_service.required_apis["container.googleapis.com"],
    google_compute_network.vpc,
  ]
}

# Node pools
resource "google_container_node_pool" "primary_nodes" {
  name       = "${var.project_name}-node-pool-${var.environment}"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  
  # Autoscaling configuration
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }
  
  # Node management
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  # Node configuration
  node_config {
    preemptible  = var.environment != "production"
    machine_type = var.machine_type
    
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.kubernetes.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Disk configuration
    disk_size_gb = 100
    disk_type    = "pd-ssd"
    
    # Workload Identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    
    # Shielded instance configuration
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    
    # Labels
    labels = {
      environment = var.environment
      node_pool   = "primary"
    }
    
    # Metadata
    metadata = {
      disable-legacy-endpoints = "true"
    }
    
    # Taints for production workloads
    dynamic "taint" {
      for_each = var.environment == "production" ? [{key = "production", value = "true", effect = "NO_SCHEDULE"}] : []
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }
  
  # Upgrade settings
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
    strategy        = "SURGE"
  }
  
  lifecycle {
    ignore_changes = [initial_node_count]
  }
}

# Service account for nodes
resource "google_service_account" "kubernetes" {
  account_id   = "${var.project_name}-k8s-${var.environment}"
  display_name = "Kubernetes Service Account for ${var.environment}"
  description  = "Service account for GKE nodes in ${var.environment}"
}

# Grant necessary permissions to the service account
resource "google_project_iam_member" "kubernetes_permissions" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
    "roles/storage.objectViewer",
    "roles/artifactregistry.reader",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.kubernetes.email}"
}