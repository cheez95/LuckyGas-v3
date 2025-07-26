import React, { useEffect, useState } from 'react';
import { Badge, Tooltip } from 'antd';
import { WifiOutlined, DisconnectOutlined, LoadingOutlined } from '@ant-design/icons';
import { websocketService } from '../../services/websocket.service';

type ConnectionState = 'connected' | 'connecting' | 'disconnected' | 'reconnecting';

const WebSocketStatus: React.FC = () => {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  useEffect(() => {
    // Update connection state based on WebSocket events
    const updateConnectionState = () => {
      const state = websocketService.getConnectionState();
      if (state === 'connected') {
        setConnectionState('connected');
        setReconnectAttempts(0);
      } else if (state === 'connecting') {
        setConnectionState('connecting');
      } else {
        setConnectionState('disconnected');
      }
    };

    // Initial state
    updateConnectionState();

    // Listen to WebSocket events
    const handleConnected = () => {
      setConnectionState('connected');
      setReconnectAttempts(0);
    };

    const handleDisconnected = () => {
      setConnectionState('disconnected');
    };

    const handleReconnecting = () => {
      setConnectionState('reconnecting');
      setReconnectAttempts(prev => prev + 1);
    };

    websocketService.on('connected', handleConnected);
    websocketService.on('disconnected', handleDisconnected);
    websocketService.on('reconnecting', handleReconnecting);

    // Check connection state periodically
    const interval = setInterval(updateConnectionState, 1000);

    return () => {
      websocketService.off('connected', handleConnected);
      websocketService.off('disconnected', handleDisconnected);
      websocketService.off('reconnecting', handleReconnecting);
      clearInterval(interval);
    };
  }, []);

  const getStatusConfig = () => {
    switch (connectionState) {
      case 'connected':
        return {
          status: 'success' as const,
          icon: <WifiOutlined />,
          text: '已連線',
          color: '#52c41a',
        };
      case 'connecting':
        return {
          status: 'processing' as const,
          icon: <LoadingOutlined spin />,
          text: '連線中',
          color: '#1890ff',
        };
      case 'reconnecting':
        return {
          status: 'warning' as const,
          icon: <LoadingOutlined spin />,
          text: `重新連線中 (${reconnectAttempts})`,
          color: '#faad14',
        };
      case 'disconnected':
      default:
        return {
          status: 'error' as const,
          icon: <DisconnectOutlined />,
          text: '已斷線',
          color: '#ff4d4f',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <Tooltip title={`即時通訊狀態: ${config.text}`}>
      <Badge
        status={config.status}
        text={
          <span style={{ color: config.color, fontSize: '12px' }}>
            {config.icon} {config.text}
          </span>
        }
      />
    </Tooltip>
  );
};

export default WebSocketStatus;