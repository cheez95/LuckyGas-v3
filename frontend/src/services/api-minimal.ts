/**
 * Minimal API client with retry logic and better error handling
 * For use with the emergency minimal backend
 */
import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // Start with 1 second
const REQUEST_TIMEOUT = 30000; // 30 seconds

// Error messages in Traditional Chinese
const ERROR_MESSAGES = {
  NETWORK_ERROR: '網路連線錯誤，請稍後再試',
  AUTH_EXPIRED: '認證已過期，請重新登入',
  SERVER_ERROR: '伺服器錯誤，請聯繫管理員',
  TIMEOUT: '請求超時，請檢查網路連線',
  UNKNOWN: '發生未知錯誤',
};

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request queue for offline support
const requestQueue: Array<{
  config: AxiosRequestConfig;
  resolve: (value: any) => void;
  reject: (reason: any) => void;
}> = [];

// Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log request in development
    if (import.meta.env.DEV) {
      // console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
        params: config.params,
        data: config.data,
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Exponential backoff retry logic
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const retryRequest = async (error: AxiosError, retryCount = 0): Promise<any> => {
  const config = error.config;
  
  if (!config || retryCount >= MAX_RETRIES) {
    return Promise.reject(error);
  }
  
  // Don't retry auth endpoints
  if (config.url?.includes('/auth/')) {
    return Promise.reject(error);
  }
  
  // Calculate delay with exponential backoff
  const delay = RETRY_DELAY * Math.pow(2, retryCount);
  
  console.warn(`⚠️ Retrying request (${retryCount + 1}/${MAX_RETRIES}) after ${delay}ms...`);
  await sleep(delay);
  
  // Retry the request
  return apiClient.request(config).catch((err) => retryRequest(err, retryCount + 1));
};

// Response interceptor with retry logic
apiClient.interceptors.response.use(
  (response) => {
    // Log response in development
    if (import.meta.env.DEV) {
      // console.log(`✅ API Response: ${response.config.url}`, response.data);
    }
    return response;
  },
  async (error: AxiosError) => {
    // Log error
    console.error('❌ API Error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
    });
    
    // Handle different error types
    if (error.code === 'ECONNABORTED') {
      // Timeout
      throw new Error(ERROR_MESSAGES.TIMEOUT);
    }
    
    if (!error.response) {
      // Network error - attempt retry
      if (error.code === 'ERR_NETWORK') {
        try {
          return await retryRequest(error);
        } catch (retryError) {
          // Queue for later if all retries fail
          if (error.config) {
            return new Promise((resolve, reject) => {
              requestQueue.push({
                config: error.config!,
                resolve,
                reject,
              });
              reject(new Error(ERROR_MESSAGES.NETWORK_ERROR));
            });
          }
        }
      }
      throw new Error(ERROR_MESSAGES.NETWORK_ERROR);
    }
    
    // Handle specific status codes
    switch (error.response.status) {
      case 401:
        // Clear token and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        throw new Error(ERROR_MESSAGES.AUTH_EXPIRED);
        
      case 500:
      case 502:
      case 503:
        // Server error - attempt retry
        try {
          return await retryRequest(error);
        } catch (retryError) {
          throw new Error(ERROR_MESSAGES.SERVER_ERROR);
        }
        
      default:
        // Return the error response data if available
        if (error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data) {
          throw new Error(error.response.data.detail as string);
        }
        throw new Error(ERROR_MESSAGES.UNKNOWN);
    }
  }
);

// Process queued requests when connection is restored
export const processRequestQueue = async () => {
  // console.log(`📤 Processing ${requestQueue.length} queued requests...`);
  
  while (requestQueue.length > 0) {
    const { config, resolve, reject } = requestQueue.shift()!;
    
    try {
      const response = await apiClient.request(config);
      resolve(response);
    } catch (error) {
      reject(error);
    }
  }
};

// Check connection status
export const checkConnection = async (): Promise<boolean> => {
  try {
    await apiClient.get('/api/v1/health');
    return true;
  } catch {
    return false;
  }
};

// Listen for online event
window.addEventListener('online', () => {
  // console.log('🌐 Connection restored, processing queued requests...');
  processRequestQueue();
});

// Export configured client
export default apiClient;

// Convenience methods
export const api = {
  get: <T = any>(url: string, config?: AxiosRequestConfig) => 
    apiClient.get<T>(url, config).then(res => res.data),
    
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => 
    apiClient.post<T>(url, data, config).then(res => res.data),
    
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => 
    apiClient.put<T>(url, data, config).then(res => res.data),
    
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => 
    apiClient.delete<T>(url, config).then(res => res.data),
};