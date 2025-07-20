import axios from 'axios';
import type { AxiosError, AxiosInstance } from 'axios';
import { navigateTo } from '../utils/router';

// Extend axios config to include metadata
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: Date;
    };
  }
}

const API_URL = import.meta.env.VITE_API_URL || '';

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
    }
    
    const originalRequest = error.config as any;
    
    // Handle 401 errors - redirect to login for unauthorized requests
    if (error.response?.status === 401 && !originalRequest.url?.includes('/auth/login')) {
      // Clear token and redirect to login
      localStorage.removeItem('access_token');
      
      // Only redirect if not already on login page
      if (!window.location.pathname.includes('/login')) {
        navigateTo('/login');
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;

// Helper function to handle API errors
export const handleApiError = (error: any): string => {
  // Check for timeout error
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return '請求超時，請檢查網路連線或稍後再試';
  }
  
  // Check for network error
  if (error.code === 'ERR_NETWORK') {
    return '網路連線失敗，請檢查網路設定';
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
      return '伺服器錯誤，請稍後再試';
    } else if (status === 404) {
      return '請求的資源不存在';
    } else if (status === 403) {
      return '您沒有權限執行此操作';
    } else if (status === 401) {
      return '登入已過期，請重新登入';
    }
  }
  
  // Fallback to error message if available
  if (error.message) {
    return error.message;
  }
  
  return '發生未知錯誤';
};