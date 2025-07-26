import api from './api';
import { message } from 'antd';
import i18n from '../i18n';

export interface RouteStop {
  id: string;
  orderId: number;
  sequence: number;
  location: {
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
  dateFrom?: string;
  dateTo?: string;
  driverId?: number;
  status?: string[];
  area?: string;
}

class RouteService {
  /**
   * Create a new route plan
   */
  async createRoutePlan(data: Partial<RoutePlan>): Promise<RoutePlan> {
    try {
      const response = await api.post('/routes/plans', data);
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
      const response = await api.get(`/routes/plans/${id}`);
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
      const response = await api.put(`/routes/plans/${id}`, data);
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
      await api.delete(`/routes/plans/${id}`);
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
      const response = await api.get('/routes/plans', { params });
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
      await api.post(`/routes/plans/${routeId}/assign-driver`, { driverId });
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
      await api.put(`/routes/plans/${routeId}/status`, { status });
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
}

export const routeService = new RouteService();