import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, List, Badge, Space, Tag, Progress, Modal, Spin, message } from 'antd';
import {
  ArrowLeftOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  CarOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import RouteMap from './components/RouteMap';
import './RouteDetails.css';

interface Delivery {
  id: string;
  orderId: string;
  customer: {
    name: string;
    phone: string;
    address: string;
    coordinates: {
      lat: number;
      lng: number;
    };
  };
  products: Array<{
    name: string;
    quantity: number;
    type: string;
  }>;
  status: 'pending' | 'in_progress' | 'delivered' | 'failed';
  notes?: string;
  estimatedTime?: string;
}

interface RouteData {
  id: string;
  name: string;
  deliveries: Delivery[];
  optimizedPath: Array<{ lat: number; lng: number }>;
  totalDistance: number;
  estimatedDuration: string;
  status: 'pending' | 'in_progress' | 'completed';
  currentDeliveryIndex: number;
}

const RouteDetails: React.FC = () => {
  const { routeId } = useParams<{ routeId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [route, setRoute] = useState<RouteData | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingOffline, setDownloadingOffline] = useState(false);
  const [isOfflineReady, setIsOfflineReady] = useState(false);
  const [mapVisible, setMapVisible] = useState(false);

  useEffect(() => {
    if (routeId) {
      fetchRouteDetails();
      checkOfflineStatus();
    }
  }, [routeId]);

  const fetchRouteDetails = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/driver/routes/${routeId}`);
      setRoute(response.data);
      // Cache for offline
      localStorage.setItem(`route_${routeId}`, JSON.stringify(response.data));
    } catch (error) {
      // Try loading from cache
      const cached = localStorage.getItem(`route_${routeId}`);
      if (cached) {
        setRoute(JSON.parse(cached));
      } else {
        message.error(t('driver.route.loadError'));
        navigate('/driver');
      }
    } finally {
      setLoading(false);
    }
  };

  const checkOfflineStatus = () => {
    const offlineData = localStorage.getItem(`route_offline_${routeId}`);
    setIsOfflineReady(!!offlineData);
  };

  const handleDownloadOffline = async () => {
    setDownloadingOffline(true);
    try {
      // Download route data and map tiles
      const response = await api.get(`/driver/routes/${routeId}/offline`);
      localStorage.setItem(`route_offline_${routeId}`, JSON.stringify(response.data));
      setIsOfflineReady(true);
      message.success(t('driver.route.offlineReady'));
    } catch (error) {
      message.error(t('driver.route.offlineError'));
    } finally {
      setDownloadingOffline(false);
    }
  };

  const handleStartRoute = () => {
    if (!route) return;
    navigate(`/driver/delivery/${route.id}/${route.currentDeliveryIndex || 0}`);
  };

  const getDeliveryStatusIcon = (status: string) => {
    switch (status) {
      case 'delivered':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'in_progress':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#999' }} />;
    }
  };

  const getCompletionProgress = () => {
    if (!route) return 0;
    const completed = route.deliveries.filter(d => d.status === 'delivered').length;
    return Math.round((completed / route.deliveries.length) * 100);
  };

  if (loading) {
    return (
      <div className="route-details-loading">
        <Spin size="large" />
      </div>
    );
  }

  if (!route) {
    return null;
  }

  return (
    <div className="route-details">
      {/* Header */}
      <div className="route-header">
        <Button
          icon={<ArrowLeftOutlined />}
          type="text"
          onClick={() => navigate('/driver')}
          className="back-button"
        />
        <div className="route-title">
          <h2>{route.name}</h2>
          <Tag color={route.status === 'completed' ? 'green' : 'blue'}>
            {t(`driver.routes.status.${route.status}`)}
          </Tag>
        </div>
        <Button
          icon={isOfflineReady ? <CheckCircleOutlined /> : <DownloadOutlined />}
          type="text"
          onClick={handleDownloadOffline}
          loading={downloadingOffline}
          data-testid="download-offline-button"
        />
      </div>

      {/* Progress Card */}
      <Card className="progress-card">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Progress
            percent={getCompletionProgress()}
            status={route.status === 'completed' ? 'success' : 'active'}
          />
          <Space justify="space-between" style={{ width: '100%' }}>
            <span>{t('driver.route.deliveries', {
              completed: route.deliveries.filter(d => d.status === 'delivered').length,
              total: route.deliveries.length
            })}</span>
            <span>{route.estimatedDuration}</span>
          </Space>
        </Space>
      </Card>

      {/* Action Buttons */}
      <div className="action-buttons">
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleStartRoute}
          block
          data-testid="start-route-button"
          disabled={route.status === 'completed'}
        >
          {route.status === 'in_progress'
            ? t('driver.route.continue')
            : t('driver.route.start')}
        </Button>
        <Button
          size="large"
          icon={<EnvironmentOutlined />}
          onClick={() => setMapVisible(true)}
          block
          data-testid="view-map-button"
        >
          {t('driver.route.viewMap')}
        </Button>
      </div>

      {/* Offline Ready Badge */}
      {isOfflineReady && (
        <Badge
          className="offline-badge"
          data-testid="offline-ready-badge"
          color="green"
          text={t('driver.route.offlineAvailable')}
        />
      )}

      {/* Delivery List */}
      <Card title={t('driver.route.deliveryList')} className="delivery-list-card">
        <List
          dataSource={route.deliveries}
          renderItem={(delivery, index) => (
            <List.Item
              className={`delivery-item ${delivery.status}`}
              onClick={() => {
                if (route.status !== 'completed') {
                  navigate(`/driver/delivery/${route.id}/${index}`);
                }
              }}
            >
              <Space align="start" style={{ width: '100%' }}>
                <div className="delivery-number">
                  {index + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div className="customer-name">
                    {delivery.customer.name}
                  </div>
                  <div className="delivery-address">
                    <EnvironmentOutlined /> {delivery.customer.address}
                  </div>
                  <div className="delivery-products">
                    {delivery.products.map((p, i) => (
                      <Tag key={i}>{p.quantity}x {p.type}</Tag>
                    ))}
                  </div>
                  {delivery.estimatedTime && (
                    <div className="estimated-time">
                      <ClockCircleOutlined /> {delivery.estimatedTime}
                    </div>
                  )}
                </div>
                {getDeliveryStatusIcon(delivery.status)}
              </Space>
            </List.Item>
          )}
        />
      </Card>

      {/* Map Modal */}
      <Modal
        title={t('driver.route.routeMap')}
        open={mapVisible}
        onCancel={() => setMapVisible(false)}
        footer={null}
        width="100%"
        style={{ top: 0 }}
        className="map-modal"
      >
        <RouteMap
          route={route}
          currentDeliveryIndex={route.currentDeliveryIndex}
        />
      </Modal>
    </div>
  );
};

export default RouteDetails;