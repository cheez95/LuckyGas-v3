import React, { useState, useEffect, useCallback } from 'react';
import { 
  Layout, Card, Button, List, Space, Tag, Progress,
  Modal, message, Drawer, Badge, Typography, Avatar,
  Switch, Statistic, Row, Col, Alert
} from 'antd';
import {
  CheckCircleOutlined, CompassOutlined, AimOutlined,
  PhoneOutlined, BatteryFull20Outlined, BatteryFullOutlined,
  PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined,
  MenuOutlined, UserOutlined, LogoutOutlined, WifiOutlined,
  CloudSyncOutlined, EnvironmentOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import { useAuth } from '../../../contexts/AuthContext';
import { useWebSocket } from '../../../hooks/useWebSocket';
import { routeService } from '../../../services/route.service';
import mobileService, { LocationUpdate } from '../../../services/mobile.service';
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

const EnhancedMobileDriverInterface: React.FC = () => {
  const { user, logout } = useAuth();
  
  // State management
  const [loading, setLoading] = useState(true);
  const [route, setRoute] = useState<RouteWithDetails | null>(null);
  const [stops, setStops] = useState<RouteStop[]>([]);
  const [selectedStop, setSelectedStop] = useState<RouteStop | null>(null);
  const [completionModalVisible, setCompletionModalVisible] = useState(false);
  const [routeStarted, setRouteStarted] = useState(false);
  const [locationTracking, setLocationTracking] = useState(false);
  const [backgroundTracking, setBackgroundTracking] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  
  // Mobile-specific state
  const [batteryLevel, setBatteryLevel] = useState(100);
  const [isOnline, setIsOnline] = useState(mobileService.isDeviceOnline());
  const [offlineQueueCount, setOfflineQueueCount] = useState(0);
  const [lastLocationUpdate, setLastLocationUpdate] = useState<Date | null>(null);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<LocationUpdate | null>(null);

  // Initialize mobile service
  useEffect(() => {
    const initializeMobileFeatures = async () => {
      // Register service worker
      await mobileService.registerServiceWorker();
      
      // Request notification permission
      const notificationPermission = await mobileService.requestNotificationPermission();
      setNotificationsEnabled(notificationPermission);
      
      // Monitor battery level
      const updateBatteryLevel = () => {
        setBatteryLevel(mobileService.getBatteryLevel());
      };
      updateBatteryLevel();
      const batteryInterval = window.setInterval(updateBatteryLevel, 30000); // Update every 30s
      
      // Monitor online status
      const handleOnline = () => {
        setIsOnline(true);
        message.success('已恢復網路連線');
      };
      const handleOffline = () => {
        setIsOnline(false);
        message.warning('目前處於離線模式');
      };
      
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
      
      // Monitor offline queue
      const updateOfflineQueue = () => {
        setOfflineQueueCount(mobileService.getOfflineQueueCount());
      };
      updateOfflineQueue();
      const queueInterval = window.setInterval(updateOfflineQueue, 5000); // Check every 5s
      
      return () => {
        window.clearInterval(batteryInterval);
        window.clearInterval(queueInterval);
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    };
    
    initializeMobileFeatures();
  }, []);

  // Fetch driver's route for today
  const fetchRoute = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      const routes = await routeService.getDriverRoutes(user?.id || 0, today);
      
      if (routes && routes.length > 0) {
        const routeId = routes[0].id || 0;
        const todayRoute = await routeService.getDriverRoute(user?.id || 0, routeId);
        
        if (todayRoute) {
          setRoute(todayRoute);
          setRouteStarted(todayRoute.status === 'in_progress');
          
          if (todayRoute.stops) {
            const sortedStops = [...todayRoute.stops].sort((a, b) => a.stop_sequence - b.stop_sequence);
            setStops(sortedStops);
          }
          
          // If route is in progress, resume tracking
          if (todayRoute.status === 'in_progress' && !locationTracking) {
            await startLocationTracking(false);
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch route:', error);
      if (!isOnline) {
        message.info('離線模式：使用快取資料');
      } else {
        message.error('無法載入路線資料');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user?.id, isOnline, locationTracking]);

  // WebSocket setup
  const { sendMessage } = useWebSocket({
    endpoint: 'ws/driver',
    onMessage: (wsMessage) => {
      if (wsMessage.type === 'route_update' && wsMessage.data?.route_id === route?.id) {
        fetchRoute(false);
      } else if (wsMessage.type === 'route_assigned') {
        fetchRoute();
        message.info('您有新的配送路線！');
        if (notificationsEnabled) {
          mobileService.showNotification('新配送路線', {
            body: '您有新的配送任務，請查看詳情',
            tag: 'route-assigned',
          });
        }
      } else if (wsMessage.type === 'emergency_order') {
        message.warning('緊急配送任務！');
        if (notificationsEnabled) {
          mobileService.showNotification('緊急配送', {
            body: '您有緊急配送任務需要處理',
            tag: 'emergency',
            requireInteraction: true,
          });
        }
      }
    }
  });

  // Initial load
  useEffect(() => {
    fetchRoute();
  }, [fetchRoute]);

  // Location tracking handler
  const handleLocationUpdate = useCallback((location: LocationUpdate) => {
    setCurrentLocation(location);
    setLastLocationUpdate(new Date());
    
    // Send via WebSocket if online
    if (isOnline) {
      sendMessage({
        type: 'location_update',
        data: location
      });
    }
    
    // Update route service
    routeService.updateDriverLocation({
      latitude: location.latitude,
      longitude: location.longitude,
    }).catch(error => {
      if (!isOnline) {
        // Will be queued for offline sync
        console.log('Location update queued for offline sync');
      } else {
        console.error('Failed to update location:', error);
      }
    });
  }, [isOnline, sendMessage]);

  // Start location tracking
  const startLocationTracking = useCallback(async (showMessage = true) => {
    const success = await mobileService.startLocationTracking(
      handleLocationUpdate,
      {
        highAccuracy: batteryLevel > 20,
        backgroundMode: backgroundTracking,
        minInterval: backgroundTracking ? 30000 : 15000,
      }
    );
    
    if (success) {
      setLocationTracking(true);
      if (showMessage) {
        message.success('位置追蹤已開啟');
      }
    }
  }, [handleLocationUpdate, batteryLevel, backgroundTracking]);

  // Stop location tracking
  const stopLocationTracking = useCallback(() => {
    mobileService.stopLocationTracking();
    setLocationTracking(false);
    message.info('位置追蹤已關閉');
  }, []);

  // Toggle background tracking
  const toggleBackgroundTracking = async (checked: boolean) => {
    setBackgroundTracking(checked);
    if (locationTracking) {
      // Restart tracking with new settings
      stopLocationTracking();
      await startLocationTracking(false);
    }
  };

  // Start route
  const handleStartRoute = async () => {
    if (!route) return;
    
    try {
      await routeService.startRoute(route.id);
      setRouteStarted(true);
      await startLocationTracking();
      
      // Show notification
      if (notificationsEnabled) {
        mobileService.showNotification('路線已開始', {
          body: `開始配送路線 #${route.route_number}`,
          tag: 'route-started',
        });
      }
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
      if (isOnline) {
        await routeService.completeStop(selectedStop.id, {
          signature: data.signature,
          photos: data.photos,
          notes: data.notes,
        });
        message.success('配送完成！');
      } else {
        // Queue for offline sync
        mobileService.addToOfflineQueue('delivery_completion', {
          deliveryId: selectedStop.id,
          signature: data.signature,
          photos: data.photos,
          notes: data.notes,
          completedAt: new Date().toISOString(),
        });
        message.info('配送已記錄，將在恢復連線後同步');
      }
      
      setCompletionModalVisible(false);
      fetchRoute(false);
    } catch (error) {
      console.error('Failed to complete delivery:', error);
      message.error('無法完成配送');
    }
  };

  // Navigation helper
  const handleNavigation = (stop: RouteStop) => {
    if (stop.latitude && stop.longitude) {
      const destination = `${stop.latitude},${stop.longitude}`;
      const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${destination}`;
      window.open(googleMapsUrl, '_blank');
    } else {
      // Fallback to address
      const encodedAddress = encodeURIComponent(stop.address);
      const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodedAddress}`;
      window.open(googleMapsUrl, '_blank');
    }
  };

  // Sync offline data
  const syncOfflineData = async () => {
    if (!isOnline) {
      message.warning('請在有網路連線時同步');
      return;
    }
    
    message.loading('正在同步離線資料...');
    await mobileService.processOfflineQueue();
    setOfflineQueueCount(mobileService.getOfflineQueueCount());
    message.success('離線資料同步完成');
  };

  // Calculate progress
  const completionRate = route && route.total_orders > 0
    ? Math.round((route.completed_orders / route.total_orders) * 100)
    : 0;

  // Get next stop
  const nextStop = stops.find(stop => !stop.is_completed);

  return (
    <Layout className="enhanced-mobile-driver-layout">
      <Header className="mobile-header">
        <div className="header-content">
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setSidebarVisible(true)}
            className="menu-button"
          />
          <Title level={4} className="header-title">司機介面</Title>
          <Space>
            <Badge dot={!isOnline} offset={[-2, 2]}>
              <WifiOutlined style={{ fontSize: 20, color: isOnline ? '#52c41a' : '#ff4d4f' }} />
            </Badge>
            <Badge count={route ? route.total_orders - route.completed_orders : 0}>
              <Avatar icon={<UserOutlined />} />
            </Badge>
          </Space>
        </div>
      </Header>

      <Content className="mobile-content">
        {/* Status Bar */}
        <Card size="small" className="status-bar">
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="電量"
                value={batteryLevel}
                suffix="%"
                prefix={batteryLevel > 50 ? <BatteryFullOutlined /> : <BatteryFull20Outlined />}
                valueStyle={{ fontSize: 14, color: batteryLevel < 20 ? '#ff4d4f' : undefined }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="離線待同步"
                value={offlineQueueCount}
                valueStyle={{ fontSize: 14 }}
                suffix={
                  offlineQueueCount > 0 && isOnline ? (
                    <Button 
                      size="small" 
                      type="link" 
                      icon={<CloudSyncOutlined />}
                      onClick={syncOfflineData}
                    />
                  ) : null
                }
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="最後定位"
                value={lastLocationUpdate ? 
                  `${Math.floor((new Date().getTime() - lastLocationUpdate.getTime()) / 1000)}秒前` : 
                  '未定位'
                }
                valueStyle={{ fontSize: 14 }}
                prefix={<EnvironmentOutlined />}
              />
            </Col>
          </Row>
        </Card>

        {/* Location tracking settings */}
        {routeStarted && (
          <Card size="small" className="tracking-settings">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text>背景追蹤</Text>
                <Switch
                  checked={backgroundTracking}
                  onChange={toggleBackgroundTracking}
                  checkedChildren="開啟"
                  unCheckedChildren="關閉"
                />
              </div>
              {backgroundTracking && batteryLevel < 30 && (
                <Alert
                  message="電量較低"
                  description="背景追蹤會增加電量消耗"
                  type="warning"
                  showIcon
                  closable
                />
              )}
            </Space>
          </Card>
        )}

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
                  <Space>
                    <Tag color={locationTracking ? 'processing' : 'default'}>
                      {locationTracking ? '定位中' : '定位關閉'}
                    </Tag>
                    {!isOnline && <Tag color="warning">離線模式</Tag>}
                  </Space>
                </div>
                
                <Progress 
                  percent={completionRate} 
                  strokeColor="#52c41a"
                  format={() => `${route.completed_orders} / ${route.total_orders}`}
                />
                
                {nextStop && (
                  <Alert
                    message="下一站"
                    description={`${nextStop.customer_name || `訂單 #${nextStop.order_id}`} - ${nextStop.address}`}
                    type="info"
                    action={
                      <Button 
                        size="small" 
                        icon={<AimOutlined />}
                        onClick={() => handleNavigation(nextStop)}
                      >
                        導航
                      </Button>
                    }
                  />
                )}
                
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
                      onClick={locationTracking ? stopLocationTracking : () => startLocationTracking()}
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
                const isNext = stop === nextStop;
                
                return (
                  <Card
                    className={`stop-card ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''} ${isNext ? 'next' : ''}`}
                    onClick={() => handleDeliveryClick(stop)}
                  >
                    <div className="stop-header">
                      <Space>
                        <Badge 
                          count={stop.stop_sequence} 
                          style={{ 
                            backgroundColor: isCompleted ? '#52c41a' : isNext ? '#fa8c16' : '#1890ff' 
                          }} 
                        />
                        <Text strong className="customer-name">
                          {stop.customer_name || `訂單 #${stop.order_id}`}
                        </Text>
                      </Space>
                      {isCompleted && <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />}
                    </div>
                    
                    <div className="stop-content">
                      <Text className="address">{stop.address}</Text>
                      
                      {stop.delivery_notes && (
                        <Text type="secondary" className="notes">
                          備註：{stop.delivery_notes}
                        </Text>
                      )}
                      
                      <Space className="stop-time">
                        <ClockCircleOutlined />
                        {stop.estimated_arrival ? (
                          <Text type="secondary">
                            預計：{new Date(stop.estimated_arrival).toLocaleTimeString('zh-TW', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </Text>
                        ) : (
                          <Text type="secondary">未排程</Text>
                        )}
                      </Space>
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
                        icon={<AimOutlined />}
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
        width={280}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* Driver info */}
          <Card size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>司機編號：{user?.id}</Text>
              <Text>今日完成：{route?.completed_orders || 0} 單</Text>
              {currentLocation && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  位置：{currentLocation.latitude.toFixed(6)}, {currentLocation.longitude.toFixed(6)}
                </Text>
              )}
            </Space>
          </Card>

          {/* Notification settings */}
          <Card size="small" title="通知設定">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text>推播通知</Text>
              <Switch
                checked={notificationsEnabled}
                disabled
                checkedChildren="已開啟"
                unCheckedChildren="已關閉"
              />
            </div>
          </Card>

          {/* Actions */}
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
          
          {offlineQueueCount > 0 && isOnline && (
            <Button
              icon={<CloudSyncOutlined />}
              onClick={() => {
                setSidebarVisible(false);
                syncOfflineData();
              }}
              block
            >
              同步離線資料 ({offlineQueueCount})
            </Button>
          )}
          
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
          enableOfflineQueue={!isOnline}
        />
      )}

      <style jsx>{`
        .enhanced-mobile-driver-layout {
          min-height: 100vh;
          background: #f5f5f5;
        }
        
        .status-bar {
          margin-bottom: 8px;
        }
        
        .tracking-settings {
          margin-bottom: 8px;
        }
        
        .stop-card.next {
          border: 2px solid #fa8c16;
        }
        
        .stop-time {
          margin-top: 8px;
          font-size: 12px;
        }
      `}</style>
    </Layout>
  );
};

export default EnhancedMobileDriverInterface;