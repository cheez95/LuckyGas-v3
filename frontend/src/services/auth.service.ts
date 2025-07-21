import api from './api';
import { LoginRequest, LoginResponse, User } from '../types/auth';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Convert to form data format for OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    const response = await api.post<{ access_token: string; token_type: string }>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    // Store token
    const { access_token, token_type } = response.data;
    localStorage.setItem('access_token', access_token);
    
    // Fetch user data after successful login
    const user = await this.getCurrentUser();
    
    // Return combined response
    return {
      access_token,
      refresh_token: null as any, // Backend doesn't support refresh tokens yet
      token_type,
      user,
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