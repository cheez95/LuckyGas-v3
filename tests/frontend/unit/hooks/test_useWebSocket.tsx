/**
 * Unit tests for useWebSocket custom hook
 * Tests WebSocket connection, reconnection, messaging, and error handling
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useWebSocket, WebSocketMessage } from '../../../../frontend/src/hooks/useWebSocket';
import { AuthProvider } from '../../../../frontend/src/contexts/AuthContext';
import React from 'react';

// Mock WebSocket
class MockWebSocket {
  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    mockWebSocketInstances.push(this);
  }

  send(data: string) {
    mockSendSpy(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper to simulate events
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  simulateError(error: Error) {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

let mockWebSocketInstances: MockWebSocket[] = [];
const mockSendSpy = vi.fn();

// Mock auth context
const mockAuthToken = 'test-auth-token';
vi.mock('../../../../frontend/src/contexts/AuthContext', () => ({
  useAuth: () => ({ token: mockAuthToken })
}));

// Mock notification
vi.mock('antd', () => ({
  notification: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  }
}));

describe('useWebSocket Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWebSocketInstances = [];
    global.WebSocket = MockWebSocket as any;
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('establishes WebSocket connection with authentication token', async () => {
    const { result } = renderHook(() => useWebSocket());

    await waitFor(() => {
      expect(mockWebSocketInstances).toHaveLength(1);
    });

    const ws = mockWebSocketInstances[0];
    expect(ws.url).toContain(`token=${mockAuthToken}`);
    expect(ws.url).toContain('/api/v1/websocket/ws');
  });

  it('updates connection state when WebSocket opens', async () => {
    const onConnect = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onConnect }));

    expect(result.current.isConnected).toBe(false);

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
      expect(onConnect).toHaveBeenCalled();
    });
  });

  it('handles incoming messages correctly', async () => {
    const onMessage = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onMessage }));

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    const testMessage: WebSocketMessage = {
      type: 'order_update',
      data: { orderId: 123, status: 'delivered' },
      timestamp: new Date().toISOString()
    };

    act(() => {
      mockWebSocketInstances[0].simulateMessage(testMessage);
    });

    await waitFor(() => {
      expect(onMessage).toHaveBeenCalledWith(testMessage);
      expect(result.current.lastMessage).toEqual(testMessage);
    });
  });

  it('sends messages through WebSocket', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    const testMessage = { type: 'ping', data: 'test' };

    act(() => {
      result.current.sendMessage(testMessage);
    });

    expect(mockSendSpy).toHaveBeenCalledWith(JSON.stringify(testMessage));
  });

  it('handles heartbeat mechanism', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    // Fast-forward time to trigger heartbeat
    act(() => {
      vi.advanceTimersByTime(30000); // 30 seconds
    });

    expect(mockSendSpy).toHaveBeenCalledWith(
      JSON.stringify({ type: 'ping', timestamp: expect.any(Number) })
    );

    vi.useRealTimers();
  });

  it('handles automatic reconnection on disconnect', async () => {
    vi.useFakeTimers();
    const onDisconnect = vi.fn();
    const { result } = renderHook(() => 
      useWebSocket({ onDisconnect, autoReconnect: true, reconnectInterval: 5000 })
    );

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    expect(result.current.isConnected).toBe(true);

    // Simulate disconnect
    act(() => {
      mockWebSocketInstances[0].simulateClose();
    });

    expect(result.current.isConnected).toBe(false);
    expect(onDisconnect).toHaveBeenCalled();

    // Fast-forward to trigger reconnection
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    await waitFor(() => {
      expect(mockWebSocketInstances).toHaveLength(2); // New connection created
    });

    vi.useRealTimers();
  });

  it('respects autoReconnect false option', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => 
      useWebSocket({ autoReconnect: false })
    );

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    act(() => {
      mockWebSocketInstances[0].simulateClose();
    });

    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(10000);
    });

    // Should not create new connection
    expect(mockWebSocketInstances).toHaveLength(1);

    vi.useRealTimers();
  });

  it('handles different WebSocket endpoints', async () => {
    const { result: driverResult } = renderHook(() => 
      useWebSocket({ endpoint: 'ws/driver' })
    );

    const { result: officeResult } = renderHook(() => 
      useWebSocket({ endpoint: 'ws/office' })
    );

    await waitFor(() => {
      expect(mockWebSocketInstances).toHaveLength(2);
    });

    expect(mockWebSocketInstances[0].url).toContain('/api/v1/websocket/ws/driver');
    expect(mockWebSocketInstances[1].url).toContain('/api/v1/websocket/ws/office');
  });

  it('cleans up WebSocket connection on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket());

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    const ws = mockWebSocketInstances[0];
    const closeSpy = vi.spyOn(ws, 'close');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  it('queues messages when connection is not open', async () => {
    const { result } = renderHook(() => useWebSocket());

    const testMessage = { type: 'test', data: 'queued' };

    // Send message before connection is open
    act(() => {
      result.current.sendMessage(testMessage);
    });

    expect(mockSendSpy).not.toHaveBeenCalled();

    // Open connection
    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    // Message should be sent after connection opens
    await waitFor(() => {
      expect(mockSendSpy).toHaveBeenCalledWith(JSON.stringify(testMessage));
    });
  });

  it('handles WebSocket errors gracefully', async () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onError }));

    act(() => {
      mockWebSocketInstances[0].simulateError(new Error('Connection failed'));
    });

    expect(onError).toHaveBeenCalled();
    expect(result.current.error).toBeDefined();
  });

  it('supports custom message handlers for different message types', async () => {
    const orderHandler = vi.fn();
    const notificationHandler = vi.fn();

    const { result } = renderHook(() => useWebSocket({
      onMessage: (message) => {
        switch (message.type) {
          case 'order_update':
            orderHandler(message);
            break;
          case 'notification':
            notificationHandler(message);
            break;
        }
      }
    }));

    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });

    act(() => {
      mockWebSocketInstances[0].simulateMessage({ type: 'order_update', data: {} });
      mockWebSocketInstances[0].simulateMessage({ type: 'notification', data: {} });
    });

    expect(orderHandler).toHaveBeenCalledTimes(1);
    expect(notificationHandler).toHaveBeenCalledTimes(1);
  });

  it('maintains connection status through multiple reconnection attempts', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useWebSocket({ 
      autoReconnect: true, 
      reconnectInterval: 1000 
    }));

    // Initial connection
    act(() => {
      mockWebSocketInstances[0].simulateOpen();
    });
    expect(result.current.reconnectCount).toBe(0);

    // First disconnect
    act(() => {
      mockWebSocketInstances[0].simulateClose();
    });

    // First reconnection
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.reconnectCount).toBe(1);

    // Second disconnect
    act(() => {
      mockWebSocketInstances[1].simulateClose();
    });

    // Second reconnection
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.reconnectCount).toBe(2);

    vi.useRealTimers();
  });
});