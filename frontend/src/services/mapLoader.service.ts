/**
 * Secure Google Maps Loader Service
 * 
 * This service handles loading the Google Maps JavaScript API securely
 * by fetching the API configuration from the backend, which manages
 * the API key securely server-side.
 */

import axios from 'axios';

export interface MapConfig {
  libraries: string[];
  language: string;
  region: string;
  version: string;
}

class GoogleMapsLoader {
  private static instance: GoogleMapsLoader;
  private loadPromise: Promise<void> | null = null;
  private isLoaded: boolean = false;
  private apiUrl: string;

  private constructor() {
    this.apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  }

  static getInstance(): GoogleMapsLoader {
    if (!GoogleMapsLoader.instance) {
      GoogleMapsLoader.instance = new GoogleMapsLoader();
    }
    return GoogleMapsLoader.instance;
  }

  /**
   * Load Google Maps JavaScript API securely
   * The API key is managed server-side and injected via a secure endpoint
   */
  async load(config?: Partial<MapConfig>): Promise<void> {
    // If already loaded, return immediately
    if (this.isLoaded && window.google?.maps) {
      return Promise.resolve();
    }

    // If currently loading, return the existing promise
    if (this.loadPromise) {
      return this.loadPromise;
    }

    // Start loading
    this.loadPromise = this.loadMapsApi(config);
    
    try {
      await this.loadPromise;
      this.isLoaded = true;
    } catch (error) {
      this.loadPromise = null;
      throw error;
    }

    return this.loadPromise;
  }

  private async loadMapsApi(config?: Partial<MapConfig>): Promise<void> {
    try {
      // Get secure script URL from backend
      const token = localStorage.getItem('authToken');
      const response = await axios.get(`${this.apiUrl}/api/v1/maps/script-url`, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
        params: {
          libraries: config?.libraries?.join(',') || 'places,drawing,geometry',
          language: config?.language || 'zh-TW',
          region: config?.region || 'TW',
          version: config?.version || 'weekly',
        },
      });

      const scriptUrl = response.data.url;

      // Create and load script
      return new Promise((resolve, reject) => {
        // Check if already loaded
        if (window.google?.maps) {
          resolve();
          return;
        }

        const script = document.createElement('script');
        script.src = scriptUrl;
        script.async = true;
        script.defer = true;
        
        script.onload = () => {
          if (window.google?.maps) {
            resolve();
          } else {
            reject(new Error('Google Maps failed to load'));
          }
        };

        script.onerror = () => {
          reject(new Error('Failed to load Google Maps script'));
        };

        document.head.appendChild(script);
      });
    } catch (error) {
      console.error('Failed to get Maps script URL:', error);
      throw new Error('無法載入地圖服務，請稍後再試');
    }
  }

  /**
   * Check if Google Maps is loaded
   */
  isGoogleMapsLoaded(): boolean {
    return this.isLoaded && !!window.google?.maps;
  }

  /**
   * Wait for Google Maps to be available
   */
  async waitForGoogleMaps(timeout: number = 10000): Promise<void> {
    const startTime = Date.now();
    
    while (!this.isGoogleMapsLoaded()) {
      if (Date.now() - startTime > timeout) {
        throw new Error('Timeout waiting for Google Maps to load');
      }
      
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  /**
   * Create a new map instance
   */
  async createMap(
    element: HTMLElement,
    options: google.maps.MapOptions
  ): Promise<google.maps.Map> {
    await this.load();
    return new window.google.maps.Map(element, options);
  }

  /**
   * Create a marker
   */
  async createMarker(
    options: google.maps.MarkerOptions
  ): Promise<google.maps.Marker> {
    await this.load();
    return new window.google.maps.Marker(options);
  }

  /**
   * Create a polyline
   */
  async createPolyline(
    options: google.maps.PolylineOptions
  ): Promise<google.maps.Polyline> {
    await this.load();
    return new window.google.maps.Polyline(options);
  }

  /**
   * Create an info window
   */
  async createInfoWindow(
    options?: google.maps.InfoWindowOptions
  ): Promise<google.maps.InfoWindow> {
    await this.load();
    return new window.google.maps.InfoWindow(options);
  }

  /**
   * Create bounds
   */
  async createBounds(): Promise<google.maps.LatLngBounds> {
    await this.load();
    return new window.google.maps.LatLngBounds();
  }

  /**
   * Create a LatLng object
   */
  async createLatLng(lat: number, lng: number): Promise<google.maps.LatLng> {
    await this.load();
    return new window.google.maps.LatLng(lat, lng);
  }

  /**
   * Get directions service
   */
  async getDirectionsService(): Promise<google.maps.DirectionsService> {
    await this.load();
    return new window.google.maps.DirectionsService();
  }

  /**
   * Get directions renderer
   */
  async getDirectionsRenderer(
    options?: google.maps.DirectionsRendererOptions
  ): Promise<google.maps.DirectionsRenderer> {
    await this.load();
    return new window.google.maps.DirectionsRenderer(options);
  }

  /**
   * Get places service
   */
  async getPlacesService(map: google.maps.Map): Promise<google.maps.places.PlacesService> {
    await this.load();
    return new window.google.maps.places.PlacesService(map);
  }

  /**
   * Get geocoder
   */
  async getGeocoder(): Promise<google.maps.Geocoder> {
    await this.load();
    return new window.google.maps.Geocoder();
  }
}

// Export singleton instance
export const mapsLoader = GoogleMapsLoader.getInstance();

// Export class for testing
export default GoogleMapsLoader;