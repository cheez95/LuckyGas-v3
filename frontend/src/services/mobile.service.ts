import { message } from 'antd';
import i18n from '../utils/i18n';

interface LocationUpdate {
  latitude: number;
  longitude: number;
  accuracy: number;
  timestamp: string;
  batteryLevel?: number;
  speed?: number;
  heading?: number;
}

interface OfflineQueueItem {
  id: string;
  type: 'location' | 'delivery_completion' | 'photo_upload';
  data: any;
  timestamp: string;
  retryCount: number;
}

class MobileService {
  private static instance: MobileService;
  private offlineQueue: OfflineQueueItem[] = [];
  private isOnline: boolean = navigator.onLine;
  private batteryLevel: number = 100;
  private locationWatchId: number | null = null;
  private backgroundLocationInterval: number | null = null;
  private wakeLock: WakeLockSentinel | null = null;
  
  // Service Worker registration for background sync
  private serviceWorkerRegistration: ServiceWorkerRegistration | null = null;

  private constructor() {
    this.initializeOfflineSupport();
    this.initializeBatteryMonitoring();
    this.loadOfflineQueue();
  }

  static getInstance(): MobileService {
    if (!MobileService.instance) {
      MobileService.instance = new MobileService();
    }
    return MobileService.instance;
  }

  // Initialize offline support
  private initializeOfflineSupport() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      message.success(i18n.t('notification.connection.restored'));
      this.processOfflineQueue();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      message.warning(i18n.t('notification.connection.offline'));
    });
  }

  // Initialize battery monitoring
  private async initializeBatteryMonitoring() {
    if ('getBattery' in navigator) {
      try {
        const battery = await (navigator as any).getBattery();
        this.batteryLevel = battery.level * 100;
        
        battery.addEventListener('levelchange', () => {
          this.batteryLevel = battery.level * 100;
          this.adjustTrackingFrequency();
        });
      } catch (error) {
        console.error('Battery API not supported:', error);
      }
    }
  }

  // Register service worker for background sync
  async registerServiceWorker() {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        this.serviceWorkerRegistration = registration;
        // console.log('Service Worker registered for background sync');
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  // Start GPS tracking with battery optimization
  async startLocationTracking(
    onLocationUpdate: (location: LocationUpdate) => void,
    options?: {
      highAccuracy?: boolean;
      backgroundMode?: boolean;
      minInterval?: number;
    }
  ): Promise<boolean> {
    if (!navigator.geolocation) {
      message.error(i18n.t('gps.error.notSupported'));
      return false;
    }

    // Request wake lock for continuous tracking
    if (options?.backgroundMode) {
      await this.requestWakeLock();
    }

    const trackingOptions: PositionOptions = {
      enableHighAccuracy: options?.highAccuracy ?? true,
      timeout: 10000,
      maximumAge: 0,
    };

    // Adjust based on battery level
    if (this.batteryLevel < 20) {
      trackingOptions.enableHighAccuracy = false;
      trackingOptions.maximumAge = 30000; // Use cached position for 30 seconds
    }

    try {
      // Clear existing tracking
      this.stopLocationTracking();

      // Start watching position
      this.locationWatchId = navigator.geolocation.watchPosition(
        (position) => {
          const locationUpdate: LocationUpdate = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            speed: position.coords.speed || undefined,
            heading: position.coords.heading || undefined,
          };

          // Save to offline queue if needed
          if (!this.isOnline) {
            this.addToOfflineQueue('location', locationUpdate);
          }

          onLocationUpdate(locationUpdate);
        },
        (error) => {
          console.error('Location error:', error);
          message.error(`定位錯誤: ${this.getLocationErrorMessage(error.code)}`);
        },
        trackingOptions
      );

      // Setup background tracking interval if requested
      if (options?.backgroundMode) {
        const interval = options.minInterval || this.calculateTrackingInterval();
        this.backgroundLocationInterval = window.setInterval(() => {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              const locationUpdate: LocationUpdate = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy,
                timestamp: new Date().toISOString(),
                batteryLevel: this.batteryLevel,
              };
              
              if (!this.isOnline) {
                this.addToOfflineQueue('location', locationUpdate);
              }
              
              onLocationUpdate(locationUpdate);
            },
            (error) => console.error('Background location error:', error),
            { enableHighAccuracy: false, timeout: 5000 }
          );
        }, interval);
      }

      return true;
    } catch (error) {
      console.error('Failed to start location tracking:', error);
      return false;
    }
  }

  // Stop GPS tracking
  stopLocationTracking() {
    if (this.locationWatchId !== null) {
      navigator.geolocation.clearWatch(this.locationWatchId);
      this.locationWatchId = null;
    }

    if (this.backgroundLocationInterval !== null) {
      clearInterval(this.backgroundLocationInterval);
      this.backgroundLocationInterval = null;
    }

    this.releaseWakeLock();
  }

  // Request wake lock to prevent device sleep
  private async requestWakeLock() {
    if ('wakeLock' in navigator) {
      try {
        this.wakeLock = await navigator.wakeLock.request('screen');
        // console.log('Wake lock acquired');
      } catch (error) {
        console.error('Wake lock request failed:', error);
      }
    }
  }

  // Release wake lock
  private releaseWakeLock() {
    if (this.wakeLock) {
      this.wakeLock.release();
      this.wakeLock = null;
      // console.log('Wake lock released');
    }
  }

  // Calculate tracking interval based on battery and accuracy needs
  private calculateTrackingInterval(): number {
    if (this.batteryLevel < 20) {
      return 60000; // 1 minute
    } else if (this.batteryLevel < 50) {
      return 30000; // 30 seconds
    } else {
      return 15000; // 15 seconds
    }
  }

  // Adjust tracking frequency based on battery
  private adjustTrackingFrequency() {
    if (this.backgroundLocationInterval !== null) {
      clearInterval(this.backgroundLocationInterval);
      const newInterval = this.calculateTrackingInterval();
      // console.log(`Adjusting tracking interval to ${newInterval}ms (battery: ${this.batteryLevel}%)`);
    }
  }

  // Add item to offline queue
  addToOfflineQueue(type: OfflineQueueItem['type'], data: any) {
    const item: OfflineQueueItem = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      data,
      timestamp: new Date().toISOString(),
      retryCount: 0,
    };

    this.offlineQueue.push(item);
    this.saveOfflineQueue();

    // Register for background sync if available
    if (this.serviceWorkerRegistration && 'sync' in this.serviceWorkerRegistration) {
      this.serviceWorkerRegistration.sync.register('offline-sync').catch(console.error);
    }
  }

  // Process offline queue when online
  async processOfflineQueue() {
    if (!this.isOnline || this.offlineQueue.length === 0) return;

    const itemsToProcess = [...this.offlineQueue];
    
    for (const item of itemsToProcess) {
      try {
        await this.processQueueItem(item);
        // Remove from queue on success
        this.offlineQueue = this.offlineQueue.filter(i => i.id !== item.id);
      } catch (error) {
        console.error(`Failed to process offline item ${item.id}:`, error);
        item.retryCount++;
        
        // Remove if too many retries
        if (item.retryCount > 3) {
          this.offlineQueue = this.offlineQueue.filter(i => i.id !== item.id);
        }
      }
    }

    this.saveOfflineQueue();
  }

  // Process individual queue item
  private async processQueueItem(item: OfflineQueueItem) {
    switch (item.type) {
      case 'location':
        // Send location update to server
        const response = await fetch('/api/v1/driver/location', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify(item.data),
        });
        
        if (!response.ok) throw new Error('Failed to sync location');
        break;

      case 'delivery_completion':
        // Sync delivery completion
        const deliveryResponse = await fetch(`/api/v1/deliveries/${item.data.deliveryId}/complete`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify(item.data),
        });
        
        if (!deliveryResponse.ok) throw new Error('Failed to sync delivery');
        break;

      case 'photo_upload':
        // Upload photo
        const formData = new FormData();
        formData.append('photo', item.data.photo);
        formData.append('metadata', JSON.stringify(item.data.metadata));
        
        const photoResponse = await fetch('/api/v1/photos/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: formData,
        });
        
        if (!photoResponse.ok) throw new Error('Failed to upload photo');
        break;
    }
  }

  // Save offline queue to localStorage
  private saveOfflineQueue() {
    try {
      localStorage.setItem('luckygas_offline_queue', JSON.stringify(this.offlineQueue));
    } catch (error) {
      console.error('Failed to save offline queue:', error);
    }
  }

  // Load offline queue from localStorage
  private loadOfflineQueue() {
    try {
      const saved = localStorage.getItem('luckygas_offline_queue');
      if (saved) {
        this.offlineQueue = JSON.parse(saved);
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
    }
  }

  // Get location error message
  private getLocationErrorMessage(code: number): string {
    switch (code) {
      case 1:
        return i18n.t('gps.error.permissionDenied');
      case 2:
        return i18n.t('gps.error.positionUnavailable');
      case 3:
        return i18n.t('gps.error.timeout');
      default:
        return i18n.t('gps.error.unknown');
    }
  }

  // Request notification permission
  async requestNotificationPermission(): Promise<boolean> {
    if (!('Notification' in window)) {
      // console.log('This browser does not support notifications');
      return false;
    }

    if (Notification.permission === 'granted') {
      return true;
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }

    return false;
  }

  // Show push notification
  showNotification(title: string, options?: NotificationOptions) {
    if (Notification.permission === 'granted') {
      const notification = new Notification(title, {
        icon: '/logo192.png',
        badge: '/logo192.png',
        ...options,
      });

      notification.onclick = () => {
        window.focus();
        notification.close();
      };
    }
  }

  // Get current battery level
  getBatteryLevel(): number {
    return this.batteryLevel;
  }

  // Check if online
  isDeviceOnline(): boolean {
    return this.isOnline;
  }

  // Get offline queue count
  getOfflineQueueCount(): number {
    return this.offlineQueue.length;
  }
}

export default MobileService.getInstance();
export type { LocationUpdate, OfflineQueueItem };