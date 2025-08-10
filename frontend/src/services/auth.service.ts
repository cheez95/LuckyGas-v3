import api from './api';
import { LoginRequest, LoginResponse, User } from '../types/auth';
import { TokenRefreshResponse } from './tokenRefresh';

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Convert to form data format for OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    console.log('🔐 Sending login request...');
    const startTime = performance.now();
    
    const response = await api.post<{ access_token: string; refresh_token: string; token_type: string }>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      timeout: 10000, // 10 second timeout for login
    });
    
    const loginTime = performance.now() - startTime;
    console.log(`🔐 Login response received in ${loginTime.toFixed(0)}ms`, response.data);
    
    // Store tokens
    const { access_token, refresh_token, token_type } = response.data;
    console.log('🔐 Storing tokens...');
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    
    // Store token expiry time (2 hours from now)
    const expiryTime = new Date().getTime() + (2 * 60 * 60 * 1000); // 2 hours in milliseconds
    localStorage.setItem('token_expiry', expiryTime.toString());
    
    console.log('🔐 Tokens stored, checking localStorage:', {
      hasAccessToken: !!localStorage.getItem('access_token'),
      hasRefreshToken: !!localStorage.getItem('refresh_token'),
    });
    
    // Fetch user data after successful login
    console.log('🔐 Fetching current user...');
    const userStartTime = performance.now();
    const user = await this.getCurrentUser();
    const userTime = performance.now() - userStartTime;
    console.log(`🔐 User data fetched in ${userTime.toFixed(0)}ms`);
    
    const totalTime = performance.now() - startTime;
    console.log(`✅ Login complete in ${totalTime.toFixed(0)}ms (login: ${loginTime.toFixed(0)}ms, user: ${userTime.toFixed(0)}ms)`);
    
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
    // await api.post('/auth/logout/');
    
    // Clear tokens and expiry
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_expiry');
  },
  
  
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
  
  async requestPasswordReset(email: string): Promise<void> {
    await api.post('/auth/forgot-password', { email });
  },
  
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  },
  
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
  
  async refreshToken(refreshToken: string): Promise<TokenRefreshResponse> {
    const response = await api.post<TokenRefreshResponse & { token_type: string }>(
      '/auth/refresh',
      { refresh_token: refreshToken }
    );
    
    const { access_token, refresh_token: new_refresh_token } = response.data;
    
    // Update stored tokens
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', new_refresh_token);
    
    // Update token expiry time
    const expiryTime = new Date().getTime() + (2 * 60 * 60 * 1000); // 2 hours
    localStorage.setItem('token_expiry', expiryTime.toString());
    
    return { access_token, refresh_token: new_refresh_token };
  },
};