import React, { useEffect, useState, useRef } from 'react';
import { Card, List, Tag, Progress, Space, Badge, Avatar, Typography, Empty, Button, Tooltip } from 'antd';
import {
  EnvironmentOutlined,
  
  UserOutlined,
  PhoneOutlined,
  CarOutlined,
  
  ExclamationCircleOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useWebSocketContext } from '../../../contexts/WebSocketContext';
import { useNavigate } from 'react-router-dom';

const { Text, Title } = Typography;

interface RouteProgress {
  routeId: number;
  routeNumber: string;
  driverId: number;
  driverName: string;
  driverPhone: string;
  vehicleNumber: string;
  totalStops: number;
  completedStops: number;
  currentStop?: {
    orderId: number;
    customerName: string;
    address: string;
    estimatedArrival: string;
    products: string;
  };
  status: 'not_started' | 'in_progress' | 'delayed' | 'completed';
  startTime: string;
  estimatedEndTime: string;
  lastUpdate: string;
  currentLocation?: {
    lat: number;
    lng: number;
    speed: number;
    heading: number;
  };
  delays?: number;
  incidents?: number;
}

interface LiveRouteTrackerProps {
  onRouteClick?: (routeId: number) => void;
  maxHeight?: string;
}

const LiveRouteTracker: React.FC<LiveRouteTrackerProps> = ({ onRouteClick, maxHeight = '600px' }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { socket, isConnected } = useWebSocketContext();
  const [activeRoutes, setActiveRoutes] = useState<RouteProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const updateIntervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    fetchActiveRoutes();
    
    // Set up periodic refresh
    updateIntervalRef.current = window.setInterval(() => {
      fetchActiveRoutes();
    }, 30000); // Refresh every 30 seconds

    return () => {
      if (updateIntervalRef.current) {
        window.clearInterval(updateIntervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!socket || !isConnected) return;

    // Listen for real-time route updates
    const handleRouteUpdate = (data: any) => {
      setActiveRoutes(prev => {
        const index = prev.findIndex(r => r.routeId === data.routeId);
        if (index >= 0) {
          const updated = [...prev];
          updated[index] = { ...updated[index], ...data };
          return updated;
        }
        return [...prev, data];
      });
    };

    const handleLocationUpdate = (data: any) => {
      setActiveRoutes(prev => {
        const index = prev.findIndex(r => r.driverId === data.driverId);
        if (index >= 0) {
          const updated = [...prev];
          updated[index] = {
            ...updated[index],
            currentLocation: data.location,
            lastUpdate: new Date().toISOString(),
          };
          return updated;
        }
        return prev;
      });
    };

    socket.on('route:progress:update', handleRouteUpdate);
    socket.on('driver:location:update', handleLocationUpdate);
    socket.on('route:status:change', handleRouteUpdate);

    return () => {
      socket.off('route:progress:update', handleRouteUpdate);
      socket.off('driver:location:update', handleLocationUpdate);
      socket.off('route:status:change', handleRouteUpdate);
    };
  }, [socket, isConnected]);

  const fetchActiveRoutes = async () => {
    setLoading(true);
    try {
      // Mock data for demonstration
      const mockRoutes: RouteProgress[] = [
        {
          routeId: 1,
          routeNumber: 'RT-2024-0126-001',
          driverId: 101,
          driverName: '張師傅',
          driverPhone: '0912-345-678',
          vehicleNumber: 'TPE-123',
          totalStops: 15,
          completedStops: 8,
          currentStop: {
            orderId: 1234,
            customerName: '王小明餐廳',
            address: '台北市信義區信義路五段123號',
            estimatedArrival: new Date(Date.now() + 15 * 60000).toISOString(),
            products: '50kg×2, 20kg×1',
          },
          status: 'in_progress',
          startTime: new Date(Date.now() - 2 * 3600000).toISOString(),
          estimatedEndTime: new Date(Date.now() + 3 * 3600000).toISOString(),
          lastUpdate: new Date().toISOString(),
          currentLocation: {
            lat: 25.0330,
            lng: 121.5654,
            speed: 28.5,
            heading: 45,
          },
        },
        {
          routeId: 2,
          routeNumber: 'RT-2024-0126-002',
          driverId: 102,
          driverName: '李師傅',
          driverPhone: '0923-456-789',
          vehicleNumber: 'TPE-456',
          totalStops: 12,
          completedStops: 3,
          currentStop: {
            orderId: 1235,
            customerName: '幸福美食',
            address: '台北市大安區復興南路二段456號',
            estimatedArrival: new Date(Date.now() + 25 * 60000).toISOString(),
            products: '20kg×3',
          },
          status: 'delayed',
          startTime: new Date(Date.now() - 1.5 * 3600000).toISOString(),
          estimatedEndTime: new Date(Date.now() + 4 * 3600000).toISOString(),
          lastUpdate: new Date().toISOString(),
          delays: 2,
          currentLocation: {
            lat: 25.0261,
            lng: 121.5435,
            speed: 0,
            heading: 180,
          },
        },
      ];
      setActiveRoutes(mockRoutes);
    } catch (error) {
      console.error('Error fetching active routes:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRouteStatus = (route: RouteProgress) => {
    const progress = (route.completedStops / route.totalStops) * 100;
    if (route.status === 'completed') {
      return { color: 'green', text: t('dispatch.dashboard.completed') };
    } else if (route.status === 'delayed') {
      return { color: 'red', text: t('dispatch.dashboard.delayed') };
    } else if (progress > 0) {
      return { color: 'blue', text: t('dispatch.dashboard.inProgress') };
    } else {
      return { color: 'default', text: t('dispatch.dashboard.notStarted') };
    }
  };

  const getTimeRemaining = (endTime: string) => {
    const remaining = new Date(endTime).getTime() - Date.now();
    if (remaining <= 0) return t('dispatch.dashboard.overdue');
    
    const hours = Math.floor(remaining / 3600000);
    const minutes = Math.floor((remaining % 3600000) / 60000);
    
    if (hours > 0) {
      return t('dispatch.dashboard.hoursMinutesRemaining', { hours, minutes });
    } else {
      return t('dispatch.dashboard.minutesRemaining', { minutes });
    }
  };

  const handleViewRoute = (routeId: number) => {
    if (onRouteClick) {
      onRouteClick(routeId);
    } else {
      navigate(`/routes/track/${routeId}`);
    }
  };

  if (loading) {
    return (
      <Card loading title={t('dispatch.dashboard.liveTracking')} />
    );
  }

  return (
    <Card
      title={
        <Space>
          <Badge status="processing" />
          <Title level={5} style={{ margin: 0 }}>
            {t('dispatch.dashboard.liveTracking')}
          </Title>
          <Text type="secondary">({activeRoutes.length} {t('dispatch.dashboard.activeRoutes')})</Text>
        </Space>
      }
      extra={
        <Button
          type="text"
          icon={<ReloadOutlined />}
          onClick={fetchActiveRoutes}
        >
          {t('common.action.refresh')}
        </Button>
      }
      bodyStyle={{ padding: 0 }}
    >
      {activeRoutes.length === 0 ? (
        <Empty
          description={t('dispatch.dashboard.noActiveRoutes')}
          style={{ padding: '40px 0' }}
        />
      ) : (
        <List
          dataSource={activeRoutes}
          style={{ maxHeight, overflow: 'auto' }}
          renderItem={(route) => {
            const status = getRouteStatus(route);
            const progress = (route.completedStops / route.totalStops) * 100;
            
            return (
              <List.Item
                key={route.routeId}
                style={{ padding: '16px 24px' }}
                actions={[
                  <Tooltip title={t('dispatch.dashboard.viewDetails')}>
                    <Button
                      type="link"
                      icon={<EyeOutlined />}
                      onClick={() => handleViewRoute(route.routeId)}
                    />
                  </Tooltip>,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar
                      icon={<CarOutlined />}
                      style={{ backgroundColor: status.color === 'blue' ? '#1890ff' : '#d9d9d9' }}
                    />
                  }
                  title={
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Space>
                        <Text strong>{route.routeNumber}</Text>
                        <Tag color={status.color}>{status.text}</Tag>
                        {route.delays && route.delays > 0 && (
                          <Tag color="red" icon={<ExclamationCircleOutlined />}>
                            {route.delays} {t('dispatch.dashboard.delays')}
                          </Tag>
                        )}
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {getTimeRemaining(route.estimatedEndTime)}
                      </Text>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" style={{ width: '100%' }} size="small">
                      {/* Driver Info */}
                      <Space split="•">
                        <Space size="small">
                          <UserOutlined />
                          <Text>{route.driverName}</Text>
                        </Space>
                        <Space size="small">
                          <PhoneOutlined />
                          <Text>{route.driverPhone}</Text>
                        </Space>
                        <Space size="small">
                          <CarOutlined />
                          <Text>{route.vehicleNumber}</Text>
                        </Space>
                        {route.currentLocation && (
                          <Text type="secondary">
                            {route.currentLocation.speed.toFixed(1)} km/h
                          </Text>
                        )}
                      </Space>
                      
                      {/* Progress */}
                      <div>
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Text>
                            {t('dispatch.dashboard.progress')}: {route.completedStops}/{route.totalStops} {t('dispatch.dashboard.stops')}
                          </Text>
                          <Text strong>{progress.toFixed(0)}%</Text>
                        </Space>
                        <Progress
                          percent={progress}
                          strokeColor={status.color === 'delayed' ? '#ff4d4f' : '#1890ff'}
                          showInfo={false}
                          size="small"
                        />
                      </div>
                      
                      {/* Current Stop */}
                      {route.currentStop && (
                        <Card size="small" style={{ backgroundColor: '#f5f5f5' }}>
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
                            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                              <Text strong>{t('dispatch.dashboard.currentStop')}</Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {t('dispatch.dashboard.eta')}: {new Date(route.currentStop.estimatedArrival).toLocaleTimeString('zh-TW', {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </Text>
                            </Space>
                            <Space size="small">
                              <EnvironmentOutlined />
                              <Text>{route.currentStop.customerName}</Text>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {route.currentStop.address}
                            </Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {route.currentStop.products}
                            </Text>
                          </Space>
                        </Card>
                      )}
                      
                      {/* Last Update */}
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {t('dispatch.dashboard.lastUpdate')}: {new Date(route.lastUpdate).toLocaleTimeString('zh-TW')}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </Card>
  );
};

export default LiveRouteTracker;