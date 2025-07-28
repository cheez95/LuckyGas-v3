import { openDB, DBSchema, IDBPDatabase } from 'idb';

// IndexedDB schema definition
interface LuckyGasDB extends DBSchema {
  orders: {
    key: string;
    value: {
      id: string;
      orderId: number;
      customerId: number;
      customerName: string;
      customerPhone: string;
      address: string;
      products: Array<{
        productId: number;
        productName: string;
        quantity: number;
        sizeKg: number;
      }>;
      status: 'pending' | 'delivered' | 'failed';
      deliveryNotes?: string;
      signature?: string;
      photos?: string[];
      timestamp: number;
      synced: boolean;
    };
    indexes: { 'by-status': string; 'by-synced': boolean; 'by-timestamp': number };
  };
  syncQueue: {
    key: string;
    value: {
      id: string;
      type: 'delivery_completion' | 'location_update' | 'route_status' | 'order_update';
      data: any;
      timestamp: number;
      retries: number;
      lastRetry?: number;
      error?: string;
      priority: 'high' | 'normal' | 'low';
    };
    indexes: { 'by-timestamp': number; 'by-priority': string; 'by-retries': number };
  };
  locations: {
    key: string;
    value: {
      id: string;
      latitude: number;
      longitude: number;
      accuracy: number;
      timestamp: number;
      synced: boolean;
    };
    indexes: { 'by-timestamp': number; 'by-synced': boolean };
  };
  photos: {
    key: string;
    value: {
      id: string;
      orderId: string;
      blob: Blob;
      mimeType: string;
      size: number;
      timestamp: number;
      synced: boolean;
    };
    indexes: { 'by-order': string; 'by-synced': boolean };
  };
  cache: {
    key: string;
    value: {
      key: string;
      data: any;
      timestamp: number;
      ttl: number;
    };
  };
}

const DB_NAME = 'luckygas-offline';
const DB_VERSION = 1;

// Singleton database instance
let dbInstance: IDBPDatabase<LuckyGasDB> | null = null;

// Storage quota management
const STORAGE_QUOTA_WARNING = 0.8; // Warn at 80% usage
const STORAGE_QUOTA_CRITICAL = 0.95; // Critical at 95% usage

export class OfflineStorage {
  private static instance: OfflineStorage;
  private db: IDBPDatabase<LuckyGasDB> | null = null;

  private constructor() {}

  static getInstance(): OfflineStorage {
    if (!OfflineStorage.instance) {
      OfflineStorage.instance = new OfflineStorage();
    }
    return OfflineStorage.instance;
  }

  async initialize(): Promise<void> {
    if (this.db) return;

    try {
      this.db = await openDB<LuckyGasDB>(DB_NAME, DB_VERSION, {
        upgrade(db, oldVersion, newVersion) {
          // Orders store
          if (!db.objectStoreNames.contains('orders')) {
            const orderStore = db.createObjectStore('orders', { keyPath: 'id' });
            orderStore.createIndex('by-status', 'status');
            orderStore.createIndex('by-synced', 'synced');
            orderStore.createIndex('by-timestamp', 'timestamp');
          }

          // Sync queue store
          if (!db.objectStoreNames.contains('syncQueue')) {
            const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id' });
            syncStore.createIndex('by-timestamp', 'timestamp');
            syncStore.createIndex('by-priority', 'priority');
            syncStore.createIndex('by-retries', 'retries');
          }

          // Locations store
          if (!db.objectStoreNames.contains('locations')) {
            const locationStore = db.createObjectStore('locations', { keyPath: 'id' });
            locationStore.createIndex('by-timestamp', 'timestamp');
            locationStore.createIndex('by-synced', 'synced');
          }

          // Photos store
          if (!db.objectStoreNames.contains('photos')) {
            const photoStore = db.createObjectStore('photos', { keyPath: 'id' });
            photoStore.createIndex('by-order', 'orderId');
            photoStore.createIndex('by-synced', 'synced');
          }

          // Cache store
          if (!db.objectStoreNames.contains('cache')) {
            db.createObjectStore('cache', { keyPath: 'key' });
          }
        },
      });

      dbInstance = this.db;
      console.log('IndexedDB initialized successfully');
    } catch (error) {
      console.error('Failed to initialize IndexedDB:', error);
      throw error;
    }
  }

  private async getDB(): Promise<IDBPDatabase<LuckyGasDB>> {
    if (!this.db) {
      await this.initialize();
    }
    if (!this.db) {
      throw new Error('Database not initialized');
    }
    return this.db;
  }

  // Storage quota management
  async checkStorageQuota(): Promise<{
    usage: number;
    quota: number;
    percentage: number;
    status: 'ok' | 'warning' | 'critical';
  }> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      const usage = estimate.usage || 0;
      const quota = estimate.quota || 0;
      const percentage = quota > 0 ? usage / quota : 0;

      let status: 'ok' | 'warning' | 'critical' = 'ok';
      if (percentage >= STORAGE_QUOTA_CRITICAL) {
        status = 'critical';
      } else if (percentage >= STORAGE_QUOTA_WARNING) {
        status = 'warning';
      }

      return { usage, quota, percentage, status };
    }

    return { usage: 0, quota: 0, percentage: 0, status: 'ok' };
  }

  // Order operations
  async saveOrder(order: LuckyGasDB['orders']['value']): Promise<void> {
    const db = await this.getDB();
    await db.put('orders', order);
  }

  async getOrder(id: string): Promise<LuckyGasDB['orders']['value'] | undefined> {
    const db = await this.getDB();
    return db.get('orders', id);
  }

  async getAllOrders(): Promise<LuckyGasDB['orders']['value'][]> {
    const db = await this.getDB();
    return db.getAll('orders');
  }

  async getUnsyncedOrders(): Promise<LuckyGasDB['orders']['value'][]> {
    const db = await this.getDB();
    return db.getAllFromIndex('orders', 'by-synced', false);
  }

  async markOrderSynced(id: string): Promise<void> {
    const db = await this.getDB();
    const order = await db.get('orders', id);
    if (order) {
      order.synced = true;
      await db.put('orders', order);
    }
  }

  async deleteOrder(id: string): Promise<void> {
    const db = await this.getDB();
    await db.delete('orders', id);
  }

  // Sync queue operations
  async addToSyncQueue(item: Omit<LuckyGasDB['syncQueue']['value'], 'id'>): Promise<void> {
    const db = await this.getDB();
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    await db.put('syncQueue', { ...item, id });
  }

  async getSyncQueue(): Promise<LuckyGasDB['syncQueue']['value'][]> {
    const db = await this.getDB();
    const tx = db.transaction('syncQueue', 'readonly');
    const index = tx.store.index('by-priority');
    
    // Get items ordered by priority
    const high = await index.getAll('high');
    const normal = await index.getAll('normal');
    const low = await index.getAll('low');
    
    return [...high, ...normal, ...low];
  }

  async updateSyncQueueItem(id: string, updates: Partial<LuckyGasDB['syncQueue']['value']>): Promise<void> {
    const db = await this.getDB();
    const item = await db.get('syncQueue', id);
    if (item) {
      await db.put('syncQueue', { ...item, ...updates });
    }
  }

  async removeSyncQueueItem(id: string): Promise<void> {
    const db = await this.getDB();
    await db.delete('syncQueue', id);
  }

  // Location operations
  async saveLocation(location: Omit<LuckyGasDB['locations']['value'], 'id'>): Promise<void> {
    const db = await this.getDB();
    const id = `loc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    await db.put('locations', { ...location, id });
  }

  async getUnsyncedLocations(): Promise<LuckyGasDB['locations']['value'][]> {
    const db = await this.getDB();
    return db.getAllFromIndex('locations', 'by-synced', false);
  }

  async markLocationsSynced(ids: string[]): Promise<void> {
    const db = await this.getDB();
    const tx = db.transaction('locations', 'readwrite');
    
    await Promise.all(
      ids.map(async (id) => {
        const location = await tx.store.get(id);
        if (location) {
          location.synced = true;
          await tx.store.put(location);
        }
      })
    );
  }

  // Photo operations
  async savePhoto(photo: Omit<LuckyGasDB['photos']['value'], 'id'>): Promise<string> {
    const db = await this.getDB();
    const id = `photo-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    await db.put('photos', { ...photo, id });
    return id;
  }

  async getPhotosByOrder(orderId: string): Promise<LuckyGasDB['photos']['value'][]> {
    const db = await this.getDB();
    return db.getAllFromIndex('photos', 'by-order', orderId);
  }

  async deletePhoto(id: string): Promise<void> {
    const db = await this.getDB();
    await db.delete('photos', id);
  }

  // Cache operations
  async cacheData(key: string, data: any, ttl: number = 3600000): Promise<void> {
    const db = await this.getDB();
    await db.put('cache', {
      key,
      data,
      timestamp: Date.now(),
      ttl,
    });
  }

  async getCachedData(key: string): Promise<any | null> {
    const db = await this.getDB();
    const cached = await db.get('cache', key);
    
    if (!cached) return null;
    
    const age = Date.now() - cached.timestamp;
    if (age > cached.ttl) {
      await db.delete('cache', key);
      return null;
    }
    
    return cached.data;
  }

  async clearExpiredCache(): Promise<void> {
    const db = await this.getDB();
    const allCache = await db.getAll('cache');
    const now = Date.now();
    
    const tx = db.transaction('cache', 'readwrite');
    await Promise.all(
      allCache
        .filter(item => (now - item.timestamp) > item.ttl)
        .map(item => tx.store.delete(item.key))
    );
  }

  // Cleanup operations
  async cleanupOldData(daysToKeep: number = 7): Promise<void> {
    const db = await this.getDB();
    const cutoffTime = Date.now() - (daysToKeep * 24 * 60 * 60 * 1000);
    
    // Clean up old synced orders
    const oldOrders = await db.getAllFromIndex('orders', 'by-timestamp');
    const tx1 = db.transaction('orders', 'readwrite');
    await Promise.all(
      oldOrders
        .filter(order => order.synced && order.timestamp < cutoffTime)
        .map(order => tx1.store.delete(order.id))
    );
    
    // Clean up old synced locations
    const oldLocations = await db.getAllFromIndex('locations', 'by-timestamp');
    const tx2 = db.transaction('locations', 'readwrite');
    await Promise.all(
      oldLocations
        .filter(loc => loc.synced && loc.timestamp < cutoffTime)
        .map(loc => tx2.store.delete(loc.id))
    );
    
    // Clean up expired cache
    await this.clearExpiredCache();
  }

  // Clear all data
  async clearAllData(): Promise<void> {
    const db = await this.getDB();
    await Promise.all([
      db.clear('orders'),
      db.clear('syncQueue'),
      db.clear('locations'),
      db.clear('photos'),
      db.clear('cache'),
    ]);
  }

  // Close database connection
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// Export singleton instance
export const offlineStorage = OfflineStorage.getInstance();