/**
 * K6 Performance Test Script for Lucky Gas WebSocket
 * Tests WebSocket connections, message throughput, and real-time features
 */

import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter, Gauge } from 'k6/metrics';

// Custom metrics
const wsConnectionTime = new Trend('ws_connection_time');
const wsMessagesSent = new Counter('ws_messages_sent');
const wsMessagesReceived = new Counter('ws_messages_received');
const wsMessageLatency = new Trend('ws_message_latency');
const wsConnectionsActive = new Gauge('ws_connections_active');
const wsErrorRate = new Rate('ws_errors');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 50 },    // Ramp up to 50 connections
    { duration: '3m', target: 200 },   // Ramp up to 200 connections
    { duration: '5m', target: 500 },   // Ramp up to 500 connections
    { duration: '10m', target: 500 },  // Stay at 500 connections
    { duration: '3m', target: 1000 },  // Stress test: 1000 connections
    { duration: '5m', target: 1000 },  // Maintain stress level
    { duration: '5m', target: 0 },     // Ramp down
  ],
  thresholds: {
    ws_connection_time: ['p(95)<5000'],     // 95% connect within 5s
    ws_message_latency: ['p(95)<1000'],     // 95% messages within 1s
    ws_errors: ['rate<0.05'],               // Error rate below 5%
    ws_connections_active: ['value>0'],      // At least some connections active
  },
};

const BASE_URL = __ENV.BASE_URL || 'localhost:8000';
const WS_URL = `ws://${BASE_URL}/api/v1/websocket`;

// Test user types
const userTypes = [
  { type: 'office', token: 'office_token_123', endpoint: 'ws/office' },
  { type: 'driver', token: 'driver_token_456', endpoint: 'ws/driver' },
  { type: 'general', token: 'general_token_789', endpoint: 'ws' },
];

// Message types to simulate
const messageTypes = [
  {
    type: 'order_update',
    generator: () => ({
      type: 'order_update',
      data: {
        order_id: Math.floor(Math.random() * 1000),
        status: ['pending', 'confirmed', 'in_delivery', 'delivered'][Math.floor(Math.random() * 4)],
        timestamp: new Date().toISOString(),
      },
    }),
  },
  {
    type: 'location_update',
    generator: () => ({
      type: 'location_update',
      data: {
        driver_id: Math.floor(Math.random() * 50),
        latitude: 25.0330 + (Math.random() - 0.5) * 0.1,
        longitude: 121.5654 + (Math.random() - 0.5) * 0.1,
        speed: Math.random() * 60,
        timestamp: new Date().toISOString(),
      },
    }),
  },
  {
    type: 'notification',
    generator: () => ({
      type: 'notification',
      data: {
        title: '系統通知',
        message: `測試通知 ${Math.random().toString(36).substring(7)}`,
        level: ['info', 'warning', 'error'][Math.floor(Math.random() * 3)],
        timestamp: new Date().toISOString(),
      },
    }),
  },
  {
    type: 'ping',
    generator: () => ({
      type: 'ping',
      timestamp: Date.now(),
    }),
  },
];

export default function () {
  const userType = userTypes[Math.floor(Math.random() * userTypes.length)];
  const url = `${WS_URL}/${userType.endpoint}?token=${userType.token}`;
  
  const connectionStart = Date.now();
  let messageCount = 0;
  let errorCount = 0;
  let lastPingTime = Date.now();
  let isConnected = false;

  const res = ws.connect(url, {}, function (socket) {
    socket.on('open', () => {
      const connectionDuration = Date.now() - connectionStart;
      wsConnectionTime.add(connectionDuration);
      wsConnectionsActive.add(1);
      isConnected = true;
      console.log(`WebSocket connected in ${connectionDuration}ms`);

      // Send initial authentication/subscription messages
      socket.send(JSON.stringify({
        type: 'subscribe',
        channels: ['orders', 'deliveries', 'notifications'],
      }));
    });

    socket.on('message', (data) => {
      wsMessagesReceived.add(1);
      messageCount++;

      try {
        const message = JSON.parse(data);
        
        // Handle different message types
        switch (message.type) {
          case 'pong':
            const latency = Date.now() - lastPingTime;
            wsMessageLatency.add(latency);
            break;
            
          case 'order_update':
            // Simulate order update handling
            check(message, {
              'order update has order_id': (m) => m.data && m.data.order_id !== undefined,
              'order update has status': (m) => m.data && m.data.status !== undefined,
            });
            break;
            
          case 'notification':
            // Simulate notification handling
            check(message, {
              'notification has title': (m) => m.data && m.data.title !== undefined,
              'notification has message': (m) => m.data && m.data.message !== undefined,
            });
            break;
            
          case 'location_update':
            // Simulate location update handling
            check(message, {
              'location has coordinates': (m) => 
                m.data && m.data.latitude !== undefined && m.data.longitude !== undefined,
            });
            break;
        }
        
        wsErrorRate.add(0);
      } catch (e) {
        console.error('Failed to parse message:', e);
        errorCount++;
        wsErrorRate.add(1);
      }
    });

    socket.on('error', (e) => {
      console.error('WebSocket error:', e);
      errorCount++;
      wsErrorRate.add(1);
    });

    socket.on('close', () => {
      wsConnectionsActive.add(-1);
      isConnected = false;
      console.log(`WebSocket closed. Messages received: ${messageCount}, Errors: ${errorCount}`);
    });

    // Simulate real-time interactions
    socket.setInterval(() => {
      if (!isConnected) return;

      // Send ping for latency measurement
      lastPingTime = Date.now();
      socket.send(JSON.stringify({
        type: 'ping',
        timestamp: lastPingTime,
      }));
      wsMessagesSent.add(1);
    }, 5000); // Ping every 5 seconds

    // Send various message types
    socket.setInterval(() => {
      if (!isConnected) return;

      const messageType = messageTypes[Math.floor(Math.random() * messageTypes.length)];
      const message = messageType.generator();
      
      try {
        socket.send(JSON.stringify(message));
        wsMessagesSent.add(1);
      } catch (e) {
        console.error('Failed to send message:', e);
        errorCount++;
        wsErrorRate.add(1);
      }
    }, 2000); // Send message every 2 seconds

    // Simulate driver location updates (more frequent)
    if (userType.type === 'driver') {
      socket.setInterval(() => {
        if (!isConnected) return;

        const locationUpdate = {
          type: 'location_update',
          data: {
            latitude: 25.0330 + (Math.random() - 0.5) * 0.01,
            longitude: 121.5654 + (Math.random() - 0.5) * 0.01,
            speed: 20 + Math.random() * 40,
            heading: Math.random() * 360,
            accuracy: 5 + Math.random() * 10,
            timestamp: new Date().toISOString(),
          },
        };

        try {
          socket.send(JSON.stringify(locationUpdate));
          wsMessagesSent.add(1);
        } catch (e) {
          console.error('Failed to send location update:', e);
          errorCount++;
          wsErrorRate.add(1);
        }
      }, 1000); // Every second for drivers
    }

    // Simulate broadcast reception
    socket.setTimeout(() => {
      if (!isConnected) return;

      // Request broadcast test
      socket.send(JSON.stringify({
        type: 'broadcast_test',
        data: {
          message: 'Test broadcast message',
          timestamp: new Date().toISOString(),
        },
      }));
    }, 10000); // After 10 seconds

    // Keep connection alive for test duration
    socket.setTimeout(() => {
      socket.close();
    }, 60000); // Close after 60 seconds
  });

  check(res, {
    'WebSocket connection established': (r) => r && r.status === 101,
  });
}

// Scenario for testing connection limits
export function connectionStress() {
  const connections = [];
  const maxConnections = 100;

  // Try to create many connections rapidly
  for (let i = 0; i < maxConnections; i++) {
    const url = `${WS_URL}/ws?token=stress_test_${i}`;
    
    const res = ws.connect(url, {}, function (socket) {
      connections.push(socket);
      
      socket.on('open', () => {
        wsConnectionsActive.add(1);
      });

      socket.on('close', () => {
        wsConnectionsActive.add(-1);
      });

      socket.on('error', (e) => {
        wsErrorRate.add(1);
      });

      // Keep alive for 30 seconds
      socket.setTimeout(() => {
        socket.close();
      }, 30000);
    });

    sleep(0.1); // Small delay between connections
  }

  sleep(35); // Wait for all connections to close
}

// Scenario for testing message throughput
export function messageThroughput() {
  const url = `${WS_URL}/ws?token=throughput_test`;
  let messagesSent = 0;
  let messagesReceived = 0;
  const testDuration = 30000; // 30 seconds
  const startTime = Date.now();

  ws.connect(url, {}, function (socket) {
    socket.on('open', () => {
      console.log('Throughput test started');

      // Send messages as fast as possible
      socket.setInterval(() => {
        const elapsed = Date.now() - startTime;
        if (elapsed >= testDuration) {
          socket.close();
          return;
        }

        const message = {
          type: 'throughput_test',
          sequence: messagesSent,
          timestamp: Date.now(),
          payload: 'x'.repeat(1024), // 1KB payload
        };

        socket.send(JSON.stringify(message));
        messagesSent++;
        wsMessagesSent.add(1);
      }, 1); // Send as fast as possible
    });

    socket.on('message', () => {
      messagesReceived++;
      wsMessagesReceived.add(1);
    });

    socket.on('close', () => {
      const duration = (Date.now() - startTime) / 1000;
      const sentRate = messagesSent / duration;
      const receivedRate = messagesReceived / duration;
      
      console.log(`Throughput test completed:`);
      console.log(`  Messages sent: ${messagesSent} (${sentRate.toFixed(2)} msg/s)`);
      console.log(`  Messages received: ${messagesReceived} (${receivedRate.toFixed(2)} msg/s)`);
    });
  });

  sleep(35); // Wait for test to complete
}

// Export test scenarios
export { connectionStress, messageThroughput };

// Export summary
export function handleSummary(data) {
  return {
    'stdout': JSON.stringify(data, null, 2),
    '/tmp/k6-websocket-summary.json': JSON.stringify(data, null, 2),
  };
}