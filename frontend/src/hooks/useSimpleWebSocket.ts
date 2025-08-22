/**
 * Simple WebSocket hook for real-time updates
 * Replaces complex WebSocket service with direct connection
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { notification } from 'antd';
import { useAuth } from '@/hooks/useAuth';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

interface WebSocketOptions {
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: WebSocketMessage) => void;
}

export function useSimpleWebSocket(options: WebSocketOptions = {}) {
  const {
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
    onMessage
  } = options;

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  
  const queryClient = useQueryClient();
  const { token } = useAuth();

  const connect = useCallback(() => {
    if (!token) {
      console.log('No auth token, skipping WebSocket connection');
      return;
    }

    // Clean up existing connection
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.close();
    }

    // Build WebSocket URL with token
    const wsUrl = new URL('/api/v1/websocket/ws', import.meta.env.VITE_WS_URL || 'ws://localhost:8000');
    wsUrl.searchParams.append('token', token);
    
    console.log('Connecting to WebSocket:', wsUrl.origin);
    ws.current = new WebSocket(wsUrl.toString());
    
    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      reconnectAttempts.current = 0;
      
      // Send initial ping
      ws.current?.send(JSON.stringify({ type: 'ping' }));
    };
    
    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        handleMessage(message);
        
        // Call custom handler if provided
        onMessage?.(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      setIsConnected(false);
      
      // Attempt reconnection if not intentional close
      if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++;
        console.log(`Reconnecting in ${reconnectDelay}ms... (attempt ${reconnectAttempts.current})`);
        
        reconnectTimer.current = setTimeout(connect, reconnectDelay);
      }
    };
    
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [token, reconnectDelay, maxReconnectAttempts, onMessage]);

  const handleMessage = (message: WebSocketMessage) => {
    console.log('WebSocket message:', message.type, message.data);
    
    switch (message.type) {
      case 'connected':
        // Connection confirmed
        break;
        
      case 'pong':
        // Heartbeat response
        break;
      
      case 'order_updated':
        // Invalidate order queries to trigger refetch
        queryClient.invalidateQueries({ queryKey: ['orders'] });
        queryClient.invalidateQueries({ queryKey: ['order', message.data.order_id] });
        
        // Show notification
        notification.info({
          message: '訂單狀態更新',
          description: `訂單 ${message.data.details?.order_number || message.data.order_id} 狀態已更新為 ${message.data.status}`,
          placement: 'topRight',
        });
        break;
        
      case 'route_assigned':
        // Invalidate route queries
        queryClient.invalidateQueries({ queryKey: ['routes'] });
        queryClient.invalidateQueries({ queryKey: ['route', message.data.route_id] });
        
        notification.success({
          message: '路線已分配',
          description: `路線已分配給司機 ${message.data.driver_id}`,
          placement: 'topRight',
        });
        break;
        
      case 'driver_location':
        // Update driver location on map if visible
        const event = new CustomEvent('driver-location-update', {
          detail: message.data
        });
        window.dispatchEvent(event);
        break;
        
      case 'routes_assigned':
        // Batch route assignment notification
        notification.success({
          message: '路線分配完成',
          description: `已分配 ${message.data.assigned_orders} 個訂單到 ${message.data.routes_created} 條路線`,
          placement: 'topRight',
        });
        break;
        
      default:
        console.debug('Unhandled WebSocket message type:', message.type);
    }
  };

  const sendMessage = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    reconnectAttempts.current = maxReconnectAttempts; // Prevent reconnection
    
    if (ws.current) {
      ws.current.close(1000, 'User disconnect');
      ws.current = null;
    }
    
    setIsConnected(false);
  }, [maxReconnectAttempts]);

  // Set up connection on mount
  useEffect(() => {
    connect();
    
    // Set up periodic ping to keep connection alive
    const pingInterval = window.setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendMessage({ type: 'ping' });
      }
    }, 30000); // Ping every 30 seconds
    
    return () => {
      window.clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect, sendMessage]);

  return {
    isConnected,
    sendMessage,
    disconnect,
    reconnect: connect
  };
}

// Example usage in a component:
/*
function OrderManagement() {
  const { isConnected } = useSimpleWebSocket({
    onMessage: (message) => {
      // Custom message handling
      if (message.type === 'order_updated' && message.data.status === 'delivered') {
        // Play sound or show special notification
        playDeliverySound();
      }
    }
  });

  return (
    <div>
      <Badge status={isConnected ? 'success' : 'error'} text={isConnected ? '已連線' : '未連線'} />
      {/* Rest of component *//*}
    </div>
  );
}
*/

// Hook for driver location updates
export function useDriverTracking(driverId?: number) {
  const [driverLocation, setDriverLocation] = useState<{
    latitude: number;
    longitude: number;
    heading?: number;
    speed?: number;
  } | null>(null);

  useSimpleWebSocket({
    onMessage: (message) => {
      if (message.type === 'driver_location' && message.data.driver_id === driverId) {
        setDriverLocation({
          latitude: message.data.latitude,
          longitude: message.data.longitude,
          heading: message.data.heading,
          speed: message.data.speed
        });
      }
    }
  });

  return driverLocation;
}