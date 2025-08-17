import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { WebSocketService } from '../websocket.service';

describe('WebSocket Memory Leak Fixes', () => {
  let wsService: WebSocketService;
  let mockWebSocket: any;

  beforeEach(() => {
    // Mock WebSocket
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: WebSocket.CONNECTING,
    };
    
    global.WebSocket = jest.fn(() => mockWebSocket) as any;
    wsService = WebSocketService.getInstance();
  });

  afterEach(() => {
    wsService.disconnect();
    jest.clearAllMocks();
  });

  describe('Reconnection Limits', () => {
    it('should limit reconnection attempts to 5', () => {
      // Verify MAX_RECONNECT_ATTEMPTS is set to 5
      expect(wsService['MAX_RECONNECT_ATTEMPTS']).toBe(5);
    });

    it('should stop reconnecting after 5 attempts', async () => {
      wsService.connect();
      
      // Simulate 5 failed connections
      for (let i = 0; i < 5; i++) {
        mockWebSocket.readyState = WebSocket.CLOSED;
        const errorHandler = mockWebSocket.addEventListener.mock.calls
          .find((call: any) => call[0] === 'error')?.[1];
        if (errorHandler) {
          errorHandler(new Event('error'));
        }
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      expect(wsService['reconnectAttempts']).toBeLessThanOrEqual(5);
    });

    it('should implement exponential backoff with max delay of 30 seconds', () => {
      expect(wsService['MAX_RECONNECT_DELAY']).toBe(30000);
    });

    it('should clear reconnection timer on disconnect', () => {
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      wsService.connect();
      wsService.disconnect();
      
      expect(clearTimeoutSpy).toHaveBeenCalled();
      expect(wsService['reconnectTimeout']).toBeNull();
    });
  });

  describe('Message Queue Limits', () => {
    it('should limit message queue to 50 messages', () => {
      expect(wsService['MAX_MESSAGE_QUEUE_SIZE']).toBe(50);
    });

    it('should limit message history to 50 messages', () => {
      expect(wsService['MAX_MESSAGE_HISTORY']).toBe(50);
    });

    it('should not exceed message queue limit', () => {
      // Queue 60 messages
      for (let i = 0; i < 60; i++) {
        wsService['queueMessage']({ type: 'test', data: i });
      }
      
      expect(wsService['messageQueue'].length).toBeLessThanOrEqual(50);
    });

    it('should not exceed message history limit', () => {
      // Add 60 messages to history
      for (let i = 0; i < 60; i++) {
        wsService['addToMessageHistory']({ 
          type: 'test', 
          data: i,
          timestamp: Date.now() 
        });
      }
      
      expect(wsService['messageHistory'].length).toBeLessThanOrEqual(50);
    });
  });

  describe('Event Listener Cleanup', () => {
    it('should remove all event listeners on disconnect', () => {
      wsService.connect();
      const removeEventListenerSpy = jest.spyOn(mockWebSocket, 'removeEventListener');
      
      wsService.disconnect();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('open', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('message', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('error', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('close', expect.any(Function));
    });

    it('should clear all handlers on cleanup', () => {
      const handler = jest.fn();
      wsService.addMessageHandler(handler);
      
      wsService['cleanup']();
      
      expect(wsService['messageHandlers'].size).toBe(0);
    });
  });

  describe('Memory Cleanup', () => {
    it('should clear message queue on disconnect', () => {
      wsService['queueMessage']({ type: 'test', data: 'test' });
      wsService.disconnect();
      
      expect(wsService['messageQueue'].length).toBe(0);
    });

    it('should clear message history on disconnect', () => {
      wsService['addToMessageHistory']({ 
        type: 'test', 
        data: 'test',
        timestamp: Date.now() 
      });
      wsService.disconnect();
      
      expect(wsService['messageHistory'].length).toBe(0);
    });

    it('should reset reconnect attempts on successful connection', () => {
      wsService['reconnectAttempts'] = 3;
      
      const openHandler = mockWebSocket.addEventListener.mock.calls
        .find((call: any) => call[0] === 'open')?.[1];
      if (openHandler) {
        openHandler(new Event('open'));
      }
      
      expect(wsService['reconnectAttempts']).toBe(0);
    });
  });
});