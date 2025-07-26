import React, { useState, useEffect } from 'react';
import {
  Card,
  Space,
  Typography,
  Button,
  Badge,
  Timeline,
  List,
  Avatar,
  Statistic,
  Row,
  Col,
  Tag,
  Divider,
  Empty,
  Spin,
} from 'antd';
import {
  HomeOutlined,
  ShoppingCartOutlined,
  HistoryOutlined,
  BellOutlined,
  PhoneOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CarOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { useRealtimeUpdates } from '../../hooks/useRealtimeUpdates';
import api from '../../services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface ActiveOrder {
  id: string;
  orderNumber: string;
  orderDate: string;
  status: string;
  cylinderType: string;
  quantity: number;
  estimatedDelivery?: string;
  driverName?: string;
  driverPhone?: string;
  trackingEnabled: boolean;
}

interface DeliveryHistory {
  id: string;
  orderNumber: string;
  deliveryDate: string;
  cylinderType: string;
  quantity: number;
  amount: number;
}

interface Notification {
  id: string;
  type: 'order' | 'delivery' | 'payment' | 'promotion';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

const CustomerPortal: React.FC = () => {
  const { user } = useAuth();
  const [activeOrders, setActiveOrders] = useState<ActiveOrder[]>([]);
  const [deliveryHistory, setDeliveryHistory] = useState<DeliveryHistory[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [statistics, setStatistics] = useState({
    totalOrders: 0,
    averageConsumption: 0,
    nextPredictedOrder: '',
    loyaltyPoints: 0,
  });
  const [loading, setLoading] = useState(true);

  // Real-time updates
  useRealtimeUpdates({
    onOrderUpdate: (order) => {
      if (order.customer_id === user?.id) {
        fetchActiveOrders();
      }
    },
    onDeliveryUpdate: (delivery) => {
      if (activeOrders.some(o => o.id === delivery.order_id)) {
        fetchActiveOrders();
      }
    },
    enableNotifications: true,
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchActiveOrders(),
        fetchDeliveryHistory(),
        fetchNotifications(),
        fetchStatistics(),
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveOrders = async () => {
    try {
      const response = await api.get('/customers/me/orders/active');
      setActiveOrders(response.data);
    } catch (error) {
      console.error('Failed to fetch active orders:', error);
    }
  };

  const fetchDeliveryHistory = async () => {
    try {
      const response = await api.get('/customers/me/orders/history');
      setDeliveryHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch delivery history:', error);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await api.get('/customers/me/notifications');
      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await api.get('/customers/me/statistics');
      setStatistics(response.data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };

  const handleNewOrder = () => {
    // Navigate to order placement
    window.location.href = '/customer/new-order';
  };

  const handleTrackOrder = (orderId: string) => {
    window.location.href = `/customer/track/${orderId}`;
  };

  const handleCallSupport = () => {
    window.location.href = 'tel:+886212345678';
  };

  const handleReorder = (delivery: DeliveryHistory) => {
    // Store the reorder data in sessionStorage to pass to order page
    const reorderData = {
      cylinderType: delivery.cylinderType,
      quantity: delivery.quantity,
      previousOrderNumber: delivery.orderNumber,
      source: 'reorder'
    };
    sessionStorage.setItem('reorderData', JSON.stringify(reorderData));
    
    // Navigate to new order page
    window.location.href = '/customer/new-order';
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      confirmed: 'processing',
      assigned: 'processing',
      in_delivery: 'warning',
      delivered: 'success',
      cancelled: 'error',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      pending: '待確認',
      confirmed: '已確認',
      assigned: '已指派',
      in_delivery: '配送中',
      delivered: '已送達',
      cancelled: '已取消',
    };
    return texts[status] || status;
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', backgroundColor: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              歡迎回來，{user?.name}！
            </Title>
            <Text type="secondary">
              <EnvironmentOutlined /> {user?.address || '台北市大安區'}
            </Text>
          </div>
          <Space>
            <Badge count={notifications.filter(n => !n.read).length}>
              <Button icon={<BellOutlined />} shape="circle" />
            </Badge>
            <Button icon={<PhoneOutlined />} onClick={handleCallSupport}>
              客服
            </Button>
          </Space>
        </Space>
      </Card>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="總訂單數"
              value={statistics.totalOrders}
              prefix={<ShoppingCartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="月均用量"
              value={statistics.averageConsumption}
              suffix="kg"
              precision={1}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="預測下次訂購"
              value={statistics.nextPredictedOrder}
              valueStyle={{ fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="會員點數"
              value={statistics.loyaltyPoints}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Card
        title="快速操作"
        style={{ marginBottom: 24 }}
        bodyStyle={{ padding: '12px' }}
      >
        <Button
          type="primary"
          size="large"
          block
          icon={<ShoppingCartOutlined />}
          onClick={handleNewOrder}
          style={{ height: 60 }}
        >
          立即訂購瓦斯
        </Button>
      </Card>

      {/* Active Orders */}
      <Card
        title={<Space><CarOutlined /> 進行中的訂單</Space>}
        style={{ marginBottom: 24 }}
      >
        {activeOrders.length > 0 ? (
          <List
            dataSource={activeOrders}
            renderItem={(order) => (
              <List.Item
                actions={[
                  order.trackingEnabled && (
                    <Button
                      type="link"
                      onClick={() => handleTrackOrder(order.id)}
                    >
                      追蹤配送
                    </Button>
                  ),
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Avatar
                      style={{
                        backgroundColor: getStatusColor(order.status) === 'success' ? '#52c41a' : '#1890ff',
                      }}
                      icon={<ShoppingCartOutlined />}
                    />
                  }
                  title={
                    <Space>
                      <Text strong>{order.orderNumber}</Text>
                      <Tag color={getStatusColor(order.status)}>
                        {getStatusText(order.status)}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={0}>
                      <Text>
                        {order.quantity} x {order.cylinderType} 瓦斯桶
                      </Text>
                      {order.estimatedDelivery && (
                        <Text type="secondary">
                          <ClockCircleOutlined /> 預計送達：{order.estimatedDelivery}
                        </Text>
                      )}
                      {order.driverName && (
                        <Text type="secondary">
                          司機：{order.driverName}
                          {order.driverPhone && ` (${order.driverPhone})`}
                        </Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <Empty description="目前沒有進行中的訂單" />
        )}
      </Card>

      {/* Delivery History */}
      <Card
        title={<Space><HistoryOutlined /> 配送記錄</Space>}
        extra={<Button type="link">查看全部</Button>}
      >
        {deliveryHistory.length > 0 ? (
          <Timeline>
            {deliveryHistory.slice(0, 5).map((delivery) => (
              <Timeline.Item
                key={delivery.id}
                dot={<CheckCircleOutlined style={{ fontSize: '16px' }} />}
                color="green"
              >
                <Space direction="vertical" size={0} style={{ width: '100%' }}>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <div>
                      <Text strong>
                        {dayjs(delivery.deliveryDate).format('YYYY-MM-DD')} - {delivery.orderNumber}
                      </Text>
                      <br />
                      <Text type="secondary">
                        {delivery.quantity} x {delivery.cylinderType} | NT$ {delivery.amount}
                      </Text>
                    </div>
                    <Button
                      size="small"
                      type="primary"
                      ghost
                      icon={<ShoppingCartOutlined />}
                      onClick={() => handleReorder(delivery)}
                    >
                      再次訂購
                    </Button>
                  </Space>
                </Space>
              </Timeline.Item>
            ))}
          </Timeline>
        ) : (
          <Empty description="暫無配送記錄" />
        )}
      </Card>
    </div>
  );
};

export default CustomerPortal;