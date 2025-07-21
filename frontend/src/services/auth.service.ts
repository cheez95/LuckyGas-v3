import api from './api';
import { LoginRequest, LoginResponse, User } from '../types/auth';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Convert to form data format for OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    const response = await api.post<{ access_token: string; refresh_token: string; token_type: string }>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    // Store tokens
    const { access_token, refresh_token, token_type } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    
    // Store token expiry time (2 hours from now)
    const expiryTime = new Date().getTime() + (2 * 60 * 60 * 1000); // 2 hours in milliseconds
    localStorage.setItem('token_expiry', expiryTime.toString());
    
    // Fetch user data after successful login
    const user = await this.getCurrentUser();
    
    // Return combined response
    return {
      access_token,
      refresh_token,
      token_type,
      user,
    };
  },
  
  async logout(): Promise<void> {
    // Call logout endpoint if needed
    // await api.post('/auth/logout');
    
    // Clear tokens and expiry
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expiry');
  },
  
  
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};