import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Progress, Space, Typography } from 'antd';
import {
  CarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  TruckOutlined,
  UserOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../../../contexts/WebSocketContext';

const { Title, Text } = Typography;

interface DispatchMetricsData {
  activeRoutes: number;
  completedDeliveries: number;
  pendingOrders: number;
  driversOnDuty: number;
  onTimeDeliveryRate: number;
  averageDeliveryTime: number;
  totalDistance: number;
  emergencyOrders: number;
  utilizationRate: number;
  customerSatisfaction: number;
}

const DispatchMetrics: React.FC = () => {
  const { t } = useTranslation();
  const { socket, isConnected } = useWebSocket();
  const [metrics, setMetrics] = useState<DispatchMetricsData>({
    activeRoutes: 12,
    completedDeliveries: 156,
    pendingOrders: 34,
    driversOnDuty: 8,
    onTimeDeliveryRate: 94.5,
    averageDeliveryTime: 28,
    totalDistance: 1234,
    emergencyOrders: 2,
    utilizationRate: 87,
    customerSatisfaction: 4.8,
  });
  const [previousMetrics, setPreviousMetrics] = useState<DispatchMetricsData>(metrics);

  useEffect(() => {
    if (!socket || !isConnected) return;

    // Listen for metrics updates
    const handleMetricsUpdate = (data: any) => {
      setPreviousMetrics(metrics);
      setMetrics(data);
    };

    socket.on('dispatch:metrics:update', handleMetricsUpdate);
    socket.on('metrics:realtime', handleMetricsUpdate);

    // Request initial metrics
    socket.emit('dispatch:metrics:request');

    return () => {
      socket.off('dispatch:metrics:update', handleMetricsUpdate);
      socket.off('metrics:realtime', handleMetricsUpdate);
    };
  }, [socket, isConnected, metrics]);

  const getChangeIndicator = (current: number, previous: number) => {
    if (current === previous) return null;
    const change = ((current - previous) / previous) * 100;
    const isPositive = change > 0;
    return (
      <Space size="small">
        {isPositive ? (
          <RiseOutlined style={{ color: '#52c41a' }} />
        ) : (
          <FallOutlined style={{ color: '#ff4d4f' }} />
        )}
        <Text type={isPositive ? 'success' : 'danger'} style={{ fontSize: 12 }}>
          {Math.abs(change).toFixed(1)}%
        </Text>
      </Space>
    );
  };

  const getUtilizationColor = (rate: number) => {
    if (rate >= 90) return '#ff4d4f';
    if (rate >= 70) return '#52c41a';
    if (rate >= 50) return '#faad14';
    return '#d9d9d9';
  };

  const getSatisfactionColor = (rating: number) => {
    if (rating >= 4.5) return '#52c41a';
    if (rating >= 4.0) return '#1890ff';
    if (rating >= 3.5) return '#faad14';
    return '#ff4d4f';
  };

  return (
    <>
      {/* Primary Metrics */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dispatch.dashboard.activeRoutes')}
              value={metrics.activeRoutes}
              prefix={<TruckOutlined />}
              valueStyle={{ color: '#1890ff' }}
              suffix={getChangeIndicator(metrics.activeRoutes, previousMetrics.activeRoutes)}
            />
            <Progress
              percent={Math.min((metrics.activeRoutes / 20) * 100, 100)}
              strokeColor="#1890ff"
              showInfo={false}
              size="small"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dispatch.dashboard.completedDeliveries')}
              value={metrics.completedDeliveries}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix={getChangeIndicator(metrics.completedDeliveries, previousMetrics.completedDeliveries)}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('common.time.today')}
            </Text>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dispatch.dashboard.pendingOrders')}
              value={metrics.pendingOrders}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
              suffix={metrics.emergencyOrders > 0 && (
                <Space size="small">
                  <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                  <Text type="danger" style={{ fontSize: 12 }}>
                    {metrics.emergencyOrders} {t('dispatch.dashboard.urgent')}
                  </Text>
                </Space>
              )}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title={t('dispatch.dashboard.driversOnDuty')}
              value={metrics.driversOnDuty}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#13c2c2' }}
            />
            <Progress
              percent={metrics.utilizationRate}
              strokeColor={getUtilizationColor(metrics.utilizationRate)}
              format={(percent) => `${percent}% ${t('dispatch.dashboard.utilized')}`}
              size="small"
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Performance Metrics */}
      <Card
        title={t('dispatch.dashboard.performanceMetrics')}
        style={{ marginTop: 16 }}
        bodyStyle={{ padding: '16px' }}
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="circle"
                percent={metrics.onTimeDeliveryRate}
                format={(percent) => `${percent}%`}
                strokeColor={{
                  '0%': '#ff4d4f',
                  '50%': '#faad14',
                  '100%': '#52c41a',
                }}
                width={120}
              />
              <Title level={5} style={{ marginTop: 16 }}>
                {t('dispatch.dashboard.onTimeDelivery')}
              </Title>
              <Text type="secondary">
                {t('dispatch.dashboard.target')}: 95%
              </Text>
            </div>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <div style={{ textAlign: 'center' }}>
              <Statistic
                title={t('dispatch.dashboard.avgDeliveryTime')}
                value={metrics.averageDeliveryTime}
                suffix={t('common.unit.minutes')}
                valueStyle={{ color: metrics.averageDeliveryTime <= 30 ? '#52c41a' : '#faad14' }}
              />
              <Progress
                percent={Math.max(0, 100 - (metrics.averageDeliveryTime / 60) * 100)}
                strokeColor={metrics.averageDeliveryTime <= 30 ? '#52c41a' : '#faad14'}
                showInfo={false}
                size="small"
                style={{ marginTop: 8 }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('dispatch.dashboard.target')}: 30 {t('common.unit.minutes')}
              </Text>
            </div>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <div style={{ textAlign: 'center' }}>
              <Statistic
                title={t('dispatch.dashboard.customerSatisfaction')}
                value={metrics.customerSatisfaction}
                precision={1}
                suffix="/ 5.0"
                valueStyle={{ color: getSatisfactionColor(metrics.customerSatisfaction) }}
                prefix="⭐"
              />
              <Progress
                percent={(metrics.customerSatisfaction / 5) * 100}
                strokeColor={getSatisfactionColor(metrics.customerSatisfaction)}
                showInfo={false}
                size="small"
                style={{ marginTop: 8 }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('dispatch.dashboard.basedOnReviews', { count: 245 })}
              </Text>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Daily Summary */}
      <Card
        title={t('dispatch.dashboard.dailySummary')}
        style={{ marginTop: 16 }}
        extra={
          <Text type="secondary">
            {new Date().toLocaleDateString('zh-TW', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              weekday: 'long',
            })}
          </Text>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('dispatch.dashboard.totalDistance')}
              value={metrics.totalDistance}
              suffix="km"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('dispatch.dashboard.fuelSaved')}
              value={Math.round(metrics.totalDistance * 0.08)}
              suffix="L"
              valueStyle={{ fontSize: 20, color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('dispatch.dashboard.co2Reduced')}
              value={Math.round(metrics.totalDistance * 0.2)}
              suffix="kg"
              valueStyle={{ fontSize: 20, color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('dispatch.dashboard.revenue')}
              value={metrics.completedDeliveries * 180}
              prefix="NT$"
              valueStyle={{ fontSize: 20, color: '#1890ff' }}
            />
          </Col>
        </Row>
      </Card>
    </>
  );
};

export default DispatchMetrics;