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
    
    try {
      // Use the simplified backend login endpoint directly
      console.log('🚀 Calling simplified backend login endpoint...');
      const response = await api.post<{
        access_token: string;
        refresh_token?: string;
        token_type: string;
        user?: User;
      }>('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        timeout: 10000, // 10 second timeout for login
      });
      
      const loginTime = performance.now() - startTime;
      console.log(`🚀 Login response received in ${loginTime.toFixed(0)}ms`, response.data);
      
      // Store tokens - simplified backend returns user in response
      const { access_token, token_type, user } = response.data;
      console.log('🔐 Storing access token...');
      localStorage.setItem('access_token', access_token);
      
      // Note: Simplified backend doesn't use refresh tokens, so we'll skip that
      // Store token expiry time (30 minutes from now as per backend settings)
      const expiryTime = new Date().getTime() + (30 * 60 * 1000); // 30 minutes in milliseconds
      localStorage.setItem('token_expiry', expiryTime.toString());
      
      console.log('🔐 Token stored, checking localStorage:', {
        hasAccessToken: !!localStorage.getItem('access_token'),
      });
      
      const totalTime = performance.now() - startTime;
      console.log(`✅ Login complete in ${totalTime.toFixed(0)}ms`);
      
      // Return response with user data if provided, otherwise fetch it
      if (user) {
        return {
          access_token,
          refresh_token: '', // No refresh token in simplified backend
          token_type,
          user,
        };
      } else {
        // Fetch user data if not included in login response
        const userResponse = await api.get<User>('/auth/me');
        return {
          access_token,
          refresh_token: '', // No refresh token in simplified backend
          token_type,
          user: userResponse.data,
        };
      }
    } catch (error: any) {
      // Log the error details
      console.error('❌ Login failed:', error?.response?.data || error.message);
      
      // Throw a user-friendly error message
      if (error?.response?.status === 401) {
        throw new Error('帳號或密碼錯誤'); // "Incorrect username or password"
      } else if (error?.response?.status === 400) {
        throw new Error('帳號已被停用'); // "Account has been deactivated"
      } else if (!error?.response) {
        throw new Error('網路連線錯誤，請檢查您的網路連線'); // "Network error, please check your connection"
      } else {
        throw new Error('登入失敗，請稍後再試'); // "Login failed, please try again later"
      }
    }
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