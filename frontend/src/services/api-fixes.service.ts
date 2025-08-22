/**
 * API Fixes Service
 * Provides wrapper functions with proper error handling and parameter formatting
 */

import api from './api';
import { apiClient } from './api.service';
import moment from 'moment';

export const apiFixesService = {
  /**
   * Get customer statistics with proper date parameters
   */
  async getCustomerStatistics(includeInactive = false) {
    try {
      const params = {
        include_inactive: includeInactive,
        date_from: moment().startOf('month').format('YYYY-MM-DD'),
        date_to: moment().endOf('month').format('YYYY-MM-DD')
      };
      const response = await api.get('/customers/statistics', { params });
      return response.data;
    } catch (error: any) {
      console.warn('Customer statistics endpoint failed, returning defaults');
      // Return default statistics if endpoint fails
      return {
        total_customers: 0,
        active_customers: 0,
        inactive_customers: 0,
        customers_with_delivery_today: 0,
        customers_with_overdue: 0,
        new_customers_this_month: 0
      };
    }
  },

  /**
   * Search orders with proper query parameters
   */
  async searchOrders(searchText: string, status = 'all', options = {}) {
    try {
      const params = {
        q: searchText || '',
        status: status,
        skip: 0,
        limit: 100,
        ...options
      };
      
      // Try the search endpoint with GET
      const response = await api.get('/orders/search', { params });
      return {
        orders: response.data.orders || response.data.items || [],
        total: response.data.total || 0
      };
    } catch (error: any) {
      // If search endpoint fails, fall back to regular orders endpoint
      if (error.response?.status === 404) {
        console.warn('Search endpoint not found, using regular orders endpoint');
        try {
          const response = await api.get('/orders', { 
            params: { 
              search: searchText,
              status: status === 'all' ? undefined : status 
            } 
          });
          return {
            orders: response.data.items || [],
            total: response.data.total || 0
          };
        } catch (fallbackError) {
          console.error('Orders endpoint also failed:', fallbackError);
        }
      }
      
      return { orders: [], total: 0 };
    }
  },

  /**
   * Get deliveries (handles both delivery-history and deliveries endpoints)
   */
  async getDeliveries(params = {}) {
    const endpoints = ['/deliveries', '/delivery-history', '/orders'];
    
    for (const endpoint of endpoints) {
      try {
        const response = await api.get(endpoint, { params });
        return {
          items: response.data.items || response.data.deliveries || [],
          total: response.data.total || 0
        };
      } catch (error: any) {
        if (error.response?.status !== 404) {
          throw error; // Re-throw non-404 errors
        }
        // Continue to next endpoint on 404
      }
    }
    
    // All endpoints failed, return empty
    console.warn('No delivery endpoints available');
    return { items: [], total: 0 };
  },

  /**
   * Get delivery statistics
   */
  async getDeliveryStats(dateRange?: { from: string; to: string }) {
    try {
      const params = dateRange ? {
        date_from: dateRange.from,
        date_to: dateRange.to
      } : {};
      
      // Try multiple possible endpoints
      const endpoints = ['/deliveries/stats', '/delivery-history/stats', '/analytics/delivery-stats'];
      
      for (const endpoint of endpoints) {
        try {
          const response = await api.get(endpoint, { params });
          return response.data;
        } catch (error: any) {
          if (error.response?.status !== 404) {
            throw error;
          }
        }
      }
      
      // All failed, return defaults
      return {
        total_deliveries: 0,
        total_amount: 0,
        total_customers: 0,
        total_drivers: 0,
        average_delivery_time: 0
      };
    } catch (error) {
      console.error('Failed to get delivery stats:', error);
      return {
        total_deliveries: 0,
        total_amount: 0,
        total_customers: 0,
        total_drivers: 0,
        average_delivery_time: 0
      };
    }
  },

  /**
   * Health check with proper error handling
   */
  async healthCheck() {
    try {
      const response = await api.get('/health');
      return { 
        status: 'healthy', 
        message: 'API is running',
        ...response.data 
      };
    } catch (error: any) {
      // Don't throw on health check failure
      return { 
        status: 'unhealthy', 
        message: error.message || 'API is not responding',
        error: error.response?.data || error.message
      };
    }
  },

  /**
   * Configure CORS headers for requests
   */
  configureCORS() {
    // Add CORS headers to all requests
    api.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
    api.defaults.headers.common['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS';
    api.defaults.headers.common['Access-Control-Allow-Headers'] = 'Content-Type, Authorization';
    
    // Also configure for apiClient
    apiClient.defaults.headers.common['Access-Control-Allow-Origin'] = '*';
    apiClient.defaults.headers.common['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS';
    apiClient.defaults.headers.common['Access-Control-Allow-Headers'] = 'Content-Type, Authorization';
  }
};

// Configure CORS on service load
apiFixesService.configureCORS();

export default apiFixesService;