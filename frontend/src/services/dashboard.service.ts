import { apiClient } from './api.service';

export interface DashboardStats {
  today_orders: number;
  today_revenue: number;
  active_customers: number;
  drivers_on_route: number;
  recent_deliveries: number;
  urgent_orders: number;
  completion_rate: number;
}

export interface RouteProgress {
  id: number;
  route_number: string;
  status: string;
  total_orders: number;
  completed_orders: number;
  driver_name?: string;
  progress_percentage: number;
}

export interface DashboardSummary {
  stats: DashboardStats;
  routes: RouteProgress[];
  predictions: {
    total: number;
    urgent: number;
    confidence: number;
  };
  response_time_ms: number;
}

class DashboardService {
  private readonly baseUrl = '/dashboard';
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private readonly CACHE_TTL = 30000; // 30 seconds

  /**
   * Get dashboard summary with all statistics in a single optimized call
   * @param date Optional date for statistics (defaults to today)
   * @returns Dashboard summary with stats, routes, and predictions
   */
  async getDashboardSummary(date?: string): Promise<DashboardSummary> {
    const cacheKey = `summary-${date || 'today'}`;
    
    // Check cache
    const cached = this.cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
      // console.log('📊 Using cached dashboard data');
      return cached.data;
    }
    
    try {
      const response = await apiClient.get<DashboardSummary>(`${this.baseUrl}/summary`, {
        params: date ? { date } : undefined
      });
      
      // Cache the response
      this.cache.set(cacheKey, {
        data: response.data,
        timestamp: Date.now()
      });
      
      return response.data;
    } catch (error) {
      console.error('Failed to fetch dashboard summary:', error);
      throw error;
    }
  }
  
  /**
   * Health check for dashboard API
   * @returns Health status
   */
  async checkHealth(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await apiClient.get(`${this.baseUrl}/health`);
      return response.data;
    } catch (error) {
      console.error('Dashboard health check failed:', error);
      return { status: 'unhealthy', timestamp: new Date().toISOString() };
    }
  }
  
  /**
   * Clear dashboard cache
   */
  clearCache(): void {
    this.cache.clear();
    // console.log('📊 Dashboard cache cleared');
  }
  
  /**
   * Invalidate specific cache entry
   * @param date Date to invalidate (optional, clears all if not provided)
   */
  invalidateCache(date?: string): void {
    if (date) {
      this.cache.delete(`summary-${date}`);
    } else {
      this.clearCache();
    }
  }
}

export const dashboardService = new DashboardService();