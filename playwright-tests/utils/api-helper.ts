import { APIRequestContext, APIResponse } from '@playwright/test';
import users from '../fixtures/users.json';

export class APIHelper {
  private request: APIRequestContext;
  private baseURL: string;
  private token: string | null = null;

  constructor(request: APIRequestContext) {
    this.request = request;
    this.baseURL = process.env.API_URL || 'http://localhost:8000';
  }

  async login(userType: keyof typeof users = 'admin'): Promise<string> {
    const user = users[userType];
    const response = await this.request.post(`${this.baseURL}/api/v1/auth/login`, {
      data: {
        username: user.username,
        password: user.password
      }
    });

    const responseData = await response.json();
    this.token = responseData.access_token;
    return this.token;
  }

  async logout(): Promise<void> {
    if (this.token) {
      await this.request.post(`${this.baseURL}/api/v1/auth/logout`, {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      });
      this.token = null;
    }
  }

  async get(endpoint: string, options?: any): Promise<APIResponse> {
    return await this.request.get(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        ...options?.headers,
        'Authorization': this.token ? `Bearer ${this.token}` : ''
      }
    });
  }

  async post(endpoint: string, data?: any, options?: any): Promise<APIResponse> {
    return await this.request.post(`${this.baseURL}${endpoint}`, {
      ...options,
      data,
      headers: {
        ...options?.headers,
        'Authorization': this.token ? `Bearer ${this.token}` : ''
      }
    });
  }

  async put(endpoint: string, data?: any, options?: any): Promise<APIResponse> {
    return await this.request.put(`${this.baseURL}${endpoint}`, {
      ...options,
      data,
      headers: {
        ...options?.headers,
        'Authorization': this.token ? `Bearer ${this.token}` : ''
      }
    });
  }

  async delete(endpoint: string, options?: any): Promise<APIResponse> {
    return await this.request.delete(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        ...options?.headers,
        'Authorization': this.token ? `Bearer ${this.token}` : ''
      }
    });
  }

  getToken(): string | null {
    return this.token;
  }

  setToken(token: string): void {
    this.token = token;
  }

  // Helper methods for specific API operations
  async createCustomer(customerData: any): Promise<any> {
    const response = await this.post('/api/v1/customers/', customerData);
    return await response.json();
  }

  async createOrder(orderData: any): Promise<any> {
    const response = await this.post('/api/v1/orders/', orderData);
    return await response.json();
  }

  async geocodeAddress(address: string): Promise<any> {
    const response = await this.get(`/api/v1/maps/geocode?address=${encodeURIComponent(address)}`);
    return await response.json();
  }

  async getAnalytics(endpoint: string, params?: any): Promise<any> {
    const queryString = params ? '?' + new URLSearchParams(params).toString() : '';
    const response = await this.get(`/api/v1/analytics/${endpoint}${queryString}`);
    return await response.json();
  }

  async getPredictions(type: string, data?: any): Promise<any> {
    const response = await this.post(`/api/v1/predictions/${type}`, data);
    return await response.json();
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.request.get(`${this.baseURL}/health`);
      return response.ok();
    } catch {
      return false;
    }
  }
}