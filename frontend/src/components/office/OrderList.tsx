import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Tag,
  Space,
  DatePicker,
  Select,
  Input,
  message,
  Modal,
  Descriptions,
  Divider,
  Row,
  Col,
  Statistic,
  Tooltip,
  Form,
  InputNumber,
  Switch,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
  CalendarOutlined,
  DollarOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { orderService } from '../../services/order.service';
import { customerService } from '../../services/customer.service';
import ProductSelector from './ProductSelector';
import { useWebSocket } from '../../hooks/useWebSocket';
import {
  Order,
  OrderStatus,
  PaymentStatus,
  OrderUpdate,
  OrderV2,
  OrderCreateV2,
  getOrderStatusColor,
  getOrderStatusText,
  getPaymentStatusColor,
  getPaymentStatusText,
  Customer,
} from '../../types/order';
import { OrderItemCreate } from '../../types/product';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { confirm } = Modal;

const OrderList: React.FC = () => {
  const { t } = useTranslation();
  const { on } = useWebSocket();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [selectedOrderV2, setSelectedOrderV2] = useState<OrderV2 | null>(null);
  const [isDetailModalVisible, setIsDetailModalVisible] = useState(false);
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [selectedOrderItems, setSelectedOrderItems] = useState<OrderItemCreate[]>([]);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // Filter states
  const [filters, setFilters] = useState({
    status: undefined as OrderStatus | undefined,
    customer_id: undefined as number | undefined,
    date_range: [] as any[],
    is_urgent: undefined as boolean | undefined,
  });

  // Fetch orders
  const fetchOrders = async () => {
    setLoading(true);
    try {
      const params: any = {
        skip: 0,
        limit: 100,
      };

      if (filters.status) params.status = filters.status;
      if (filters.customer_id) params.customer_id = filters.customer_id;
      if (filters.is_urgent !== undefined) params.is_urgent = filters.is_urgent;
      if (filters.date_range.length === 2) {
        params.date_from = filters.date_range[0].toISOString();
        params.date_to = filters.date_range[1].toISOString();
      }

      const data = await orderService.getOrders(params);
      setOrders(data);
    } catch (error) {
      message.error('獲取訂單失敗');
    } finally {
      setLoading(false);
    }
  };

  // Fetch order stats
  const fetchStats = async () => {
    try {
      const dateFrom = filters.date_range[0]?.toISOString();
      const dateTo = filters.date_range[1]?.toISOString();
      const data = await orderService.getOrderStats(dateFrom, dateTo);
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  // Fetch customers for dropdown
  const fetchCustomers = async () => {
    try {
      const response = await customerService.getCustomers({ limit: 1000 });
      setCustomers(response.items);
    } catch (error) {
      console.error('Failed to fetch customers:', error);
    }
  };

  useEffect(() => {
    fetchOrders();
    fetchStats();
    fetchCustomers();
  }, [filters]);

  // WebSocket listeners for real-time updates
  useEffect(() => {
    const unsubscribeOrderCreated = on('order_created', (data) => {
      // Add flash effect to new order
      message.success(`新訂單 #${data.order_number} 已創建`);
      fetchOrders();
      fetchStats();
    });

    const unsubscribeOrderUpdated = on('order_updated', (data) => {
      // Update order in the list if it's visible
      setOrders(prevOrders => 
        prevOrders.map(order => 
          order.id === data.order_id ? { ...order, ...data } : order
        )
      );
      
      // Update detail modal if it's showing this order
      if (selectedOrder?.id === data.order_id) {
        setSelectedOrder(prev => prev ? { ...prev, ...data } : null);
      }
      
      fetchStats();
    });

    const unsubscribeOrderAssigned = on('order_assigned', (data) => {
      message.info(`訂單 #${data.order_number} 已分配給路線 ${data.route_number}`);
      fetchOrders();
    });

    const unsubscribeDeliveryCompleted = on('delivery_completed', (data) => {
      message.success(`訂單 #${data.order_id} 已送達`);
      fetchOrders();
      fetchStats();
    });

    return () => {
      unsubscribeOrderCreated();
      unsubscribeOrderUpdated();
      unsubscribeOrderAssigned();
      unsubscribeDeliveryCompleted();
    };
  }, [on, selectedOrder]);

  // View order details
  const handleViewDetails = async (order: Order) => {
    setSelectedOrder(order);
    try {
      // Fetch V2 order for details with order items
      const orderV2 = await orderService.getOrderV2(order.id);
      setSelectedOrderV2(orderV2);
    } catch (error) {
      console.error('Failed to fetch order details:', error);
      setSelectedOrderV2(null);
    }
    setIsDetailModalVisible(true);
  };

  // Create order
  const handleCreateOrder = async (values: any) => {
    try {
      if (selectedOrderItems.length === 0) {
        message.error('請至少選擇一個產品');
        return;
      }

      const orderData: OrderCreateV2 = {
        customer_id: values.customer_id,
        scheduled_date: values.scheduled_date.toISOString(),
        delivery_time_start: values.delivery_time_start,
        delivery_time_end: values.delivery_time_end,
        order_items: selectedOrderItems,
        delivery_address: values.delivery_address,
        delivery_notes: values.delivery_notes,
        is_urgent: values.is_urgent || false,
        payment_method: values.payment_method,
      };

      await orderService.createOrderV2(orderData);
      message.success('訂單創建成功');
      setIsCreateModalVisible(false);
      form.resetFields();
      setSelectedOrderItems([]);
      fetchOrders();
      fetchStats();
    } catch (error) {
      message.error('創建訂單失敗');
    }
  };

  // Edit order
  const handleEditOrder = (order: Order) => {
    editForm.setFieldsValue({
      ...order,
      scheduled_date: dayjs(order.scheduled_date),
    });
    setSelectedOrder(order);
    setIsEditModalVisible(true);
  };

  // Update order
  const handleUpdateOrder = async (values: any) => {
    if (!selectedOrder) return;

    try {
      const updateData: OrderUpdate = {
        scheduled_date: values.scheduled_date.toISOString(),
        delivery_time_start: values.delivery_time_start,
        delivery_time_end: values.delivery_time_end,
        qty_50kg: values.qty_50kg,
        qty_20kg: values.qty_20kg,
        qty_16kg: values.qty_16kg,
        qty_10kg: values.qty_10kg,
        qty_4kg: values.qty_4kg,
        delivery_address: values.delivery_address,
        delivery_notes: values.delivery_notes,
        is_urgent: values.is_urgent,
        status: values.status,
        payment_status: values.payment_status,
      };

      await orderService.updateOrder(selectedOrder.id, updateData);
      message.success('訂單更新成功');
      setIsEditModalVisible(false);
      fetchOrders();
      fetchStats();
    } catch (error) {
      message.error('更新訂單失敗');
    }
  };

  // Cancel order
  const handleCancelOrder = (order: Order) => {
    confirm({
      title: '確認取消訂單',
      icon: <ExclamationCircleOutlined />,
      content: `確定要取消訂單 ${order.order_number} 嗎？`,
      okText: '確認',
      cancelText: '取消',
      onOk: async () => {
        try {
          await orderService.cancelOrder(order.id, '用戶取消');
          message.success('訂單已取消');
          fetchOrders();
          fetchStats();
        } catch (error) {
          message.error('取消訂單失敗');
        }
      },
    });
  };

  // Table columns
  const columns: ColumnsType<Order> = [
    {
      title: '訂單編號',
      dataIndex: 'order_number',
      key: 'order_number',
      fixed: 'left',
      render: (text, record) => (
        <a onClick={() => handleViewDetails(record)}>{text}</a>
      ),
    },
    {
      title: '客戶',
      dataIndex: 'customer',
      key: 'customer',
      render: (customer: Customer) => customer?.short_name || '-',
    },
    {
      title: '配送日期',
      dataIndex: 'scheduled_date',
      key: 'scheduled_date',
      render: (date) => dayjs(date).format('YYYY/MM/DD'),
      sorter: (a, b) => dayjs(a.scheduled_date).unix() - dayjs(b.scheduled_date).unix(),
    },
    {
      title: '配送時段',
      key: 'delivery_time',
      render: (_, record) => {
        if (record.delivery_time_start && record.delivery_time_end) {
          return `${record.delivery_time_start} - ${record.delivery_time_end}`;
        }
        return '-';
      },
    },
    {
      title: '訂單內容',
      key: 'order_content',
      render: (_, record) => {
        // For backwards compatibility, show cylinder quantities if available
        const quantities = [];
        if (record.qty_50kg > 0) quantities.push(`50kg×${record.qty_50kg}`);
        if (record.qty_20kg > 0) quantities.push(`20kg×${record.qty_20kg}`);
        if (record.qty_16kg > 0) quantities.push(`16kg×${record.qty_16kg}`);
        if (record.qty_10kg > 0) quantities.push(`10kg×${record.qty_10kg}`);
        if (record.qty_4kg > 0) quantities.push(`4kg×${record.qty_4kg}`);
        
        if (quantities.length > 0) {
          return quantities.join(', ');
        }
        
        // For V2 orders, show "查看詳情" link
        return (
          <a onClick={() => handleViewDetails(record)}>查看產品明細</a>
        );
      },
    },
    {
      title: '金額',
      dataIndex: 'final_amount',
      key: 'final_amount',
      render: (amount) => `NT$ ${amount.toLocaleString()} 元`,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status: OrderStatus) => (
        <Tag color={getOrderStatusColor(status)}>
          {getOrderStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '付款狀態',
      dataIndex: 'payment_status',
      key: 'payment_status',
      render: (status: PaymentStatus) => (
        <Tag color={getPaymentStatusColor(status)}>
          {getPaymentStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '緊急',
      dataIndex: 'is_urgent',
      key: 'is_urgent',
      render: (urgent) => urgent && <Tag color="red" icon={<ThunderboltOutlined />}>緊急</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看詳情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          <Tooltip title="編輯">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditOrder(record)}
              disabled={record.status === 'delivered' || record.status === 'cancelled'}
            />
          </Tooltip>
          <Tooltip title="取消訂單">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleCancelOrder(record)}
              disabled={record.status === 'delivered' || record.status === 'cancelled'}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="order-list">
      {/* Statistics */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="總訂單數"
                value={stats.total_orders}
                prefix={<CalendarOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="總收入"
                value={stats.total_revenue}
                prefix={<DollarOutlined />}
                suffix="NT$"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="緊急訂單"
                value={stats.urgent_orders}
                prefix={<ThunderboltOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="客戶數"
                value={stats.unique_customers}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Main Card */}
      <Card
        title={t('order.title')}
        extra={
          <Space>
            <Tag color="green" icon={<ThunderboltOutlined />}>
              即時更新
            </Tag>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsCreateModalVisible(true)}
            >
              {t('order.addButton')}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchOrders}>
              刷新
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="訂單狀態"
            style={{ width: 120 }}
            allowClear
            value={filters.status}
            onChange={(value) => setFilters({ ...filters, status: value })}
          >
            <Option value="pending">待確認</Option>
            <Option value="confirmed">已確認</Option>
            <Option value="assigned">已分配</Option>
            <Option value="in_delivery">配送中</Option>
            <Option value="delivered">已送達</Option>
            <Option value="cancelled">已取消</Option>
          </Select>

          <Select
            placeholder="選擇客戶"
            style={{ width: 200 }}
            showSearch
            allowClear
            value={filters.customer_id}
            onChange={(value) => setFilters({ ...filters, customer_id: value })}
            filterOption={(input, option) => {
              const label = String(option?.label || option?.value || '');
              return label.toLowerCase().includes(input.toLowerCase());
            }}
          >
            {customers.map((customer) => (
              <Option key={customer.id} value={customer.id}>
                {customer.short_name}
              </Option>
            ))}
          </Select>

          <RangePicker
            value={filters.date_range as any}
            onChange={(dates) => setFilters({ ...filters, date_range: dates as any || [] })}
          />

          <Select
            placeholder="緊急狀態"
            style={{ width: 120 }}
            allowClear
            value={filters.is_urgent}
            onChange={(value) => setFilters({ ...filters, is_urgent: value })}
          >
            <Option value={true}>緊急</Option>
            <Option value={false}>一般</Option>
          </Select>
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={orders}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆`,
          }}
          rowClassName={(record) => {
            // Add animation class for recently updated orders
            const isRecent = record.updated_at && 
              dayjs().diff(dayjs(record.updated_at), 'second') < 5;
            return isRecent ? 'order-row-updated' : '';
          }}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title="訂單詳情"
        open={isDetailModalVisible}
        onCancel={() => setIsDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedOrder && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="訂單編號">
              {selectedOrder.order_number}
            </Descriptions.Item>
            <Descriptions.Item label="狀態">
              <Tag color={getOrderStatusColor(selectedOrder.status)}>
                {getOrderStatusText(selectedOrder.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="客戶名稱">
              {selectedOrder.customer?.short_name}
            </Descriptions.Item>
            <Descriptions.Item label="客戶代碼">
              {selectedOrder.customer?.customer_code}
            </Descriptions.Item>
            <Descriptions.Item label="配送日期">
              {dayjs(selectedOrder.scheduled_date).format('YYYY/MM/DD')}
            </Descriptions.Item>
            <Descriptions.Item label="配送時段">
              {selectedOrder.delivery_time_start} - {selectedOrder.delivery_time_end}
            </Descriptions.Item>
            <Descriptions.Item label="配送地址" span={2}>
              {selectedOrder.delivery_address}
            </Descriptions.Item>
            <Descriptions.Item label="備註" span={2}>
              {selectedOrder.delivery_notes || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="緊急訂單">
              {selectedOrder.is_urgent ? (
                <Tag color="red" icon={<ThunderboltOutlined />}>是</Tag>
              ) : '否'}
            </Descriptions.Item>
            <Descriptions.Item label="付款狀態">
              <Tag color={getPaymentStatusColor(selectedOrder.payment_status)}>
                {getPaymentStatusText(selectedOrder.payment_status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="訂單產品" span={2}>
              {selectedOrderV2 && selectedOrderV2.order_items.length > 0 ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {selectedOrderV2.order_items.map((item, index) => (
                    <div key={index} style={{ marginBottom: 8 }}>
                      <Space>
                        <Tag color="blue">
                          {item.gas_product?.display_name || `產品 ID: ${item.gas_product_id}`}
                        </Tag>
                        <span>數量: {item.quantity}</span>
                        <span>單價: NT$ {item.unit_price}</span>
                        <span>小計: NT$ {item.subtotal}</span>
                        {item.is_exchange && <Tag color="green">交換</Tag>}
                        {item.discount_percentage > 0 && <Tag color="orange">折扣 {item.discount_percentage}%</Tag>}
                      </Space>
                    </div>
                  ))}
                </Space>
              ) : (
                <Space>
                  {selectedOrder.qty_50kg > 0 && <Tag>50kg × {selectedOrder.qty_50kg}</Tag>}
                  {selectedOrder.qty_20kg > 0 && <Tag>20kg × {selectedOrder.qty_20kg}</Tag>}
                  {selectedOrder.qty_16kg > 0 && <Tag>16kg × {selectedOrder.qty_16kg}</Tag>}
                  {selectedOrder.qty_10kg > 0 && <Tag>10kg × {selectedOrder.qty_10kg}</Tag>}
                  {selectedOrder.qty_4kg > 0 && <Tag>4kg × {selectedOrder.qty_4kg}</Tag>}
                </Space>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="總金額">
              NT$ {selectedOrder.total_amount.toLocaleString()} 元
            </Descriptions.Item>
            <Descriptions.Item label="折扣">
              NT$ {selectedOrder.discount_amount.toLocaleString()} 元
            </Descriptions.Item>
            <Descriptions.Item label="應付金額">
              <strong>NT$ {selectedOrder.final_amount.toLocaleString()} 元</strong>
            </Descriptions.Item>
            <Descriptions.Item label="建立時間">
              {dayjs(selectedOrder.created_at).format('YYYY/MM/DD HH:mm')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* Create Modal */}
      <Modal
        title="新增訂單"
        open={isCreateModalVisible}
        onCancel={() => {
          setIsCreateModalVisible(false);
          form.resetFields();
          setSelectedOrderItems([]);
        }}
        onOk={() => form.submit()}
        width={900}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrder}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="customer_id"
                label="客戶"
                rules={[{ required: true, message: '請選擇客戶' }]}
              >
                <Select
                  placeholder="選擇客戶"
                  showSearch
                  filterOption={(input, option) => {
                    const label = String(option?.label || option?.value || '');
                    return label.toLowerCase().includes(input.toLowerCase());
                  }}
                >
                  {customers.map((customer) => (
                    <Option key={customer.id} value={customer.id}>
                      {customer.short_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="scheduled_date"
                label="配送日期"
                rules={[{ required: true, message: '請選擇配送日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="delivery_time_start" label="配送開始時間">
                <Input placeholder="例如: 09:00" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="delivery_time_end" label="配送結束時間">
                <Input placeholder="例如: 17:00" />
              </Form.Item>
            </Col>
          </Row>

          <Divider>產品選擇</Divider>
          <Form.Item label="訂單產品" required>
            <ProductSelector 
              onProductsChange={setSelectedOrderItems}
              initialItems={selectedOrderItems}
            />
          </Form.Item>

          <Form.Item name="is_urgent" label="緊急訂單" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="delivery_address" label="配送地址">
            <Input.TextArea rows={2} placeholder="如不填寫，將使用客戶預設地址" />
          </Form.Item>

          <Form.Item name="delivery_notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="payment_method" label="付款方式">
            <Select placeholder="選擇付款方式">
              <Option value="cash">現金</Option>
              <Option value="transfer">轉帳</Option>
              <Option value="monthly">月結</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="編輯訂單"
        open={isEditModalVisible}
        onCancel={() => {
          setIsEditModalVisible(false);
          editForm.resetFields();
        }}
        onOk={() => editForm.submit()}
        width={800}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdateOrder}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="scheduled_date"
                label="配送日期"
                rules={[{ required: true, message: '請選擇配送日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="訂單狀態">
                <Select>
                  <Option value="pending">待確認</Option>
                  <Option value="confirmed">已確認</Option>
                  <Option value="assigned">已分配</Option>
                  <Option value="in_delivery">配送中</Option>
                  <Option value="delivered">已送達</Option>
                  <Option value="cancelled">已取消</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="delivery_time_start" label="配送開始時間">
                <Input placeholder="例如: 09:00" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="delivery_time_end" label="配送結束時間">
                <Input placeholder="例如: 17:00" />
              </Form.Item>
            </Col>
          </Row>

          <Divider>瓦斯桶數量</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="qty_50kg" label="50kg">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="qty_20kg" label="20kg">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="qty_16kg" label="16kg">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="qty_10kg" label="10kg">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="qty_4kg" label="4kg">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="is_urgent" label="緊急訂單" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="delivery_address" label="配送地址">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="delivery_notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="payment_status" label="付款狀態">
            <Select>
              <Option value="unpaid">未付款</Option>
              <Option value="paid">已付款</Option>
              <Option value="partial">部分付款</Option>
              <Option value="refunded">已退款</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OrderList;