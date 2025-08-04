// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Add TextEncoder/TextDecoder for tests
import { TextEncoder, TextDecoder } from 'util';
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock import.meta.env for Vite
global.import = {
  meta: {
    env: {
      VITE_API_URL: 'http://localhost:8000',
      VITE_WS_URL: 'ws://localhost:8000',
      VITE_ENV: 'test',
      VITE_GOOGLE_MAPS_API_KEY: 'test-key',
    }
  }
} as any;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin: string = '';
  readonly thresholds: ReadonlyArray<number> = [];
  
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return [];
  }
} as any;

// Mock WebSocket
global.WebSocket = class WebSocket {
  url: string;
  readyState: number = 1;
  CONNECTING = 0;
  OPEN = 1;
  CLOSING = 2;
  CLOSED = 3;
  
  constructor(url: string) {
    this.url = url;
  }
  
  send = jest.fn();
  close = jest.fn();
  addEventListener = jest.fn();
  removeEventListener = jest.fn();
} as any;

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor(callback: ResizeObserverCallback) {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: () => new Promise(() => {}),
      language: 'zh-TW',
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
  initReactI18next: {
    type: '3rdParty',
    init: () => {},
  },
}));

// Mock router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  useLocation: () => ({
    pathname: '/',
    search: '',
    hash: '',
    state: null,
  }),
  useParams: () => ({}),
  Link: ({ children, to }: any) => children,
  NavLink: ({ children, to }: any) => children,
}));

// Suppress console errors in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Mock WebSocket context
jest.mock('./contexts/WebSocketContext', () => ({
  WebSocketProvider: ({ children }: { children: React.ReactNode }) => children,
  useWebSocketContext: () => ({
    isConnected: true,
    sendMessage: jest.fn(),
    on: jest.fn(),
    off: jest.fn(),
    error: null,
  }),
}));

// Mock notification context  
jest.mock('./contexts/NotificationContext', () => ({
  NotificationProvider: ({ children }: { children: React.ReactNode }) => children,
  useNotification: () => ({
    api: {
      success: jest.fn(),
      error: jest.fn(),
      info: jest.fn(),
      warning: jest.fn(),
    },
    contextHolder: null,
  }),
}));

// Mock auth context
jest.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
    user: { id: 1, username: 'testuser', role: 'admin' },
    isAuthenticated: true,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
  }),
}));

// Mock useWebSocket hooks
jest.mock('./hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: true,
    ws: null,
    sendMessage: jest.fn(),
    lastMessage: null,
    reconnect: jest.fn(),
    disconnect: jest.fn(),
    error: null,
    readyState: 1,
  }),
  useDriverWebSocket: () => ({
    on: jest.fn(),
    off: jest.fn(),
    emit: jest.fn(),
    updateLocation: jest.fn(),
    updateDeliveryStatus: jest.fn(),
    completedDelivery: jest.fn(),
    isConnected: true,
    error: null,
  }),
  useOfficeWebSocket: () => ({
    on: jest.fn(),
    off: jest.fn(),
    emit: jest.fn(),
    subscribeToCustomerUpdates: jest.fn(),
    unsubscribeFromCustomerUpdates: jest.fn(),
    subscribeToOrderUpdates: jest.fn(),
    unsubscribeFromOrderUpdates: jest.fn(),
    subscribeToRouteUpdates: jest.fn(),
    unsubscribeFromRouteUpdates: jest.fn(),
    isConnected: true,
    error: null,
  }),
}));