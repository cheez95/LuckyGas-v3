# Real-time Updates & Localization - Brownfield Addition

## User Story

As a Lucky Gas dispatcher,
I want to see real-time updates of orders and deliveries with all interface text in Traditional Chinese,
So that I can monitor operations effectively and work comfortably in my native language.

## Story Context

**Existing System Integration:**

- Integrates with: WebSocket service at ws://localhost:8000/ws
- Technology: React + TypeScript, Socket.io client, react-i18next
- Follows pattern: Custom hooks for WebSocket, context providers for state
- Touch points: Order status updates, delivery tracking, driver locations

## Acceptance Criteria

**Functional Requirements:**

1. WebSocket connection established with automatic reconnection on failure
2. Real-time updates for order status, delivery progress, and driver locations
3. Complete Traditional Chinese (繁體中文) localization for all UI text

**Integration Requirements:**
4. WebSocket events match backend event structure exactly
5. Connection status indicator shows online/offline/reconnecting states
6. Localization system supports dynamic content and number formatting

**Quality Requirements:**
7. Updates appear within 1 second of backend event emission
8. Reconnection happens within 5 seconds with exponential backoff
9. All text, including error messages and tooltips, in Traditional Chinese

## Technical Notes

- **Integration Approach:** 
  - Create WebSocket service with event handlers
  - Use React Context for distributing real-time updates
  - Implement connection status monitoring with UI indicators

- **Existing Pattern Reference:** 
  - WebSocket patterns: `/frontend/src/services/websocket/`
  - Localization setup: `/frontend/src/locales/`
  - Hook patterns: `/frontend/src/hooks/`

- **Key Constraints:** 
  - Must handle connection interruptions gracefully
  - Traditional Chinese requires proper font support
  - Date/time formats must follow Taiwan conventions

## Implementation Details

```typescript
// WebSocket service
// src/services/websocket/client.ts
export class WebSocketClient {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  
  connect(token: string) {
    this.socket = io(process.env.REACT_APP_WS_URL || 'ws://localhost:8000', {
      auth: { token },
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });
    
    this.setupEventHandlers();
  }
  
  private setupEventHandlers() {
    this.socket?.on('order:update', this.handleOrderUpdate);
    this.socket?.on('delivery:status', this.handleDeliveryStatus);
    this.socket?.on('driver:location', this.handleDriverLocation);
  }
}

// React hook for WebSocket
// src/hooks/useWebSocket.ts
export const useWebSocket = () => {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  
  useEffect(() => {
    const client = new WebSocketClient();
    client.on('statusChange', setStatus);
    client.connect(getAuthToken());
    
    return () => client.disconnect();
  }, []);
  
  return { status, lastUpdate };
};

// Localization setup
// src/locales/zh-TW/translation.json
{
  "common": {
    "loading": "載入中...",
    "error": "發生錯誤",
    "save": "儲存",
    "cancel": "取消",
    "delete": "刪除",
    "edit": "編輯"
  },
  "customer": {
    "title": "客戶管理",
    "name": "客戶名稱",
    "address": "地址",
    "phone": "電話",
    "type": {
      "commercial": "商業",
      "residential": "住宅"
    }
  },
  "order": {
    "title": "訂單管理",
    "status": {
      "pending": "待處理",
      "confirmed": "已確認",
      "delivered": "已送達",
      "cancelled": "已取消"
    }
  },
  "connection": {
    "online": "連線中",
    "offline": "離線",
    "reconnecting": "重新連線中..."
  }
}
```

## WebSocket Events

```typescript
// Event types matching backend
interface OrderUpdateEvent {
  orderId: number;
  status: OrderStatus;
  updatedAt: string;
  updatedBy: string;
}

interface DeliveryStatusEvent {
  deliveryId: number;
  status: DeliveryStatus;
  location?: {
    latitude: number;
    longitude: number;
  };
  timestamp: string;
}

interface DriverLocationEvent {
  driverId: number;
  location: {
    latitude: number;
    longitude: number;
  };
  speed?: number;
  heading?: number;
  timestamp: string;
}
```

## Definition of Done

- [x] WebSocket connection with auto-reconnection implemented
- [x] Real-time events updating UI components correctly
- [x] Connection status indicator visible and accurate
- [x] Complete Traditional Chinese localization
- [x] Taiwan-specific formatting (dates, numbers, addresses)
- [x] Integration tests for WebSocket events

## Risk and Compatibility Check

**Minimal Risk Assessment:**

- **Primary Risk:** WebSocket connection stability in production environment
- **Mitigation:** Implement fallback to periodic polling if WebSocket fails
- **Rollback:** Disable real-time features, use manual refresh

**Compatibility Verification:**

- [x] WebSocket protocol matches backend implementation
- [x] Event payloads compatible with backend schemas
- [x] Localization doesn't break existing layouts
- [x] Performance acceptable with real-time updates

---

**Developer Notes:**

This story completes the frontend-backend integration by adding real-time capabilities and full localization. The WebSocket implementation should be resilient to network issues common in mobile scenarios (for future driver app).

Key implementation points:
- Use Socket.io client for compatibility with FastAPI-SocketIO
- Implement event debouncing for high-frequency updates (driver locations)
- Ensure all date/time displays use Taiwan timezone (UTC+8)
- Test with various network conditions (slow, intermittent, offline)

Localization checklist:
- All static UI text
- Dynamic content (status messages, notifications)
- Error messages from backend
- Date/time formatting (民國年 optional)
- Number formatting (thousands separator)
- Currency display (NT$)