import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';
import { offlineStorage } from '../services/offline/offlineStorage';
import { syncQueue } from '../services/offline/syncQueue';
import type { SyncProgress } from '../services/offline/syncQueue';

export const useOfflineSync = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncProgress, setSyncProgress] = useState<SyncProgress>({
    total: 0,
    completed: 0,
    failed: 0,
    inProgress: false,
  });
  const [storageQuota, setStorageQuota] = useState<{
    usage: number;
    quota: number;
    percentage: number;
    status: 'ok' | 'warning' | 'critical';
  }>({ usage: 0, quota: 0, percentage: 0, status: 'ok' });
  const checkStorageIntervalRef = useRef<NodeJS.Timeout>();

  // Initialize offline storage
  useEffect(() => {
    offlineStorage.initialize().catch((error) => {
      console.error('Failed to initialize offline storage:', error);
      message.error('離線儲存初始化失敗');
    });
  }, []);

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      message.success('已連接網路，開始同步資料');
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

  // Subscribe to sync progress
  useEffect(() => {
    const unsubscribe = syncQueue.onProgress((progress) => {
      setSyncProgress(progress);
    });

    return unsubscribe;
  }, []);

  // Check storage quota periodically
  useEffect(() => {
    const checkQuota = async () => {
      const quota = await offlineStorage.checkStorageQuota();
      setStorageQuota(quota);
      
      if (quota.status === 'warning') {
        message.warning('儲存空間即將不足，請清理舊資料');
      } else if (quota.status === 'critical') {
        message.error('儲存空間嚴重不足，部分功能可能無法使用');
      }
    };

    checkQuota();
    checkStorageIntervalRef.current = setInterval(checkQuota, 60000); // Check every minute

    return () => {
      if (checkStorageIntervalRef.current) {
        clearInterval(checkStorageIntervalRef.current);
      }
    };
  }, []);

  // Save delivery completion offline
  const saveDeliveryOffline = useCallback(async (stopId: number, orderId: number, data: {
    signature?: string;
    photos?: string[];
    notes?: string;
    customerName?: string;
    customerPhone?: string;
    address?: string;
    products?: any[];
  }) => {
    const orderData = {
      id: `${stopId}-${orderId}`,
      orderId,
      customerId: 0, // Will be filled from server data
      customerName: data.customerName || '',
      customerPhone: data.customerPhone || '',
      address: data.address || '',
      products: data.products || [],
      status: 'delivered' as const,
      deliveryNotes: data.notes,
      signature: data.signature,
      photos: data.photos,
      timestamp: Date.now(),
      synced: false,
    };

    await offlineStorage.saveOrder(orderData);
    
    // Add to sync queue
    await syncQueue.addToQueue({
      type: 'delivery_completion',
      data: {
        stopId,
        orderId,
        signature: data.signature,
        photos: data.photos,
        notes: data.notes,
        timestamp: Date.now(),
      },
      priority: 'high',
    });

    message.success('配送資料已儲存，將在連線後同步');
  }, []);

  // Save location update offline
  const saveLocationOffline = useCallback(async (latitude: number, longitude: number, accuracy: number = 0) => {
    await offlineStorage.saveLocation({
      latitude,
      longitude,
      accuracy,
      timestamp: Date.now(),
      synced: false,
    });

    // Batch location updates (send every 10 locations or 5 minutes)
    const unsyncedLocations = await offlineStorage.getUnsyncedLocations();
    if (unsyncedLocations.length >= 10) {
      await syncQueue.addToQueue({
        type: 'location_update',
        data: {
          locations: unsyncedLocations.map(loc => ({
            id: loc.id,
            latitude: loc.latitude,
            longitude: loc.longitude,
            timestamp: loc.timestamp,
          })),
        },
        priority: 'low',
      });
    }
  }, []);

  // Save route status offline
  const saveRouteStatusOffline = useCallback(async (routeId: number, status: 'started' | 'completed') => {
    await syncQueue.addToQueue({
      type: 'route_status',
      data: {
        routeId,
        status,
        timestamp: Date.now(),
      },
      priority: 'high',
    });

    message.info(`路線狀態已儲存，將在連線後同步`);
  }, []);

  // Save photo offline
  const savePhotoOffline = useCallback(async (orderId: string, blob: Blob, mimeType: string = 'image/jpeg'): Promise<string> => {
    const photoId = await offlineStorage.savePhoto({
      orderId,
      blob,
      mimeType,
      size: blob.size,
      timestamp: Date.now(),
      synced: false,
    });

    return photoId;
  }, []);

  // Get offline orders
  const getOfflineOrders = useCallback(async () => {
    return await offlineStorage.getAllOrders();
  }, []);

  // Get sync status
  const getSyncStatus = useCallback(async () => {
    const status = await syncQueue.getSyncStatus();
    return {
      ...status,
      storageQuota,
    };
  }, [storageQuota]);

  // Trigger manual sync
  const triggerSync = useCallback(async () => {
    if (!isOnline) {
      message.error('無法在離線狀態下進行同步');
      return;
    }

    try {
      await syncQueue.triggerSync();
      message.info('開始手動同步...');
    } catch (error: any) {
      message.error(error.message || '同步失敗');
    }
  }, [isOnline]);

  // Clear all offline data
  const clearOfflineData = useCallback(async () => {
    await offlineStorage.clearAllData();
    syncQueue.clearConflicts();
    message.success('所有離線資料已清除');
  }, []);

  // Clean up old data
  const cleanupOldData = useCallback(async (daysToKeep: number = 7) => {
    await offlineStorage.cleanupOldData(daysToKeep);
    message.info(`已清理 ${daysToKeep} 天前的舊資料`);
  }, []);

  return {
    isOnline,
    syncProgress,
    storageQuota,
    saveDeliveryOffline,
    saveLocationOffline,
    saveRouteStatusOffline,
    savePhotoOffline,
    getOfflineOrders,
    getSyncStatus,
    triggerSync,
    clearOfflineData,
    cleanupOldData,
  };
};