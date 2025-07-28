import React, { useState, useEffect } from 'react';
import {
  Card,
  List,
  Tag,
  Space,
  Button,
  Badge,
  Typography,
  Empty,
  Tooltip,
  message,
  Popconfirm,
} from 'antd';
import {
  FireOutlined,
  ClockCircleOutlined,
  UserOutlined,
  CarOutlined,
  PhoneOutlined,
  EnvironmentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useWebSocketContext } from '../../../contexts/WebSocketContext';

const { Text, Title } = Typography;

export interface EmergencyOrder {
  id: string;
  type: 'gas_leak' | 'urgent_delivery' | 'customer_emergency' | 'driver_emergency';
  priority: 'high' | 'critical';
  status: 'pending' | 'assigned' | 'dispatched' | 'completed' | 'cancelled';
  customerId: number;
  customerName: string;
  customerCode: string;
  address: string;
  contactPhone: string;
  description: string;
  createdAt: string;
  assignedDriverId?: number;
  assignedDriverName?: string;
  dispatchedAt?: string;
  completedAt?: string;
  estimatedArrival?: string;
  location?: {
    lat: number;
    lng: number;
  };
}

interface PriorityQueueManagerProps {
  onDispatch?: (order: EmergencyOrder) => void;
  onViewDetails?: (order: EmergencyOrder) => void;
}

const PriorityQueueManager: React.FC<PriorityQueueManagerProps> = ({
  onDispatch,
  onViewDetails,
}) => {
  const { t } = useTranslation();
  const { socket, isConnected } = useWebSocketContext();
  const [emergencyQueue, setEmergencyQueue] = useState<EmergencyOrder[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEmergencyQueue();
  }, []);

  useEffect(() => {
    if (!socket || !isConnected) return;

    // Listen for emergency queue updates
    const handleQueueUpdate = (data: any) => {
      if (data.type === 'new') {
        setEmergencyQueue(prev => [data.order, ...prev]);
        message.warning(t('dispatch.emergency.newEmergencyOrder'));
      } else if (data.type === 'update') {
        setEmergencyQueue(prev =>
          prev.map(order => (order.id === data.order.id ? data.order : order))
        );
      } else if (data.type === 'remove') {
        setEmergencyQueue(prev => prev.filter(order => order.id !== data.orderId));
      }
    };

    socket.on('emergency:queue:update', handleQueueUpdate);

    return () => {
      socket.off('emergency:queue:update', handleQueueUpdate);
    };
  }, [socket, isConnected, t]);

  const fetchEmergencyQueue = async () => {
    setLoading(true);
    try {
      // Mock data for demonstration
      const mockQueue: EmergencyOrder[] = [
        {
          id: 'em-001',
          type: 'gas_leak',
          priority: 'critical',
          status: 'pending',
          customerId: 1001,
          customerName: '王小明',
          customerCode: 'C-001',
          address: '台北市信義區信義路五段7號',
          contactPhone: '0912-345-678',
          description: '疑似瓦斯洩漏，有濃烈瓦斯味',
          createdAt: new Date(Date.now() - 5 * 60000).toISOString(),
          location: { lat: 25.0330, lng: 121.5654 },
        },
        {
          id: 'em-002',
          type: 'urgent_delivery',
          priority: 'high',
          status: 'assigned',
          customerId: 1002,
          customerName: '林美華',
          customerCode: 'C-002',
          address: '台北市大安區復興南路二段123號',
          contactPhone: '0923-456-789',
          description: '餐廳急需瓦斯，晚餐時段前需要送達',
          createdAt: new Date(Date.now() - 15 * 60000).toISOString(),
          assignedDriverId: 101,
          assignedDriverName: '張師傅',
          dispatchedAt: new Date(Date.now() - 10 * 60000).toISOString(),
          estimatedArrival: new Date(Date.now() + 20 * 60000).toISOString(),
        },
      ];
      setEmergencyQueue(mockQueue);
    } catch (error) {
      message.error(t('common.error.fetchFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (orderId: string) => {
    try {
      // API call to complete emergency order
      setEmergencyQueue(prev =>
        prev.map(order =>
          order.id === orderId
            ? { ...order, status: 'completed', completedAt: new Date().toISOString() }
            : order
        )
      );
      message.success(t('dispatch.emergency.orderCompleted'));
    } catch (error) {
      message.error(t('common.error.updateFailed'));
    }
  };

  const handleCancel = async (orderId: string) => {
    try {
      // API call to cancel emergency order
      setEmergencyQueue(prev => prev.filter(order => order.id !== orderId));
      message.info(t('dispatch.emergency.orderCancelled'));
    } catch (error) {
      message.error(t('common.error.updateFailed'));
    }
  };

  const getTypeIcon = (type: EmergencyOrder['type']) => {
    switch (type) {
      case 'gas_leak':
        return <FireOutlined style={{ color: '#ff4d4f' }} />;
      case 'urgent_delivery':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'customer_emergency':
        return <UserOutlined style={{ color: '#ff7a45' }} />;
      case 'driver_emergency':
        return <CarOutlined style={{ color: '#ff4d4f' }} />;
    }
  };

  const getTypeLabel = (type: EmergencyOrder['type']) => {
    switch (type) {
      case 'gas_leak':
        return t('dispatch.emergency.gasLeak');
      case 'urgent_delivery':
        return t('dispatch.emergency.urgentDelivery');
      case 'customer_emergency':
        return t('dispatch.emergency.customerEmergency');
      case 'driver_emergency':
        return t('dispatch.emergency.driverEmergency');
    }
  };

  const getStatusColor = (status: EmergencyOrder['status']) => {
    switch (status) {
      case 'pending':
        return 'red';
      case 'assigned':
        return 'orange';
      case 'dispatched':
        return 'blue';
      case 'completed':
        return 'green';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  const getTimeSince = (dateString: string) => {
    const minutes = Math.floor(
      (new Date().getTime() - new Date(dateString).getTime()) / 60000
    );
    if (minutes < 60) {
      return t('common.time.minutesAgo', { count: minutes });
    }
    const hours = Math.floor(minutes / 60);
    return t('common.time.hoursAgo', { count: hours });
  };

  const sortedQueue = [...emergencyQueue].sort((a, b) => {
    // Sort by priority first (critical > high)
    if (a.priority !== b.priority) {
      return a.priority === 'critical' ? -1 : 1;
    }
    // Then by creation time (older first)
    return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
  });

  return (
    <Card
      title={
        <Space>
          <Badge count={emergencyQueue.filter(o => o.status === 'pending').length} offset={[10, 0]}>
            <Title level={5} style={{ margin: 0 }}>
              {t('dispatch.emergency.priorityQueue')}
            </Title>
          </Badge>
        </Space>
      }
      extra={
        <Button type="link" onClick={fetchEmergencyQueue}>
          {t('common.action.refresh')}
        </Button>
      }
      loading={loading}
    >
      {sortedQueue.length === 0 ? (
        <Empty
          description={t('dispatch.emergency.noEmergencyOrders')}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <List
          dataSource={sortedQueue}
          renderItem={(order) => (
            <List.Item
              key={order.id}
              actions={[
                order.status === 'pending' && onDispatch && (
                  <Button
                    type="primary"
                    size="small"
                    danger={order.priority === 'critical'}
                    onClick={() => onDispatch(order)}
                  >
                    {t('dispatch.emergency.dispatch')}
                  </Button>
                ),
                order.status === 'dispatched' && (
                  <Tooltip title={t('dispatch.emergency.markComplete')}>
                    <Button
                      type="link"
                      icon={<CheckCircleOutlined />}
                      onClick={() => handleComplete(order.id)}
                    />
                  </Tooltip>
                ),
                onViewDetails && (
                  <Button
                    type="link"
                    icon={<RightOutlined />}
                    onClick={() => onViewDetails(order)}
                  >
                    {t('common.action.details')}
                  </Button>
                ),
                order.status === 'pending' && (
                  <Popconfirm
                    title={t('dispatch.emergency.cancelConfirm')}
                    onConfirm={() => handleCancel(order.id)}
                  >
                    <Button type="link" danger icon={<CloseCircleOutlined />} />
                  </Popconfirm>
                ),
              ].filter(Boolean)}
            >
              <List.Item.Meta
                avatar={
                  <div style={{ fontSize: 24 }}>
                    {getTypeIcon(order.type)}
                  </div>
                }
                title={
                  <Space>
                    <Tag color={order.priority === 'critical' ? 'red' : 'orange'}>
                      {order.priority === 'critical'
                        ? t('dispatch.emergency.priorityCritical')
                        : t('dispatch.emergency.priorityHigh')}
                    </Tag>
                    <Text strong>{getTypeLabel(order.type)}</Text>
                    <Tag color={getStatusColor(order.status)}>
                      {t(`dispatch.emergency.status.${order.status}`)}
                    </Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Space>
                      <UserOutlined />
                      <Text>{order.customerName} ({order.customerCode})</Text>
                      <PhoneOutlined />
                      <Text>{order.contactPhone}</Text>
                    </Space>
                    <Space>
                      <EnvironmentOutlined />
                      <Text type="secondary">{order.address}</Text>
                    </Space>
                    <Text>{order.description}</Text>
                    <Space split={<span>•</span>}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('dispatch.emergency.created')}: {getTimeSince(order.createdAt)}
                      </Text>
                      {order.assignedDriverName && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {t('dispatch.emergency.assignedTo')}: {order.assignedDriverName}
                        </Text>
                      )}
                      {order.estimatedArrival && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {t('dispatch.emergency.eta')}: {new Date(order.estimatedArrival).toLocaleTimeString('zh-TW')}
                        </Text>
                      )}
                    </Space>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

export default PriorityQueueManager;