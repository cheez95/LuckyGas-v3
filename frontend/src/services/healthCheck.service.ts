/**
 * Health Check Service
 * Comprehensive system health monitoring for production readiness
 */

export interface HealthCheckResult {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  responseTime: number;
  message?: string;
  timestamp: Date;
  details?: any;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'unhealthy';
  checks: HealthCheckResult[];
  timestamp: Date;
  uptime: number;
  performance: {
    avgResponseTime: number;
    errorRate: number;
    successRate: number;
  };
}

class HealthCheckService {
  private static instance: HealthCheckService;
  private healthChecks: HealthCheckResult[] = [];
  private startTime: Date = new Date();
  
  private constructor() {}
  
  static getInstance(): HealthCheckService {
    if (!HealthCheckService.instance) {
      HealthCheckService.instance = new HealthCheckService();
    }
    return HealthCheckService.instance;
  }
  
  /**
   * Check API endpoint health
   */
  async checkAPIHealth(): Promise<HealthCheckResult> {
    const start = performance.now();
    const result: HealthCheckResult = {
      service: 'API',
      status: 'unhealthy',
      responseTime: 0,
      timestamp: new Date(),
    };
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000),
      });
      
      result.responseTime = performance.now() - start;
      
      if (response.ok) {
        const data = await response.json();
        result.status = 'healthy';
        result.details = data;
        result.message = 'API is responsive';
      } else {
        result.status = response.status >= 500 ? 'unhealthy' : 'degraded';
        result.message = `API returned status ${response.status}`;
      }
    } catch (error: any) {
      result.status = 'unhealthy';
      result.responseTime = performance.now() - start;
      result.message = `API check failed: ${error.message}`;
    }
    
    this.healthChecks.push(result);
    return result;
  }
  
  /**
   * Check WebSocket connectivity
   */
  async checkWebSocketHealth(): Promise<HealthCheckResult> {
    const start = performance.now();
    const result: HealthCheckResult = {
      service: 'WebSocket',
      status: 'unhealthy',
      responseTime: 0,
      timestamp: new Date(),
    };
    
    return new Promise((resolve) => {
      const wsUrl = import.meta.env.VITE_WS_URL || 'wss://localhost';
      const timeout = setTimeout(() => {
        result.status = 'unhealthy';
        result.responseTime = performance.now() - start;
        result.message = 'WebSocket connection timeout';
        this.healthChecks.push(result);
        resolve(result);
      }, 5000);
      
      try {
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          result.status = 'healthy';
          result.responseTime = performance.now() - start;
          result.message = 'WebSocket connected successfully';
          clearTimeout(timeout);
          ws.close();
          this.healthChecks.push(result);
          resolve(result);
        };
        
        ws.onerror = (error) => {
          result.status = 'unhealthy';
          result.responseTime = performance.now() - start;
          result.message = 'WebSocket connection failed';
          clearTimeout(timeout);
          this.healthChecks.push(result);
          resolve(result);
        };
      } catch (error: any) {
        result.status = 'unhealthy';
        result.responseTime = performance.now() - start;
        result.message = `WebSocket error: ${error.message}`;
        clearTimeout(timeout);
        this.healthChecks.push(result);
        resolve(result);
      }
    });
  }
  
  /**
   * Check authentication service
   */
  async checkAuthHealth(): Promise<HealthCheckResult> {
    const start = performance.now();
    const result: HealthCheckResult = {
      service: 'Authentication',
      status: 'unhealthy',
      responseTime: 0,
      timestamp: new Date(),
    };
    
    try {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        result.status = 'degraded';
        result.message = 'No authentication token found';
        result.responseTime = performance.now() - start;
      } else {
        // Verify token with backend
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/me`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          signal: AbortSignal.timeout(5000),
        });
        
        result.responseTime = performance.now() - start;
        
        if (response.ok) {
          result.status = 'healthy';
          result.message = 'Authentication valid';
          const user = await response.json();
          result.details = { user: user.username, role: user.role };
        } else if (response.status === 401) {
          result.status = 'degraded';
          result.message = 'Authentication expired or invalid';
        } else {
          result.status = 'unhealthy';
          result.message = `Auth check returned status ${response.status}`;
        }
      }
    } catch (error: any) {
      result.status = 'unhealthy';
      result.responseTime = performance.now() - start;
      result.message = `Auth check failed: ${error.message}`;
    }
    
    this.healthChecks.push(result);
    return result;
  }
  
  /**
   * Check database connectivity through API
   */
  async checkDatabaseHealth(): Promise<HealthCheckResult> {
    const start = performance.now();
    const result: HealthCheckResult = {
      service: 'Database',
      status: 'unhealthy',
      responseTime: 0,
      timestamp: new Date(),
    };
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/health/db`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(5000),
      });
      
      result.responseTime = performance.now() - start;
      
      if (response.ok) {
        result.status = 'healthy';
        result.message = 'Database connection healthy';
        const data = await response.json();
        result.details = data;
      } else {
        result.status = 'unhealthy';
        result.message = `Database check returned status ${response.status}`;
      }
    } catch (error: any) {
      result.status = 'unhealthy';
      result.responseTime = performance.now() - start;
      result.message = `Database check failed: ${error.message}`;
    }
    
    this.healthChecks.push(result);
    return result;
  }
  
  /**
   * Check critical endpoints
   */
  async checkCriticalEndpoints(): Promise<HealthCheckResult[]> {
    const endpoints = [
      { name: 'Orders', url: '/api/v1/orders', method: 'GET' },
      { name: 'Customers', url: '/api/v1/customers', method: 'GET' },
      { name: 'Drivers', url: '/api/v1/drivers', method: 'GET' },
      { name: 'Routes', url: '/api/v1/routes', method: 'GET' },
      { name: 'Analytics', url: '/api/v1/analytics/summary', method: 'GET' },
    ];
    
    const results: HealthCheckResult[] = [];
    
    for (const endpoint of endpoints) {
      const start = performance.now();
      const result: HealthCheckResult = {
        service: endpoint.name,
        status: 'unhealthy',
        responseTime: 0,
        timestamp: new Date(),
      };
      
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${import.meta.env.VITE_API_URL}${endpoint.url}`, {
          method: endpoint.method,
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json',
          },
          signal: AbortSignal.timeout(5000),
        });
        
        result.responseTime = performance.now() - start;
        
        if (response.ok) {
          result.status = result.responseTime < 500 ? 'healthy' : 'degraded';
          result.message = `${endpoint.name} endpoint responsive`;
        } else if (response.status === 401) {
          result.status = 'degraded';
          result.message = `${endpoint.name} requires authentication`;
        } else {
          result.status = 'unhealthy';
          result.message = `${endpoint.name} returned status ${response.status}`;
        }
      } catch (error: any) {
        result.status = 'unhealthy';
        result.responseTime = performance.now() - start;
        result.message = `${endpoint.name} check failed: ${error.message}`;
      }
      
      results.push(result);
      this.healthChecks.push(result);
    }
    
    return results;
  }
  
  /**
   * Run comprehensive health check
   */
  async runFullHealthCheck(): Promise<SystemHealth> {
    const checks: HealthCheckResult[] = [];
    
    // Run all health checks
    checks.push(await this.checkAPIHealth());
    checks.push(await this.checkWebSocketHealth());
    checks.push(await this.checkAuthHealth());
    checks.push(await this.checkDatabaseHealth());
    
    const endpointChecks = await this.checkCriticalEndpoints();
    checks.push(...endpointChecks);
    
    // Calculate overall health
    const unhealthyCount = checks.filter(c => c.status === 'unhealthy').length;
    const degradedCount = checks.filter(c => c.status === 'degraded').length;
    
    let overall: 'healthy' | 'degraded' | 'unhealthy';
    if (unhealthyCount > 0) {
      overall = 'unhealthy';
    } else if (degradedCount > 0) {
      overall = 'degraded';
    } else {
      overall = 'healthy';
    }
    
    // Calculate performance metrics
    const avgResponseTime = checks.reduce((sum, c) => sum + c.responseTime, 0) / checks.length;
    const errorRate = (unhealthyCount / checks.length) * 100;
    const successRate = (checks.filter(c => c.status === 'healthy').length / checks.length) * 100;
    
    const uptime = Date.now() - this.startTime.getTime();
    
    return {
      overall,
      checks,
      timestamp: new Date(),
      uptime,
      performance: {
        avgResponseTime,
        errorRate,
        successRate,
      },
    };
  }
  
  /**
   * Get historical health data
   */
  getHealthHistory(): HealthCheckResult[] {
    return [...this.healthChecks];
  }
  
  /**
   * Clear health check history
   */
  clearHistory(): void {
    this.healthChecks = [];
  }
  
  /**
   * Calculate uptime percentage
   */
  getUptimePercentage(): number {
    if (this.healthChecks.length === 0) return 100;
    
    const healthyChecks = this.healthChecks.filter(c => c.status !== 'unhealthy').length;
    return (healthyChecks / this.healthChecks.length) * 100;
  }
}

export const healthCheckService = HealthCheckService.getInstance();