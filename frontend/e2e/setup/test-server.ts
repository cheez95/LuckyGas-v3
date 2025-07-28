import express from 'express';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { mockData } from './mock-data';
import { authRoutes } from './routes/auth';
import { customerRoutes } from './routes/customers';
import { orderRoutes } from './routes/orders';
import { routeRoutes } from './routes/routes';
import { predictionRoutes } from './routes/predictions';
import { notificationRoutes } from './routes/notifications';
import { WebSocketManager } from './websocket-manager';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: {
    origin: ['http://localhost:5173', 'http://localhost:3000'],
    credentials: true
  }
});

const PORT = process.env.MOCK_PORT || 3001;
const SECRET_KEY = 'test-secret-key-for-e2e-testing';

// WebSocket manager
const wsManager = new WebSocketManager(io);

// Middleware
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:3000'],
  credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Add request logging for debugging
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    service: 'e2e-test-server',
    timestamp: new Date().toISOString(),
    websocket: io.engine.clientsCount
  });
});

// API version info
app.get('/api/v1', (req, res) => {
  res.json({
    version: '1.0.0',
    environment: 'test',
    features: {
      auth: true,
      websocket: true,
      predictions: true,
      notifications: true
    }
  });
});

// Mount routes
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1/customers', customerRoutes);
app.use('/api/v1/orders', orderRoutes);
app.use('/api/v1/routes', routeRoutes);
app.use('/api/v1/predictions', predictionRoutes);
app.use('/api/v1/notifications', notificationRoutes);

// WebSocket connection handling
io.on('connection', (socket) => {
  console.log(`WebSocket client connected: ${socket.id}`);
  
  socket.on('authenticate', (token) => {
    try {
      const decoded = jwt.verify(token, SECRET_KEY);
      socket.data.user = decoded;
      socket.join(`user:${decoded.user_id}`);
      socket.join(`role:${decoded.role}`);
      
      socket.emit('authenticated', { 
        success: true, 
        user: decoded 
      });
      
      // Send initial notifications
      wsManager.sendUserNotifications(socket, decoded.user_id);
    } catch (error) {
      socket.emit('authenticated', { 
        success: false, 
        error: 'Invalid token' 
      });
    }
  });
  
  socket.on('join-route', (routeId) => {
    if (socket.data.user) {
      socket.join(`route:${routeId}`);
      console.log(`User ${socket.data.user.username} joined route ${routeId}`);
    }
  });
  
  socket.on('leave-route', (routeId) => {
    socket.leave(`route:${routeId}`);
  });
  
  socket.on('location-update', (data) => {
    if (socket.data.user && socket.data.user.role === 'driver') {
      wsManager.broadcastLocationUpdate(socket.data.user.user_id, data);
    }
  });
  
  socket.on('disconnect', () => {
    console.log(`WebSocket client disconnected: ${socket.id}`);
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ 
    detail: 'Not found',
    path: req.path 
  });
});

// Error handler
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Server error:', err);
  res.status(err.status || 500).json({
    detail: err.message || 'Internal server error',
    error: process.env.NODE_ENV === 'development' ? err : {}
  });
});

// Start server
httpServer.listen(PORT, () => {
  console.log(`E2E test server running on http://localhost:${PORT}`);
  console.log('WebSocket server ready');
  console.log('\nAvailable test users:');
  console.log('  - admin / admin123 (admin)');
  console.log('  - driver1 / driver123 (driver)');
  console.log('  - office1 / office123 (office_staff)');
  console.log('  - manager1 / manager123 (manager)');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  httpServer.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export { app, httpServer, io, wsManager };