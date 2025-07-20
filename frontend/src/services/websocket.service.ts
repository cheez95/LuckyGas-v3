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

  constructor() {
    super();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Extract host from API URL or use localhost:8000 as default
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const host = apiUrl.replace(/^https?:\/\//, '');
    this.url = `${protocol}//${host}/ws`;
  }

  connect(): void {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('No authentication token found');
      return;
    }

    try {
      this.ws = new WebSocket(`${this.url}?token=${encodeURIComponent(token)}`);
      this.setupEventHandlers();
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.emit('connected');
      this.isIntentionallyClosed = false;
      
      // Clear reconnect timer
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      // Start heartbeat
      this.startHeartbeat();

      // Resubscribe to topics
      this.subscriptions.forEach(topic => {
        this.send({ type: 'subscribe', topic });
      });

      // Send queued messages
      while (this.messageQueue.length > 0) {
        const message = this.messageQueue.shift();
        if (message) {
          this.send(message);
        }
      }
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
      console.error('WebSocket error:', error);
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
      // Queue message if not connected
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
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Send ping every 30 seconds
  }

  private clearTimers(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer || this.isIntentionallyClosed) {
      return;
    }

    console.log(`Reconnecting in ${this.reconnectInterval / 1000} seconds...`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectInterval);

    // Exponential backoff, max 60 seconds
    this.reconnectInterval = Math.min(this.reconnectInterval * 1.5, 60000);
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
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export convenience hooks for React components
export const useWebSocket = () => {
  return websocketService;
};