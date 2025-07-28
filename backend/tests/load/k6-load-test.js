import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// Custom metrics
const apiErrorRate = new Rate('api_errors');
const apiResponseTime = new Trend('api_response_time');
const loginSuccess = new Rate('login_success');
const orderCreationTime = new Trend('order_creation_time');
const routeOptimizationTime = new Trend('route_optimization_time');

// Test configuration for 1000 concurrent users
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '3m', target: 500 },   // Ramp up to 500 users
    { duration: '5m', target: 1000 },  // Ramp up to 1000 users
    { duration: '10m', target: 1000 }, // Stay at 1000 users
    { duration: '3m', target: 500 },   // Ramp down to 500
    { duration: '2m', target: 0 },     // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<100', 'p(99)<200'], // 95% < 100ms, 99% < 200ms
    http_req_failed: ['rate<0.001'],                // Error rate < 0.1%
    api_errors: ['rate<0.001'],                     // API error rate < 0.1%
    api_response_time: ['p(95)<100'],               // API p95 < 100ms
  },
  ext: {
    loadimpact: {
      projectID: 'luckygas-v3',
      name: 'Production Load Test - 1000 Users',
    },
  },
};

// Test data
const users = new SharedArray('users', function () {
  const data = [];
  for (let i = 0; i < 100; i++) {
    data.push({
      username: `test_user_${i}@luckygas.com`,
      password: 'password123',
      role: i < 70 ? 'office' : i < 90 ? 'driver' : 'manager',
    });
  }
  return data;
});

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Helper functions
function authenticateUser(user) {
  const res = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    username: user.username,
    password: user.password,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  const success = check(res, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('access_token') !== '',
  });

  loginSuccess.add(success);
  
  if (success) {
    return res.json('access_token');
  }
  return null;
}

// Main test scenarios
export default function () {
  const user = users[Math.floor(Math.random() * users.length)];
  const token = authenticateUser(user);

  if (!token) {
    apiErrorRate.add(1);
    return;
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Scenario based on user role
  switch (user.role) {
    case 'office':
      officeStaffScenario(headers);
      break;
    case 'driver':
      driverScenario(headers);
      break;
    case 'manager':
      managerScenario(headers);
      break;
  }

  sleep(Math.random() * 3 + 1); // Random think time 1-4 seconds
}

function officeStaffScenario(headers) {
  // Get customer list
  let res = http.get(`${BASE_URL}/api/v1/customers?page=1&size=20`, { headers });
  apiResponseTime.add(res.timings.duration);
  
  check(res, {
    'customers retrieved': (r) => r.status === 200,
    'response time OK': (r) => r.timings.duration < 100,
  }) || apiErrorRate.add(1);

  // Create new order
  const orderStart = Date.now();
  res = http.post(`${BASE_URL}/api/v1/orders`, JSON.stringify({
    customer_id: Math.floor(Math.random() * 1000) + 1,
    products: [
      {
        product_id: 1,
        quantity: Math.floor(Math.random() * 5) + 1,
      },
    ],
    delivery_date: new Date(Date.now() + 86400000).toISOString(),
    delivery_time_slot: 'morning',
  }), { headers });
  
  orderCreationTime.add(Date.now() - orderStart);
  
  check(res, {
    'order created': (r) => r.status === 201,
    'order ID returned': (r) => r.json('id') > 0,
  }) || apiErrorRate.add(1);

  // Search orders
  res = http.get(`${BASE_URL}/api/v1/orders/search?q=test&status=pending`, { headers });
  apiResponseTime.add(res.timings.duration);
  
  check(res, {
    'search completed': (r) => r.status === 200,
    'search fast': (r) => r.timings.duration < 200,
  }) || apiErrorRate.add(1);
}

function driverScenario(headers) {
  // Get assigned routes
  let res = http.get(`${BASE_URL}/api/v1/drivers/routes/today`, { headers });
  apiResponseTime.add(res.timings.duration);
  
  check(res, {
    'routes retrieved': (r) => r.status === 200,
    'routes response fast': (r) => r.timings.duration < 100,
  }) || apiErrorRate.add(1);

  // Update delivery status
  const deliveryId = Math.floor(Math.random() * 1000) + 1;
  res = http.patch(`${BASE_URL}/api/v1/deliveries/${deliveryId}/status`, JSON.stringify({
    status: 'in_progress',
    location: {
      latitude: 25.0330 + (Math.random() - 0.5) * 0.1,
      longitude: 121.5654 + (Math.random() - 0.5) * 0.1,
    },
  }), { headers });
  
  apiResponseTime.add(res.timings.duration);
  
  check(res, {
    'status updated': (r) => r.status === 200,
    'update fast': (r) => r.timings.duration < 50,
  }) || apiErrorRate.add(1);

  // Upload delivery proof
  const photoData = open('./test-assets/delivery-proof.jpg', 'b');
  const formData = {
    photo: http.file(photoData, 'proof.jpg'),
    signature: 'base64_signature_data_here',
  };
  
  res = http.post(`${BASE_URL}/api/v1/deliveries/${deliveryId}/complete`, formData, { headers });
  
  check(res, {
    'delivery completed': (r) => r.status === 200,
    'completion processed': (r) => r.timings.duration < 500,
  }) || apiErrorRate.add(1);
}

function managerScenario(headers) {
  // Get performance metrics
  let res = http.get(`${BASE_URL}/api/v1/analytics/dashboard`, { headers });
  apiResponseTime.add(res.timings.duration);
  
  check(res, {
    'analytics loaded': (r) => r.status === 200,
    'analytics fast': (r) => r.timings.duration < 200,
  }) || apiErrorRate.add(1);

  // Optimize routes
  const optimizeStart = Date.now();
  res = http.post(`${BASE_URL}/api/v1/routes/optimize`, JSON.stringify({
    date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    area: '信義區',
    constraints: {
      max_stops_per_route: 30,
      max_route_duration: 480, // 8 hours
      vehicle_capacity: 50,
    },
  }), { headers });
  
  routeOptimizationTime.add(Date.now() - optimizeStart);
  
  check(res, {
    'routes optimized': (r) => r.status === 200,
    'optimization complete': (r) => (Date.now() - optimizeStart) < 5000, // < 5 seconds
  }) || apiErrorRate.add(1);

  // Assign routes to drivers
  if (res.status === 200) {
    const routes = res.json('routes') || [];
    if (routes.length > 0) {
      const routeId = routes[0].id;
      res = http.patch(`${BASE_URL}/api/v1/routes/${routeId}/assign`, JSON.stringify({
        driver_id: Math.floor(Math.random() * 50) + 1,
      }), { headers });
      
      check(res, {
        'route assigned': (r) => r.status === 200,
      }) || apiErrorRate.add(1);
    }
  }
}

// WebSocket test (separate scenario)
export function websocketScenario() {
  const url = `ws://localhost:8000/ws`;
  const params = {
    headers: {
      'Authorization': `Bearer ${authenticateUser(users[0])}`,
    },
  };

  const res = ws.connect(url, params, function (socket) {
    socket.on('open', () => {
      console.log('WebSocket connected');
      
      // Subscribe to updates
      socket.send(JSON.stringify({
        type: 'subscribe',
        channel: 'order_updates',
      }));
    });

    socket.on('message', (data) => {
      const message = JSON.parse(data);
      check(message, {
        'valid message format': (m) => m.type && m.data,
      });
    });

    socket.on('error', (e) => {
      console.error('WebSocket error:', e);
      apiErrorRate.add(1);
    });

    // Simulate activity
    socket.setTimeout(function () {
      socket.send(JSON.stringify({
        type: 'location_update',
        data: {
          latitude: 25.0330,
          longitude: 121.5654,
        },
      }));
    }, 5000);

    socket.setTimeout(function () {
      socket.close();
    }, 30000);
  });

  check(res, { 'WebSocket connection successful': (r) => r && r.status === 101 });
}

// Summary handler
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'load-test-results.json': JSON.stringify(data, null, 2),
    'load-test-results.html': htmlReport(data),
  };
}