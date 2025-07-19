import React, { useState, useEffect } from 'react';
import { Table, Card, Input, Button, Space, Typography, Tag, message, Modal, Form, Row, Col, Switch, InputNumber, TimePicker, Select } from 'antd';
import { SearchOutlined, PlusOutlined, EditOutlined, EyeOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { customerService } from '../../services/customer.service';
import { Customer } from '../../types/order';

const { Title } = Typography;
const { Search } = Input;
const { Option } = Select;
const { confirm } = Modal;

const CustomerList: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
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
    } catch (error) {
      message.error(isEditMode ? '更新客戶失敗' : '創建客戶失敗');
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
      title: '確認停用客戶',
      icon: <ExclamationCircleOutlined />,
      content: `確定要停用客戶 ${customer.short_name} 嗎？`,
      okText: '確認',
      cancelText: '取消',
      onOk: async () => {
        try {
          await customerService.updateCustomer(customer.id, { is_terminated: true });
          message.success('客戶已停用');
          fetchCustomers(searchText, currentPage, pageSize);
        } catch (error) {
          message.error('停用客戶失敗');
        }
      },
    });
  };

  const columns: ColumnsType<Customer> = [
    {
      title: '客戶編號',
      dataIndex: 'customer_code',
      key: 'customer_code',
      width: 120,
      fixed: 'left',
    },
    {
      title: '客戶簡稱',
      dataIndex: 'short_name',
      key: 'short_name',
      width: 150,
    },
    {
      title: '發票抬頭',
      dataIndex: 'invoice_title',
      key: 'invoice_title',
      width: 200,
      ellipsis: true,
    },
    {
      title: '地址',
      dataIndex: 'address',
      key: 'address',
      ellipsis: true,
    },
    {
      title: '配送區域',
      dataIndex: 'area',
      key: 'area',
      width: 100,
    },
    {
      title: '配送時段',
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
      title: '月配送量',
      dataIndex: 'avg_daily_usage',
      key: 'avg_daily_usage',
      width: 100,
      render: (value) => value ? `${value} kg/日` : '-',
    },
    {
      title: '付款方式',
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
      title: '客戶類型',
      dataIndex: 'customer_type',
      key: 'customer_type',
      width: 100,
      render: (type) => type || '-',
    },
    {
      title: '狀態',
      key: 'status',
      width: 120,
      render: (_, record) => (
        <Space>
          {record.is_terminated ? (
            <Tag color="red">已停用</Tag>
          ) : (
            <Tag color="green">啟用</Tag>
          )}
          {record.is_subscription && <Tag color="blue">訂閱</Tag>}
          {record.needs_same_day_delivery && <Tag color="orange">當日配送</Tag>}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            編輯
          </Button>
          <Button
            size="small"
            danger
            onClick={() => handleDelete(record)}
            disabled={record.is_terminated}
          >
            停用
          </Button>
        </Space>
      ),
    },
  ];

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
      <Title level={2}>客戶管理</Title>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Search
              placeholder="搜尋客戶編號、名稱或地址"
              allowClear
              enterButton={<SearchOutlined />}
              size="middle"
              onSearch={handleSearch}
              style={{ width: 300 }}
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
            >
              新增客戶
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
                <Input disabled={isEditMode} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="short_name"
                label="客戶簡稱"
                rules={[{ required: true, message: '請輸入客戶簡稱' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="invoice_title" label="發票抬頭">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
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
            label="地址"
            rules={[{ required: true, message: '請輸入地址' }]}
          >
            <Input.TextArea rows={2} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="area" label="配送區域">
                <Select placeholder="選擇區域">
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
            <Col span={8}>
              <Form.Item name="payment_method" label="付款方式">
                <Select placeholder="選擇付款方式">
                  <Option value="月結">月結</Option>
                  <Option value="現金">現金</Option>
                  <Option value="轉帳">轉帳</Option>
                </Select>
              </Form.Item>
            </Col>
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
                <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_cycle_days" label="最大週期(天)">
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="can_delay_days" label="可延後天數">
                <InputNumber min={0} style={{ width: '100%' }} />
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
    </div>
  );
};

export default CustomerList;