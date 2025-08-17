import { ErrorInfo } from 'react';
import { AxiosError } from 'axios';

// Error monitoring service interface
interface ErrorMonitoringService {
  logError: (error: Error | AxiosError, context?: any) => void;
  logWarning: (message: string, context?: any) => void;
  logInfo: (message: string, context?: any) => void;
  setUserContext: (userId: string, userInfo?: any) => void;
  clearUserContext: () => void;
}

// Error log entry structure
interface ErrorLogEntry {
  id: string;
  timestamp: string;
  level: 'error' | 'warning' | 'info';
  message: string;
  stack?: string;
  context?: any;
  userAgent: string;
  url: string;
  userId?: string;
  sessionId?: string;
}

// Local storage for error logs (for offline capability)
class ErrorLogStorage {
  private readonly storageKey = 'luckygas_error_logs';
  private readonly maxLogs = 100;
  
  save(entry: ErrorLogEntry): void {
    try {
      const logs = this.getAll();
      logs.push(entry);
      
      // Keep only the latest logs
      if (logs.length > this.maxLogs) {
        logs.splice(0, logs.length - this.maxLogs);
      }
      
      localStorage.setItem(this.storageKey, JSON.stringify(logs));
    } catch (error) {
      console.error('Failed to save error log to storage:', error);
    }
  }
  
  getAll(): ErrorLogEntry[] {
    try {
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to read error logs from storage:', error);
      return [];
    }
  }
  
  clear(): void {
    try {
      localStorage.removeItem(this.storageKey);
    } catch (error) {
      console.error('Failed to clear error logs:', error);
    }
  }
  
  getPending(): ErrorLogEntry[] {
    return this.getAll().filter(log => !log.synced);
  }
}

// Main error monitoring service
class ErrorMonitoring implements ErrorMonitoringService {
  private userId?: string;
  private userInfo?: any;
  private sessionId: string;
  private logStorage: ErrorLogStorage;
  private syncInterval?: NodeJS.Timeout;
  private apiEndpoint = '/api/v1/monitoring/errors';
  
  constructor() {
    this.sessionId = this.generateSessionId();
    this.logStorage = new ErrorLogStorage();
    
    // DISABLED - Error monitoring causing infinite loop
    console.warn('[ERROR MONITORING] Service initialization DISABLED');
    // this.startSyncInterval();
    
    // Make service available globally
    if (typeof window !== 'undefined') {
      (window as any).errorReporting = this;
    }
  }
  
  private generateSessionId(): string {
    return `SESSION-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  private generateLogId(): string {
    return `LOG-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  private createLogEntry(
    level: 'error' | 'warning' | 'info',
    message: string,
    error?: Error | AxiosError,
    context?: any
  ): ErrorLogEntry {
    return {
      id: this.generateLogId(),
      timestamp: new Date().toISOString(),
      level,
      message,
      stack: error?.stack,
      context: {
        ...context,
        errorName: error?.name,
        errorMessage: error?.message,
        axiosConfig: (error as AxiosError)?.config,
        axiosResponse: (error as AxiosError)?.response?.data,
        axiosStatus: (error as AxiosError)?.response?.status,
      },
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: this.userId,
      sessionId: this.sessionId,
    };
  }
  
  logError(error: Error | AxiosError, context?: any): void {
    // DISABLED - Preventing infinite loop
    if (import.meta.env.DEV) {
      console.error('[Error Monitor DISABLED]', error.message, error);
    }
    return;
    
    // const entry = this.createLogEntry('error', error.message, error, context);
    
    // // Log to console in development
    // if (import.meta.env.DEV) {
    //   console.error('[Error Monitor]', entry);
    // }
    
    // // Save to local storage
    // this.logStorage.save(entry);
    
    // // Try to send immediately
    // this.sendLog(entry).catch(() => {
    //   // Will be retried by sync interval
    // });
  }
  
  logWarning(message: string, context?: any): void {
    const entry = this.createLogEntry('warning', message, undefined, context);
    
    if (import.meta.env.DEV) {
      console.warn('[Error Monitor]', entry);
    }
    
    this.logStorage.save(entry);
    this.sendLog(entry).catch(() => {});
  }
  
  logInfo(message: string, context?: any): void {
    const entry = this.createLogEntry('info', message, undefined, context);
    
    if (import.meta.env.DEV) {
      console.info('[Error Monitor]', entry);
    }
    
    // Info logs are less critical, only save if important
    if (context?.important) {
      this.logStorage.save(entry);
      this.sendLog(entry).catch(() => {});
    }
  }
  
  setUserContext(userId: string, userInfo?: any): void {
    this.userId = userId;
    this.userInfo = userInfo;
    
    // Log user context change
    this.logInfo('User context updated', { userId, userInfo });
  }
  
  clearUserContext(): void {
    this.userId = undefined;
    this.userInfo = undefined;
    
    this.logInfo('User context cleared');
  }
  
  private async sendLog(entry: ErrorLogEntry): Promise<void> {
    // COMPLETELY DISABLED - DO NOT SEND ANY LOGS
    return Promise.resolve();
    
    // // Skip sending in development unless explicitly enabled
    // if (import.meta.env.DEV && !import.meta.env.VITE_ENABLE_ERROR_REPORTING) {
    //   return;
    // }
    
    // try {
    //   const response = await fetch(this.apiEndpoint, {
    //     method: 'POST',
    //     headers: {
    //       'Content-Type': 'application/json',
    //       'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    //     },
    //     body: JSON.stringify(entry),
    //   });
      
    //   if (!response.ok) {
    //     throw new Error(`Failed to send log: ${response.status}`);
    //   }
      
    //   // Mark as synced
    //   (entry as any).synced = true;
    // } catch (error) {
    //   console.error('Failed to send error log:', error);
    //   throw error;
    // }
  }
  
  private async syncPendingLogs(): Promise<void> {
    try {
      const pending = this.logStorage.getPending();
      
      if (pending.length === 0) {
        return;
      }
      
      if (import.meta.env.DEV) {
        console.log(`[Error Monitor] Syncing ${pending.length} pending logs`);
      }
      
      // Batch send logs with timeout
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      try {
        const response = await fetch(`${this.apiEndpoint}/batch`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify({ logs: pending }),
          signal: controller.signal,
        });
        
        clearTimeout(timeout);
        
        if (response.ok) {
          // Clear synced logs
          const remaining = this.logStorage.getAll().filter(log => !(log as any).synced);
          localStorage.setItem('luckygas_error_logs', JSON.stringify(remaining));
        }
      } catch (error: any) {
        clearTimeout(timeout);
        if (error.name !== 'AbortError') {
          console.error('Failed to sync error logs:', error);
        }
      }
    } catch (error) {
      // Silently fail - will retry on next interval
      if (import.meta.env.DEV) {
        console.error('Failed to sync error logs:', error);
      }
    }
  }
  
  private startSyncInterval(): void {
    // DISABLED - CAUSING INFINITE LOOP AND MEMORY LEAK
    // DO NOT RE-ENABLE UNTIL FIXED
    console.warn('[ERROR MONITORING] Sync interval DISABLED due to infinite loop bug');
    return;
    
    // // Sync pending logs every 30 seconds
    // this.syncInterval = window.setInterval(() => {
    //   this.syncPendingLogs();
    // }, 30000);
    
    // // Also sync on page visibility change
    // document.addEventListener('visibilitychange', () => {
    //   if (!document.hidden) {
    //     this.syncPendingLogs();
    //   }
    // });
    
    // // Sync before page unload
    // window.addEventListener('beforeunload', () => {
    //   this.syncPendingLogs();
    // });
  }
  
  public stopSync(): void {
    if (this.syncInterval) {
      window.clearInterval(this.syncInterval);
    }
  }
  
  // Get logs for debugging
  public getLogs(): ErrorLogEntry[] {
    return this.logStorage.getAll();
  }
  
  // Clear all logs
  public clearLogs(): void {
    this.logStorage.clear();
  }
  
  // Export logs for analysis
  public exportLogs(): string {
    const logs = this.getLogs();
    return JSON.stringify(logs, null, 2);
  }
  
  // Download logs as file
  public downloadLogs(): void {
    const logs = this.exportLogs();
    const blob = new Blob([logs], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `error-logs-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// Create singleton instance
export const errorMonitoring = new ErrorMonitoring();

// Integration with React ErrorBoundary
export function logReactError(error: Error, errorInfo: ErrorInfo): void {
  errorMonitoring.logError(error, {
    type: 'React ErrorBoundary',
    componentStack: errorInfo.componentStack,
  });
}

// Integration with unhandled promise rejections
export function setupUnhandledRejectionHandler(): void {
  window.addEventListener('unhandledrejection', (event) => {
    // Prevent default browser error logging
    event.preventDefault();
    
    // Create proper error object
    const error = event.reason instanceof Error 
      ? event.reason 
      : new Error(event.reason?.message || event.reason?.toString() || 'Unhandled Promise Rejection');
    
    errorMonitoring.logError(error, {
      type: 'Unhandled Promise Rejection',
      reason: event.reason,
      promise: event.promise,
      stack: error.stack || new Error().stack,
    });
    
    // Log to console in development for debugging
    if (import.meta.env.DEV) {
      console.error('Unhandled Promise Rejection:', event.reason);
    }
  });
}

// Integration with global errors
export function setupGlobalErrorHandler(): void {
  window.addEventListener('error', (event) => {
    errorMonitoring.logError(
      event.error || new Error(event.message),
      {
        type: 'Global Error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      }
    );
  });
}

// Setup all handlers
export function setupErrorMonitoring(): void {
  // DISABLED - Error monitoring causing infinite loop
  console.warn('[ERROR MONITORING] Setup DISABLED - infinite loop bug');
  return;
  
  // setupUnhandledRejectionHandler();
  // setupGlobalErrorHandler();
}

// Export for use in other modules
export default errorMonitoring;