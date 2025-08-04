/**
 * Simple marker clustering implementation for performance optimization
 */

import type { RouteStop } from '../../../types/maps.types';

export interface Cluster {
  id: string;
  center: google.maps.LatLng;
  bounds: google.maps.LatLngBounds;
  markers: MarkerData[];
  size: number;
}

export interface MarkerData {
  id: string;
  position: google.maps.LatLng;
  stop: RouteStop;
  routeId: string;
}

export interface ClusterOptions {
  gridSize: number;
  maxZoom: number;
  minimumClusterSize: number;
}

const DEFAULT_OPTIONS: ClusterOptions = {
  gridSize: 60,
  maxZoom: 15,
  minimumClusterSize: 3,
};

export class MarkerClusterer {
  private map: google.maps.Map;
  private markers: MarkerData[] = [];
  private clusters: Cluster[] = [];
  private options: ClusterOptions;
  private clusterMarkers: Map<string, google.maps.Marker> = new Map();
  
  constructor(map: google.maps.Map, options: Partial<ClusterOptions> = {}) {
    this.map = map;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    
    // Listen to map events
    this.map.addListener('zoom_changed', () => this.onMapChange());
    this.map.addListener('idle', () => this.onMapChange());
  }
  
  addMarkers(markers: MarkerData[]) {
    this.markers.push(...markers);
    this.cluster();
  }
  
  removeMarkers(markerIds: string[]) {
    const idSet = new Set(markerIds);
    this.markers = this.markers.filter(m => !idSet.has(m.id));
    this.cluster();
  }
  
  clearMarkers() {
    this.markers = [];
    this.clearClusters();
  }
  
  private onMapChange() {
    // Re-cluster on map change
    this.cluster();
  }
  
  private cluster() {
    const zoom = this.map.getZoom();
    
    // Clear existing clusters
    this.clearClusters();
    
    // Don't cluster at high zoom levels
    if (!zoom || zoom > this.options.maxZoom) {
      return;
    }
    
    // Create grid-based clusters
    const bounds = this.map.getBounds();
    if (!bounds) return;
    
    const clusters = this.createClusters(bounds);
    
    // Filter out small clusters
    this.clusters = clusters.filter(
      cluster => cluster.size >= this.options.minimumClusterSize
    );
    
    // Create cluster markers
    this.createClusterMarkers();
  }
  
  private createClusters(bounds: google.maps.LatLngBounds): Cluster[] {
    const clusters: Cluster[] = [];
    const processed = new Set<string>();
    
    // Grid size in pixels
    const gridSize = this.options.gridSize;
    
    for (const marker of this.markers) {
      if (processed.has(marker.id)) continue;
      if (!bounds.contains(marker.position)) continue;
      
      // Create new cluster
      const cluster: Cluster = {
        id: `cluster-${clusters.length}`,
        center: marker.position,
        bounds: new google.maps.LatLngBounds(marker.position, marker.position),
        markers: [marker],
        size: 1,
      };
      
      processed.add(marker.id);
      
      // Find nearby markers
      for (const other of this.markers) {
        if (processed.has(other.id)) continue;
        if (!bounds.contains(other.position)) continue;
        
        const distance = this.pixelDistance(
          marker.position,
          other.position
        );
        
        if (distance < gridSize) {
          cluster.markers.push(other);
          cluster.bounds.extend(other.position);
          cluster.size++;
          processed.add(other.id);
        }
      }
      
      // Update cluster center
      cluster.center = cluster.bounds.getCenter();
      clusters.push(cluster);
    }
    
    return clusters;
  }
  
  private pixelDistance(pos1: google.maps.LatLng, pos2: google.maps.LatLng): number {
    if (!this.map.getProjection()) return 0;
    
    const projection = this.map.getProjection()!;
    const p1 = projection.fromLatLngToPoint(pos1);
    const p2 = projection.fromLatLngToPoint(pos2);
    
    if (!p1 || !p2) return 0;
    
    const scale = Math.pow(2, this.map.getZoom() || 0);
    const dx = (p1.x - p2.x) * scale;
    const dy = (p1.y - p2.y) * scale;
    
    return Math.sqrt(dx * dx + dy * dy);
  }
  
  private clearClusters() {
    // Remove cluster markers from map
    this.clusterMarkers.forEach(marker => marker.setMap(null));
    this.clusterMarkers.clear();
    this.clusters = [];
  }
  
  private createClusterMarkers() {
    for (const cluster of this.clusters) {
      const marker = new google.maps.Marker({
        position: cluster.center,
        map: this.map,
        title: `${cluster.size} 個配送點`,
        icon: this.createClusterIcon(cluster.size),
        zIndex: 1000,
      });
      
      // Add click handler to zoom in
      marker.addListener('click', () => {
        this.map.fitBounds(cluster.bounds);
      });
      
      this.clusterMarkers.set(cluster.id, marker);
    }
  }
  
  private createClusterIcon(size: number): google.maps.Icon {
    const scale = this.getClusterScale(size);
    const color = this.getClusterColor(size);
    
    return {
      url: this.createClusterSVG(size, color),
      scaledSize: new google.maps.Size(scale, scale),
      anchor: new google.maps.Point(scale / 2, scale / 2),
    };
  }
  
  private getClusterScale(size: number): number {
    if (size < 10) return 40;
    if (size < 50) return 50;
    return 60;
  }
  
  private getClusterColor(size: number): string {
    if (size < 10) return '#1890ff';
    if (size < 50) return '#fa8c16';
    return '#f5222d';
  }
  
  private createClusterSVG(size: number, color: string): string {
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="${color}" opacity="0.8" />
        <circle cx="50" cy="50" r="45" fill="none" stroke="white" stroke-width="4" />
        <text x="50" y="55" text-anchor="middle" fill="white" 
              font-family="Arial" font-size="28" font-weight="bold">
          ${size}
        </text>
      </svg>
    `;
    
    return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg);
  }
  
  getClusters(): Cluster[] {
    return this.clusters;
  }
  
  getMarkers(): MarkerData[] {
    return this.markers;
  }
}

export default MarkerClusterer;