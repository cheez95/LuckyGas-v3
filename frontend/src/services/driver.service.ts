import api from './api';
import { message } from 'antd';
import i18n from '../i18n';

export interface Driver {
  id: number;
  email: string;
  username: string;
  fullName: string;
  role: string;
  isActive: boolean;
  createdAt: string;
  updatedAt?: string;
  // Driver specific fields
  vehicleId?: number;
  vehicleNumber?: string;
  vehicleType?: string;
  licensePlate?: string;
  phoneNumber?: string;
  emergencyContact?: string;
  emergencyPhone?: string;
  isAvailable?: boolean;
  currentLocation?: {
    latitude: number;
    longitude: number;
    heading?: number;
    speed?: number;
    updatedAt: string;
  };
}

export interface DriverStats {
  totalDeliveries: number;
  totalDistance: number;
  averageDeliveryTime: number;
  onTimeRate: number;
  customerRating?: number;
}

export interface DriverAvailability {
  driverId: number;
  date: string;
  isAvailable: boolean;
  startTime?: string;
  endTime?: string;
  notes?: string;
}

class DriverService {
  /**
   * Get all drivers
   */
  async getDrivers(): Promise<Driver[]> {
    try {
      const response = await api.get('/drivers');
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get driver by ID
   */
  async getDriver(id: number): Promise<Driver> {
    try {
      const response = await api.get(`/drivers/${id}`);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get available drivers for a specific date
   */
  async getAvailableDrivers(date: string): Promise<Driver[]> {
    try {
      const response = await api.get('/drivers/available', {
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
   * Update driver availability
   */
  async updateAvailability(driverId: number, availability: Partial<DriverAvailability>): Promise<void> {
    try {
      await api.put(`/drivers/${driverId}/availability`, availability);
      message.success(i18n.t('common.success.updateSuccess'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.updateFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get driver statistics
   */
  async getDriverStats(driverId: number, dateFrom?: string, dateTo?: string): Promise<DriverStats> {
    try {
      const response = await api.get(`/drivers/${driverId}/stats`, {
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
   * Get driver's current location
   */
  async getDriverLocation(driverId: number): Promise<{
    latitude: number;
    longitude: number;
    heading?: number;
    speed?: number;
    updatedAt: string;
  }> {
    try {
      const response = await api.get(`/drivers/${driverId}/location`);
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Track multiple drivers' locations
   */
  async trackDrivers(driverIds: number[]): Promise<Map<number, {
    latitude: number;
    longitude: number;
    heading?: number;
    speed?: number;
    updatedAt: string;
  }>> {
    try {
      const response = await api.post('/drivers/track', { driverIds });
      return new Map(Object.entries(response.data).map(([id, location]) => [Number(id), location]));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.fetchFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Assign vehicle to driver
   */
  async assignVehicle(driverId: number, vehicleId: number): Promise<void> {
    try {
      await api.post(`/drivers/${driverId}/assign-vehicle`, { vehicleId });
      message.success(i18n.t('dispatch.driver.vehicleAssigned'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.driver.vehicleAssignError');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Update driver profile
   */
  async updateDriver(id: number, data: Partial<Driver>): Promise<Driver> {
    try {
      const response = await api.put(`/drivers/${id}`, data);
      message.success(i18n.t('common.success.updateSuccess'));
      return response.data;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('common.error.updateFailed');
      message.error(errorMessage);
      throw error;
    }
  }

  /**
   * Get driver's route history
   */
  async getDriverRouteHistory(driverId: number, dateFrom: string, dateTo: string): Promise<{
    routes: any[];
    totalRoutes: number;
    totalDistance: number;
    totalDeliveries: number;
  }> {
    try {
      const response = await api.get(`/drivers/${driverId}/route-history`, {
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
   * Send notification to driver
   */
  async sendNotification(driverId: number, notification: {
    title: string;
    message: string;
    type: 'info' | 'warning' | 'urgent';
    data?: any;
  }): Promise<void> {
    try {
      await api.post(`/drivers/${driverId}/notify`, notification);
      message.success(i18n.t('dispatch.driver.notificationSent'));
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || i18n.t('dispatch.driver.notificationError');
      message.error(errorMessage);
      throw error;
    }
  }
}

export const driverService = new DriverService();