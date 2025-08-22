/**
 * Memory Leak Detection Utility
 * Monitors memory usage and detects potential leaks
 */

interface MemorySnapshot {
  timestamp: number;
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  activeDOMNodes?: number;
  activeListeners?: number;
}

class MemoryLeakDetector {
  private snapshots: MemorySnapshot[] = [];
  private maxSnapshots = 100;
  private warningThreshold = 50; // MB
  private criticalThreshold = 100; // MB
  private baselineMemory: number | null = null;
  private isMonitoring = false;
  private intervalId: number | null = null;

  /**
   * Start monitoring memory usage
   */
  startMonitoring(intervalMs = 5000): void {
    if (this.isMonitoring) {
      console.warn('[MemoryLeakDetector] Already monitoring');
      return;
    }

    if (!performance.memory) {
      console.warn('[MemoryLeakDetector] Performance.memory API not available');
      return;
    }

    console.log('[MemoryLeakDetector] Starting memory monitoring...');
    this.isMonitoring = true;
    this.takeSnapshot(); // Initial snapshot

    this.intervalId = window.setInterval(() => {
      this.takeSnapshot();
      this.analyzeMemoryTrend();
    }, intervalMs);
  }

  /**
   * Stop monitoring memory usage
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) return;

    console.log('[MemoryLeakDetector] Stopping memory monitoring');
    this.isMonitoring = false;

    if (this.intervalId) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.generateReport();
  }

  /**
   * Take a memory snapshot
   */
  private takeSnapshot(): void {
    if (!performance.memory) return;

    const snapshot: MemorySnapshot = {
      timestamp: Date.now(),
      usedJSHeapSize: performance.memory.usedJSHeapSize,
      totalJSHeapSize: performance.memory.totalJSHeapSize,
      jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
      activeDOMNodes: document.querySelectorAll('*').length,
      activeListeners: this.countEventListeners(),
    };

    this.snapshots.push(snapshot);

    // Keep only recent snapshots
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots.shift();
    }

    // Set baseline if not set
    if (!this.baselineMemory && this.snapshots.length === 1) {
      this.baselineMemory = snapshot.usedJSHeapSize;
      console.log(`[MemoryLeakDetector] Baseline memory: ${this.formatBytes(this.baselineMemory)}`);
    }
  }

  /**
   * Analyze memory trend for potential leaks
   */
  private analyzeMemoryTrend(): void {
    if (this.snapshots.length < 5) return;

    const recent = this.snapshots.slice(-5);
    const current = recent[recent.length - 1];
    const previous = recent[0];

    const memoryIncrease = current.usedJSHeapSize - previous.usedJSHeapSize;
    const memoryIncreaseMB = memoryIncrease / (1024 * 1024);

    // Check for sustained memory growth
    const isGrowing = recent.every((snapshot, index) => {
      if (index === 0) return true;
      return snapshot.usedJSHeapSize > recent[index - 1].usedJSHeapSize;
    });

    if (isGrowing && memoryIncreaseMB > this.warningThreshold) {
      console.warn('[MemoryLeakDetector] ⚠️ Potential memory leak detected!');
      console.warn(`Memory increased by ${memoryIncreaseMB.toFixed(2)}MB in the last ${recent.length} snapshots`);
      this.logCurrentState(current);
    }

    if (this.baselineMemory) {
      const totalIncrease = current.usedJSHeapSize - this.baselineMemory;
      const totalIncreaseMB = totalIncrease / (1024 * 1024);

      if (totalIncreaseMB > this.criticalThreshold) {
        console.error('[MemoryLeakDetector] 🚨 CRITICAL: Memory usage exceeds threshold!');
        console.error(`Total increase: ${totalIncreaseMB.toFixed(2)}MB since baseline`);
        this.logCurrentState(current);
      }
    }
  }

  /**
   * Count active event listeners (approximation)
   */
  private countEventListeners(): number {
    // This is an approximation as there's no direct API
    let count = 0;
    const allElements = document.querySelectorAll('*');
    
    // Common event types to check
    const eventTypes = ['click', 'change', 'input', 'submit', 'keydown', 'keyup', 'mouseenter', 'mouseleave'];
    
    allElements.forEach(element => {
      eventTypes.forEach(eventType => {
        // Check if element has listener (this is a heuristic)
        if (element.onclick || element.onchange || element.oninput) {
          count++;
        }
      });
    });

    return count;
  }

  /**
   * Log current memory state
   */
  private logCurrentState(snapshot: MemorySnapshot): void {
    console.group('[MemoryLeakDetector] Current State');
    console.log(`Heap Used: ${this.formatBytes(snapshot.usedJSHeapSize)}`);
    console.log(`Heap Total: ${this.formatBytes(snapshot.totalJSHeapSize)}`);
    console.log(`Heap Limit: ${this.formatBytes(snapshot.jsHeapSizeLimit)}`);
    console.log(`DOM Nodes: ${snapshot.activeDOMNodes}`);
    console.log(`Event Listeners (approx): ${snapshot.activeListeners}`);
    console.log(`Time: ${new Date(snapshot.timestamp).toLocaleTimeString()}`);
    console.groupEnd();
  }

  /**
   * Generate final report
   */
  private generateReport(): void {
    if (this.snapshots.length === 0) return;

    const first = this.snapshots[0];
    const last = this.snapshots[this.snapshots.length - 1];
    const duration = (last.timestamp - first.timestamp) / 1000;
    const memoryChange = last.usedJSHeapSize - first.usedJSHeapSize;
    const avgGrowthRate = memoryChange / duration; // bytes per second

    console.group('[MemoryLeakDetector] Final Report');
    console.log(`Monitoring Duration: ${duration.toFixed(1)}s`);
    console.log(`Starting Memory: ${this.formatBytes(first.usedJSHeapSize)}`);
    console.log(`Ending Memory: ${this.formatBytes(last.usedJSHeapSize)}`);
    console.log(`Total Change: ${this.formatBytes(memoryChange)} (${memoryChange > 0 ? '+' : ''}${(memoryChange / (1024 * 1024)).toFixed(2)}MB)`);
    console.log(`Average Growth Rate: ${this.formatBytes(avgGrowthRate)}/s`);
    console.log(`DOM Nodes Change: ${(last.activeDOMNodes || 0) - (first.activeDOMNodes || 0)}`);
    
    // Analyze for leak patterns
    if (avgGrowthRate > 1024 * 1024) { // > 1MB/s
      console.error('❌ HIGH LEAK RISK: Memory growing rapidly');
    } else if (avgGrowthRate > 100 * 1024) { // > 100KB/s
      console.warn('⚠️ MODERATE LEAK RISK: Memory growing steadily');
    } else if (avgGrowthRate > 10 * 1024) { // > 10KB/s
      console.log('ℹ️ LOW LEAK RISK: Minor memory growth detected');
    } else {
      console.log('✅ NO LEAK DETECTED: Memory usage stable');
    }
    
    console.groupEnd();
  }

  /**
   * Format bytes to human readable string
   */
  private formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)}MB`;
  }

  /**
   * Get current memory stats
   */
  getCurrentStats(): MemorySnapshot | null {
    if (this.snapshots.length === 0) return null;
    return this.snapshots[this.snapshots.length - 1];
  }

  /**
   * Clear all snapshots
   */
  reset(): void {
    this.snapshots = [];
    this.baselineMemory = null;
    console.log('[MemoryLeakDetector] Reset complete');
  }
}

// Export singleton instance
export const memoryLeakDetector = new MemoryLeakDetector();

// Auto-start in development mode
if (process.env.NODE_ENV === 'development' && typeof window !== 'undefined') {
  // Add to window for debugging
  (window as any).memoryLeakDetector = memoryLeakDetector;
  
  console.log('[MemoryLeakDetector] Available in console as window.memoryLeakDetector');
  console.log('Commands: startMonitoring(), stopMonitoring(), getCurrentStats(), reset()');
}

export default memoryLeakDetector;