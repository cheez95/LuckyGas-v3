import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Steps,
  Typography,
  Space,
  Button,
  Descriptions,
  Timeline,
  Badge,
  Spin,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CarOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useWebSocketContext } from '../../contexts/WebSocketContext';
import { api } from '../../services/api';

const { Title, Text } = Typography;
const { Step } = Steps;

interface OrderDetails {
  id: string;
  orderNumber: string;
  status: string;
  customerName: string;
  customerAddress: string;
  cylinderType: string;
  quantity: number;
  orderDate: string;
  estimatedDelivery?: string;
  actualDelivery?: string;
  driverName?: string;
  driverPhone?: string;
  driverLocation?: {
    latitude: number;
    longitude: number;
    lastUpdate: string;
  };
  timeline: Array<{
    timestamp: string;
    status: string;
    description: string;
  }>;
}

const OrderTracking: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const mapRef = useRef<HTMLDivElement>(null);
  const [orderDetails, setOrderDetails] = useState<OrderDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [driverMarker, setDriverMarker] = useState<google.maps.Marker | null>(null);
  const [destinationMarker, setDestinationMarker] = useState<google.maps.Marker | null>(null);
  
  const { subscribeToDriverLocation, unsubscribeFromDriverLocation } = useWebSocketContext();

  useEffect(() => {
    if (orderId) {
      fetchOrderDetails();
      subscribeToDriverLocation(orderId);
    }

    return () => {
      if (orderId) {
        unsubscribeFromDriverLocation(orderId);
      }
    };
  }, [orderId]);

  useEffect(() => {
    // Initialize map when order details are loaded
    if (orderDetails && window.google && mapRef.current && !map) {
      initializeMap();
    }
  }, [orderDetails, map]);

  const fetchOrderDetails = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/orders/${orderId}/tracking`);
      setOrderDetails(response.data);
      
      if (response.data.driverLocation) {
        updateDriverLocation(response.data.driverLocation);
      }
    } catch (error) {
      message.error('無法載入訂單資訊');
      navigate('/customer');
    } finally {
      setLoading(false);
    }
  };

  const initializeMap = () => {
    if (!mapRef.current || !orderDetails) return;

    const mapInstance = new google.maps.Map(mapRef.current, {
      zoom: 13,
      center: { lat: 25.0330, lng: 121.5654 }, // Default to Taipei
      mapTypeControl: false,
      fullscreenControl: false,
      streetViewControl: false,
    });

    setMap(mapInstance);

    // Add destination marker
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ address: orderDetails.customerAddress }, (results, status) => {
      if (status === 'OK' && results && results[0]) {
        const destination = results[0].geometry.location;
        
        const marker = new google.maps.Marker({
          position: destination,
          map: mapInstance,
          title: '配送地址',
          icon: {
            url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
          },
        });
        
        setDestinationMarker(marker);
        mapInstance.setCenter(destination);
      }
    });
  };

  const updateDriverLocation = (location: { latitude: number; longitude: number }) => {
    if (!map) return;

    const position = new google.maps.LatLng(location.latitude, location.longitude);

    if (driverMarker) {
      // Update existing marker
      driverMarker.setPosition(position);
    } else {
      // Create new marker
      const marker = new google.maps.Marker({
        position,
        map,
        title: '司機位置',
        icon: {
          url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
        },
      });
      setDriverMarker(marker);
    }

    // Center map on driver
    map.setCenter(position);
  };

  const getCurrentStep = () => {
    if (!orderDetails) return 0;
    
    const statusSteps: Record<string, number> = {
      pending: 0,
      confirmed: 0,
      assigned: 1,
      in_delivery: 2,
      delivered: 3,
    };
    
    return statusSteps[orderDetails.status] || 0;
  };

  const handleCallDriver = () => {
    if (orderDetails?.driverPhone) {
      window.location.href = `tel:${orderDetails.driverPhone}`;
    }
  };

  const handleRefresh = () => {
    fetchOrderDetails();
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!orderDetails) {
    return null;
  }

  const showMap = orderDetails.status === 'in_delivery' && orderDetails.driverLocation;

  return (
    <div style={{ padding: '24px', backgroundColor: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/customer')}
          >
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            訂單追蹤
          </Title>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
          >
            重新整理
          </Button>
        </Space>
      </Card>

      {/* Order Progress */}
      <Card style={{ marginBottom: 24 }}>
        <Steps current={getCurrentStep()} style={{ marginBottom: 24 }}>
          <Step title="訂單確認" icon={<CheckCircleOutlined />} />
          <Step title="司機指派" icon={<CarOutlined />} />
          <Step title="配送中" icon={<EnvironmentOutlined />} />
          <Step title="已送達" icon={<CheckCircleOutlined />} />
        </Steps>

        <Descriptions column={1}>
          <Descriptions.Item label="訂單編號">
            {orderDetails.orderNumber}
          </Descriptions.Item>
          <Descriptions.Item label="訂購項目">
            {orderDetails.quantity} x {orderDetails.cylinderType} 瓦斯桶
          </Descriptions.Item>
          <Descriptions.Item label="配送地址">
            {orderDetails.customerAddress}
          </Descriptions.Item>
          <Descriptions.Item label="預計送達時間">
            {orderDetails.estimatedDelivery || '尚未安排'}
          </Descriptions.Item>
          {orderDetails.driverName && (
            <Descriptions.Item label="配送司機">
              <Space>
                <Text>{orderDetails.driverName}</Text>
                {orderDetails.driverPhone && (
                  <Button
                    type="link"
                    size="small"
                    icon={<PhoneOutlined />}
                    onClick={handleCallDriver}
                  >
                    聯絡司機
                  </Button>
                )}
              </Space>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* Live Map (only show when in delivery) */}
      {showMap && (
        <Card
          title={<Space><CarOutlined /> 即時位置</Space>}
          style={{ marginBottom: 24 }}
        >
          <div ref={mapRef} style={{ height: 300, marginBottom: 16 }} />
          <Text type="secondary">
            最後更新：{orderDetails.driverLocation?.lastUpdate}
          </Text>
        </Card>
      )}

      {/* Timeline */}
      <Card title="訂單進度">
        <Timeline>
          {orderDetails.timeline.map((event, index) => (
            <Timeline.Item
              key={index}
              color={index === 0 ? 'blue' : 'gray'}
              dot={index === 0 ? <ClockCircleOutlined /> : undefined}
            >
              <Space direction="vertical" size={0}>
                <Text strong>{event.description}</Text>
                <Text type="secondary">{event.timestamp}</Text>
              </Space>
            </Timeline.Item>
          ))}
        </Timeline>
      </Card>
    </div>
  );
};

export default OrderTracking;