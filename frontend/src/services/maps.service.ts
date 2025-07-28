/**
 * Google Maps Service
 * 
 * Provides secure access to Google Maps functionality through backend proxy.
 * This service routes all Maps API requests through the backend to protect API keys
 * and implement proper rate limiting and access control.
 */

import axios, { AxiosInstance } from 'axios';
import { message } from 'antd';

export interface GeocodeResult {
  formatted_address: string;
  geometry: {
    location: {
      lat: number;
      lng: number;
    };
  };
  place_id: string;
}

export interface DirectionsResult {
  routes: Array<{
    overview_polyline: {
      points: string;
    };
    legs: Array<{
      distance: { text: string; value: number };
      duration: { text: string; value: number };
      steps: Array<{
        html_instructions: string;
        distance: { text: string; value: number };
        duration: { text: string; value: number };
      }>;
    }>;
  }>;
}

export interface PlaceResult {
  place_id: string;
  name: string;
  vicinity: string;
  geometry: {
    location: {
      lat: number;
      lng: number;
    };
  };
  types: string[];
  rating?: number;
}

export interface DistanceMatrixResult {
  rows: Array<{
    elements: Array<{
      distance: { text: string; value: number };
      duration: { text: string; value: number };
      status: string;
    }>;
  }>;
}

class GoogleMapsService {
  private api: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    
    this.api = axios.create({
      baseURL: `${this.baseURL}/api/v1/maps`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Handle responses and errors
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          switch (error.response.status) {
            case 401:
              message.error('請重新登入');
              // Redirect to login
              window.location.href = '/login';
              break;
            case 429:
              const retryAfter = error.response.data.retry_after || 60;
              message.warning(`請求過於頻繁，請在 ${retryAfter} 秒後重試`);
              break;
            case 403:
              message.error('您沒有權限執行此操作');
              break;
            default:
              message.error('地圖服務暫時無法使用');
          }
        } else {
          message.error('網絡連接錯誤');
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Geocode an address to coordinates
   */
  async geocode(address: string): Promise<GeocodeResult | null> {
    try {
      const response = await this.api.get('/geocode', {
        params: {
          address,
          language: 'zh-TW',
          region: 'TW',
        },
      });

      if (response.data.results && response.data.results.length > 0) {
        return response.data.results[0];
      }

      message.warning('找不到該地址');
      return null;
    } catch (error) {
      console.error('Geocoding error:', error);
      return null;
    }
  }

  /**
   * Get directions between locations
   */
  async getDirections(
    origin: string | { lat: number; lng: number },
    destination: string | { lat: number; lng: number },
    waypoints?: Array<string | { lat: number; lng: number }>
  ): Promise<DirectionsResult | null> {
    try {
      const formatLocation = (loc: string | { lat: number; lng: number }) => {
        if (typeof loc === 'string') {
          return loc;
        }
        return `${loc.lat},${loc.lng}`;
      };

      const params: any = {
        origin: formatLocation(origin),
        destination: formatLocation(destination),
        mode: 'driving',
        language: 'zh-TW',
      };

      if (waypoints && waypoints.length > 0) {
        params.waypoints = waypoints.map(formatLocation).join('|');
      }

      const response = await this.api.get('/directions', { params });

      if (response.data.routes && response.data.routes.length > 0) {
        return response.data;
      }

      message.warning('找不到路線');
      return null;
    } catch (error) {
      console.error('Directions error:', error);
      return null;
    }
  }

  /**
   * Search for nearby places
   */
  async searchNearby(
    location: { lat: number; lng: number },
    radius: number = 1000,
    type?: string,
    keyword?: string
  ): Promise<PlaceResult[]> {
    try {
      const params: any = {
        location: `${location.lat},${location.lng}`,
        radius,
        language: 'zh-TW',
      };

      if (type) {
        params.type = type;
      }

      if (keyword) {
        params.keyword = keyword;
      }

      const response = await this.api.get('/places/nearby', { params });

      if (response.data.results) {
        return response.data.results;
      }

      return [];
    } catch (error) {
      console.error('Places search error:', error);
      return [];
    }
  }

  /**
   * Calculate distance matrix between multiple points
   */
  async getDistanceMatrix(
    origins: Array<string | { lat: number; lng: number }>,
    destinations: Array<string | { lat: number; lng: number }>
  ): Promise<DistanceMatrixResult | null> {
    try {
      const formatLocation = (loc: string | { lat: number; lng: number }) => {
        if (typeof loc === 'string') {
          return loc;
        }
        return `${loc.lat},${loc.lng}`;
      };

      const params = {
        origins: origins.map(formatLocation).join('|'),
        destinations: destinations.map(formatLocation).join('|'),
        mode: 'driving',
        language: 'zh-TW',
      };

      const response = await this.api.get('/distance-matrix', { params });

      if (response.data.rows) {
        return response.data;
      }

      return null;
    } catch (error) {
      console.error('Distance matrix error:', error);
      return null;
    }
  }

  /**
   * Get static map URL (for image display)
   * Note: This generates a URL that the backend will proxy
   */
  getStaticMapUrl(
    center: { lat: number; lng: number },
    zoom: number = 15,
    size: { width: number; height: number } = { width: 600, height: 400 },
    markers?: Array<{ lat: number; lng: number; label?: string }>
  ): string {
    const params = new URLSearchParams({
      center: `${center.lat},${center.lng}`,
      zoom: zoom.toString(),
      size: `${size.width}x${size.height}`,
      language: 'zh-TW',
    });

    if (markers && markers.length > 0) {
      const markerStrings = markers.map(m => {
        if (m.label) {
          return `label:${m.label}|${m.lat},${m.lng}`;
        }
        return `${m.lat},${m.lng}`;
      });
      params.append('markers', markerStrings.join('|'));
    }

    return `${this.baseURL}/api/v1/maps/static?${params.toString()}`;
  }

  /**
   * Calculate optimal route for multiple stops
   * This is a higher-level function that uses directions API
   */
  async optimizeRoute(
    depot: { lat: number; lng: number },
    stops: Array<{
      id: string;
      location: { lat: number; lng: number };
      priority?: number;
    }>
  ): Promise<{
    optimizedStops: typeof stops;
    totalDistance: number;
    totalDuration: number;
    polyline: string;
  } | null> {
    try {
      // For now, use a simple nearest neighbor algorithm
      // In production, this would call a specialized optimization endpoint
      
      const optimizedStops: typeof stops = [];
      const remaining = [...stops];
      let currentLocation = depot;
      let totalDistance = 0;
      let totalDuration = 0;

      // Sort by priority first if available
      remaining.sort((a, b) => (b.priority || 0) - (a.priority || 0));

      while (remaining.length > 0) {
        // Find nearest stop
        let nearestIndex = 0;
        let nearestDistance = Infinity;

        for (let i = 0; i < remaining.length; i++) {
          const distance = this.calculateDistance(
            currentLocation,
            remaining[i].location
          );
          if (distance < nearestDistance) {
            nearestDistance = distance;
            nearestIndex = i;
          }
        }

        const nextStop = remaining.splice(nearestIndex, 1)[0];
        optimizedStops.push(nextStop);
        currentLocation = nextStop.location;
      }

      // Get actual route
      const waypoints = optimizedStops.map(s => s.location);
      const directions = await this.getDirections(depot, depot, waypoints);

      if (directions && directions.routes.length > 0) {
        const route = directions.routes[0];
        
        // Calculate totals
        for (const leg of route.legs) {
          totalDistance += leg.distance.value;
          totalDuration += leg.duration.value;
        }

        return {
          optimizedStops,
          totalDistance: totalDistance / 1000, // Convert to km
          totalDuration: totalDuration / 60, // Convert to minutes
          polyline: route.overview_polyline.points,
        };
      }

      return null;
    } catch (error) {
      console.error('Route optimization error:', error);
      return null;
    }
  }

  /**
   * Calculate straight-line distance between two points (Haversine formula)
   */
  private calculateDistance(
    point1: { lat: number; lng: number },
    point2: { lat: number; lng: number }
  ): number {
    const R = 6371; // Earth's radius in km
    const dLat = this.toRad(point2.lat - point1.lat);
    const dLng = this.toRad(point2.lng - point1.lng);
    
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(point1.lat)) *
      Math.cos(this.toRad(point2.lat)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
  }

  private toRad(value: number): number {
    return (value * Math.PI) / 180;
  }
}

// Export singleton instance
export const mapsService = new GoogleMapsService();

// Export class for testing
export default GoogleMapsService;