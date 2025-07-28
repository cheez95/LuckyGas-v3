/**
 * Migration-related type definitions
 */

export interface MigrationMetrics {
  totalCustomers: number;
  migratedCustomers: number;
  pendingCustomers: number;
  failedCustomers: number;
  successRate: number;
  averageSyncTime: number;
  lastSyncAt: string | null;
  estimatedCompletion: string | null;
}

export interface SyncOperation {
  id: string;
  entityType: string;
  entityId: string;
  direction: 'to_legacy' | 'from_legacy' | 'bidirectional';
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'conflict';
  createdAt: string;
  completedAt?: string;
  errorMessage?: string;
  retryCount: number;
}

export interface FeatureFlag {
  name: string;
  description: string;
  type: 'boolean' | 'percentage' | 'variant' | 'customer_list';
  status: 'active' | 'inactive' | 'scheduled';
  percentage?: number;
  enabledCustomers?: number;
  variants?: VariantConfig[];
  defaultVariant?: string;
  createdAt: string;
  updatedAt: string;
}

export interface VariantConfig {
  name: string;
  percentage: number;
  config: Record<string, any>;
}

export interface ConflictItem {
  id: string;
  entityType: string;
  entityId: string;
  customerName?: string;
  conflictType: string;
  detectedAt: string;
  newValue: any;
  legacyValue: any;
}

export interface CustomerSelectionRequest {
  percentage: number;
  minOrderCount?: number;
  region?: string;
  customerType?: 'residential' | 'commercial' | 'restaurant';
}

export interface CustomerSelectionResponse {
  customerIds: string[];
  count: number;
}

export interface MigrationStartRequest {
  customerIds: string[];
  batchSize?: number;
}

export type ConflictResolution = 
  | 'newest_wins' 
  | 'legacy_wins' 
  | 'new_system_wins' 
  | 'manual';

export interface ConflictResolutionRequest {
  resolution: ConflictResolution;
  resolvedData?: any;
}

export interface FeatureFlagUpdateRequest {
  status?: string;
  percentage?: number;
  enabledCustomers?: string[];
}

export interface MigrationHistory {
  id: string;
  timestamp: string;
  action: string;
  entityType: string;
  entityId: string;
  userId: string;
  userName: string;
  details: Record<string, any>;
  success: boolean;
  errorMessage?: string;
}

export interface SyncMetrics {
  totalSynced: number;
  successful: number;
  failed: number;
  conflicts: number;
  averageSyncTimeMs: number;
  lastSyncAt?: string;
}

export interface PilotProgramStats {
  totalPilotCustomers: number;
  activeCustomers: number;
  totalOrders: number;
  totalRevenue: number;
  averageOrderValue: number;
  satisfactionScore: number;
  issuesReported: number;
  issuesResolved: number;
}

export interface MigrationConfig {
  syncEnabled: boolean;
  batchSize: number;
  retryLimit: number;
  conflictResolution: ConflictResolution;
  autoRollbackThreshold: number;
  notificationSettings: {
    onSuccess: boolean;
    onFailure: boolean;
    onConflict: boolean;
    webhookUrl?: string;
  };
}