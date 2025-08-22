import { useEffect, useRef, useState, useCallback } from 'react';
import { notification } from 'antd';
import { useAuth } from '../contexts/AuthContext';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  [key: string]: any;
}

interface UseWebSocketOptions {
  endpoint?: 'ws' | 'ws/driver' | 'ws/office';
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export const useWebSocket = ({
  endpoint = 'ws',
  onMessage,
  onConnect,
  onDisconnect,
  autoReconnect = true,
  reconnectInterval = 5000,
}: UseWebSocketOptions = {}) => {
  const { token } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!token || websocketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${
      window.location.host
    }/api/v1/websocket/${endpoint}?token=${token}`;

    const ws = new WebSocket(wsUrl);
    websocketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      onConnect?.();

      // Start heartbeat
      heartbeatIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'heartbeat' }));
        }
      }, 30000); // 30 seconds
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);
        onMessage?.(message);

        // Handle specific message types
        handleSystemMessages(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      notification.error({
        message: '連線錯誤',
        description: '與伺服器的即時連線發生錯誤',
      });
    };

    ws.onclose = (event) => {
      console.log('WebSocket disconnected', event.code, event.reason);
      setIsConnected(false);
      onDisconnect?.();

      // Clear heartbeat
      if (heartbeatIntervalRef.current) {
        window.clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }

      // Auto reconnect
      if (autoReconnect && event.code !== 1000) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, reconnectInterval);
      }
    };
  }, [token, endpoint, onMessage, onConnect, onDisconnect, autoReconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      window.clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (websocketRef.current) {
      websocketRef.current.close(1000, 'User disconnect');
      websocketRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      websocketRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }, []);

  const handleSystemMessages = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'system.notification':
        notification.info({
          message: '系統通知',
          description: message.data?.message || '系統訊息',
        });
        break;

      case 'maintenance.alert':
        notification.warning({
          message: '維護通知',
          description: message.data?.message || '系統維護中',
          duration: 0,
        });
        break;

      case 'order.delivered':
        notification.success({
          message: '訂單完成',
          description: `訂單 ${message.data?.order_id} 已送達`,
        });
        break;

      case 'route.assigned':
        notification.info({
          message: '路線指派',
          description: `新路線已指派給您`,
        });
        break;

      // Add more system message handlers as needed
    }
  };

  useEffect(() => {
    if (token) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [token, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
};