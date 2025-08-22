/**
 * Safe Error Monitoring Service with Circuit Breaker Pattern
 * Prevents infinite loops and cascading failures
 */

interface ErrorEntry {
  error: Error;
  context?: any;
  timestamp: number;
  retryCount: number;
}

interface CircuitBreakerConfig {
  maxFailures: number;
  resetTimeout: number;
  maxRetries: number;
  backoffMultiplier: number;
}

class SafeErrorMonitor {
  private static instance: SafeErrorMonitor | null = null;
  
  // Circuit breaker state
  private circuitOpen = false;
  private failureCount = 0;
  private circuitResetTimer: number | null = null;
  
  // Error queue management
  private errorQueue: ErrorEntry[] = [];
  private lastBatchSendTime = 0;
  private batchTimer: number | null = null;
  
  // Configuration
  private readonly config: CircuitBreakerConfig = {
    maxFailures: 3,
    resetTimeout: 60000, // 1 minute
    maxRetries: 3,
    backoffMultiplier: 2,
  };
  
  private readonly BATCH_INTERVAL = 30000; // 30 seconds
  private readonly MAX_QUEUE_SIZE = 50;
  private readonly ERROR_TTL = 300000; // 5 minutes
  private readonly MONITORING_ENDPOINTS = [
    '/monitoring/',
    '/api/v1/monitoring/',
    '/analytics/',
    '/api/v1/analytics/',
  ];
  
  // Kill switch
  private readonly KILL_SWITCH_KEY = 'error-monitoring-disabled';
  
  private constructor() {
    this.initializeKillSwitch();
    this.startQueueCleaner();
  }
  
  static getInstance(): SafeErrorMonitor {
    if (!SafeErrorMonitor.instance) {
      SafeErrorMonitor.instance = new SafeErrorMonitor();
    }
    return SafeErrorMonitor.instance;
  }
  
  /**
   * Initialize kill switch from localStorage
   */
  private initializeKillSwitch(): void {
    // Check for kill switch on initialization
    const isDisabled = localStorage.getItem(this.KILL_SWITCH_KEY) === 'true';
    if (isDisabled) {
      console.warn('[SafeErrorMonitor] Monitoring disabled via kill switch');
      this.circuitOpen = true;
    }
  }
  
  /**
   * Enable/disable monitoring via localStorage
   */
  public setKillSwitch(disabled: boolean): void {
    if (disabled) {
      localStorage.setItem(this.KILL_SWITCH_KEY, 'true');
      this.circuitOpen = true;
      this.clearQueue();
      console.warn('[SafeErrorMonitor] Monitoring disabled via kill switch');
    } else {
      localStorage.removeItem(this.KILL_SWITCH_KEY);
      this.circuitOpen = false;
      this.failureCount = 0;
      console.info('[SafeErrorMonitor] Monitoring enabled');
    }
  }
  
  /**
   * Log an error with safeguards
   */
  public logError(error: Error, context?: any): void {
    // Skip if kill switch is active
    if (localStorage.getItem(this.KILL_SWITCH_KEY) === 'true') {
      console.error('[SafeErrorMonitor] Skipped (kill switch)', error);
      return;
    }
    
    // Skip monitoring endpoint errors to prevent recursion
    if (this.isMonitoringError(error)) {
      console.warn('[SafeErrorMonitor] Skipped monitoring endpoint error', error);
      return;
    }
    
    // Skip if circuit is open
    if (this.circuitOpen) {
      console.warn('[SafeErrorMonitor] Circuit breaker open, error logged locally only', error);
      return;
    }
    
    // Check queue size limit
    if (this.errorQueue.length >= this.MAX_QUEUE_SIZE) {
      console.warn('[SafeErrorMonitor] Queue full, dropping oldest errors');
      this.errorQueue = this.errorQueue.slice(-Math.floor(this.MAX_QUEUE_SIZE / 2));
    }
    
    // Add to queue
    const entry: ErrorEntry = {
      error,
      context,
      timestamp: Date.now(),
      retryCount: 0,
    };
    
    this.errorQueue.push(entry);
    
    // Schedule batch send if not already scheduled
    this.scheduleBatchSend();
  }
  
  /**
   * Check if error is from monitoring endpoints
   */
  private isMonitoringError(error: Error): boolean {
    const errorString = error.stack || error.message || '';
    return this.MONITORING_ENDPOINTS.some(endpoint => 
      errorString.includes(endpoint)
    );
  }
  
  /**
   * Schedule batch send with throttling
   */
  private scheduleBatchSend(): void {
    // Clear existing timer
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
    }
    
    const timeSinceLastSend = Date.now() - this.lastBatchSendTime;
    const delay = Math.max(0, this.BATCH_INTERVAL - timeSinceLastSend);
    
    this.batchTimer = window.setTimeout(() => {
      this.sendBatch();
    }, delay);
  }
  
  /**
   * Send error batch with circuit breaker protection
   */
  private async sendBatch(): Promise<void> {
    if (this.circuitOpen || this.errorQueue.length === 0) {
      return;
    }
    
    // Get errors to send (with retry limit check)
    const errorsToSend = this.errorQueue.filter(e => e.retryCount < this.config.maxRetries);
    
    if (errorsToSend.length === 0) {
      this.errorQueue = []; // Clear queue of max-retry errors
      return;
    }
    
    try {
      // Prepare batch payload
      const payload = {
        errors: errorsToSend.map(e => ({
          message: e.error.message,
          stack: e.error.stack,
          context: e.context,
          timestamp: e.timestamp,
        })),
        userAgent: navigator.userAgent,
        url: window.location.href,
        timestamp: Date.now(),
      };
      
      // Send with timeout
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch('/api/v1/monitoring/errors/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      
      clearTimeout(timeout);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      // Success - reset circuit breaker and clear sent errors
      this.failureCount = 0;
      this.errorQueue = this.errorQueue.filter(e => !errorsToSend.includes(e));
      this.lastBatchSendTime = Date.now();
      
      console.info(`[SafeErrorMonitor] Batch sent successfully (${errorsToSend.length} errors)`);
      
    } catch (error) {
      // Failure - increment failure count
      this.failureCount++;
      
      // Increment retry count for errors
      errorsToSend.forEach(e => e.retryCount++);
      
      console.warn(`[SafeErrorMonitor] Batch send failed (attempt ${this.failureCount}/${this.config.maxFailures})`);
      
      // Check if circuit should open
      if (this.failureCount >= this.config.maxFailures) {
        this.openCircuit();
      } else {
        // Retry with exponential backoff
        const backoffDelay = Math.min(
          1000 * Math.pow(this.config.backoffMultiplier, this.failureCount),
          30000
        );
        
        setTimeout(() => {
          this.sendBatch();
        }, backoffDelay);
      }
    }
  }
  
  /**
   * Open circuit breaker
   */
  private openCircuit(): void {
    this.circuitOpen = true;
    console.error('[SafeErrorMonitor] Circuit breaker OPEN - monitoring disabled temporarily');
    
    // Schedule circuit reset
    if (this.circuitResetTimer) {
      clearTimeout(this.circuitResetTimer);
    }
    
    this.circuitResetTimer = window.setTimeout(() => {
      this.resetCircuit();
    }, this.config.resetTimeout);
  }
  
  /**
   * Reset circuit breaker for retry
   */
  private resetCircuit(): void {
    // Don't reset if kill switch is active
    if (localStorage.getItem(this.KILL_SWITCH_KEY) === 'true') {
      return;
    }
    
    this.circuitOpen = false;
    this.failureCount = 0;
    console.info('[SafeErrorMonitor] Circuit breaker RESET - monitoring re-enabled');
    
    // Try sending queued errors
    if (this.errorQueue.length > 0) {
      this.scheduleBatchSend();
    }
  }
  
  /**
   * Clean old errors from queue
   */
  private startQueueCleaner(): void {
    setInterval(() => {
      const now = Date.now();
      this.errorQueue = this.errorQueue.filter(e => 
        (now - e.timestamp) < this.ERROR_TTL
      );
    }, 60000); // Clean every minute
  }
  
  /**
   * Clear error queue
   */
  public clearQueue(): void {
    this.errorQueue = [];
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }
  }
  
  /**
   * Get monitoring status
   */
  public getStatus(): {
    circuitOpen: boolean;
    failureCount: number;
    queueSize: number;
    killSwitchActive: boolean;
  } {
    return {
      circuitOpen: this.circuitOpen,
      failureCount: this.failureCount,
      queueSize: this.errorQueue.length,
      killSwitchActive: localStorage.getItem(this.KILL_SWITCH_KEY) === 'true',
    };
  }
  
  /**
   * Cleanup on destroy
   */
  public destroy(): void {
    this.clearQueue();
    if (this.circuitResetTimer) {
      clearTimeout(this.circuitResetTimer);
    }
  }
}

// Export singleton instance
export const safeErrorMonitor = SafeErrorMonitor.getInstance();

// Global error handler with safeguards
export function setupSafeErrorMonitoring(): void {
  // Only setup if not disabled
  if (localStorage.getItem('error-monitoring-disabled') === 'true') {
    console.warn('[SafeErrorMonitor] Setup skipped due to kill switch');
    return;
  }
  
  // Window error handler
  window.addEventListener('error', (event) => {
    safeErrorMonitor.logError(new Error(event.message), {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  });
  
  // Promise rejection handler
  window.addEventListener('unhandledrejection', (event) => {
    safeErrorMonitor.logError(new Error(event.reason), {
      type: 'unhandledRejection',
    });
  });
  
  console.info('[SafeErrorMonitor] Safe error monitoring initialized with circuit breaker');
}

// Helper for React Error Boundaries
export function logReactError(error: Error, errorInfo: any): void {
  safeErrorMonitor.logError(error, {
    componentStack: errorInfo.componentStack,
    type: 'React Error Boundary',
  });
}