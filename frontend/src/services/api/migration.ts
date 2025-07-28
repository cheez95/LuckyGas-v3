import api from '@/services/api';
import { 
  MigrationMetrics, 
  SyncOperation, 
  FeatureFlag, 
  ConflictItem,
  CustomerSelectionRequest,
  CustomerSelectionResponse,
  MigrationStartRequest,
  ConflictResolutionRequest,
  FeatureFlagUpdateRequest
} from '@/types/migration';

/**
 * Migration API service
 */
export const migrationApi = {
  /**
   * Get migration metrics
   */
  getMetrics: async (): Promise<MigrationMetrics> => {
    const response = await api.get('/admin/migration/metrics');
    return response.data;
  },

  /**
   * Get sync operations
   */
  getSyncOperations: async (params?: {
    limit?: number;
    status?: string;
  }): Promise<SyncOperation[]> => {
    const response = await api.get('/admin/migration/sync-operations', { params });
    return response.data;
  },

  /**
   * Get conflicts
   */
  getConflicts: async (limit?: number): Promise<ConflictItem[]> => {
    const response = await api.get('/admin/migration/conflicts', {
      params: { limit }
    });
    return response.data;
  },

  /**
   * Select customers for pilot
   */
  selectCustomers: async (
    criteria: CustomerSelectionRequest
  ): Promise<CustomerSelectionResponse> => {
    const response = await api.post('/admin/migration/select-customers', criteria);
    return response.data;
  },

  /**
   * Start migration
   */
  startMigration: async (
    request: MigrationStartRequest
  ): Promise<{ status: string; customerCount: number }> => {
    const response = await api.post('/admin/migration/start', request);
    return response.data;
  },

  /**
   * Pause sync service
   */
  pauseSync: async (): Promise<{ status: string }> => {
    const response = await api.post('/admin/migration/pause');
    return response.data;
  },

  /**
   * Resume sync service
   */
  resumeSync: async (): Promise<{ status: string }> => {
    const response = await api.post('/admin/migration/resume');
    return response.data;
  },

  /**
   * Rollback all migrations
   */
  rollback: async (): Promise<{ 
    status: string; 
    customerCount: number 
  }> => {
    const response = await api.post('/admin/migration/rollback');
    return response.data;
  },

  /**
   * Resolve a conflict
   */
  resolveConflict: async (
    conflictId: string,
    resolution: ConflictResolutionRequest
  ): Promise<{ status: string; conflictId: string }> => {
    const response = await api.post(
      `/admin/migration/conflicts/${conflictId}/resolve`,
      resolution
    );
    return response.data;
  },

  /**
   * Get all feature flags
   */
  getFeatureFlags: async (): Promise<FeatureFlag[]> => {
    const response = await api.get('/admin/feature-flags');
    return response.data;
  },

  /**
   * Update a feature flag
   */
  updateFeatureFlag: async (
    flagName: string,
    update: FeatureFlagUpdateRequest
  ): Promise<{ status: string; flagName: string }> => {
    const response = await api.put(
      `/admin/feature-flags/${flagName}`,
      update
    );
    return response.data;
  },

  /**
   * Export migration report
   */
  exportReport: async (format: 'json' | 'csv' = 'json'): Promise<Blob> => {
    const response = await api.get('/admin/migration/export', {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  },

  /**
   * Get migration history
   */
  getHistory: async (params?: {
    startDate?: string;
    endDate?: string;
    limit?: number;
  }): Promise<any[]> => {
    const response = await api.get('/admin/migration/history', { params });
    return response.data;
  },

  /**
   * Test sync for a specific customer
   */
  testSync: async (customerId: string): Promise<{
    success: boolean;
    message: string;
    details: any;
  }> => {
    const response = await api.post(`/admin/migration/test-sync/${customerId}`);
    return response.data;
  },

  /**
   * Get real-time sync status via WebSocket
   */
  subscribeSyncStatus: (
    onUpdate: (status: any) => void,
    onError?: (error: any) => void
  ) => {
    // This would connect to WebSocket for real-time updates
    // Implementation depends on your WebSocket setup
    const ws = new WebSocket(`${process.env.REACT_APP_WS_URL}/sync-status`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onUpdate(data);
    };
    
    ws.onerror = (error) => {
      if (onError) {
        onError(error);
      }
    };
    
    return () => {
      ws.close();
    };
  }
};

export default migrationApi;