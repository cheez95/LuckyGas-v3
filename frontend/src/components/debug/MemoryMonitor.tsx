/**
 * Memory Monitor Component
 * Displays real-time memory usage in development
 * Helps identify memory leaks during development
 */

import React, { useState, useEffect } from 'react';
import { Card, Progress, Statistic, Alert, Button, Space, Typography } from 'antd';
import { WarningOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { memoryManager } from '../../utils/memoryManager';
import { websocketService } from '../../services/websocket.service';
import { useCleanup } from '../../hooks/useCleanup';

const { Text } = Typography;

const MemoryMonitor: React.FC = () => {
  const cleanup = useCleanup();
  const [memoryStatus, setMemoryStatus] = useState<any>(null);
  const [wsStats, setWsStats] = useState<any>(null);
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    // Start memory monitoring
    memoryManager.startMonitoring(10000); // Check every 10 seconds in dev

    const updateStats = () => {
      if (!cleanup.isMounted()) return;
      
      const status = memoryManager.getStatus();
      setMemoryStatus(status);
      
      const websocketStats = websocketService.getMemoryStats();
      setWsStats(websocketStats);
      
      // Show warning if memory is increasing
      if (status.trend === 'increasing') {
        setShowWarning(true);
      }
    };

    // Initial update
    updateStats();

    // Update periodically
    const interval = cleanup.setInterval(updateStats, 5000);

    return () => {
      cleanup.clearInterval(interval);
      memoryManager.stopMonitoring();
    };
  }, [cleanup]);

  const handleClearCaches = () => {
    memoryManager.clearCaches();
    websocketService.clearMessageHistory();
    window.location.reload(); // Reload to clear all memory
  };

  const handleForceGC = () => {
    memoryManager.forceGC();
  };

  if (!memoryStatus || !memoryStatus.current) {
    return null;
  }

  const { current, trend } = memoryStatus;
  const memoryPercent = Math.round((current.heapUsed / current.external) * 100);
  const isHighMemory = memoryPercent > 80;

  // Don't show in production
  if (process.env.NODE_ENV === 'production') {
    return null;
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 20,
        left: 20,
        zIndex: 9999,
        width: 320,
        opacity: 0.95,
      }}
    >
      <Card
        title={
          <Space>
            Memory Monitor
            {trend === 'increasing' && <WarningOutlined style={{ color: '#ff4d4f' }} />}
          </Space>
        }
        size="small"
        extra={
          <Space>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={handleForceGC}
              title="Force Garbage Collection"
            />
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={handleClearCaches}
              title="Clear Caches & Reload"
            />
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* Memory Usage */}
          <div>
            <Text type="secondary">Heap Usage</Text>
            <Progress
              percent={memoryPercent}
              status={isHighMemory ? 'exception' : 'normal'}
              format={percent => `${percent}%`}
            />
            <Space>
              <Statistic
                value={Math.round(current.heapUsed / 1024 / 1024)}
                suffix="MB"
                valueStyle={{ fontSize: 14 }}
              />
              <Text type="secondary">
                / {Math.round(current.external / 1024 / 1024)} MB
              </Text>
            </Space>
          </div>

          {/* Memory Trend */}
          <div>
            <Text type="secondary">Trend: </Text>
            <Text
              strong
              type={
                trend === 'increasing'
                  ? 'danger'
                  : trend === 'decreasing'
                  ? 'success'
                  : 'secondary'
              }
            >
              {trend.toUpperCase()}
            </Text>
          </div>

          {/* WebSocket Stats */}
          {wsStats && (
            <div>
              <Text type="secondary">WebSocket:</Text>
              <div style={{ paddingLeft: 12 }}>
                <Text style={{ fontSize: 12 }}>
                  Queue: {wsStats.messageQueueSize} | 
                  History: {wsStats.messageHistorySize} | 
                  Subs: {wsStats.subscriptionCount}
                </Text>
                <br />
                <Text style={{ fontSize: 12 }}>
                  Reconnects: {wsStats.reconnectAttempts} | 
                  State: {wsStats.connectionState}
                </Text>
              </div>
            </div>
          )}

          {/* Warning Alert */}
          {showWarning && (
            <Alert
              message="Memory Usage Increasing"
              description="Consider refreshing the page if memory continues to increase."
              type="warning"
              showIcon
              closable
              onClose={() => setShowWarning(false)}
            />
          )}
        </Space>
      </Card>
    </div>
  );
};

// Export memoized version to prevent re-renders
export default React.memo(MemoryMonitor);