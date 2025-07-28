import { message } from 'antd';
import i18n from '../utils/i18n';

export interface Position {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: number;
  heading?: number;
  speed?: number;
}

export interface GPSError {
  code: number;
  message: string;
}

class GPSService {
  private watchId: number | null = null;
  private lastPosition: Position | null = null;
  private callbacks: ((position: Position) => void)[] = [];
  private errorCallbacks: ((error: GPSError) => void)[] = [];
  private isTracking = false;

  /**
   * Check if GPS is available
   */
  isAvailable(): boolean {
    return 'geolocation' in navigator;
  }

  /**
   * Get current position once
   */
  async getCurrentPosition(): Promise<Position> {
    if (!this.isAvailable()) {
      throw new Error('Geolocation is not supported by this browser');
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const pos: Position = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined
          };
          this.lastPosition = pos;
          resolve(pos);
        },
        (error) => {
          reject(this.handleError(error));
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      );
    });
  }

  /**
   * Start continuous tracking
   */
  startTracking(callback?: (position: Position) => void, errorCallback?: (error: GPSError) => void): boolean {
    if (!this.isAvailable()) {
      const error = { code: 0, message: 'Geolocation is not supported' };
      if (errorCallback) errorCallback(error);
      return false;
    }

    if (this.isTracking) {
      console.warn('GPS tracking is already active');
      return true;
    }

    if (callback) this.callbacks.push(callback);
    if (errorCallback) this.errorCallbacks.push(errorCallback);

    this.watchId = navigator.geolocation.watchPosition(
      (position) => {
        const pos: Position = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp,
          heading: position.coords.heading || undefined,
          speed: position.coords.speed || undefined
        };
        
        this.lastPosition = pos;
        this.callbacks.forEach(cb => cb(pos));
      },
      (error) => {
        const gpsError = this.handleError(error);
        this.errorCallbacks.forEach(cb => cb(gpsError));
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
        // For better battery life on mobile devices
        distanceFilter: 10 // Only update if moved at least 10 meters
      }
    );

    this.isTracking = true;
    return true;
  }

  /**
   * Stop tracking
   */
  stopTracking(): void {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
      this.isTracking = false;
      this.callbacks = [];
      this.errorCallbacks = [];
    }
  }

  /**
   * Add callback for position updates
   */
  onPositionUpdate(callback: (position: Position) => void): void {
    if (!this.callbacks.includes(callback)) {
      this.callbacks.push(callback);
    }
  }

  /**
   * Remove callback
   */
  removeCallback(callback: (position: Position) => void): void {
    this.callbacks = this.callbacks.filter(cb => cb !== callback);
  }

  /**
   * Get last known position
   */
  getLastPosition(): Position | null {
    return this.lastPosition;
  }

  /**
   * Check if currently tracking
   */
  isCurrentlyTracking(): boolean {
    return this.isTracking;
  }

  /**
   * Calculate distance between two positions (in meters)
   */
  calculateDistance(pos1: Position, pos2: Position): number {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = pos1.latitude * Math.PI / 180;
    const φ2 = pos2.latitude * Math.PI / 180;
    const Δφ = (pos2.latitude - pos1.latitude) * Math.PI / 180;
    const Δλ = (pos2.longitude - pos1.longitude) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
  }

  /**
   * Format position for display
   */
  formatPosition(position: Position): string {
    return `${position.latitude.toFixed(6)}, ${position.longitude.toFixed(6)}`;
  }

  /**
   * Generate Google Maps URL for position
   */
  getGoogleMapsUrl(position: Position): string {
    return `https://www.google.com/maps?q=${position.latitude},${position.longitude}`;
  }

  /**
   * Handle geolocation errors
   */
  private handleError(error: GeolocationPositionError): GPSError {
    let errorMessage: string;
    
    switch (error.code) {
      case error.PERMISSION_DENIED:
        errorMessage = i18n.t('gps.error.permissionDenied');
        message.error(i18n.t('gps.error.permissionDenied'));
        break;
      case error.POSITION_UNAVAILABLE:
        errorMessage = i18n.t('gps.error.positionUnavailable');
        message.error(i18n.t('gps.error.positionUnavailable'));
        break;
      case error.TIMEOUT:
        errorMessage = i18n.t('gps.error.timeout');
        message.warning(i18n.t('gps.error.timeout'));
        break;
      default:
        errorMessage = i18n.t('gps.error.unknown');
        message.error(i18n.t('gps.error.unknown'));
    }

    return {
      code: error.code,
      message: errorMessage
    };
  }
}

// Export singleton instance
export const gpsService = new GPSService();