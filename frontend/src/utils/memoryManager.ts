/**
 * Memory Management Utility
 * Monitors and manages memory usage to prevent leaks
 */

export interface MemoryMetrics {
  heapUsed: number;
  heapTotal: number;
  external: number;
  timestamp: number;
  leakWarning?: boolean;
}

class MemoryManager {
  private static instance: MemoryManager;
  private memoryHistory: MemoryMetrics[] = [];
  private maxHistorySize = 100; // Keep only last 100 measurements
  private monitorInterval: NodeJS.Timeout | null = null;
  private leakThreshold = 100 * 1024 * 1024; // 100MB increase is suspicious
  private baselineMemory: number | null = null;

  private constructor() {
    // Singleton pattern
  }

  static getInstance(): MemoryManager {
    if (!MemoryManager.instance) {
      MemoryManager.instance = new MemoryManager();
    }
    return MemoryManager.instance;
  }

  /**
   * Start monitoring memory usage
   */
  startMonitoring(intervalMs: number = 30000): void {
    if (this.monitorInterval) {
      console.warn('[MemoryManager] Already monitoring');
      return;
    }

    // console.log('[MemoryManager] Starting memory monitoring');
    
    // Take initial baseline
    const initial = this.getCurrentMemory();
    if (initial) {
      this.baselineMemory = initial.heapUsed;
    }

    this.monitorInterval = window.setInterval(() => {
      this.checkMemory();
    }, intervalMs);
  }

  /**
   * Stop monitoring memory usage
   */
  stopMonitoring(): void {
    if (this.monitorInterval) {
      window.clearInterval(this.monitorInterval);
      this.monitorInterval = null;
      // console.log('[MemoryManager] Stopped memory monitoring');
    }
  }

  /**
   * Get current memory usage
   */
  private getCurrentMemory(): MemoryMetrics | null {
    if (typeof performance !== 'undefined' && 'memory' in performance) {
      const memory = (performance as any).memory;
      return {
        heapUsed: memory.usedJSHeapSize,
        heapTotal: memory.totalJSHeapSize,
        external: memory.jsHeapSizeLimit,
        timestamp: Date.now(),
      };
    }
    return null;
  }

  /**
   * Check memory and detect potential leaks
   */
  private checkMemory(): void {
    const metrics = this.getCurrentMemory();
    if (!metrics) return;

    // Check for potential leak
    if (this.baselineMemory !== null) {
      const increase = metrics.heapUsed - this.baselineMemory;
      if (increase > this.leakThreshold) {
        metrics.leakWarning = true;
        console.warn('[MemoryManager] Potential memory leak detected!', {
          baseline: this.formatBytes(this.baselineMemory),
          current: this.formatBytes(metrics.heapUsed),
          increase: this.formatBytes(increase),
        });
        
        // Log to monitoring service if available
        this.reportLeak(metrics);
      }
    }

    // Add to history
    this.memoryHistory.push(metrics);

    // Trim history to prevent unbounded growth
    if (this.memoryHistory.length > this.maxHistorySize) {
      this.memoryHistory = this.memoryHistory.slice(-this.maxHistorySize);
    }

    // Log periodic status
    if (this.memoryHistory.length % 10 === 0) {
      // console.log('[MemoryManager] Memory status:', {
        current: this.formatBytes(metrics.heapUsed),
        total: this.formatBytes(metrics.heapTotal),
        limit: this.formatBytes(metrics.external),
      });
    }
  }

  /**
   * Format bytes to human readable format
   */
  private formatBytes(bytes: number): string {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }

  /**
   * Report memory leak to monitoring service
   */
  private reportLeak(metrics: MemoryMetrics): void {
    // Send to monitoring service
    if (window.gtag) {
      window.gtag('event', 'memory_leak', {
        event_category: 'Performance',
        event_label: 'Memory Leak Detected',
        value: Math.round(metrics.heapUsed / 1024 / 1024), // MB
      });
    }

    // Could also send to backend monitoring
    try {
      fetch('/api/v1/monitoring/memory-leak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...metrics,
          userAgent: navigator.userAgent,
          url: window.location.href,
        }),
      }).catch(err => console.error('[MemoryManager] Failed to report leak:', err));
    } catch (error) {
      console.error('[MemoryManager] Failed to report leak:', error);
    }
  }

  /**
   * Get memory history
   */
  getHistory(): MemoryMetrics[] {
    return [...this.memoryHistory];
  }

  /**
   * Get current memory status
   */
  getStatus(): { current: MemoryMetrics | null; trend: 'stable' | 'increasing' | 'decreasing' } {
    const current = this.getCurrentMemory();
    
    let trend: 'stable' | 'increasing' | 'decreasing' = 'stable';
    if (this.memoryHistory.length > 10) {
      const recent = this.memoryHistory.slice(-10);
      const oldAvg = recent.slice(0, 5).reduce((sum, m) => sum + m.heapUsed, 0) / 5;
      const newAvg = recent.slice(5).reduce((sum, m) => sum + m.heapUsed, 0) / 5;
      
      const change = (newAvg - oldAvg) / oldAvg;
      if (change > 0.1) trend = 'increasing';
      else if (change < -0.1) trend = 'decreasing';
    }

    return { current, trend };
  }

  /**
   * Force garbage collection if available (requires --expose-gc flag)
   */
  forceGC(): void {
    if (typeof (global as any).gc === 'function') {
      // console.log('[MemoryManager] Forcing garbage collection');
      (global as any).gc();
    } else {
      // console.log('[MemoryManager] Garbage collection not available');
    }
  }

  /**
   * Clear all cached data to free memory
   */
  clearCaches(): void {
    // Clear any application-level caches
    if ('caches' in window) {
      caches.keys().then(names => {
        names.forEach(name => {
          caches.delete(name);
        });
      });
    }

    // Clear sessionStorage
    try {
      sessionStorage.clear();
    } catch (e) {
      console.error('[MemoryManager] Failed to clear sessionStorage:', e);
    }

    // console.log('[MemoryManager] Caches cleared');
  }
}

// Export singleton instance
export const memoryManager = MemoryManager.getInstance();

// Auto-start monitoring in development
if (process.env.NODE_ENV === 'development') {
  // Start monitoring after app loads
  setTimeout(() => {
    memoryManager.startMonitoring(60000); // Check every minute in dev
  }, 5000);
}

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    memoryManager.stopMonitoring();
  });
}