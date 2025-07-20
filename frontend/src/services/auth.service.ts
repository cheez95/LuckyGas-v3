import api from './api';
import { LoginRequest, LoginResponse, User } from '../types/auth';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    const response = await api.post<{ access_token: string; token_type: string }>('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Store token temporarily to get user data
    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    
    // Get user data
    const userResponse = await api.get<User>('/auth/me');
    
    // Return combined response
    return {
      access_token,
      refresh_token: null as any, // Backend doesn't support refresh tokens yet
      token_type: response.data.token_type,
      user: userResponse.data,
    };
  },
  
  async logout(): Promise<void> {
    // Call logout endpoint if needed
    // await api.post('/auth/logout');
    
    // Clear token
    localStorage.removeItem('access_token');
  },
  
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};