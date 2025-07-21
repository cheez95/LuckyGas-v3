import React from 'react';
import { useTokenRefresh } from '../../hooks/useTokenRefresh';
import { useSessionTimeout } from '../../hooks/useSessionTimeout';

interface SessionManagerProps {
  children: React.ReactNode;
}

const SessionManager: React.FC<SessionManagerProps> = ({ children }) => {
  // Automatic token refresh
  useTokenRefresh();
  
  // Session timeout warning
  useSessionTimeout({
    warningTime: 5 * 60 * 1000, // Show warning 5 minutes before expiry
    checkInterval: 30 * 1000, // Check every 30 seconds
  });
  
  return <>{children}</>;
};

export default SessionManager;