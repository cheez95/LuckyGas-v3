import { Router } from 'express';
import { mockData } from '../mock-data';
import { verifyToken } from './auth';

const router = Router();

// Apply auth middleware to all routes
router.use(verifyToken);

// Get routes
router.get('/', (req, res) => {
  const date = req.query.date as string;
  const driver_id = req.query.driver_id as string;
  const status = req.query.status as string;
  
  let filtered = [...mockData.routes];
  
  // Apply filters
  if (date) {
    filtered = filtered.filter(r => r.date === date);
  }
  
  if (driver_id) {
    filtered = filtered.filter(r => r.driver_id === parseInt(driver_id));
  }
  
  if (status) {
    filtered = filtered.filter(r => r.status === status);
  }
  
  // Filter by role
  if (req.user.role === 'driver') {
    filtered = filtered.filter(r => r.driver_id === req.user.user_id);
  }
  
  res.json(filtered);
});

// Get route statistics
router.get('/statistics', (req, res) => {
  const today = new Date().toISOString().split('T')[0];
  const todayRoutes = mockData.routes.filter(r => r.date === today);
  
  res.json({
    total_routes: mockData.routes.length,
    today_routes: todayRoutes.length,
    active_routes: mockData.routes.filter(r => r.status === 'in_progress').length,
    completed_routes: mockData.routes.filter(r => r.status === 'completed').length,
    average_stops_per_route: mockData.routes.reduce((sum, r) => sum + r.stops.length, 0) / mockData.routes.length,
    total_distance_today: todayRoutes.reduce((sum, r) => sum + r.total_distance, 0),
    drivers_on_road: mockData.routes.filter(r => r.status === 'in_progress').length
  });
});

// Get single route
router.get('/:id', (req, res) => {
  const route = mockData.routes.find(r => r.id === parseInt(req.params.id));
  if (!route) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  
  // Check permissions
  if (req.user.role === 'driver' && route.driver_id !== req.user.user_id) {
    return res.status(403).json({ detail: '無權查看此路線' });
  }
  
  res.json(route);
});

// Optimize routes
router.post('/optimize', (req, res) => {
  const { date, area, constraints } = req.body;
  
  // Mock optimization
  setTimeout(() => {
    res.json({
      optimized: true,
      message: '路線已優化（使用模擬服務）',
      routes: mockData.routes.filter(r => !date || r.date === date),
      optimization_metrics: {
        total_distance_saved: 5.2,
        total_time_saved: 25,
        fuel_cost_saved: 150,
        routes_optimized: 3
      }
    });
  }, 1000); // Simulate processing time
});

// Create route
router.post('/', (req, res) => {
  const driver = mockData.users.find(u => u.id === req.body.driver_id);
  if (!driver || driver.role !== 'driver') {
    return res.status(400).json({ detail: '無效的司機ID' });
  }
  
  const newRoute = {
    id: Math.max(...mockData.routes.map(r => r.id)) + 1,
    ...req.body,
    route_number: `R${String(mockData.routes.length + 1).padStart(3, '0')}`,
    driver_name: driver.display_name,
    status: 'assigned',
    total_orders: req.body.stops?.length || 0,
    completed_orders: 0,
    created_at: new Date().toISOString(),
    created_by: req.user.user_id
  };
  
  mockData.routes.push(newRoute);
  res.status(201).json(newRoute);
});

// Update route
router.put('/:id', (req, res) => {
  const index = mockData.routes.findIndex(r => r.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  
  mockData.routes[index] = { 
    ...mockData.routes[index], 
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  res.json(mockData.routes[index]);
});

// Start route
router.post('/:id/start', (req, res) => {
  const route = mockData.routes.find(r => r.id === parseInt(req.params.id));
  if (!route) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  
  if (route.status !== 'assigned') {
    return res.status(400).json({ detail: '只能開始已分配的路線' });
  }
  
  route.status = 'in_progress';
  route.actual_start_time = new Date().toISOString();
  
  res.json(route);
});

// Complete stop
router.post('/:routeId/stops/:stopId/complete', (req, res) => {
  const route = mockData.routes.find(r => r.id === parseInt(req.params.routeId));
  if (!route) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  
  const stop = route.stops.find(s => s.id === parseInt(req.params.stopId));
  if (!stop) {
    return res.status(404).json({ detail: '站點不存在' });
  }
  
  stop.status = 'completed';
  stop.actual_arrival = new Date().toISOString();
  
  // Update route progress
  const completedStops = route.stops.filter(s => s.status === 'completed').length;
  route.completed_orders = completedStops;
  
  // If all stops completed, complete the route
  if (completedStops === route.stops.length) {
    route.status = 'completed';
    route.actual_end_time = new Date().toISOString();
  }
  
  res.json({
    route,
    stop,
    message: '配送完成'
  });
});

// Get route tracking
router.get('/:id/tracking', (req, res) => {
  const route = mockData.routes.find(r => r.id === parseInt(req.params.id));
  if (!route) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  
  // Mock tracking data
  const tracking = {
    route_id: route.id,
    driver: {
      id: route.driver_id,
      name: route.driver_name,
      phone: '0912-345-678'
    },
    vehicle: {
      id: route.vehicle_id,
      number: route.vehicle_number
    },
    current_location: {
      latitude: 25.0330 + (Math.random() - 0.5) * 0.1,
      longitude: 121.5654 + (Math.random() - 0.5) * 0.1,
      speed: Math.floor(Math.random() * 60),
      heading: Math.floor(Math.random() * 360),
      accuracy: 10,
      timestamp: new Date().toISOString()
    },
    stops: route.stops.map(s => ({
      ...s,
      estimated_distance: Math.floor(Math.random() * 10) + 1,
      estimated_time: Math.floor(Math.random() * 30) + 5
    })),
    progress: {
      total_stops: route.stops.length,
      completed_stops: route.completed_orders,
      percentage: Math.round((route.completed_orders / route.stops.length) * 100)
    }
  };
  
  res.json(tracking);
});

// Assign driver to route
router.post('/:id/assign', (req, res) => {
  const route = mockData.routes.find(r => r.id === parseInt(req.params.id));
  if (!route) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  
  const driver = mockData.users.find(u => u.id === req.body.driver_id);
  if (!driver || driver.role !== 'driver') {
    return res.status(400).json({ detail: '無效的司機ID' });
  }
  
  route.driver_id = driver.id;
  route.driver_name = driver.display_name;
  route.status = 'assigned';
  
  res.json(route);
});

export { router as routeRoutes };