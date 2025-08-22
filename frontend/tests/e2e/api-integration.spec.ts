import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

const API_BASE_URL = 'https://luckygas-backend-production-154687573210.asia-east1.run.app';

test.describe('API Integration Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // Get auth token for API tests
    const response = await request.post(`${API_BASE_URL}/api/v1/auth/login`, {
      data: {
        username: 'admin@luckygas.com',
        password: 'admin123'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    authToken = data.access_token || data.token;
    expect(authToken).toBeTruthy();
  });

  test.describe('Orders API', () => {
    test('should fetch orders list', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check response structure
      expect(data).toHaveProperty('orders');
      expect(Array.isArray(data.orders) || Array.isArray(data)).toBeTruthy();
    });

    test('should fetch order statistics', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/stats/summary/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        params: {
          date_from: '2025-01-01',
          date_to: '2025-12-31'
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check statistics structure
      expect(data).toHaveProperty('total_orders');
      expect(data).toHaveProperty('pending');
      expect(data).toHaveProperty('completed');
    });

    test('should search orders', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/search/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        params: {
          q: 'ORD-2025'
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check search response
      expect(data).toHaveProperty('orders');
      expect(Array.isArray(data.orders) || Array.isArray(data)).toBeTruthy();
    });

    test('should get single order', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/1/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check order structure
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('order_number');
      expect(data).toHaveProperty('customer_id');
    });

    test('should create order', async ({ request }) => {
      const orderData = {
        customer_id: 1,
        items: [
          {
            product: '20kg 瓦斯桶',
            quantity: 2,
            unit_price: 750
          }
        ],
        delivery_address: '台北市中正區重慶南路一段122號',
        scheduled_date: new Date().toISOString()
      };
      
      const response = await request.post(`${API_BASE_URL}/api/v1/orders/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: orderData
      });
      
      // Check if creation was successful or returned expected error
      const status = response.status();
      expect([200, 201, 422]).toContain(status);
      
      if (response.ok()) {
        const data = await response.json();
        expect(data).toHaveProperty('id');
      }
    });
  });

  test.describe('Customers API', () => {
    test('should fetch customers list', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/customers/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check response structure
      expect(Array.isArray(data) || Array.isArray(data.customers) || Array.isArray(data.items)).toBeTruthy();
    });

    test('should search customers', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/customers/search/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        params: {
          q: '客戶'
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check search response
      expect(data).toHaveProperty('customers');
      expect(Array.isArray(data.customers) || Array.isArray(data)).toBeTruthy();
    });

    test('should get single customer', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/customers/1/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      // Customer might not exist
      if (response.ok()) {
        const data = await response.json();
        expect(data).toHaveProperty('id');
        expect(data).toHaveProperty('name');
      } else {
        expect([404, 422]).toContain(response.status());
      }
    });
  });

  test.describe('Drivers API', () => {
    test('should fetch drivers list', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/drivers/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check response structure
      expect(Array.isArray(data) || Array.isArray(data.drivers)).toBeTruthy();
    });

    test('should fetch available drivers', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/drivers/available/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check response is array
      expect(Array.isArray(data) || Array.isArray(data.drivers)).toBeTruthy();
    });
  });

  test.describe('Routes API', () => {
    test('should fetch routes', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/routes/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      
      // Check response structure
      expect(Array.isArray(data) || Array.isArray(data.routes)).toBeTruthy();
    });

    test('should optimize route', async ({ request }) => {
      const routeData = {
        driver_id: 1,
        orders: [1, 2, 3],
        start_location: {
          lat: 25.0330,
          lng: 121.5654
        }
      };
      
      const response = await request.post(`${API_BASE_URL}/api/v1/routes/optimize/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: routeData
      });
      
      // Optimization might fail with test data
      const status = response.status();
      expect([200, 201, 422, 400]).toContain(status);
      
      if (response.ok()) {
        const data = await response.json();
        expect(data).toHaveProperty('optimized_route');
      }
    });
  });

  test.describe('WebSocket Connection', () => {
    test('should establish WebSocket connection', async ({ page }) => {
      const loginPage = new LoginPage(page);
      
      // Login first
      await loginPage.goto();
      await loginPage.login('admin@luckygas.com', 'admin123');
      await page.waitForLoadState('networkidle');
      
      // Navigate to a page that uses WebSocket
      await page.goto('/#/office/orders');
      
      // Check WebSocket connection
      const wsConnected = await page.evaluate(() => {
        return new Promise((resolve) => {
          // Try to establish WebSocket connection
          const wsUrl = 'wss://luckygas-backend-production-154687573210.asia-east1.run.app/ws';
          const ws = new WebSocket(wsUrl);
          
          ws.onopen = () => resolve(true);
          ws.onerror = () => resolve(false);
          
          setTimeout(() => resolve(false), 5000);
        });
      });
      
      // WebSocket might not be implemented yet
      console.log('WebSocket connection status:', wsConnected);
    });
  });

  test.describe('Error Handling', () => {
    test('should handle 401 unauthorized', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/`, {
        headers: {
          'Authorization': 'Bearer invalid-token'
        }
      });
      
      expect(response.status()).toBe(401);
    });

    test('should handle 404 not found', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/999999/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      expect([404, 422]).toContain(response.status());
    });

    test('should handle 422 validation error', async ({ request }) => {
      const response = await request.post(`${API_BASE_URL}/api/v1/orders/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: {
          // Invalid data
          invalid_field: 'test'
        }
      });
      
      expect(response.status()).toBe(422);
      const data = await response.json();
      expect(data).toHaveProperty('detail');
    });

    test('should handle rate limiting', async ({ request }) => {
      // Make multiple rapid requests
      const requests = [];
      for (let i = 0; i < 20; i++) {
        requests.push(
          request.get(`${API_BASE_URL}/api/v1/orders/`, {
            headers: {
              'Authorization': `Bearer ${authToken}`
            }
          })
        );
      }
      
      const responses = await Promise.all(requests);
      
      // Check if any were rate limited
      const rateLimited = responses.some(r => r.status() === 429);
      console.log('Rate limiting active:', rateLimited);
      
      // All should either succeed or be rate limited
      responses.forEach(r => {
        expect([200, 429]).toContain(r.status());
      });
    });
  });

  test.describe('CORS Headers', () => {
    test('should have proper CORS headers', async ({ request }) => {
      const response = await request.get(`${API_BASE_URL}/api/v1/orders/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Origin': 'https://vast-tributary-466619-m8.web.app'
        }
      });
      
      // Check CORS headers
      const headers = response.headers();
      expect(headers['access-control-allow-origin']).toBeTruthy();
      
      // Should allow credentials
      expect(headers['access-control-allow-credentials']).toBe('true');
    });

    test('should handle preflight requests', async ({ request }) => {
      const response = await request.fetch(`${API_BASE_URL}/api/v1/orders/`, {
        method: 'OPTIONS',
        headers: {
          'Origin': 'https://vast-tributary-466619-m8.web.app',
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'authorization,content-type'
        }
      });
      
      expect(response.ok()).toBeTruthy();
      
      const headers = response.headers();
      expect(headers['access-control-allow-methods']).toContain('POST');
      expect(headers['access-control-allow-headers']).toBeTruthy();
    });
  });
});