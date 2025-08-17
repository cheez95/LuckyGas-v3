import React, { useState, useEffect } from 'react';
import { Table, Card, DatePicker, Select, Space, Typography, Button, Statistic, Row, Col, message } from 'antd';
import { ReloadOutlined, ExportOutlined, CalendarOutlined, DollarOutlined, TruckOutlined, UserOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import api from '../../services/api';

const { Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface DeliveryRecord {
  id: number;
  transaction_date: string;
  transaction_time?: string;
  customer_code: string;
  customer_name?: string;
  customer_address?: string;
  qty_50kg: number;
  qty_20kg: number;
  qty_16kg: number;
  qty_10kg: number;
  qty_4kg: number;
  total_weight_kg: number;
  total_cylinders: number;
}

interface DeliveryStats {
  total_deliveries: number;
  total_weight_kg: number;
  total_cylinders: number;
  unique_customers: number;
  cylinders_by_type: Record<string, number>;
  top_customers: Array<{
    customer_code: string;
    customer_name: string;
    deliveries: number;
    total_weight: number;
  }>;
  deliveries_by_date: Array<{
    date: string;
    count: number;
    weight: number;
  }>;
}

const DeliveryHistory: React.FC = () => {
  const [deliveries, setDeliveries] = useState<DeliveryRecord[]>([]);
  const [stats, setStats] = useState<DeliveryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([
    dayjs().startOf('month'),
    dayjs().endOf('month'),
  ]);
  const [selectedCustomer, setSelectedCustomer] = useState<string | undefined>(undefined);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // Fetch delivery history
  const fetchDeliveries = async () => {
    setLoading(true);
    try {
      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      };

      if (dateRange[0] && dateRange[1]) {
        params.date_from = dateRange[0].format('YYYY-MM-DD');
        params.date_to = dateRange[1].format('YYYY-MM-DD');
      }

      if (selectedCustomer) {
        params.customer_code = selectedCustomer;
      }

      // Try deliveries endpoint instead of delivery-history
      const response = await api.get('/deliveries', { params });
      setDeliveries(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (error: any) {
      // Handle 404 gracefully - endpoint might not exist yet
      if (error.response?.status === 404) {
        console.warn('Deliveries endpoint not found, showing empty state');
        setDeliveries([]);
        setTotal(0);
      } else {
        message.error('載入配送歷史失敗');
      }
    } finally {
      setLoading(false);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const params: any = {};
      if (dateRange[0] && dateRange[1]) {
        params.date_from = dateRange[0].format('YYYY-MM-DD');
        params.date_to = dateRange[1].format('YYYY-MM-DD');
      }

      // Try deliveries/stats endpoint
      const response = await api.get('/deliveries/stats', { params });
      setStats(response.data);
    } catch (error: any) {
      // Handle 404 gracefully - endpoint might not exist yet
      if (error.response?.status === 404) {
        console.warn('Deliveries stats endpoint not found, using defaults');
        setStats({
          total_deliveries: 0,
          total_amount: 0,
          total_customers: 0,
          total_drivers: 0
        });
      } else {
        console.error('Failed to fetch stats:', error);
      }
    }
  };

  useEffect(() => {
    fetchDeliveries();
    fetchStats();
  }, [currentPage, pageSize, dateRange, selectedCustomer]);

  const columns: ColumnsType<DeliveryRecord> = [
    {
      title: '日期',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      width: 100,
      render: (date) => dayjs(date).format('YYYY/MM/DD'),
      sorter: (a, b) => dayjs(a.transaction_date).unix() - dayjs(b.transaction_date).unix(),
    },
    {
      title: '時間',
      dataIndex: 'transaction_time',
      key: 'transaction_time',
      width: 80,
      render: (time) => time || '-',
    },
    {
      title: '客戶編號',
      dataIndex: 'customer_code',
      key: 'customer_code',
      width: 100,
    },
    {
      title: '客戶名稱',
      dataIndex: 'customer_name',
      key: 'customer_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '地址',
      dataIndex: 'customer_address',
      key: 'customer_address',
      ellipsis: true,
    },
    {
      title: '50kg',
      dataIndex: 'qty_50kg',
      key: 'qty_50kg',
      width: 60,
      render: (qty) => qty || '-',
    },
    {
      title: '20kg',
      dataIndex: 'qty_20kg',
      key: 'qty_20kg',
      width: 60,
      render: (qty) => qty || '-',
    },
    {
      title: '16kg',
      dataIndex: 'qty_16kg',
      key: 'qty_16kg',
      width: 60,
      render: (qty) => qty || '-',
    },
    {
      title: '10kg',
      dataIndex: 'qty_10kg',
      key: 'qty_10kg',
      width: 60,
      render: (qty) => qty || '-',
    },
    {
      title: '4kg',
      dataIndex: 'qty_4kg',
      key: 'qty_4kg',
      width: 60,
      render: (qty) => qty || '-',
    },
    {
      title: '總重量(kg)',
      dataIndex: 'total_weight_kg',
      key: 'total_weight_kg',
      width: 100,
      render: (weight) => `${weight} kg`,
    },
    {
      title: '總桶數',
      dataIndex: 'total_cylinders',
      key: 'total_cylinders',
      width: 80,
    },
  ];

  const handleTableChange = (pagination: any) => {
    setCurrentPage(pagination.current);
    setPageSize(pagination.pageSize);
  };

  const handleExport = () => {
    message.info('匯出功能開發中');
  };

  return (
    <div>
      <Title level={2}>配送歷史記錄</Title>

      {/* Statistics */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="總配送次數"
                value={stats.total_deliveries}
                prefix={<TruckOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="總配送重量"
                value={stats.total_weight_kg}
                suffix="kg"
                prefix={<DollarOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="總配送桶數"
                value={stats.total_cylinders}
                prefix={<CalendarOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="服務客戶數"
                value={stats.unique_customers}
                prefix={<UserOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Top Customers */}
      {stats && stats.top_customers.length > 0 && (
        <Card title="主要客戶" style={{ marginBottom: 16 }}>
          <Row gutter={8}>
            {stats.top_customers.slice(0, 5).map((customer, index) => (
              <Col span={4} key={customer.customer_code}>
                <Card size="small">
                  <Statistic
                    title={`${index + 1}. ${customer.customer_name || customer.customer_code}`}
                    value={customer.deliveries}
                    suffix="次"
                  />
                  <div style={{ fontSize: 12, color: '#999' }}>
                    {customer.total_weight} kg
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* Main Table */}
      <Card
        title="配送記錄"
        extra={
          <Space>
            <RangePicker
              value={dateRange}
              onChange={(dates) => {
                setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null]);
                setCurrentPage(1);
              }}
            />
            <Select
              placeholder="選擇客戶"
              style={{ width: 200 }}
              allowClear
              showSearch
              value={selectedCustomer}
              onChange={(value) => {
                setSelectedCustomer(value);
                setCurrentPage(1);
              }}
            >
              {stats?.top_customers.map((customer) => (
                <Option key={customer.customer_code} value={customer.customer_code}>
                  {customer.customer_name || customer.customer_code}
                </Option>
              ))}
            </Select>
            <Button icon={<ExportOutlined />} onClick={handleExport}>
              匯出
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchDeliveries}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={deliveries}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          onChange={handleTableChange}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆記錄`,
          }}
        />
      </Card>

      {/* Cylinder Type Summary */}
      {stats && (
        <Card title="瓦斯桶類型統計" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            {Object.entries(stats.cylinders_by_type).map(([type, count]) => (
              <Col span={4} key={type}>
                <Statistic
                  title={type}
                  value={count}
                  suffix="桶"
                />
              </Col>
            ))}
          </Row>
        </Card>
      )}
    </div>
  );
};

export default DeliveryHistory;