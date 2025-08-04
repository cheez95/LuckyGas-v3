import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import NetInfo from '@react-native-community/netinfo';
import { useMMKVObject, useMMKVBoolean } from 'react-native-mmkv';
import Toast from 'react-native-toast-message';

import { offlineService } from '@/services/offline';
import { Course, Module, Progress } from '@/types/training';

interface OfflineData {
  courses: Course[];
  modules: Module[];
  progress: Progress[];
  pendingActions: PendingAction[];
}

interface PendingAction {
  id: string;
  type: 'progress_update' | 'quiz_submission' | 'enrollment';
  data: any;
  timestamp: number;
  retryCount: number;
}

interface OfflineContextType {
  isOffline: boolean;
  isReachable: boolean;
  offlineData: OfflineData | null;
  downloadedCourses: Set<string>;
  downloadCourse: (courseId: string) => Promise<void>;
  removeCourse: (courseId: string) => Promise<void>;
  syncOfflineData: () => Promise<void>;
  getPendingActionsCount: () => number;
  clearPendingActions: () => void;
}

const OfflineContext = createContext<OfflineContextType | undefined>(undefined);

export function OfflineProvider({ children }: { children: ReactNode }) {
  const [isOffline, setIsOffline] = useMMKVBoolean('is_offline');
  const [isReachable, setIsReachable] = useState(true);
  const [offlineData, setOfflineData] = useMMKVObject<OfflineData>('offline_data');
  const [downloadedCourses, setDownloadedCourses] = useMMKVObject<string[]>('downloaded_courses');

  useEffect(() => {
    // Subscribe to network state changes
    const unsubscribe = NetInfo.addEventListener(state => {
      const offline = !state.isConnected;
      const reachable = state.isInternetReachable ?? false;
      
      setIsOffline(offline);
      setIsReachable(reachable);
      
      // Show toast when connection changes
      if (offline) {
        Toast.show({
          type: 'info',
          text1: '離線模式',
          text2: '您現在處於離線模式，部分功能可能受限',
          position: 'bottom',
        });
      } else if (!isOffline && state.isConnected) {
        Toast.show({
          type: 'success',
          text1: '已連線',
          text2: '正在同步離線資料...',
          position: 'bottom',
        });
        
        // Auto-sync when coming back online
        syncOfflineData();
      }
    });

    return () => unsubscribe();
  }, [isOffline]);

  useEffect(() => {
    // Initialize offline data if not exists
    if (!offlineData) {
      setOfflineData({
        courses: [],
        modules: [],
        progress: [],
        pendingActions: [],
      });
    }
  }, []);

  const downloadCourse = async (courseId: string) => {
    try {
      Toast.show({
        type: 'info',
        text1: '開始下載',
        text2: '正在下載課程內容...',
      });

      // Download course data and videos
      const courseData = await offlineService.downloadCourse(courseId);
      
      // Update offline data
      const currentData = offlineData || {
        courses: [],
        modules: [],
        progress: [],
        pendingActions: [],
      };

      setOfflineData({
        ...currentData,
        courses: [...currentData.courses, courseData.course],
        modules: [...currentData.modules, ...courseData.modules],
      });

      // Track downloaded courses
      const currentDownloaded = new Set(downloadedCourses || []);
      currentDownloaded.add(courseId);
      setDownloadedCourses(Array.from(currentDownloaded));

      Toast.show({
        type: 'success',
        text1: '下載完成',
        text2: '課程已可離線使用',
      });
    } catch (error) {
      console.error('Download error:', error);
      Toast.show({
        type: 'error',
        text1: '下載失敗',
        text2: '請檢查網路連線後重試',
      });
    }
  };

  const removeCourse = async (courseId: string) => {
    try {
      // Remove from offline storage
      await offlineService.removeCourse(courseId);

      // Update offline data
      const currentData = offlineData || {
        courses: [],
        modules: [],
        progress: [],
        pendingActions: [],
      };

      setOfflineData({
        ...currentData,
        courses: currentData.courses.filter(c => c.course_id !== courseId),
        modules: currentData.modules.filter(m => m.course_id !== courseId),
      });

      // Update downloaded courses
      const currentDownloaded = new Set(downloadedCourses || []);
      currentDownloaded.delete(courseId);
      setDownloadedCourses(Array.from(currentDownloaded));

      Toast.show({
        type: 'success',
        text1: '刪除成功',
        text2: '已移除離線課程',
      });
    } catch (error) {
      console.error('Remove error:', error);
      Toast.show({
        type: 'error',
        text1: '刪除失敗',
        text2: '請稍後再試',
      });
    }
  };

  const syncOfflineData = async () => {
    if (isOffline || !offlineData?.pendingActions?.length) {
      return;
    }

    try {
      const syncResult = await offlineService.syncPendingActions(
        offlineData.pendingActions
      );

      // Update pending actions based on sync result
      const remainingActions = offlineData.pendingActions.filter(
        action => !syncResult.successful.includes(action.id)
      );

      setOfflineData({
        ...offlineData,
        pendingActions: remainingActions,
      });

      if (syncResult.successful.length > 0) {
        Toast.show({
          type: 'success',
          text1: '同步完成',
          text2: `已同步 ${syncResult.successful.length} 項更新`,
        });
      }

      if (syncResult.failed.length > 0) {
        Toast.show({
          type: 'warning',
          text1: '部分同步失敗',
          text2: `${syncResult.failed.length} 項更新將稍後重試`,
        });
      }
    } catch (error) {
      console.error('Sync error:', error);
      Toast.show({
        type: 'error',
        text1: '同步失敗',
        text2: '請檢查網路連線',
      });
    }
  };

  const getPendingActionsCount = () => {
    return offlineData?.pendingActions?.length || 0;
  };

  const clearPendingActions = () => {
    if (offlineData) {
      setOfflineData({
        ...offlineData,
        pendingActions: [],
      });
    }
  };

  const value: OfflineContextType = {
    isOffline: isOffline || false,
    isReachable,
    offlineData,
    downloadedCourses: new Set(downloadedCourses || []),
    downloadCourse,
    removeCourse,
    syncOfflineData,
    getPendingActionsCount,
    clearPendingActions,
  };

  return (
    <OfflineContext.Provider value={value}>
      {children}
    </OfflineContext.Provider>
  );
}

export function useOffline() {
  const context = useContext(OfflineContext);
  if (context === undefined) {
    throw new Error('useOffline must be used within an OfflineProvider');
  }
  return context;
}