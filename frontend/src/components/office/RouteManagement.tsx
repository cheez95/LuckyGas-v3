import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  DatePicker,
  Select,
  Row,
  Col,
  Statistic,
  Tooltip,
  Progress,
} from 'antd';
import {
  EnvironmentOutlined,
  CarOutlined,
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

interface Route {
  id: number;
  route_number: string;
  route_date: string;
  area: string;
  driver_name: string;
  vehicle_plate: string;
  status: 'planned' | 'optimized' | 'in_progress' | 'completed';
  total_orders: number;
  completed_orders: number;
  total_distance_km: number;
  estimated_duration_minutes: number;
}

const RouteManagement: React.FC = () => {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());

  // Mock data for demo
  useEffect(() => {
    setLoading(true);
    setTimeout(() => {
      setRoutes([
        {
          id: 1,
          route_number: 'R-20250120-001',
          route_date: '2025-01-20',
          area: '大安區',
          driver_name: '王大明',
          vehicle_plate: 'ABC-1234',
          status: 'in_progress',
          total_orders: 15,
          completed_orders: 8,
          total_distance_km: 45.2,
          estimated_duration_minutes: 240,
        },
        {
          id: 2,
          route_number: 'R-20250120-002',
          route_date: '2025-01-20',
          area: '信義區',
          driver_name: '李小華',
          vehicle_plate: 'XYZ-5678',
          status: 'planned',
          total_orders: 12,
          completed_orders: 0,
          total_distance_km: 38.5,
          estimated_duration_minutes: 180,
        },
      ]);
      setLoading(false);
    }, 1000);
  }, [selectedDate]);

  const getStatusTag = (status: string) => {
    const statusConfig = {
      planned: { color: 'default', text: '已規劃' },
      optimized: { color: 'processing', text: '已優化' },
      in_progress: { color: 'blue', text: '配送中' },
      completed: { color: 'success', text: '已完成' },
    };
    const config = statusConfig[status as keyof typeof statusConfig];
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns: ColumnsType<Route> = [
    {
      title: '路線編號',
      dataIndex: 'route_number',
      key: 'route_number',
      fixed: 'left',
    },
    {
      title: '日期',
      dataIndex: 'route_date',
      key: 'route_date',
      render: (date) => dayjs(date).format('MM/DD'),
    },
    {
      title: '區域',
      dataIndex: 'area',
      key: 'area',
    },
    {
      title: '司機',
      dataIndex: 'driver_name',
      key: 'driver_name',
    },
    {
      title: '車牌',
      dataIndex: 'vehicle_plate',
      key: 'vehicle_plate',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => getStatusTag(status),
    },
    {
      title: '訂單進度',
      key: 'progress',
      render: (_, record) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <span>{record.completed_orders} / {record.total_orders}</span>
          <Progress
            percent={Math.round((record.completed_orders / record.total_orders) * 100)}
            size="small"
            strokeColor="#52c41a"
          />
        </Space>
      ),
    },
    {
      title: '距離',
      dataIndex: 'total_distance_km',
      key: 'total_distance_km',
      render: (km) => `${km} km`,
    },
    {
      title: '預估時間',
      dataIndex: 'estimated_duration_minutes',
      key: 'estimated_duration_minutes',
      render: (minutes) => `${Math.floor(minutes / 60)}小時${minutes % 60}分`,
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right',
      render: () => (
        <Space size="small">
          <Tooltip title="查看詳情">
            <Button type="text" icon={<EyeOutlined />} />
          </Tooltip>
          <Tooltip title="編輯路線">
            <Button type="text" icon={<EditOutlined />} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日路線"
              value={routes.length}
              prefix={<EnvironmentOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="派遣司機"
              value={routes.filter(r => r.driver_name).length}
              prefix={<CarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="配送中"
              value={routes.filter(r => r.status === 'in_progress').length}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={routes.filter(r => r.status === 'completed').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Card */}
      <Card
        title="路線管理"
        extra={
          <Space>
            <DatePicker
              value={selectedDate}
              onChange={(date) => setSelectedDate(date || dayjs())}
            />
            <Button type="primary" icon={<PlusOutlined />}>
              新增路線
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
              刷新
            </Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Select defaultValue="all" style={{ width: 120 }}>
              <Select.Option value="all">全部狀態</Select.Option>
              <Select.Option value="planned">已規劃</Select.Option>
              <Select.Option value="in_progress">配送中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
            </Select>
            <Select placeholder="選擇區域" style={{ width: 120 }} allowClear>
              <Select.Option value="大安區">大安區</Select.Option>
              <Select.Option value="信義區">信義區</Select.Option>
              <Select.Option value="中山區">中山區</Select.Option>
              <Select.Option value="松山區">松山區</Select.Option>
            </Select>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={routes}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆`,
          }}
        />
      </Card>

      <Card title="路線地圖" style={{ marginTop: 16 }}>
        <div style={{ height: 400, background: '#f0f2f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Space direction="vertical" align="center">
            <EnvironmentOutlined style={{ fontSize: 48, color: '#bfbfbf' }} />
            <span style={{ color: '#8c8c8c' }}>地圖功能即將上線</span>
            <span style={{ color: '#8c8c8c', fontSize: 12 }}>將整合 Google Maps 顯示配送路線</span>
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default RouteManagement;