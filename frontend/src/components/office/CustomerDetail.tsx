import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Tabs,
  Form,
  Input,
  Select,
  Button,
  Space,
  Table,
  Tag,
  Card,
  Statistic,
  Row,
  Col,
  
  Typography,
  message,
  Spin,
  InputNumber,
  Empty,
} from 'antd';
import {
  UserOutlined,
  PhoneOutlined,
  EnvironmentOutlined,
  ShoppingCartOutlined,
  CalendarOutlined,
  DollarOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import dayjs from 'dayjs';
import { features } from '../../config/features';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface Customer {
  id: string;
  name: string;
  phone: string;
  address: string;
  district: string;
  postalCode: string;
  customerType: 'residential' | 'commercial';
  status: 'active' | 'inactive' | 'suspended';
  cylinderType: '20kg' | '16kg' | '50kg';
  lastOrderDate?: string;
  totalOrders: number;
  averageFrequency: number;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

interface Order {
  id: string;
  orderNumber: string;
  orderDate: string;
  deliveryDate?: string;
  status: string;
  cylinderType: string;
  quantity: number;
  totalAmount: number;
  paymentStatus: string;
}

interface InventoryItem {
  cylinderType: '20kg' | '16kg' | '50kg' | '10kg' | '4kg';
  quantity: number;
  lastRefillDate?: string;
  estimatedEmptyDate?: string;
}

interface CustomerDetailProps {
  visible: boolean;
  customer: Customer | null;
  onClose: () => void;
  onUpdate: (customer: Customer) => void;
}

const CustomerDetail: React.FC<CustomerDetailProps> = ({
  visible,
  customer,
  onClose,
  onUpdate,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('info');
  const [editing, setEditing] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [loadingInventory, setLoadingInventory] = useState(false);

  useEffect(() => {
    if (customer && visible) {
      form.setFieldsValue(customer);
      if (activeTab === 'orders') {
        fetchOrderHistory();
      } else if (activeTab === 'inventory') {
        fetchInventory();
      }
    }
  }, [customer, visible, activeTab]);

  const fetchOrderHistory = async () => {
    if (!customer) return;
    
    setLoadingOrders(true);
    try {
      const response = await api.get(`/customers/${customer.id}/orders`);
      setOrders(response.data);
    } catch (error) {
      // If endpoint doesn't exist, show mock data for demo
      console.error('Failed to fetch order history:', error);
      // Mock data for demonstration
      setOrders([
        {
          id: '1',
          orderNumber: 'LG20240120001',
          orderDate: '2024-01-20',
          deliveryDate: '2024-01-21',
          status: 'delivered',
          cylinderType: customer.cylinderType,
          quantity: 1,
          totalAmount: 800,
          paymentStatus: 'paid',
        },
        {
          id: '2',
          orderNumber: 'LG20240115001',
          orderDate: '2024-01-15',
          deliveryDate: '2024-01-16',
          status: 'delivered',
          cylinderType: customer.cylinderType,
          quantity: 1,
          totalAmount: 800,
          paymentStatus: 'paid',
        },
      ]);
    } finally {
      setLoadingOrders(false);
    }
  };

  const fetchInventory = async () => {
    if (!customer) return;
    
    setLoadingInventory(true);
    try {
      const response = await api.get(`/customers/${customer.id}/inventory`);
      setInventory(response.data);
    } catch (error) {
      // If endpoint doesn't exist, show mock data for demo
      console.error('Failed to fetch inventory:', error);
      // Mock data for demonstration
      setInventory([
        {
          cylinderType: customer.cylinderType,
          quantity: 1,
          lastRefillDate: '2024-01-21',
          estimatedEmptyDate: '2024-02-21',
        },
      ]);
    } finally {
      setLoadingInventory(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      // Transform to backend schema if needed
      const updatedCustomer = { ...customer, ...values };
      
      // Call parent update function
      onUpdate(updatedCustomer);
      setEditing(false);
      message.success(t('customers.updateSuccess'));
    } catch (error) {
      message.error(t('customers.updateError'));
    }
  };

  const orderColumns: ColumnsType<Order> = [
    {
      title: t('orders.orderNumber'),
      dataIndex: 'orderNumber',
      key: 'orderNumber',
    },
    {
      title: t('orders.orderDate'),
      dataIndex: 'orderDate',
      key: 'orderDate',
      render: (date) => dayjs(date).format('YYYY/MM/DD'),
    },
    {
      title: t('orders.deliveryDate'),
      dataIndex: 'deliveryDate',
      key: 'deliveryDate',
      render: (date) => date ? dayjs(date).format('YYYY/MM/DD') : '-',
    },
    {
      title: t('orders.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusColors: Record<string, string> = {
          pending: 'orange',
          delivered: 'green',
          cancelled: 'red',
        };
        return <Tag color={statusColors[status] || 'default'}>{t(`orders.status.${status}`)}</Tag>;
      },
    },
    {
      title: t('orders.product'),
      key: 'product',
      render: (_, record) => `${record.cylinderType} x ${record.quantity}`,
    },
    {
      title: t('orders.amount'),
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      render: (amount) => `NT$ ${amount.toLocaleString()}`,
    },
  ].filter(column => {
    // Filter out payment-related columns if payment features are disabled
    if (!features.anyPaymentFeature) {
      return column.key !== 'totalAmount';
    }
    return true;
  });

  const inventoryColumns: ColumnsType<InventoryItem> = [
    {
      title: t('inventory.cylinderType'),
      dataIndex: 'cylinderType',
      key: 'cylinderType',
    },
    {
      title: t('inventory.quantity'),
      dataIndex: 'quantity',
      key: 'quantity',
      render: (quantity) => (
        <Space>
          <span>{quantity}</span>
          {editing && (
            <InputNumber
              min={0}
              max={10}
              defaultValue={quantity}
              size="small"
              onChange={(value) => {
                // Handle inventory update
                console.log('Update quantity:', value);
              }}
            />
          )}
        </Space>
      ),
    },
    {
      title: t('inventory.lastRefillDate'),
      dataIndex: 'lastRefillDate',
      key: 'lastRefillDate',
      render: (date) => date ? dayjs(date).format('YYYY/MM/DD') : '-',
    },
    {
      title: t('inventory.estimatedEmptyDate'),
      dataIndex: 'estimatedEmptyDate',
      key: 'estimatedEmptyDate',
      render: (date) => date ? dayjs(date).format('YYYY/MM/DD') : '-',
    },
  ];

  if (!customer) return null;

  return (
    <Drawer
      title={
        <Space>
          <UserOutlined />
          {customer.name}
          <Tag color={customer.status === 'active' ? 'green' : 'red'}>
            {t(`customers.status.${customer.status}`)}
          </Tag>
        </Space>
      }
      placement="right"
      width={720}
      open={visible}
      onClose={onClose}
      extra={
        <Space>
          {activeTab === 'info' && !editing && (
            <Button icon={<EditOutlined />} onClick={() => setEditing(true)}>
              {t('common.edit')}
            </Button>
          )}
          {activeTab === 'info' && editing && (
            <>
              <Button icon={<SaveOutlined />} type="primary" onClick={handleSave}>
                {t('common.save')}
              </Button>
              <Button icon={<CloseOutlined />} onClick={() => setEditing(false)}>
                {t('common.cancel')}
              </Button>
            </>
          )}
        </Space>
      }
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={t('customers.tabs.info')} key="info">
          <Form form={form} layout="vertical" disabled={!editing}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="name"
                  label={t('customers.name')}
                  rules={[{ required: true }]}
                >
                  <Input prefix={<UserOutlined />} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="phone"
                  label={t('customers.phone')}
                  rules={[{ required: true }]}
                >
                  <Input prefix={<PhoneOutlined />} />
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item
              name="address"
              label={t('customers.address')}
              rules={[{ required: true }]}
            >
              <Input prefix={<EnvironmentOutlined />} />
            </Form.Item>
            
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="district"
                  label={t('customers.district')}
                  rules={[{ required: true }]}
                >
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="postalCode"
                  label={t('customers.postalCode')}
                >
                  <Input />
                </Form.Item>
              </Col>
            </Row>
            
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="customerType"
                  label={t('customers.type')}
                  rules={[{ required: true }]}
                >
                  <Select>
                    <Select.Option value="residential">{t('customers.types.residential')}</Select.Option>
                    <Select.Option value="commercial">{t('customers.types.commercial')}</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="cylinderType"
                  label={t('customers.cylinderType')}
                  rules={[{ required: true }]}
                >
                  <Select>
                    <Select.Option value="20kg">20kg</Select.Option>
                    <Select.Option value="16kg">16kg</Select.Option>
                    <Select.Option value="50kg">50kg</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item
              name="notes"
              label={t('customers.notes')}
            >
              <Input.TextArea rows={3} />
            </Form.Item>
            
            {!editing && (
              <Card>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title={t('customers.stats.totalOrders')}
                      value={customer.totalOrders}
                      prefix={<ShoppingCartOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={t('customers.stats.averageFrequency')}
                      value={customer.averageFrequency}
                      suffix={t('common.days')}
                      prefix={<CalendarOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={t('customers.stats.lastOrderDate')}
                      value={customer.lastOrderDate ? dayjs(customer.lastOrderDate).format('MM/DD') : '-'}
                      prefix={<CalendarOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title={t('customers.stats.memberSince')}
                      value={dayjs(customer.createdAt).format('YYYY')}
                      prefix={<UserOutlined />}
                    />
                  </Col>
                </Row>
              </Card>
            )}
          </Form>
        </TabPane>
        
        <TabPane tab={t('customers.tabs.orders')} key="orders">
          <Spin spinning={loadingOrders}>
            {orders.length > 0 ? (
              <Table
                columns={orderColumns}
                dataSource={orders}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <Empty description={t('customers.noOrders')} />
            )}
          </Spin>
        </TabPane>
        
        <TabPane tab={t('customers.tabs.inventory')} key="inventory">
          <Spin spinning={loadingInventory}>
            {inventory.length > 0 ? (
              <>
                <Table
                  columns={inventoryColumns}
                  dataSource={inventory}
                  rowKey="cylinderType"
                  pagination={false}
                />
                <Card style={{ marginTop: 16 }}>
                  <Title level={5}>{t('inventory.management')}</Title>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button type="primary" icon={<ShoppingCartOutlined />}>
                      {t('inventory.requestRefill')}
                    </Button>
                    <Text type="secondary">
                      {t('inventory.refillNote')}
                    </Text>
                  </Space>
                </Card>
              </>
            ) : (
              <Empty description={t('customers.noInventory')} />
            )}
          </Spin>
        </TabPane>
      </Tabs>
    </Drawer>
  );
};

export default CustomerDetail;