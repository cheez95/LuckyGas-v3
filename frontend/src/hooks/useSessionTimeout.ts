import { useEffect, useRef, useState, useCallback } from 'react';
import { Modal } from 'antd';
import { useAuth } from '../contexts/AuthContext';
import { tokenRefreshService } from '../services/tokenRefresh';

interface UseSessionTimeoutOptions {
  warningTime?: number; // Time before expiry to show warning (in milliseconds)
  checkInterval?: number; // How often to check session status (in milliseconds)
}

export const useSessionTimeout = (options: UseSessionTimeoutOptions = {}) => {
  const {
    warningTime = 5 * 60 * 1000, // 5 minutes before expiry
    checkInterval = 30 * 1000, // Check every 30 seconds
  } = options;
  
  const { isAuthenticated, logout } = useAuth();
  const [showWarning, setShowWarning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const warningModalRef = useRef<any>(null);
  
  const formatTime = (ms: number): string => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}分${seconds}秒`;
  };
  
  const handleContinueSession = useCallback(async () => {
    try {
      await tokenRefreshService.refreshToken();
      setShowWarning(false);
      if (warningModalRef.current) {
        warningModalRef.current.destroy();
        warningModalRef.current = null;
      }
    } catch (error) {
      console.error('Failed to refresh session:', error);
    }
  }, []);
  
  const handleLogout = useCallback(() => {
    setShowWarning(false);
    if (warningModalRef.current) {
      warningModalRef.current.destroy();
      warningModalRef.current = null;
    }
    logout();
  }, [logout]);
  
  const checkSession = useCallback(() => {
    if (!isAuthenticated) {
      return;
    }
    
    const timeUntilExpiry = tokenRefreshService.getTimeUntilExpiry();
    setTimeRemaining(timeUntilExpiry);
    
    // Check if we should show warning
    if (timeUntilExpiry > 0 && timeUntilExpiry <= warningTime && !showWarning && !warningModalRef.current) {
      setShowWarning(true);
      
      warningModalRef.current = Modal.warning({
        title: '登入即將過期',
        content: `您的登入將在 ${formatTime(timeUntilExpiry)} 後過期。是否要繼續使用？`,
        okText: '繼續使用',
        cancelText: '登出',
        onOk: handleContinueSession,
        onCancel: handleLogout,
        okCancel: true,
        centered: true,
        maskClosable: false,
        keyboard: false,
      });
    }
    
    // Auto logout if token expired
    if (timeUntilExpiry <= 0) {
      handleLogout();
    }
  }, [isAuthenticated, warningTime, showWarning, handleContinueSession, handleLogout]);
  
  // Update warning modal content with remaining time
  useEffect(() => {
    if (showWarning && warningModalRef.current && timeRemaining > 0) {
      warningModalRef.current.update({
        content: `您的登入將在 ${formatTime(timeRemaining)} 後過期。是否要繼續使用？`,
      });
    }
  }, [showWarning, timeRemaining]);
  
  useEffect(() => {
    if (isAuthenticated) {
      // Initial check
      checkSession();
      
      // Set up interval
      intervalRef.current = setInterval(checkSession, checkInterval);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (warningModalRef.current) {
        warningModalRef.current.destroy();
        warningModalRef.current = null;
      }
    };
  }, [isAuthenticated, checkSession, checkInterval]);
  
  return {
    showWarning,
    timeRemaining,
    handleContinueSession,
    handleLogout,
  };
};