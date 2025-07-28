import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const loginSuccessRate = new Rate('login_success');
const orderCreationRate = new Rate('order_creation_success');
const reportGenerationRate = new Rate('report_generation_success');

// Test configuration
const BASE_URL = __ENV.BASE_URL || 'https://api.luckygas.com.tw';
const MAX_VUS = __ENV.MAX_VUS || '1000';

// Load test data
const testUsers = new SharedArray('users', function () {
  return JSON.parse(open('./test-data/users.json'));
});

const testOrders = new SharedArray('orders', function () {
  return JSON.parse(open('./test-data/orders.json'));
});

// Test scenarios
export const options = {
  scenarios: {
    // Scenario 1: Login surge (morning shift start)
    login_surge: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 500 }, // Ramp up to 500 users
        { duration: '5m', target: 500 }, // Stay at 500 users
        { duration: '2m', target: 0 },   // Ramp down
      ],
      gracefulRampDown: '30s',
      exec: 'loginSurgeTest',
    },
    
    // Scenario 2: Order creation peak (lunch time)
    order_creation_peak: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '3m', target: 300 },  // Ramp up
        { duration: '10m', target: 300 }, // Sustained load
        { duration: '2m', target: 600 },  // Peak surge
        { duration: '5m', target: 600 },  // Sustained peak
        { duration: '3m', target: 0 },    // Ramp down
      ],
      gracefulRampDown: '30s',
      exec: 'orderCreationTest',
      startTime: '10m', // Start after login surge
    },
    
    // Scenario 3: Report generation (end of day)
    report_generation: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      stages: [
        { duration: '2m', target: 50 },   // Increase to 50 RPS
        { duration: '5m', target: 100 },  // Peak at 100 RPS
        { duration: '3m', target: 20 },   // Reduce load
      ],
      preAllocatedVUs: 200,
      maxVUs: 400,
      exec: 'reportGenerationTest',
      startTime: '25m', // Start after order creation
    },
    
    // Scenario 4: Database connection pool stress
    db_connection_stress: {
      executor: 'constant-vus',
      vus: 200,
      duration: '10m',
      exec: 'databaseStressTest',
      startTime: '35m',
    },
    
    // Scenario 5: Mixed realistic load
    mixed_load: {
      executor: 'ramping-vus',
      startVUs: 50,
      stages: [
        { duration: '5m', target: 200 },   // Morning ramp up
        { duration: '10m', target: 400 },  // Mid-morning
        { duration: '10m', target: 800 },  // Lunch peak
        { duration: '10m', target: 1000 }, // 2x peak traffic
        { duration: '10m', target: 600 },  // Afternoon
        { duration: '5m', target: 200 },   // Evening wind down
      ],
      exec: 'mixedLoadTest',
      startTime: '45m',
    },
  },
  
  thresholds: {
    // Performance thresholds
    http_req_duration: [
      'p(95)<200', // 95% of requests must complete within 200ms
      'p(99)<500', // 99% of requests must complete within 500ms
    ],
    http_req_failed: ['rate<0.01'], // Error rate must be below 1%
    
    // Custom metric thresholds
    errors: ['rate<0.05'],
    login_success: ['rate>0.95'],
    order_creation_success: ['rate>0.95'],
    report_generation_success: ['rate>0.90'],
    
    // Database connection thresholds
    'http_req_duration{scenario:db_connection_stress}': ['p(95)<100'],
  },
};

// Helper functions
function getAuthToken(username, password) {
  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, 
    JSON.stringify({ username, password }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  
  const success = check(loginRes, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('access_token') !== '',
  });
  
  loginSuccessRate.add(success);
  errorRate.add(!success);
  
  return success ? loginRes.json('access_token') : null;
}

// Test functions
export function loginSurgeTest() {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];
  
  const startTime = new Date();
  const token = getAuthToken(user.username, user.password);
  const duration = new Date() - startTime;
  
  check(duration, {
    'login completed within SLA': (d) => d < 200,
  });
  
  if (token) {
    // Simulate user activity after login
    const headers = { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    
    // Get dashboard data
    const dashboardRes = http.get(`${BASE_URL}/api/v1/dashboard`, { headers });
    check(dashboardRes, {
      'dashboard loaded': (r) => r.status === 200,
    });
    
    // Get user profile
    const profileRes = http.get(`${BASE_URL}/api/v1/users/me`, { headers });
    check(profileRes, {
      'profile loaded': (r) => r.status === 200,
    });
  }
  
  sleep(Math.random() * 3 + 1); // Random think time
}

export function orderCreationTest() {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];
  const token = getAuthToken(user.username, user.password);
  
  if (!token) {
    errorRate.add(1);
    return;
  }
  
  const headers = { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
  
  // Create order batch (simulating office staff creating multiple orders)
  const orderBatch = [];
  const batchSize = Math.floor(Math.random() * 5) + 1; // 1-5 orders
  
  for (let i = 0; i < batchSize; i++) {
    const order = testOrders[Math.floor(Math.random() * testOrders.length)];
    orderBatch.push({
      ...order,
      delivery_date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
      notes: `Load test order ${__VU}-${__ITER}-${i}`,
    });
  }
  
  // Create orders
  const createRes = http.post(
    `${BASE_URL}/api/v1/orders/batch`,
    JSON.stringify({ orders: orderBatch }),
    { headers, timeout: '30s' }
  );
  
  const success = check(createRes, {
    'batch order created': (r) => r.status === 201,
    'order IDs returned': (r) => r.json('order_ids') && r.json('order_ids').length === batchSize,
  });
  
  orderCreationRate.add(success);
  errorRate.add(!success);
  
  if (success) {
    // Simulate order status checks
    const orderIds = createRes.json('order_ids');
    sleep(2);
    
    // Check order status
    const statusRes = http.get(
      `${BASE_URL}/api/v1/orders/${orderIds[0]}`,
      { headers }
    );
    
    check(statusRes, {
      'order status retrieved': (r) => r.status === 200,
    });
  }
  
  sleep(Math.random() * 5 + 2); // Longer think time for order creation
}

export function reportGenerationTest() {
  const user = testUsers.find(u => u.role === 'manager' || u.role === 'admin');
  const token = getAuthToken(user.username, user.password);
  
  if (!token) {
    errorRate.add(1);
    return;
  }
  
  const headers = { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
  
  // Generate different types of reports
  const reportTypes = [
    { type: 'daily-summary', params: { date: new Date().toISOString().split('T')[0] } },
    { type: 'delivery-performance', params: { period: 'week' } },
    { type: 'customer-analysis', params: { limit: 100 } },
    { type: 'revenue-report', params: { month: new Date().getMonth() + 1 } },
    { type: 'inventory-status', params: { warehouse_id: 'all' } },
  ];
  
  const report = reportTypes[Math.floor(Math.random() * reportTypes.length)];
  
  const reportRes = http.post(
    `${BASE_URL}/api/v1/reports/generate`,
    JSON.stringify(report),
    { headers, timeout: '60s' }
  );
  
  const success = check(reportRes, {
    'report generation initiated': (r) => r.status === 202,
    'job ID returned': (r) => r.json('job_id') !== '',
  });
  
  reportGenerationRate.add(success);
  errorRate.add(!success);
  
  if (success) {
    const jobId = reportRes.json('job_id');
    sleep(2);
    
    // Poll for report completion
    let attempts = 0;
    let completed = false;
    
    while (attempts < 10 && !completed) {
      const statusRes = http.get(
        `${BASE_URL}/api/v1/reports/status/${jobId}`,
        { headers }
      );
      
      if (statusRes.status === 200 && statusRes.json('status') === 'completed') {
        completed = true;
        
        // Download report
        const downloadRes = http.get(
          `${BASE_URL}/api/v1/reports/download/${jobId}`,
          { headers, responseType: 'binary' }
        );
        
        check(downloadRes, {
          'report downloaded': (r) => r.status === 200,
          'report size reasonable': (r) => r.body.length > 1000,
        });
      }
      
      attempts++;
      if (!completed) sleep(3);
    }
  }
  
  sleep(Math.random() * 10 + 5); // Reports are less frequent
}

export function databaseStressTest() {
  const user = testUsers[Math.floor(Math.random() * testUsers.length)];
  const token = getAuthToken(user.username, user.password);
  
  if (!token) {
    errorRate.add(1);
    return;
  }
  
  const headers = { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
  
  // Perform database-heavy operations
  const operations = [
    // Complex customer search
    () => {
      const searchRes = http.get(
        `${BASE_URL}/api/v1/customers/search?q=王&include_orders=true&limit=50`,
        { headers }
      );
      return check(searchRes, {
        'customer search completed': (r) => r.status === 200,
        'search results returned': (r) => r.json('customers') !== null,
      });
    },
    
    // Order history with aggregations
    () => {
      const historyRes = http.get(
        `${BASE_URL}/api/v1/orders/history?days=30&include_stats=true`,
        { headers }
      );
      return check(historyRes, {
        'order history retrieved': (r) => r.status === 200,
        'statistics calculated': (r) => r.json('stats') !== null,
      });
    },
    
    // Route optimization (heavy computation)
    () => {
      const routeData = {
        date: new Date(Date.now() + 86400000).toISOString(),
        warehouse_id: 'WH001',
        max_stops: 50,
        optimization_level: 'advanced',
      };
      
      const routeRes = http.post(
        `${BASE_URL}/api/v1/routes/optimize`,
        JSON.stringify(routeData),
        { headers, timeout: '45s' }
      );
      
      return check(routeRes, {
        'route optimization completed': (r) => r.status === 200,
        'routes generated': (r) => r.json('routes') && r.json('routes').length > 0,
      });
    },
    
    // Analytics query
    () => {
      const analyticsRes = http.get(
        `${BASE_URL}/api/v1/analytics/trends?metric=delivery_time&period=month&groupBy=district`,
        { headers }
      );
      return check(analyticsRes, {
        'analytics query completed': (r) => r.status === 200,
        'data points returned': (r) => r.json('data') && r.json('data').length > 0,
      });
    },
  ];
  
  // Execute random operation
  const operation = operations[Math.floor(Math.random() * operations.length)];
  const success = operation();
  errorRate.add(!success);
  
  sleep(Math.random() * 2 + 0.5);
}

export function mixedLoadTest() {
  const scenario = Math.random();
  
  if (scenario < 0.4) {
    // 40% order operations
    orderCreationTest();
  } else if (scenario < 0.7) {
    // 30% login/dashboard
    loginSurgeTest();
  } else if (scenario < 0.85) {
    // 15% database heavy
    databaseStressTest();
  } else {
    // 15% reports
    reportGenerationTest();
  }
}

// Lifecycle hooks
export function setup() {
  // Warm up the system
  console.log('Warming up the system...');
  const warmupRes = http.get(`${BASE_URL}/health`);
  check(warmupRes, {
    'system is healthy': (r) => r.status === 200,
  });
  
  return { startTime: new Date() };
}

export function teardown(data) {
  console.log(`Test completed. Duration: ${new Date() - data.startTime}ms`);
}

// Custom summary
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.html': htmlReport(data),
    'summary.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  // Custom text summary implementation
  return `
Load Test Summary
=================
Total Requests: ${data.metrics.http_reqs.values.count}
Success Rate: ${(1 - data.metrics.http_req_failed.values.rate) * 100}%
Average Response Time: ${data.metrics.http_req_duration.values.avg}ms
P95 Response Time: ${data.metrics.http_req_duration.values['p(95)']}ms
P99 Response Time: ${data.metrics.http_req_duration.values['p(99)']}ms

Scenario Results:
- Login Success Rate: ${data.metrics.login_success.values.rate * 100}%
- Order Creation Success: ${data.metrics.order_creation_success.values.rate * 100}%
- Report Generation Success: ${data.metrics.report_generation_success.values.rate * 100}%
- Overall Error Rate: ${data.metrics.errors.values.rate * 100}%
`;
}

function htmlReport(data) {
  // Generate HTML report
  return `
<!DOCTYPE html>
<html>
<head>
    <title>LuckyGas Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { margin: 10px 0; padding: 10px; background: #f5f5f5; }
        .pass { color: green; }
        .fail { color: red; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>LuckyGas Load Test Report</h1>
    <h2>Test Configuration</h2>
    <p>Max VUs: ${MAX_VUS}</p>
    <p>Test Duration: ${data.state.testRunDurationMs / 1000 / 60} minutes</p>
    
    <h2>Performance Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Threshold</th>
            <th>Status</th>
        </tr>
        <tr>
            <td>P95 Response Time</td>
            <td>${data.metrics.http_req_duration.values['p(95)']}ms</td>
            <td>&lt; 200ms</td>
            <td class="${data.metrics.http_req_duration.values['p(95)'] < 200 ? 'pass' : 'fail'}">
                ${data.metrics.http_req_duration.values['p(95)'] < 200 ? 'PASS' : 'FAIL'}
            </td>
        </tr>
        <tr>
            <td>Error Rate</td>
            <td>${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%</td>
            <td>&lt; 1%</td>
            <td class="${data.metrics.http_req_failed.values.rate < 0.01 ? 'pass' : 'fail'}">
                ${data.metrics.http_req_failed.values.rate < 0.01 ? 'PASS' : 'FAIL'}
            </td>
        </tr>
    </table>
    
    <h2>Scenario Performance</h2>
    <table>
        <tr>
            <th>Scenario</th>
            <th>Requests</th>
            <th>Success Rate</th>
            <th>Avg Response Time</th>
        </tr>
        ${Object.entries(data.metrics).filter(([key]) => key.includes('scenario')).map(([key, value]) => `
        <tr>
            <td>${key}</td>
            <td>${value.values.count}</td>
            <td>${((1 - value.values.rate) * 100).toFixed(2)}%</td>
            <td>${value.values.avg}ms</td>
        </tr>
        `).join('')}
    </table>
</body>
</html>
`;
}