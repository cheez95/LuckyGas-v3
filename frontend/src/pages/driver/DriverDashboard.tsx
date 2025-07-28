import React, { useState, useEffect } from 'react';
import { Card, Button, Badge, Space, Statistic, Row, Col, List, Avatar, Tag, Drawer } from 'antd';
import { 
  CarOutlined, 
  CheckCircleOutlined, 
  ClockCircleOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  MenuOutlined,
  SyncOutlined,
  WifiOutlined,
  DisconnectOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import GPSTracker from './components/GPSTracker';
import { Position } from '../../services/gps.service';
import MobileDriverInterface from '../../components/driver/mobile/MobileDriverInterface';
import './DriverDashboard.css';

interface Route {
  id: string;
  name: string;
  deliveryCount: number;
  completedCount: number;
  estimatedTime: string;
  distance: number;
  status: 'pending' | 'in_progress' | 'completed';
}

interface DeliveryStats {
  total: number;
  completed: number;
  pending: number;
  failed: number;
}

const DriverDashboard: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [routes, setRoutes] = useState<Route[]>([]);
  const [stats, setStats] = useState<DeliveryStats>({
    total: 0,
    completed: 0,
    pending: 0,
    failed: 0
  });
  const [loading, setLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error'>('idle');
  const [currentPosition, setCurrentPosition] = useState<Position | null>(null);

  // Mobile detection
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Check if device is mobile
    const checkMobile = () => {
      const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
      const mobileRegex = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i;
      const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      const isSmallScreen = window.innerWidth <= 768;
      
      setIsMobile(mobileRegex.test(userAgent.toLowerCase()) || (isTouch && isSmallScreen));
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  }, []);

  useEffect(() => {
    fetchTodayRoutes();
    fetchDeliveryStats();
    
    // Monitor online status
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const fetchTodayRoutes = async () => {
    setLoading(true);
    try {
      const response = await api.get('/driver/routes/today');
      setRoutes(response.data);
    } catch (error) {
      console.error('Failed to fetch routes:', error);
      // Load from local storage if offline
      const cachedRoutes = localStorage.getItem('driver_routes_cache');
      if (cachedRoutes) {
        setRoutes(JSON.parse(cachedRoutes));
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchDeliveryStats = async () => {
    try {
      const response = await api.get('/driver/stats/today');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleStartRoute = (routeId: string) => {
    navigate(`/driver/route/${routeId}`);
  };

  const handleSync = async () => {
    setSyncStatus('syncing');
    try {
      // Sync offline data
      await api.post('/driver/sync');
      setSyncStatus('idle');
      fetchTodayRoutes();
      fetchDeliveryStats();
    } catch (error) {
      setSyncStatus('error');
      setTimeout(() => setSyncStatus('idle'), 3000);
    }
  };

  const handlePositionUpdate = async (position: Position) => {
    setCurrentPosition(position);
    
    // Send position to backend if online
    if (isOnline) {
      try {
        await api.post('/driver/location', {
          latitude: position.latitude,
          longitude: position.longitude,
          accuracy: position.accuracy,
          timestamp: position.timestamp,
          speed: position.speed,
          heading: position.heading
        });
      } catch (error) {
        console.error('Failed to update location:', error);
        // Store in local storage for later sync
        const storedPositions = JSON.parse(localStorage.getItem('pendingPositions') || '[]');
        storedPositions.push(position);
        localStorage.setItem('pendingPositions', JSON.stringify(storedPositions));
      }
    }
  };

  const getRouteStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'green';
      case 'in_progress': return 'blue';
      default: return 'default';
    }
  };

  // Render mobile interface if on mobile device
  if (isMobile) {
    return <MobileDriverInterface />;
  }

  // Desktop interface
  return (
    <div className="driver-dashboard">
      {/* Mobile Header */}
      <div className="driver-mobile-header" data-testid="driver-mobile-header">
        <div className="header-content">
          <Button 
            icon={<MenuOutlined />} 
            type="text"
            onClick={() => setDrawerVisible(true)}
            className="menu-button"
          />
          <h2>{t('driver.dashboard.title')}</h2>
          <Space>
            {isOnline ? (
              <WifiOutlined style={{ color: '#52c41a', fontSize: '18px' }} />
            ) : (
              <DisconnectOutlined style={{ color: '#ff4d4f', fontSize: '18px' }} />
            )}
            {syncStatus === 'syncing' && (
              <SyncOutlined spin style={{ fontSize: '18px' }} />
            )}
          </Space>
        </div>
        {!isOnline && (
          <div className="offline-mode-banner" data-testid="offline-mode-banner">
            {t('driver.offline.message')}
          </div>
        )}
      </div>

      {/* Delivery Summary */}
      <Card className="delivery-summary-card" data-testid="delivery-summary">
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic
              title={t('driver.stats.total')}
              value={stats.total}
              prefix={<CarOutlined />}
              data-testid="total-deliveries"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('driver.stats.completed')}
              value={stats.completed}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
              data-testid="completed-deliveries"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('driver.stats.pending')}
              value={stats.pending}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ClockCircleOutlined />}
              data-testid="pending-deliveries"
            />
          </Col>
          <Col span={6}>
            <Button
              type="primary"
              block
              size="large"
              onClick={handleSync}
              loading={syncStatus === 'syncing'}
              style={{ marginTop: 8 }}
            >
              {t('driver.sync')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* GPS Tracking */}
      <Card className="gps-tracker-card" style={{ marginBottom: 16 }}>
        <GPSTracker 
          onPositionUpdate={handlePositionUpdate}
          autoStart={false}
          showDetails={true}
        />
      </Card>

      {/* Today's Routes */}
      <Card 
        title={t('driver.routes.today')}
        className="routes-card"
        data-testid="today-routes"
      >
        <List
          loading={loading}
          dataSource={routes}
          renderItem={(route) => (
            <List.Item
              className="route-item"
              data-testid="route-item"
              onClick={() => handleStartRoute(route.id)}
            >
              <List.Item.Meta
                avatar={
                  <Avatar
                    size="large"
                    style={{ backgroundColor: '#1890ff' }}
                  >
                    {route.name.charAt(0)}
                  </Avatar>
                }
                title={
                  <Space>
                    <span data-testid="route-name">{route.name}</span>
                    <Tag color={getRouteStatusColor(route.status)}>
                      {t(`driver.routes.status.${route.status}`)}
                    </Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={0}>
                    <span data-testid="delivery-count">
                      {t('driver.routes.deliveries', { 
                        completed: route.completedCount, 
                        total: route.deliveryCount 
                      })}
                    </span>
                    <Space>
                      <ClockCircleOutlined />
                      <span data-testid="estimated-time">{route.estimatedTime}</span>
                      <EnvironmentOutlined />
                      <span>{route.distance} km</span>
                    </Space>
                  </Space>
                }
              />
              <Button
                type="primary"
                size="large"
                className="start-route-button"
                data-testid="start-route-button"
                disabled={route.status === 'completed'}
              >
                {route.status === 'in_progress' 
                  ? t('driver.routes.continue') 
                  : t('driver.routes.start')
                }
              </Button>
            </List.Item>
          )}
        />
      </Card>

      {/* Side Drawer Menu */}
      <Drawer
        title={t('driver.menu.title')}
        placement="left"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={280}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Button 
            block 
            size="large"
            icon={<CarOutlined />}
            onClick={() => {
              setDrawerVisible(false);
              navigate('/driver/routes/completed');
            }}
          >
            {t('driver.menu.completedRoutes')}
          </Button>
          <Button 
            block 
            size="large"
            icon={<PhoneOutlined />}
            onClick={() => {
              setDrawerVisible(false);
              navigate('/driver/communication');
            }}
            data-testid="office-chat-button"
          >
            {t('driver.menu.contactOffice')}
          </Button>
          <Button 
            block 
            size="large"
            onClick={() => {
              setDrawerVisible(false);
              navigate('/driver/cylinder-return');
            }}
          >
            {t('driver.menu.cylinderReturn')}
          </Button>
          <Button 
            block 
            size="large"
            danger
            onClick={() => {
              // Clock out logic
              navigate('/driver/clock-out');
            }}
            data-testid="clock-out-button"
          >
            {t('driver.menu.clockOut')}
          </Button>
        </Space>
      </Drawer>
    </div>
  );
};

export default DriverDashboard;