import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { notification } from 'antd';
import { useWebSocket } from '../hooks/useWebSocket';
import type { NotificationMessage } from '../services/websocket.service';

interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'success' | 'info' | 'warning' | 'error';
  timestamp: Date;
  read: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotification: (id: string) => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const { on } = useWebSocket();

  // Calculate unread count
  const unreadCount = notifications.filter(n => !n.read).length;

  // Add notification
  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      read: false,
    };

    setNotifications(prev => [newNotification, ...prev]);

    // Show Ant Design notification
    notification[notification.type]({
      message: notification.title,
      description: notification.message,
      placement: 'topRight',
      duration: 5,
    });
  }, []);

  // Mark as read
  const markAsRead = useCallback((id: string) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  // Clear notification
  const clearNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  // Clear all
  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  // Listen to WebSocket notifications
  useEffect(() => {
    const unsubscribeNotification = on<NotificationMessage>('notification', (message) => {
      let type: 'success' | 'info' | 'warning' | 'error' = 'info';
      
      // Map priority to notification type
      switch (message.priority) {
        case 'urgent':
          type = 'error';
          break;
        case 'high':
          type = 'warning';
          break;
        default:
          type = 'info';
      }

      addNotification({
        title: message.title,
        message: message.message,
        type,
      });
    });

    const unsubscribeSystemMessage = on('system_message', (message) => {
      addNotification({
        title: '系統訊息',
        message: message.message,
        type: message.priority === 'high' ? 'warning' : 'info',
      });
    });

    const unsubscribeOrderUpdate = on('order_update', (message) => {
      addNotification({
        title: '訂單更新',
        message: `訂單 #${message.order_id} 狀態已更新為 ${message.status}`,
        type: 'info',
      });
    });

    const unsubscribeRouteUpdate = on('route_update', (message) => {
      addNotification({
        title: '路線更新',
        message: `路線 #${message.route_id} 已更新`,
        type: 'info',
      });
    });

    const unsubscribePredictionReady = on('prediction_ready', (message) => {
      addNotification({
        title: '需求預測完成',
        message: `批次 ${message.batch_id} 的預測已完成`,
        type: 'success',
      });
    });

    const unsubscribeRouteAssigned = on('route_assigned', (message) => {
      addNotification({
        title: '新路線分配',
        message: `您已被分配到路線 #${message.route_id}`,
        type: 'warning',
      });
    });

    // Cleanup
    return () => {
      unsubscribeNotification();
      unsubscribeSystemMessage();
      unsubscribeOrderUpdate();
      unsubscribeRouteUpdate();
      unsubscribePredictionReady();
      unsubscribeRouteAssigned();
    };
  }, [on, addNotification]);

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    clearNotification,
    clearAll,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};