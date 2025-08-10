import axios from 'axios';
import type { AxiosError, AxiosInstance } from 'axios';
import { message } from 'antd';
import { navigateTo } from '../utils/router';
import { performanceMonitor } from './performance.service';
import i18n from '../utils/i18n';
import { setupRetryInterceptor, setupCircuitBreakerInterceptor } from './apiInterceptor';
import { setupGlobalErrorHandlers } from '../utils/errorHandler';

// Extend axios config to include metadata
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: Date;
    };
  }
}

// Check for runtime override first, then fall back to environment variable
const API_URL = (window as any).LUCKY_GAS_BACKEND_URL || 
                (window as any).API_URL || 
                import.meta.env.VITE_API_URL || 
                'https://luckygas-backend-full-154687573210.asia-east1.run.app';

console.log('🔧 API URL configured as:', API_URL);

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_URL ? `${API_URL}/api/v1` : '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
  withCredentials: true, // Include credentials for CORS
});

// Request interceptor to add auth token and log requests
api.interceptors.request.use(
  (config) => {
    // Add auth token
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log(`🔐 Adding Authorization header to ${config.url}:`, config.headers.Authorization.substring(0, 50) + '...');
    } else {
      console.log(`🔐 No token found for ${config.url}`);
    }
    
    // Add request timestamp for performance monitoring
    config.metadata = { startTime: new Date() };
    
    // Log request in development
    if (import.meta.env.DEV) {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
        params: config.params,
        data: config.data,
      });
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

import { tokenRefreshService } from './tokenRefresh';

// Flag to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

// Helper to notify all subscribers when token is refreshed
const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

// Helper to add request to queue while refreshing
const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

// Response interceptor to handle token refresh and log responses
api.interceptors.response.use(
  (response) => {
    // Log response time in development
    if (import.meta.env.DEV && response.config.metadata) {
      const endTime = new Date();
      const duration = endTime.getTime() - response.config.metadata.startTime.getTime();
      
      const emoji = duration < 1000 ? '✅' : duration < 3000 ? '⚠️' : '🐌';
      console.log(`${emoji} API Response: ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`, {
        status: response.status,
        data: response.data,
      });
      
      // Warn if response is slow
      if (duration > 5000) {
        console.warn(`⚠️ Slow API Response: ${response.config.url} took ${duration}ms`);
      }
      
      // Track performance metrics
      const endpoint = response.config.url || 'unknown';
      performanceMonitor.trackApiCall(endpoint, duration, true, response.status);
    }
    
    return response;
  },
  async (error: AxiosError) => {
    // Log error response time
    if (import.meta.env.DEV && error.config?.metadata) {
      const endTime = new Date();
      const duration = endTime.getTime() - error.config.metadata.startTime.getTime();
      
      console.error(`❌ API Error: ${error.config.method?.toUpperCase()} ${error.config.url} - ${duration}ms`, {
        status: error.response?.status,
        error: error.response?.data || error.message,
        code: error.code,
      });
      
      // Track failed API calls
      const endpoint = error.config.url || 'unknown';
      performanceMonitor.trackApiCall(endpoint, duration, false, error.response?.status);
    }
    
    const originalRequest = error.config as any;
    
    // Handle 401 errors - try to refresh token first
    if (error.response?.status === 401 && !originalRequest.url?.includes('/auth/login') && !originalRequest.url?.includes('/auth/refresh')) {
      console.log(`🔐 Got 401 for ${originalRequest.url}, retry status:`, originalRequest._retry);
      
      // Mark request as retry to avoid infinite loop
      if (originalRequest._retry) {
        // Already tried to refresh, clear tokens and redirect
        console.log('🔐 Already tried refresh, clearing tokens...');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token_expiry');
        message.error(i18n.t('auth.sessionExpired'));
        
        if (!window.location.pathname.includes('/login')) {
          navigateTo('/login');
        }
        return Promise.reject(error);
      }
      
      originalRequest._retry = true;
      
      // If not already refreshing, start refresh process
      if (!isRefreshing) {
        isRefreshing = true;
        
        try {
          const { access_token } = await tokenRefreshService.refreshToken();
          isRefreshing = false;
          onTokenRefreshed(access_token);
          
          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          isRefreshing = false;
          return Promise.reject(refreshError);
        }
      }
      
      // If already refreshing, queue this request
      return new Promise((resolve) => {
        addRefreshSubscriber((token: string) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          resolve(api(originalRequest));
        });
      });
    }
    
    // Handle 404 errors
    if (error.response?.status === 404) {
      message.error(i18n.t('message.error.notFound'));
    }
    
    // Handle 500 errors
    if (error.response?.status >= 500) {
      message.error(i18n.t('message.error.serverError'));
    }
    
    // Handle network errors
    if (error.code === 'ERR_NETWORK') {
      message.error(i18n.t('message.error.network'));
    }
    
    // Handle timeout errors
    if (error.code === 'ECONNABORTED') {
      message.error(i18n.t('message.error.timeout'));
    }
    
    return Promise.reject(error);
  }
);

export default api;

// Helper function to handle API errors
export const handleApiError = (error: any): string => {
  // Check for timeout error
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return i18n.t('message.error.timeout');
  }
  
  // Check for network error
  if (error.code === 'ERR_NETWORK') {
    return i18n.t('message.error.network');
  }
  
  // Check for server errors
  if (error.response) {
    const status = error.response.status;
    
    // Check for detailed error message from server first
    if (error.response.data?.detail) {
      return error.response.data.detail;
    } else if (error.response.data?.message) {
      return error.response.data.message;
    }
    
    // Fallback to generic messages based on status code
    if (status >= 500) {
      return i18n.t('message.error.serverError');
    } else if (status === 404) {
      return i18n.t('message.error.notFound');
    } else if (status === 403) {
      return i18n.t('message.error.unauthorized');
    } else if (status === 401) {
      return i18n.t('auth.sessionExpired');
    }
  }
  
  // Fallback to error message if available
  if (error.message) {
    return error.message;
  }
  
  return i18n.t('message.error.general');
};

// Setup error handling and interceptors
setupRetryInterceptor(api);
setupCircuitBreakerInterceptor(api);
setupGlobalErrorHandlers();