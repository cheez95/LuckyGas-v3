import { Router } from 'express';
import { mockData } from '../mock-data';
import { verifyToken } from './auth';

const router = Router();

// Apply auth middleware to all routes
router.use(verifyToken);

// Get customers with pagination and search
router.get('/', (req, res) => {
  const page = parseInt(req.query.page as string) || 1;
  const size = parseInt(req.query.limit as string) || 10;
  const skip = parseInt(req.query.skip as string) || 0;
  const search = (req.query.search as string)?.toLowerCase() || '';
  const area = req.query.area as string;
  const is_active = req.query.is_active as string;
  
  let filtered = [...mockData.customers];
  
  // Apply search filter
  if (search) {
    filtered = filtered.filter(c => 
      c.customer_code.toLowerCase().includes(search) ||
      c.name.toLowerCase().includes(search) ||
      c.short_name.toLowerCase().includes(search) ||
      c.phone?.includes(search) ||
      c.mobile?.includes(search) ||
      c.address.toLowerCase().includes(search)
    );
  }
  
  // Apply area filter
  if (area) {
    filtered = filtered.filter(c => c.area === area);
  }
  
  // Apply active filter
  if (is_active !== undefined) {
    filtered = filtered.filter(c => c.is_active === (is_active === 'true'));
  }
  
  // Calculate pagination
  const actualPage = skip > 0 ? Math.floor(skip / size) + 1 : page;
  const start = (actualPage - 1) * size;
  const items = filtered.slice(start, start + size);
  
  res.json({
    items,
    total: filtered.length,
    page: actualPage,
    size,
    pages: Math.ceil(filtered.length / size)
  });
});

// Get customer statistics
router.get('/statistics', (req, res) => {
  const totalCustomers = mockData.customers.length;
  const activeCustomers = mockData.customers.filter(c => c.is_active).length;
  const newCustomersThisMonth = mockData.customers.filter(c => {
    const createdDate = new Date(c.created_at);
    const thisMonth = new Date();
    return createdDate.getMonth() === thisMonth.getMonth() && 
           createdDate.getFullYear() === thisMonth.getFullYear();
  }).length;
  
  res.json({
    totalCustomers,
    activeCustomers,
    inactiveCustomers: totalCustomers - activeCustomers,
    newCustomersThisMonth,
    averageOrderFrequency: 15,
    customersByType: {
      commercial: mockData.customers.filter(c => c.customer_type === '商業').length,
      restaurant: mockData.customers.filter(c => c.customer_type === '餐飲').length,
      industrial: mockData.customers.filter(c => c.customer_type === '工業').length,
      residential: mockData.customers.filter(c => c.customer_type === '住宅').length
    }
  });
});

// Export customers
router.get('/export', (req, res) => {
  const format = req.query.format || 'csv';
  
  // Simulate file generation
  res.setHeader('Content-Type', format === 'excel' ? 'application/vnd.ms-excel' : 'text/csv');
  res.setHeader('Content-Disposition', `attachment; filename=customers_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'csv'}`);
  
  if (format === 'csv') {
    const csv = [
      'Customer Code,Name,Short Name,Phone,Mobile,Address,Area,Type,Active',
      ...mockData.customers.map(c => 
        `${c.customer_code},${c.name},${c.short_name},${c.phone},${c.mobile},"${c.address}",${c.area},${c.customer_type},${c.is_active}`
      )
    ].join('\n');
    
    res.send(csv);
  } else {
    // For Excel, we'd normally use a library, but for testing just send CSV
    res.send('Excel export simulated');
  }
});

// Get single customer
router.get('/:id', (req, res) => {
  const customer = mockData.customers.find(c => c.id === parseInt(req.params.id));
  if (!customer) {
    return res.status(404).json({ detail: '客戶不存在' });
  }
  res.json(customer);
});

// Get customer orders
router.get('/:id/orders', (req, res) => {
  const customerId = parseInt(req.params.id);
  const orders = mockData.orders.filter(o => o.customer_id === customerId);
  
  res.json({
    items: orders,
    total: orders.length
  });
});

// Get customer predictions
router.get('/:id/predictions', (req, res) => {
  const customerId = parseInt(req.params.id);
  const customer = mockData.customers.find(c => c.id === customerId);
  
  if (!customer) {
    return res.status(404).json({ detail: '客戶不存在' });
  }
  
  // Generate mock predictions
  const predictions = Array.from({ length: 7 }, (_, i) => ({
    id: i + 1,
    customer_id: customerId,
    predicted_date: new Date(Date.now() + (i + 1) * 86400000).toISOString(),
    quantities: {
      '50kg': 0,
      '20kg': 0,
      '16kg': Math.floor(Math.random() * 3) + 1,
      '10kg': 0,
      '4kg': 0
    },
    confidence_score: 0.7 + Math.random() * 0.2,
    model_version: 'v1.0',
    created_at: new Date().toISOString()
  }));
  
  res.json({
    items: predictions,
    total: predictions.length
  });
});

// Create customer
router.post('/', (req, res) => {
  // Check for duplicate customer code
  if (mockData.customers.some(c => c.customer_code === req.body.customer_code)) {
    return res.status(400).json({ detail: '客戶代碼已存在' });
  }
  
  const newCustomer = {
    id: Math.max(...mockData.customers.map(c => c.id)) + 1,
    ...req.body,
    is_active: req.body.is_active !== false,
    created_at: new Date().toISOString()
  };
  
  mockData.customers.push(newCustomer);
  res.status(201).json(newCustomer);
});

// Update customer
router.put('/:id', (req, res) => {
  const index = mockData.customers.findIndex(c => c.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '客戶不存在' });
  }
  
  // Check for duplicate customer code (excluding current customer)
  if (req.body.customer_code && 
      mockData.customers.some(c => 
        c.customer_code === req.body.customer_code && 
        c.id !== parseInt(req.params.id)
      )) {
    return res.status(400).json({ detail: '客戶代碼已存在' });
  }
  
  mockData.customers[index] = { 
    ...mockData.customers[index], 
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  res.json(mockData.customers[index]);
});

// Delete customer
router.delete('/:id', (req, res) => {
  const index = mockData.customers.findIndex(c => c.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '客戶不存在' });
  }
  
  // Check if customer has active orders
  const hasActiveOrders = mockData.orders.some(o => 
    o.customer_id === parseInt(req.params.id) && 
    ['pending', 'in_progress'].includes(o.status)
  );
  
  if (hasActiveOrders) {
    return res.status(400).json({ detail: '無法刪除有進行中訂單的客戶' });
  }
  
  mockData.customers.splice(index, 1);
  res.status(204).send();
});

// Bulk delete customers
router.post('/bulk-delete', (req, res) => {
  const { ids } = req.body;
  
  if (!Array.isArray(ids) || ids.length === 0) {
    return res.status(400).json({ detail: '請提供要刪除的客戶ID列表' });
  }
  
  // Check for active orders
  const hasActiveOrders = ids.some(id => 
    mockData.orders.some(o => 
      o.customer_id === id && 
      ['pending', 'in_progress'].includes(o.status)
    )
  );
  
  if (hasActiveOrders) {
    return res.status(400).json({ detail: '選擇的客戶中有進行中的訂單' });
  }
  
  // Remove customers
  const deletedCount = ids.reduce((count, id) => {
    const index = mockData.customers.findIndex(c => c.id === id);
    if (index !== -1) {
      mockData.customers.splice(index, 1);
      return count + 1;
    }
    return count;
  }, 0);
  
  res.json({ 
    message: '批量刪除成功',
    deleted_count: deletedCount 
  });
});

export { router as customerRoutes };