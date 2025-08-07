import React, { useState, useEffect } from 'react';
import { Table, Card, Input, Button, Space, Typography, Tag, message, Modal, Form, Row, Col, Switch, InputNumber, TimePicker, Select } from 'antd';
import { SearchOutlined, PlusOutlined, EditOutlined, ExclamationCircleOutlined, ContainerOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { customerService } from '../../services/customer.service';
import { Customer } from '../../types/order';
import CustomerInventory from './CustomerInventory';
import { features } from '../../config/features';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

const CustomerList: React.FC = () => {
  const { t } = useTranslation();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [inventoryModalVisible, setInventoryModalVisible] = useState(false);
  const [form] = Form.useForm();

  // Fetch customers from API
  const fetchCustomers = async (search?: string, page: number = 1, size: number = 10) => {
    setLoading(true);
    try {
      const params = {
        skip: (page - 1) * size,
        limit: size,
        search: search || undefined,
      };
      const response = await customerService.getCustomers(params);
      setCustomers(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('載入客戶資料失敗');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers(searchText, currentPage, pageSize);
  }, [currentPage, pageSize]);

  // Handle customer creation/update
  const handleSubmit = async (values: any) => {
    try {
      const customerData = {
        ...values,
        delivery_time_start: values.delivery_time?.[0]?.format('HH:mm'),
        delivery_time_end: values.delivery_time?.[1]?.format('HH:mm'),
      };
      delete customerData.delivery_time;

      if (isEditMode && selectedCustomer) {
        await customerService.updateCustomer(selectedCustomer.id, customerData);
        message.success('客戶更新成功');
      } else {
        await customerService.createCustomer(customerData);
        message.success('客戶創建成功');
      }
      
      setIsModalVisible(false);
      form.resetFields();
      fetchCustomers(searchText, currentPage, pageSize);
    } catch (error: any) {
      // Check for duplicate customer code error
      if (error.message?.includes('客戶代碼已存在')) {
        message.error('此客戶編號已存在，請使用其他編號');
      } else {
        message.error(isEditMode ? '更新客戶失敗' : '創建客戶失敗');
      }
    }
  };

  // Handle edit
  const handleEdit = (customer: Customer) => {
    setSelectedCustomer(customer);
    setIsEditMode(true);
    form.setFieldsValue({
      ...customer,
      delivery_time: customer.delivery_time_start && customer.delivery_time_end
        ? [dayjs(customer.delivery_time_start, 'HH:mm'), dayjs(customer.delivery_time_end, 'HH:mm')]
        : undefined,
    });
    setIsModalVisible(true);
  };

  // Handle delete
  const handleDelete = (customer: Customer) => {
    confirm({
      title: '確認刪除客戶',
      icon: <ExclamationCircleOutlined />,
      content: `確定要刪除客戶 ${customer.short_name} 嗎？此操作無法復原。`,
      okText: '確認',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await customerService.deleteCustomer(customer.id);
          message.success('客戶已刪除');
          fetchCustomers(searchText, currentPage, pageSize);
        } catch (error) {
          message.error('刪除客戶失敗');
        }
      },
    });
  };

  const handleViewInventory = (customer: Customer) => {
    setSelectedCustomer(customer);
    setInventoryModalVisible(true);
  };

  const columns: ColumnsType<Customer> = [
    {
      title: t('customer.code'),
      dataIndex: 'customer_code',
      key: 'customer_code',
      width: 120,
      fixed: 'left',
    },
    {
      title: t('customer.shortName'),
      dataIndex: 'short_name',
      key: 'short_name',
      width: 150,
    },
    {
      title: t('customer.invoiceTitle'),
      dataIndex: 'invoice_title',
      key: 'invoice_title',
      width: 200,
      ellipsis: true,
    },
    {
      title: t('customer.address'),
      dataIndex: 'address',
      key: 'address',
      ellipsis: true,
    },
    {
      title: t('customer.area'),
      dataIndex: 'area',
      key: 'area',
      width: 100,
    },
    {
      title: t('customer.deliveryTime'),
      key: 'delivery_time',
      width: 120,
      render: (_, record) => {
        if (record.delivery_time_start && record.delivery_time_end) {
          return `${record.delivery_time_start}-${record.delivery_time_end}`;
        }
        return '-';
      },
    },
    {
      title: t('customer.monthlyDelivery'),
      dataIndex: 'avg_daily_usage',
      key: 'avg_daily_usage',
      width: 100,
      render: (value) => value ? `${value} kg/日` : '-',
    },
    {
      title: t('customer.paymentMethod'),
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 100,
      render: (method) => {
        const methodMap: Record<string, string> = {
          '月結': '月結',
          '現金': '現金',
          '轉帳': '轉帳',
        };
        return methodMap[method] || method || '-';
      },
    },
    {
      title: t('customer.type'),
      dataIndex: 'customer_type',
      key: 'customer_type',
      width: 100,
      render: (type) => type || '-',
    },
    {
      title: t('customer.status'),
      key: 'status',
      width: 120,
      render: (_, record) => (
        record.is_active ? (
          <Tag color="green">啟用</Tag>
        ) : (
          <Tag color="red">已停用</Tag>
        )
      ),
    },
    {
      title: t('app.actions'),
      key: 'action',
      fixed: 'right',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<ContainerOutlined />}
            onClick={() => handleViewInventory(record)}
          >
            庫存
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            data-testid={`edit-customer-${record.id}`}
          >
            編輯
          </Button>
          <Button
            size="small"
            danger
            onClick={() => handleDelete(record)}
            data-testid={`delete-customer-${record.id}`}
          >
            刪除
          </Button>
        </Space>
      ),
    },
  ].filter(column => {
    // Filter out payment-related columns if payment features are disabled
    if (!features.anyPaymentFeature) {
      return column.key !== 'invoice_title' && column.key !== 'payment_method';
    }
    return true;
  });

  const handleSearch = (value: string) => {
    setSearchText(value);
    setCurrentPage(1);
    fetchCustomers(value, 1, pageSize);
  };

  const handleTableChange = (pagination: any) => {
    setCurrentPage(pagination.current);
    setPageSize(pagination.pageSize);
  };

  return (
    <div>
      <Title level={2} data-testid="customer-list-title">{t('customer.title')}</Title>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Search
              placeholder={t('customer.searchPlaceholder')}
              allowClear
              enterButton={<SearchOutlined />}
              size="middle"
              onSearch={handleSearch}
              style={{ width: 300 }}
              data-testid="customer-search-input"
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setIsEditMode(false);
                setSelectedCustomer(null);
                form.resetFields();
                setIsModalVisible(true);
              }}
              data-testid="add-customer-button"
            >
              {t('customer.addButton')}
            </Button>
          </Space>
        </div>
        <Table
          columns={columns}
          dataSource={customers}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          onChange={handleTableChange}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆資料`,
          }}
          data-testid="customer-table"
        />
      </Card>

      {/* Customer Form Modal */}
      <Modal
        title={isEditMode ? '編輯客戶' : '新增客戶'}
        open={isModalVisible}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={800}
        data-testid="customer-modal"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customer_code"
                label="客戶編號"
                rules={[{ required: true, message: '請輸入客戶編號' }]}
              >
                <Input disabled={isEditMode} data-testid="customer-code-input" id="customer_code" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="short_name"
                label={t('customer.shortName')}
                rules={[{ required: true, message: t('validation.required') }]}
              >
                <Input data-testid="customer-shortname-input" id="short_name" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            {features.anyPaymentFeature && (
              <Col span={12}>
                <Form.Item name="invoice_title" label="發票抬頭">
                  <Input data-testid="customer-invoice-input" id="invoice_title" />
                </Form.Item>
              </Col>
            )}
            <Col span={features.anyPaymentFeature ? 12 : 24}>
              <Form.Item name="customer_type" label="客戶類型">
                <Select placeholder="選擇客戶類型">
                  <Option value="學校">學校</Option>
                  <Option value="商業">商業</Option>
                  <Option value="市場">市場</Option>
                  <Option value="夜市">夜市</Option>
                  <Option value="餐車">餐車</Option>
                  <Option value="辦桌">辦桌</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="address"
            label={t('customer.address')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Input.TextArea rows={2} data-testid="customer-address-input" id="address" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="電話"
                rules={[
                  { 
                    pattern: /^(0[2-9]-?\d{4}-?\d{4}|09\d{2}-?\d{3}-?\d{3})$/,
                    message: '請輸入有效的台灣電話號碼'
                  }
                ]}
              >
                <Input placeholder="02-1234-5678 或 0912-345-678" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="email" label="電子郵件">
                <Input type="email" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="area" label="配送區域">
                <Select placeholder="選擇區域" data-testid="customer-area-select" id="area">
                  <Option value="A-瑞光">A-瑞光</Option>
                  <Option value="B-四維">B-四維</Option>
                  <Option value="C-漢中">C-漢中</Option>
                  <Option value="D-東方大鎮">D-東方大鎮</Option>
                  <Option value="E-力國">E-力國</Option>
                  <Option value="Y-富岡">Y-富岡</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="delivery_time" label="配送時段">
                <TimePicker.RangePicker format="HH:mm" />
              </Form.Item>
            </Col>
            {features.anyPaymentFeature && (
              <Col span={8}>
                <Form.Item name="payment_method" label="付款方式">
                  <Select placeholder="選擇付款方式">
                    <Option value="月結">月結</Option>
                    <Option value="現金">現金</Option>
                    <Option value="轉帳">轉帳</Option>
                  </Select>
                </Form.Item>
              </Col>
            )}
          </Row>

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="cylinders_50kg" label="50kg瓦斯桶">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="cylinders_20kg" label="20kg瓦斯桶">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="cylinders_16kg" label="16kg瓦斯桶">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="cylinders_4kg" label="4kg瓦斯桶">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="avg_daily_usage" label="平均日使用量(kg)">
                <InputNumber min={0} step={0.1} style={{ width: '100%' }} data-testid="customer-avg-usage-input" id="avg_daily_usage" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_cycle_days" label="最大週期(天)">
                <InputNumber min={1} style={{ width: '100%' }} data-testid="customer-max-cycle-input" id="max_cycle_days" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="can_delay_days" label="可延後天數">
                <InputNumber min={0} style={{ width: '100%' }} data-testid="customer-delay-days-input" id="can_delay_days" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="is_subscription" label="訂閱式會員" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="needs_same_day_delivery" label="需要當天配送" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_terminated" label="已停用" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Customer Inventory Modal */}
      {selectedCustomer && (
        <CustomerInventory
          customer={selectedCustomer}
          open={inventoryModalVisible}
          onClose={() => setInventoryModalVisible(false)}
        />
      )}
    </div>
  );
};

export default CustomerList;