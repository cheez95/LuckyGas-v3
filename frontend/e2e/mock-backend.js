// Mock backend server for E2E testing without Docker
const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');

const app = express();
const PORT = process.env.PORT || 3001;
const SECRET_KEY = 'test-secret-key-for-e2e-testing';

// Middleware
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:3000'],
  credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Mock data
const users = {
  admin: { id: 1, username: 'admin', password: 'admin123', role: 'admin', display_name: '系統管理員' },
  driver1: { id: 2, username: 'driver1', password: 'driver123', role: 'driver', display_name: '司機一號' },
  office1: { id: 3, username: 'office1', password: 'office123', role: 'office_staff', display_name: '辦公室人員' },
  manager1: { id: 4, username: 'manager1', password: 'manager123', role: 'manager', display_name: '經理' }
};

const customers = [
  { 
    id: 1, 
    customer_code: 'C001',
    short_name: '王大明',
    invoice_title: '王大明商行',
    address: '台北市大安區忠孝東路四段1號',
    area: 'A-瑞光',
    delivery_time_start: '09:00',
    delivery_time_end: '18:00',
    avg_daily_usage: 15,
    payment_method: '月結',
    customer_type: '商業',
    is_active: true
  },
  { 
    id: 2,
    customer_code: 'C002', 
    short_name: '李小華',
    invoice_title: '小華餐廳',
    address: '新北市板橋區文化路一段100號',
    area: 'B-四維',
    delivery_time_start: '10:00',
    delivery_time_end: '17:00',
    avg_daily_usage: 20,
    payment_method: '現金',
    customer_type: '餐飲',
    is_active: true
  },
  { 
    id: 3,
    customer_code: 'C003',
    short_name: '張美玲',
    invoice_title: '美玲食品行',
    address: '台中市西屯區台灣大道三段99號',
    area: 'C-漢中',
    delivery_time_start: '08:00',
    delivery_time_end: '16:00',
    avg_daily_usage: 25,
    payment_method: '轉帳',
    customer_type: '餐飲',
    is_active: true
  },
  { 
    id: 4,
    customer_code: 'C004',
    short_name: '陳建國',
    invoice_title: '建國工業',
    address: '高雄市前鎮區中山二路2號',
    area: 'D-東方大鎮',
    delivery_time_start: '09:00',
    delivery_time_end: '17:00', 
    avg_daily_usage: 30,
    payment_method: '月結',
    customer_type: '工業',
    is_active: true
  },
  { 
    id: 5,
    customer_code: 'C005',
    short_name: '林淑芬',
    invoice_title: '淑芬小吃店',
    address: '台南市東區大學路1號',
    area: 'E-其他',
    delivery_time_start: '11:00',
    delivery_time_end: '20:00',
    avg_daily_usage: 10,
    payment_method: '現金',
    customer_type: '餐飲',
    is_active: true
  }
];

const orders = [
  { id: 1, customer_id: 1, customer_name: '王大明', quantity: 1, delivery_date: new Date().toISOString(), status: 'pending', amount: 800 },
  { id: 2, customer_id: 2, customer_name: '李小華', quantity: 2, delivery_date: new Date(Date.now() + 86400000).toISOString(), status: 'pending', amount: 1600 },
  { id: 3, customer_id: 3, customer_name: '張美玲', quantity: 1, delivery_date: new Date(Date.now() + 172800000).toISOString(), status: 'scheduled', amount: 800 }
];

const routes = [
  {
    id: 1,
    name: '北區路線A',
    date: new Date().toISOString().split('T')[0],
    driver_id: 2,
    driver_name: '司機一號',
    stops: [
      { customer_id: 1, customer_name: '王大明', sequence: 1, estimated_time: '09:00' },
      { customer_id: 2, customer_name: '李小華', sequence: 2, estimated_time: '10:00' }
    ],
    total_distance: 15.5,
    estimated_duration: 120,
    status: 'assigned'
  }
];

// Helper functions
function generateToken(user) {
  return jwt.sign(
    { user_id: user.id, username: user.username, role: user.role },
    SECRET_KEY,
    { expiresIn: '30m' }
  );
}

function verifyToken(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({ detail: '未授權' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, SECRET_KEY);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ detail: '無效的令牌' });
  }
}

// Routes
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'mock-backend' });
});

// Authentication
app.post('/api/v1/auth/login', (req, res) => {
  const { username, password } = req.body;
  const user = users[username];
  
  if (!user || user.password !== password) {
    return res.status(401).json({ detail: '帳號或密碼錯誤' });
  }
  
  const access_token = generateToken(user);
  const refresh_token = generateToken(user); // In real app, this would be different
  
  res.json({
    access_token,
    refresh_token,
    token_type: 'bearer',
    user: {
      id: user.id,
      username: user.username,
      role: user.role,
      display_name: user.display_name
    }
  });
});

app.post('/api/v1/auth/refresh', verifyToken, (req, res) => {
  const user = users[req.user.username];
  const access_token = generateToken(user);
  
  res.json({
    access_token,
    token_type: 'bearer'
  });
});

app.get('/api/v1/auth/me', verifyToken, (req, res) => {
  const user = users[req.user.username];
  res.json({
    id: user.id,
    username: user.username,
    role: user.role,
    display_name: user.display_name,
    email: `${user.username}@luckygas.com.tw`,
    full_name: user.display_name,
    is_active: true,
    created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
  });
});

// Customers
app.get('/api/v1/customers', verifyToken, (req, res) => {
  const page = parseInt(req.query.skip) / parseInt(req.query.limit) + 1 || 1;
  const size = parseInt(req.query.limit) || 10;
  const search = req.query.search?.toLowerCase() || '';
  
  console.log('Customer search:', { search, totalCustomers: customers.length });
  
  let filtered = customers;
  if (search) {
    filtered = customers.filter(c => 
      (c.customer_code && c.customer_code.toLowerCase().includes(search)) ||
      (c.name && c.name.toLowerCase().includes(search)) ||
      (c.short_name && c.short_name.toLowerCase().includes(search)) ||
      (c.phone && c.phone.includes(search)) ||
      (c.address && c.address.toLowerCase().includes(search))
    );
  }
  
  const start = (page - 1) * size;
  const items = filtered.slice(start, start + size);
  
  res.json({
    items,
    total: filtered.length,
    page,
    size,
    pages: Math.ceil(filtered.length / size)
  });
});

app.get('/api/v1/customers/statistics', verifyToken, (req, res) => {
  const totalCustomers = customers.length;
  const activeCustomers = customers.filter(c => c.is_active !== false).length;
  const newCustomersThisMonth = customers.filter(c => {
    const createdDate = new Date(c.created_at || Date.now());
    const thisMonth = new Date();
    return createdDate.getMonth() === thisMonth.getMonth() && 
           createdDate.getFullYear() === thisMonth.getFullYear();
  }).length;
  
  res.json({
    totalCustomers,
    activeCustomers,
    newCustomersThisMonth,
    averageOrderFrequency: 15
  });
});

app.get('/api/v1/customers/:id', verifyToken, (req, res) => {
  const customer = customers.find(c => c.id === parseInt(req.params.id));
  if (!customer) {
    return res.status(404).json({ detail: '客戶不存在' });
  }
  res.json(customer);
});

app.post('/api/v1/customers', verifyToken, (req, res) => {
  const newCustomer = {
    id: customers.length + 1,
    ...req.body,
    created_at: new Date().toISOString()
  };
  customers.push(newCustomer);
  console.log('Created customer:', newCustomer);
  console.log('Total customers:', customers.length);
  res.status(201).json(newCustomer);
});

app.put('/api/v1/customers/:id', verifyToken, (req, res) => {
  const index = customers.findIndex(c => c.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '客戶不存在' });
  }
  customers[index] = { ...customers[index], ...req.body };
  res.json(customers[index]);
});

// Orders
app.get('/api/v1/orders', verifyToken, (req, res) => {
  // Add order_items to each order for Dashboard compatibility
  const ordersWithItems = orders.map(order => ({
    ...order,
    order_items: [{
      id: 1,
      product_name: '16KG 瓦斯鋼瓶',
      quantity: order.quantity,
      unit_price: 800,
      total_price: order.amount || (order.quantity * 800)
    }]
  }));
  
  // Return array directly for service compatibility
  res.json(ordersWithItems);
});

app.post('/api/v1/orders', verifyToken, (req, res) => {
  const newOrder = {
    id: orders.length + 1,
    ...req.body,
    status: 'pending',
    created_at: new Date().toISOString()
  };
  orders.push(newOrder);
  res.status(201).json(newOrder);
});

// Routes
app.get('/api/v1/routes', verifyToken, (req, res) => {
  // Add route fields expected by Dashboard
  const routesWithDetails = routes.map(route => ({
    ...route,
    route_number: route.name,
    route_date: route.date,
    total_orders: route.stops.length,
    completed_orders: 0,
    status: 'in_progress'
  }));
  
  if (req.user.role === 'driver') {
    // Filter routes for the specific driver
    const driverRoutes = routesWithDetails.filter(r => r.driver_id === req.user.user_id);
    res.json(driverRoutes);
  } else {
    res.json(routesWithDetails);
  }
});

app.get('/api/v1/routes/:id', verifyToken, (req, res) => {
  const route = routes.find(r => r.id === parseInt(req.params.id));
  if (!route) {
    return res.status(404).json({ detail: '路線不存在' });
  }
  res.json(route);
});

app.post('/api/v1/routes/optimize', verifyToken, (req, res) => {
  // Mock optimization - just return the same routes with a message
  res.json({
    optimized: true,
    message: '路線已優化（使用模擬服務）',
    routes: routes,
    total_distance_saved: 2.5,
    total_time_saved: 15
  });
});

// Predictions
app.post('/api/v1/predictions/generate', verifyToken, (req, res) => {
  const predictions = customers.map((customer, index) => ({
    customer_id: customer.id,
    customer_name: customer.name,
    predicted_demand: Math.floor(Math.random() * 3) + 1,
    confidence: 0.5 + Math.random() * 0.3,
    last_delivery_date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    recommendation: '建議配送'
  }));
  
  res.json({
    predictions,
    generated_at: new Date().toISOString(),
    using_placeholder: true
  });
});

app.get('/api/v1/predictions/summary', verifyToken, (req, res) => {
  // Return prediction summary for dashboard
  res.json({
    total: customers.length,
    urgent: Math.floor(customers.length * 0.3),
    average_confidence: 0.75,
    next_batch_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
  });
});

app.get('/api/v1/predictions', verifyToken, (req, res) => {
  // Return previously generated predictions as array
  const predictions = customers.map((customer, index) => ({
    id: index + 1,
    customer_id: customer.id,
    predicted_date: new Date(Date.now() + (index % 7) * 24 * 60 * 60 * 1000).toISOString(),
    quantities: {
      '50kg': 0,
      '20kg': 0,
      '16kg': Math.floor(Math.random() * 3) + 1,
      '10kg': 0,
      '4kg': 0
    },
    confidence_score: 0.5 + Math.random() * 0.3,
    model_version: 'v1.0',
    is_converted_to_order: false,
    created_at: new Date().toISOString()
  }));
  
  // Return array directly for service compatibility
  res.json(predictions);
});

// Driver endpoints
app.post('/api/v1/deliveries/:id/complete', verifyToken, (req, res) => {
  const { signature, photos, notes } = req.body;
  
  // Mock successful completion
  res.json({
    success: true,
    delivery_id: req.params.id,
    completed_at: new Date().toISOString(),
    signature_url: 'mock://signature.png',
    photo_urls: photos ? photos.map((_, i) => `mock://photo${i}.jpg`) : []
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Mock backend server running on http://localhost:${PORT}`);
  console.log('Available users:');
  Object.entries(users).forEach(([username, user]) => {
    console.log(`  - ${username} / ${user.password} (${user.role})`);
  });
});