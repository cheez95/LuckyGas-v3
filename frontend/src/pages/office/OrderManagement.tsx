import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Card, Input, Tag, Modal, Form, Select, DatePicker, Row, Col, message, Statistic, Timeline, Drawer } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ClockCircleOutlined, CheckCircleOutlined, CarOutlined, ExclamationCircleOutlined, EyeOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { api } from '../../services/api';
import dayjs from 'dayjs';
import { useRealtimeUpdates } from '../../hooks/useRealtimeUpdates';

interface Order {
  id: string;
  orderNumber: string;
  customerId: string;
  customerName: string;
  customerPhone: string;
  customerAddress: string;
  orderDate: string;
  deliveryDate?: string;
  status: 'pending' | 'confirmed' | 'assigned' | 'in_delivery' | 'delivered' | 'cancelled';
  priority: 'normal' | 'urgent' | 'scheduled';
  cylinderType: '20kg' | '16kg' | '50kg';
  quantity: number;
  unitPrice: number;
  totalAmount: number;
  paymentMethod: 'cash' | 'transfer' | 'credit';
  paymentStatus: 'pending' | 'paid' | 'partial';
  driverId?: string;
  driverName?: string;
  routeId?: string;
  deliveryNotes?: string;
  createdAt: string;
  updatedAt: string;
}

interface OrderTimeline {
  timestamp: string;
  status: string;
  description: string;
  user?: string;
}

const OrderManagement: React.FC = () => {
  const { t } = useTranslation();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isDetailDrawerVisible, setIsDetailDrawerVisible] = useState(false);
  const [orderTimeline, setOrderTimeline] = useState<OrderTimeline[]>([]);
  const [searchText, setSearchText] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [form] = Form.useForm();

  // Statistics
  const [stats, setStats] = useState({
    totalOrders: 0,
    pendingOrders: 0,
    todayDeliveries: 0,
    monthlyRevenue: 0,
  });

  // Real-time updates
  const { subscribeToOrder } = useRealtimeUpdates({
    onOrderUpdate: (updatedOrder) => {
      setOrders(prevOrders => {
        const index = prevOrders.findIndex(o => o.id === updatedOrder.id);
        if (index >= 0) {
          const newOrders = [...prevOrders];
          newOrders[index] = { ...newOrders[index], ...updatedOrder };
          return newOrders;
        } else {
          return [updatedOrder, ...prevOrders];
        }
      });
      
      // Update selected order if it's the one being viewed
      if (selectedOrder?.id === updatedOrder.id) {
        setSelectedOrder(prev => ({ ...prev, ...updatedOrder }));
      }
      
      // Refresh statistics
      fetchStatistics();
    },
    enableNotifications: true,
  });

  useEffect(() => {
    fetchOrders();
    fetchStatistics();
  }, []);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const response = await api.get('/orders');
      setOrders(response.data);
    } catch (error) {
      message.error(t('orders.fetchError'));
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await api.get('/orders/statistics');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };

  const fetchOrderTimeline = async (orderId: string) => {
    try {
      const response = await api.get(`/orders/${orderId}/timeline`);
      setOrderTimeline(response.data);
    } catch (error) {
      console.error('Failed to fetch timeline:', error);
    }
  };

  const handleAdd = () => {
    setSelectedOrder(null);
    form.resetFields();
    form.setFieldValue('orderDate', dayjs());
    form.setFieldValue('priority', 'normal');
    form.setFieldValue('quantity', 1);
    form.setFieldValue('paymentMethod', 'cash');
    form.setFieldValue('paymentStatus', 'pending');
    setIsModalVisible(true);
  };

  const handleEdit = (order: Order) => {
    setSelectedOrder(order);
    form.setFieldsValue({
      ...order,
      orderDate: dayjs(order.orderDate),
      deliveryDate: order.deliveryDate ? dayjs(order.deliveryDate) : null,
    });
    setIsModalVisible(true);
  };

  const handleViewDetail = async (order: Order) => {
    setSelectedOrder(order);
    await fetchOrderTimeline(order.id);
    setIsDetailDrawerVisible(true);
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: t('orders.deleteConfirm'),
      content: t('orders.deleteWarning'),
      onOk: async () => {
        try {
          await api.delete(`/orders/${id}`);
          message.success(t('orders.deleteSuccess'));
          fetchOrders();
        } catch (error) {
          message.error(t('orders.deleteError'));
        }
      },
    });
  };

  const handleSubmit = async (values: any) => {
    try {
      const orderData = {
        ...values,
        orderDate: values.orderDate.format('YYYY-MM-DD'),
        deliveryDate: values.deliveryDate ? values.deliveryDate.format('YYYY-MM-DD') : null,
        totalAmount: values.quantity * values.unitPrice,
      };

      if (selectedOrder) {
        await api.put(`/orders/${selectedOrder.id}`, orderData);
        message.success(t('orders.updateSuccess'));
      } else {
        await api.post('/orders', orderData);
        message.success(t('orders.createSuccess'));
      }
      setIsModalVisible(false);
      fetchOrders();
      fetchStatistics();
    } catch (error) {
      message.error(t('orders.saveError'));
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'orange',
      confirmed: 'blue',
      assigned: 'purple',
      in_delivery: 'cyan',
      delivered: 'green',
      cancelled: 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusIcon = (status: string) => {
    const icons: Record<string, React.ReactNode> = {
      pending: <ClockCircleOutlined />,
      confirmed: <CheckCircleOutlined />,
      assigned: <CarOutlined />,
      in_delivery: <CarOutlined />,
      delivered: <CheckCircleOutlined />,
      cancelled: <ExclamationCircleOutlined />,
    };
    return icons[status] || null;
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      normal: 'default',
      urgent: 'red',
      scheduled: 'blue',
    };
    return colors[priority] || 'default';
  };

  const columns: ColumnsType<Order> = [
    {
      title: t('orders.orderNumber'),
      dataIndex: 'orderNumber',
      key: 'orderNumber',
      fixed: 'left',
      width: 120,
    },
    {
      title: t('orders.customer'),
      key: 'customer',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <span>{record.customerName}</span>
          <span style={{ fontSize: '12px', color: '#999' }}>{record.customerPhone}</span>
        </Space>
      ),
    },
    {
      title: t('orders.orderDate'),
      dataIndex: 'orderDate',
      key: 'orderDate',
      render: (date) => dayjs(date).format('YYYY/MM/DD'),
      sorter: (a, b) => new Date(a.orderDate).getTime() - new Date(b.orderDate).getTime(),
    },
    {
      title: t('orders.deliveryDate'),
      dataIndex: 'deliveryDate',
      key: 'deliveryDate',
      render: (date) => date ? dayjs(date).format('YYYY/MM/DD') : '-',
    },
    {
      title: t('orders.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority) => (
        <Tag color={getPriorityColor(priority)}>
          {t(`orders.priority.${priority}`)}
        </Tag>
      ),
      filters: [
        { text: t('orders.priority.normal'), value: 'normal' },
        { text: t('orders.priority.urgent'), value: 'urgent' },
        { text: t('orders.priority.scheduled'), value: 'scheduled' },
      ],
      onFilter: (value, record) => record.priority === value,
    },
    {
      title: t('orders.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag icon={getStatusIcon(status)} color={getStatusColor(status)}>
          {t(`orders.status.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('orders.product'),
      key: 'product',
      render: (_, record) => (
        <Space>
          <Tag>{record.cylinderType}</Tag>
          <span>x {record.quantity}</span>
        </Space>
      ),
    },
    {
      title: t('orders.amount'),
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      render: (amount) => `NT$ ${amount.toLocaleString()}`,
      sorter: (a, b) => a.totalAmount - b.totalAmount,
    },
    {
      title: t('orders.payment'),
      key: 'payment',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag>{t(`orders.paymentMethod.${record.paymentMethod}`)}</Tag>
          <Tag color={record.paymentStatus === 'paid' ? 'green' : 'orange'}>
            {t(`orders.paymentStatus.${record.paymentStatus}`)}
          </Tag>
        </Space>
      ),
    },
    {
      title: t('orders.driver'),
      dataIndex: 'driverName',
      key: 'driverName',
      render: (name) => name || '-',
    },
    {
      title: t('orders.actions'),
      key: 'actions',
      fixed: 'right',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          />
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          />
        </Space>
      ),
    },
  ];

  const filteredOrders = orders.filter(order => {
    const matchesSearch = 
      order.orderNumber.toLowerCase().includes(searchText.toLowerCase()) ||
      order.customerName.toLowerCase().includes(searchText.toLowerCase()) ||
      order.customerPhone.includes(searchText);
    
    const matchesStatus = filterStatus === 'all' || order.status === filterStatus;
    
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="order-management">
      <Card title={t('orders.title')}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('orders.stats.total')}
                value={stats.totalOrders}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('orders.stats.pending')}
                value={stats.pendingOrders}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('orders.stats.todayDeliveries')}
                value={stats.todayDeliveries}
                valueStyle={{ color: '#1890ff' }}
                prefix={<CarOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('orders.stats.monthlyRevenue')}
                value={stats.monthlyRevenue}
                prefix="NT$"
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder={t('orders.searchPlaceholder')}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
          />
          <Select
            value={filterStatus}
            onChange={setFilterStatus}
            style={{ width: 150 }}
          >
            <Select.Option value="all">{t('orders.allStatuses')}</Select.Option>
            <Select.Option value="pending">{t('orders.status.pending')}</Select.Option>
            <Select.Option value="confirmed">{t('orders.status.confirmed')}</Select.Option>
            <Select.Option value="assigned">{t('orders.status.assigned')}</Select.Option>
            <Select.Option value="in_delivery">{t('orders.status.in_delivery')}</Select.Option>
            <Select.Option value="delivered">{t('orders.status.delivered')}</Select.Option>
            <Select.Option value="cancelled">{t('orders.status.cancelled')}</Select.Option>
          </Select>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            {t('orders.createOrder')}
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={filteredOrders}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => t('common.totalItems', { total }),
          }}
        />
      </Card>

      <Modal
        title={selectedOrder ? t('orders.editOrder') : t('orders.createOrder')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customerId"
                label={t('orders.customer')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select
                  showSearch
                  placeholder={t('orders.selectCustomer')}
                  optionFilterProp="children"
                >
                  {/* Customer options will be loaded from API */}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="orderDate"
                label={t('orders.orderDate')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="deliveryDate"
                label={t('orders.deliveryDate')}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="priority"
                label={t('orders.priority')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select>
                  <Select.Option value="normal">{t('orders.priority.normal')}</Select.Option>
                  <Select.Option value="urgent">{t('orders.priority.urgent')}</Select.Option>
                  <Select.Option value="scheduled">{t('orders.priority.scheduled')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="cylinderType"
                label={t('orders.cylinderType')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select>
                  <Select.Option value="20kg">20kg</Select.Option>
                  <Select.Option value="16kg">16kg</Select.Option>
                  <Select.Option value="50kg">50kg</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="quantity"
                label={t('orders.quantity')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Input type="number" min={1} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="unitPrice"
                label={t('orders.unitPrice')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Input type="number" prefix="NT$" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="paymentMethod"
                label={t('orders.paymentMethod')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select>
                  <Select.Option value="cash">{t('orders.paymentMethod.cash')}</Select.Option>
                  <Select.Option value="transfer">{t('orders.paymentMethod.transfer')}</Select.Option>
                  <Select.Option value="credit">{t('orders.paymentMethod.credit')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="paymentStatus"
                label={t('orders.paymentStatus')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select>
                  <Select.Option value="pending">{t('orders.paymentStatus.pending')}</Select.Option>
                  <Select.Option value="paid">{t('orders.paymentStatus.paid')}</Select.Option>
                  <Select.Option value="partial">{t('orders.paymentStatus.partial')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="deliveryNotes"
            label={t('orders.deliveryNotes')}
          >
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {t('common.save')}
              </Button>
              <Button onClick={() => setIsModalVisible(false)}>
                {t('common.cancel')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={t('orders.orderDetail')}
        placement="right"
        width={600}
        open={isDetailDrawerVisible}
        onClose={() => setIsDetailDrawerVisible(false)}
      >
        {selectedOrder && (
          <>
            <Card title={t('orders.orderInfo')} style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <strong>{t('orders.orderNumber')}:</strong> {selectedOrder.orderNumber}
                </Col>
                <Col span={12}>
                  <strong>{t('orders.status')}:</strong>{' '}
                  <Tag color={getStatusColor(selectedOrder.status)}>
                    {t(`orders.status.${selectedOrder.status}`)}
                  </Tag>
                </Col>
                <Col span={12}>
                  <strong>{t('orders.customer')}:</strong> {selectedOrder.customerName}
                </Col>
                <Col span={12}>
                  <strong>{t('orders.phone')}:</strong> {selectedOrder.customerPhone}
                </Col>
                <Col span={24}>
                  <strong>{t('orders.address')}:</strong> {selectedOrder.customerAddress}
                </Col>
                <Col span={12}>
                  <strong>{t('orders.product')}:</strong> {selectedOrder.cylinderType} x {selectedOrder.quantity}
                </Col>
                <Col span={12}>
                  <strong>{t('orders.amount')}:</strong> NT$ {selectedOrder.totalAmount.toLocaleString()}
                </Col>
              </Row>
            </Card>

            <Card title={t('orders.timeline')}>
              <Timeline>
                {orderTimeline.map((item, index) => (
                  <Timeline.Item
                    key={index}
                    color={item.status === 'delivered' ? 'green' : 'blue'}
                  >
                    <p>{item.description}</p>
                    <p style={{ fontSize: '12px', color: '#999' }}>
                      {dayjs(item.timestamp).format('YYYY/MM/DD HH:mm')}
                      {item.user && ` - ${item.user}`}
                    </p>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default OrderManagement;