import React from 'react';
import { Badge, Tag, Tooltip } from 'antd';
import { WifiOutlined, CloudSyncOutlined } from '@ant-design/icons';

interface OfflineIndicatorProps {
  isOnline: boolean;
  pendingSync?: number;
  syncing?: boolean;
}

const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({
  isOnline,
  pendingSync = 0,
  syncing = false,
}) => {
  if (isOnline && pendingSync === 0) {
    return (
      <Tag color="success" icon={<WifiOutlined />}>
        線上
      </Tag>
    );
  }

  if (isOnline && syncing) {
    return (
      <Tag color="processing" icon={<CloudSyncOutlined spin />} data-testid="sync-status">
        同步中...
      </Tag>
    );
  }

  if (isOnline && pendingSync > 0) {
    return (
      <Tooltip title={`${pendingSync} 筆資料待同步`}>
        <Badge count={pendingSync} size="small">
          <Tag color="warning" icon={<CloudSyncOutlined />} data-testid="sync-status">
            待同步
          </Tag>
        </Badge>
      </Tooltip>
    );
  }

  return (
    <Tooltip title="資料將在連線恢復後自動同步">
      <Badge count={pendingSync} size="small">
        <Tag color="error" icon={<WifiOutlined />} data-testid="offline-indicator">
          離線
        </Tag>
      </Badge>
    </Tooltip>
  );
};

export default OfflineIndicator;