import React, { useState } from 'react';
import { Row, Col, Card, Button, Space, Statistic, message } from 'antd';
import {
  ExclamationCircleOutlined,
  PlusOutlined,
  FireOutlined,
  ClockCircleOutlined,
  UserOutlined,
  CarOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import EmergencyAlertBanner from '../../components/dispatch/emergency/EmergencyAlertBanner';
import EmergencyDispatchModal from '../../components/dispatch/emergency/EmergencyDispatchModal';
import PriorityQueueManager, { EmergencyOrder } from '../../components/dispatch/emergency/PriorityQueueManager';
import { routeService } from '../../services/route.service';

const EmergencyDispatch: React.FC = () => {
  const { t } = useTranslation();
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<EmergencyOrder | undefined>();
  const [stats, setStats] = useState({
    totalEmergencies: 12,
    activeEmergencies: 2,
    averageResponseTime: 8.5,
    resolvedToday: 10,
  });

  const handleCreateEmergency = () => {
    setSelectedOrder(undefined);
    setModalVisible(true);
  };

  const handleDispatchOrder = (order: EmergencyOrder) => {
    setSelectedOrder(order);
    setModalVisible(true);
  };

  const handleAlertClick = (alert: any) => {
    // Handle emergency alert click
    if (alert.orderId) {
      // Fetch order details and open modal
      message.info(t('dispatch.emergency.openingOrder'));
    }
  };

  const handleEmergencySubmit = async (data: any) => {
    try {
      // Create emergency dispatch
      if (data.driverId) {
        // Create immediate route assignment
        await routeService.createRoutePlan({
          routeDate: new Date().toISOString().split('T')[0],
          driverId: data.driverId,
          stops: [
            {
              id: `emergency-${Date.now()}`,
              orderId: data.orderId || 0,
              location: data.location || { lat: 25.0330, lng: 121.5654 },
              orderNumber: `EM-${Date.now()}`,
              customerName: data.customerName || '',
              products: t('dispatch.emergency.emergencyDelivery'),
              isUrgent: true,
              sequence: 1,
            },
          ],
          totalDistance: 0,
          totalDuration: 0,
          totalStops: 1,
        });
      }
      message.success(t('dispatch.emergency.dispatchSuccess'));
    } catch (error) {
      throw error;
    }
  };

  const emergencyTypes = [
    {
      type: 'gas_leak',
      icon: <FireOutlined style={{ fontSize: 32, color: '#ff4d4f' }} />,
      title: t('dispatch.emergency.gasLeak'),
      color: '#fff1f0',
    },
    {
      type: 'urgent_delivery',
      icon: <ClockCircleOutlined style={{ fontSize: 32, color: '#faad14' }} />,
      title: t('dispatch.emergency.urgentDelivery'),
      color: '#fffbe6',
    },
    {
      type: 'customer_emergency',
      icon: <UserOutlined style={{ fontSize: 32, color: '#ff7a45' }} />,
      title: t('dispatch.emergency.customerEmergency'),
      color: '#fff7e6',
    },
    {
      type: 'driver_emergency',
      icon: <CarOutlined style={{ fontSize: 32, color: '#ff4d4f' }} />,
      title: t('dispatch.emergency.driverEmergency'),
      color: '#fff1f0',
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* Emergency Alert Banner */}
      <EmergencyAlertBanner onAlertClick={handleAlertClick} />

      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="large">
              <ExclamationCircleOutlined style={{ fontSize: 32, color: '#ff4d4f' }} />
              <div>
                <h2 style={{ margin: 0 }}>{t('dispatch.emergency.title')}</h2>
                <p style={{ margin: 0, color: '#666' }}>
                  {t('dispatch.emergency.subtitle')}
                </p>
              </div>
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              danger
              size="large"
              icon={<PlusOutlined />}
              onClick={handleCreateEmergency}
            >
              {t('dispatch.emergency.createNew')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dispatch.emergency.totalEmergencies')}
              value={stats.totalEmergencies}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dispatch.emergency.activeEmergencies')}
              value={stats.activeEmergencies}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dispatch.emergency.avgResponseTime')}
              value={stats.averageResponseTime}
              suffix={t('common.unit.minutes')}
              precision={1}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dispatch.emergency.resolvedToday')}
              value={stats.resolvedToday}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Emergency Type Quick Actions */}
      <Card title={t('dispatch.emergency.quickActions')} style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          {emergencyTypes.map((type) => (
            <Col span={6} key={type.type}>
              <Card
                hoverable
                style={{ backgroundColor: type.color, textAlign: 'center' }}
                onClick={() => {
                  setSelectedOrder(undefined);
                  setModalVisible(true);
                }}
              >
                {type.icon}
                <p style={{ marginTop: 8, marginBottom: 0, fontWeight: 500 }}>
                  {type.title}
                </p>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Priority Queue */}
      <PriorityQueueManager
        onDispatch={handleDispatchOrder}
        onViewDetails={(order) => {
          message.info(t('dispatch.emergency.viewingDetails'));
        }}
      />

      {/* Emergency Dispatch Modal */}
      <EmergencyDispatchModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onSubmit={handleEmergencySubmit}
        initialData={selectedOrder ? {
          type: selectedOrder.type,
          priority: selectedOrder.priority,
          customerId: selectedOrder.customerId,
          description: selectedOrder.description,
          contactPhone: selectedOrder.contactPhone,
          address: selectedOrder.address,
        } : undefined}
      />
    </div>
  );
};

export default EmergencyDispatch;