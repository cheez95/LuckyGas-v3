"""Geographic clustering for route optimization."""
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics.pairwise import haversine_distances
from math import radians
import logging

from app.models.optimization import ClusterInfo

logger = logging.getLogger(__name__)


class GeographicClusterer:
    """
    Geographic clustering for grouping delivery locations.
    Supports DBSCAN and K-means clustering with Taiwan-specific constraints.
    """
    
    def __init__(self):
        self.earth_radius_km = 6371.0
        # Taiwan geographic constraints
        self.taiwan_constraints = {
            "mountain_regions": [
                # Central Mountain Range approximate boundaries
                {"lat_min": 23.5, "lat_max": 25.0, "lng_min": 120.8, "lng_max": 121.3}
            ],
            "river_barriers": [
                # Major rivers that affect routing
                {"name": "Tamsui River", "lat": 25.17, "lng": 121.41},
                {"name": "Dahan River", "lat": 24.95, "lng": 121.35}
            ]
        }
    
    def cluster_by_dbscan(
        self,
        locations: List[Dict],
        eps_km: float = 2.0,
        min_samples: int = 3,
        consider_time_windows: bool = False
    ) -> List[ClusterInfo]:
        """
        Cluster locations using DBSCAN (Density-Based Spatial Clustering).
        
        Args:
            locations: List of dicts with 'id', 'lat', 'lng', and optional 'time_window'
            eps_km: Maximum distance between points in same cluster (kilometers)
            min_samples: Minimum points to form a dense region
            consider_time_windows: Whether to consider delivery time windows
            
        Returns:
            List of ClusterInfo objects
        """
        if not locations:
            return []
        
        # Extract coordinates
        coords = np.array([[loc['lat'], loc['lng']] for loc in locations])
        coords_rad = np.radians(coords)
        
        # Calculate distance matrix using haversine
        distance_matrix = haversine_distances(coords_rad) * self.earth_radius_km
        
        # Adjust distances based on time windows if requested
        if consider_time_windows:
            distance_matrix = self._adjust_for_time_windows(distance_matrix, locations)
        
        # Apply Taiwan geographic constraints
        distance_matrix = self._apply_geographic_constraints(distance_matrix, coords)
        
        # Perform DBSCAN clustering
        clustering = DBSCAN(eps=eps_km, min_samples=min_samples, metric='precomputed')
        labels = clustering.fit_predict(distance_matrix)
        
        # Build cluster info
        return self._build_cluster_info(locations, labels, coords)
    
    def cluster_by_kmeans(
        self,
        locations: List[Dict],
        n_clusters: int,
        max_iterations: int = 300
    ) -> List[ClusterInfo]:
        """
        Cluster locations using K-means clustering.
        
        Args:
            locations: List of dicts with 'id', 'lat', 'lng'
            n_clusters: Number of clusters to create
            max_iterations: Maximum iterations for convergence
            
        Returns:
            List of ClusterInfo objects
        """
        if not locations or n_clusters <= 0:
            return []
        
        # Limit clusters to number of locations
        n_clusters = min(n_clusters, len(locations))
        
        # Extract coordinates
        coords = np.array([[loc['lat'], loc['lng']] for loc in locations])
        
        # Perform K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, max_iter=max_iterations, random_state=42)
        labels = kmeans.fit_predict(coords)
        
        # Build cluster info with K-means centers
        clusters = self._build_cluster_info(locations, labels, coords)
        
        # Update cluster centers from K-means
        for i, cluster in enumerate(clusters):
            if i < len(kmeans.cluster_centers_):
                cluster.center_lat = float(kmeans.cluster_centers_[i][0])
                cluster.center_lng = float(kmeans.cluster_centers_[i][1])
        
        return clusters
    
    def cluster_with_constraints(
        self,
        locations: List[Dict],
        constraints: List[str],
        max_cluster_size: int = 20,
        target_density: float = 5.0
    ) -> List[ClusterInfo]:
        """
        Cluster with specific constraints like vehicle capacity and geographic barriers.
        
        Args:
            locations: List of location dictionaries
            constraints: List of constraint types ['mountains', 'rivers', 'capacity']
            max_cluster_size: Maximum locations per cluster
            target_density: Target density (locations per sq km)
            
        Returns:
            List of ClusterInfo objects
        """
        # Start with geographic clustering
        eps_km = self._calculate_eps_from_density(len(locations), target_density)
        clusters = self.cluster_by_dbscan(locations, eps_km=eps_km, min_samples=2)
        
        # Apply size constraints
        if 'capacity' in constraints:
            clusters = self._enforce_cluster_size_limit(clusters, locations, max_cluster_size)
        
        # Verify geographic constraints
        if 'mountains' in constraints or 'rivers' in constraints:
            clusters = self._verify_geographic_accessibility(clusters, locations)
        
        return clusters
    
    def cluster_by_time_windows(
        self,
        locations: List[Dict],
        eps_km: float = 2.0
    ) -> List[ClusterInfo]:
        """
        Cluster locations considering delivery time windows.
        
        Args:
            locations: List with 'time_window' field
            eps_km: Maximum distance for clustering
            
        Returns:
            List of ClusterInfo objects
        """
        # Group by time windows first
        time_groups = {}
        for loc in locations:
            window = loc.get('time_window', 'anytime')
            if window not in time_groups:
                time_groups[window] = []
            time_groups[window].append(loc)
        
        # Cluster within each time window
        all_clusters = []
        cluster_id_offset = 0
        
        for window, window_locations in time_groups.items():
            if not window_locations:
                continue
                
            # Cluster this time window group
            window_clusters = self.cluster_by_dbscan(
                window_locations,
                eps_km=eps_km,
                min_samples=2
            )
            
            # Adjust cluster IDs to be globally unique
            for cluster in window_clusters:
                cluster.cluster_id += cluster_id_offset
            
            cluster_id_offset += len(window_clusters)
            all_clusters.extend(window_clusters)
        
        return all_clusters
    
    def _adjust_for_time_windows(
        self,
        distance_matrix: np.ndarray,
        locations: List[Dict]
    ) -> np.ndarray:
        """Adjust distance matrix based on time window compatibility."""
        adjusted = distance_matrix.copy()
        n = len(locations)
        
        for i in range(n):
            for j in range(i + 1, n):
                window_i = locations[i].get('time_window', 'anytime')
                window_j = locations[j].get('time_window', 'anytime')
                
                # Increase distance for incompatible time windows
                if window_i != window_j and window_i != 'anytime' and window_j != 'anytime':
                    # Make them appear 10x farther apart
                    adjusted[i, j] *= 10
                    adjusted[j, i] *= 10
        
        return adjusted
    
    def _apply_geographic_constraints(
        self,
        distance_matrix: np.ndarray,
        coords: np.ndarray
    ) -> np.ndarray:
        """Apply Taiwan-specific geographic constraints."""
        adjusted = distance_matrix.copy()
        n = len(coords)
        
        for i in range(n):
            for j in range(i + 1, n):
                # Check if points are separated by mountains
                if self._crosses_mountain(coords[i], coords[j]):
                    # Increase effective distance by 3x
                    adjusted[i, j] *= 3
                    adjusted[j, i] *= 3
                
                # Check if points are separated by major rivers
                if self._crosses_river(coords[i], coords[j]):
                    # Increase effective distance by 1.5x
                    adjusted[i, j] *= 1.5
                    adjusted[j, i] *= 1.5
        
        return adjusted
    
    def _crosses_mountain(self, point1: np.ndarray, point2: np.ndarray) -> bool:
        """Check if line between two points crosses mountain regions."""
        for mountain in self.taiwan_constraints["mountain_regions"]:
            # Simple check: if one point is west and other is east of mountain range
            if (point1[1] < mountain["lng_min"] and point2[1] > mountain["lng_max"]) or \
               (point2[1] < mountain["lng_min"] and point1[1] > mountain["lng_max"]):
                # And both are within mountain latitude range
                if (mountain["lat_min"] <= point1[0] <= mountain["lat_max"] and
                    mountain["lat_min"] <= point2[0] <= mountain["lat_max"]):
                    return True
        return False
    
    def _crosses_river(self, point1: np.ndarray, point2: np.ndarray) -> bool:
        """Check if line between two points crosses major rivers."""
        # Simplified check - in production, use actual river geometry
        for river in self.taiwan_constraints["river_barriers"]:
            river_lat = river["lat"]
            river_lng = river["lng"]
            
            # Check if line crosses near river point
            if min(point1[0], point2[0]) <= river_lat <= max(point1[0], point2[0]):
                if min(point1[1], point2[1]) <= river_lng <= max(point1[1], point2[1]):
                    return True
        return False
    
    def _build_cluster_info(
        self,
        locations: List[Dict],
        labels: np.ndarray,
        coords: np.ndarray
    ) -> List[ClusterInfo]:
        """Build ClusterInfo objects from clustering results."""
        clusters = {}
        
        for idx, label in enumerate(labels):
            if label == -1:  # Noise point in DBSCAN
                # Create single-point cluster for noise
                label = max(clusters.keys(), default=-1) + 1
            
            if label not in clusters:
                clusters[label] = {
                    "order_ids": [],
                    "coords": [],
                    "demands": {}
                }
            
            clusters[label]["order_ids"].append(locations[idx]["id"])
            clusters[label]["coords"].append(coords[idx])
            
            # Aggregate demands if present
            if "demand" in locations[idx]:
                for product, qty in locations[idx]["demand"].items():
                    if product not in clusters[label]["demands"]:
                        clusters[label]["demands"][product] = 0
                    clusters[label]["demands"][product] += qty
        
        # Convert to ClusterInfo objects
        cluster_infos = []
        for cluster_id, data in clusters.items():
            coords_array = np.array(data["coords"])
            center = coords_array.mean(axis=0)
            
            # Calculate cluster radius
            if len(coords_array) > 1:
                distances = np.sqrt(np.sum((coords_array - center)**2, axis=1))
                radius_km = np.max(distances) * 111  # Rough conversion to km
            else:
                radius_km = 0.5  # Default for single-point clusters
            
            # Calculate density
            area_km2 = np.pi * radius_km ** 2 if radius_km > 0 else 1
            density = len(data["order_ids"]) / area_km2
            
            cluster_info = ClusterInfo(
                cluster_id=int(cluster_id),
                center_lat=float(center[0]),
                center_lng=float(center[1]),
                order_ids=data["order_ids"],
                total_demand=data["demands"],
                radius_km=float(radius_km),
                density_score=float(density)
            )
            cluster_infos.append(cluster_info)
        
        return cluster_infos
    
    def _calculate_eps_from_density(
        self,
        n_locations: int,
        target_density: float
    ) -> float:
        """Calculate DBSCAN eps parameter from target density."""
        # Assuming uniform distribution, calculate radius for target density
        # density = n_points / area, area = pi * r^2
        # r = sqrt(n_points / (density * pi))
        import math
        radius = math.sqrt(n_locations / (target_density * math.pi))
        return max(0.5, min(5.0, radius))  # Clamp between 0.5 and 5 km
    
    def _enforce_cluster_size_limit(
        self,
        clusters: List[ClusterInfo],
        locations: List[Dict],
        max_size: int
    ) -> List[ClusterInfo]:
        """Split clusters that exceed size limit."""
        location_map = {loc["id"]: loc for loc in locations}
        new_clusters = []
        
        for cluster in clusters:
            if len(cluster.order_ids) <= max_size:
                new_clusters.append(cluster)
            else:
                # Split large cluster using K-means
                n_subclusters = (len(cluster.order_ids) + max_size - 1) // max_size
                cluster_locations = [location_map[oid] for oid in cluster.order_ids]
                
                subclusters = self.cluster_by_kmeans(cluster_locations, n_subclusters)
                new_clusters.extend(subclusters)
        
        return new_clusters
    
    def _verify_geographic_accessibility(
        self,
        clusters: List[ClusterInfo],
        locations: List[Dict]
    ) -> List[ClusterInfo]:
        """Verify clusters don't span geographic barriers."""
        # This is a simplified check - in production, use actual road network data
        location_map = {loc["id"]: loc for loc in locations}
        verified_clusters = []
        
        for cluster in clusters:
            if len(cluster.order_ids) <= 1:
                verified_clusters.append(cluster)
                continue
            
            # Check if any locations are separated by barriers
            cluster_locs = [location_map[oid] for oid in cluster.order_ids]
            coords = np.array([[loc['lat'], loc['lng']] for loc in cluster_locs])
            
            # Simple check: if cluster spans too much latitude/longitude, split it
            lat_span = coords[:, 0].max() - coords[:, 0].min()
            lng_span = coords[:, 1].max() - coords[:, 1].min()
            
            if lat_span > 0.1 or lng_span > 0.1:  # ~11km span
                # Split using K-means
                subclusters = self.cluster_by_kmeans(cluster_locs, 2)
                verified_clusters.extend(subclusters)
            else:
                verified_clusters.append(cluster)
        
        return verified_clusters