import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  DatePicker,
  Select,
  Table,
  Tag,
  Space,
  message,
  Modal,
  Form,
  InputNumber,
  Divider,
  Statistic,
  Tooltip,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  SaveOutlined,
  SendOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  CarOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs, { Dayjs } from 'dayjs';
import type { ColumnsType } from 'antd/es/table';
import RoutePlanningMap from '../../components/dispatch/maps/RoutePlanningMap';
import { orderService } from '../../services/order.service';
import { routeService } from '../../services/route.service';
import { driverService } from '../../services/driver.service';

interface Order {
  id: number;
  orderNumber: string;
  customerName: string;
  customerCode: string;
  deliveryAddress: string;
  area: string;
  products: string;
  totalAmount: number;
  isUrgent: boolean;
  deliveryNotes?: string;
  location?: {
    lat: number;
    lng: number;
  };
}

interface Driver {
  id: number;
  fullName: string;
  username: string;
  vehicleNumber?: string;
  vehicleType?: string;
  isAvailable: boolean;
}

interface RouteStop {
  id: string;
  orderId: number;
  location: {
    lat: number;
    lng: number;
    address?: string;
  };
  orderNumber: string;
  customerName: string;
  products: string;
  isUrgent?: boolean;
  sequence?: number;
}

interface RoutePlan {
  id?: number;
  routeDate: string;
  driverId?: number;
  stops: RouteStop[];
  totalDistance?: number;
  totalDuration?: number;
  optimizationScore?: number;
}

const RoutePlanning: React.FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  
  // State
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [selectedArea, setSelectedArea] = useState<string>('all');
  const [availableOrders, setAvailableOrders] = useState<Order[]>([]);
  const [selectedOrders, setSelectedOrders] = useState<Order[]>([]);
  const [routeStops, setRouteStops] = useState<RouteStop[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [selectedDriver, setSelectedDriver] = useState<number | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [routeStats, setRouteStats] = useState({
    totalDistance: 0,
    totalDuration: 0,
    totalStops: 0,
    totalWeight: 0,
  });

  // Fetch available orders
  const fetchAvailableOrders = async () => {
    setIsLoading(true);
    try {
      const response = await orderService.searchOrders({
        dateFrom: selectedDate.format('YYYY-MM-DD'),
        dateTo: selectedDate.format('YYYY-MM-DD'),
        status: ['pending', 'confirmed'],
        area: selectedArea !== 'all' ? selectedArea : undefined,
      });
      
      setAvailableOrders(response.orders.map((order: any) => ({
        id: order.id,
        orderNumber: order.orderNumber,
        customerName: order.customer.shortName,
        customerCode: order.customer.customerCode,
        deliveryAddress: order.deliveryAddress || order.customer.address,
        area: order.customer.area,
        products: formatProducts(order),
        totalAmount: order.finalAmount,
        isUrgent: order.isUrgent,
        deliveryNotes: order.deliveryNotes,
        location: order.customer.location ? {
          lat: order.customer.location.latitude,
          lng: order.customer.location.longitude,
        } : generateMockLocation(order.customer.area),
      })));
    } catch (error) {
      message.error(t('dispatch.route.fetchOrdersError'));
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch available drivers
  const fetchDrivers = async () => {
    try {
      const response = await driverService.getAvailableDrivers(selectedDate.format('YYYY-MM-DD'));
      setDrivers(response);
    } catch (error) {
      message.error(t('dispatch.route.fetchDriversError'));
    }
  };

  // Initial data load
  useEffect(() => {
    fetchAvailableOrders();
    fetchDrivers();
  }, [selectedDate, selectedArea]);

  // Format products display
  const formatProducts = (order: any): string => {
    const products = [];
    if (order.qty50kg) products.push(`50kg×${order.qty50kg}`);
    if (order.qty20kg) products.push(`20kg×${order.qty20kg}`);
    if (order.qty16kg) products.push(`16kg×${order.qty16kg}`);
    if (order.qty10kg) products.push(`10kg×${order.qty10kg}`);
    if (order.qty4kg) products.push(`4kg×${order.qty4kg}`);
    return products.join(', ');
  };

  // Generate mock location for demo (in production, use geocoding)
  const generateMockLocation = (area: string) => {
    const baseLocations: Record<string, { lat: number; lng: number }> = {
      '信義區': { lat: 25.0330, lng: 121.5654 },
      '大安區': { lat: 25.0261, lng: 121.5435 },
      '中山區': { lat: 25.0687, lng: 121.5264 },
      '松山區': { lat: 25.0494, lng: 121.5786 },
      '內湖區': { lat: 25.0835, lng: 121.5874 },
    };
    
    const base = baseLocations[area] || { lat: 25.0330, lng: 121.5654 };
    return {
      lat: base.lat + (Math.random() - 0.5) * 0.02,
      lng: base.lng + (Math.random() - 0.5) * 0.02,
    };
  };

  // Add orders to route
  const addOrdersToRoute = (orders: Order[]) => {
    const newStops = orders.map((order, index) => ({
      id: `stop-${Date.now()}-${index}`,
      orderId: order.id,
      location: order.location || generateMockLocation(order.area),
      orderNumber: order.orderNumber,
      customerName: order.customerName,
      products: order.products,
      isUrgent: order.isUrgent,
      sequence: routeStops.length + index + 1,
    }));
    
    setRouteStops([...routeStops, ...newStops]);
    setSelectedOrders([...selectedOrders, ...orders]);
    
    // Update stats
    setRouteStats(prev => ({
      ...prev,
      totalStops: prev.totalStops + orders.length,
    }));
  };

  // Remove stop from route
  const removeStopFromRoute = (stopId: string) => {
    const stopToRemove = routeStops.find(s => s.id === stopId);
    if (!stopToRemove) return;
    
    setRouteStops(routeStops.filter(s => s.id !== stopId));
    setSelectedOrders(selectedOrders.filter(o => o.id !== stopToRemove.orderId));
    
    // Update stats
    setRouteStats(prev => ({
      ...prev,
      totalStops: prev.totalStops - 1,
    }));
  };

  // Optimize route
  const handleOptimizeRoute = async () => {
    if (routeStops.length < 2) {
      message.warning(t('dispatch.route.needMoreStops'));
      return;
    }
    
    setIsOptimizing(true);
    try {
      const response = await routeService.optimizeRoute({
        date: selectedDate.format('YYYY-MM-DD'),
        driverId: selectedDriver,
        orderIds: routeStops.map(s => s.orderId),
      });
      
      // Reorder stops based on optimization
      const optimizedStops = response.optimizedOrder.map((orderId: number, index: number) => {
        const stop = routeStops.find(s => s.orderId === orderId);
        return {
          ...stop,
          sequence: index + 1,
        };
      });
      
      setRouteStops(optimizedStops);
      setRouteStats({
        totalDistance: response.totalDistance,
        totalDuration: response.totalDuration,
        totalStops: optimizedStops.length,
        totalWeight: response.totalWeight,
      });
      
      message.success(t('dispatch.route.optimizeSuccess'));
    } catch (error) {
      message.error(t('dispatch.route.optimizeError'));
    } finally {
      setIsOptimizing(false);
    }
  };

  // Save route
  const handleSaveRoute = async () => {
    if (!selectedDriver) {
      message.warning(t('dispatch.route.selectDriver'));
      return;
    }
    
    if (routeStops.length === 0) {
      message.warning(t('dispatch.route.noStops'));
      return;
    }
    
    Modal.confirm({
      title: t('dispatch.route.saveConfirm'),
      icon: <ExclamationCircleOutlined />,
      content: t('dispatch.route.saveConfirmContent'),
      onOk: async () => {
        setIsSaving(true);
        try {
          await routeService.createRoutePlan({
            routeDate: selectedDate.format('YYYY-MM-DD'),
            driverId: selectedDriver,
            stops: routeStops,
            totalDistance: routeStats.totalDistance,
            totalDuration: routeStats.totalDuration,
          });
          
          message.success(t('dispatch.route.saveSuccess'));
          
          // Reset form
          setRouteStops([]);
          setSelectedOrders([]);
          setSelectedDriver(undefined);
          setRouteStats({
            totalDistance: 0,
            totalDuration: 0,
            totalStops: 0,
            totalWeight: 0,
          });
          
          // Refresh available orders
          fetchAvailableOrders();
        } catch (error) {
          message.error(t('dispatch.route.saveError'));
        } finally {
          setIsSaving(false);
        }
      },
    });
  };

  // Available orders table columns
  const availableOrdersColumns: ColumnsType<Order> = [
    {
      title: t('dispatch.route.orderNumber'),
      dataIndex: 'orderNumber',
      key: 'orderNumber',
      width: 120,
    },
    {
      title: t('dispatch.route.customer'),
      dataIndex: 'customerName',
      key: 'customerName',
      ellipsis: true,
    },
    {
      title: t('dispatch.route.area'),
      dataIndex: 'area',
      key: 'area',
      width: 100,
      render: (area: string) => <Tag>{area}</Tag>,
    },
    {
      title: t('dispatch.route.products'),
      dataIndex: 'products',
      key: 'products',
      ellipsis: true,
    },
    {
      title: t('dispatch.route.amount'),
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      width: 100,
      align: 'right',
      render: (amount: number) => `$${amount.toLocaleString()}`,
    },
    {
      title: t('dispatch.route.status'),
      key: 'status',
      width: 80,
      render: (_, record) => (
        record.isUrgent ? (
          <Tag color="red">{t('dispatch.route.urgent')}</Tag>
        ) : null
      ),
    },
  ];

  // Route stops table columns
  const routeStopsColumns: ColumnsType<RouteStop> = [
    {
      title: t('dispatch.route.sequence'),
      dataIndex: 'sequence',
      key: 'sequence',
      width: 80,
      align: 'center',
    },
    {
      title: t('dispatch.route.orderNumber'),
      dataIndex: 'orderNumber',
      key: 'orderNumber',
      width: 120,
    },
    {
      title: t('dispatch.route.customer'),
      dataIndex: 'customerName',
      key: 'customerName',
      ellipsis: true,
    },
    {
      title: t('dispatch.route.products'),
      dataIndex: 'products',
      key: 'products',
      ellipsis: true,
    },
    {
      title: t('dispatch.route.actions'),
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          danger
          size="small"
          icon={<DeleteOutlined />}
          onClick={() => removeStopFromRoute(record.id)}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* Header Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={6}>
            <DatePicker
              value={selectedDate}
              onChange={(date) => setSelectedDate(date || dayjs())}
              style={{ width: '100%' }}
              format="YYYY-MM-DD"
            />
          </Col>
          <Col span={6}>
            <Select
              value={selectedArea}
              onChange={setSelectedArea}
              style={{ width: '100%' }}
              placeholder={t('dispatch.route.selectArea')}
            >
              <Select.Option value="all">{t('dispatch.route.allAreas')}</Select.Option>
              <Select.Option value="信義區">信義區</Select.Option>
              <Select.Option value="大安區">大安區</Select.Option>
              <Select.Option value="中山區">中山區</Select.Option>
              <Select.Option value="松山區">松山區</Select.Option>
              <Select.Option value="內湖區">內湖區</Select.Option>
            </Select>
          </Col>
          <Col span={6}>
            <Select
              value={selectedDriver}
              onChange={setSelectedDriver}
              style={{ width: '100%' }}
              placeholder={t('dispatch.route.selectDriver')}
              allowClear
            >
              {drivers.map(driver => (
                <Select.Option key={driver.id} value={driver.id}>
                  {driver.fullName} {driver.vehicleNumber && `(${driver.vehicleNumber})`}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col span={6}>
            <Space style={{ float: 'right' }}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSaveRoute}
                loading={isSaving}
                disabled={routeStops.length === 0 || !selectedDriver}
              >
                {t('dispatch.route.save')}
              </Button>
              <Button
                icon={<SendOutlined />}
                disabled={routeStops.length === 0 || !selectedDriver}
              >
                {t('dispatch.route.assign')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        {/* Left Panel - Available Orders */}
        <Col span={8}>
          <Card
            title={t('dispatch.route.availableOrders')}
            extra={
              <span style={{ fontSize: '14px', color: '#666' }}>
                {availableOrders.length} {t('dispatch.route.orders')}
              </span>
            }
            style={{ height: 'calc(100vh - 250px)' }}
            bodyStyle={{ padding: 0, height: 'calc(100% - 57px)', overflow: 'auto' }}
          >
            <Table
              columns={availableOrdersColumns}
              dataSource={availableOrders.filter(o => !selectedOrders.find(so => so.id === o.id))}
              rowKey="id"
              size="small"
              loading={isLoading}
              pagination={false}
              rowSelection={{
                type: 'checkbox',
                onChange: (_, selectedRows) => {
                  addOrdersToRoute(selectedRows);
                },
              }}
            />
          </Card>
        </Col>

        {/* Middle Panel - Route Map */}
        <Col span={10}>
          <RoutePlanningMap
            stops={routeStops}
            height="calc(100vh - 250px)"
            showOptimizeButton
            isOptimizing={isOptimizing}
            onOptimizeRoute={handleOptimizeRoute}
            onStopsReordered={setRouteStops}
          />
        </Col>

        {/* Right Panel - Route Details */}
        <Col span={6}>
          <Card
            title={t('dispatch.route.routeDetails')}
            style={{ height: 'calc(100vh - 250px)' }}
            bodyStyle={{ height: 'calc(100% - 57px)', overflow: 'auto' }}
          >
            {/* Route Statistics */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Statistic
                  title={t('dispatch.route.totalDistance')}
                  value={routeStats.totalDistance}
                  suffix="km"
                  prefix={<EnvironmentOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('dispatch.route.totalDuration')}
                  value={Math.round(routeStats.totalDuration / 60)}
                  suffix={t('dispatch.route.hours')}
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Statistic
                  title={t('dispatch.route.totalStops')}
                  value={routeStats.totalStops}
                  prefix={<CarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('dispatch.route.totalWeight')}
                  value={routeStats.totalWeight}
                  suffix="kg"
                />
              </Col>
            </Row>

            <Divider />

            {/* Route Stops List */}
            <h4>{t('dispatch.route.stops')}</h4>
            {routeStops.length === 0 ? (
              <Alert
                message={t('dispatch.route.noStopsAdded')}
                description={t('dispatch.route.addStopsHint')}
                type="info"
                showIcon
              />
            ) : (
              <Table
                columns={routeStopsColumns}
                dataSource={routeStops}
                rowKey="id"
                size="small"
                pagination={false}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RoutePlanning;