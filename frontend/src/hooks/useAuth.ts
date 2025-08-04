import { useContext, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthContext from '../contexts/AuthContext';
import authService from '../services/api/auth';
import { LoginRequest } from '../types/auth';
import { setupStorageListener, removeStorageListener } from '../utils/storage';

export const useAuth = () => {
  const context = useContext(AuthContext);
  const navigate = useNavigate();
  
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  const { login: contextLogin, logout: contextLogout, refreshAccessToken, checkAuth } = context;
  
  // Enhanced login with navigation
  const login = useCallback(async (credentials: LoginRequest, redirectTo?: string) => {
    try {
      await contextLogin(credentials);
      // Navigate to dashboard or specified route after successful login
      navigate(redirectTo || '/dashboard');
    } catch (error) {
      // Error is handled in context
      throw error;
    }
  }, [contextLogin, navigate]);
  
  // Enhanced logout with navigation
  const logout = useCallback(async () => {
    await contextLogout();
    navigate('/login');
  }, [contextLogout, navigate]);
  
  // Setup multi-tab synchronization
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.newValue === null) {
        // Tokens were cleared in another tab
        contextLogout();
        navigate('/login');
      } else {
        // Tokens were updated in another tab
        checkAuth();
      }
    };
    
    setupStorageListener(handleStorageChange);
    
    return () => {
      removeStorageListener(handleStorageChange);
    };
  }, [contextLogout, checkAuth, navigate]);
  
  // Permission checking utility
  const hasPermission = useCallback((resource: string, action: string): boolean => {
    return authService.hasPermission(context.user, resource, action);
  }, [context.user]);
  
  // Role checking utilities
  const isAdmin = useCallback((): boolean => {
    return context.user?.role === 'super_admin';
  }, [context.user]);
  
  const isManager = useCallback((): boolean => {
    return context.user?.role === 'manager' || isAdmin();
  }, [context.user, isAdmin]);
  
  const isOfficeStaff = useCallback((): boolean => {
    return context.user?.role === 'office_staff' || isManager();
  }, [context.user, isManager]);
  
  const isDriver = useCallback((): boolean => {
    return context.user?.role === 'driver';
  }, [context.user]);
  
  const isCustomer = useCallback((): boolean => {
    return context.user?.role === 'customer';
  }, [context.user]);
  
  return {
    ...context,
    login,
    logout,
    refreshAccessToken,
    hasPermission,
    isAdmin,
    isManager,
    isOfficeStaff,
    isDriver,
    isCustomer
  };
};