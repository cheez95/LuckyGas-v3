import { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { notification } from 'antd';
import { 
  showErrorNotification, 
  isRetryableError, 
  logError, 
  getUserFriendlyMessage 
} from '../utils/errorHandler';

// Extend axios config for retry metadata
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    _retryCount?: number;
    _retryDelay?: number;
    _requestId?: string;
    skipRetry?: boolean;
    skipErrorNotification?: boolean;
  }
}

// Retry configuration
interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  shouldRetry?: (error: AxiosError) => boolean;
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,  // 1 second
  maxDelay: 10000,  // 10 seconds
};

// Calculate exponential backoff delay
function calculateRetryDelay(retryCount: number, baseDelay: number, maxDelay: number): number {
  const delay = Math.min(baseDelay * Math.pow(2, retryCount), maxDelay);
  // Add jitter to prevent thundering herd
  const jitter = Math.random() * 0.3 * delay;
  return Math.floor(delay + jitter);
}

// Sleep helper for retry delay
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Setup retry interceptor
export function setupRetryInterceptor(
  axiosInstance: AxiosInstance,
  config: Partial<RetryConfig> = {}
) {
  const retryConfig: RetryConfig = {
    ...DEFAULT_RETRY_CONFIG,
    ...config,
  };

  // Add request ID for tracking
  axiosInstance.interceptors.request.use(
    (config) => {
      // Generate unique request ID
      if (!config._requestId) {
        config._requestId = `REQ-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      }
      
      // Initialize retry count
      if (config._retryCount === undefined) {
        config._retryCount = 0;
      }
      
      // Log request with ID
      if (import.meta.env.DEV) {
        // console.log(`🚀 [${config._requestId}] API Request:`, {
        //   method: config.method,
        //   url: config.url,
        //   retryCount: config._retryCount,
        // });
      }
      
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Add retry logic to response interceptor
  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const config = error.config as InternalAxiosRequestConfig;
      
      if (!config) {
        return Promise.reject(error);
      }

      // Skip retry if explicitly disabled
      if (config.skipRetry) {
        if (!config.skipErrorNotification) {
          showErrorNotification(error);
        }
        return Promise.reject(error);
      }

      // Check if we should retry
      const shouldRetry = retryConfig.shouldRetry 
        ? retryConfig.shouldRetry(error) 
        : isRetryableError(error);

      const retryCount = config._retryCount || 0;
      
      if (!shouldRetry || retryCount >= retryConfig.maxRetries) {
        // Log final failure
        if (import.meta.env.DEV) {
          console.error(`❌ [${config._requestId}] Request failed after ${retryCount} retries:`, {
            url: config.url,
            status: error.response?.status,
            error: error.message,
          });
        }
        
        // Show error notification
        if (!config.skipErrorNotification) {
          showErrorNotification(error);
        }
        
        // Log error for monitoring
        logError(error, {
          requestId: config._requestId,
          retryCount,
          url: config.url,
          method: config.method,
        });
        
        return Promise.reject(error);
      }

      // Calculate retry delay
      const delay = calculateRetryDelay(retryCount, retryConfig.baseDelay, retryConfig.maxDelay);
      
      // Update retry count
      config._retryCount = retryCount + 1;
      config._retryDelay = delay;
      
      // Log retry attempt
      if (import.meta.env.DEV) {
        // console.log(`🔄 [${config._requestId}] Retrying request (${config._retryCount}/${retryConfig.maxRetries}) after ${delay}ms:`, {
        //   url: config.url,
        //   status: error.response?.status,
        //   reason: error.message,
        // });
      }
      
      // Show retry notification for long delays
      if (delay > 3000) {
        notification.info({
          message: '重試中',
          description: `正在重新嘗試連線... (第 ${config._retryCount} 次)`,
          duration: 2,
        });
      }
      
      // Wait before retrying
      await sleep(delay);
      
      // Retry the request
      return axiosInstance.request(config);
    }
  );
}

// Circuit breaker implementation
export class CircuitBreaker {
  private failures: Map<string, number> = new Map();
  private lastFailureTime: Map<string, number> = new Map();
  private circuitState: Map<string, 'closed' | 'open' | 'half-open'> = new Map();
  
  private readonly threshold: number;
  private readonly timeout: number;
  private readonly resetTimeout: number;
  
  constructor(
    threshold = 5,           // Number of failures before opening
    timeout = 60000,        // Time window for failures (1 minute)
    resetTimeout = 30000    // Time before trying half-open (30 seconds)
  ) {
    this.threshold = threshold;
    this.timeout = timeout;
    this.resetTimeout = resetTimeout;
  }
  
  isOpen(endpoint: string): boolean {
    const state = this.circuitState.get(endpoint);
    
    if (state === 'open') {
      const lastFailure = this.lastFailureTime.get(endpoint) || 0;
      const now = Date.now();
      
      // Check if we should try half-open
      if (now - lastFailure > this.resetTimeout) {
        this.circuitState.set(endpoint, 'half-open');
        return false;
      }
      
      return true;
    }
    
    return false;
  }
  
  recordSuccess(endpoint: string): void {
    const state = this.circuitState.get(endpoint);
    
    if (state === 'half-open') {
      // Reset circuit on successful half-open attempt
      this.circuitState.set(endpoint, 'closed');
      this.failures.delete(endpoint);
      this.lastFailureTime.delete(endpoint);
      
      if (import.meta.env.DEV) {
        // console.log(`⚡ Circuit breaker closed for ${endpoint}`);
      }
    }
  }
  
  recordFailure(endpoint: string): void {
    const now = Date.now();
    const failures = this.failures.get(endpoint) || 0;
    const lastFailure = this.lastFailureTime.get(endpoint) || 0;
    
    // Reset counter if outside time window
    if (now - lastFailure > this.timeout) {
      this.failures.set(endpoint, 1);
    } else {
      this.failures.set(endpoint, failures + 1);
    }
    
    this.lastFailureTime.set(endpoint, now);
    
    // Check if we should open the circuit
    const currentFailures = this.failures.get(endpoint) || 0;
    if (currentFailures >= this.threshold) {
      const previousState = this.circuitState.get(endpoint);
      this.circuitState.set(endpoint, 'open');
      
      if (previousState !== 'open' && import.meta.env.DEV) {
        console.warn(`⚠️ Circuit breaker opened for ${endpoint} after ${currentFailures} failures`);
      }
      
      // Show user notification
      notification.warning({
        message: '服務暫時無法使用',
        description: '系統檢測到服務異常，請稍後再試',
        duration: 5,
      });
    }
  }
  
  getState(endpoint: string): 'closed' | 'open' | 'half-open' {
    return this.circuitState.get(endpoint) || 'closed';
  }
  
  reset(endpoint?: string): void {
    if (endpoint) {
      this.failures.delete(endpoint);
      this.lastFailureTime.delete(endpoint);
      this.circuitState.delete(endpoint);
    } else {
      this.failures.clear();
      this.lastFailureTime.clear();
      this.circuitState.clear();
    }
  }
}

// Global circuit breaker instance
export const circuitBreaker = new CircuitBreaker();

// Setup circuit breaker interceptor
export function setupCircuitBreakerInterceptor(axiosInstance: AxiosInstance) {
  // Check circuit before request
  axiosInstance.interceptors.request.use(
    (config) => {
      const endpoint = config.url || '';
      
      if (circuitBreaker.isOpen(endpoint)) {
        const error = new Error('Circuit breaker is open') as any;
        error.code = 'CIRCUIT_BREAKER_OPEN';
        error.config = config;
        
        if (import.meta.env.DEV) {
          console.warn(`🔌 Circuit breaker blocked request to ${endpoint}`);
        }
        
        return Promise.reject(error);
      }
      
      return config;
    },
    (error) => Promise.reject(error)
  );
  
  // Record success/failure after response
  axiosInstance.interceptors.response.use(
    (response) => {
      const endpoint = response.config.url || '';
      circuitBreaker.recordSuccess(endpoint);
      return response;
    },
    (error: AxiosError) => {
      if (error.code !== 'CIRCUIT_BREAKER_OPEN') {
        const endpoint = error.config?.url || '';
        circuitBreaker.recordFailure(endpoint);
      }
      return Promise.reject(error);
    }
  );
}