import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/auth.service';
import { AuthContextType, AuthState, LoginRequest } from '../types/auth';
import { handleApiError } from '../services/api';

const initialState: AuthState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const navigate = useNavigate();
  const [state, setState] = useState<AuthState>(initialState);

  // Check if user is already logged in on mount
  useEffect(() => {
    const initAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      
      if (accessToken) {
        try {
          const user = await authService.getCurrentUser();
          setState({
            user,
            accessToken,
            refreshToken: null,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          // Token might be expired or invalid, clear it
          localStorage.removeItem('access_token');
          setState({
            ...initialState,
            isLoading: false,
          });
        }
      } else {
        setState({
          ...initialState,
          isLoading: false,
        });
      }
    };
    
    initAuth();
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const response = await authService.login(credentials);
      
      // Store token
      localStorage.setItem('access_token', response.access_token);
      
      setState({
        user: response.user,
        accessToken: response.access_token,
        refreshToken: null,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      
      // Navigate based on user role
      switch (response.user.role) {
        case 'driver':
          navigate('/driver');
          break;
        case 'customer':
          navigate('/customer');
          break;
        default:
          navigate('/dashboard');
      }
    } catch (error) {
      const errorMessage = handleApiError(error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [navigate]);

  const logout = useCallback(() => {
    authService.logout();
    setState({
      ...initialState,
      isLoading: false,
    });
    navigate('/login');
  }, [navigate]);

  const refreshAccessToken = useCallback(async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await authService.refreshToken(refreshToken);
      
      // Update state with new token
      setState(prev => ({
        ...prev,
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
      }));
      
      return response.access_token;
    } catch (error) {
      // If refresh fails, clear everything and redirect to login
      logout();
      throw error;
    }
  }, [logout]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    refreshAccessToken,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};