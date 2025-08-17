import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Table, Button, Space, Card, Input, Tag, Modal, Form, Select, DatePicker, Row, Col, message, Statistic, Timeline, Drawer, InputNumber } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ClockCircleOutlined, CheckCircleOutlined, CarOutlined, ExclamationCircleOutlined, EyeOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';
import { apiWithCancel, requestManager } from '../../services/api.service';
import dayjs from 'dayjs';
import { useRealtimeUpdates } from '../../hooks/useRealtimeUpdates';
import OrderModificationModal from '../../components/orders/OrderModificationModal';
import BulkOrderActions from '../../components/orders/BulkOrderActions';
import CreditSummary from '../../components/orders/CreditSummary';
import OrderSearchPanel, { SearchCriteria } from '../../components/orders/OrderSearchPanel';
import TemplateQuickSelect from '../../components/orders/TemplateQuickSelect';
import OrderTemplateManager from '../../components/orders/OrderTemplateManager';
import { features } from '../../config/features';
import { 
  toArray, 
  safeMap, 
  safeFilter, 
  safeFind, 
  safeReduce, 
  safeLength,
  safeSome,
  safeForEach,
  ensureArray 
} from '../../utils/dataHelpers';

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
  // Support for multiple products
  products?: Array<{
    cylinderType: '20kg' | '16kg' | '50kg' | '10kg' | '4kg';
    quantity: number;
    unitPrice: number;
  }>;
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
  const [isModificationModalVisible, setIsModificationModalVisible] = useState(false);
  const [isDetailDrawerVisible, setIsDetailDrawerVisible] = useState(false);
  const [orderTimeline, setOrderTimeline] = useState<OrderTimeline[]>([]);
  const [searchText, setSearchText] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [form] = Form.useForm();
  const [customers, setCustomers] = useState<any[]>([]);
  const [customersLoading, setCustomersLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<Order[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);
  const [drivers, setDrivers] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchCriteria, setSearchCriteria] = useState<SearchCriteria | null>(null);
  
  // UseRef to track if component is mounted
  const isMountedRef = useRef(true);

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
    // Set mounted flag
    isMountedRef.current = true;
    
    // Fetch initial data
    fetchOrders();
    fetchStatistics();
    fetchCustomers();
    fetchDrivers();
    
    // Cleanup function
    return () => {
      isMountedRef.current = false;
      // Cancel all pending requests
      requestManager.cancel('orders-fetch');
      requestManager.cancel('orders-statistics');
      requestManager.cancel('orders-customers');
      requestManager.cancel('orders-drivers');
    };
  }, []);

  const fetchOrders = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    setLoading(true);
    try {
      const response = await apiWithCancel.get('/orders', 'orders-fetch', { 
        cache: true,
        debounce: 300 
      });
      
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        // Use toArray to safely extract orders array from response
        const ordersData = toArray(response.data, 'orders');
        setOrders(ordersData);
      }
    } catch (error: any) {
      // Only show error if component is mounted and it's not a cancellation
      if (isMountedRef.current && error.message !== 'Request cancelled') {
        message.error(t('orders.fetchError'));
        setOrders([]); // Ensure orders is always an array even on error
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [t]);

  const fetchStatistics = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    try {
      // Try without any parameters first to see what the API expects
      const response = await apiWithCancel.get('/orders/statistics', 'orders-statistics', {
        cache: true,
        debounce: 500
      });
      
      if (isMountedRef.current) {
        setStats(response.data);
      }
    } catch (error: any) {
      if (error.message === 'Request cancelled') return;
      
      console.error('Failed to fetch statistics:', error.response?.data || error);
      // If that fails, try with different parameter combinations
      try {
        // Try with just date parameters
        const today = dayjs();
        const params = {
          start_date: today.startOf('day').format('YYYY-MM-DD'),
          end_date: today.endOf('day').format('YYYY-MM-DD')
        };
        const response = await apiWithCancel.get('/orders/statistics?start_date=' + params.start_date + '&end_date=' + params.end_date, 'orders-statistics-retry', {
          cache: true
        });
        
        if (isMountedRef.current) {
          setStats(response.data);
        }
      } catch (error2: any) {
        if (isMountedRef.current && error2.message !== 'Request cancelled') {
          console.error('Failed with date params:', error2.response?.data || error2);
          // Set default stats if API fails
          setStats({
            totalOrders: 0,
            pendingOrders: 0,
            todayDeliveries: 0,
            monthlyRevenue: 0,
          });
        }
      }
    }
  }, []);

  const fetchCustomers = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    setCustomersLoading(true);
    try {
      const response = await apiWithCancel.get('/customers', 'orders-customers', {
        cache: true,
        debounce: 500
      });
      
      if (isMountedRef.current) {
        // Handle both array and object response formats using toArray
        const customerData = toArray(response.data, 'customers');
        
        // Filter out customers without valid IDs and ensure unique IDs
        const validCustomers = safeFilter(customerData, (customer) => {
          const id = customer.id || customer.編號;
          return id !== null && id !== undefined;
        });
        
        setCustomers(validCustomers);
      }
    } catch (error: any) {
      if (isMountedRef.current && error.message !== 'Request cancelled') {
        console.error('Failed to fetch customers:', error);
        setCustomers([]); // Ensure customers is always an array
      }
    } finally {
      if (isMountedRef.current) {
        setCustomersLoading(false);
      }
    }
  }, []);

  const fetchOrderTimeline = async (orderId: string) => {
    try {
      const response = await api.get(`/orders/${orderId}/timeline`);
      // Ensure timeline is always an array
      const timelineData = toArray(response.data, 'timeline');
      setOrderTimeline(timelineData);
    } catch (error) {
      console.error('Failed to fetch timeline:', error);
      setOrderTimeline([]); // Ensure it's always an array
    }
  };

  const fetchDrivers = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    try {
      const response = await apiWithCancel.get('/users/drivers', 'orders-drivers', {
        cache: true,
        debounce: 500
      });
      
      if (isMountedRef.current) {
        // Use toArray to safely extract drivers array
        const driversData = toArray(response.data, 'drivers');
        setDrivers(driversData);
      }
    } catch (error: any) {
      if (isMountedRef.current && error.message !== 'Request cancelled') {
        console.error('Failed to fetch drivers:', error);
        setDrivers([]); // Ensure drivers is always an array
      }
    }
  }, []);

  const handleAdvancedSearch = async (criteria: SearchCriteria) => {
    setSearchLoading(true);
    setSearchCriteria(criteria);
    try {
      const response = await api.post('/orders/search', criteria);
      setOrders(response.data.orders);
      message.success(`${t('orders.searchResults')}: ${response.data.total} ${t('orders.searchTime', { time: response.data.search_time.toFixed(2) })}`);
    } catch (error) {
      message.error(t('orders.fetchError'));
    } finally {
      setSearchLoading(false);
    }
  };

  const handleExportSearchResults = async (criteria: SearchCriteria) => {
    setSearchLoading(true);
    try {
      // First get all results without pagination
      const fullCriteria = { ...criteria, skip: 0, limit: 10000 };
      const response = await api.post('/orders/search', fullCriteria);
      
      // Create Excel export using the existing xlsx logic
      const ordersArray = toArray(response.data?.orders || response.data, 'orders');
      const exportData = safeMap(ordersArray, (order: any) => ({
        [t('orders.orderNumber')]: order.order_number,
        [t('orders.customer')]: order.customer_name,
        [t('orders.phone')]: order.customer_phone,
        [t('orders.address')]: order.customer_address,
        [t('orders.orderDate')]: order.order_date ? dayjs(order.order_date).format('YYYY-MM-DD') : '',
        [t('orders.deliveryDate')]: order.scheduled_date ? dayjs(order.scheduled_date).format('YYYY-MM-DD') : '',
        [t('orders.status')]: t(`orders.status${order.status.charAt(0).toUpperCase() + order.status.slice(1)}`),
        [t('orders.paymentStatus')]: t(`orders.payment${order.payment_status.charAt(0).toUpperCase() + order.payment_status.slice(1)}`),
        [t('orders.totalAmount')]: order.final_amount,
        [t('orders.deliveryNotes')]: order.delivery_notes || ''
      }));
      
      // Import xlsx dynamically
      const XLSX = await import('xlsx');
      const ws = XLSX.utils.json_to_sheet(exportData);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, t('orders.searchResults'));
      
      // Auto-size columns
      const colWidths = safeMap(Object.keys(exportData[0] || {}), key => ({
        wch: Math.max(key.length, ...safeMap(exportData, row => String(row[key] || '').length))
      }));
      ws['!cols'] = colWidths;
      
      // Download file
      XLSX.writeFile(wb, `order_search_results_${dayjs().format('YYYYMMDD_HHmmss')}.xlsx`);
      message.success(t('orders.exportSuccess'));
    } catch (error) {
      message.error(t('orders.exportError'));
    } finally {
      setSearchLoading(false);
    }
  };

  const handleAdd = () => {
    setSelectedOrder(null);
    setSelectedCustomerId(null);
    form.resetFields();
    form.setFieldValue('orderDate', dayjs());
    form.setFieldValue('priority', 'normal');
    form.setFieldValue('paymentMethod', 'cash');
    form.setFieldValue('paymentStatus', 'pending');
    // Initialize products array with one default product
    form.setFieldValue('products', [{ cylinderType: '20kg', quantity: 1, unitPrice: 800 }]);
    setIsModalVisible(true);
  };

  const handleEdit = (order: Order) => {
    setSelectedOrder(order);
    setSelectedCustomerId(order.customerId ? Number(order.customerId) : null);
    
    // For existing orders with status other than 'pending', use the modification modal
    if (order.status !== 'pending') {
      setIsModificationModalVisible(true);
    } else {
      // For pending orders, use the regular edit modal
      const products = order.products || [{
        cylinderType: order.cylinderType,
        quantity: order.quantity,
        unitPrice: order.unitPrice,
      }];
      
      form.setFieldsValue({
        ...order,
        orderDate: dayjs(order.orderDate),
        deliveryDate: order.deliveryDate ? dayjs(order.deliveryDate) : null,
        products: products,
      });
      setIsModalVisible(true);
    }
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
      // Get selected customer details
      const selectedCustomer = safeFind(customers, c => c.id === values.customerId);
      if (!selectedCustomer) {
        message.error(t('orders.customerNotFound'));
        return;
      }

      // Calculate total amount from products array
      const products = ensureArray(values.products);
      const totalAmount = safeReduce(products, (sum: number, product: any) => {
        return sum + ((product?.quantity || 0) * (product?.unitPrice || 0));
      }, 0);

      // For now, we'll still send the first product as the main product
      // This maintains backward compatibility with the current backend
      const firstProduct = products[0] || { cylinderType: '20kg', quantity: 1, unitPrice: 800 };

      // Map frontend cylinder types to backend quantity fields
      const quantityFields: Record<string, number> = {
        qty_50kg: 0,
        qty_20kg: 0,
        qty_16kg: 0,
        qty_10kg: 0,
        qty_4kg: 0,
      };

      // Process each product and accumulate quantities by type
      safeForEach(products, (product: any) => {
        const qtyField = `qty_${product.cylinderType}`;
        if (qtyField in quantityFields) {
          quantityFields[qtyField] += product.quantity || 0;
        }
      });

      const orderData = {
        // Required fields for backend
        customer_id: values.customerId,
        scheduled_date: values.deliveryDate ? values.deliveryDate.format('YYYY-MM-DDTHH:mm:ss') : values.orderDate.format('YYYY-MM-DDTHH:mm:ss'),
        is_urgent: values.priority === 'urgent',
        payment_method: values.paymentMethod === 'cash' ? '現金' : values.paymentMethod === 'transfer' ? '轉帳' : '信用卡',
        delivery_notes: values.deliveryNotes || '',
        // Cylinder quantities
        ...quantityFields,
        // Additional frontend fields (may be ignored by backend)
        orderDate: values.orderDate.format('YYYY-MM-DD'),
        deliveryDate: values.deliveryDate ? values.deliveryDate.format('YYYY-MM-DD') : null,
        customerName: selectedCustomer.short_name || selectedCustomer.name || selectedCustomer.簡稱,
        customerPhone: selectedCustomer.phone || selectedCustomer.電話 || '',
        customerAddress: selectedCustomer.address || selectedCustomer.地址 || '',
        cylinderType: firstProduct.cylinderType,
        quantity: firstProduct.quantity,
        unitPrice: firstProduct.unitPrice,
        totalAmount: totalAmount,
        products: products,
      };

      // Remove the products field from orderData if backend doesn't support it yet
      // This can be removed once backend is updated to handle multiple products
      if (!selectedOrder || !selectedOrder.products) {
        delete orderData.products;
      }

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
    } catch (error: any) {
      console.error('Order save error:', error);
      if (error.response?.data?.detail) {
        // Show specific error from backend
        message.error(error.response.data.detail);
      } else {
        message.error(t('orders.saveError'));
      }
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
      render: (_, record) => {
        // If order has products array, display all products
        if (safeLength(record.products) > 0) {
          return (
            <Space direction="vertical" size="small">
              {safeMap(record.products, (product, index) => (
                <Space key={index}>
                  <Tag>{product.cylinderType}</Tag>
                  <span>x {product.quantity}</span>
                </Space>
              ))}
            </Space>
          );
        }
        // Fallback to single product display
        return (
          <Space>
            <Tag>{record.cylinderType}</Tag>
            <span>x {record.quantity}</span>
          </Space>
        );
      },
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
  ].filter(column => {
    // Filter out payment-related columns if payment features are disabled
    if (!features.anyPaymentFeature) {
      return column.key !== 'totalAmount' && column.key !== 'payment';
    }
    return true;
  });

  // Use orders directly as they are already filtered by the advanced search
  const filteredOrders = orders;

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[], newSelectedRows: Order[]) => {
      setSelectedRowKeys(newSelectedRowKeys as string[]);
      setSelectedRows(newSelectedRows);
    },
  };

  return (
    <div className="order-management">
      {/* Advanced Search Panel */}
      <OrderSearchPanel
        onSearch={handleAdvancedSearch}
        onExport={handleExportSearchResults}
        customers={customers}
        drivers={drivers}
        loading={searchLoading}
      />
      
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
          {features.anyPaymentFeature && (
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
          )}
        </Row>

        <div style={{ marginBottom: 16 }}>
          <Space style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
            >
              {t('orders.createOrder')}
            </Button>
          </Space>
          
          {safeLength(selectedRowKeys) > 0 && (
            <BulkOrderActions
              selectedOrderIds={selectedRowKeys}
              selectedOrders={selectedRows}
              onActionComplete={() => {
                setSelectedRowKeys([]);
                setSelectedRows([]);
                fetchOrders();
                fetchStatistics();
              }}
            />
          )}
        </div>

        <Table
          columns={columns}
          dataSource={filteredOrders}
          rowKey="id"
          loading={loading}
          rowSelection={rowSelection}
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
        onCancel={() => {
          setIsModalVisible(false);
          setSelectedCustomerId(null);
        }}
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
                  loading={customersLoading}
                  notFoundContent={customersLoading ? t('common.loading') : t('common.noData')}
                  filterOption={(input, option) =>
                    option?.children?.toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                  onChange={(value) => setSelectedCustomerId(value ? Number(value) : null)}
                >
                  {safeMap(customers, (customer, index) => (
                    <Select.Option 
                      key={customer.id || customer.編號 || `customer-${index}`} 
                      value={customer.id || customer.編號}
                    >
                      {customer.short_name || customer.name || customer.簡稱}
                    </Select.Option>
                  ))}
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

          {features.anyPaymentFeature && (
            <CreditSummary customerId={selectedCustomerId} />
          )}

          {selectedCustomerId && (
            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <TemplateQuickSelect
                customerId={selectedCustomerId}
                onTemplateSelect={(template) => {
                  // Apply template data to form
                  const templateProducts = safeMap(template.products, (product: any) => ({
                    cylinderType: '20kg', // Default, will need to map from product ID
                    quantity: product.quantity,
                    unitPrice: product.unit_price || 800
                  }));
                  
                  form.setFieldsValue({
                    products: templateProducts,
                    priority: template.priority,
                    paymentMethod: template.payment_method,
                    deliveryNotes: template.delivery_notes
                  });
                }}
              />
            </div>
          )}

          <Form.List
            name="products"
            initialValue={[{ cylinderType: '20kg', quantity: 1, unitPrice: 800 }]}
          >
            {(fields, { add, remove }) => (
              <>
                <Card 
                  title={t('orders.products')}
                  extra={
                    <Button
                      type="link"
                      onClick={() => add({ cylinderType: '20kg', quantity: 1, unitPrice: 800 })}
                      icon={<PlusOutlined />}
                    >
                      {t('orders.addProduct')}
                    </Button>
                  }
                  style={{ marginBottom: 16 }}
                >
                  {safeMap(fields, ({ key, name, ...restField }) => (
                    <Row gutter={16} key={key} style={{ marginBottom: 8 }}>
                      <Col span={8}>
                        <Form.Item
                          {...restField}
                          name={[name, 'cylinderType']}
                          label={key === 0 ? t('orders.cylinderType') : ''}
                          rules={[{ required: true, message: t('validation.required') }]}
                        >
                          <Select>
                            <Select.Option value="20kg">20kg</Select.Option>
                            <Select.Option value="16kg">16kg</Select.Option>
                            <Select.Option value="50kg">50kg</Select.Option>
                            <Select.Option value="10kg">10kg</Select.Option>
                            <Select.Option value="4kg">4kg</Select.Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'quantity']}
                          label={key === 0 ? t('orders.quantity') : ''}
                          rules={[{ required: true, message: t('validation.required') }]}
                        >
                          <InputNumber min={1} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'unitPrice']}
                          label={key === 0 ? t('orders.unitPrice') : ''}
                          rules={[{ required: true, message: t('validation.required') }]}
                        >
                          <InputNumber
                            min={0}
                            prefix="NT$"
                            style={{ width: '100%' }}
                            onChange={() => {
                              // Trigger total calculation
                              form.validateFields();
                            }}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        {safeLength(fields) > 1 && (
                          <Button
                            type="link"
                            danger
                            onClick={() => remove(name)}
                            icon={<MinusCircleOutlined />}
                            style={{ marginTop: key === 0 ? 30 : 0 }}
                          >
                            {t('common.remove')}
                          </Button>
                        )}
                      </Col>
                    </Row>
                  ))}
                </Card>
                
                <Form.Item shouldUpdate>
                  {() => {
                    const products = ensureArray(form.getFieldValue('products'));
                    const total = safeReduce(products, (sum: number, product: any) => {
                      return sum + ((product?.quantity || 0) * (product?.unitPrice || 0));
                    }, 0);
                    
                    return (
                      <Card>
                        <Statistic
                          title={t('orders.totalAmount')}
                          value={total}
                          prefix="NT$"
                          precision={0}
                        />
                      </Card>
                    );
                  }}
                </Form.Item>
              </>
            )}
          </Form.List>

          {features.anyPaymentFeature && (
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
          )}

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
                {features.anyPaymentFeature && (
                  <Col span={12}>
                    <strong>{t('orders.amount')}:</strong> NT$ {selectedOrder.totalAmount.toLocaleString()}
                  </Col>
                )}
              </Row>
            </Card>

            <Card title={t('orders.timeline')}>
              <Timeline>
                {safeMap(orderTimeline, (item, index) => (
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

      <OrderModificationModal
        visible={isModificationModalVisible}
        order={selectedOrder}
        onClose={() => setIsModificationModalVisible(false)}
        onSuccess={() => {
          fetchOrders();
          fetchStatistics();
        }}
      />
    </div>
  );
};

export default OrderManagement;