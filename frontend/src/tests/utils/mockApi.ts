/**
 * Mock API handlers for testing
 */
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { 
  createMockCustomer, 
  createMockOrder, 
  createMockUser,
  createPaginatedResponse,
  createSuccessResponse,
  createErrorResponse 
} from './mockData';

const API_URL = import.meta.env.VITE_API_URL || 'https://localhost:8000';

// Define mock handlers
export const handlers = [
  // Auth endpoints
  rest.post(`${API_URL}/api/v1/auth/login`, async (req, res, ctx) => {
    const { username, password } = await req.json();
    
    if (username === 'testuser' && password === 'password') {
      return res(
        ctx.status(200),
        ctx.json({
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
          user: createMockUser()
        })
      );
    }
    
    return res(
      ctx.status(401),
      ctx.json({ detail: 'Invalid credentials' })
    );
  }),

  rest.get(`${API_URL}/api/v1/auth/me`, (req, res, ctx) => {
    const auth = req.headers.get('Authorization');
    
    if (auth === 'Bearer mock-jwt-token') {
      return res(ctx.status(200), ctx.json(createMockUser()));
    }
    
    return res(ctx.status(401), ctx.json({ detail: 'Not authenticated' }));
  }),

  // Customer endpoints
  rest.get(`${API_URL}/api/v1/customers`, (req, res, ctx) => {
    const page = Number(req.url.searchParams.get('page') || 1);
    const size = Number(req.url.searchParams.get('size') || 20);
    
    const customers = Array.from({ length: 50 }, (_, i) => 
      createMockCustomer({ id: i + 1 })
    );
    
    return res(
      ctx.status(200),
      ctx.json(createPaginatedResponse(customers, page, size))
    );
  }),

  rest.get(`${API_URL}/api/v1/customers/:id`, (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.status(200),
      ctx.json(createMockCustomer({ id: Number(id) }))
    );
  }),

  rest.post(`${API_URL}/api/v1/customers`, async (req, res, ctx) => {
    const data = await req.json();
    return res(
      ctx.status(201),
      ctx.json(createMockCustomer(data))
    );
  }),

  rest.put(`${API_URL}/api/v1/customers/:id`, async (req, res, ctx) => {
    const { id } = req.params;
    const data = await req.json();
    return res(
      ctx.status(200),
      ctx.json(createMockCustomer({ ...data, id: Number(id) }))
    );
  }),

  // Order endpoints
  rest.get(`${API_URL}/api/v1/orders`, (req, res, ctx) => {
    const page = Number(req.url.searchParams.get('page') || 1);
    const size = Number(req.url.searchParams.get('size') || 20);
    
    const orders = Array.from({ length: 100 }, (_, i) => 
      createMockOrder({ id: i + 1 })
    );
    
    return res(
      ctx.status(200),
      ctx.json(createPaginatedResponse(orders, page, size))
    );
  }),

  rest.get(`${API_URL}/api/v1/orders/:id`, (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.status(200),
      ctx.json(createMockOrder({ id: Number(id) }))
    );
  }),

  rest.post(`${API_URL}/api/v1/orders`, async (req, res, ctx) => {
    const data = await req.json();
    return res(
      ctx.status(201),
      ctx.json(createMockOrder(data))
    );
  }),

  rest.put(`${API_URL}/api/v1/orders/:id/status`, async (req, res, ctx) => {
    const { id } = req.params;
    const { status } = await req.json();
    return res(
      ctx.status(200),
      ctx.json(createMockOrder({ id: Number(id), status }))
    );
  }),

  // Health check
  rest.get(`${API_URL}/api/v1/health`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ status: 'healthy', timestamp: new Date().toISOString() })
    );
  }),
];

// Create mock server
export const server = setupServer(...handlers);

// Helper functions for tests
export const mockApiError = (endpoint: string, status: number = 500, message: string = 'Internal Server Error') => {
  server.use(
    rest.get(`${API_URL}${endpoint}`, (req, res, ctx) => {
      return res(
        ctx.status(status),
        ctx.json(createErrorResponse(message, status))
      );
    })
  );
};

export const mockApiDelay = (endpoint: string, delay: number = 1000) => {
  server.use(
    rest.get(`${API_URL}${endpoint}`, (req, res, ctx) => {
      return res(
        ctx.delay(delay),
        ctx.status(200),
        ctx.json(createSuccessResponse({}))
      );
    })
  );
};

export const mockApiSuccess = (method: 'get' | 'post' | 'put' | 'delete', endpoint: string, data: any) => {
  const restMethod = rest[method];
  server.use(
    restMethod(`${API_URL}${endpoint}`, (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json(data)
      );
    })
  );
};

// Setup and teardown helpers
export const setupMockServer = () => {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
};

// Mock localStorage
export class LocalStorageMock {
  private store: { [key: string]: string } = {};

  getItem(key: string): string | null {
    return this.store[key] || null;
  }

  setItem(key: string, value: string): void {
    this.store[key] = value;
  }

  removeItem(key: string): void {
    delete this.store[key];
  }

  clear(): void {
    this.store = {};
  }

  key(index: number): string | null {
    const keys = Object.keys(this.store);
    return keys[index] || null;
  }

  get length(): number {
    return Object.keys(this.store).length;
  }
}

// Mock WebSocket
export class WebSocketMock {
  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }

  send(data: string): void {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Echo back for testing
    setTimeout(() => {
      if (this.onmessage) {
        this.onmessage(new MessageEvent('message', { data }));
      }
    }, 0);
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper method to simulate receiving a message
  simulateMessage(data: any): void {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { 
        data: typeof data === 'string' ? data : JSON.stringify(data) 
      }));
    }
  }

  // Helper method to simulate error
  simulateError(): void {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}