export const DeliveryMethod = {
  CYLINDER: 'cylinder',
  FLOW: 'flow'
} as const;

export type DeliveryMethod = typeof DeliveryMethod[keyof typeof DeliveryMethod];

export const ProductAttribute = {
  REGULAR: 'regular',
  COMMERCIAL: 'commercial',
  HAOYUN: 'haoyun',
  PINGAN: 'pingan',
  XINGFU: 'xingfu',
  SPECIAL: 'special'
} as const;

export type ProductAttribute = typeof ProductAttribute[keyof typeof ProductAttribute];

export interface GasProduct {
  id: number;
  delivery_method: DeliveryMethod;
  size_kg: number;
  attribute: ProductAttribute;
  sku: string;
  name_zh: string;
  name_en?: string;
  description?: string;
  unit_price: number;
  deposit_amount: number;
  is_active: boolean;
  is_available: boolean;
  track_inventory: boolean;
  low_stock_threshold: number;
  display_name: string;
}

export interface GasProductCreate {
  delivery_method: DeliveryMethod;
  size_kg: number;
  attribute: ProductAttribute;
  sku?: string;
  name_zh: string;
  name_en?: string;
  description?: string;
  unit_price: number;
  deposit_amount?: number;
  is_active?: boolean;
  is_available?: boolean;
  track_inventory?: boolean;
  low_stock_threshold?: number;
}

export interface GasProductUpdate {
  delivery_method?: DeliveryMethod;
  size_kg?: number;
  attribute?: ProductAttribute;
  sku?: string;
  name_zh?: string;
  name_en?: string;
  description?: string;
  unit_price?: number;
  deposit_amount?: number;
  is_active?: boolean;
  is_available?: boolean;
  track_inventory?: boolean;
  low_stock_threshold?: number;
}

export interface GasProductList {
  items: GasProduct[];
  total: number;
  skip: number;
  limit: number;
}

export interface ProductFilters {
  delivery_method?: DeliveryMethod;
  size_kg?: number;
  attribute?: ProductAttribute;
  is_available?: boolean;
  is_active?: boolean;
}

export interface CustomerInventory {
  id: number;
  customer_id: number;
  gas_product_id: number;
  quantity_owned: number;
  quantity_rented: number;
  quantity_available: number;
  last_updated: string;
  gas_product?: GasProduct;
}

export interface CustomerInventoryList {
  items: CustomerInventory[];
  total: number;
  skip: number;
  limit: number;
}

export interface OrderItem {
  id?: number;
  order_id?: number;
  gas_product_id: number;
  quantity: number;
  unit_price: number;
  subtotal: number;
  discount_percentage: number;
  discount_amount: number;
  final_amount: number;
  is_exchange: boolean;
  empty_received: number;
  is_flow_delivery: boolean;
  meter_reading_start?: number;
  meter_reading_end?: number;
  actual_quantity?: number;
  notes?: string;
  gas_product?: GasProduct;
}

export interface OrderItemCreate {
  gas_product_id: number;
  quantity: number;
  unit_price?: number;
  discount_percentage?: number;
  discount_amount?: number;
  is_exchange?: boolean;
  empty_received?: number;
  is_flow_delivery?: boolean;
  meter_reading_start?: number;
  meter_reading_end?: number;
  actual_quantity?: number;
  notes?: string;
}