import { useEffect, useRef, useCallback, useState } from 'react';
import { debounce } from '../../../utils/debounce';
import type { WebSocketMessage } from '../../../types/maps.types';

interface UseOptimizedWebSocketOptions {
  url: string;
  channels: string[];
  onMessage: (message: WebSocketMessage) => void;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
  batchMessages?: boolean;
  batchInterval?: number;
}

interface UseOptimizedWebSocketReturn {
  isConnected: boolean;
  send: (message: any) => void;
  reconnect: () => void;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
}

export function useOptimizedWebSocket({
  url,
  channels,
  onMessage,
  reconnectDelay = 5000,
  maxReconnectAttempts = 5,
  batchMessages = true,
  batchInterval = 100,
}: UseOptimizedWebSocketOptions): UseOptimizedWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const messageQueueRef = useRef<WebSocketMessage[]>([]);
  const subscribedChannelsRef = useRef<Set<string>>(new Set(channels));
  
  // Process batched messages
  const processBatchedMessages = useCallback(() => {
    if (messageQueueRef.current.length === 0) return;
    
    const messages = [...messageQueueRef.current];
    messageQueueRef.current = [];
    
    // Group messages by type for efficient processing
    const groupedMessages = messages.reduce((acc, msg) => {
      if (!acc[msg.type]) {
        acc[msg.type] = [];
      }
      acc[msg.type].push(msg);
      return acc;
    }, {} as Record<string, WebSocketMessage[]>);
    
    // Process each group
    Object.entries(groupedMessages).forEach(([type, msgs]) => {
      // For location updates, only keep the latest per driver
      if (type === 'driver-location') {
        const latestByDriver = new Map<string, WebSocketMessage>();
        msgs.forEach(msg => {
          if ('driverId' in msg) {
            latestByDriver.set(msg.driverId, msg);
          }
        });
        latestByDriver.forEach(msg => onMessage(msg));
      } else {
        // Process all other messages
        msgs.forEach(msg => onMessage(msg));
      }
    });
  }, [onMessage]);
  
  // Debounced message processor
  const debouncedProcessMessages = useRef(
    debounce(processBatchedMessages, batchInterval)
  ).current;
  
  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      if (batchMessages) {
        messageQueueRef.current.push(message);
        debouncedProcessMessages();
      } else {
        onMessage(message);
      }
    } catch (error) {
      console.error('WebSocket message parsing error:', error);
    }
  }, [batchMessages, debouncedProcessMessages, onMessage]);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    try {
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        
        // Subscribe to channels
        subscribedChannelsRef.current.forEach(channel => {
          ws.send(JSON.stringify({ 
            type: 'subscribe', 
            channel 
          }));
        });
      };
      
      ws.onmessage = handleMessage;
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;
        
        // Attempt reconnection
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log(`Reconnecting... (attempt ${reconnectAttemptsRef.current})`);
            connect();
          }, reconnectDelay * reconnectAttemptsRef.current);
        }
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [url, handleMessage, reconnectDelay, maxReconnectAttempts]);
  
  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);
  
  // Send message
  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);
  
  // Subscribe to channel
  const subscribe = useCallback((channel: string) => {
    subscribedChannelsRef.current.add(channel);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      send({ type: 'subscribe', channel });
    }
  }, [send]);
  
  // Unsubscribe from channel
  const unsubscribe = useCallback((channel: string) => {
    subscribedChannelsRef.current.delete(channel);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      send({ type: 'unsubscribe', channel });
    }
  }, [send]);
  
  // Manual reconnect
  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect, disconnect]);
  
  // Setup connection
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);
  
  // Update channels
  useEffect(() => {
    const currentChannels = subscribedChannelsRef.current;
    const newChannels = new Set(channels);
    
    // Unsubscribe from removed channels
    currentChannels.forEach(channel => {
      if (!newChannels.has(channel)) {
        unsubscribe(channel);
      }
    });
    
    // Subscribe to new channels
    newChannels.forEach(channel => {
      if (!currentChannels.has(channel)) {
        subscribe(channel);
      }
    });
  }, [channels, subscribe, unsubscribe]);
  
  return {
    isConnected,
    send,
    reconnect,
    subscribe,
    unsubscribe,
  };
}

// Utility debounce function if not already available
function createDebounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | null = null;
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = window.setTimeout(() => func(...args), wait);
  };
}