import React, { useState, useEffect } from 'react';
import { Badge, Button, Card, Progress, Space, Tag, Tooltip, Typography, Modal, List, Statistic } from 'antd';
import {
  WifiOutlined,
  DisconnectOutlined,
  SyncOutlined,
  CloudSyncOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { syncQueue } from '../../services/offline/syncQueue';
import { offlineStorage } from '../../services/offline/offlineStorage';
import type { SyncProgress } from '../../services/offline/syncQueue';

const { Text, Title } = Typography;

interface OfflineIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({ className, showDetails = true }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncProgress, setSyncProgress] = useState<SyncProgress>({
    total: 0,
    completed: 0,
    failed: 0,
    inProgress: false,
  });
  const [storageStatus, setStorageStatus] = useState<{
    usage: number;
    quota: number;
    percentage: number;
    status: 'ok' | 'warning' | 'critical';
  }>({ usage: 0, quota: 0, percentage: 0, status: 'ok' });
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [lastSyncTime, setLastSyncTime] = useState<number | null>(null);

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Subscribe to sync progress
  useEffect(() => {
    const unsubscribe = syncQueue.onProgress((progress) => {
      setSyncProgress(progress);
      if (progress.lastSyncTime) {
        setLastSyncTime(progress.lastSyncTime);
      }
    });

    return unsubscribe;
  }, []);

  // Check storage status periodically
  useEffect(() => {
    const checkStorage = async () => {
      const status = await offlineStorage.checkStorageQuota();
      setStorageStatus(status);
    };

    checkStorage();
    const interval = window.setInterval(checkStorage, 60000); // Check every minute

    return () => window.clearInterval(interval);
  }, []);

  // Load sync status
  useEffect(() => {
    const loadSyncStatus = async () => {
      const status = await syncQueue.getSyncStatus();
      setSyncProgress({
        total: status.queueLength,
        completed: 0,
        failed: 0,
        inProgress: status.isSyncing,
      });
      setConflicts(status.conflicts);
    };

    loadSyncStatus();
  }, []);

  // Handle manual sync
  const handleManualSync = async () => {
    try {
      await syncQueue.triggerSync();
    } catch (error: any) {
      Modal.error({
        title: '同步失敗',
        content: error.message || '無法進行同步，請檢查網路連線',
      });
    }
  };

  // Handle conflict resolution
  const handleResolveConflict = (conflict: any) => {
    Modal.confirm({
      title: '解決衝突',
      content: `此資料與伺服器版本有衝突，要使用本地版本覆蓋嗎？`,
      okText: '使用本地版本',
      cancelText: '保留伺服器版本',
      onOk: async () => {
        // Re-add to sync queue with force flag
        await syncQueue.addToQueue({
          type: conflict.type,
          data: { ...conflict.data, forceOverwrite: true },
          priority: 'high',
        });
        
        // Remove from conflicts
        syncQueue.clearConflicts();
        setConflicts([]);
      },
      onCancel: () => {
        // Remove from conflicts without re-syncing
        syncQueue.clearConflicts();
        setConflicts([]);
      },
    });
  };

  // Format time ago
  const formatTimeAgo = (timestamp: number): string => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    
    if (seconds < 60) return `${seconds} 秒前`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} 分鐘前`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小時前`;
    return `${Math.floor(seconds / 86400)} 天前`;
  };

  // Get status color
  const getStatusColor = () => {
    if (!isOnline) return 'error';
    if (syncProgress.inProgress) return 'processing';
    if (syncProgress.failed > 0 || conflicts.length > 0) return 'warning';
    if (syncProgress.total > 0) return 'default';
    return 'success';
  };

  // Get status icon
  const getStatusIcon = () => {
    if (!isOnline) return <DisconnectOutlined />;
    if (syncProgress.inProgress) return <SyncOutlined spin />;
    if (syncProgress.failed > 0 || conflicts.length > 0) return <ExclamationCircleOutlined />;
    if (syncProgress.total > 0) return <ClockCircleOutlined />;
    return <WifiOutlined />;
  };

  // Get status text
  const getStatusText = () => {
    if (!isOnline) return '離線模式';
    if (syncProgress.inProgress) return '同步中...';
    if (syncProgress.failed > 0 || conflicts.length > 0) return '同步錯誤';
    if (syncProgress.total > 0) return `${syncProgress.total} 筆待同步`;
    return '已同步';
  };

  // Render compact indicator
  if (!showDetails) {
    return (
      <Tooltip
        title={
          <Space direction="vertical" size="small">
            <Text style={{ color: 'white' }}>{getStatusText()}</Text>
            {lastSyncTime && (
              <Text style={{ color: 'white', fontSize: 12 }}>
                最後同步: {formatTimeAgo(lastSyncTime)}
              </Text>
            )}
          </Space>
        }
      >
        <Badge
          count={syncProgress.total}
          showZero={false}
          offset={[-5, 5]}
        >
          <Tag
            color={getStatusColor()}
            icon={getStatusIcon()}
            className={className}
            style={{ cursor: 'pointer' }}
            onClick={() => setDetailsModalVisible(true)}
          >
            {getStatusText()}
          </Tag>
        </Badge>
      </Tooltip>
    );
  }

  // Render full indicator
  return (
    <>
      <Card
        size="small"
        className={className}
        title={
          <Space>
            {getStatusIcon()}
            <Text strong>{getStatusText()}</Text>
          </Space>
        }
        extra={
          <Button
            type="text"
            size="small"
            icon={<CloudSyncOutlined />}
            onClick={handleManualSync}
            disabled={!isOnline || syncProgress.inProgress}
          >
            手動同步
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* Sync Progress */}
          {syncProgress.total > 0 && (
            <div>
              <Text type="secondary">同步進度</Text>
              <Progress
                percent={
                  syncProgress.total > 0
                    ? Math.round((syncProgress.completed / syncProgress.total) * 100)
                    : 0
                }
                status={syncProgress.failed > 0 ? 'exception' : 'active'}
                format={() => `${syncProgress.completed} / ${syncProgress.total}`}
              />
            </div>
          )}

          {/* Storage Status */}
          <div>
            <Space>
              <DatabaseOutlined />
              <Text type="secondary">儲存空間</Text>
              {storageStatus.status === 'warning' && (
                <Tag color="warning" icon={<WarningOutlined />}>
                  空間不足
                </Tag>
              )}
            </Space>
            <Progress
              percent={Math.round(storageStatus.percentage * 100)}
              status={
                storageStatus.status === 'critical'
                  ? 'exception'
                  : storageStatus.status === 'warning'
                  ? 'exception'
                  : 'normal'
              }
              format={() =>
                `${(storageStatus.usage / 1024 / 1024).toFixed(1)} / ${(
                  storageStatus.quota /
                  1024 /
                  1024
                ).toFixed(1)} MB`
              }
            />
          </div>

          {/* Last Sync Time */}
          {lastSyncTime && (
            <Space>
              <ClockCircleOutlined />
              <Text type="secondary">最後同步時間:</Text>
              <Text>{formatTimeAgo(lastSyncTime)}</Text>
            </Space>
          )}

          {/* Conflicts Alert */}
          {conflicts.length > 0 && (
            <Button
              type="link"
              danger
              icon={<ExclamationCircleOutlined />}
              onClick={() => setDetailsModalVisible(true)}
            >
              {conflicts.length} 筆資料衝突需要處理
            </Button>
          )}
        </Space>
      </Card>

      {/* Details Modal */}
      <Modal
        title="離線同步詳情"
        open={detailsModalVisible}
        onCancel={() => setDetailsModalVisible(false)}
        footer={null}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Statistics */}
          <Card size="small">
            <Space style={{ width: '100%', justifyContent: 'space-around' }}>
              <Statistic
                title="待同步"
                value={syncProgress.total}
                prefix={<ClockCircleOutlined />}
              />
              <Statistic
                title="已完成"
                value={syncProgress.completed}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
              <Statistic
                title="失敗"
                value={syncProgress.failed}
                prefix={<ExclamationCircleOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Space>
          </Card>

          {/* Conflicts List */}
          {conflicts.length > 0 && (
            <div>
              <Title level={5}>資料衝突</Title>
              <List
                dataSource={conflicts}
                renderItem={(conflict) => (
                  <List.Item
                    actions={[
                      <Button
                        type="link"
                        onClick={() => handleResolveConflict(conflict)}
                      >
                        解決衝突
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={`類型: ${conflict.type}`}
                      description={
                        <Space direction="vertical" size="small">
                          <Text type="secondary">{conflict.error}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            時間: {formatTimeAgo(conflict.timestamp)}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </div>
          )}

          {/* Actions */}
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setDetailsModalVisible(false)}>關閉</Button>
            <Button
              type="primary"
              icon={<CloudSyncOutlined />}
              onClick={handleManualSync}
              disabled={!isOnline || syncProgress.inProgress}
              loading={syncProgress.inProgress}
            >
              立即同步
            </Button>
          </Space>
        </Space>
      </Modal>
    </>
  );
};

export default OfflineIndicator;