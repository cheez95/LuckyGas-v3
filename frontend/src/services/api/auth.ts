import apiClient from './client';
import { LoginRequest, LoginResponse, RefreshTokenRequest, AuthResponse, User } from '../../types/auth';
import { setTokens, setUserData, clearTokens, getRefreshToken } from '../../utils/storage';

class AuthService {
  /**
   * Login with username and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', credentials);
      const { access_token, refresh_token, user } = response.data;
      
      // Store tokens and user data
      setTokens(access_token, refresh_token);
      setUserData(user);
      
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Logout and clear all stored data
   */
  async logout(): Promise<void> {
    try {
      // Call logout endpoint if available
      await apiClient.post('/api/v1/auth/logout');
    } catch (error) {
      // Logout endpoint might not exist or fail, continue with local cleanup
      console.error('Logout API error:', error);
    } finally {
      // Always clear local storage
      clearTokens();
    }
  }

  /**
   * Refresh the access token
   */
  async refreshToken(): Promise<AuthResponse> {
    const refreshToken = getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await apiClient.post<AuthResponse>('/api/v1/auth/refresh', {
        refresh_token: refreshToken
      } as RefreshTokenRequest);
      
      const { access_token, refresh_token: newRefreshToken, user } = response.data;
      
      // Update tokens and user data
      setTokens(access_token, newRefreshToken);
      if (user) {
        setUserData(user);
      }
      
      return response.data;
    } catch (error) {
      console.error('Token refresh error:', error);
      clearTokens();
      throw error;
    }
  }

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<User>('/api/v1/auth/me');
      setUserData(response.data);
      return response.data;
    } catch (error) {
      console.error('Get current user error:', error);
      throw error;
    }
  }

  /**
   * Change user password
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
    } catch (error) {
      console.error('Change password error:', error);
      throw error;
    }
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/password-reset', { email });
    } catch (error) {
      console.error('Password reset request error:', error);
      throw error;
    }
  }

  /**
   * Confirm password reset with token
   */
  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/password-reset/confirm', {
        token,
        new_password: newPassword
      });
    } catch (error) {
      console.error('Password reset confirmation error:', error);
      throw error;
    }
  }

  /**
   * Verify if user has specific permission
   */
  hasPermission(user: User | null, resource: string, action: string): boolean {
    if (!user) return false;
    
    // Role-based permission mapping (based on backend RBAC)
    const rolePermissions: Record<string, string[]> = {
      super_admin: ['*'], // All permissions
      manager: ['view_reports', 'assign_routes', 'manage_drivers', 'manage_orders'],
      office_staff: ['manage_orders', 'manage_customers', 'view_reports'],
      driver: ['view_routes', 'update_delivery', 'view_own_data'],
      customer: ['view_orders', 'track_delivery', 'view_own_data']
    };
    
    const userPermissions = rolePermissions[user.role] || [];
    
    // Check if user has wildcard permission or specific permission
    return userPermissions.includes('*') || 
           userPermissions.includes(`${action}_${resource}`) ||
           userPermissions.includes(action);
  }
}

// Export singleton instance
export default new AuthService();