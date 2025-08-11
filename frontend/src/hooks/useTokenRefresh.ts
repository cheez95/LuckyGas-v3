import { useEffect, useRef, useCallback } from 'react';
import { tokenRefreshService } from '../services/tokenRefresh';
import { useAuth } from '../contexts/AuthContext';

export const useTokenRefresh = () => {
  const { isAuthenticated, logout } = useAuth();
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  const scheduleTokenRefresh = useCallback(() => {
    // Clear any existing timer
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    
    const timeUntilExpiry = tokenRefreshService.getTimeUntilExpiry();
    
    // If token_expiry is not set but access_token exists, set a default expiry
    const hasToken = localStorage.getItem('access_token');
    const hasExpiry = localStorage.getItem('token_expiry');
    
    if (hasToken && !hasExpiry) {
      // Set default expiry to 2 hours from now
      const defaultExpiry = new Date().getTime() + (2 * 60 * 60 * 1000);
      localStorage.setItem('token_expiry', defaultExpiry.toString());
      // Recalculate time until expiry
      scheduleTokenRefresh();
      return;
    }
    
    if (timeUntilExpiry <= 0 && hasExpiry) {
      // Token already expired (only if expiry was actually set)
      logout();
      return;
    }
    
    // Schedule refresh 5 minutes before expiry
    const refreshTime = Math.max(0, timeUntilExpiry - 5 * 60 * 1000);
    
    if (refreshTime > 0) {
      refreshTimerRef.current = setTimeout(async () => {
        try {
          await tokenRefreshService.refreshToken();
          // Schedule next refresh
          scheduleTokenRefresh();
        } catch (error) {
          console.error('Token refresh failed:', error);
          // Let the interceptor handle the logout
        }
      }, refreshTime);
    }
  }, [logout]);
  
  useEffect(() => {
    if (isAuthenticated) {
      scheduleTokenRefresh();
    }
    
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [isAuthenticated, scheduleTokenRefresh]);
  
  return {
    scheduleTokenRefresh,
    timeUntilExpiry: tokenRefreshService.getTimeUntilExpiry(),
    isTokenExpiringSoon: tokenRefreshService.isTokenExpiringSoon()
  };
};