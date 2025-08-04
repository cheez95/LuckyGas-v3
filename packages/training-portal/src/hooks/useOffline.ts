import { useEffect, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from './useToast';

interface OfflineQueueItem {
  id: string;
  type: 'progress' | 'quiz' | 'achievement';
  data: any;
  timestamp: number;
  retries: number;
}

export function useOffline() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineQueue, setOfflineQueue] = useState<OfflineQueueItem[]>([]);
  const queryClient = useQueryClient();

  // Load offline queue from localStorage
  useEffect(() => {
    const savedQueue = localStorage.getItem('offlineQueue');
    if (savedQueue) {
      setOfflineQueue(JSON.parse(savedQueue));
    }
  }, []);

  // Save offline queue to localStorage
  useEffect(() => {
    if (offlineQueue.length > 0) {
      localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue));
    } else {
      localStorage.removeItem('offlineQueue');
    }
  }, [offlineQueue]);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      toast.success('已恢復網路連線');
      processOfflineQueue();
    };

    const handleOffline = () => {
      setIsOnline(false);
      toast.warning('目前處於離線模式，資料將在恢復連線後同步');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Add item to offline queue
  const addToOfflineQueue = useCallback((type: string, data: any) => {
    const item: OfflineQueueItem = {
      id: `${type}-${Date.now()}-${Math.random()}`,
      type: type as any,
      data,
      timestamp: Date.now(),
      retries: 0,
    };

    setOfflineQueue((prev) => [...prev, item]);
    toast.info('資料已儲存，將在恢復連線後同步');
  }, []);

  // Process offline queue when online
  const processOfflineQueue = useCallback(async () => {
    if (!isOnline || offlineQueue.length === 0) return;

    const queue = [...offlineQueue];
    const failed: OfflineQueueItem[] = [];

    for (const item of queue) {
      try {
        await processQueueItem(item);
        // Remove successful item from queue
        setOfflineQueue((prev) => prev.filter((i) => i.id !== item.id));
      } catch (error) {
        console.error('Failed to process offline item:', error);
        item.retries++;
        if (item.retries < 3) {
          failed.push(item);
        }
      }
    }

    // Re-add failed items to queue
    if (failed.length > 0) {
      setOfflineQueue((prev) => [...prev.filter((i) => !queue.includes(i)), ...failed]);
      toast.warning(`${failed.length} 項資料同步失敗，稍後將重試`);
    } else if (queue.length > 0) {
      toast.success('所有離線資料已成功同步');
      // Invalidate queries to refresh data
      queryClient.invalidateQueries();
    }
  }, [isOnline, offlineQueue, queryClient]);

  // Process individual queue item
  const processQueueItem = async (item: OfflineQueueItem) => {
    switch (item.type) {
      case 'progress':
        // Call API to update progress
        const response = await fetch(`/api/v1/courses/${item.data.courseId}/modules/${item.data.moduleId}/progress`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: JSON.stringify(item.data.progress),
        });
        if (!response.ok) throw new Error('Failed to update progress');
        break;

      case 'quiz':
        // Submit quiz answers
        const quizResponse = await fetch(`/api/v1/quizzes/${item.data.quizId}/submit`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: JSON.stringify(item.data.answers),
        });
        if (!quizResponse.ok) throw new Error('Failed to submit quiz');
        break;

      case 'achievement':
        // Sync achievement data
        // This might be handled differently depending on your API
        break;

      default:
        console.warn('Unknown offline queue item type:', item.type);
    }
  };

  // Manual sync trigger
  const syncOfflineData = useCallback(() => {
    if (isOnline) {
      processOfflineQueue();
    } else {
      toast.error('無法同步：目前處於離線狀態');
    }
  }, [isOnline, processOfflineQueue]);

  // Get offline-capable data
  const getCachedData = useCallback((key: string) => {
    const cached = localStorage.getItem(`offline-${key}`);
    if (cached) {
      return JSON.parse(cached);
    }
    return null;
  }, []);

  // Save data for offline use
  const setCachedData = useCallback((key: string, data: any) => {
    localStorage.setItem(`offline-${key}`, JSON.stringify(data));
  }, []);

  // Download content for offline use
  const downloadForOffline = useCallback(async (courseId: string) => {
    if (!isOnline) {
      toast.error('無法下載：目前處於離線狀態');
      return;
    }

    try {
      toast.info('開始下載課程內容...');

      // Fetch course data
      const courseResponse = await fetch(`/api/v1/courses/${courseId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const courseData = await courseResponse.json();

      // Save course data
      setCachedData(`course-${courseId}`, courseData);

      // Download module content
      for (const module of courseData.modules) {
        const moduleResponse = await fetch(`/api/v1/modules/${module.module_id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        });
        const moduleData = await moduleResponse.json();
        setCachedData(`module-${module.module_id}`, moduleData);

        // Download video if exists (just metadata, not actual video file)
        if (module.content_type === 'video' && module.video_url) {
          // In a real app, you might use service worker to cache video files
          setCachedData(`video-${module.module_id}`, {
            url: module.video_url,
            duration: module.duration_minutes,
          });
        }
      }

      toast.success('課程內容已下載，可在離線時使用');
    } catch (error) {
      console.error('Failed to download course:', error);
      toast.error('下載失敗，請稍後再試');
    }
  }, [isOnline, setCachedData]);

  // Check if content is available offline
  const isAvailableOffline = useCallback((type: string, id: string) => {
    const key = `${type}-${id}`;
    return getCachedData(key) !== null;
  }, [getCachedData]);

  // Clear offline cache
  const clearOfflineCache = useCallback(() => {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith('offline-')) {
        localStorage.removeItem(key);
      }
    });
    toast.success('離線快取已清除');
  }, []);

  // Get offline storage usage
  const getStorageInfo = useCallback(async () => {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return {
        usage: estimate.usage || 0,
        quota: estimate.quota || 0,
        percentage: ((estimate.usage || 0) / (estimate.quota || 1)) * 100,
      };
    }
    return null;
  }, []);

  return {
    isOnline,
    offlineQueue,
    addToOfflineQueue,
    syncOfflineData,
    getCachedData,
    setCachedData,
    downloadForOffline,
    isAvailableOffline,
    clearOfflineCache,
    getStorageInfo,
    pendingCount: offlineQueue.length,
  };
}