import React, { createContext, useContext, ReactNode } from 'react';
import { useWebSocket, WebSocketMessage } from '../hooks/useWebSocket';
import { useAuth } from './AuthContext';

interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: WebSocketMessage) => void;
  subscribeToOrderUpdates: (orderId: string) => void;
  unsubscribeFromOrderUpdates: (orderId: string) => void;
  subscribeToRouteUpdates: (routeId: string) => void;
  unsubscribeFromRouteUpdates: (routeId: string) => void;
  subscribeToDriverLocation: (driverId: string) => void;
  unsubscribeFromDriverLocation: (driverId: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user } = useAuth();
  
  // Determine endpoint based on user role
  const getEndpoint = () => {
    if (!user) return 'ws';
    
    switch (user.role) {
      case 'driver':
        return 'ws/driver';
      case 'office_staff':
      case 'manager':
      case 'super_admin':
        return 'ws/office';
      default:
        return 'ws';
    }
  };

  const { isConnected, lastMessage, sendMessage } = useWebSocket({
    endpoint: getEndpoint() as any,
    onMessage: (message) => {
      console.log('WebSocket message received:', message);
    },
    onConnect: () => {
      console.log('WebSocket connected in context');
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected in context');
    },
  });

  // Subscription helpers
  const subscribeToOrderUpdates = (orderId: string) => {
    sendMessage({
      type: 'subscribe',
      channel: 'orders',
      filter: { order_id: orderId },
    });
  };

  const unsubscribeFromOrderUpdates = (orderId: string) => {
    sendMessage({
      type: 'unsubscribe',
      channel: 'orders',
      filter: { order_id: orderId },
    });
  };

  const subscribeToRouteUpdates = (routeId: string) => {
    sendMessage({
      type: 'subscribe',
      channel: 'routes',
      filter: { route_id: routeId },
    });
  };

  const unsubscribeFromRouteUpdates = (routeId: string) => {
    sendMessage({
      type: 'unsubscribe',
      channel: 'routes',
      filter: { route_id: routeId },
    });
  };

  const subscribeToDriverLocation = (driverId: string) => {
    sendMessage({
      type: 'subscribe',
      channel: 'drivers',
      filter: { driver_id: driverId },
    });
  };

  const unsubscribeFromDriverLocation = (driverId: string) => {
    sendMessage({
      type: 'unsubscribe',
      channel: 'drivers',
      filter: { driver_id: driverId },
    });
  };

  const value: WebSocketContextType = {
    isConnected,
    lastMessage,
    sendMessage,
    subscribeToOrderUpdates,
    unsubscribeFromOrderUpdates,
    subscribeToRouteUpdates,
    unsubscribeFromRouteUpdates,
    subscribeToDriverLocation,
    unsubscribeFromDriverLocation,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
};