import { offlineStorage } from './offlineStorage';
import { routeService } from '../route.service';
import { orderService } from '../order.service';

export interface SyncOperation {
  type: 'delivery_completion' | 'location_update' | 'route_status' | 'order_update';
  data: any;
  priority?: 'high' | 'normal' | 'low';
  conflictResolution?: 'last-write-wins' | 'manual-review';
}

export interface SyncResult {
  success: boolean;
  error?: string;
  conflictDetected?: boolean;
  conflictData?: any;
}

export interface SyncProgress {
  total: number;
  completed: number;
  failed: number;
  inProgress: boolean;
  lastSyncTime?: number;
}

type SyncProgressCallback = (progress: SyncProgress) => void;

class SyncQueueManager {
  private static instance: SyncQueueManager;
  private syncing = false;
  private syncTimer: NodeJS.Timeout | null = null;
  private progressCallbacks: Set<SyncProgressCallback> = new Set();
  private retryDelays = [1000, 5000, 15000, 30000, 60000]; // Exponential backoff
  
  private constructor() {
    // Initialize sync on online status change
    window.addEventListener('online', () => this.startSync());
    window.addEventListener('offline', () => this.stopSync());
    
    // Start sync if online
    if (navigator.onLine) {
      this.startSync();
    }
  }
  
  static getInstance(): SyncQueueManager {
    if (!SyncQueueManager.instance) {
      SyncQueueManager.instance = new SyncQueueManager();
    }
    return SyncQueueManager.instance;
  }
  
  // Add operation to sync queue
  async addToQueue(operation: SyncOperation): Promise<void> {
    await offlineStorage.addToSyncQueue({
      type: operation.type,
      data: operation.data,
      timestamp: Date.now(),
      retries: 0,
      priority: operation.priority || 'normal',
    });
    
    // Trigger sync if online
    if (navigator.onLine && !this.syncing) {
      this.startSync();
    }
  }
  
  // Subscribe to sync progress updates
  onProgress(callback: SyncProgressCallback): () => void {
    this.progressCallbacks.add(callback);
    return () => this.progressCallbacks.delete(callback);
  }
  
  // Notify progress callbacks
  private notifyProgress(progress: SyncProgress): void {
    this.progressCallbacks.forEach(cb => cb(progress));
  }
  
  // Start sync process
  async startSync(): Promise<void> {
    if (this.syncing || !navigator.onLine) return;
    
    this.syncing = true;
    await this.processSyncQueue();
    
    // Schedule next sync
    this.syncTimer = setTimeout(() => {
      this.syncing = false;
      this.startSync();
    }, 30000); // Sync every 30 seconds
  }
  
  // Stop sync process
  stopSync(): void {
    this.syncing = false;
    if (this.syncTimer) {
      clearTimeout(this.syncTimer);
      this.syncTimer = null;
    }
  }
  
  // Process sync queue
  private async processSyncQueue(): Promise<void> {
    try {
      const queue = await offlineStorage.getSyncQueue();
      if (queue.length === 0) return;
      
      const progress: SyncProgress = {
        total: queue.length,
        completed: 0,
        failed: 0,
        inProgress: true,
        lastSyncTime: Date.now(),
      };
      
      this.notifyProgress(progress);
      
      for (const item of queue) {
        const result = await this.syncItem(item);
        
        if (result.success) {
          await offlineStorage.removeSyncQueueItem(item.id);
          progress.completed++;
        } else {
          // Handle retry logic
          const newRetries = item.retries + 1;
          const retryDelay = this.getRetryDelay(newRetries);
          
          await offlineStorage.updateSyncQueueItem(item.id, {
            retries: newRetries,
            lastRetry: Date.now(),
            error: result.error,
          });
          
          // Remove if max retries exceeded
          if (newRetries >= this.retryDelays.length) {
            await offlineStorage.removeSyncQueueItem(item.id);
            progress.failed++;
            
            // Store failed operation for manual review if needed
            if (result.conflictDetected) {
              await this.storeConflict(item, result);
            }
          }
        }
        
        this.notifyProgress(progress);
      }
      
      progress.inProgress = false;
      this.notifyProgress(progress);
      
    } catch (error) {
      console.error('Sync queue processing error:', error);
    }
  }
  
  // Sync individual item
  private async syncItem(item: any): Promise<SyncResult> {
    try {
      switch (item.type) {
        case 'delivery_completion':
          return await this.syncDeliveryCompletion(item.data);
          
        case 'location_update':
          return await this.syncLocationUpdate(item.data);
          
        case 'route_status':
          return await this.syncRouteStatus(item.data);
          
        case 'order_update':
          return await this.syncOrderUpdate(item.data);
          
        default:
          return { success: false, error: `Unknown sync type: ${item.type}` };
      }
    } catch (error: any) {
      return { 
        success: false, 
        error: error.message || 'Sync failed',
        conflictDetected: error.status === 409,
        conflictData: error.conflictData,
      };
    }
  }
  
  // Sync delivery completion
  private async syncDeliveryCompletion(data: any): Promise<SyncResult> {
    try {
      const { stopId, orderId, signature, photos, notes, timestamp } = data;
      
      // Check for conflicts (e.g., stop already completed by another driver)
      const currentStop = await routeService.getStop(stopId);
      if (currentStop.is_completed && currentStop.completed_at < timestamp) {
        return {
          success: false,
          conflictDetected: true,
          error: 'Stop already completed',
          conflictData: currentStop,
        };
      }
      
      // Upload photos if any
      let photoUrls: string[] = [];
      if (photos && photos.length > 0) {
        photoUrls = await this.uploadPhotos(orderId, photos);
      }
      
      // Complete the stop
      await routeService.completeStop(stopId, {
        signature,
        photos: photoUrls,
        notes,
        completedAt: timestamp,
      });
      
      // Update order status
      if (orderId) {
        await orderService.updateOrder(orderId, {
          status: 'delivered',
          delivery_notes: notes,
          delivered_at: new Date(timestamp).toISOString(),
        });
      }
      
      // Mark local order as synced
      const localOrderId = `${stopId}-${orderId}`;
      await offlineStorage.markOrderSynced(localOrderId);
      
      return { success: true };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.message,
        conflictDetected: error.status === 409,
      };
    }
  }
  
  // Sync location update
  private async syncLocationUpdate(data: any): Promise<SyncResult> {
    try {
      const { locations } = data;
      
      // Batch upload locations
      if (locations && locations.length > 0) {
        await routeService.updateDriverLocationBatch(locations);
        
        // Mark locations as synced
        const locationIds = locations.map((loc: any) => loc.id);
        await offlineStorage.markLocationsSynced(locationIds);
      }
      
      return { success: true };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }
  
  // Sync route status
  private async syncRouteStatus(data: any): Promise<SyncResult> {
    try {
      const { routeId, status, timestamp } = data;
      
      // Check current route status to avoid conflicts
      const currentRoute = await routeService.getRoute(routeId);
      
      if (status === 'started' && currentRoute.status !== 'planned') {
        return {
          success: false,
          conflictDetected: true,
          error: 'Route already started',
          conflictData: currentRoute,
        };
      }
      
      if (status === 'started') {
        await routeService.startRoute(routeId);
      } else if (status === 'completed') {
        await routeService.completeRoute(routeId);
      }
      
      return { success: true };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.message,
        conflictDetected: error.status === 409,
      };
    }
  }
  
  // Sync order update
  private async syncOrderUpdate(data: any): Promise<SyncResult> {
    try {
      const { orderId, updates, timestamp } = data;
      
      // Apply last-write-wins strategy
      const currentOrder = await orderService.getOrder(orderId);
      if (currentOrder.updated_at && new Date(currentOrder.updated_at) > new Date(timestamp)) {
        return {
          success: false,
          conflictDetected: true,
          error: 'Order has newer updates',
          conflictData: currentOrder,
        };
      }
      
      await orderService.updateOrder(orderId, updates);
      return { success: true };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.message,
        conflictDetected: error.status === 409,
      };
    }
  }
  
  // Upload photos
  private async uploadPhotos(orderId: string, photoIds: string[]): Promise<string[]> {
    const uploadedUrls: string[] = [];
    
    for (const photoId of photoIds) {
      const photos = await offlineStorage.getPhotosByOrder(orderId);
      const photo = photos.find(p => p.id === photoId);
      
      if (photo) {
        // Convert blob to base64 or upload to server
        const formData = new FormData();
        formData.append('photo', photo.blob, `delivery-${orderId}-${photoId}.jpg`);
        
        try {
          // Assuming there's an upload endpoint
          const response = await fetch('/api/v1/uploads/delivery-photo', {
            method: 'POST',
            body: formData,
          });
          
          if (response.ok) {
            const result = await response.json();
            uploadedUrls.push(result.url);
            
            // Delete local photo after successful upload
            await offlineStorage.deletePhoto(photoId);
          }
        } catch (error) {
          console.error(`Failed to upload photo ${photoId}:`, error);
        }
      }
    }
    
    return uploadedUrls;
  }
  
  // Get retry delay based on retry count
  private getRetryDelay(retries: number): number {
    const index = Math.min(retries, this.retryDelays.length - 1);
    return this.retryDelays[index];
  }
  
  // Store conflict for manual review
  private async storeConflict(item: any, result: SyncResult): Promise<void> {
    // Store conflicts in a separate IndexedDB store or localStorage
    const conflicts = JSON.parse(localStorage.getItem('sync_conflicts') || '[]');
    conflicts.push({
      id: item.id,
      type: item.type,
      data: item.data,
      error: result.error,
      conflictData: result.conflictData,
      timestamp: Date.now(),
    });
    localStorage.setItem('sync_conflicts', JSON.stringify(conflicts));
  }
  
  // Get sync status
  async getSyncStatus(): Promise<{
    queueLength: number;
    isOnline: boolean;
    isSyncing: boolean;
    conflicts: any[];
  }> {
    const queue = await offlineStorage.getSyncQueue();
    const conflicts = JSON.parse(localStorage.getItem('sync_conflicts') || '[]');
    
    return {
      queueLength: queue.length,
      isOnline: navigator.onLine,
      isSyncing: this.syncing,
      conflicts,
    };
  }
  
  // Clear conflicts
  clearConflicts(): void {
    localStorage.removeItem('sync_conflicts');
  }
  
  // Manual sync trigger
  async triggerSync(): Promise<void> {
    if (!navigator.onLine) {
      throw new Error('Cannot sync while offline');
    }
    
    this.stopSync();
    this.syncing = false;
    await this.startSync();
  }
}

// Export singleton instance
export const syncQueue = SyncQueueManager.getInstance();