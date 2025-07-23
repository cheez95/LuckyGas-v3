/**
 * K6 Performance Test Script for Lucky Gas API
 * Tests API endpoints under various load conditions
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import encoding from 'k6/encoding';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration');
const orderCreationDuration = new Trend('order_creation_duration');
const routeOptimizationDuration = new Trend('route_optimization_duration');
const apiErrors = new Counter('api_errors');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 50 },   // Ramp up to 50 users
    { duration: '10m', target: 100 }, // Stay at 100 users
    { duration: '5m', target: 200 },  // Ramp up to 200 users
    { duration: '10m', target: 200 }, // Stay at 200 users
    { duration: '5m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
    http_req_failed: ['rate<0.1'],     // Error rate must be below 10%
    errors: ['rate<0.1'],              // Custom error rate below 10%
    login_duration: ['p(95)<1000'],    // 95% of logins below 1s
    order_creation_duration: ['p(95)<1500'], // 95% of order creations below 1.5s
  },
};

// Test data
const users = new SharedArray('users', function () {
  return [
    { email: 'office1@luckygas.tw', password: 'Test123!', role: 'office_staff' },
    { email: 'office2@luckygas.tw', password: 'Test123!', role: 'office_staff' },
    { email: 'driver1@luckygas.tw', password: 'Test123!', role: 'driver' },
    { email: 'manager@luckygas.tw', password: 'Test123!', role: 'manager' },
  ];
});

const customers = new SharedArray('customers', function () {
  const data = [];
  for (let i = 1; i <= 100; i++) {
    data.push({
      id: i,
      name: `測試客戶${i}`,
      phone: `091${String(i).padStart(7, '0')}`,
      address: `台北市大安區測試路${i}號`,
    });
  }
  return data;
});

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Helper functions
function authenticateUser(user) {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    http.params.urlencode({
      username: user.email,
      password: user.password,
    }),
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      tags: { name: 'Login' },
    }
  );

  const success = check(loginRes, {
    'login successful': (r) => r.status === 200,
    'access token returned': (r) => r.json('access_token') !== undefined,
  });

  if (!success) {
    errorRate.add(1);
    apiErrors.add(1);
    return null;
  }

  errorRate.add(0);
  loginDuration.add(loginRes.timings.duration);

  return loginRes.json('access_token');
}

function getAuthHeaders(token) {
  return {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };
}

// Test scenarios
export default function () {
  const user = users[Math.floor(Math.random() * users.length)];
  const token = authenticateUser(user);

  if (!token) {
    sleep(1);
    return;
  }

  const authHeaders = getAuthHeaders(token);

  group('Customer Operations', function () {
    // List customers with pagination
    const listRes = http.get(
      `${BASE_URL}/api/v1/customers?page=1&size=20`,
      { ...authHeaders, tags: { name: 'ListCustomers' } }
    );

    check(listRes, {
      'customers listed': (r) => r.status === 200,
      'pagination info present': (r) => r.json('total') !== undefined,
    });

    // Search customers
    const searchRes = http.get(
      `${BASE_URL}/api/v1/customers/search?q=測試`,
      { ...authHeaders, tags: { name: 'SearchCustomers' } }
    );

    check(searchRes, {
      'search successful': (r) => r.status === 200,
    });

    // Get customer details
    const customerId = Math.floor(Math.random() * 100) + 1;
    const detailRes = http.get(
      `${BASE_URL}/api/v1/customers/${customerId}`,
      { ...authHeaders, tags: { name: 'GetCustomerDetail' } }
    );

    check(detailRes, {
      'customer detail retrieved': (r) => r.status === 200 || r.status === 404,
    });
  });

  sleep(1);

  group('Order Management', function () {
    const customer = customers[Math.floor(Math.random() * customers.length)];
    
    // Create order
    const orderData = {
      customer_id: customer.id,
      delivery_date: new Date(Date.now() + 86400000).toISOString().split('T')[0], // Tomorrow
      delivery_time_slot: 'morning',
      items: [
        { product_id: 1, quantity: 2 }, // 20kg cylinders
        { product_id: 2, quantity: 1 }, // 16kg cylinder
      ],
      delivery_address: customer.address,
      notes: '請按門鈴',
      payment_method: 'cash',
    };

    const createOrderRes = http.post(
      `${BASE_URL}/api/v1/orders`,
      JSON.stringify(orderData),
      { ...authHeaders, tags: { name: 'CreateOrder' } }
    );

    const orderCreated = check(createOrderRes, {
      'order created': (r) => r.status === 201,
      'order ID returned': (r) => r.json('id') !== undefined,
    });

    if (orderCreated) {
      orderCreationDuration.add(createOrderRes.timings.duration);
      errorRate.add(0);

      const orderId = createOrderRes.json('id');

      // Get order status
      const statusRes = http.get(
        `${BASE_URL}/api/v1/orders/${orderId}`,
        { ...authHeaders, tags: { name: 'GetOrderStatus' } }
      );

      check(statusRes, {
        'order status retrieved': (r) => r.status === 200,
      });

      // Update order status (if manager or office_staff)
      if (user.role !== 'driver') {
        const updateRes = http.put(
          `${BASE_URL}/api/v1/orders/${orderId}/status`,
          JSON.stringify({ status: 'confirmed', notes: '已確認訂單' }),
          { ...authHeaders, tags: { name: 'UpdateOrderStatus' } }
        );

        check(updateRes, {
          'order status updated': (r) => r.status === 200,
        });
      }
    } else {
      errorRate.add(1);
      apiErrors.add(1);
    }
  });

  sleep(2);

  group('Route Management', function () {
    if (user.role === 'manager' || user.role === 'office_staff') {
      // Get pending orders
      const pendingRes = http.get(
        `${BASE_URL}/api/v1/orders?status=confirmed&delivery_date=${new Date().toISOString().split('T')[0]}`,
        { ...authHeaders, tags: { name: 'GetPendingOrders' } }
      );

      if (pendingRes.status === 200 && pendingRes.json('items').length > 0) {
        const orderIds = pendingRes.json('items').slice(0, 5).map(o => o.id);

        // Create optimized route
        const routeData = {
          route_date: new Date().toISOString().split('T')[0],
          driver_id: 1,
          vehicle_id: 1,
          start_time: '08:00',
          order_ids: orderIds,
          optimize: true,
          optimization_params: {
            algorithm: 'or_tools',
            objective: 'minimize_distance',
          },
        };

        const routeRes = http.post(
          `${BASE_URL}/api/v1/routes`,
          JSON.stringify(routeData),
          { ...authHeaders, tags: { name: 'CreateOptimizedRoute' } }
        );

        const routeCreated = check(routeRes, {
          'route created': (r) => r.status === 201,
          'optimization score present': (r) => r.json('optimization_score') !== undefined,
        });

        if (routeCreated) {
          routeOptimizationDuration.add(routeRes.timings.duration);
        }
      }
    }

    // Driver operations
    if (user.role === 'driver') {
      // Get driver's routes
      const driverRoutesRes = http.get(
        `${BASE_URL}/api/v1/routes?driver_id=me&status=planned`,
        { ...authHeaders, tags: { name: 'GetDriverRoutes' } }
      );

      check(driverRoutesRes, {
        'driver routes retrieved': (r) => r.status === 200,
      });

      // Update location (simulate tracking)
      const locationUpdate = {
        latitude: 25.0330 + (Math.random() - 0.5) * 0.01,
        longitude: 121.5654 + (Math.random() - 0.5) * 0.01,
        speed: Math.random() * 60,
        heading: Math.random() * 360,
        accuracy: 10.0,
      };

      const locationRes = http.post(
        `${BASE_URL}/api/v1/routes/current/location`,
        JSON.stringify(locationUpdate),
        { ...authHeaders, tags: { name: 'UpdateDriverLocation' } }
      );

      check(locationRes, {
        'location updated': (r) => r.status === 200 || r.status === 404,
      });
    }
  });

  sleep(2);

  group('Analytics and Reports', function () {
    if (user.role === 'manager' || user.role === 'office_staff') {
      // Daily statistics
      const statsRes = http.get(
        `${BASE_URL}/api/v1/analytics/daily-stats?date=${new Date().toISOString().split('T')[0]}`,
        { ...authHeaders, tags: { name: 'GetDailyStats' } }
      );

      check(statsRes, {
        'daily stats retrieved': (r) => r.status === 200,
      });

      // Revenue report
      const revenueRes = http.get(
        `${BASE_URL}/api/v1/analytics/revenue?start_date=${new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0]}&end_date=${new Date().toISOString().split('T')[0]}`,
        { ...authHeaders, tags: { name: 'GetRevenueReport' } }
      );

      check(revenueRes, {
        'revenue report retrieved': (r) => r.status === 200,
      });
    }
  });

  sleep(1);

  // Logout
  const logoutRes = http.post(
    `${BASE_URL}/api/v1/auth/logout`,
    null,
    { ...authHeaders, tags: { name: 'Logout' } }
  );

  check(logoutRes, {
    'logout successful': (r) => r.status === 200,
  });
}

// Export summary
export function handleSummary(data) {
  return {
    'stdout': JSON.stringify(data, null, 2),
    '/tmp/k6-api-summary.json': JSON.stringify(data, null, 2),
  };
}