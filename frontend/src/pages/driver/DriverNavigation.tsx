import React, { useEffect, useRef, useState } from 'react';
import { Card, Button, Space, Typography, Drawer, List, Avatar, Badge, message } from 'antd';
import {
  ArrowLeftOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useWebSocketContext } from '../../contexts/WebSocketContext';

const { Text, Title } = Typography;

interface NavigationState {
  stop: {
    id: string;
    customer_name: string;
    address: string;
    phone: string;
    cylinder_count: number;
    cylinder_type: string;
    notes?: string;
  };
}

const DriverNavigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const mapRef = useRef<HTMLDivElement>(null);
  const { sendMessage } = useWebSocketContext();
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [directionsService, setDirectionsService] = useState<google.maps.DirectionsService | null>(null);
  const [directionsRenderer, setDirectionsRenderer] = useState<google.maps.DirectionsRenderer | null>(null);
  const [currentPosition, setCurrentPosition] = useState<GeolocationPosition | null>(null);
  const [navigationInfo, setNavigationInfo] = useState({
    distance: '',
    duration: '',
    nextTurn: '',
  });
  const [showDeliveryDrawer, setShowDeliveryDrawer] = useState(false);

  const navigationState = location.state as NavigationState;
  const stop = navigationState?.stop;

  useEffect(() => {
    if (!stop) {
      navigate('/driver');
      return;
    }

    // Initialize Google Maps
    if (window.google && mapRef.current) {
      const mapInstance = new google.maps.Map(mapRef.current, {
        zoom: 15,
        center: { lat: 25.0330, lng: 121.5654 }, // Default to Taipei
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
      });

      const service = new google.maps.DirectionsService();
      const renderer = new google.maps.DirectionsRenderer({
        map: mapInstance,
        suppressMarkers: false,
      });

      setMap(mapInstance);
      setDirectionsService(service);
      setDirectionsRenderer(renderer);
    }

    // Start watching position
    if ('geolocation' in navigator) {
      const watchId = navigator.geolocation.watchPosition(
        (position) => {
          setCurrentPosition(position);
          updateRoute(position);
          
          // Send location update
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
          message.error('無法取得位置資訊');
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
  }, [stop, navigate, sendMessage]);

  const updateRoute = async (position: GeolocationPosition) => {
    if (!directionsService || !directionsRenderer || !stop) return;

    const origin = new google.maps.LatLng(
      position.coords.latitude,
      position.coords.longitude
    );

    // Geocode destination address
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ address: stop.address }, (results, status) => {
      if (status === 'OK' && results && results[0]) {
        const destination = results[0].geometry.location;

        const request: google.maps.DirectionsRequest = {
          origin,
          destination,
          travelMode: google.maps.TravelMode.DRIVING,
          unitSystem: google.maps.UnitSystem.METRIC,
          avoidHighways: false,
          avoidTolls: false,
        };

        directionsService.route(request, (result, status) => {
          if (status === 'OK' && result) {
            directionsRenderer.setDirections(result);
            
            const route = result.routes[0];
            const leg = route.legs[0];
            
            setNavigationInfo({
              distance: leg.distance?.text || '',
              duration: leg.duration?.text || '',
              nextTurn: leg.steps[0]?.instructions || '',
            });

            // Check if arrived (within 100 meters)
            if (leg.distance && leg.distance.value < 100) {
              handleArrival();
            }
          }
        });
      }
    });
  };

  const handleArrival = () => {
    message.success('已抵達配送地點');
    sendMessage({
      type: 'driver.arrived',
      stop_id: stop?.id,
    });
    setShowDeliveryDrawer(true);
  };

  const handleDeliveryComplete = () => {
    sendMessage({
      type: 'order.delivered',
      stop_id: stop?.id,
      delivered_at: new Date().toISOString(),
    });
    message.success('配送完成');
    navigate('/driver');
  };

  const handleDeliveryFailed = () => {
    setShowDeliveryDrawer(false);
    // Navigate to report issue page
    navigate('/driver/report-issue', { state: { stop } });
  };

  const handleCallCustomer = () => {
    if (stop?.phone) {
      window.location.href = `tel:${stop.phone}`;
    }
  };

  const handleRefreshRoute = () => {
    if (currentPosition) {
      updateRoute(currentPosition);
    }
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Card 
        size="small" 
        style={{ borderRadius: 0 }}
        bodyStyle={{ padding: '8px 16px' }}
      >
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/driver')}
          >
            返回
          </Button>
          <Space>
            <Button icon={<PhoneOutlined />} onClick={handleCallCustomer} />
            <Button icon={<ReloadOutlined />} onClick={handleRefreshRoute} />
          </Space>
        </Space>
      </Card>

      {/* Navigation Info */}
      <Card 
        size="small" 
        style={{ margin: '8px', position: 'absolute', top: 60, left: 0, right: 0, zIndex: 1000 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Title level={5} style={{ margin: 0 }}>
            {stop?.customer_name} - {stop?.address}
          </Title>
          <Space>
            <Text strong>{navigationInfo.distance}</Text>
            <Text type="secondary">•</Text>
            <Text strong>{navigationInfo.duration}</Text>
          </Space>
          {navigationInfo.nextTurn && (
            <Text type="secondary">{navigationInfo.nextTurn}</Text>
          )}
        </Space>
      </Card>

      {/* Map */}
      <div ref={mapRef} style={{ flex: 1 }} />

      {/* Delivery Confirmation Drawer */}
      <Drawer
        title="確認配送"
        placement="bottom"
        open={showDeliveryDrawer}
        onClose={() => setShowDeliveryDrawer(false)}
        height="auto"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Card>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={4}>{stop?.customer_name}</Title>
              <Text>{stop?.address}</Text>
              <Space>
                <Badge color="blue" text={`${stop?.cylinder_count} x ${stop?.cylinder_type}`} />
              </Space>
              {stop?.notes && (
                <Text type="warning">備註：{stop.notes}</Text>
              )}
            </Space>
          </Card>
          
          <Space style={{ width: '100%', justifyContent: 'space-around' }}>
            <Button 
              type="primary" 
              size="large"
              icon={<CheckCircleOutlined />}
              onClick={handleDeliveryComplete}
              style={{ flex: 1 }}
            >
              確認送達
            </Button>
            <Button 
              danger
              size="large"
              icon={<CloseCircleOutlined />}
              onClick={handleDeliveryFailed}
              style={{ flex: 1 }}
            >
              無法送達
            </Button>
          </Space>
        </Space>
      </Drawer>
    </div>
  );
};

export default DriverNavigation;