import EventEmitter from 'eventemitter3';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface NotificationMessage {
  type: 'notification';
  title: string;
  message: string;
  priority: 'normal' | 'high' | 'urgent';
  timestamp: string;
}

export interface OrderUpdateMessage {
  type: 'order_update';
  order_id: number;
  status: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface RouteUpdateMessage {
  type: 'route_update';
  route_id: number;
  update_type: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface DriverLocationMessage {
  type: 'driver_location_update';
  driver_id: number;
  latitude: number;
  longitude: number;
  timestamp: string;
}

export interface PredictionReadyMessage {
  type: 'prediction_ready';
  batch_id: string;
  summary: Record<string, any>;
  timestamp: string;
}

export type MessageHandler<T = WebSocketMessage> = (message: T) => void;

class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 5000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private url: string;
  private isIntentionallyClosed: boolean = false;
  private messageQueue: WebSocketMessage[] = [];
  private subscriptions: Set<string> = new Set();
  
  // Memory leak prevention
  private readonly MAX_MESSAGE_QUEUE_SIZE = 50; // Reduced from 100
  private readonly MAX_RECONNECT_ATTEMPTS = 3; // Reduced to 3 to prevent excessive reconnection
  private reconnectAttempts: number = 0;
  private messageHistory: WebSocketMessage[] = [];
  private readonly MAX_MESSAGE_HISTORY = 50; // Reduced from 100
  private readonly MAX_RECONNECT_DELAY = 30000; // Max 30 seconds

  constructor() {
    super();
    // Use WebSocket URL from environment variables
    const wsUrl = import.meta.env.VITE_WS_URL;
    
    if (wsUrl) {
      // Use the WebSocket URL from env if available
      this.url = `${wsUrl}/api/v1/websocket/ws`;
    } else {
      // Fallback to local development
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = import.meta.env.PROD ? window.location.host : 'localhost:8000';
      this.url = `${protocol}//${host}/api/v1/websocket/ws`;
    }
    
    console.log('🔌 WebSocket URL:', this.url);
  }

  connect(): void {
    console.log('🔌 WebSocket connect() called');
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('No authentication token found');
      return;
    }

    // Check if we've exceeded max reconnect attempts
    if (this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      console.error('Max reconnect attempts reached. Stopping reconnection.');
      this.emit('max_reconnects_reached');
      return;
    }

    const wsUrl = `${this.url}?token=${encodeURIComponent(token)}`;
    console.log('🔌 Attempting to connect to:', wsUrl);

    try {
      // Clean up old connection if exists
      this.cleanupWebSocket();
      
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
      console.log('🔌 WebSocket connection initiated');
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    console.log('🔌 WebSocket disconnect() called');
    this.isIntentionallyClosed = true;
    this.reconnectAttempts = 0; // Reset reconnect attempts
    this.clearTimers();
    
    // Clean up WebSocket
    this.cleanupWebSocket();
    
    // Clear message queues to free memory
    this.messageQueue = [];
    this.messageHistory = [];
    
    // Clear subscriptions
    this.subscriptions.clear();
    
    // Remove all event listeners
    this.removeAllListeners();
    
    console.log('🔌 WebSocket fully disconnected and cleaned up');
  }
  
  /**
   * Clean up WebSocket connection and handlers
   */
  private cleanupWebSocket(): void {
    if (this.ws) {
      // Remove event handlers before closing
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      
      // Close connection if open
      if (this.ws.readyState !== WebSocket.CLOSED) {
        console.log('🔌 Closing WebSocket connection');
        this.ws.close(1000, 'Client disconnecting');
      }
      
      this.ws = null;
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;
    
    console.log('🔌 Setting up WebSocket event handlers');

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected successfully!');
      this.emit('connected');
      this.isIntentionallyClosed = false;
      this.reconnectAttempts = 0; // Reset on successful connection
      this.reconnectInterval = 5000; // Reset backoff
      
      // Clear reconnect timer
      if (this.reconnectTimer) {
        window.clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      // Start heartbeat
      this.startHeartbeat();

      // Resubscribe to topics
      this.subscriptions.forEach(topic => {
        this.send({ type: 'subscribe', topic });
      });

      // Send queued messages (limit to prevent memory issues)
      const messagesToSend = this.messageQueue.slice(0, this.MAX_MESSAGE_QUEUE_SIZE);
      this.messageQueue = this.messageQueue.slice(this.MAX_MESSAGE_QUEUE_SIZE);
      
      messagesToSend.forEach(message => {
        this.send(message);
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      console.error('❌ WebSocket readyState:', this.ws?.readyState);
      console.error('❌ WebSocket URL:', this.ws?.url);
      this.emit('error', error);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected', { code: event.code, reason: event.reason });
      this.emit('disconnected');
      this.clearTimers();

      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
      }
    };
  }

  private handleMessage(message: WebSocketMessage): void {
    console.log('📨 WebSocket received message:', message);
    
    // Store in history with limit
    this.messageHistory.push(message);
    if (this.messageHistory.length > this.MAX_MESSAGE_HISTORY) {
      this.messageHistory = this.messageHistory.slice(-this.MAX_MESSAGE_HISTORY);
    }
    
    // Emit generic message event
    this.emit('message', message);

    // Emit specific message type events
    switch (message.type) {
      case 'connection':
        this.emit('connection', message);
        break;

      case 'pong':
        // Heartbeat response
        break;

      case 'notification':
        this.emit('notification', message as NotificationMessage);
        break;

      case 'order_update':
        this.emit('order_update', message as OrderUpdateMessage);
        break;

      case 'route_update':
        this.emit('route_update', message as RouteUpdateMessage);
        break;

      case 'driver_location_update':
        this.emit('driver_location', message as DriverLocationMessage);
        break;

      case 'prediction_ready':
        this.emit('prediction_ready', message as PredictionReadyMessage);
        break;

      case 'delivery_status_update':
        this.emit('delivery_status', message);
        break;

      case 'system_message':
        this.emit('system_message', message);
        break;

      case 'route_assigned':
        this.emit('route_assigned', message);
        break;

      case 'subscribed':
      case 'unsubscribed':
        this.emit(message.type, message);
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message if not connected (with size limit)
      if (this.messageQueue.length >= this.MAX_MESSAGE_QUEUE_SIZE) {
        console.warn('Message queue full, dropping oldest message');
        this.messageQueue.shift(); // Remove oldest
      }
      this.messageQueue.push(message);
    }
  }

  subscribe(topic: string): void {
    this.subscriptions.add(topic);
    this.send({ type: 'subscribe', topic });
  }

  unsubscribe(topic: string): void {
    this.subscriptions.delete(topic);
    this.send({ type: 'unsubscribe', topic });
  }

  // Driver-specific methods
  updateDriverLocation(latitude: number, longitude: number): void {
    this.send({
      type: 'driver_location',
      latitude,
      longitude,
    });
  }

  updateDeliveryStatus(orderId: number, status: string): void {
    this.send({
      type: 'delivery_status',
      order_id: orderId,
      status,
    });
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Send ping every 30 seconds
  }

  private clearTimers(): void {
    if (this.heartbeatInterval) {
      window.clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer || this.isIntentionallyClosed) {
      return;
    }

    // Check max attempts
    if (this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      console.error('Max reconnect attempts reached');
      this.emit('max_reconnects_reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Reconnecting in ${this.reconnectInterval / 1000} seconds... (attempt ${this.reconnectAttempts}/${this.MAX_RECONNECT_ATTEMPTS})`);
    this.emit('reconnecting');
    
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectInterval);

    // Exponential backoff with max delay
    this.reconnectInterval = Math.min(this.reconnectInterval * 2, this.MAX_RECONNECT_DELAY);
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }
  
  /**
   * Get message history (limited to prevent memory issues)
   */
  getMessageHistory(): WebSocketMessage[] {
    return [...this.messageHistory];
  }
  
  /**
   * Clear message history to free memory
   */
  clearMessageHistory(): void {
    this.messageHistory = [];
    console.log('🔌 Message history cleared');
  }
  
  /**
   * Get current memory usage stats
   */
  getMemoryStats() {
    return {
      messageQueueSize: this.messageQueue.length,
      messageHistorySize: this.messageHistory.length,
      subscriptionCount: this.subscriptions.size,
      reconnectAttempts: this.reconnectAttempts,
      connectionState: this.getConnectionState(),
    };
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Expose to window for debugging
if (typeof window !== 'undefined') {
  (window as any).websocketService = websocketService;
  
  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    websocketService.disconnect();
  });
}

// Export convenience hooks for React components
export const useWebSocket = () => {
  return websocketService;
};