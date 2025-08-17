import React, { useState, useEffect, useMemo } from 'react';
import { Card, Row, Col, Statistic, Badge, List, Tag, Progress, Alert, Space, Avatar, Tooltip } from 'antd';
import {
  ShoppingCartOutlined,
  CarOutlined,
  UserOutlined,
  DollarOutlined,
  RiseOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TruckOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '../../hooks/useWebSocket';
import { GoogleMap, Marker, InfoWindow } from '@react-google-maps/api';
import moment from 'moment';
import 'moment/locale/zh-tw';

moment.locale('zh-tw');

interface DashboardStats {
  todayOrders: number;
  activeDeliveries: number;
  completedDeliveries: number;
  totalRevenue: number;
  activeDrivers: number;
  pendingOrders: number;
}

interface ActiveDriver {
  id: string;
  name: string;
  location: {
    lat: number;
    lng: number;
  };
  status: 'idle' | 'driving' | 'delivering';
  currentOrder?: string;
  routeProgress: number;
  lastUpdate: string;
}

interface RecentActivity {
  id: string;
  type: 'order' | 'delivery' | 'alert';
  title: string;
  description: string;
  timestamp: string;
  severity?: 'info' | 'warning' | 'success' | 'error';
}

const RealtimeDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    todayOrders: 0,
    activeDeliveries: 0,
    completedDeliveries: 0,
    totalRevenue: 0,
    activeDrivers: 0,
    pendingOrders: 0,
  });

  const [activeDrivers, setActiveDrivers] = useState<ActiveDriver[]>([]);
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
  const [selectedDriver, setSelectedDriver] = useState<string | null>(null);
  const [mapCenter, setMapCenter] = useState({ lat: 25.0330, lng: 121.5654 }); // Taipei

  const { isConnected, lastMessage, subscribe } = useWebSocket({
    endpoint: 'ws/office',
    onMessage: handleWebSocketMessage,
  });

  // Handle WebSocket messages
  function handleWebSocketMessage(message: any) {
    switch (message.type) {
      case 'order.created':
        setStats(prev => ({
          ...prev,
          todayOrders: prev.todayOrders + 1,
          pendingOrders: prev.pendingOrders + 1,
        }));
        addActivity({
          id: message.order_id,
          type: 'order',
          title: '新訂單',
          description: `來自 ${message.customer_name} 的新訂單`,
          timestamp: message.timestamp,
          severity: 'info',
        });
        break;

      case 'order.assigned':
        setStats(prev => ({
          ...prev,
          pendingOrders: Math.max(0, prev.pendingOrders - 1),
          activeDeliveries: prev.activeDeliveries + 1,
        }));
        break;

      case 'order.delivered':
        setStats(prev => ({
          ...prev,
          activeDeliveries: Math.max(0, prev.activeDeliveries - 1),
          completedDeliveries: prev.completedDeliveries + 1,
        }));
        addActivity({
          id: message.order_id,
          type: 'delivery',
          title: '訂單完成',
          description: `訂單 #${message.order_id} 已送達`,
          timestamp: message.timestamp,
          severity: 'success',
        });
        break;

      case 'driver.location':
        updateDriverLocation(message.driver_id, {
          lat: message.latitude,
          lng: message.longitude,
        });
        break;

      case 'driver.status':
        updateDriverStatus(message.driver_id, message.status);
        break;

      case 'system.alert':
        addActivity({
          id: `alert-${Date.now()}`,
          type: 'alert',
          title: '系統提醒',
          description: message.message,
          timestamp: message.timestamp,
          severity: message.severity || 'warning',
        });
        break;
    }
  }

  // Update driver location
  const updateDriverLocation = (driverId: string, location: { lat: number; lng: number }) => {
    setActiveDrivers(prev =>
      prev.map(driver =>
        driver.id === driverId
          ? { ...driver, location, lastUpdate: moment().toISOString() }
          : driver
      )
    );
  };

  // Update driver status
  const updateDriverStatus = (driverId: string, status: string) => {
    setActiveDrivers(prev =>
      prev.map(driver =>
        driver.id === driverId
          ? { ...driver, status: status as any }
          : driver
      )
    );
  };

  // Add activity to recent list
  const addActivity = (activity: RecentActivity) => {
    setRecentActivities(prev => [activity, ...prev].slice(0, 10)); // Keep last 10
  };

  // Subscribe to channels
  useEffect(() => {
    if (isConnected) {
      subscribe('orders');
      subscribe('drivers');
      subscribe('system');
    }
  }, [isConnected, subscribe]);

  // Fetch initial data
  useEffect(() => {
    fetchDashboardData();
    const interval = window.setInterval(fetchDashboardData, 60000); // Refresh every minute
    return () => window.clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('/api/v1/analytics/dashboard/realtime', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setStats(data.stats);
        setActiveDrivers(data.activeDrivers);
        setRecentActivities(data.recentActivities);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
  };

  // Get driver marker icon based on status
  const getDriverIcon = (status: string) => {
    const icons = {
      idle: '/images/driver-idle.png',
      driving: '/images/driver-moving.png',
      delivering: '/images/driver-delivering.png',
    };
    return icons[status as keyof typeof icons] || icons.idle;
  };

  // Calculate stats change percentage (mock data)
  const statsChange = useMemo(() => ({
    orders: 12.5,
    revenue: 8.3,
    deliveries: -2.1,
    drivers: 0,
  }), []);

  return (
    <div>
      {/* Connection Status */}
      {!isConnected && (
        <Alert
          message="即時更新已斷線"
          description="目前顯示的資料可能不是最新的"
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="今日訂單"
              value={stats.todayOrders}
              prefix={<ShoppingCartOutlined />}
              suffix={
                <span style={{ fontSize: 14, color: statsChange.orders > 0 ? '#52c41a' : '#ff4d4f' }}>
                  {statsChange.orders > 0 ? '+' : ''}{statsChange.orders}%
                </span>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="進行中配送"
              value={stats.activeDeliveries}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="今日營收"
              value={stats.totalRevenue}
              prefix={<DollarOutlined />}
              suffix="NT$"
              precision={0}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="待處理訂單"
              value={stats.pendingOrders}
              prefix={<ClockCircleOutlined />}
              valueStyle={stats.pendingOrders > 10 ? { color: '#ff4d4f' } : {}}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Real-time Map */}
        <Col xs={24} lg={16}>
          <Card title="司機即時位置" extra={`${stats.activeDrivers} 位司機在線`}>
            <div style={{ height: '500px', width: '100%' }}>
              <GoogleMap
                mapContainerStyle={{ height: '100%', width: '100%' }}
                zoom={12}
                center={mapCenter}
                options={{
                  zoomControl: true,
                  streetViewControl: false,
                  mapTypeControl: false,
                  fullscreenControl: true,
                }}
              >
                {activeDrivers.map(driver => (
                  <Marker
                    key={driver.id}
                    position={driver.location}
                    icon={{
                      url: getDriverIcon(driver.status),
                      scaledSize: new google.maps.Size(40, 40),
                    }}
                    onClick={() => setSelectedDriver(driver.id)}
                  />
                ))}
                
                {selectedDriver && (
                  <InfoWindow
                    position={activeDrivers.find(d => d.id === selectedDriver)?.location!}
                    onCloseClick={() => setSelectedDriver(null)}
                  >
                    <div>
                      <h4>{activeDrivers.find(d => d.id === selectedDriver)?.name}</h4>
                      <p>狀態: {activeDrivers.find(d => d.id === selectedDriver)?.status}</p>
                      <p>進度: {activeDrivers.find(d => d.id === selectedDriver)?.routeProgress}%</p>
                    </div>
                  </InfoWindow>
                )}
              </GoogleMap>
            </div>
          </Card>
        </Col>

        {/* Active Drivers List */}
        <Col xs={24} lg={8}>
          <Card
            title="司機狀態"
            bodyStyle={{ height: '500px', overflow: 'auto' }}
          >
            <List
              dataSource={activeDrivers}
              renderItem={driver => (
                <List.Item key={driver.id}>
                  <List.Item.Meta
                    avatar={
                      <Badge
                        status={
                          driver.status === 'idle' ? 'default' :
                          driver.status === 'driving' ? 'processing' :
                          'success'
                        }
                      >
                        <Avatar icon={<UserOutlined />} />
                      </Badge>
                    }
                    title={driver.name}
                    description={
                      <Space direction="vertical" size={0}>
                        <span>
                          狀態: <Tag color={
                            driver.status === 'idle' ? 'default' :
                            driver.status === 'driving' ? 'blue' :
                            'green'
                          }>
                            {driver.status === 'idle' ? '待命' :
                             driver.status === 'driving' ? '配送中' :
                             '送達中'}
                          </Tag>
                        </span>
                        {driver.currentOrder && (
                          <span>訂單: #{driver.currentOrder}</span>
                        )}
                        <Progress
                          percent={driver.routeProgress}
                          size="small"
                          status="active"
                        />
                        <span style={{ fontSize: 12, color: '#999' }}>
                          更新: {moment(driver.lastUpdate).fromNow()}
                        </span>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Activities */}
      <Card
        title="即時動態"
        style={{ marginTop: 16 }}
        extra={
          <Badge count={recentActivities.length} showZero>
            <ClockCircleOutlined />
          </Badge>
        }
      >
        <List
          dataSource={recentActivities}
          renderItem={activity => (
            <List.Item key={activity.id}>
              <List.Item.Meta
                avatar={
                  <Avatar
                    icon={
                      activity.type === 'order' ? <ShoppingCartOutlined /> :
                      activity.type === 'delivery' ? <CheckCircleOutlined /> :
                      <WarningOutlined />
                    }
                    style={{
                      backgroundColor:
                        activity.severity === 'success' ? '#52c41a' :
                        activity.severity === 'warning' ? '#faad14' :
                        activity.severity === 'error' ? '#ff4d4f' :
                        '#1890ff'
                    }}
                  />
                }
                title={activity.title}
                description={
                  <Space>
                    <span>{activity.description}</span>
                    <span style={{ color: '#999', fontSize: 12 }}>
                      {moment(activity.timestamp).format('HH:mm:ss')}
                    </span>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default RealtimeDashboard;