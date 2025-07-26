import React, { useEffect, useState } from 'react';
import { Alert, Badge, Space, Button } from 'antd';
import { ExclamationCircleOutlined, CloseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../../../contexts/WebSocketContext';

interface EmergencyAlert {
  id: string;
  type: 'urgent_order' | 'customer_emergency' | 'driver_emergency' | 'gas_leak';
  title: string;
  description: string;
  priority: 'high' | 'critical';
  timestamp: string;
  orderId?: number;
  customerId?: number;
  driverId?: number;
  location?: {
    lat: number;
    lng: number;
    address: string;
  };
}

interface EmergencyAlertBannerProps {
  onAlertClick?: (alert: EmergencyAlert) => void;
}

const EmergencyAlertBanner: React.FC<EmergencyAlertBannerProps> = ({ onAlertClick }) => {
  const { t } = useTranslation();
  const { socket, isConnected } = useWebSocket();
  const [alerts, setAlerts] = useState<EmergencyAlert[]>([]);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!socket || !isConnected) return;

    // Subscribe to emergency alerts
    const handleEmergencyAlert = (data: any) => {
      const newAlert: EmergencyAlert = {
        id: data.id || `alert-${Date.now()}`,
        type: data.type,
        title: data.title,
        description: data.description,
        priority: data.priority || 'high',
        timestamp: data.timestamp || new Date().toISOString(),
        orderId: data.orderId,
        customerId: data.customerId,
        driverId: data.driverId,
        location: data.location,
      };

      setAlerts(prev => [
        newAlert,
        ...prev.filter(a => a.id !== newAlert.id),
      ]);
    };

    // Listen for emergency events
    socket.on('dispatch:emergency', handleEmergencyAlert);
    socket.on('emergency:new', handleEmergencyAlert);
    socket.on('emergency:update', handleEmergencyAlert);

    return () => {
      socket.off('dispatch:emergency', handleEmergencyAlert);
      socket.off('emergency:new', handleEmergencyAlert);
      socket.off('emergency:update', handleEmergencyAlert);
    };
  }, [socket, isConnected]);

  const handleDismiss = (alertId: string) => {
    setDismissedAlerts(prev => new Set(prev).add(alertId));
  };

  const visibleAlerts = alerts.filter(alert => !dismissedAlerts.has(alert.id));

  if (visibleAlerts.length === 0) {
    return null;
  }

  const getAlertType = (alert: EmergencyAlert) => {
    switch (alert.priority) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      default:
        return 'warning';
    }
  };

  const getAlertIcon = (type: EmergencyAlert['type']) => {
    switch (type) {
      case 'gas_leak':
        return '🔥';
      case 'customer_emergency':
        return '🚨';
      case 'driver_emergency':
        return '🚑';
      case 'urgent_order':
      default:
        return '⚡';
    }
  };

  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, 
      left: 0, 
      right: 0, 
      zIndex: 1000,
      padding: '8px 16px',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
    }}>
      {visibleAlerts.map(alert => (
        <Alert
          key={alert.id}
          message={
            <Space>
              <span style={{ fontSize: 20 }}>{getAlertIcon(alert.type)}</span>
              <strong>{alert.title}</strong>
              {alert.priority === 'critical' && (
                <Badge count={t('dispatch.emergency.critical')} style={{ backgroundColor: '#ff4d4f' }} />
              )}
            </Space>
          }
          description={
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <span>{alert.description}</span>
              <Space>
                {onAlertClick && (
                  <Button 
                    type="primary" 
                    size="small"
                    onClick={() => onAlertClick(alert)}
                  >
                    {t('dispatch.emergency.handle')}
                  </Button>
                )}
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={() => handleDismiss(alert.id)}
                />
              </Space>
            </Space>
          }
          type={getAlertType(alert)}
          showIcon
          icon={<ExclamationCircleOutlined />}
          style={{ marginBottom: 8 }}
        />
      ))}
    </div>
  );
};

export default EmergencyAlertBanner;