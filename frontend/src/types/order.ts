// Order related types
import { OrderItem, OrderItemCreate } from './product';

export type OrderStatus = 
  | 'pending'
  | 'confirmed'
  | 'assigned'
  | 'in_delivery'
  | 'delivered'
  | 'cancelled';

export type PaymentStatus = 
  | 'unpaid'
  | 'paid'
  | 'partial'
  | 'refunded';

export interface Order {
  id: number;
  order_number: string;
  customer_id: number;
  status: OrderStatus;
  order_date: string;
  scheduled_date: string;
  delivery_time_start?: string;
  delivery_time_end?: string;
  
  // Cylinder quantities
  qty_50kg: number;
  qty_20kg: number;
  qty_16kg: number;
  qty_10kg: number;
  qty_4kg: number;
  
  // Pricing
  total_amount: number;
  discount_amount: number;
  final_amount: number;
  
  // Payment
  payment_status: PaymentStatus;
  payment_method?: string;
  invoice_number?: string;
  
  // Delivery
  delivery_address?: string;
  delivery_notes?: string;
  is_urgent: boolean;
  
  // Assignment
  route_id?: number;
  driver_id?: number;
  
  // Timestamps
  created_at: string;
  updated_at?: string;
  delivered_at?: string;
  
  // Related data
  customer?: Customer;
}

export interface OrderCreate {
  customer_id: number;
  scheduled_date: string;
  delivery_time_start?: string;
  delivery_time_end?: string;
  
  // Cylinder quantities
  qty_50kg: number;
  qty_20kg: number;
  qty_16kg: number;
  qty_10kg: number;
  qty_4kg: number;
  
  // Delivery info
  delivery_address?: string;
  delivery_notes?: string;
  is_urgent: boolean;
  
  // Payment
  payment_method?: string;
}

export interface OrderUpdate {
  scheduled_date?: string;
  delivery_time_start?: string;
  delivery_time_end?: string;
  
  // Quantities
  qty_50kg?: number;
  qty_20kg?: number;
  qty_16kg?: number;
  qty_10kg?: number;
  qty_4kg?: number;
  
  // Status
  status?: OrderStatus;
  payment_status?: PaymentStatus;
  
  // Delivery
  delivery_address?: string;
  delivery_notes?: string;
  is_urgent?: boolean;
  
  // Assignment
  route_id?: number;
  driver_id?: number;
}

export interface OrderStats {
  date_range: {
    from: string;
    to: string;
  };
  status_summary: Record<OrderStatus, number>;
  total_revenue: number;
  urgent_orders: number;
  unique_customers: number;
  total_orders: number;
}

export interface Customer {
  id: number;
  customer_code: string;
  invoice_title?: string;
  short_name: string;
  address: string;
  area?: string;
  phone?: string;
  
  // Delivery preferences
  delivery_time_start?: string;
  delivery_time_end?: string;
  
  // Cylinder inventory
  cylinders_50kg: number;
  cylinders_20kg: number;
  cylinders_16kg: number;
  cylinders_10kg: number;
  cylinders_4kg: number;
  
  // Status
  is_active: boolean;
}

// Helper functions
export const getOrderStatusColor = (status: OrderStatus) => {
  const colorMap = {
    pending: 'default',
    confirmed: 'processing',
    assigned: 'warning',
    in_delivery: 'blue',
    delivered: 'success',
    cancelled: 'error',
  };
  return colorMap[status] || 'default';
};

export const getOrderStatusText = (status: OrderStatus) => {
  const textMap = {
    pending: '待確認',
    confirmed: '已確認',
    assigned: '已分配',
    in_delivery: '配送中',
    delivered: '已送達',
    cancelled: '已取消',
  };
  return textMap[status] || status;
};

export const getPaymentStatusColor = (status: PaymentStatus) => {
  const colorMap = {
    unpaid: 'error',
    paid: 'success',
    partial: 'warning',
    refunded: 'default',
  };
  return colorMap[status] || 'default';
};

export const getPaymentStatusText = (status: PaymentStatus) => {
  const textMap = {
    unpaid: '未付款',
    paid: '已付款',
    partial: '部分付款',
    refunded: '已退款',
  };
  return textMap[status] || status;
};

// V2 Order types for flexible product system
export interface OrderV2 {
  id: number;
  orderNumber: string;
  customerId: number;
  status: OrderStatus;
  scheduledDate: string;
  deliveryTimeStart?: string;
  deliveryTimeEnd?: string;
  
  // Pricing
  totalAmount: number;
  discountAmount: number;
  finalAmount: number;
  
  // Payment
  paymentStatus: PaymentStatus;
  paymentMethod?: string;
  invoiceNumber?: string;
  
  // Delivery
  deliveryAddress?: string;
  deliveryNotes?: string;
  isUrgent: boolean;
  
  // Assignment
  routeId?: number;
  driverId?: number;
  
  // Timestamps
  createdAt: string;
  updatedAt?: string;
  deliveredAt?: string;
  
  // Order items (flexible products)
  orderItems: OrderItem[];
  
  // Related data
  customer?: Customer;
  customerName?: string;
  customerPhone?: string;
}

export interface OrderCreateV2 {
  customerId: number;
  scheduledDate: string;
  deliveryTimeStart?: string;
  deliveryTimeEnd?: string;
  
  // Order items
  orderItems: OrderItemCreate[];
  
  // Delivery info
  deliveryAddress?: string;
  deliveryNotes?: string;
  isUrgent?: boolean;
  
  // Payment
  paymentMethod?: string;
}

export interface OrderUpdateV2 {
  scheduledDate?: string;
  deliveryTimeStart?: string;
  deliveryTimeEnd?: string;
  
  // Status
  status?: OrderStatus;
  paymentStatus?: PaymentStatus;
  
  // Delivery
  deliveryAddress?: string;
  deliveryNotes?: string;
  isUrgent?: boolean;
  
  // Assignment
  routeId?: number;
  driverId?: number;
}