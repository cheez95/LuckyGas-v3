import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';
import { routeService } from '../services/route.service';
import { orderService } from '../services/order.service';

interface SyncQueueItem {
  id: string;
  type: 'delivery_completion' | 'location_update' | 'route_status';
  data: any;
  timestamp: number;
  retries: number;
}

const SYNC_QUEUE_KEY = 'luckygas_sync_queue';
const MAX_RETRIES = 3;
const SYNC_INTERVAL = 30000; // 30 seconds

export const useOfflineSync = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncQueue, setSyncQueue] = useState<SyncQueueItem[]>([]);
  const [syncPending, setSyncPending] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const syncIntervalRef = useRef<NodeJS.Timeout>();

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      message.success('已連接網路，開始同步資料');
      syncPendingData();
    };

    const handleOffline = () => {
      setIsOnline(false);
      message.warning('網路斷線，資料將在恢復連線後同步');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial check
    setIsOnline(navigator.onLine);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load queue from localStorage
  useEffect(() => {
    const savedQueue = localStorage.getItem(SYNC_QUEUE_KEY);
    if (savedQueue) {
      try {
        const queue = JSON.parse(savedQueue);
        setSyncQueue(queue);
        setSyncPending(queue.length);
      } catch (error) {
        console.error('Failed to load sync queue:', error);
        localStorage.removeItem(SYNC_QUEUE_KEY);
      }
    }
  }, []);

  // Periodic sync when online
  useEffect(() => {
    if (isOnline && syncQueue.length > 0) {
      syncIntervalRef.current = setInterval(() => {
        syncPendingData();
      }, SYNC_INTERVAL);
    }

    return () => {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }
    };
  }, [isOnline, syncQueue.length]);

  // Save queue to localStorage
  const saveQueue = useCallback((queue: SyncQueueItem[]) => {
    try {
      localStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(queue));
      setSyncQueue(queue);
      setSyncPending(queue.length);
    } catch (error) {
      console.error('Failed to save sync queue:', error);
    }
  }, []);

  // Add item to sync queue
  const addToQueue = useCallback((type: SyncQueueItem['type'], data: any) => {
    const item: SyncQueueItem = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      data,
      timestamp: Date.now(),
      retries: 0,
    };

    const newQueue = [...syncQueue, item];
    saveQueue(newQueue);

    // Try to sync immediately if online
    if (isOnline) {
      setTimeout(() => syncPendingData(), 1000);
    }
  }, [syncQueue, isOnline, saveQueue]);

  // Sync specific item
  const syncItem = async (item: SyncQueueItem): Promise<boolean> => {
    try {
      switch (item.type) {
        case 'delivery_completion':
          await syncDeliveryCompletion(item.data);
          break;
          
        case 'location_update':
          await syncLocationUpdate(item.data);
          break;
          
        case 'route_status':
          await syncRouteStatus(item.data);
          break;
          
        default:
          console.warn('Unknown sync type:', item.type);
          return false;
      }
      
      return true;
    } catch (error) {
      console.error(`Sync failed for item ${item.id}:`, error);
      return false;
    }
  };

  // Sync all pending data
  const syncPendingData = useCallback(async () => {
    if (!isOnline || syncQueue.length === 0 || syncing) return;

    setSyncing(true);
    const processed: string[] = [];
    const failed: SyncQueueItem[] = [];
    let successCount = 0;

    for (const item of syncQueue) {
      const success = await syncItem(item);
      
      if (success) {
        processed.push(item.id);
        successCount++;
      } else {
        // Increment retry count
        item.retries++;
        
        // Keep in queue if under retry limit
        if (item.retries < MAX_RETRIES) {
          failed.push(item);
        } else {
          console.error(`Item ${item.id} exceeded max retries, removing from queue`);
        }
      }
    }

    // Update queue with failed items
    const remainingQueue = failed.filter(item => !processed.includes(item.id));
    saveQueue(remainingQueue);

    if (successCount > 0) {
      message.success(`已同步 ${successCount} 筆資料`);
    }

    setSyncing(false);
  }, [isOnline, syncQueue, saveQueue]);

  // Sync delivery completion
  const syncDeliveryCompletion = async (data: any) => {
    const { stopId, signature, photos, notes } = data;
    await routeService.completeStop(stopId, { signature, photos, notes });
  };

  // Sync location update
  const syncLocationUpdate = async (data: any) => {
    const { latitude, longitude, timestamp } = data;
    await routeService.updateDriverLocation({ latitude, longitude, timestamp });
  };

  // Sync route status
  const syncRouteStatus = async (data: any) => {
    const { routeId, status } = data;
    if (status === 'started') {
      await routeService.startRoute(routeId);
    } else if (status === 'completed') {
      await routeService.completeRoute(routeId);
    }
  };

  // Clear sync queue
  const clearQueue = useCallback(() => {
    setSyncQueue([]);
    setSyncPending(0);
    localStorage.removeItem(SYNC_QUEUE_KEY);
    message.info('離線資料已清除');
  }, []);

  // Get queue status
  const getQueueStatus = useCallback(() => {
    const now = Date.now();
    const oldestItem = syncQueue.length > 0 
      ? Math.min(...syncQueue.map(item => item.timestamp))
      : null;
      
    return {
      pendingCount: syncQueue.length,
      oldestItemAge: oldestItem ? now - oldestItem : null,
      failedItems: syncQueue.filter(item => item.retries > 0).length,
    };
  }, [syncQueue]);

  return {
    isOnline,
    syncPending,
    syncing,
    syncQueue,
    addToQueue,
    syncData: syncPendingData,
    clearQueue,
    getQueueStatus,
  };
};