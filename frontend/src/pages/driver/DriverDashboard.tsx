import React, { useState, useEffect } from 'react';
import { Card, Button, Badge, List, Avatar, Typography, Space, Progress, Statistic } from 'antd';
import {
  EnvironmentOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CarOutlined,
  PhoneOutlined,
  QrcodeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import { useAuth } from '../../contexts/AuthContext';

const { Title, Text } = Typography;

interface RouteStop {
  id: string;
  sequence: number;
  customer_name: string;
  address: string;
  phone: string;
  cylinder_count: number;
  cylinder_type: string;
  status: 'pending' | 'arrived' | 'delivered';
  estimated_arrival: string;
  notes?: string;
}

interface ActiveRoute {
  id: string;
  date: string;
  status: 'assigned' | 'in_progress' | 'completed';
  total_stops: number;
  completed_stops: number;
  total_distance: number;
  estimated_duration: number;
  stops: RouteStop[];
}

const DriverDashboard: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { lastMessage, sendMessage } = useWebSocketContext();
  const [activeRoute, setActiveRoute] = useState<ActiveRoute | null>(null);
  const [currentStop, setCurrentStop] = useState<RouteStop | null>(null);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    // Load active route
    loadActiveRoute();
    
    // Start location tracking
    if ('geolocation' in navigator) {
      const watchId = navigator.geolocation.watchPosition(
        (position) => {
          sendMessage({
            type: 'driver.location',
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            speed: position.coords.speed || 0,
            heading: position.coords.heading || 0,
          });
        },
        (error) => {
          console.error('Location error:', error);
        },
        {
          enableHighAccuracy: true,
          maximumAge: 0,
          timeout: 5000,
        }
      );

      return () => {
        navigator.geolocation.clearWatch(watchId);
      };
    }
  }, [sendMessage]);

  useEffect(() => {
    // Handle WebSocket messages
    if (lastMessage) {
      switch (lastMessage.type) {
        case 'route.assigned':
          loadActiveRoute();
          break;
        case 'route.updated':
          if (lastMessage.route_id === activeRoute?.id) {
            loadActiveRoute();
          }
          break;
      }
    }
  }, [lastMessage, activeRoute]);

  const loadActiveRoute = async () => {
    // TODO: Fetch from API
    const mockRoute: ActiveRoute = {
      id: 'R-20250722-01',
      date: new Date().toISOString().split('T')[0],
      status: 'in_progress',
      total_stops: 15,
      completed_stops: 5,
      total_distance: 45.8,
      estimated_duration: 240,
      stops: [
        {
          id: 'S001',
          sequence: 1,
          customer_name: '王小明',
          address: '台北市大安區和平東路一段129號',
          phone: '0912-345-678',
          cylinder_count: 2,
          cylinder_type: '20kg',
          status: 'delivered',
          estimated_arrival: '09:00',
        },
        {
          id: 'S002',
          sequence: 2,
          customer_name: '李美華',
          address: '台北市大安區信義路四段265號',
          phone: '0923-456-789',
          cylinder_count: 1,
          cylinder_type: '16kg',
          status: 'arrived',
          estimated_arrival: '09:30',
          notes: '請按門鈴，狗會叫但不咬人',
        },
        {
          id: 'S003',
          sequence: 3,
          customer_name: '張大同',
          address: '台北市大安區忠孝東路四段181號',
          phone: '0934-567-890',
          cylinder_count: 3,
          cylinder_type: '20kg',
          status: 'pending',
          estimated_arrival: '10:00',
        },
      ],
    };
    
    setActiveRoute(mockRoute);
    setCurrentStop(mockRoute.stops.find(s => s.status === 'arrived') || mockRoute.stops.find(s => s.status === 'pending') || null);
  };

  const handleStartRoute = () => {
    sendMessage({
      type: 'route.started',
      route_id: activeRoute?.id,
    });
    navigate('/driver/navigation');
  };

  const handleScanDelivery = () => {
    navigate('/driver/scan');
  };

  const handleCallCustomer = (phone: string) => {
    window.location.href = `tel:${phone}`;
  };

  const handleNavigateToStop = (stop: RouteStop) => {
    navigate('/driver/navigation', { state: { stop } });
  };

  const completionRate = activeRoute 
    ? Math.round((activeRoute.completed_stops / activeRoute.total_stops) * 100)
    : 0;

  return (
    <div style={{ padding: '16px', backgroundColor: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header Status */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Avatar style={{ backgroundColor: '#1890ff' }}>
              {user?.name?.charAt(0) || 'D'}
            </Avatar>
            <div>
              <Text strong>{user?.name || '司機'}</Text>
              <br />
              <Badge status={isOnline ? 'success' : 'default'} text={isOnline ? '上線' : '離線'} />
            </div>
          </Space>
          <Button 
            type={isOnline ? 'default' : 'primary'}
            onClick={() => setIsOnline(!isOnline)}
          >
            {isOnline ? '結束上線' : '開始上線'}
          </Button>
        </Space>
      </Card>

      {/* Today's Route Summary */}
      {activeRoute && (
        <Card 
          title={<Space><CarOutlined /> 今日路線</Space>}
          extra={
            <Button type="primary" onClick={handleStartRoute}>
              開始配送
            </Button>
          }
          style={{ marginBottom: 16 }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Progress percent={completionRate} status="active" />
            <Space wrap>
              <Statistic 
                title="總站點" 
                value={activeRoute.total_stops} 
                suffix="站" 
              />
              <Statistic 
                title="已完成" 
                value={activeRoute.completed_stops} 
                suffix="站" 
              />
              <Statistic 
                title="總距離" 
                value={activeRoute.total_distance} 
                suffix="公里" 
                precision={1}
              />
              <Statistic 
                title="預計時間" 
                value={Math.round(activeRoute.estimated_duration / 60)} 
                suffix="小時" 
                precision={1}
              />
            </Space>
          </Space>
        </Card>
      )}

      {/* Current Stop */}
      {currentStop && (
        <Card 
          title={<Space><EnvironmentOutlined /> 當前配送點</Space>}
          style={{ marginBottom: 16 }}
          actions={[
            <Button 
              type="primary" 
              icon={<EnvironmentOutlined />}
              onClick={() => handleNavigateToStop(currentStop)}
            >
              導航
            </Button>,
            <Button 
              icon={<QrcodeOutlined />}
              onClick={handleScanDelivery}
            >
              掃描確認
            </Button>,
            <Button 
              icon={<PhoneOutlined />}
              onClick={() => handleCallCustomer(currentStop.phone)}
            >
              聯絡客戶
            </Button>,
          ]}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Title level={5}>{currentStop.customer_name}</Title>
            <Text>{currentStop.address}</Text>
            <Space>
              <Text type="secondary">
                <ClockCircleOutlined /> 預計 {currentStop.estimated_arrival}
              </Text>
              <Text strong>
                {currentStop.cylinder_count} x {currentStop.cylinder_type}
              </Text>
            </Space>
            {currentStop.notes && (
              <Text type="warning">備註：{currentStop.notes}</Text>
            )}
          </Space>
        </Card>
      )}

      {/* Route Stops List */}
      {activeRoute && (
        <Card title="配送站點列表">
          <List
            dataSource={activeRoute.stops}
            renderItem={(stop) => (
              <List.Item
                onClick={() => stop.status === 'pending' && handleNavigateToStop(stop)}
                style={{ 
                  cursor: stop.status === 'pending' ? 'pointer' : 'default',
                  opacity: stop.status === 'delivered' ? 0.6 : 1,
                }}
              >
                <List.Item.Meta
                  avatar={
                    <Badge count={stop.sequence}>
                      <Avatar 
                        icon={stop.status === 'delivered' ? <CheckCircleOutlined /> : <EnvironmentOutlined />}
                        style={{ 
                          backgroundColor: stop.status === 'delivered' ? '#52c41a' : 
                                         stop.status === 'arrived' ? '#faad14' : '#1890ff' 
                        }}
                      />
                    </Badge>
                  }
                  title={
                    <Space>
                      <Text strong>{stop.customer_name}</Text>
                      <Text type="secondary">
                        {stop.cylinder_count} x {stop.cylinder_type}
                      </Text>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={0}>
                      <Text>{stop.address}</Text>
                      <Text type="secondary">
                        <ClockCircleOutlined /> {stop.estimated_arrival}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
};

export default DriverDashboard;