// Token refresh logic separated to avoid circular dependencies
import axios from 'axios';
import { message } from 'antd';
import { navigateTo } from '../utils/router';

const API_URL = import.meta.env.VITE_API_URL || '';

export interface TokenRefreshResponse {
  access_token: string;
  refresh_token: string;
}

export const tokenRefreshService = {
  async refreshToken(): Promise<TokenRefreshResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await axios.post<TokenRefreshResponse & { token_type: string }>(
        `${API_URL ? `${API_URL}/api/v1` : '/api/v1'}/auth/refresh`,
        { refresh_token: refreshToken },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      
      const { access_token, refresh_token: new_refresh_token } = response.data;
      
      // Update stored tokens
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', new_refresh_token);
      
      // Update token expiry time
      const expiryTime = new Date().getTime() + (2 * 60 * 60 * 1000); // 2 hours in milliseconds
      localStorage.setItem('token_expiry', expiryTime.toString());
      
      return { access_token, refresh_token: new_refresh_token };
    } catch (error) {
      // Clear tokens and redirect to login on refresh failure
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('token_expiry');
      message.error('登入已過期，請重新登入');
      navigateTo('/login');
      throw error;
    }
  },
  
  isTokenExpiringSoon(): boolean {
    const expiryTime = localStorage.getItem('token_expiry');
    if (!expiryTime) return true;
    
    const now = new Date().getTime();
    const expiry = parseInt(expiryTime);
    const timeUntilExpiry = expiry - now;
    
    // Consider token expiring soon if less than 5 minutes left
    return timeUntilExpiry < 5 * 60 * 1000;
  },
  
  getTimeUntilExpiry(): number {
    const expiryTime = localStorage.getItem('token_expiry');
    if (!expiryTime) {
      // If no expiry time but token exists, assume it's valid for 2 hours
      const hasToken = localStorage.getItem('access_token');
      if (hasToken) {
        // Return a safe default (1 hour remaining)
        return 60 * 60 * 1000;
      }
      return 0;
    }
    
    const now = new Date().getTime();
    const expiry = parseInt(expiryTime);
    return Math.max(0, expiry - now);
  }
};