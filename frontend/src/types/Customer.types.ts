/**
 * Customer Type Definitions
 * 客戶資料類型定義
 */

// Enums matching backend
export enum CustomerType {
  RESIDENTIAL = "RESIDENTIAL",
  RESTAURANT = "RESTAURANT",
  COMMERCIAL = "COMMERCIAL",
  INDUSTRIAL = "INDUSTRIAL",
  INSTITUTIONAL = "INSTITUTIONAL",
  OTHER = "OTHER"
}

export enum CylinderType {
  STANDARD_50KG = "STANDARD_50KG",
  STANDARD_20KG = "STANDARD_20KG",
  STANDARD_16KG = "STANDARD_16KG",
  STANDARD_10KG = "STANDARD_10KG",
  STANDARD_4KG = "STANDARD_4KG",
  COMMERCIAL_20KG = "COMMERCIAL_20KG",
  FLOW_50KG = "FLOW_50KG",
  FLOW_20KG = "FLOW_20KG",
  FLOW_LUCKY_16KG = "FLOW_LUCKY_16KG",
  LUCKY_16KG = "LUCKY_16KG",
  LUCKY_PILL = "LUCKY_PILL",
  SAFETY_BUCKET_10KG = "SAFETY_BUCKET_10KG"
}

export enum PricingMethod {
  BY_CYLINDER = "BY_CYLINDER",
  BY_WEIGHT = "BY_WEIGHT",
  BY_FLOW = "BY_FLOW",
  CONTRACT = "CONTRACT",
  SPECIAL = "SPECIAL"
}

export enum PaymentMethod {
  CASH = "CASH",
  MONTHLY = "MONTHLY",
  QUARTERLY = "QUARTERLY",
  CREDIT = "CREDIT",
  TRANSFER = "TRANSFER"
}

// Cylinder info
export interface CylinderInfo {
  cylinder_type: string;
  quantity: number;
}

// Time availability
export interface TimeAvailabilityInfo {
  weekday: string;
  time_slot: string;
  is_available: boolean;
}

// Equipment info
export interface EquipmentInfo {
  has_switch_valve: boolean;
  has_gas_meter: boolean;
  has_monitoring_device: boolean;
  has_safety_equipment: boolean;
  equipment_notes?: string;
}

// Usage area info
export interface UsageAreaInfo {
  area_number: number;
  description?: string;
  usage_type?: string;
}

// Usage metrics
export interface UsageMetricsInfo {
  monthly_consumption?: number;
  average_cylinder_count?: number;
  refill_frequency_days?: number;
  consumption_pattern?: string;
}

// Customer summary for list view
export interface CustomerSummary {
  id: number;
  customer_code: string;
  short_name: string;
  customer_type: string;
  district: string;
  area: string;
  address: string;
  is_active: boolean;
  cylinder_summary: string;
  pricing_method: string;
  payment_method: string;
}

// Complete customer details
export interface CustomerDetail {
  // Basic info
  id: number;
  customer_code: string;
  short_name: string;
  full_name?: string;
  customer_type: string;
  district: string;
  area: string;
  address: string;
  phone?: string;
  contact_person?: string;
  
  // Pricing and payment
  pricing_method: string;
  payment_method: string;
  requires_invoice_file: boolean;
  
  // Status
  is_active: boolean;
  is_vip: boolean;
  has_contract: boolean;
  termination_date?: Date | null;
  
  // Notes
  notes?: string;
  registration_number?: string;
  order_note?: string;
  address_note?: string;
  
  // Related data
  cylinders: CylinderInfo[];
  time_availability: TimeAvailabilityInfo[];
  equipment?: EquipmentInfo | null;
  usage_areas: UsageAreaInfo[];
  usage_metrics?: UsageMetricsInfo | null;
}

// API response for paginated list
export interface PaginatedCustomers {
  items: CustomerSummary[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

// Analytics summary
export interface AnalyticsSummary {
  total_customers: number;
  active_customers: number;
  customers_by_area: Record<string, number>;
  customers_by_type: Record<string, number>;
  cylinder_distribution: Record<string, number>;
  payment_methods: Record<string, number>;
  pricing_methods: Record<string, number>;
  time_preference_heatmap: Array<{
    weekday: string;
    time_slot: string;
    count: number;
  }>;
  equipment_adoption: Record<string, number>;
}

// Filter parameters
export interface CustomerFilterParams {
  page?: number;
  limit?: number;
  search?: string;
  area?: string;
  district?: string;
  customer_type?: string;
  is_active?: boolean;
}

// Cylinder type display mapping
export const CylinderTypeDisplay: Record<string, string> = {
  STANDARD_50KG: "標準 50公斤",
  STANDARD_20KG: "標準 20公斤",
  STANDARD_16KG: "標準 16公斤",
  STANDARD_10KG: "標準 10公斤",
  STANDARD_4KG: "標準 4公斤",
  COMMERCIAL_20KG: "營業用 20公斤",
  FLOW_50KG: "流量計 50公斤",
  FLOW_20KG: "流量計 20公斤",
  FLOW_LUCKY_16KG: "流量計幸福瓶 16公斤",
  LUCKY_16KG: "幸福瓶 16公斤",
  LUCKY_PILL: "幸福丸",
  SAFETY_BUCKET_10KG: "安全桶裝 10公斤"
};

// Customer type display mapping
export const CustomerTypeDisplay: Record<string, string> = {
  RESIDENTIAL: "住宅",
  RESTAURANT: "餐飲業",
  COMMERCIAL: "商業",
  INDUSTRIAL: "工業",
  INSTITUTIONAL: "機構",
  OTHER: "其他"
};

// Payment method display
export const PaymentMethodDisplay: Record<string, string> = {
  CASH: "現金",
  MONTHLY: "月結",
  QUARTERLY: "季結",
  CREDIT: "信用卡",
  TRANSFER: "轉帳"
};

// Pricing method display
export const PricingMethodDisplay: Record<string, string> = {
  BY_CYLINDER: "按瓶計價",
  BY_WEIGHT: "按重量計價",
  BY_FLOW: "按流量計價",
  CONTRACT: "合約價",
  SPECIAL: "特殊價"
};

// Weekday display
export const WeekdayDisplay: Record<string, string> = {
  MONDAY: "星期一",
  TUESDAY: "星期二",
  WEDNESDAY: "星期三",
  THURSDAY: "星期四",
  FRIDAY: "星期五",
  SATURDAY: "星期六",
  SUNDAY: "星期日"
};

// Time slot display
export const TimeSlotDisplay: Record<string, string> = {
  "MORNING_6_8": "早上 6-8",
  "MORNING_8_10": "早上 8-10",
  "MORNING_10_12": "早上 10-12",
  "AFTERNOON_12_14": "下午 12-14",
  "AFTERNOON_14_16": "下午 14-16",
  "AFTERNOON_16_18": "下午 16-18",
  "EVENING_18_20": "晚上 18-20",
  "EVENING_20_22": "晚上 20-22",
  "NIGHT_22_24": "深夜 22-24",
  "ANYTIME": "任何時間"
};