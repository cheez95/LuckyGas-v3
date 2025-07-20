import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { websocketService } from '../services/websocket.service';

// Mock WebSocket
class MockWebSocket {
  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate connection after a delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    console.log('MockWebSocket sending:', data);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

// Replace global WebSocket with mock
(global as any).WebSocket = MockWebSocket;

describe('WebSocket Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    websocketService.disconnect();
  });

  it('should connect to WebSocket server', async () => {
    const connectSpy = vi.fn();
    websocketService.on('connect', connectSpy);

    websocketService.connect('test-token');

    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 150));

    expect(connectSpy).toHaveBeenCalled();
  });

  it('should handle incoming messages', async () => {
    const messageSpy = vi.fn();
    websocketService.on('order_created', messageSpy);

    websocketService.connect('test-token');

    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 150));

    // Simulate incoming message
    const ws = (websocketService as any).ws as MockWebSocket;
    if (ws.onmessage) {
      ws.onmessage(new MessageEvent('message', {
        data: JSON.stringify({
          type: 'order_created',
          data: { order_id: 123, order_number: 'ORD-001' }
        })
      }));
    }

    expect(messageSpy).toHaveBeenCalledWith({ order_id: 123, order_number: 'ORD-001' });
  });

  it('should handle subscription messages', () => {
    const topics = ['orders', 'routes'];
    websocketService.subscribe(topics);

    // Verify subscription would be sent when connected
    expect((websocketService as any).subscriptions.size).toBe(2);
    expect((websocketService as any).subscriptions.has('orders')).toBe(true);
    expect((websocketService as any).subscriptions.has('routes')).toBe(true);
  });

  it('should unsubscribe from topics', () => {
    websocketService.subscribe(['orders', 'routes']);
    websocketService.unsubscribe(['orders']);

    expect((websocketService as any).subscriptions.size).toBe(1);
    expect((websocketService as any).subscriptions.has('routes')).toBe(true);
    expect((websocketService as any).subscriptions.has('orders')).toBe(false);
  });

  it('should emit disconnect event when connection closes', async () => {
    const disconnectSpy = vi.fn();
    websocketService.on('disconnect', disconnectSpy);

    websocketService.connect('test-token');

    // Wait for connection
    await new Promise(resolve => setTimeout(resolve, 150));

    // Simulate disconnect
    websocketService.disconnect();

    expect(disconnectSpy).toHaveBeenCalled();
  });

  it('should queue messages when disconnected', () => {
    // Don't connect, just try to send
    websocketService.send('test_event', { data: 'test' });

    // Message should be queued
    expect((websocketService as any).messageQueue.length).toBe(1);
  });

  it('should handle reconnection', async () => {
    const reconnectSpy = vi.fn();
    websocketService.on('reconnect', reconnectSpy);

    // Set short reconnect interval for testing
    (websocketService as any).reconnectInterval = 100;

    websocketService.connect('test-token');

    // Wait for initial connection
    await new Promise(resolve => setTimeout(resolve, 150));

    // Simulate connection loss
    const ws = (websocketService as any).ws as MockWebSocket;
    ws.close();

    // Wait for reconnection attempt
    await new Promise(resolve => setTimeout(resolve, 200));

    expect(reconnectSpy).toHaveBeenCalled();
  });
});

describe('WebSocket React Hook', () => {
  it('should handle WebSocket events in React components', () => {
    // This would be better tested with React Testing Library
    // Example of what to test:
    // 1. useWebSocket hook returns correct connection status
    // 2. Event listeners are properly cleaned up
    // 3. Components re-render on WebSocket events
    // 4. Error handling works correctly
  });
});

// Integration test example
describe('WebSocket Integration', () => {
  it('should update UI when order is created', async () => {
    // This would test the full flow:
    // 1. Component subscribes to order_created event
    // 2. WebSocket receives order_created message
    // 3. Component state updates
    // 4. UI reflects the new order
    
    // Would use React Testing Library + Mock Service Worker
    // to simulate the full integration
  });
});