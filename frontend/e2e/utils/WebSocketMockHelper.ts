import { Page } from '@playwright/test';

export class WebSocketMockHelper {
  private page: Page;
  private messageQueue: any[] = [];

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Initialize WebSocket mock in the browser context
   */
  async initialize() {
    await this.page.addInitScript(() => {
      // Store the original WebSocket
      const OriginalWebSocket = window.WebSocket;
      
      // Create mock WebSocket class
      class MockWebSocket {
        url: string;
        readyState: number = 0; // CONNECTING
        onopen: ((event: Event) => void) | null = null;
        onclose: ((event: CloseEvent) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;
        onmessage: ((event: MessageEvent) => void) | null = null;
        
        constructor(url: string, protocols?: string | string[]) {
          this.url = url;
          
          // Store instance for external control
          (window as any).__mockWebSocket = this;
          
          // Simulate connection after a short delay
          setTimeout(() => {
            this.readyState = 1; // OPEN
            if (this.onopen) {
              this.onopen(new Event('open'));
            }
          }, 100);
        }
        
        send(data: string | ArrayBuffer | Blob) {
          // Store sent messages
          if (!(window as any).__wsSentMessages) {
            (window as any).__wsSentMessages = [];
          }
          (window as any).__wsSentMessages.push(data);
          
          // Echo back for testing
          if (this.readyState === 1 && this.onmessage) {
            setTimeout(() => {
              if (typeof data === 'string') {
                const parsed = JSON.parse(data);
                // Mock response based on message type
                let response;
                switch (parsed.type) {
                  case 'ping':
                    response = { type: 'pong', timestamp: Date.now() };
                    break;
                  case 'subscribe':
                    response = { type: 'subscribed', channel: parsed.channel };
                    break;
                  default:
                    response = { type: 'ack', originalType: parsed.type };
                }
                
                if (this.onmessage) {
                  this.onmessage(new MessageEvent('message', {
                    data: JSON.stringify(response)
                  }));
                }
              }
            }, 50);
          }
        }
        
        close(code?: number, reason?: string) {
          this.readyState = 3; // CLOSED
          if (this.onclose) {
            this.onclose(new CloseEvent('close', { code, reason }));
          }
        }
        
        // Additional properties for compatibility
        get CONNECTING() { return 0; }
        get OPEN() { return 1; }
        get CLOSING() { return 2; }
        get CLOSED() { return 3; }
        
        addEventListener(type: string, listener: EventListener) {
          switch (type) {
            case 'open':
              this.onopen = listener as (event: Event) => void;
              break;
            case 'close':
              this.onclose = listener as (event: CloseEvent) => void;
              break;
            case 'error':
              this.onerror = listener as (event: Event) => void;
              break;
            case 'message':
              this.onmessage = listener as (event: MessageEvent) => void;
              break;
          }
        }
        
        removeEventListener(type: string, listener: EventListener) {
          // Simple implementation - just clear the handler
          switch (type) {
            case 'open':
              this.onopen = null;
              break;
            case 'close':
              this.onclose = null;
              break;
            case 'error':
              this.onerror = null;
              break;
            case 'message':
              this.onmessage = null;
              break;
          }
        }
      }
      
      // Replace global WebSocket
      (window as any).WebSocket = MockWebSocket;
      (window as any).__OriginalWebSocket = OriginalWebSocket;
    });
  }

  /**
   * Send a message from server to client
   */
  async sendMessage(message: any) {
    await this.page.evaluate((msg) => {
      const ws = (window as any).__mockWebSocket;
      if (ws && ws.readyState === 1 && ws.onmessage) {
        ws.onmessage(new MessageEvent('message', {
          data: typeof msg === 'string' ? msg : JSON.stringify(msg)
        }));
      }
    }, message);
  }

  /**
   * Simulate connection status change
   */
  async simulateConnectionStatus(status: 'connected' | 'disconnected' | 'error') {
    await this.page.evaluate((status) => {
      const ws = (window as any).__mockWebSocket;
      if (!ws) return;
      
      switch (status) {
        case 'connected':
          ws.readyState = 1;
          if (ws.onopen) {
            ws.onopen(new Event('open'));
          }
          break;
        case 'disconnected':
          ws.readyState = 3;
          if (ws.onclose) {
            ws.onclose(new CloseEvent('close'));
          }
          break;
        case 'error':
          if (ws.onerror) {
            ws.onerror(new Event('error'));
          }
          break;
      }
    }, status);
  }

  /**
   * Get all messages sent by the client
   */
  async getSentMessages(): Promise<any[]> {
    return await this.page.evaluate(() => {
      const messages = (window as any).__wsSentMessages || [];
      return messages.map((msg: string) => {
        try {
          return JSON.parse(msg);
        } catch {
          return msg;
        }
      });
    });
  }

  /**
   * Clear sent messages
   */
  async clearSentMessages() {
    await this.page.evaluate(() => {
      (window as any).__wsSentMessages = [];
    });
  }

  /**
   * Simulate real-time events
   */
  async simulateOrderUpdate(orderId: string, status: string) {
    await this.sendMessage({
      type: 'orderUpdate',
      data: {
        orderId,
        status,
        timestamp: new Date().toISOString()
      }
    });
  }

  async simulateDriverLocation(driverId: string, lat: number, lng: number) {
    await this.sendMessage({
      type: 'driverLocation',
      data: {
        driverId,
        location: { lat, lng },
        timestamp: new Date().toISOString()
      }
    });
  }

  async simulateNewOrder(order: any) {
    await this.sendMessage({
      type: 'newOrder',
      data: order
    });
  }

  async simulateRouteUpdate(routeId: string, updates: any) {
    await this.sendMessage({
      type: 'routeUpdate',
      data: {
        routeId,
        ...updates,
        timestamp: new Date().toISOString()
      }
    });
  }

  /**
   * Wait for WebSocket connection to be established
   */
  async waitForConnection(timeout: number = 5000) {
    await this.page.waitForFunction(
      () => {
        const ws = (window as any).__mockWebSocket;
        return ws && ws.readyState === 1;
      },
      { timeout }
    );
  }

  /**
   * Check if WebSocket is connected
   */
  async isConnected(): Promise<boolean> {
    return await this.page.evaluate(() => {
      const ws = (window as any).__mockWebSocket;
      return ws && ws.readyState === 1;
    });
  }
}