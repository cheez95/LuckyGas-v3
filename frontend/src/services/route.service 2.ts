import api from './api';
import { message } from 'antd';
import i18n from '../i18n';

export interface RouteStop {
  id: string;
  order_id: number;
  stop_sequence: number;
  address?: string;
  estimated_arrival?: string;
  is_completed?: boolean;
  location?: {
    lat: number;
    lng: number;
  };
}

export interface RoutePlan {
  id?: number;
  routeDate: string;
  routeNumber?: string;
  driverId: number;
  vehicleId?: number;
  status?: string;
  totalStops: number;
  totalDistance: number;
  totalDuration: number;
  stops: RouteStop[];
  optimizationScore?: number;
  notes?: string;
}

export interface OptimizeRouteRequest {
  date: string;
  driverId?: number;
  orderIds: number[];
  optimizationMode?: 'balanced' | 'distance' | 'time';
  allowSplitOrders?: boolean;
}

export interface OptimizeRouteResponse {
  optimizedOrder: number[];
  totalDistance: number;
  totalDuration: number;
  totalWeight: number;
  warnings?: string[];
}

export interface RouteSearchParams {
  date_from?: string;
  date_to?: string;
  driverId?: number;
  status?: string;
  area?: string;
}

export interface RouteWithDetails {
  id: number;
  route_number: string;
  route_date: string;
  area?: string;
  driver_id?: number;
  driver_name?: string;
  vehicle_id?: number;
  vehicle_plate?: string;
  status: 'planned' | 'optimized' | 'in_progress' | 'completed';
  total_orders: number;
  completed_orders: number;
  total_distance_km: number;
  estimated_duration_minutes: number;
  stops?: RouteStop[];
}

class RouteService {
  /**
   * Create a new route plan
   */
  async createRoutePlan(data: Partial<RoutePlan>): Promise<RoutePlan> {
    try {
      const response = await api.post('/routes', data);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.createFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get route plan by ID
   */
  async getRoutePlan(id: number): Promise<RoutePlan> {
    try {
      const response = await api.get(`/routes/${id}`);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Update route plan
   */
  async updateRoutePlan(id: number, data: Partial<RoutePlan>): Promise<RoutePlan> {
    try {
      const response = await api.put(`/routes/${id}`, data);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.updateFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Delete route plan
   */
  async deleteRoutePlan(id: number): Promise<void> {
    try {
      await api.delete(`/routes/${id}`);
      message.success(i18n.t('common.success.deleteSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.deleteFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Search route plans
   */
  async searchRoutePlans(params: RouteSearchParams): Promise<{
    routes: RoutePlan[];
    total: number;
  }> {
    try {
      const response = await api.get('/routes', { params });
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Optimize route for given orders
   */
  async optimizeRoute(request: OptimizeRouteRequest): Promise<OptimizeRouteResponse> {
    try {
      const response = await api.post('/routes/optimize', request);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.route.optimizeError');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Assign driver to route
   */
  async assignDriver(routeId: number, driverId: number): Promise<void> {
    try {
      await api.post(`/routes/${routeId}/assign-driver`, { driverId });
      message.success(i18n.t('dispatch.route.assignSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.route.assignError');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Update route status
   */
  async updateRouteStatus(routeId: number, status: string): Promise<void> {
    try {
      await api.put(`/routes/${routeId}/status`, { status });
      message.success(i18n.t('common.success.updateSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.updateFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get route statistics for a date range
   */
  async getRouteStatistics(dateFrom: string, dateTo: string): Promise<{
    totalRoutes: number;
    totalDistance: number;
    totalDeliveries: number;
    averageOptimizationScore: number;
    onTimeDeliveryRate: number;
  }> {
    try {
      const response = await api.get('/routes/statistics', {
        params: { dateFrom, dateTo }
      });
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get driver's routes for a specific date
   */
  async getDriverRoutes(driverId: number, date: string): Promise<RoutePlan[]> {
    try {
      const response = await api.get(`/drivers/${driverId}/routes`, {
        params: { date }
      });
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get routes with details (alias for searchRoutePlans)
   */
  async getRoutes(params: RouteSearchParams): Promise<RouteWithDetails[]> {
    try {
      const response = await api.get('/routes', { params });
      return response.data.routes || response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Optimize routes in batch
   */
  async optimizeRoutesBatch(params: { date: string; area?: string }): Promise<{ routes_created: number; orders_assigned: number }> {
    try {
      const response = await api.post('/routes/optimize-batch', params);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.route.optimizeError');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get driver route details
   */
  async getDriverRoute(driverId: number, routeId: number): Promise<RouteWithDetails> {
    try {
      const response = await api.get(`/drivers/${driverId}/routes/${routeId}`);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Start a route
   */
  async startRoute(routeId: number): Promise<void> {
    try {
      await api.post(`/routes/${routeId}/start`);
      message.success(i18n.t('dispatch.route.startSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.route.startError');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Bulk assign multiple routes
   */
  async bulkAssignRoutes(assignments: { routeId: number; driverId: number }[]): Promise<void> {
    try {
      await api.post('/routes/bulk-assign', { assignments });
      message.success(i18n.t('dispatch.route.bulkAssignSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.route.bulkAssignError');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Complete a route
   */
  async completeRoute(routeId: number): Promise<void> {
    try {
      await api.post(`/routes/${routeId}/complete`);
      message.success(i18n.t('route.completeSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.updateFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Complete a delivery stop
   */
  async completeStop(stopId: string, data: {
    signature?: string;
    photos?: string[];
    notes?: string;
  }): Promise<void> {
    try {
      await api.post(`/routes/stops/${stopId}/complete`, data);
      message.success(i18n.t('route.stopCompleteSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.updateFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Update driver location
   */
  async updateDriverLocation(data: {
    latitude: number;
    longitude: number;
    accuracy?: number;
    timestamp?: string;
  }): Promise<void> {
    try {
      await api.post('/drivers/location', data);
    } catch (error: any) {
      // Silently fail for location updates to avoid spamming errors
      console.error('Failed to update driver location:', error);
    }
  }
}

export const routeService = new RouteService();