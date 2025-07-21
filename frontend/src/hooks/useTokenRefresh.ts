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
    
    if (timeUntilExpiry <= 0) {
      // Token already expired
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