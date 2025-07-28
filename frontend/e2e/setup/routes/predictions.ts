import { Router } from 'express';
import { mockData } from '../mock-data';
import { verifyToken } from './auth';

const router = Router();

// Apply auth middleware to all routes
router.use(verifyToken);

// Get predictions
router.get('/', (req, res) => {
  // Generate predictions if none exist
  if (mockData.predictions.length === 0) {
    mockData.predictions = mockData.customers.map((customer, index) => ({
      id: index + 1,
      customer_id: customer.id,
      customer_name: customer.name,
      customer_code: customer.customer_code,
      predicted_date: new Date(Date.now() + ((index % 7) + 1) * 86400000).toISOString(),
      quantities: {
        '50kg': 0,
        '20kg': Math.random() < 0.2 ? 1 : 0,
        '16kg': Math.floor(Math.random() * 3) + 1,
        '10kg': Math.random() < 0.3 ? 1 : 0,
        '4kg': 0
      },
      confidence_score: 0.5 + Math.random() * 0.4,
      model_version: 'v1.0',
      is_converted_to_order: false,
      created_at: new Date().toISOString()
    }));
  }
  
  // Filter predictions
  let filtered = [...mockData.predictions];
  
  const date_from = req.query.date_from as string;
  const date_to = req.query.date_to as string;
  const customer_id = req.query.customer_id as string;
  const is_converted = req.query.is_converted as string;
  
  if (date_from) {
    filtered = filtered.filter(p => new Date(p.predicted_date) >= new Date(date_from));
  }
  
  if (date_to) {
    filtered = filtered.filter(p => new Date(p.predicted_date) <= new Date(date_to));
  }
  
  if (customer_id) {
    filtered = filtered.filter(p => p.customer_id === parseInt(customer_id));
  }
  
  if (is_converted !== undefined) {
    filtered = filtered.filter(p => p.is_converted_to_order === (is_converted === 'true'));
  }
  
  res.json(filtered);
});

// Generate predictions
router.post('/generate', (req, res) => {
  const { date, area, confidence_threshold } = req.body;
  
  // Simulate prediction generation
  setTimeout(() => {
    const predictions = mockData.customers
      .filter(c => !area || c.area === area)
      .map((customer, index) => ({
        id: mockData.predictions.length + index + 1,
        customer_id: customer.id,
        customer_name: customer.name,
        customer_code: customer.customer_code,
        predicted_date: date || new Date(Date.now() + 86400000).toISOString(),
        quantities: {
          '50kg': Math.random() < 0.1 ? 1 : 0,
          '20kg': Math.random() < 0.2 ? 1 : 0,
          '16kg': Math.floor(Math.random() * 3) + 1,
          '10kg': Math.random() < 0.3 ? 1 : 0,
          '4kg': Math.random() < 0.1 ? 1 : 0
        },
        confidence_score: 0.5 + Math.random() * 0.4,
        model_version: 'v1.0',
        is_converted_to_order: false,
        created_at: new Date().toISOString()
      }))
      .filter(p => !confidence_threshold || p.confidence_score >= confidence_threshold);
    
    // Add to mock data
    mockData.predictions.push(...predictions);
    
    res.json({
      predictions,
      generated_at: new Date().toISOString(),
      model_version: 'v1.0',
      parameters: {
        date,
        area,
        confidence_threshold
      },
      statistics: {
        total_predictions: predictions.length,
        average_confidence: predictions.reduce((sum, p) => sum + p.confidence_score, 0) / predictions.length,
        high_confidence_count: predictions.filter(p => p.confidence_score >= 0.8).length
      }
    });
  }, 2000); // Simulate processing time
});

// Get prediction summary
router.get('/summary', (req, res) => {
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  
  const tomorrowPredictions = mockData.predictions.filter(p => {
    const predDate = new Date(p.predicted_date);
    return predDate.toDateString() === tomorrow.toDateString();
  });
  
  res.json({
    total: mockData.predictions.length,
    tomorrow: tomorrowPredictions.length,
    urgent: mockData.predictions.filter(p => p.confidence_score >= 0.8).length,
    average_confidence: mockData.predictions.length > 0 
      ? mockData.predictions.reduce((sum, p) => sum + p.confidence_score, 0) / mockData.predictions.length 
      : 0,
    next_batch_date: new Date(Date.now() + 86400000).toISOString(),
    model_version: 'v1.0',
    last_generated: mockData.predictions.length > 0 
      ? Math.max(...mockData.predictions.map(p => new Date(p.created_at).getTime()))
      : null
  });
});

// Get prediction accuracy metrics
router.get('/accuracy', (req, res) => {
  // Mock accuracy metrics
  res.json({
    overall_accuracy: 0.82,
    precision: 0.85,
    recall: 0.79,
    f1_score: 0.82,
    mean_absolute_error: 0.15,
    metrics_by_product: {
      '50kg': { accuracy: 0.90, count: 45 },
      '20kg': { accuracy: 0.85, count: 120 },
      '16kg': { accuracy: 0.80, count: 350 },
      '10kg': { accuracy: 0.78, count: 180 },
      '4kg': { accuracy: 0.75, count: 80 }
    },
    last_updated: new Date().toISOString()
  });
});

// Convert predictions to orders
router.post('/convert-to-orders', (req, res) => {
  const { prediction_ids } = req.body;
  
  if (!Array.isArray(prediction_ids) || prediction_ids.length === 0) {
    return res.status(400).json({ detail: '請提供預測ID列表' });
  }
  
  const convertedOrders = [];
  
  prediction_ids.forEach(id => {
    const prediction = mockData.predictions.find(p => p.id === id);
    if (!prediction || prediction.is_converted_to_order) {
      return;
    }
    
    const customer = mockData.customers.find(c => c.id === prediction.customer_id);
    if (!customer) {
      return;
    }
    
    // Calculate total from prediction quantities
    let totalAmount = 0;
    const orderItems = [];
    
    Object.entries(prediction.quantities).forEach(([size, quantity]) => {
      if (quantity > 0) {
        const product = mockData.products.find(p => p.size === size);
        if (product) {
          orderItems.push({
            id: Date.now() + Math.random(),
            product_id: product.id,
            product_name: product.name,
            quantity,
            unit_price: product.unit_price,
            total_price: product.unit_price * quantity
          });
          totalAmount += product.unit_price * quantity;
        }
      }
    });
    
    if (orderItems.length > 0) {
      const newOrder = {
        id: Math.max(...mockData.orders.map(o => o.id)) + 1,
        customer_id: customer.id,
        customer_name: customer.name,
        customer_code: customer.customer_code,
        order_date: new Date().toISOString(),
        delivery_date: prediction.predicted_date,
        status: 'pending',
        payment_status: 'unpaid',
        payment_method: customer.payment_method,
        total_amount: totalAmount,
        order_items: orderItems,
        created_by: req.user.user_id,
        created_at: new Date().toISOString(),
        prediction_id: prediction.id
      };
      
      mockData.orders.push(newOrder);
      convertedOrders.push(newOrder);
      
      // Mark prediction as converted
      prediction.is_converted_to_order = true;
    }
  });
  
  res.json({
    converted: convertedOrders.length,
    orders: convertedOrders,
    message: `成功將 ${convertedOrders.length} 個預測轉換為訂單`
  });
});

// Update prediction
router.put('/:id', (req, res) => {
  const index = mockData.predictions.findIndex(p => p.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '預測不存在' });
  }
  
  mockData.predictions[index] = { 
    ...mockData.predictions[index], 
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  res.json(mockData.predictions[index]);
});

// Delete prediction
router.delete('/:id', (req, res) => {
  const index = mockData.predictions.findIndex(p => p.id === parseInt(req.params.id));
  if (index === -1) {
    return res.status(404).json({ detail: '預測不存在' });
  }
  
  if (mockData.predictions[index].is_converted_to_order) {
    return res.status(400).json({ detail: '已轉換為訂單的預測無法刪除' });
  }
  
  mockData.predictions.splice(index, 1);
  res.status(204).send();
});

export { router as predictionRoutes };