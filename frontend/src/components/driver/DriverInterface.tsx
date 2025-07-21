import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, List, Button, Space, Tag, Spin, Empty, Progress, Modal, message } from 'antd';
import {
  EnvironmentOutlined,
  PhoneOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  CompassOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { useDriverWebSocket } from '../../hooks/useWebSocket';
import { routeService } from '../../services/route.service';
import { orderService } from '../../services/order.service';
import type { RouteWithDetails, RouteStop } from '../../services/route.service';
import type { Order } from '../../types/order';
import DeliveryCompletionModal from './DeliveryCompletionModal';

const { Title, Text } = Typography;

interface DeliveryStop extends RouteStop {
  order?: Order;
  customerName?: string;
  customerPhone?: string;
  products?: Array<{
    product_name: string;
    quantity: number;
    size_kg: number;
  }>;
}

const DriverInterface: React.FC = () => {
  const { user } = useAuth();
  const { on, updateLocation } = useDriverWebSocket();
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [route, setRoute] = useState<RouteWithDetails | null>(null);
  const [stops, setStops] = useState<DeliveryStop[]>([]);
  const [selectedStop, setSelectedStop] = useState<DeliveryStop | null>(null);
  const [completionModalVisible, setCompletionModalVisible] = useState(false);
  const [routeStarted, setRouteStarted] = useState(false);
  const [locationTracking, setLocationTracking] = useState(false);
  const [watchId, setWatchId] = useState<number | null>(null);

  // Fetch driver's route for today
  const fetchRoute = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const todayRoute = await routeService.getDriverRoute(user?.id || 0);
      if (todayRoute) {
        setRoute(todayRoute);
        setRouteStarted(todayRoute.status === 'in_progress');
        
        // Fetch order details for each stop
        if (todayRoute.stops) {
          const stopsWithOrders = await Promise.all(
            todayRoute.stops.map(async (stop) => {
              try {
                const order = await orderService.getOrder(stop.order_id);
                return {
                  ...stop,
                  order,
                  customerName: order.customer?.short_name || order.customer?.invoice_title,
                  customerPhone: order.customer?.phone,
                  products: order.order_items?.map(item => ({
                    product_name: item.gas_product?.display_name || `產品 ${item.gas_product_id}`,
                    quantity: item.quantity,
                    size_kg: item.gas_product?.size_kg || 0,
                  })) || [],
                };
              } catch (error) {
                console.error(`Failed to fetch order ${stop.order_id}:`, error);
                return stop;
              }
            })
          );
          setStops(stopsWithOrders.sort((a, b) => a.stop_sequence - b.stop_sequence));
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

  // Initial load
  useEffect(() => {
    fetchRoute();
  }, [fetchRoute]);

  // WebSocket listeners
  useEffect(() => {
    const unsubscribeRouteUpdate = on('route_update', (message) => {
      if (message.route_id === route?.id) {
        fetchRoute(false); // Refresh without loading indicator
      }
    });

    const unsubscribeRouteAssigned = on('route_assigned', () => {
      fetchRoute();
      message.info('您有新的配送路線！');
    });

    return () => {
      unsubscribeRouteUpdate();
      unsubscribeRouteAssigned();
    };
  }, [on, route?.id, fetchRoute]);

  // Location tracking
  const startLocationTracking = useCallback(() => {
    if (!navigator.geolocation) {
      message.error('您的瀏覽器不支援定位功能');
      return;
    }

    const id = navigator.geolocation.watchPosition(
      (position) => {
        updateLocation(position.coords.latitude, position.coords.longitude);
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
  }, [updateLocation]);

  const stopLocationTracking = useCallback(() => {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      setWatchId(null);
      setLocationTracking(false);
      message.info('位置追蹤已關閉');
    }
  }, [watchId]);

  // Start/pause route
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

  // Handle delivery completion
  const handleDeliveryClick = (stop: DeliveryStop) => {
    if (!stop.is_completed) {
      setSelectedStop(stop);
      setCompletionModalVisible(true);
    }
  };

  const handleDeliveryComplete = async (data: any) => {
    if (!selectedStop) return;
    
    try {
      // Update stop status
      await routeService.completeStop(selectedStop.id, data.notes);
      
      // Update order status if needed
      if (selectedStop.order_id) {
        await orderService.updateOrder(selectedStop.order_id, {
          status: 'delivered',
          delivery_notes: data.notes,
        });
      }
      
      message.success('配送完成！');
      setCompletionModalVisible(false);
      fetchRoute(false);
    } catch (error) {
      console.error('Failed to complete delivery:', error);
      message.error('無法完成配送');
    }
  };

  // Navigation
  const handleNavigation = (stop: DeliveryStop) => {
    const destination = `${stop.latitude},${stop.longitude}`;
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${destination}`;
    window.open(googleMapsUrl, '_blank');
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: 50 }}>
        <Spin size="large" tip="載入中..." />
      </div>
    );
  }

  if (!route) {
    return (
      <Empty
        description="今日沒有配送路線"
        style={{ marginTop: 50 }}
      >
        <Button onClick={() => fetchRoute()}>重新載入</Button>
      </Empty>
    );
  }

  const completionRate = route.total_stops > 0
    ? Math.round((route.completed_stops / route.total_stops) * 100)
    : 0;

  return (
    <div className="driver-interface">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header with route info */}
        <Card data-testid="current-route">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Title level={3} style={{ margin: 0 }}>今日配送路線</Title>
              <Space>
                <Button
                  icon={<ReloadOutlined spin={refreshing} />}
                  onClick={() => {
                    setRefreshing(true);
                    fetchRoute();
                  }}
                  disabled={refreshing}
                >
                  重新整理
                </Button>
                {locationTracking && (
                  <Tag color="processing" icon={<CompassOutlined />}>
                    定位中
                  </Tag>
                )}
              </Space>
            </div>
            
            <Space split={<span style={{ color: '#e8e8e8' }}>|</span>} size="large">
              <div>
                <Text type="secondary">路線編號：</Text>
                <Text strong>{route.route_number}</Text>
              </div>
              <div>
                <Text type="secondary">區域：</Text>
                <Text strong>{route.area || '未指定'}</Text>
              </div>
              <div>
                <Text type="secondary">車輛：</Text>
                <Text strong>{route.vehicle_plate || '未指定'}</Text>
              </div>
            </Space>

            <div>
              <Text type="secondary">配送進度</Text>
              <Progress percent={completionRate} style={{ marginTop: 8 }} />
              <Space style={{ marginTop: 8 }}>
                <Text>{route.completed_stops} / {route.total_stops} 完成</Text>
                {route.total_distance_km && (
                  <Text type="secondary">總距離: {route.total_distance_km} 公里</Text>
                )}
              </Space>
            </div>

            <Space>
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
                <>
                  <Button
                    type="primary"
                    size="large"
                    icon={<CheckCircleOutlined />}
                    onClick={handleCompleteRoute}
                    disabled={route.completed_stops < route.total_stops}
                  >
                    完成路線
                  </Button>
                  {!locationTracking && (
                    <Button
                      size="large"
                      icon={<CompassOutlined />}
                      onClick={startLocationTracking}
                    >
                      開啟定位
                    </Button>
                  )}
                  {locationTracking && (
                    <Button
                      size="large"
                      icon={<PauseCircleOutlined />}
                      onClick={stopLocationTracking}
                    >
                      關閉定位
                    </Button>
                  )}
                </>
              ) : (
                <Tag color="green" style={{ fontSize: 16, padding: '8px 16px' }}>
                  路線已完成
                </Tag>
              )}
            </Space>
          </Space>
        </Card>

        {/* Delivery stops list */}
        <div>
          <Title level={4}>配送清單</Title>
          {stops.length === 0 ? (
            <Empty description="沒有配送站點" />
          ) : (
            <List
              data-testid="routes-list"
              dataSource={stops}
              renderItem={(stop) => (
                <Card
                  data-testid="delivery-item"
                  style={{
                    marginBottom: 16,
                    borderColor: stop.is_completed ? '#52c41a' : '#1890ff',
                  }}
                  actions={[
                    <Button
                      type="link"
                      icon={<PhoneOutlined />}
                      href={`tel:${stop.customerPhone}`}
                      disabled={!stop.customerPhone}
                    >
                      撥打電話
                    </Button>,
                    <Button
                      type="link"
                      icon={<EnvironmentOutlined />}
                      onClick={() => handleNavigation(stop)}
                    >
                      導航
                    </Button>,
                    stop.is_completed ? (
                      <Tag color="success" icon={<CheckCircleOutlined />}>
                        已完成
                      </Tag>
                    ) : (
                      <Button
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        onClick={() => handleDeliveryClick(stop)}
                        disabled={route.status !== 'in_progress'}
                        data-testid="complete-delivery-btn"
                      >
                        完成配送
                      </Button>
                    ),
                  ]}
                >
                  <Card.Meta
                    title={
                      <Space>
                        <Tag>{stop.stop_sequence}</Tag>
                        <Text strong>{stop.customerName || `訂單 #${stop.order_id}`}</Text>
                        {stop.is_completed && (
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        )}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Text>{stop.address}</Text>
                        {stop.products && stop.products.length > 0 && (
                          <div>
                            <Text type="secondary">產品：</Text>
                            {stop.products.map((product, idx) => (
                              <Tag key={idx}>
                                {product.product_name} x{product.quantity}
                              </Tag>
                            ))}
                          </div>
                        )}
                        {stop.estimated_arrival && (
                          <Text type="secondary">
                            預計到達：{new Date(stop.estimated_arrival).toLocaleTimeString('zh-TW', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </Text>
                        )}
                        {stop.delivery_notes && (
                          <Text type="secondary">備註：{stop.delivery_notes}</Text>
                        )}
                      </Space>
                    }
                  />
                </Card>
              )}
            />
          )}
        </div>
      </Space>

      {/* Delivery completion modal */}
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
    </div>
  );
};

export default DriverInterface;