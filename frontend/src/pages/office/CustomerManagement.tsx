import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Card, Input, Tag, Modal, Form, Select, Statistic, Row, Col, message } from 'antd';
import { UserAddOutlined, EditOutlined, DeleteOutlined, SearchOutlined, PhoneOutlined, EnvironmentOutlined, ShoppingCartOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { api } from '../../services/api';

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
  averageFrequency: number; // days
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

const CustomerManagement: React.FC = () => {
  const { t } = useTranslation();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [form] = Form.useForm();

  // Statistics
  const [stats, setStats] = useState({
    totalCustomers: 0,
    activeCustomers: 0,
    newCustomersThisMonth: 0,
    averageOrderFrequency: 0,
  });

  useEffect(() => {
    fetchCustomers();
    fetchStatistics();
  }, []);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/customers');
      setCustomers(response.data);
    } catch (error) {
      message.error(t('customers.fetchError'));
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await api.get('/customers/statistics');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    }
  };

  const handleAdd = () => {
    setSelectedCustomer(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (customer: Customer) => {
    setSelectedCustomer(customer);
    form.setFieldsValue(customer);
    setIsModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: t('customers.deleteConfirm'),
      content: t('customers.deleteWarning'),
      onOk: async () => {
        try {
          await api.delete(`/customers/${id}`);
          message.success(t('customers.deleteSuccess'));
          fetchCustomers();
        } catch (error) {
          message.error(t('customers.deleteError'));
        }
      },
    });
  };

  const handleSubmit = async (values: any) => {
    try {
      if (selectedCustomer) {
        await api.put(`/customers/${selectedCustomer.id}`, values);
        message.success(t('customers.updateSuccess'));
      } else {
        await api.post('/customers', values);
        message.success(t('customers.createSuccess'));
      }
      setIsModalVisible(false);
      fetchCustomers();
      fetchStatistics();
    } catch (error) {
      message.error(t('customers.saveError'));
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'green';
      case 'inactive':
        return 'orange';
      case 'suspended':
        return 'red';
      default:
        return 'default';
    }
  };

  const columns: ColumnsType<Customer> = [
    {
      title: t('customers.name'),
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name, 'zh-TW'),
    },
    {
      title: t('customers.phone'),
      dataIndex: 'phone',
      key: 'phone',
      render: (phone) => (
        <Space>
          <PhoneOutlined />
          {phone}
        </Space>
      ),
    },
    {
      title: t('customers.address'),
      dataIndex: 'address',
      key: 'address',
      render: (address, record) => (
        <Space direction="vertical" size={0}>
          <span>{address}</span>
          <span style={{ fontSize: '12px', color: '#999' }}>
            {record.district} {record.postalCode}
          </span>
        </Space>
      ),
    },
    {
      title: t('customers.type'),
      dataIndex: 'customerType',
      key: 'customerType',
      render: (type) => (
        <Tag color={type === 'commercial' ? 'blue' : 'green'}>
          {t(`customers.type.${type}`)}
        </Tag>
      ),
      filters: [
        { text: t('customers.type.residential'), value: 'residential' },
        { text: t('customers.type.commercial'), value: 'commercial' },
      ],
      onFilter: (value, record) => record.customerType === value,
    },
    {
      title: t('customers.cylinderType'),
      dataIndex: 'cylinderType',
      key: 'cylinderType',
      render: (type) => <Tag>{type}</Tag>,
    },
    {
      title: t('customers.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {t(`customers.status.${status}`)}
        </Tag>
      ),
      filters: [
        { text: t('customers.status.active'), value: 'active' },
        { text: t('customers.status.inactive'), value: 'inactive' },
        { text: t('customers.status.suspended'), value: 'suspended' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: t('customers.lastOrder'),
      dataIndex: 'lastOrderDate',
      key: 'lastOrderDate',
      render: (date) => date ? new Date(date).toLocaleDateString('zh-TW') : '-',
      sorter: (a, b) => new Date(a.lastOrderDate || 0).getTime() - new Date(b.lastOrderDate || 0).getTime(),
    },
    {
      title: t('customers.totalOrders'),
      dataIndex: 'totalOrders',
      key: 'totalOrders',
      sorter: (a, b) => a.totalOrders - b.totalOrders,
    },
    {
      title: t('customers.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('common.edit')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            {t('common.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const filteredCustomers = customers.filter(customer =>
    customer.name.toLowerCase().includes(searchText.toLowerCase()) ||
    customer.phone.includes(searchText) ||
    customer.address.toLowerCase().includes(searchText.toLowerCase())
  );

  return (
    <div className="customer-management">
      <Card title={t('customers.title')}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('customers.stats.total')}
                value={stats.totalCustomers}
                prefix={<UserAddOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('customers.stats.active')}
                value={stats.activeCustomers}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('customers.stats.newThisMonth')}
                value={stats.newCustomersThisMonth}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('customers.stats.avgFrequency')}
                value={stats.averageOrderFrequency}
                suffix={t('common.days')}
                prefix={<ShoppingCartOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder={t('customers.searchPlaceholder')}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
          />
          <Button
            type="primary"
            icon={<UserAddOutlined />}
            onClick={handleAdd}
          >
            {t('customers.addCustomer')}
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={filteredCustomers}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => t('common.totalItems', { total }),
          }}
        />
      </Card>

      <Modal
        title={selectedCustomer ? t('customers.editCustomer') : t('customers.addCustomer')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label={t('customers.name')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="phone"
            label={t('customers.phone')}
            rules={[
              { required: true, message: t('validation.required') },
              { pattern: /^09\d{8}$/, message: t('validation.phoneFormat') },
            ]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="address"
            label={t('customers.address')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Input.TextArea rows={2} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="district"
                label={t('customers.district')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="postalCode"
                label={t('customers.postalCode')}
                rules={[
                  { required: true, message: t('validation.required') },
                  { pattern: /^\d{3,5}$/, message: t('validation.postalCodeFormat') },
                ]}
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
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Select>
                  <Select.Option value="residential">{t('customers.type.residential')}</Select.Option>
                  <Select.Option value="commercial">{t('customers.type.commercial')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="cylinderType"
                label={t('customers.cylinderType')}
                rules={[{ required: true, message: t('validation.required') }]}
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
            name="status"
            label={t('customers.status')}
            rules={[{ required: true, message: t('validation.required') }]}
            initialValue="active"
          >
            <Select>
              <Select.Option value="active">{t('customers.status.active')}</Select.Option>
              <Select.Option value="inactive">{t('customers.status.inactive')}</Select.Option>
              <Select.Option value="suspended">{t('customers.status.suspended')}</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="notes"
            label={t('customers.notes')}
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
    </div>
  );
};

export default CustomerManagement;