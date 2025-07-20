import { useEffect, useState, useCallback, useRef } from 'react';
import { websocketService, WebSocketMessage, MessageHandler } from '../services/websocket.service';

interface UseWebSocketOptions {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const { onConnect, onDisconnect, onError, autoConnect = true } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<string>('disconnected');
  const listenersRef = useRef<Map<string, MessageHandler>>(new Map());

  useEffect(() => {
    const handleConnect = () => {
      setIsConnected(true);
      setConnectionState('connected');
      onConnect?.();
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      setConnectionState('disconnected');
      onDisconnect?.();
    };

    const handleError = (error: Event) => {
      onError?.(error);
    };

    // Add event listeners
    websocketService.on('connected', handleConnect);
    websocketService.on('disconnected', handleDisconnect);
    websocketService.on('error', handleError);

    // Check initial connection state
    setIsConnected(websocketService.isConnected());
    setConnectionState(websocketService.getConnectionState());

    // Auto-connect if enabled
    if (autoConnect && !websocketService.isConnected()) {
      websocketService.connect();
    }

    // Cleanup
    return () => {
      websocketService.off('connected', handleConnect);
      websocketService.off('disconnected', handleDisconnect);
      websocketService.off('error', handleError);

      // Remove all message listeners
      listenersRef.current.forEach((handler, event) => {
        websocketService.off(event, handler);
      });
      listenersRef.current.clear();
    };
  }, [onConnect, onDisconnect, onError, autoConnect]);

  const subscribe = useCallback((topic: string) => {
    websocketService.subscribe(topic);
  }, []);

  const unsubscribe = useCallback((topic: string) => {
    websocketService.unsubscribe(topic);
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    websocketService.send(message);
  }, []);

  const on = useCallback(<T extends WebSocketMessage = WebSocketMessage>(
    event: string,
    handler: MessageHandler<T>
  ) => {
    // Store reference to handler
    listenersRef.current.set(event, handler as MessageHandler);
    
    // Add listener
    websocketService.on(event, handler);

    // Return cleanup function
    return () => {
      websocketService.off(event, handler);
      listenersRef.current.delete(event);
    };
  }, []);

  const off = useCallback((event: string, handler: MessageHandler) => {
    websocketService.off(event, handler);
    listenersRef.current.delete(event);
  }, []);

  return {
    isConnected,
    connectionState,
    subscribe,
    unsubscribe,
    sendMessage,
    on,
    off,
    service: websocketService,
  };
};

// Hook for driver-specific WebSocket features
export const useDriverWebSocket = () => {
  const ws = useWebSocket();

  const updateLocation = useCallback((latitude: number, longitude: number) => {
    websocketService.updateDriverLocation(latitude, longitude);
  }, []);

  const updateDeliveryStatus = useCallback((orderId: number, status: string) => {
    websocketService.updateDeliveryStatus(orderId, status);
  }, []);

  return {
    ...ws,
    updateLocation,
    updateDeliveryStatus,
  };
};