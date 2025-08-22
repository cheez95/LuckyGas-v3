import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { withRetry, isRetryableError } from '../utils/fetchWithRetry';

// Get API URL from environment variables - use HTTPS production URL as fallback
const API_URL = import.meta.env.VITE_API_URL || 'https://luckygas-backend-full-154687573210.asia-east1.run.app';

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 10000, // 10 seconds timeout (reduced from 30)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and force HTTPS
apiClient.interceptors.request.use(
  (config) => {
    // CRITICAL: Force HTTPS for all requests
    if (config.baseURL && config.baseURL.includes('http://')) {
      console.warn(`[Axios HTTPS Override] Converting HTTP to HTTPS: ${config.baseURL}`);
      config.baseURL = config.baseURL.replace('http://', 'https://');
    }
    if (config.url && config.url.includes('http://')) {
      console.warn(`[Axios HTTPS Override] Converting HTTP to HTTPS: ${config.url}`);
      config.url = config.url.replace('http://', 'https://');
    }
    
    // CRITICAL: Remove trailing slashes to prevent 307 redirects that lose auth headers
    if (config.url && config.url.length > 1 && config.url.endsWith('/')) {
      console.warn(`[Axios Trailing Slash Fix] Removing trailing slash from: ${config.url}`);
      config.url = config.url.slice(0, -1);
    }
    
    // Add auth token from localStorage if available
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log request for debugging
    if (import.meta.env.DEV) {
      console.log(`🔐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    }
    
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          if (response.data.access_token) {
            localStorage.setItem('access_token', response.data.access_token);
            originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
            return apiClient(originalRequest);
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          // Clear tokens but DON'T redirect - let ProtectedRoute handle it
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('token_expiry');
          // Dispatch a custom event that AuthContext can listen to
          window.dispatchEvent(new Event('auth:logout'));
        }
      } else {
        // No refresh token, clear storage but don't redirect
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token_expiry');
        // Let ProtectedRoute handle navigation
        window.dispatchEvent(new Event('auth:logout'));
      }
    }
    
    // Log error for debugging
    if (import.meta.env.DEV) {
      console.error(`❌ API Error: ${error.response?.status} ${error.config?.url}`);
      console.error('Error details:', error.response?.data);
    }
    
    return Promise.reject(error);
  }
);

// Export additional utilities
export default apiClient;

// API methods with retry logic for critical operations
export const apiWithRetry = {
  /**
   * GET request with retry logic
   */
  get: <T = any>(url: string, config?: AxiosRequestConfig) => 
    withRetry<AxiosResponse<T>>(
      () => apiClient.get<T>(url, config),
      {
        maxRetries: 3,
        retryCondition: isRetryableError
      }
    ),

  /**
   * POST request with retry logic
   */
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    withRetry<AxiosResponse<T>>(
      () => apiClient.post<T>(url, data, config),
      {
        maxRetries: 2, // Fewer retries for POST to avoid duplicate submissions
        retryCondition: (error) => {
          // Only retry POST on network errors, not server errors
          return !error.response && isRetryableError(error);
        }
      }
    ),

  /**
   * PUT request with retry logic
   */
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    withRetry<AxiosResponse<T>>(
      () => apiClient.put<T>(url, data, config),
      {
        maxRetries: 3,
        retryCondition: isRetryableError
      }
    ),

  /**
   * DELETE request with retry logic
   */
  delete: <T = any>(url: string, config?: AxiosRequestConfig) =>
    withRetry<AxiosResponse<T>>(
      () => apiClient.delete<T>(url, config),
      {
        maxRetries: 3,
        retryCondition: isRetryableError
      }
    )
};

/**
 * Health check with aggressive retry
 */
export async function checkBackendHealth(): Promise<any> {
  return withRetry(
    async () => {
      const response = await axios.get(`${API_URL}/health`, {
        timeout: 5000
      });
      return response.data;
    },
    {
      maxRetries: 5,
      initialDelay: 500,
      retryCondition: () => true // Always retry health checks
    }
  );
}

/**
 * Request manager with AbortController support
 */
class RequestManager {
  private abortControllers: Map<string, AbortController> = new Map();
  private requestCache: Map<string, { data: any; timestamp: number }> = new Map();
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();
  private readonly CACHE_TTL = 60000; // 1 minute cache

  /**
   * Make a cancellable request
   */
  async request<T = any>(
    key: string,
    requestFn: (signal: AbortSignal) => Promise<AxiosResponse<T>>,
    options?: {
      cache?: boolean;
      debounce?: number;
    }
  ): Promise<AxiosResponse<T>> {
    // Check cache first
    if (options?.cache) {
      const cached = this.requestCache.get(key);
      if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
        return { data: cached.data } as AxiosResponse<T>;
      }
    }

    // Handle debouncing
    if (options?.debounce) {
      return new Promise((resolve, reject) => {
        // Clear existing timer
        const existingTimer = this.debounceTimers.get(key);
        if (existingTimer) {
          clearTimeout(existingTimer);
        }

        // Set new timer
        const timer = setTimeout(async () => {
          this.debounceTimers.delete(key);
          try {
            const result = await this.executeRequest(key, requestFn, options?.cache);
            resolve(result);
          } catch (error) {
            reject(error);
          }
        }, options.debounce);

        this.debounceTimers.set(key, timer);
      });
    }

    return this.executeRequest(key, requestFn, options?.cache);
  }

  private async executeRequest<T>(
    key: string,
    requestFn: (signal: AbortSignal) => Promise<AxiosResponse<T>>,
    cache?: boolean
  ): Promise<AxiosResponse<T>> {
    // Cancel any existing request with the same key
    this.cancel(key);

    // Create new abort controller
    const controller = new AbortController();
    this.abortControllers.set(key, controller);

    try {
      const response = await requestFn(controller.signal);
      
      // Cache successful response
      if (cache && response.data) {
        this.requestCache.set(key, {
          data: response.data,
          timestamp: Date.now()
        });
      }

      return response;
    } catch (error: any) {
      if (error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
        throw new Error('Request cancelled');
      }
      throw error;
    } finally {
      this.abortControllers.delete(key);
    }
  }

  /**
   * Cancel a specific request
   */
  cancel(key: string): void {
    const controller = this.abortControllers.get(key);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(key);
    }

    // Clear debounce timer if exists
    const timer = this.debounceTimers.get(key);
    if (timer) {
      clearTimeout(timer);
      this.debounceTimers.delete(key);
    }
  }

  /**
   * Cancel all pending requests
   */
  cancelAll(): void {
    this.abortControllers.forEach(controller => controller.abort());
    this.abortControllers.clear();
    
    this.debounceTimers.forEach(timer => clearTimeout(timer));
    this.debounceTimers.clear();
  }

  /**
   * Clear cache
   */
  clearCache(key?: string): void {
    if (key) {
      this.requestCache.delete(key);
    } else {
      this.requestCache.clear();
    }
  }

  /**
   * Get cache size
   */
  getCacheSize(): number {
    return this.requestCache.size;
  }
}

// Export request manager instance
export const requestManager = new RequestManager();

/**
 * API client with cancellation support
 */
export const apiWithCancel = {
  get: <T = any>(url: string, key: string, options?: any) =>
    requestManager.request<T>(
      key,
      (signal) => apiClient.get<T>(url, { ...options, signal }),
      options
    ),

  post: <T = any>(url: string, data: any, key: string, options?: any) =>
    requestManager.request<T>(
      key,
      (signal) => apiClient.post<T>(url, data, { ...options, signal }),
      options
    ),

  put: <T = any>(url: string, data: any, key: string, options?: any) =>
    requestManager.request<T>(
      key,
      (signal) => apiClient.put<T>(url, data, { ...options, signal }),
      options
    ),

  delete: <T = any>(url: string, key: string, options?: any) =>
    requestManager.request<T>(
      key,
      (signal) => apiClient.delete<T>(url, { ...options, signal }),
      options
    ),
};