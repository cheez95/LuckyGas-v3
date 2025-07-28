import { Router } from 'express';
import { mockData } from '../mock-data';
import { verifyToken } from './auth';

const router = Router();

// Apply auth middleware to all routes
router.use(verifyToken);

// Get orders
router.get('/', (req, res) => {
  const status = req.query.status as string;
  const customer_id = req.query.customer_id as string;
  const date_from = req.query.date_from as string;
  const date_to = req.query.date_to as string;
  
  let filtered = [...mockData.orders];
  
  // Apply filters
  if (status) {
    filtered = filtered.filter(o => o.status === status);
  }
  
  if (customer_id) {
    filtered = filtered.filter(o => o.customer_id === parseInt(customer_id));
  }
  
  if (date_from) {
    filtered = filtered.filter(o => new Date(o.delivery_date) >= new Date(date_from));
  }
  
  if (date_to) {
    filtered = filtered.filter(o => new Date(o.delivery_date) <= new Date(date_to));
  }
  
  // Sort by delivery date descending
  filtered.sort((a, b) => 
    new Date(b.delivery_date).getTime() - new Date(a.delivery_date).getTime()
  );
  
  // Return array directly for compatibility
  res.json(filtered);
});

// Get order statistics
router.get('/statistics', (req, res) => {
  const today = new Date().toISOString().split('T')[0];
  const todayOrders = mockData.orders.filter(o => 
    o.delivery_date.split('T')[0] === today
  );
  
  res.json({
    total_orders: mockData.orders.length,
    pending_orders: mockData.orders.filter(o => o.status === 'pending').length,
    in_progress_orders: mockData.orders.filter(o => o.status === 'in_progress').length,
    completed_orders: mockData.orders.filter(o => o.status === 'completed').length,
    today_orders: todayOrders.length,
    today_revenue: todayOrders.reduce((sum, o) => sum + o.total_amount, 0),
    average_order_value: mockData.orders.reduce((sum, o) => sum + o.total_amount, 0) / mockData.orders.length
  });
});

// Get single order
router.get('/:id', (req, res) => {
  const order = mockData.orders.find(o => o.id === parseInt(req.params.id));
  if (!order) {
    return res.status(404).json({ detail: '訂單不存在' });
  }
  res.json(order);
});

// Create order
router.post('/', (req, res) => {
  const customer = mockData.customers.find(c => c.id === req.body.customer_id);
  if (!customer) {
    return res.status(400).json({ detail: '客戶不存在' });
  }
  
  const newOrder = {
    id: Math.max(...mockData.orders.map(o => o.id)) + 1,
    ...req.body,
    customer_name: customer.name,
    customer_code: customer.customer_code,
    status: 'pending',
    payment_status: 'unpaid',
    created_by: req.user.user_id,
    created_at: new Date().toISOString()
  };
  
  // Add default order items if not provided
  if (!newOrder.order_items) {
    newOrder.order_items = [{
      id: Date.now(),
      order_id: newOrder.id,
      product_id: 1,
      product_name: '16公斤鋼瓶',
      quantity: 1,
      unit_price: 800,
      total_price: 800
    }];
    newOrder.total_amount = 800;
  }
  
  mockData.orders.push(newOrder);
  res.status(201).json(newOrder);
});

// Update order
router.put('/:id', (req, res) => {
  const index = mockData.orders.findIndex(o => o.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '訂單不存在' });
  }
  
  mockData.orders[index] = { 
    ...mockData.orders[index], 
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  res.json(mockData.orders[index]);
});

// Cancel order
router.post('/:id/cancel', (req, res) => {
  const order = mockData.orders.find(o => o.id === parseInt(req.params.id));
  if (!order) {
    return res.status(404).json({ detail: '訂單不存在' });
  }
  
  if (order.status === 'completed') {
    return res.status(400).json({ detail: '已完成的訂單無法取消' });
  }
  
  order.status = 'cancelled';
  order.cancelled_at = new Date().toISOString();
  order.cancelled_by = req.user.user_id;
  
  res.json(order);
});

// Bulk create orders
router.post('/bulk', (req, res) => {
  const { orders } = req.body;
  
  if (!Array.isArray(orders) || orders.length === 0) {
    return res.status(400).json({ detail: '請提供訂單列表' });
  }
  
  const createdOrders = orders.map(orderData => {
    const customer = mockData.customers.find(c => c.id === orderData.customer_id);
    if (!customer) {
      return null;
    }
    
    const newOrder = {
      id: Math.max(...mockData.orders.map(o => o.id)) + 1,
      ...orderData,
      customer_name: customer.name,
      customer_code: customer.customer_code,
      status: 'pending',
      payment_status: 'unpaid',
      created_by: req.user.user_id,
      created_at: new Date().toISOString()
    };
    
    mockData.orders.push(newOrder);
    return newOrder;
  }).filter(o => o !== null);
  
  res.status(201).json({
    created: createdOrders.length,
    orders: createdOrders
  });
});

// Convert predictions to orders
router.post('/from-predictions', (req, res) => {
  const { prediction_ids } = req.body;
  
  if (!Array.isArray(prediction_ids) || prediction_ids.length === 0) {
    return res.status(400).json({ detail: '請提供預測ID列表' });
  }
  
  // Mock conversion - create orders for each prediction
  const createdOrders = prediction_ids.map(id => {
    // Find a random customer for demo
    const customer = mockData.customers[id % mockData.customers.length];
    
    const newOrder = {
      id: Math.max(...mockData.orders.map(o => o.id)) + 1,
      customer_id: customer.id,
      customer_name: customer.name,
      customer_code: customer.customer_code,
      order_date: new Date().toISOString(),
      delivery_date: new Date(Date.now() + 86400000).toISOString(),
      status: 'pending',
      payment_status: 'unpaid',
      payment_method: customer.payment_method,
      total_amount: 800,
      order_items: [{
        id: Date.now(),
        product_id: 1,
        product_name: '16公斤鋼瓶',
        quantity: 1,
        unit_price: 800,
        total_price: 800
      }],
      created_by: req.user.user_id,
      created_at: new Date().toISOString(),
      prediction_id: id
    };
    
    mockData.orders.push(newOrder);
    return newOrder;
  });
  
  res.status(201).json({
    created: createdOrders.length,
    orders: createdOrders
  });
});

export { router as orderRoutes };