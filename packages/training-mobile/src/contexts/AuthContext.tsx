import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { useMMKVObject, useMMKVString } from 'react-native-mmkv';
import { authService } from '@/services/auth';
import { User, LoginCredentials, TokenPair } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useMMKVObject<User>('user');
  const [accessToken, setAccessToken] = useMMKVString('access_token');
  const [refreshToken, setRefreshToken] = useMMKVString('refresh_token');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on mount
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      if (accessToken && user) {
        // Verify token is still valid
        const isValid = await authService.verifyToken(accessToken);
        if (!isValid && refreshToken) {
          await refreshUserToken();
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      await logout();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (credentials: LoginCredentials) => {
    try {
      setIsLoading(true);
      const response = await authService.login(credentials);
      
      // Store tokens
      setAccessToken(response.access_token);
      setRefreshToken(response.refresh_token);
      
      // Store user data
      setUser(response.user);
      
      // Also store in secure store for extra security
      await SecureStore.setItemAsync('access_token', response.access_token);
      await SecureStore.setItemAsync('refresh_token', response.refresh_token);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      
      // Call logout API if token exists
      if (accessToken) {
        await authService.logout(accessToken);
      }
      
      // Clear local storage
      setUser(undefined);
      setAccessToken(undefined);
      setRefreshToken(undefined);
      
      // Clear secure store
      await SecureStore.deleteItemAsync('access_token');
      await SecureStore.deleteItemAsync('refresh_token');
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUserToken = async () => {
    try {
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const response = await authService.refreshToken(refreshToken);
      
      // Update tokens
      setAccessToken(response.access_token);
      setRefreshToken(response.refresh_token);
      
      // Update secure store
      await SecureStore.setItemAsync('access_token', response.access_token);
      await SecureStore.setItemAsync('refresh_token', response.refresh_token);
    } catch (error) {
      console.error('Token refresh failed:', error);
      await logout();
      throw error;
    }
  };

  const updateProfile = async (updates: Partial<User>) => {
    try {
      if (!user || !accessToken) {
        throw new Error('Not authenticated');
      }
      
      const updatedUser = await authService.updateProfile(user.id, updates, accessToken);
      setUser(updatedUser);
    } catch (error) {
      console.error('Profile update failed:', error);
      throw error;
    }
  };

  const value: AuthContextType = {
    user: user || null,
    isLoading,
    isAuthenticated: !!user && !!accessToken,
    login,
    logout,
    refreshToken: refreshUserToken,
    updateProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}