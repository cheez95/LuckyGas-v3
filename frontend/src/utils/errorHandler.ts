import { notification } from 'antd';
import { AxiosError } from 'axios';

// Error types for categorization
export enum ErrorType {
  NETWORK = 'NETWORK',
  AUTHENTICATION = 'AUTHENTICATION',
  PERMISSION = 'PERMISSION',
  VALIDATION = 'VALIDATION',
  SERVER = 'SERVER',
  UNKNOWN = 'UNKNOWN'
}

// Error severity levels
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface AppError {
  id: string;
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  detail?: string;
  timestamp: Date;
  context?: Record<string, any>;
  retryable?: boolean;
}

// Error messages in Traditional Chinese
const ERROR_MESSAGES: Record<string, string> = {
  // Network errors
  'network.offline': '無法連接到網路，請檢查您的網路連線',
  'network.timeout': '請求超時，請稍後再試',
  'network.general': '網路連線錯誤，請稍後再試',
  
  // Authentication errors
  'auth.invalid_credentials': '帳號或密碼錯誤',
  'auth.token_expired': '登入已過期，請重新登入',
  'auth.unauthorized': '您沒有權限執行此操作',
  
  // Validation errors
  'validation.required_field': '請填寫所有必填欄位',
  'validation.invalid_format': '資料格式不正確',
  'validation.duplicate': '此資料已存在',
  
  // Server errors
  'server.internal': '伺服器內部錯誤，請聯繫技術支援',
  'server.maintenance': '系統維護中，請稍後再試',
  'server.unavailable': '服務暫時無法使用',
  
  // Business logic errors
  'business.insufficient_inventory': '庫存不足',
  'business.invalid_operation': '無效的操作',
  
  // Default error
  'unknown': '發生未知錯誤，請稍後再試'
};

// Categorize error based on status code and error response
export function categorizeError(error: AxiosError): ErrorType {
  if (!error.response) {
    return ErrorType.NETWORK;
  }
  
  const status = error.response.status;
  
  if (status === 401) {
    return ErrorType.AUTHENTICATION;
  } else if (status === 403) {
    return ErrorType.PERMISSION;
  } else if (status >= 400 && status < 500) {
    return ErrorType.VALIDATION;
  } else if (status >= 500) {
    return ErrorType.SERVER;
  }
  
  return ErrorType.UNKNOWN;
}

// Determine error severity
export function determineErrorSeverity(type: ErrorType, status?: number): ErrorSeverity {
  switch (type) {
    case ErrorType.NETWORK:
      return ErrorSeverity.HIGH;
    case ErrorType.AUTHENTICATION:
      return ErrorSeverity.MEDIUM;
    case ErrorType.PERMISSION:
      return ErrorSeverity.MEDIUM;
    case ErrorType.VALIDATION:
      return ErrorSeverity.LOW;
    case ErrorType.SERVER:
      return status && status >= 500 ? ErrorSeverity.CRITICAL : ErrorSeverity.HIGH;
    default:
      return ErrorSeverity.MEDIUM;
  }
}

// Check if error is retryable
export function isRetryableError(error: AxiosError): boolean {
  if (!error.response) {
    // Network errors are usually retryable
    return true;
  }
  
  const status = error.response.status;
  
  // Retry on server errors and network timeouts
  return status >= 500 || status === 408 || status === 429;
}

// Get user-friendly error message
export function getUserFriendlyMessage(error: AxiosError): string {
  // Check for custom error message from server
  const serverMessage = error.response?.data?.message;
  if (serverMessage && typeof serverMessage === 'string') {
    return serverMessage;
  }
  
  // Check for specific error codes
  const errorCode = error.response?.data?.code;
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode];
  }
  
  // Categorize and return appropriate message
  const errorType = categorizeError(error);
  switch (errorType) {
    case ErrorType.NETWORK:
      if (!navigator.onLine) {
        return ERROR_MESSAGES['network.offline'];
      }
      return error.code === 'ECONNABORTED' 
        ? ERROR_MESSAGES['network.timeout']
        : ERROR_MESSAGES['network.general'];
        
    case ErrorType.AUTHENTICATION:
      return error.response?.status === 401
        ? ERROR_MESSAGES['auth.token_expired']
        : ERROR_MESSAGES['auth.invalid_credentials'];
        
    case ErrorType.PERMISSION:
      return ERROR_MESSAGES['auth.unauthorized'];
      
    case ErrorType.VALIDATION:
      return ERROR_MESSAGES['validation.invalid_format'];
      
    case ErrorType.SERVER:
      return ERROR_MESSAGES['server.internal'];
      
    default:
      return ERROR_MESSAGES['unknown'];
  }
}

// Show error notification
export function showErrorNotification(error: AxiosError, customMessage?: string) {
  const message = customMessage || getUserFriendlyMessage(error);
  const errorType = categorizeError(error);
  const severity = determineErrorSeverity(errorType, error.response?.status);
  
  const notificationConfig = {
    message: '錯誤',
    description: message,
    duration: severity === ErrorSeverity.CRITICAL ? 0 : 4.5,
  };
  
  switch (severity) {
    case ErrorSeverity.CRITICAL:
    case ErrorSeverity.HIGH:
      notification.error(notificationConfig);
      break;
    case ErrorSeverity.MEDIUM:
      notification.warning(notificationConfig);
      break;
    case ErrorSeverity.LOW:
      notification.info(notificationConfig);
      break;
  }
}

// Log error for monitoring
export function logError(error: Error | AxiosError, context?: Record<string, any>) {
  const errorId = `ERR-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  const errorLog = {
    id: errorId,
    timestamp: new Date().toISOString(),
    message: error.message,
    stack: error.stack,
    context,
    url: window.location.href,
    userAgent: navigator.userAgent,
  };
  
  // Log to console in development
  if (import.meta.env.DEV) {
    console.error('Error logged:', errorLog);
  }
  
  // Send to error reporting service if available
  if (window.errorReporting?.logError) {
    window.errorReporting.logError(error, errorLog);
  }
  
  return errorId;
}

// Handle uncaught promise rejections
export function setupGlobalErrorHandlers() {
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    
    const error = new Error(
      event.reason?.message || 'Unhandled Promise Rejection'
    );
    error.stack = event.reason?.stack;
    
    logError(error, {
      type: 'unhandledRejection',
      promise: event.promise,
    });
    
    // Prevent default browser behavior
    event.preventDefault();
  });
  
  // Handle global errors
  window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    
    logError(event.error || new Error(event.message), {
      type: 'globalError',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  });
}