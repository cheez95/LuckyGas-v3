import api, { handleApiError } from './api';
import { Customer } from '../types/order';
import { CustomerInventory, CustomerInventoryList } from '../types/product';

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
    } catch (error: any) {
      // For duplicate customer codes, throw with the original error message
      if (error.response?.status === 400 && error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
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
  
  // Customer inventory methods
  async getCustomerInventory(customerId: number): Promise<CustomerInventoryList> {
    try {
      const response = await api.get<CustomerInventoryList>(`/customers/${customerId}/inventory`);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  async updateInventoryItem(customerId: number, productId: number, data: { quantity_owned?: number; quantity_rented?: number }): Promise<CustomerInventory> {
    try {
      const response = await api.put<CustomerInventory>(`/customers/${customerId}/inventory/${productId}`, data);
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
};