/**
 * Mock data generators for frontend tests
 */
import { Customer, Order, User, Route, GasProduct, OrderTemplate } from '../../types';

// Counter for unique IDs
let idCounter = 1;
const getNextId = () => idCounter++;

// Date helpers
const getFutureDate = (days: number = 7): string => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString();
};

const getPastDate = (days: number = 7): string => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString();
};

// User mock data
export const createMockUser = (overrides: Partial<User> = {}): User => ({
  id: getNextId(),
  username: 'testuser',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'office_staff',
  is_active: true,
  is_verified: true,
  phone: '0912-345-678',
  created_at: getPastDate(30),
  updated_at: getPastDate(1),
  ...overrides
});

// Customer mock data
export const createMockCustomer = (overrides: Partial<Customer> = {}): Customer => ({
  id: getNextId(),
  customer_code: `C${String(getNextId()).padStart(6, '0')}`,
  short_name: '測試客戶',
  invoice_title: '測試客戶有限公司',
  tax_id: '12345678',
  address: '台北市信義區信義路五段123號',
  phone1: '0912-345-678',
  phone2: '02-2758-4321',
  contact_person: '王小明',
  delivery_address: '台北市信義區信義路五段123號1樓',
  area: '信義區',
  is_corporate: false,
  customer_type: 'regular',
  is_active: true,
  is_terminated: false,
  is_subscription: false,
  credit_limit: 0,
  current_credit: 0,
  payment_terms: 0,
  bank_name: '',
  bank_account: '',
  notes: '',
  created_at: getPastDate(90),
  updated_at: getPastDate(1),
  ...overrides
});

// Order mock data
export const createMockOrder = (overrides: Partial<Order> = {}): Order => ({
  id: getNextId(),
  order_number: `ORD-${new Date().getFullYear()}${String(getNextId()).padStart(6, '0')}`,
  customer_id: 1,
  customer: createMockCustomer(),
  scheduled_date: getFutureDate(2),
  status: 'pending',
  payment_status: 'unpaid',
  qty_50kg: 2,
  qty_20kg: 1,
  qty_16kg: 0,
  qty_10kg: 0,
  qty_4kg: 0,
  total_amount: 6000,
  discount_amount: 0,
  final_amount: 6000,
  delivery_address: '台北市信義區信義路五段123號',
  delivery_notes: '',
  is_urgent: false,
  payment_method: 'cash',
  created_by: 1,
  updated_by: 1,
  created_at: getPastDate(1),
  updated_at: getPastDate(1),
  ...overrides
});

// Gas Product mock data
export const createMockGasProduct = (overrides: Partial<GasProduct> = {}): GasProduct => ({
  id: getNextId(),
  product_name: '50kg 瓦斯桶',
  size: '50kg',
  unit_price: 2500,
  is_available: true,
  display_name: '50公斤桶裝瓦斯',
  category: 'standard',
  created_at: getPastDate(365),
  updated_at: getPastDate(30),
  ...overrides
});

// Route mock data
export const createMockRoute = (overrides: Partial<Route> = {}): Route => ({
  id: getNextId(),
  route_number: `R${String(getNextId()).padStart(3, '0')}`,
  route_date: getFutureDate(1),
  area: '信義區',
  driver_id: 1,
  driver: createMockUser({ role: 'driver', full_name: 'Driver User' }),
  vehicle_id: 1,
  stops: [],
  total_stops: 0,
  completed_stops: 0,
  total_distance_km: 0,
  estimated_duration_minutes: 0,
  actual_start_time: null,
  actual_end_time: null,
  status: 'planned',
  optimization_score: 0,
  created_by: 1,
  updated_by: 1,
  created_at: getPastDate(1),
  updated_at: getPastDate(1),
  ...overrides
});

// Order Template mock data
export const createMockOrderTemplate = (overrides: Partial<OrderTemplate> = {}): OrderTemplate => ({
  id: getNextId(),
  template_name: '測試模板',
  template_code: `TPL-${String(getNextId()).padStart(4, '0')}`,
  description: '測試用訂單模板',
  customer_id: 1,
  customer: createMockCustomer(),
  products: [
    {
      gas_product_id: 1,
      quantity: 2,
      unit_price: 2500,
      discount_percentage: 0,
      is_exchange: true,
      empty_received: 2
    }
  ],
  delivery_notes: '',
  priority: 'normal',
  payment_method: 'cash',
  is_recurring: false,
  recurrence_pattern: null,
  next_order_date: null,
  times_used: 0,
  last_used_at: null,
  is_active: true,
  created_by: 1,
  updated_by: 1,
  created_at: getPastDate(30),
  updated_at: getPastDate(1),
  ...overrides
});

// Bulk data generators
export const createMockCustomers = (count: number = 5): Customer[] => {
  return Array.from({ length: count }, (_, index) => 
    createMockCustomer({
      short_name: `測試客戶${index + 1}`,
      customer_code: `C${String(index + 1).padStart(6, '0')}`,
      area: ['信義區', '大安區', '中山區', '松山區', '內湖區'][index % 5]
    })
  );
};

export const createMockOrders = (count: number = 10): Order[] => {
  const customers = createMockCustomers(5);
  return Array.from({ length: count }, (_, index) => 
    createMockOrder({
      customer_id: customers[index % customers.length].id,
      customer: customers[index % customers.length],
      scheduled_date: getFutureDate(index % 7),
      status: ['pending', 'confirmed', 'in_delivery', 'delivered', 'cancelled'][index % 5] as any,
      payment_status: index % 3 === 0 ? 'paid' : 'unpaid'
    })
  );
};

// Form data generators
export const createCustomerFormData = () => ({
  customer_code: `C${String(getNextId()).padStart(6, '0')}`,
  short_name: '新測試客戶',
  invoice_title: '新測試客戶有限公司',
  tax_id: '87654321',
  address: '台北市大安區復興南路二段123號',
  phone1: '0933-456-789',
  phone2: '',
  contact_person: '李大明',
  delivery_address: '',
  area: '大安區',
  is_corporate: true,
  customer_type: 'business',
  credit_limit: 50000,
  payment_terms: 30,
  notes: '新客戶備註'
});

export const createOrderFormData = () => ({
  customer_id: 1,
  scheduled_date: getFutureDate(3),
  qty_50kg: 1,
  qty_20kg: 2,
  qty_16kg: 0,
  qty_10kg: 0,
  qty_4kg: 1,
  delivery_address: '台北市信義區測試路456號',
  delivery_notes: '請電話通知',
  is_urgent: false,
  payment_method: 'monthly_billing'
});

// API response mocks
export const createPaginatedResponse = <T>(items: T[], page: number = 1, size: number = 20) => ({
  items: items.slice((page - 1) * size, page * size),
  total: items.length,
  page,
  size,
  pages: Math.ceil(items.length / size)
});

export const createSuccessResponse = <T>(data: T) => ({
  success: true,
  data,
  message: '操作成功',
  timestamp: new Date().toISOString()
});

export const createErrorResponse = (message: string, status: number = 400) => ({
  success: false,
  error: message,
  status,
  timestamp: new Date().toISOString()
});

// WebSocket message mocks
export const createWebSocketMessage = (type: string, data: any) => ({
  type,
  data,
  timestamp: new Date().toISOString(),
  id: `msg-${getNextId()}`
});

export const createOrderUpdateMessage = (orderId: number, status: string) => 
  createWebSocketMessage('order_update', {
    order_id: orderId,
    status,
    updated_at: new Date().toISOString()
  });

export const createNotificationMessage = (title: string, message: string, severity: 'info' | 'warning' | 'error' | 'success' = 'info') =>
  createWebSocketMessage('notification', {
    title,
    message,
    severity,
    id: `notif-${getNextId()}`
  });