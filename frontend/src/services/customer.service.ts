import api, { handleApiError } from './api';
import { Customer } from '../types/order';

interface CustomerQueryParams {
  skip?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
  area?: string;
}

interface CustomerListResponse {
  items: Customer[];
  total: number;
  skip: number;
  limit: number;
}

export const customerService = {
  async getCustomers(params?: CustomerQueryParams): Promise<CustomerListResponse> {
    try {
      const response = await api.get<CustomerListResponse>('/customers', { params });
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async getCustomer(id: number): Promise<Customer> {
    try {
      const response = await api.get<Customer>(`/customers/${id}`);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async createCustomer(data: Omit<Customer, 'id'>): Promise<Customer> {
    try {
      const response = await api.post<Customer>('/customers', data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async updateCustomer(id: number, data: Partial<Customer>): Promise<Customer> {
    try {
      const response = await api.put<Customer>(`/customers/${id}`, data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async deleteCustomer(id: number): Promise<void> {
    try {
      await api.delete(`/customers/${id}`);
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
};