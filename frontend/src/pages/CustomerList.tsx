/**
 * Customer List Page
 * 客戶列表頁面
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Table,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Card,
  Row,
  Col,
  Pagination,
  Checkbox,
  Drawer,
  Badge,
  Tooltip,
  message,
  Spin,
  Empty,
  Typography
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  ExportOutlined,
  UserOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  EyeOutlined,
  PlusCircleOutlined,
  FireOutlined,
  DollarOutlined,
  TagOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { debounce } from 'lodash';
import {
  customerApi,
  customerCache,
  useCustomerQueryKeys
} from '../services/customerApi';
import {
  CustomerSummary,
  CustomerFilterParams,
  CustomerTypeDisplay,
  PaymentMethodDisplay,
  PricingMethodDisplay
} from '../types/Customer.types';
import CustomerViewModal from '../components/office/CustomerViewModal';

const { Title, Text } = Typography;
const { Option } = Select;
const { Search } = Input;

const CustomerList: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [filterVisible, setFilterVisible] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = useState<number | string | null>(null);

  // Filter state from URL params
  const filters: CustomerFilterParams = {
    page: parseInt(searchParams.get('page') || '1'),
    limit: parseInt(searchParams.get('limit') || '50'),
    search: searchParams.get('search') || undefined,
    area: searchParams.get('area') || undefined,
    district: searchParams.get('district') || undefined,
    customer_type: searchParams.get('customer_type') || undefined,
    is_active: searchParams.get('is_active') === 'false' ? false : true
  };

  // Load areas and districts on mount
  useEffect(() => {
    customerApi.getAreasList().then(setAreas).catch(console.error);
    customerApi.getDistrictsList().then(setDistricts).catch(console.error);
  }, []);

  // Fetch customers
  const fetchCustomers = useCallback(async (params: CustomerFilterParams) => {
    try {
      setLoading(true);
      
      // Try cache first
      const cached = customerCache.getCachedCustomerList();
      if (cached && JSON.stringify(params) === JSON.stringify({ page: 1, limit: 50 })) {
        setCustomers(cached.items);
        setTotal(cached.total);
      }

      const response = await customerApi.getCustomers(params);
      setCustomers(response.items);
      setTotal(response.total);
      
      // Cache the list for offline access
      if (params.page === 1 && params.limit === 50 && !params.search) {
        customerCache.saveCustomerList(response);
      }
    } catch (error) {
      console.error('Failed to fetch customers:', error);
      message.error('無法載入客戶列表');
      
      // Try to use cached data on error
      const cached = customerCache.getCachedCustomerList();
      if (cached) {
        setCustomers(cached.items);
        setTotal(cached.total);
        message.info('使用離線快取資料');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Load customers when filters change
  useEffect(() => {
    fetchCustomers(filters);
  }, [searchParams]);

  // Debounced search
  const handleSearch = useMemo(
    () => debounce((value: string) => {
      const params = new URLSearchParams(searchParams);
      if (value) {
        params.set('search', value);
      } else {
        params.delete('search');
      }
      params.set('page', '1'); // Reset to first page
      setSearchParams(params);
    }, 300),
    [searchParams, setSearchParams]
  );

  // Update filter
  const updateFilter = (key: string, value: string | undefined) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set('page', '1'); // Reset to first page
    setSearchParams(params);
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchParams({ page: '1', limit: '50' });
    message.success('已清除所有篩選條件');
  };

  // Handle row selection
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  // Export selected customers
  const handleExport = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('請先選擇要匯出的客戶');
      return;
    }
    // TODO: Implement export functionality
    message.info(`準備匯出 ${selectedRowKeys.length} 位客戶資料`);
  };

  // Handle view customer
  const handleViewCustomer = (customerId: number | string) => {
    setSelectedCustomerId(customerId);
    setViewModalVisible(true);
  };

  // Handle edit customer
  const handleEditCustomer = () => {
    if (selectedCustomerId) {
      navigate(`/customers/${selectedCustomerId}/edit`);
    }
  };

  // Table columns
  const columns: ColumnsType<CustomerSummary> = [
    {
      title: '客戶代碼',
      dataIndex: 'customer_code',
      key: 'customer_code',
      width: 120,
      fixed: 'left',
      render: (code: string, record) => (
        <a 
          onClick={() => handleViewCustomer(record.id)}
          style={{ fontWeight: 500 }}
        >
          <TagOutlined style={{ marginRight: 4 }} />
          {code}
        </a>
      )
    },
    {
      title: '客戶名稱',
      dataIndex: 'short_name',
      key: 'short_name',
      width: 150,
      render: (name: string, record) => (
        <Space>
          <UserOutlined style={{ color: '#1890ff' }} />
          <Text strong>{name}</Text>
          {!record.is_active && <Tag color="red">已終止</Tag>}
        </Space>
      )
    },
    {
      title: '類型',
      dataIndex: 'customer_type',
      key: 'customer_type',
      width: 100,
      render: (type: string) => (
        <Tag color="blue">
          {CustomerTypeDisplay[type] || type}
        </Tag>
      )
    },
    {
      title: '區域',
      dataIndex: 'area',
      key: 'area',
      width: 80,
      render: (area: string, record) => (
        <Tooltip title={`${record.district} - ${area}`}>
          <Badge count={area} style={{ backgroundColor: '#52c41a' }} />
        </Tooltip>
      )
    },
    {
      title: '地址',
      dataIndex: 'address',
      key: 'address',
      width: 200,
      ellipsis: true,
      render: (address: string) => (
        <Tooltip title={address}>
          <Space>
            <EnvironmentOutlined />
            <Text>{address}</Text>
          </Space>
        </Tooltip>
      )
    },
    {
      title: '瓦斯瓶配置',
      dataIndex: 'cylinder_summary',
      key: 'cylinder_summary',
      width: 180,
      render: (summary: string) => {
        if (!summary || summary === '無') {
          return <Text type="secondary">無配置</Text>;
        }
        const cylinders = summary.split(', ');
        return (
          <Space wrap>
            <FireOutlined style={{ color: '#fa8c16' }} />
            {cylinders.map((cyl, idx) => (
              <Tag key={idx} color="orange">{cyl}</Tag>
            ))}
          </Space>
        );
      }
    },
    {
      title: '計價方式',
      dataIndex: 'pricing_method',
      key: 'pricing_method',
      width: 100,
      render: (method: string) => (
        <Tag color="purple">
          {PricingMethodDisplay[method] || method}
        </Tag>
      )
    },
    {
      title: '付款方式',
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 120,
      render: (method: string) => (
        <Space>
          <DollarOutlined style={{ color: '#13c2c2' }} />
          <Tag color="cyan">
            {PaymentMethodDisplay[method] || method}
          </Tag>
        </Space>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Tooltip title="檢視詳情">
          <Button
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewCustomer(record.id)}
            style={{ borderRadius: 6 }}
          >
            檢視
          </Button>
        </Tooltip>
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Title level={2}>
            客戶管理
            <Text type="secondary" style={{ fontSize: 14, marginLeft: 16 }}>
              共 {total} 位客戶
            </Text>
          </Title>
        </Col>
        <Col>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchCustomers(filters)}
              loading={loading}
            >
              重新載入
            </Button>
            <Button
              icon={<ExportOutlined />}
              onClick={handleExport}
              disabled={selectedRowKeys.length === 0}
            >
              匯出 ({selectedRowKeys.length})
            </Button>
            <Button
              type="primary"
              icon={<PlusCircleOutlined />}
              onClick={() => navigate('/customers/new')}
              size="middle"
              style={{ borderRadius: 6 }}
            >
              新增客戶
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="搜尋客戶名稱、代碼、地址、電話"
              allowClear
              defaultValue={filters.search}
              onSearch={(value) => handleSearch(value)}
              onChange={(e) => handleSearch(e.target.value)}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="選擇區域"
              allowClear
              value={filters.area}
              onChange={(value) => updateFilter('area', value)}
              style={{ width: '100%' }}
            >
              {areas.map(area => (
                <Option key={area} value={area}>{area}</Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="選擇區"
              allowClear
              value={filters.district}
              onChange={(value) => updateFilter('district', value)}
              style={{ width: '100%' }}
            >
              {districts.map(district => (
                <Option key={district} value={district}>{district}</Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="客戶類型"
              allowClear
              value={filters.customer_type}
              onChange={(value) => updateFilter('customer_type', value)}
              style={{ width: '100%' }}
            >
              {Object.entries(CustomerTypeDisplay).map(([key, value]) => (
                <Option key={key} value={key}>{value}</Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Space>
              <Checkbox
                checked={filters.is_active !== false}
                onChange={(e) => updateFilter('is_active', e.target.checked ? undefined : 'false')}
              >
                僅顯示使用中
              </Checkbox>
              <Button
                icon={<FilterOutlined />}
                onClick={() => setFilterVisible(true)}
              >
                更多
              </Button>
              {(filters.search || filters.area || filters.district || filters.customer_type) && (
                <Button onClick={clearFilters}>
                  清除篩選
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card>
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={customers}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 1500 }}
          locale={{
            emptyText: <Empty description="沒有找到客戶資料" />
          }}
        />
        
        {/* Pagination */}
        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Pagination
            current={filters.page}
            pageSize={filters.limit}
            total={total}
            showTotal={(total, range) => `第 ${range[0]}-${range[1]} 筆，共 ${total} 筆`}
            showSizeChanger
            pageSizeOptions={['20', '50', '100']}
            onChange={(page, pageSize) => {
              const params = new URLSearchParams(searchParams);
              params.set('page', page.toString());
              params.set('limit', pageSize.toString());
              setSearchParams(params);
            }}
          />
        </div>
      </Card>

      {/* Advanced Filter Drawer */}
      <Drawer
        title="進階篩選"
        placement="right"
        onClose={() => setFilterVisible(false)}
        open={filterVisible}
        width={360}
      >
        {/* TODO: Add more advanced filters */}
        <p>更多篩選選項開發中...</p>
      </Drawer>

      {/* Customer View Modal */}
      {selectedCustomerId && (
        <CustomerViewModal
          customerId={selectedCustomerId}
          visible={viewModalVisible}
          onClose={() => {
            setViewModalVisible(false);
            setSelectedCustomerId(null);
          }}
          onEdit={handleEditCustomer}
        />
      )}
    </div>
  );
};

export default CustomerList;