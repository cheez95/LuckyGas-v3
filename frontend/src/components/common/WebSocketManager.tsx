import { useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { websocketService } from '../../services/websocket.service';

/**
 * WebSocketManager component handles WebSocket connection lifecycle
 * based on authentication status
 */
const WebSocketManager: React.FC = () => {
  const { accessToken, isAuthenticated } = useAuth();

  useEffect(() => {
    // console.log('🔌 WebSocketManager: Auth state changed');
    // console.log('🔌 isAuthenticated:', isAuthenticated);
    // console.log('🔌 Token exists:', !!accessToken);
    // console.log('🔌 Token in localStorage:', !!localStorage.getItem('access_token'));
    
    let connectTimer: NodeJS.Timeout | null = null;
    
    if (isAuthenticated && accessToken) {
      // console.log('🔌 WebSocketManager: User authenticated, initializing connection...');
      // console.log('🔌 Current connection state:', websocketService.getConnectionState());
      
      // Check if already connected
      if (websocketService.isConnected()) {
        // console.log('🔌 WebSocket already connected, skipping...');
        return;
      }
      
      // Add a small delay to ensure token is properly set in localStorage
      connectTimer = setTimeout(() => {
        // console.log('🔌 Calling websocketService.connect()...');
        websocketService.connect();
      }, 500); // Increased delay to ensure auth is fully settled
    } else {
      // console.log('🔌 WebSocketManager: User not authenticated, disconnecting...');
      // console.log('🔌 Reason - isAuthenticated:', isAuthenticated, 'token:', !!accessToken);
      websocketService.disconnect();
    }

    // Cleanup on unmount
    return () => {
      // console.log('🔌 WebSocketManager: Component unmounting, cleaning up...');
      
      // Clear timer if still pending
      if (connectTimer) {
        clearTimeout(connectTimer);
      }
      
      // Don't disconnect on unmount if user is still authenticated
      if (!isAuthenticated) {
        websocketService.disconnect();
      }
    };
  }, [isAuthenticated, accessToken]);

  // This component doesn't render anything
  return null;
};

export default WebSocketManager;