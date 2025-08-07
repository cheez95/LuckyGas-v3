// Offline data synchronization service for Lucky Gas PWA
import { notification } from 'antd';

// IndexedDB configuration
const DB_NAME = 'LuckyGasOffline';
const DB_VERSION = 1;
const STORES = {
  PENDING_SYNC: 'pendingSync',
  CACHED_DATA: 'cachedData',
  OFFLINE_QUEUE: 'offlineQueue',
};

// Sync status types
export enum SyncStatus {
  PENDING = 'pending',
  SYNCING = 'syncing',
  SYNCED = 'synced',
  FAILED = 'failed',
}

// Offline data entry
export interface OfflineEntry {
  id?: number;
  timestamp: string;
  type: 'order' | 'delivery' | 'customer' | 'route';
  action: 'create' | 'update' | 'delete';
  url: string;
  method: string;
  headers: Record<string, string>;
  data: any;
  status: SyncStatus;
  retryCount: number;
  error?: string;
}

// Cached data entry
export interface CachedDataEntry {
  key: string;
  url: string;
  data: any;
  timestamp: string;
  expiresAt: string;
}

class OfflineSyncService {
  private db: IDBDatabase | null = null;
  private syncInProgress = false;
  private syncInterval: NodeJS.Timeout | null = null;
  
  constructor() {
    this.initDB();
    this.setupEventListeners();
    this.startPeriodicSync();
  }
  
  // Initialize IndexedDB
  private async initDB(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      
      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error);
        reject(request.error);
      };
      
      request.onsuccess = () => {
        this.db = request.result;
        console.log('IndexedDB initialized successfully');
        resolve();
      };
      
      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = (event.target as IDBOpenDBRequest).result;
        
        // Create stores if they don't exist
        if (!db.objectStoreNames.contains(STORES.PENDING_SYNC)) {
          const syncStore = db.createObjectStore(STORES.PENDING_SYNC, {
            keyPath: 'id',
            autoIncrement: true,
          });
          syncStore.createIndex('status', 'status', { unique: false });
          syncStore.createIndex('type', 'type', { unique: false });
          syncStore.createIndex('timestamp', 'timestamp', { unique: false });
        }
        
        if (!db.objectStoreNames.contains(STORES.CACHED_DATA)) {
          const cacheStore = db.createObjectStore(STORES.CACHED_DATA, {
            keyPath: 'key',
          });
          cacheStore.createIndex('url', 'url', { unique: false });
          cacheStore.createIndex('expiresAt', 'expiresAt', { unique: false });
        }
        
        if (!db.objectStoreNames.contains(STORES.OFFLINE_QUEUE)) {
          const queueStore = db.createObjectStore(STORES.OFFLINE_QUEUE, {
            keyPath: 'id',
            autoIncrement: true,
          });
          queueStore.createIndex('priority', 'priority', { unique: false });
        }
      };
    });
  }
  
  // Add data to offline sync queue
  async addToSyncQueue(entry: Omit<OfflineEntry, 'id' | 'timestamp' | 'status' | 'retryCount'>): Promise<void> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction([STORES.PENDING_SYNC], 'readwrite');
    const store = transaction.objectStore(STORES.PENDING_SYNC);
    
    const fullEntry: OfflineEntry = {
      ...entry,
      timestamp: new Date().toISOString(),
      status: SyncStatus.PENDING,
      retryCount: 0,
    };
    
    return new Promise((resolve, reject) => {
      const request = store.add(fullEntry);
      
      request.onsuccess = () => {
        console.log('Added to sync queue:', fullEntry);
        
        // Show notification
        notification.info({
          message: '離線模式',
          description: '資料已儲存，將在連線恢復後同步',
          duration: 3,
        });
        
        // Trigger sync if online
        if (navigator.onLine) {
          this.syncPendingData();
        }
        
        resolve();
      };
      
      request.onerror = () => {
        console.error('Failed to add to sync queue:', request.error);
        reject(request.error);
      };
    });
  }
  
  // Get all pending sync entries
  async getPendingSync(): Promise<OfflineEntry[]> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction([STORES.PENDING_SYNC], 'readonly');
    const store = transaction.objectStore(STORES.PENDING_SYNC);
    const index = store.index('status');
    
    return new Promise((resolve, reject) => {
      const request = index.getAll(SyncStatus.PENDING);
      
      request.onsuccess = () => {
        resolve(request.result || []);
      };
      
      request.onerror = () => {
        reject(request.error);
      };
    });
  }
  
  // Update sync entry status
  async updateSyncStatus(id: number, status: SyncStatus, error?: string): Promise<void> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction([STORES.PENDING_SYNC], 'readwrite');
    const store = transaction.objectStore(STORES.PENDING_SYNC);
    
    return new Promise((resolve, reject) => {
      const getRequest = store.get(id);
      
      getRequest.onsuccess = () => {
        const entry = getRequest.result;
        if (entry) {
          entry.status = status;
          if (error) {
            entry.error = error;
          }
          
          const updateRequest = store.put(entry);
          
          updateRequest.onsuccess = () => resolve();
          updateRequest.onerror = () => reject(updateRequest.error);
        } else {
          resolve();
        }
      };
      
      getRequest.onerror = () => reject(getRequest.error);
    });
  }
  
  // Sync pending data
  async syncPendingData(): Promise<void> {
    if (this.syncInProgress || !navigator.onLine) {
      return;
    }
    
    this.syncInProgress = true;
    
    try {
      const pendingEntries = await this.getPendingSync();
      
      if (pendingEntries.length === 0) {
        return;
      }
      
      console.log(`Syncing ${pendingEntries.length} pending entries...`);
      
      let successCount = 0;
      let failureCount = 0;
      
      for (const entry of pendingEntries) {
        try {
          // Update status to syncing
          await this.updateSyncStatus(entry.id!, SyncStatus.SYNCING);
          
          // Make the API request
          const response = await fetch(entry.url, {
            method: entry.method,
            headers: {
              ...entry.headers,
              'X-Offline-Sync': 'true',
              'X-Original-Timestamp': entry.timestamp,
            },
            body: entry.method !== 'GET' ? JSON.stringify(entry.data) : undefined,
          });
          
          if (response.ok) {
            // Mark as synced
            await this.updateSyncStatus(entry.id!, SyncStatus.SYNCED);
            successCount++;
            
            // Remove from queue after successful sync
            await this.removeFromQueue(entry.id!);
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
        } catch (error: any) {
          console.error('Failed to sync entry:', entry, error);
          
          // Increment retry count
          entry.retryCount++;
          
          if (entry.retryCount >= 3) {
            // Mark as failed after max retries
            await this.updateSyncStatus(entry.id!, SyncStatus.FAILED, error.message);
          } else {
            // Reset to pending for retry
            await this.updateSyncStatus(entry.id!, SyncStatus.PENDING, error.message);
          }
          
          failureCount++;
        }
      }
      
      // Show sync result notification
      if (successCount > 0) {
        notification.success({
          message: '同步完成',
          description: `成功同步 ${successCount} 筆資料`,
          duration: 4,
        });
      }
      
      if (failureCount > 0) {
        notification.warning({
          message: '部分同步失敗',
          description: `${failureCount} 筆資料同步失敗，將稍後重試`,
          duration: 4,
        });
      }
    } catch (error) {
      console.error('Sync process failed:', error);
      notification.error({
        message: '同步失敗',
        description: '無法同步離線資料，請稍後再試',
        duration: 4,
      });
    } finally {
      this.syncInProgress = false;
    }
  }
  
  // Remove entry from sync queue
  private async removeFromQueue(id: number): Promise<void> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction([STORES.PENDING_SYNC], 'readwrite');
    const store = transaction.objectStore(STORES.PENDING_SYNC);
    
    return new Promise((resolve, reject) => {
      const request = store.delete(id);
      
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }
  
  // Cache data for offline access
  async cacheData(key: string, url: string, data: any, ttl = 3600000): Promise<void> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction([STORES.CACHED_DATA], 'readwrite');
    const store = transaction.objectStore(STORES.CACHED_DATA);
    
    const entry: CachedDataEntry = {
      key,
      url,
      data,
      timestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + ttl).toISOString(),
    };
    
    return new Promise((resolve, reject) => {
      const request = store.put(entry);
      
      request.onsuccess = () => {
        console.log('Data cached:', key);
        resolve();
      };
      
      request.onerror = () => {
        console.error('Failed to cache data:', request.error);
        reject(request.error);
      };
    });
  }
  
  // Get cached data
  async getCachedData(key: string): Promise<any | null> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction([STORES.CACHED_DATA], 'readonly');
    const store = transaction.objectStore(STORES.CACHED_DATA);
    
    return new Promise((resolve, reject) => {
      const request = store.get(key);
      
      request.onsuccess = () => {
        const entry = request.result;
        
        if (entry) {
          // Check if data has expired
          if (new Date(entry.expiresAt) > new Date()) {
            resolve(entry.data);
          } else {
            // Remove expired data
            this.removeCachedData(key);
            resolve(null);
          }
        } else {
          resolve(null);
        }
      };
      
      request.onerror = () => {
        reject(request.error);
      };
    });
  }
  
  // Remove cached data
  private async removeCachedData(key: string): Promise<void> {
    if (!this.db) {
      return;
    }
    
    const transaction = this.db!.transaction([STORES.CACHED_DATA], 'readwrite');
    const store = transaction.objectStore(STORES.CACHED_DATA);
    store.delete(key);
  }
  
  // Clear all offline data
  async clearAllOfflineData(): Promise<void> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction(
      [STORES.PENDING_SYNC, STORES.CACHED_DATA, STORES.OFFLINE_QUEUE],
      'readwrite'
    );
    
    return new Promise((resolve, reject) => {
      transaction.objectStore(STORES.PENDING_SYNC).clear();
      transaction.objectStore(STORES.CACHED_DATA).clear();
      transaction.objectStore(STORES.OFFLINE_QUEUE).clear();
      
      transaction.oncomplete = () => {
        console.log('All offline data cleared');
        resolve();
      };
      
      transaction.onerror = () => {
        reject(transaction.error);
      };
    });
  }
  
  // Setup event listeners
  private setupEventListeners(): void {
    // Listen for online/offline events
    window.addEventListener('online', () => {
      console.log('Back online - syncing pending data...');
      notification.success({
        message: '已連線',
        description: '網路連線已恢復，正在同步資料...',
        duration: 3,
      });
      this.syncPendingData();
    });
    
    window.addEventListener('offline', () => {
      console.log('Gone offline - data will be synced when connection is restored');
      notification.warning({
        message: '離線模式',
        description: '網路連線已中斷，資料將在連線恢復後同步',
        duration: 0,
      });
    });
    
    // Listen for sync events from service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data.type === 'sync-success') {
          console.log('Sync success notification from service worker:', event.data);
          // Update UI or refresh data as needed
        }
      });
    }
  }
  
  // Start periodic sync
  private startPeriodicSync(): void {
    // Sync every 30 seconds when online
    this.syncInterval = setInterval(() => {
      if (navigator.onLine) {
        this.syncPendingData();
      }
    }, 30000);
  }
  
  // Stop periodic sync
  stopPeriodicSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }
  
  // Get sync statistics
  async getSyncStats(): Promise<{
    pending: number;
    synced: number;
    failed: number;
    cached: number;
  }> {
    if (!this.db) {
      await this.initDB();
    }
    
    const transaction = this.db!.transaction(
      [STORES.PENDING_SYNC, STORES.CACHED_DATA],
      'readonly'
    );
    
    const syncStore = transaction.objectStore(STORES.PENDING_SYNC);
    const cacheStore = transaction.objectStore(STORES.CACHED_DATA);
    
    return new Promise((resolve, reject) => {
      let stats = {
        pending: 0,
        synced: 0,
        failed: 0,
        cached: 0,
      };
      
      // Count sync entries by status
      const pendingRequest = syncStore.index('status').count(SyncStatus.PENDING);
      const syncedRequest = syncStore.index('status').count(SyncStatus.SYNCED);
      const failedRequest = syncStore.index('status').count(SyncStatus.FAILED);
      const cachedRequest = cacheStore.count();
      
      pendingRequest.onsuccess = () => {
        stats.pending = pendingRequest.result;
      };
      
      syncedRequest.onsuccess = () => {
        stats.synced = syncedRequest.result;
      };
      
      failedRequest.onsuccess = () => {
        stats.failed = failedRequest.result;
      };
      
      cachedRequest.onsuccess = () => {
        stats.cached = cachedRequest.result;
      };
      
      transaction.oncomplete = () => {
        resolve(stats);
      };
      
      transaction.onerror = () => {
        reject(transaction.error);
      };
    });
  }
}

// Create singleton instance
export const offlineSync = new OfflineSyncService();

// Export for use in other modules
export default offlineSync;