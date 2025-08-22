import React, { useEffect, useState, useCallback } from 'react';
import { Card, Steps, Tag, Space, Spin, Alert, Button, Row, Col, Statistic } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CarOutlined,
  HomeOutlined,
  PhoneOutlined,
  EnvironmentOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '../../hooks/useWebSocket';
import { GoogleMap, Marker, DirectionsRenderer } from '@react-google-maps/api';
import moment from 'moment';
import 'moment/locale/zh-tw';

moment.locale('zh-tw');

interface OrderTrackingProps {
  orderId: string;
  customerId?: string;
}

interface OrderStatus {
  status: 'pending' | 'confirmed' | 'preparing' | 'delivering' | 'delivered' | 'cancelled';
  timestamp: string;
  notes?: string;
}

interface DriverLocation {
  lat: number;
  lng: number;
  timestamp: string;
  speed?: number;
  heading?: number;
}

interface OrderDetails {
  id: string;
  customerName: string;
  customerPhone: string;
  deliveryAddress: string;
  products: Array<{
    name: string;
    quantity: number;
  }>;
  status: OrderStatus;
  driver?: {
    id: string;
    name: string;
    phone: string;
    vehiclePlate: string;
  };
  estimatedDeliveryTime?: string;
  actualDeliveryTime?: string;
}

const RealtimeOrderTracking: React.FC<OrderTrackingProps> = ({ orderId, customerId }) => {
  const [orderDetails, setOrderDetails] = useState<OrderDetails | null>(null);
  const [driverLocation, setDriverLocation] = useState<DriverLocation | null>(null);
  const [directions, setDirections] = useState<google.maps.DirectionsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const { isConnected, lastMessage, sendMessage, subscribe } = useWebSocket({
    endpoint: customerId ? 'ws' : 'ws/office',
    onMessage: handleWebSocketMessage,
  });

  // Handle WebSocket messages
  function handleWebSocketMessage(message: any) {
    if (message.type === 'order_update' && message.order_id === orderId) {
      fetchOrderDetails();
    } else if (message.type === 'driver_location' && orderDetails?.driver?.id === message.driver_id) {
      setDriverLocation({
        lat: message.latitude,
        lng: message.longitude,
        timestamp: message.timestamp,
        speed: message.speed,
        heading: message.heading,
      });
      updateRoute(message.latitude, message.longitude);
    } else if (message.type === 'delivery_update' && message.order_id === orderId) {
      fetchOrderDetails();
    }
  }

  // Fetch order details
  const fetchOrderDetails = useCallback(async () => {
    try {
      setRefreshing(true);
      const response = await fetch(`/api/v1/orders/${orderId}/tracking`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch order details');

      const data = await response.json();
      setOrderDetails(data);
      setError(null);
    } catch (err) {
      setError('無法載入訂單資訊');
      console.error('Error fetching order details:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [orderId]);

  // Update route when driver location changes
  const updateRoute = useCallback(
    async (driverLat: number, driverLng: number) => {
      if (!orderDetails?.deliveryAddress || !window.google) return;

      const directionsService = new google.maps.DirectionsService();
      
      try {
        const result = await directionsService.route({
          origin: { lat: driverLat, lng: driverLng },
          destination: orderDetails.deliveryAddress,
          travelMode: google.maps.TravelMode.DRIVING,
          optimizeWaypoints: true,
          drivingOptions: {
            departureTime: new Date(),
            trafficModel: google.maps.TrafficModel.BEST_GUESS,
          },
        });
        
        setDirections(result);
      } catch (error) {
        console.error('Error calculating route:', error);
      }
    },
    [orderDetails?.deliveryAddress]
  );

  // Subscribe to order updates
  useEffect(() => {
    if (isConnected) {
      subscribe(`order:${orderId}`);
      if (orderDetails?.driver?.id) {
        subscribe(`driver:${orderDetails.driver.id}`);
      }
    }
  }, [isConnected, orderId, orderDetails?.driver?.id, subscribe]);

  // Initial data fetch
  useEffect(() => {
    fetchOrderDetails();
  }, [fetchOrderDetails]);

  // Get current step
  const getCurrentStep = () => {
    if (!orderDetails) return 0;
    
    const statusMap: Record<string, number> = {
      pending: 0,
      confirmed: 1,
      preparing: 2,
      delivering: 3,
      delivered: 4,
    };
    
    return statusMap[orderDetails.status.status] || 0;
  };

  // Get step status
  const getStepStatus = (step: number) => {
    const currentStep = getCurrentStep();
    if (orderDetails?.status.status === 'cancelled') return 'error';
    if (step < currentStep) return 'finish';
    if (step === currentStep) return 'process';
    return 'wait';
  };

  if (loading && !orderDetails) {
    return (
      <Card>
        <Spin size="large" tip="載入訂單資訊中..." style={{ display: 'block', margin: '50px auto' }} />
      </Card>
    );
  }

  if (error && !orderDetails) {
    return (
      <Card>
        <Alert
          message="載入錯誤"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={fetchOrderDetails}>
              重試
            </Button>
          }
        />
      </Card>
    );
  }

  if (!orderDetails) {
    return null;
  }

  return (
    <div>
      {/* Connection Status */}
      {!isConnected && (
        <Alert
          message="即時更新已斷線"
          description="目前無法接收即時更新，請重新整理頁面"
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Order Status Card */}
      <Card
        title={
          <Space>
            <span>訂單追蹤 #{orderId}</span>
            <Tag color={orderDetails.status.status === 'delivered' ? 'success' : 'processing'}>
              {orderDetails.status.status === 'delivered' ? '已完成' : '進行中'}
            </Tag>
            <Button
              icon={<ReloadOutlined spin={refreshing} />}
              onClick={fetchOrderDetails}
              loading={refreshing}
              size="small"
            >
              重新整理
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Steps current={getCurrentStep()} style={{ marginBottom: 32 }}>
          <Steps.Step
            title="訂單確認"
            description={getStepStatus(1) === 'finish' ? moment(orderDetails.status.timestamp).format('HH:mm') : ''}
            status={getStepStatus(1)}
            icon={<CheckCircleOutlined />}
          />
          <Steps.Step
            title="準備配送"
            description={getStepStatus(2) === 'finish' ? '司機已接單' : ''}
            status={getStepStatus(2)}
            icon={<ClockCircleOutlined />}
          />
          <Steps.Step
            title="配送中"
            description={orderDetails.driver ? orderDetails.driver.name : ''}
            status={getStepStatus(3)}
            icon={<CarOutlined />}
          />
          <Steps.Step
            title="已送達"
            description={orderDetails.actualDeliveryTime ? moment(orderDetails.actualDeliveryTime).format('HH:mm') : ''}
            status={getStepStatus(4)}
            icon={<HomeOutlined />}
          />
        </Steps>

        {/* Order Details */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card size="small" title="訂單資訊">
              <p><strong>客戶：</strong> {orderDetails.customerName}</p>
              <p><strong>電話：</strong> {orderDetails.customerPhone}</p>
              <p><strong>地址：</strong> {orderDetails.deliveryAddress}</p>
              <p><strong>商品：</strong></p>
              <ul style={{ paddingLeft: 20 }}>
                {orderDetails.products.map((product, index) => (
                  <li key={index}>{product.name} x {product.quantity}</li>
                ))}
              </ul>
            </Card>
          </Col>
          
          {orderDetails.driver && (
            <Col xs={24} md={12}>
              <Card size="small" title="司機資訊">
                <p><strong>司機：</strong> {orderDetails.driver.name}</p>
                <p><strong>電話：</strong> {orderDetails.driver.phone}</p>
                <p><strong>車牌：</strong> {orderDetails.driver.vehiclePlate}</p>
                {orderDetails.estimatedDeliveryTime && (
                  <p>
                    <strong>預計送達：</strong>{' '}
                    {moment(orderDetails.estimatedDeliveryTime).format('HH:mm')}
                  </p>
                )}
              </Card>
            </Col>
          )}
        </Row>
      </Card>

      {/* Real-time Map Tracking */}
      {orderDetails.status.status === 'delivering' && driverLocation && (
        <Card title="即時位置追蹤" style={{ marginTop: 16 }}>
          <div style={{ height: '400px', width: '100%' }}>
            <GoogleMap
              mapContainerStyle={{ height: '100%', width: '100%' }}
              zoom={15}
              center={driverLocation}
              options={{
                zoomControl: true,
                streetViewControl: false,
                mapTypeControl: false,
                fullscreenControl: true,
              }}
            >
              {/* Driver Marker */}
              <Marker
                position={driverLocation}
                icon={{
                  url: '/images/delivery-truck.png',
                  scaledSize: new google.maps.Size(40, 40),
                }}
                title="司機位置"
              />
              
              {/* Customer Marker */}
              <Marker
                position={{ lat: 25.0330, lng: 121.5654 }} // Should geocode from address
                icon={{
                  url: '/images/home-marker.png',
                  scaledSize: new google.maps.Size(40, 40),
                }}
                title="送達地址"
              />
              
              {/* Route */}
              {directions && (
                <DirectionsRenderer
                  directions={directions}
                  options={{
                    suppressMarkers: true,
                    polylineOptions: {
                      strokeColor: '#1890ff',
                      strokeWeight: 5,
                    },
                  }}
                />
              )}
            </GoogleMap>
          </div>
          
          {/* Driver Stats */}
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={8}>
              <Statistic
                title="距離"
                value={directions?.routes[0]?.legs[0]?.distance?.text || '計算中...'}
                prefix={<EnvironmentOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="預計時間"
                value={directions?.routes[0]?.legs[0]?.duration?.text || '計算中...'}
                prefix={<ClockCircleOutlined />}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="速度"
                value={driverLocation.speed || 0}
                suffix="km/h"
                prefix={<CarOutlined />}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* Contact Actions */}
      {orderDetails.status.status === 'delivering' && orderDetails.driver && (
        <Card style={{ marginTop: 16 }}>
          <Space>
            <Button
              type="primary"
              icon={<PhoneOutlined />}
              href={`tel:${orderDetails.driver.phone}`}
            >
              聯絡司機
            </Button>
            <Button
              icon={<PhoneOutlined />}
              href="tel:0800-123-456"
            >
              客服專線
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default RealtimeOrderTracking;