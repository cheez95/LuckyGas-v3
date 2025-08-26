/**
 * Customer API Service
 * 客戶資料 API 服務
 */

import axios, { AxiosResponse } from 'axios';
import {
  CustomerSummary,
  CustomerDetail,
  PaginatedCustomers,
  AnalyticsSummary,
  CustomerFilterParams,
  CylinderInfo,
  EquipmentInfo,
  TimeAvailabilityInfo,
  UsageMetricsInfo
} from '../types/Customer.types';

// API base URL - get from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

/**
 * Customer API Service
 */
export const customerApi = {
  /**
   * Get paginated customer list with filters
   * @param params Filter and pagination parameters
   */
  async getCustomers(params: CustomerFilterParams = {}): Promise<PaginatedCustomers> {
    const queryParams = new URLSearchParams();
    
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.search) queryParams.append('search', params.search);
    if (params.area) queryParams.append('area', params.area);
    if (params.district) queryParams.append('district', params.district);
    if (params.customer_type) queryParams.append('customer_type', params.customer_type);
    if (params.is_active !== undefined) {
      queryParams.append('is_active', params.is_active.toString());
    }

    const response = await apiClient.get<PaginatedCustomers>(
      `/api/v1/customers?${queryParams.toString()}`
    );
    return response.data;
  },

  /**
   * Get complete customer details
   * @param customerId Customer ID
   */
  async getCustomerDetail(customerId: number): Promise<CustomerDetail> {
    const response = await apiClient.get<CustomerDetail>(
      `/api/v1/customers/${customerId}/full`
    );
    return response.data;
  },

  /**
   * Get customer cylinders
   * @param customerId Customer ID
   */
  async getCustomerCylinders(customerId: number): Promise<CylinderInfo[]> {
    const response = await apiClient.get<CylinderInfo[]>(
      `/api/v1/customers/${customerId}/cylinders`
    );
    return response.data;
  },

  /**
   * Get customer equipment
   * @param customerId Customer ID
   */
  async getCustomerEquipment(customerId: number): Promise<EquipmentInfo | null> {
    const response = await apiClient.get<EquipmentInfo | null>(
      `/api/v1/customers/${customerId}/equipment`
    );
    return response.data;
  },

  /**
   * Get customer time slots
   * @param customerId Customer ID
   */
  async getCustomerTimeSlots(customerId: number): Promise<TimeAvailabilityInfo[]> {
    const response = await apiClient.get<TimeAvailabilityInfo[]>(
      `/api/v1/customers/${customerId}/time-slots`
    );
    return response.data;
  },

  /**
   * Get customer usage metrics
   * @param customerId Customer ID
   */
  async getCustomerUsageMetrics(customerId: number): Promise<UsageMetricsInfo | null> {
    const response = await apiClient.get<UsageMetricsInfo | null>(
      `/api/v1/customers/${customerId}/usage-metrics`
    );
    return response.data;
  },

  /**
   * Get analytics summary
   */
  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const response = await apiClient.get<AnalyticsSummary>(
      '/api/v1/customers/analytics/summary'
    );
    return response.data;
  },

  /**
   * Get list of all areas
   */
  async getAreasList(): Promise<string[]> {
    const response = await apiClient.get<string[]>(
      '/api/v1/customers/areas/list'
    );
    return response.data;
  },

  /**
   * Get list of all districts
   */
  async getDistrictsList(): Promise<string[]> {
    const response = await apiClient.get<string[]>(
      '/api/v1/customers/districts/list'
    );
    return response.data;
  }
};

// Export hooks for React Query integration
export const useCustomerQueryKeys = {
  all: ['customers'] as const,
  lists: () => [...useCustomerQueryKeys.all, 'list'] as const,
  list: (params: CustomerFilterParams) => [...useCustomerQueryKeys.lists(), params] as const,
  details: () => [...useCustomerQueryKeys.all, 'detail'] as const,
  detail: (id: number) => [...useCustomerQueryKeys.details(), id] as const,
  cylinders: (id: number) => [...useCustomerQueryKeys.all, 'cylinders', id] as const,
  equipment: (id: number) => [...useCustomerQueryKeys.all, 'equipment', id] as const,
  timeSlots: (id: number) => [...useCustomerQueryKeys.all, 'timeSlots', id] as const,
  metrics: (id: number) => [...useCustomerQueryKeys.all, 'metrics', id] as const,
  analytics: () => [...useCustomerQueryKeys.all, 'analytics'] as const,
  areas: () => [...useCustomerQueryKeys.all, 'areas'] as const,
  districts: () => [...useCustomerQueryKeys.all, 'districts'] as const,
};

// Cache utilities for localStorage
export const customerCache = {
  // Cache customer list for offline access
  saveCustomerList(data: PaginatedCustomers): void {
    try {
      localStorage.setItem('customer_list_cache', JSON.stringify({
        data,
        timestamp: Date.now()
      }));
    } catch (error) {
      console.error('Failed to cache customer list:', error);
    }
  },

  // Get cached customer list
  getCachedCustomerList(): PaginatedCustomers | null {
    try {
      const cached = localStorage.getItem('customer_list_cache');
      if (!cached) return null;

      const parsed = JSON.parse(cached);
      // Check if cache is less than 5 minutes old
      if (Date.now() - parsed.timestamp < 5 * 60 * 1000) {
        return parsed.data;
      }
      return null;
    } catch (error) {
      console.error('Failed to get cached customer list:', error);
      return null;
    }
  },

  // Cache individual customer detail
  saveCustomerDetail(id: number, data: CustomerDetail): void {
    try {
      const key = `customer_detail_${id}`;
      localStorage.setItem(key, JSON.stringify({
        data,
        timestamp: Date.now()
      }));
    } catch (error) {
      console.error('Failed to cache customer detail:', error);
    }
  },

  // Get cached customer detail
  getCachedCustomerDetail(id: number): CustomerDetail | null {
    try {
      const key = `customer_detail_${id}`;
      const cached = localStorage.getItem(key);
      if (!cached) return null;

      const parsed = JSON.parse(cached);
      // Check if cache is less than 10 minutes old
      if (Date.now() - parsed.timestamp < 10 * 60 * 1000) {
        return parsed.data;
      }
      return null;
    } catch (error) {
      console.error('Failed to get cached customer detail:', error);
      return null;
    }
  },

  // Clear all customer cache
  clearCache(): void {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith('customer_')) {
          localStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.error('Failed to clear customer cache:', error);
    }
  }
};

export default customerApi;