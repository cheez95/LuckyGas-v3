import api, { handleApiError } from './api';
import { 
  Order, 
  OrderCreate, 
  OrderUpdate, 
  OrderStats,
  OrderV2,
  OrderCreateV2,
  OrderUpdateV2
} from '../types/order';

interface OrderQueryParams {
  skip?: number;
  limit?: number;
  status?: string;
  customer_id?: number;
  date_from?: string;
  date_to?: string;
  is_urgent?: boolean;
}

export const orderService = {
  async getOrders(params?: OrderQueryParams): Promise<Order[]> {
    try {
      const response = await api.get<Order[]>('/orders', { params });
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async getOrder(id: number): Promise<Order> {
    try {
      const response = await api.get<Order>(`/orders/${id}`);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async createOrder(data: OrderCreate): Promise<Order> {
    try {
      const response = await api.post<Order>('/orders', data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async updateOrder(id: number, data: OrderUpdate): Promise<Order> {
    try {
      const response = await api.put<Order>(`/orders/${id}`, data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async cancelOrder(id: number, reason?: string): Promise<void> {
    try {
      await api.delete(`/orders/${id}`, { 
        params: { reason } 
      });
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async getOrderStats(dateFrom?: string, dateTo?: string): Promise<OrderStats> {
    try {
      const response = await api.get<OrderStats>('/orders/stats/summary', {
        params: {
          date_from: dateFrom,
          date_to: dateTo,
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },

  // V2 methods for flexible product system
  async getOrderV2(id: number): Promise<OrderV2> {
    try {
      const response = await api.get<OrderV2>(`/orders/v2/${id}`);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },

  async createOrderV2(data: OrderCreateV2): Promise<OrderV2> {
    try {
      const response = await api.post<OrderV2>('/orders/v2/', data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },

  async updateOrderV2(id: number, data: OrderUpdateV2): Promise<OrderV2> {
    try {
      const response = await api.put<OrderV2>(`/orders/v2/${id}`, data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
};