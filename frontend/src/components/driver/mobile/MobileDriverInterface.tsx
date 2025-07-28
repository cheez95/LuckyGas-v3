import React, { useState, useEffect, useCallback } from 'react';
import { 
  Layout, Card, Button, List, Space, Tag, Progress,
  Modal, message, Drawer, Badge, Typography, Avatar
} from 'antd';
import {
  CheckCircleOutlined, CompassOutlined, NavigationOutlined,
   PhoneOutlined,
  PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined,
  MenuOutlined, UserOutlined, LogoutOutlined
} from '@ant-design/icons';
import { useAuth } from '../../../contexts/AuthContext';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { routeService } from '../../../services/route.service';
import DeliveryCompletionModal from '../DeliveryCompletionModal';
import type { RouteWithDetails, RouteStop as BaseRouteStop } from '../../../services/route.service';
import './MobileDriverInterface.css';

// Extended RouteStop for mobile interface
interface RouteStop extends BaseRouteStop {
  customer_name?: string;
  customer_phone?: string;
  delivery_notes?: string;
  latitude?: number;
  longitude?: number;
}

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const MobileDriverInterface: React.FC = () => {
  const { user, logout } = useAuth();
  
  // State management
  const [loading, setLoading] = useState(true);
  const [route, setRoute] = useState<RouteWithDetails | null>(null);
  const [stops, setStops] = useState<RouteStop[]>([]);
  const [selectedStop, setSelectedStop] = useState<RouteStop | null>(null);
  const [completionModalVisible, setCompletionModalVisible] = useState(false);
  const [routeStarted, setRouteStarted] = useState(false);
  const [locationTracking, setLocationTracking] = useState(false);
  const [watchId, setWatchId] = useState<number | null>(null);
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch driver's route for today
  const fetchRoute = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      // Get today's date
      const today = new Date().toISOString().split('T')[0];
      
      // First get driver's routes for today
      const routes = await routeService.getDriverRoutes(user?.id || 0, today);
      
      if (routes && routes.length > 0) {
        // Get the first route (assuming one route per day)
        const routeId = routes[0].id || 0;
        const todayRoute = await routeService.getDriverRoute(user?.id || 0, routeId);
        
        if (todayRoute) {
          setRoute(todayRoute);
          setRouteStarted(todayRoute.status === 'in_progress');
          
          // Sort stops by sequence
          if (todayRoute.stops) {
            const sortedStops = [...todayRoute.stops].sort((a, b) => a.stop_sequence - b.stop_sequence);
            setStops(sortedStops);
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch route:', error);
      message.error('無法載入路線資料');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user?.id]);

  // WebSocket setup
  const { sendMessage } = useWebSocket({
    endpoint: 'ws/driver',
    onMessage: (wsMessage) => {
      if (wsMessage.type === 'route_update' && wsMessage.data?.route_id === route?.id) {
        fetchRoute(false);
      } else if (wsMessage.type === 'route_assigned') {
        fetchRoute();
        message.info('您有新的配送路線！');
      }
    }
  });

  // Initial load
  useEffect(() => {
    fetchRoute();
  }, [fetchRoute]);

  // Location tracking
  const startLocationTracking = useCallback(() => {
    if (!navigator.geolocation) {
      message.error('您的裝置不支援定位功能');
      return;
    }

    const id = navigator.geolocation.watchPosition(
      (position) => {
        // Send location update via WebSocket
        sendMessage({
          type: 'location_update',
          data: {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: new Date().toISOString()
          }
        });
        
        // Also update via API
        routeService.updateDriverLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }).catch(console.error);
      },
      (error) => {
        console.error('Location error:', error);
        message.error('無法取得您的位置');
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      }
    );

    setWatchId(id);
    setLocationTracking(true);
    message.success('位置追蹤已開啟');
  }, [sendMessage]);

  const stopLocationTracking = useCallback(() => {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      setWatchId(null);
      setLocationTracking(false);
      message.info('位置追蹤已關閉');
    }
  }, [watchId]);

  // Start route
  const handleStartRoute = async () => {
    if (!route) return;
    
    try {
      await routeService.startRoute(route.id);
      setRouteStarted(true);
      startLocationTracking();
      message.success('路線已開始');
    } catch (error) {
      console.error('Failed to start route:', error);
      message.error('無法開始路線');
    }
  };

  // Complete route
  const handleCompleteRoute = async () => {
    if (!route) return;
    
    Modal.confirm({
      title: '確認完成路線？',
      content: '完成後將無法修改配送狀態',
      onOk: async () => {
        try {
          await routeService.completeRoute(route.id);
          stopLocationTracking();
          message.success('路線已完成！');
          fetchRoute();
        } catch (error) {
          console.error('Failed to complete route:', error);
          message.error('無法完成路線');
        }
      },
    });
  };

  // Handle delivery click
  const handleDeliveryClick = (stop: RouteStop) => {
    if (!stop.is_completed && routeStarted) {
      setSelectedStop(stop);
      setCompletionModalVisible(true);
    }
  };

  // Handle delivery completion
  const handleDeliveryComplete = async (data: any) => {
    if (!selectedStop) return;
    
    try {
      await routeService.completeStop(selectedStop.id, {
        signature: data.signature,
        photos: data.photos,
        notes: data.notes,
      });
      
      message.success('配送完成！');
      setCompletionModalVisible(false);
      fetchRoute(false);
    } catch (error) {
      console.error('Failed to complete delivery:', error);
      message.error('無法完成配送');
    }
  };

  // Navigation helper
  const handleNavigation = (stop: RouteStop) => {
    const destination = `${stop.latitude},${stop.longitude}`;
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${destination}`;
    window.open(googleMapsUrl, '_blank');
  };

  const completionRate = route && route.total_orders > 0
    ? Math.round((route.completed_orders / route.total_orders) * 100)
    : 0;

  return (
    <Layout className="mobile-driver-layout">
      <Header className="mobile-header">
        <div className="header-content">
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setSidebarVisible(true)}
            className="menu-button"
          />
          <Title level={4} className="header-title">司機介面</Title>
          <Badge 
            count={route ? route.total_orders - route.completed_orders : 0}
            className="header-badge"
          >
            <Avatar icon={<UserOutlined />} />
          </Badge>
        </div>
      </Header>

      <Content className="mobile-content">
        {loading ? (
          <div className="loading-container">
            <Progress type="circle" percent={0} />
            <Text>載入中...</Text>
          </div>
        ) : !route ? (
          <Card className="empty-state">
            <Text>今日沒有配送路線</Text>
            <Button onClick={() => fetchRoute()} className="refresh-button">
              重新載入
            </Button>
          </Card>
        ) : (
          <>
            {/* Route Summary Card */}
            <Card className="route-summary-card">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div className="route-header">
                  <Text strong>路線 #{route.route_number}</Text>
                  <Tag color={locationTracking ? 'processing' : 'default'}>
                    {locationTracking ? '定位中' : '定位關閉'}
                  </Tag>
                </div>
                
                <Progress 
                  percent={completionRate} 
                  strokeColor="#52c41a"
                  format={() => `${route.completed_orders} / ${route.total_orders}`}
                />
                
                {route.status === 'planned' || route.status === 'optimized' ? (
                  <Button
                    type="primary"
                    size="large"
                    icon={<PlayCircleOutlined />}
                    onClick={handleStartRoute}
                    block
                  >
                    開始配送
                  </Button>
                ) : route.status === 'in_progress' ? (
                  <Space style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      size="large"
                      icon={<CheckCircleOutlined />}
                      onClick={handleCompleteRoute}
                      disabled={route.completed_orders < route.total_orders}
                      style={{ flex: 1 }}
                    >
                      完成路線
                    </Button>
                    <Button
                      size="large"
                      icon={locationTracking ? <PauseCircleOutlined /> : <CompassOutlined />}
                      onClick={locationTracking ? stopLocationTracking : startLocationTracking}
                    >
                      {locationTracking ? '關閉' : '開啟'}定位
                    </Button>
                  </Space>
                ) : (
                  <Tag color="green" style={{ fontSize: 16, padding: '8px 16px' }}>
                    路線已完成
                  </Tag>
                )}
              </Space>
            </Card>

            {/* Delivery Stops List */}
            <List
              className="stops-list"
              dataSource={stops}
              renderItem={(stop) => {
                const isActive = !stop.is_completed && routeStarted;
                const isCompleted = stop.is_completed;
                
                return (
                  <Card
                    className={`stop-card ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
                    onClick={() => handleDeliveryClick(stop)}
                  >
                    <div className="stop-header">
                      <Space>
                        <Badge count={stop.stop_sequence} style={{ backgroundColor: isCompleted ? '#52c41a' : '#1890ff' }} />
                        <Text strong className="customer-name">{stop.customer_name || `訂單 #${stop.order_id}`}</Text>
                      </Space>
                      {isCompleted && <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />}
                    </div>
                    
                    <div className="stop-content">
                      <Text className="address">{stop.address}</Text>
                      
                      {stop.delivery_notes && (
                        <Text type="secondary" className="notes">備註：{stop.delivery_notes}</Text>
                      )}
                      
                      {stop.estimated_arrival && (
                        <Text type="secondary" className="arrival-time">
                          預計：{new Date(stop.estimated_arrival).toLocaleTimeString('zh-TW', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </Text>
                      )}
                    </div>
                    
                    <div className="stop-actions">
                      <Button
                        type="link"
                        icon={<PhoneOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          window.location.href = `tel:${stop.customer_phone}`;
                        }}
                      >
                        撥打
                      </Button>
                      <Button
                        type="link"
                        icon={<NavigationOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigation(stop);
                        }}
                      >
                        導航
                      </Button>
                      {isActive && (
                        <Button
                          type="primary"
                          icon={<CheckCircleOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeliveryClick(stop);
                          }}
                        >
                          完成
                        </Button>
                      )}
                    </div>
                  </Card>
                );
              }}
            />
          </>
        )}
      </Content>

      {/* Sidebar Menu */}
      <Drawer
        title={user?.username || '司機'}
        placement="left"
        onClose={() => setSidebarVisible(false)}
        open={sidebarVisible}
        width={250}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              setSidebarVisible(false);
              setRefreshing(true);
              fetchRoute();
            }}
            block
          >
            重新整理
          </Button>
          <Button
            danger
            icon={<LogoutOutlined />}
            onClick={() => {
              stopLocationTracking();
              logout();
            }}
            block
          >
            登出
          </Button>
        </Space>
      </Drawer>

      {/* Delivery Completion Modal */}
      {selectedStop && (
        <DeliveryCompletionModal
          visible={completionModalVisible}
          stop={selectedStop}
          onComplete={handleDeliveryComplete}
          onCancel={() => {
            setCompletionModalVisible(false);
            setSelectedStop(null);
          }}
        />
      )}
    </Layout>
  );
};

export default MobileDriverInterface;