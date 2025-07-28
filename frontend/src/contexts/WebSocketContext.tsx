import React, { createContext, useContext, ReactNode, useRef } from 'react';
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
  on: (event: string, callback: (data: any) => void) => () => void;
  emit: (event: string, data?: any) => void;
  socket?: any;
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
  const eventListenersRef = React.useRef<Map<string, Set<(data: any) => void>>>(new Map());
  
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
      // Emit to event listeners
      const listeners = eventListenersRef.current.get(message.type);
      if (listeners) {
        listeners.forEach(callback => callback(message.data || message));
      }
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

  // Event listener methods
  const on = (event: string, callback: (data: any) => void) => {
    if (!eventListenersRef.current.has(event)) {
      eventListenersRef.current.set(event, new Set());
    }
    eventListenersRef.current.get(event)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      const listeners = eventListenersRef.current.get(event);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          eventListenersRef.current.delete(event);
        }
      }
    };
  };

  const emit = (event: string, data?: any) => {
    sendMessage({ type: event, data });
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
    on,
    emit,
    socket: { on, emit, connected: isConnected },
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
};