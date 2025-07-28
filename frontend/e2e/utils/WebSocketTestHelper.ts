import { Page } from '@playwright/test';

export class WebSocketTestHelper {
  private page: Page;
  private messages: any[] = [];
  private connected: boolean = false;

  constructor(page: Page) {
    this.page = page;
  }

  async setupWebSocketInterception() {
    // Intercept WebSocket connections
    await this.page.evaluate(() => {
      // Store original WebSocket
      const OriginalWebSocket = window.WebSocket;
      
      // Create message storage
      (window as any).__wsMessages = [];
      (window as any).__wsConnections = [];
      
      // Override WebSocket constructor
      (window as any).WebSocket = class MockWebSocket extends OriginalWebSocket {
        constructor(url: string | URL, protocols?: string | string[]) {
          super(url, protocols);
          
          const connection = {
            url: url.toString(),
            readyState: this.readyState,
            messages: [] as any[]
          };
          
          (window as any).__wsConnections.push(connection);
          
          // Track connection state
          this.addEventListener('open', () => {
            connection.readyState = this.readyState;
            console.log('[WS Test] Connected to:', url);
          });
          
          // Track messages
          this.addEventListener('message', (event) => {
            const message = {
              type: 'received',
              data: event.data,
              timestamp: new Date().toISOString()
            };
            
            connection.messages.push(message);
            (window as any).__wsMessages.push(message);
            console.log('[WS Test] Received:', event.data);
          });
          
          // Override send to track outgoing messages
          const originalSend = this.send.bind(this);
          this.send = (data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
            const message = {
              type: 'sent',
              data: data,
              timestamp: new Date().toISOString()
            };
            
            connection.messages.push(message);
            (window as any).__wsMessages.push(message);
            console.log('[WS Test] Sent:', data);
            
            return originalSend(data);
          };
          
          // Track close
          this.addEventListener('close', () => {
            connection.readyState = this.readyState;
            console.log('[WS Test] Disconnected from:', url);
          });
        }
      };
    });
  }

  async waitForConnection(timeout: number = 5000): Promise<boolean> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const connections = await this.page.evaluate(() => (window as any).__wsConnections || []);
      
      if (connections.some((conn: any) => conn.readyState === 1)) {
        this.connected = true;
        return true;
      }
      
      await this.page.waitForTimeout(100);
    }
    
    return false;
  }

  async waitForMessage(
    predicate: (message: any) => boolean,
    timeout: number = 5000
  ): Promise<any> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const messages = await this.getMessages();
      const message = messages.find(predicate);
      
      if (message) {
        return message;
      }
      
      await this.page.waitForTimeout(100);
    }
    
    throw new Error('Timeout waiting for WebSocket message');
  }

  async sendMessage(data: any) {
    await this.page.evaluate((messageData) => {
      const connections = (window as any).__wsConnections || [];
      const activeConnection = connections.find((conn: any) => conn.readyState === 1);
      
      if (activeConnection && activeConnection.ws) {
        activeConnection.ws.send(
          typeof messageData === 'string' ? messageData : JSON.stringify(messageData)
        );
      }
    }, data);
  }

  async getMessages(): Promise<any[]> {
    return await this.page.evaluate(() => {
      return ((window as any).__wsMessages || []).map((msg: any) => {
        try {
          return {
            ...msg,
            parsedData: typeof msg.data === 'string' ? JSON.parse(msg.data) : msg.data
          };
        } catch {
          return msg;
        }
      });
    });
  }

  async getConnections(): Promise<any[]> {
    return await this.page.evaluate(() => (window as any).__wsConnections || []);
  }

  async clearMessages() {
    await this.page.evaluate(() => {
      (window as any).__wsMessages = [];
    });
  }

  async simulateDisconnect() {
    await this.page.evaluate(() => {
      const connections = (window as any).__wsConnections || [];
      connections.forEach((conn: any) => {
        if (conn.ws && conn.readyState === 1) {
          conn.ws.close();
        }
      });
    });
  }

  async simulateReconnect() {
    await this.page.evaluate(() => {
      // Trigger reconnection logic in the app
      window.dispatchEvent(new Event('online'));
    });
  }

  // Mock specific WebSocket events
  async mockNotification(notification: any) {
    await this.page.evaluate((notif) => {
      window.dispatchEvent(new CustomEvent('ws-notification', {
        detail: notif
      }));
    }, notification);
  }

  async mockLocationUpdate(locationData: any) {
    await this.page.evaluate((data) => {
      window.dispatchEvent(new CustomEvent('ws-location-update', {
        detail: data
      }));
    }, locationData);
  }

  async mockOrderUpdate(orderData: any) {
    await this.page.evaluate((data) => {
      window.dispatchEvent(new CustomEvent('ws-order-update', {
        detail: data
      }));
    }, orderData);
  }

  // Helper to verify WebSocket authentication
  async verifyAuthentication(token: string): Promise<boolean> {
    await this.sendMessage({
      type: 'authenticate',
      token
    });

    try {
      const authResponse = await this.waitForMessage(
        (msg) => msg.parsedData?.type === 'authenticated',
        3000
      );
      
      return authResponse.parsedData?.success === true;
    } catch {
      return false;
    }
  }

  // Helper to join a room
  async joinRoom(roomName: string) {
    await this.sendMessage({
      type: 'join',
      room: roomName
    });
  }

  // Helper to leave a room
  async leaveRoom(roomName: string) {
    await this.sendMessage({
      type: 'leave',
      room: roomName
    });
  }

  // Get messages of specific type
  async getMessagesByType(type: string): Promise<any[]> {
    const messages = await this.getMessages();
    return messages.filter(msg => msg.parsedData?.type === type);
  }

  // Wait for multiple messages
  async waitForMessages(
    count: number,
    predicate: (message: any) => boolean,
    timeout: number = 5000
  ): Promise<any[]> {
    const startTime = Date.now();
    const collectedMessages: any[] = [];
    
    while (Date.now() - startTime < timeout && collectedMessages.length < count) {
      const messages = await this.getMessages();
      const matching = messages.filter(predicate);
      
      for (const msg of matching) {
        if (!collectedMessages.find(m => m.timestamp === msg.timestamp)) {
          collectedMessages.push(msg);
        }
      }
      
      if (collectedMessages.length >= count) {
        return collectedMessages.slice(0, count);
      }
      
      await this.page.waitForTimeout(100);
    }
    
    throw new Error(`Timeout waiting for ${count} messages, got ${collectedMessages.length}`);
  }
}