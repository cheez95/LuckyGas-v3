/**
 * Performance Testing Service
 * Load testing and performance benchmarking for production readiness
 */

export interface PerformanceTestResult {
  testName: string;
  status: 'pass' | 'fail';
  metrics: {
    avgResponseTime: number;
    minResponseTime: number;
    maxResponseTime: number;
    p95ResponseTime: number;
    p99ResponseTime: number;
    successRate: number;
    errorRate: number;
    throughput: number;
  };
  details: {
    totalRequests: number;
    successfulRequests: number;
    failedRequests: number;
    duration: number;
  };
  timestamp: Date;
}

export interface LoadTestConfig {
  concurrentUsers: number;
  duration: number; // in seconds
  rampUpTime: number; // in seconds
  targetUrl?: string;
}

class PerformanceTestService {
  private static instance: PerformanceTestService;
  private testResults: PerformanceTestResult[] = [];
  
  private constructor() {}
  
  static getInstance(): PerformanceTestService {
    if (!PerformanceTestService.instance) {
      PerformanceTestService.instance = new PerformanceTestService();
    }
    return PerformanceTestService.instance;
  }
  
  /**
   * Simulate concurrent user requests
   */
  async runLoadTest(config: LoadTestConfig): Promise<PerformanceTestResult> {
    const { concurrentUsers, duration, targetUrl } = config;
    const url = targetUrl || `${import.meta.env.VITE_API_URL}/health`;
    
    const results: number[] = [];
    let successCount = 0;
    let errorCount = 0;
    const startTime = Date.now();
    const endTime = startTime + (duration * 1000);
    
    // Create concurrent request promises
    const runRequest = async (): Promise<void> => {
      while (Date.now() < endTime) {
        const requestStart = performance.now();
        
        try {
          const response = await fetch(url, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(5000),
          });
          
          const responseTime = performance.now() - requestStart;
          results.push(responseTime);
          
          if (response.ok) {
            successCount++;
          } else {
            errorCount++;
          }
        } catch (error) {
          errorCount++;
          results.push(5000); // Timeout as max response time
        }
        
        // Small delay between requests to prevent overwhelming
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    };
    
    // Start concurrent users
    const userPromises = [];
    for (let i = 0; i < concurrentUsers; i++) {
      // Stagger user start times for ramp-up
      const delay = (config.rampUpTime * 1000 / concurrentUsers) * i;
      userPromises.push(
        new Promise(resolve => setTimeout(resolve, delay))
          .then(() => runRequest())
      );
    }
    
    // Wait for all users to complete
    await Promise.all(userPromises);
    
    // Calculate metrics
    const actualDuration = (Date.now() - startTime) / 1000;
    const totalRequests = results.length;
    
    const metrics = this.calculateMetrics(results, successCount, errorCount, actualDuration);
    
    const result: PerformanceTestResult = {
      testName: `Load Test - ${concurrentUsers} users`,
      status: metrics.avgResponseTime < 500 && metrics.successRate > 95 ? 'pass' : 'fail',
      metrics,
      details: {
        totalRequests,
        successfulRequests: successCount,
        failedRequests: errorCount,
        duration: actualDuration,
      },
      timestamp: new Date(),
    };
    
    this.testResults.push(result);
    return result;
  }
  
  /**
   * Test WebSocket connections
   */
  async testWebSocketLoad(connectionCount: number): Promise<PerformanceTestResult> {
    const wsUrl = import.meta.env.VITE_WS_URL || 'wss://localhost';
    const connections: WebSocket[] = [];
    const connectionTimes: number[] = [];
    let successCount = 0;
    let errorCount = 0;
    const startTime = Date.now();
    
    // Create WebSocket connections
    const createConnection = (): Promise<void> => {
      return new Promise((resolve) => {
        const connStart = performance.now();
        const timeout = setTimeout(() => {
          errorCount++;
          connectionTimes.push(5000);
          resolve();
        }, 5000);
        
        try {
          const ws = new WebSocket(wsUrl);
          
          ws.onopen = () => {
            const connTime = performance.now() - connStart;
            connectionTimes.push(connTime);
            successCount++;
            connections.push(ws);
            clearTimeout(timeout);
            
            // Keep connection alive for 10 seconds
            setTimeout(() => {
              ws.close();
              resolve();
            }, 10000);
          };
          
          ws.onerror = () => {
            errorCount++;
            connectionTimes.push(5000);
            clearTimeout(timeout);
            resolve();
          };
        } catch (error) {
          errorCount++;
          connectionTimes.push(5000);
          clearTimeout(timeout);
          resolve();
        }
      });
    };
    
    // Create connections with slight delay
    const connectionPromises = [];
    for (let i = 0; i < connectionCount; i++) {
      await new Promise(resolve => setTimeout(resolve, 50)); // 50ms delay between connections
      connectionPromises.push(createConnection());
    }
    
    // Wait for all connections to complete
    await Promise.all(connectionPromises);
    
    const duration = (Date.now() - startTime) / 1000;
    const metrics = this.calculateMetrics(connectionTimes, successCount, errorCount, duration);
    
    const result: PerformanceTestResult = {
      testName: `WebSocket Load Test - ${connectionCount} connections`,
      status: metrics.avgResponseTime < 1000 && metrics.successRate > 90 ? 'pass' : 'fail',
      metrics,
      details: {
        totalRequests: connectionCount,
        successfulRequests: successCount,
        failedRequests: errorCount,
        duration,
      },
      timestamp: new Date(),
    };
    
    // Clean up connections
    connections.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });
    
    this.testResults.push(result);
    return result;
  }
  
  /**
   * Test memory usage under stress
   */
  async testMemoryStress(): Promise<{ initial: number; peak: number; final: number; leaked: boolean }> {
    const getMemoryUsage = () => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize / 1048576; // Convert to MB
      }
      return 0;
    };
    
    const initialMemory = getMemoryUsage();
    let peakMemory = initialMemory;
    
    // Create memory stress
    const largeArrays: any[] = [];
    
    for (let i = 0; i < 10; i++) {
      // Create large objects
      const largeObject = {
        data: new Array(100000).fill(Math.random()),
        nested: {
          more: new Array(50000).fill({ id: i, value: Math.random() }),
        },
      };
      largeArrays.push(largeObject);
      
      const currentMemory = getMemoryUsage();
      if (currentMemory > peakMemory) {
        peakMemory = currentMemory;
      }
      
      // Small delay
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Clear references
    largeArrays.length = 0;
    
    // Force garbage collection if available
    if ('gc' in window) {
      (window as any).gc();
    }
    
    // Wait for cleanup
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const finalMemory = getMemoryUsage();
    const leaked = finalMemory > initialMemory * 1.2; // 20% threshold for leak detection
    
    return {
      initial: initialMemory,
      peak: peakMemory,
      final: finalMemory,
      leaked,
    };
  }
  
  /**
   * Test CPU usage patterns
   */
  async testCPUPerformance(): Promise<{ score: number; status: 'good' | 'average' | 'poor' }> {
    const iterations = 1000000;
    const startTime = performance.now();
    
    // CPU intensive operations
    let result = 0;
    for (let i = 0; i < iterations; i++) {
      result += Math.sqrt(i) * Math.sin(i);
    }
    
    const duration = performance.now() - startTime;
    
    // Score based on time taken (lower is better)
    let score: number;
    let status: 'good' | 'average' | 'poor';
    
    if (duration < 100) {
      score = 100;
      status = 'good';
    } else if (duration < 300) {
      score = 75;
      status = 'average';
    } else {
      score = 50;
      status = 'poor';
    }
    
    return { score, status };
  }
  
  /**
   * Calculate performance metrics from results
   */
  private calculateMetrics(
    responseTimes: number[],
    successCount: number,
    errorCount: number,
    duration: number
  ): PerformanceTestResult['metrics'] {
    if (responseTimes.length === 0) {
      return {
        avgResponseTime: 0,
        minResponseTime: 0,
        maxResponseTime: 0,
        p95ResponseTime: 0,
        p99ResponseTime: 0,
        successRate: 0,
        errorRate: 100,
        throughput: 0,
      };
    }
    
    // Sort response times for percentile calculation
    const sorted = [...responseTimes].sort((a, b) => a - b);
    
    const avgResponseTime = responseTimes.reduce((sum, t) => sum + t, 0) / responseTimes.length;
    const minResponseTime = sorted[0];
    const maxResponseTime = sorted[sorted.length - 1];
    const p95ResponseTime = sorted[Math.floor(sorted.length * 0.95)];
    const p99ResponseTime = sorted[Math.floor(sorted.length * 0.99)];
    
    const totalRequests = successCount + errorCount;
    const successRate = (successCount / totalRequests) * 100;
    const errorRate = (errorCount / totalRequests) * 100;
    const throughput = totalRequests / duration; // requests per second
    
    return {
      avgResponseTime,
      minResponseTime,
      maxResponseTime,
      p95ResponseTime,
      p99ResponseTime,
      successRate,
      errorRate,
      throughput,
    };
  }
  
  /**
   * Run comprehensive performance test suite
   */
  async runFullPerformanceTest(): Promise<{
    loadTest: PerformanceTestResult;
    websocketTest: PerformanceTestResult;
    memoryTest: any;
    cpuTest: any;
  }> {
    // Run load test with 100 concurrent users
    const loadTest = await this.runLoadTest({
      concurrentUsers: 10, // Reduced for browser testing
      duration: 10,
      rampUpTime: 2,
    });
    
    // Test WebSocket with 50 connections
    const websocketTest = await this.testWebSocketLoad(10); // Reduced for browser testing
    
    // Test memory stress
    const memoryTest = await this.testMemoryStress();
    
    // Test CPU performance
    const cpuTest = await this.testCPUPerformance();
    
    return {
      loadTest,
      websocketTest,
      memoryTest,
      cpuTest,
    };
  }
  
  /**
   * Get test history
   */
  getTestHistory(): PerformanceTestResult[] {
    return [...this.testResults];
  }
  
  /**
   * Clear test history
   */
  clearHistory(): void {
    this.testResults = [];
  }
}

export const performanceTestService = PerformanceTestService.getInstance();