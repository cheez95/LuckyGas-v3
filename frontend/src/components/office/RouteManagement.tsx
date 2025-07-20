import React, { useState, useEffect, useCallback } from 'react';
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
  Modal,
  message,
  Drawer,
  Descriptions,
  List,
  Timeline,
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
  RocketOutlined,
  SyncOutlined,
  FieldTimeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useWebSocket } from '../../hooks/useWebSocket';
import { routeService, RouteWithDetails, RouteStop } from '../../services/route.service';
import { orderService } from '../../services/order.service';
import GoogleMapsPlaceholder, { MapMarker } from '../common/GoogleMapsPlaceholder';


const RouteManagement: React.FC = () => {
  const { on } = useWebSocket();
  const [routes, setRoutes] = useState<RouteWithDetails[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [selectedArea, setSelectedArea] = useState<string>();
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedRoute, setSelectedRoute] = useState<RouteWithDetails | null>(null);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [optimizeModalVisible, setOptimizeModalVisible] = useState(false);
  const [mapMarkers, setMapMarkers] = useState<MapMarker[]>([]);

  // Fetch routes
  const fetchRoutes = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = {
        date_from: selectedDate.startOf('day').toISOString(),
        date_to: selectedDate.endOf('day').toISOString(),
      };
      if (selectedArea) params.area = selectedArea;
      if (selectedStatus !== 'all') params.status = selectedStatus;

      const data = await routeService.getRoutes(params);
      setRoutes(data);

      // Generate map markers
      const markers: MapMarker[] = [
        {
          id: 'depot',
          position: { lat: 25.0330, lng: 121.5654 },
          title: '幸福氣倉庫',
          type: 'depot',
        },
      ];

      data.forEach((route, idx) => {
        if (route.status === 'in_progress') {
          markers.push({
            id: `driver-${route.id}`,
            position: { 
              lat: 25.0330 + (idx * 0.01), 
              lng: 121.5654 + (idx * 0.01) 
            },
            title: route.driver_name || `司機 ${route.driver_id}`,
            type: 'driver',
            info: `路線: ${route.route_number}`,
          });
        }
      });

      setMapMarkers(markers);
    } catch (error) {
      message.error('無法載入路線資料');
      console.error('Failed to fetch routes:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedArea, selectedStatus]);

  // Initial load
  useEffect(() => {
    fetchRoutes();
  }, [fetchRoutes]);

  // WebSocket listeners
  useEffect(() => {
    const unsubscribe = on('route_update', () => {
      fetchRoutes();
    });
    return () => unsubscribe();
  }, [on, fetchRoutes]);

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

  // View route details
  const viewRouteDetails = async (route: RouteWithDetails) => {
    setSelectedRoute(route);
    setDetailDrawerVisible(true);
  };

  // Optimize routes
  const handleOptimizeRoutes = async () => {
    Modal.confirm({
      title: '確認優化路線？',
      content: '系統將自動分配訂單到可用車輛並優化配送路線',
      onOk: async () => {
        try {
          const result = await routeService.optimizeRoutesBatch({
            date: selectedDate.format('YYYY-MM-DD'),
            area: selectedArea,
          });
          message.success(`成功創建 ${result.routes_created} 條路線，分配了 ${result.orders_assigned} 個訂單`);
          setOptimizeModalVisible(false);
          fetchRoutes();
        } catch (error) {
          message.error('路線優化失敗');
          console.error('Failed to optimize routes:', error);
        }
      },
    });
  };

  const columns: ColumnsType<RouteWithDetails> = [
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
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看詳情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => viewRouteDetails(record)}
            />
          </Tooltip>
          <Tooltip title="編輯路線">
            <Button 
              type="text" 
              icon={<EditOutlined />}
              disabled={record.status === 'completed'}
            />
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
            <Button 
              type="primary" 
              icon={<RocketOutlined />}
              onClick={() => setOptimizeModalVisible(true)}
            >
              優化路線
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchRoutes}>
              刷新
            </Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Select 
              value={selectedStatus}
              onChange={setSelectedStatus}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部狀態</Select.Option>
              <Select.Option value="planned">已規劃</Select.Option>
              <Select.Option value="optimized">已優化</Select.Option>
              <Select.Option value="in_progress">配送中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
            </Select>
            <Select 
              placeholder="選擇區域" 
              style={{ width: 120 }} 
              allowClear
              value={selectedArea}
              onChange={setSelectedArea}
            >
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
        <GoogleMapsPlaceholder
          height={400}
          markers={mapMarkers}
          onMarkerClick={(marker) => {
            if (marker.type === 'driver') {
              message.info(`司機位置: ${marker.title}`);
            }
          }}
        />
      </Card>

      {/* Route detail drawer */}
      <Drawer
        title={`路線詳情 - ${selectedRoute?.route_number}`}
        placement="right"
        width={600}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {selectedRoute && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Descriptions bordered column={1}>
              <Descriptions.Item label="路線編號">
                {selectedRoute.route_number}
              </Descriptions.Item>
              <Descriptions.Item label="日期">
                {dayjs(selectedRoute.route_date).format('YYYY-MM-DD')}
              </Descriptions.Item>
              <Descriptions.Item label="區域">
                {selectedRoute.area || '未指定'}
              </Descriptions.Item>
              <Descriptions.Item label="司機">
                {selectedRoute.driver_name || '未指派'}
              </Descriptions.Item>
              <Descriptions.Item label="車輛">
                {selectedRoute.vehicle_plate || '未指定'}
              </Descriptions.Item>
              <Descriptions.Item label="狀態">
                {getStatusTag(selectedRoute.status)}
              </Descriptions.Item>
              <Descriptions.Item label="配送進度">
                <Progress
                  percent={Math.round(
                    (selectedRoute.completed_orders / selectedRoute.total_orders) * 100
                  )}
                />
                <span>
                  {selectedRoute.completed_orders} / {selectedRoute.total_orders} 完成
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="總距離">
                {selectedRoute.total_distance_km} 公里
              </Descriptions.Item>
              <Descriptions.Item label="預估時間">
                {selectedRoute.estimated_duration_minutes
                  ? `${Math.floor(selectedRoute.estimated_duration_minutes / 60)}小時
                     ${selectedRoute.estimated_duration_minutes % 60}分`
                  : '未計算'}
              </Descriptions.Item>
            </Descriptions>

            {selectedRoute.stops && selectedRoute.stops.length > 0 && (
              <Card title="配送站點" size="small">
                <Timeline>
                  {selectedRoute.stops
                    .sort((a, b) => a.stop_sequence - b.stop_sequence)
                    .map((stop) => (
                      <Timeline.Item
                        key={stop.id}
                        color={stop.is_completed ? 'green' : 'blue'}
                      >
                        <Space direction="vertical" size="small">
                          <Space>
                            <Tag>{stop.stop_sequence}</Tag>
                            <Text strong>
                              訂單 #{stop.order_id}
                            </Text>
                            {stop.is_completed && (
                              <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            )}
                          </Space>
                          <Text type="secondary">{stop.address}</Text>
                          {stop.estimated_arrival && (
                            <Text type="secondary">
                              預計到達：
                              {new Date(stop.estimated_arrival).toLocaleTimeString(
                                'zh-TW',
                                {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                }
                              )}
                            </Text>
                          )}
                        </Space>
                      </Timeline.Item>
                    ))}
                </Timeline>
              </Card>
            )}
          </Space>
        )}
      </Drawer>

      {/* Optimize modal */}
      <Modal
        title="路線優化"
        open={optimizeModalVisible}
        onOk={handleOptimizeRoutes}
        onCancel={() => setOptimizeModalVisible(false)}
        okText="開始優化"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <p>系統將為 {selectedDate.format('YYYY-MM-DD')} 的訂單進行路線優化</p>
          {selectedArea && <p>區域限制：{selectedArea}</p>}
          <p>優化功能將：</p>
          <ul>
            <li>自動分配未指派的訂單到可用車輛</li>
            <li>根據地理位置優化配送順序</li>
            <li>考慮車輛容量和時間窗口</li>
            <li>最小化總配送距離和時間</li>
          </ul>
        </Space>
      </Modal>
    </div>
  );
};

export default RouteManagement;