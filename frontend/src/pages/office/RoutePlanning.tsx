import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Button, Space, Select, DatePicker, Row, Col, List, Tag, Statistic, message, Spin, Badge, Tooltip, Modal, Form, Input, Drawer, Timeline, Transfer, Progress } from 'antd';
import { EnvironmentOutlined, CarOutlined, ClockCircleOutlined, UserOutlined, ReloadOutlined, SendOutlined, DragOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import { apiWithCancel, requestManager } from '../../services/api.service';
import dayjs from 'dayjs';
import GoogleMapsPlaceholder, { MapMarker } from '../../components/common/GoogleMapsPlaceholder';
import { useRealtimeUpdates } from '../../hooks/useRealtimeUpdates';
import { useWebSocketContext } from '../../contexts/WebSocketContext';

interface Driver {
  id: string;
  name: string;
  phone: string;
  vehicleType: string;
  vehicleNumber: string;
  status: 'available' | 'on_route' | 'offline';
  currentLocation?: {
    latitude: number;
    longitude: number;
  };
  maxCapacity: number;
  currentLoad: number;
}

interface RouteStop {
  id: string;
  orderId: string;
  orderNumber: string;
  customerName: string;
  customerPhone: string;
  address: string;
  cylinderType: string;
  quantity: number;
  priority: 'normal' | 'urgent';
  estimatedTime?: string;
  distance?: number;
  sequence: number;
  status: 'pending' | 'completed' | 'skipped';
  deliveryNotes?: string;
}

interface Route {
  id: string;
  routeNumber: string;
  driverId: string;
  driverName: string;
  date: string;
  status: 'draft' | 'assigned' | 'in_progress' | 'completed';
  stops: RouteStop[];
  totalDistance: number;
  estimatedDuration: number;
  startTime?: string;
  endTime?: string;
  optimizationScore: number;
}

const RoutePlanning: React.FC = () => {
  const { t } = useTranslation();
  const mapRef = useRef<HTMLDivElement>(null);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [unassignedOrders, setUnassignedOrders] = useState<RouteStop[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [isAssignDriverModalVisible, setIsAssignDriverModalVisible] = useState(false);
  const [isRouteDetailDrawerVisible, setIsRouteDetailDrawerVisible] = useState(false);
  const [form] = Form.useForm();
  
  // Real-time driver locations
  const [driverLocations, setDriverLocations] = useState<Map<string, { latitude: number; longitude: number }>>(new Map());
  
  // WebSocket context
  const { subscribeToDriverLocation, unsubscribeFromDriverLocation } = useWebSocketContext();

  // Statistics
  const [stats, setStats] = useState({
    totalOrders: 0,
    assignedOrders: 0,
    totalDistance: 0,
    averageStopsPerRoute: 0,
  });
  
  // Real-time WebSocket updates
  useRealtimeUpdates({
    onDriverLocation: (location) => {
      // Update driver location in the map
      setDriverLocations(prev => {
        const newLocations = new Map(prev);
        newLocations.set(location.driver_id, {
          latitude: location.latitude,
          longitude: location.longitude
        });
        return newLocations;
      });
      
      // Update driver status in drivers list
      setDrivers(prevDrivers => 
        (prevDrivers || []).map(driver => 
          driver.id === location.driver_id 
            ? { ...driver, currentLocation: { latitude: location.latitude, longitude: location.longitude } }
            : driver
        )
      );
    },
    onRouteUpdate: (updatedRoute) => {
      setRoutes(prevRoutes => {
        const index = prevRoutes.findIndex(r => r.id === updatedRoute.id);
        if (index >= 0) {
          const newRoutes = [...prevRoutes];
          newRoutes[index] = { ...newRoutes[index], ...updatedRoute };
          return newRoutes;
        }
        return prevRoutes;
      });
    },
    enableNotifications: true,
  });

  // UseRef to track if component is mounted
  const isMountedRef = useRef(true);
  
  useEffect(() => {
    // Set mounted flag
    isMountedRef.current = true;
    
    // Cleanup function to cancel requests and set unmounted flag
    return () => {
      isMountedRef.current = false;
      // Cancel all pending requests for this component
      requestManager.cancel('route-planning-drivers');
      requestManager.cancel('route-planning-routes');
      requestManager.cancel('route-planning-orders');
    };
  }, []);
  
  useEffect(() => {
    fetchData();
    // Cleanup function to cancel requests when date changes
    return () => {
      requestManager.cancel('route-planning-drivers');
      requestManager.cancel('route-planning-routes');
      requestManager.cancel('route-planning-orders');
    };
  }, [selectedDate]);
  
  // Subscribe to driver locations when drivers are loaded
  useEffect(() => {
    // Subscribe to all active drivers
    const activeDrivers = drivers.filter(d => d.status !== 'offline');
    
    activeDrivers.forEach(driver => {
      subscribeToDriverLocation(driver.id);
    });
    
    // Cleanup: unsubscribe when component unmounts or drivers change
    return () => {
      activeDrivers.forEach(driver => {
        unsubscribeFromDriverLocation(driver.id);
      });
    };
  }, [drivers, subscribeToDriverLocation, unsubscribeFromDriverLocation]);

  const fetchData = async () => {
    // Only proceed if component is mounted
    if (!isMountedRef.current) return;
    
    setLoading(true);
    try {
      const [driversRes, routesRes, ordersRes] = await Promise.all([
        apiWithCancel.get('/drivers', 'route-planning-drivers', { cache: true }),
        apiWithCancel.get(
          `/routes?date=${selectedDate.format('YYYY-MM-DD')}`, 
          'route-planning-routes',
          { cache: true, debounce: 500 }
        ),
        apiWithCancel.get(
          `/orders/unassigned?date=${selectedDate.format('YYYY-MM-DD')}`,
          'route-planning-orders',
          { cache: true, debounce: 500 }
        ),
      ]).catch(error => {
        // Handle cancellation errors silently
        if (error.message === 'Request cancelled') {
          return [];
        }
        throw error;
      });
      
      // Only update state if component is still mounted
      if (isMountedRef.current && driversRes && routesRes && ordersRes) {
        setDrivers(driversRes.data || []);
        setRoutes(routesRes.data || []);
        setUnassignedOrders(ordersRes.data || []);
        
        calculateStatistics(routesRes.data || [], ordersRes.data || []);
      }
    } catch (error: any) {
      // Only show error if component is mounted and it's not a cancellation
      if (isMountedRef.current && error.message !== 'Request cancelled') {
        message.error(t('routes.fetchError'));
        console.error('Failed to fetch route planning data:', error);
      }
    } finally {
      // Only update loading state if component is mounted
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  const calculateStatistics = (routes: Route[], unassigned: RouteStop[]) => {
    const totalAssigned = routes.reduce((acc, route) => acc + route.stops.length, 0);
    const totalDistance = routes.reduce((acc, route) => acc + route.totalDistance, 0);
    
    setStats({
      totalOrders: totalAssigned + unassigned.length,
      assignedOrders: totalAssigned,
      totalDistance,
      averageStopsPerRoute: routes.length > 0 ? Math.round(totalAssigned / routes.length) : 0,
    });
  };

  // Prepare map markers from drivers and route stops
  const prepareMapMarkers = (): MapMarker[] => {
    const markers: MapMarker[] = [];
    
    // Add driver markers
    drivers.forEach(driver => {
      if (driver.currentLocation) {
        markers.push({
          id: `driver-${driver.id}`,
          position: { 
            lat: driver.currentLocation.latitude, 
            lng: driver.currentLocation.longitude 
          },
          title: driver.name,
          type: 'driver',
          info: `${driver.vehicleNumber} - ${t(`drivers.status.${driver.status}`)}`
        });
      }
    });
    
    // Add route stop markers for selected route
    if (selectedRoute) {
      selectedRoute.stops.forEach(stop => {
        // For demo purposes, generate random coordinates near Taipei
        const baseLat = 25.0330;
        const baseLng = 121.5654;
        const offset = 0.05;
        
        markers.push({
          id: `stop-${stop.id}`,
          position: {
            lat: baseLat + (Math.random() - 0.5) * offset,
            lng: baseLng + (Math.random() - 0.5) * offset
          },
          title: stop.customerName,
          type: 'customer',
          info: `${stop.address} - ${stop.cylinderType} x${stop.quantity}`
        });
      });
    }
    
    // Add depot marker
    markers.push({
      id: 'depot-main',
      position: { lat: 25.0330, lng: 121.5654 },
      title: '幸福氣體總部',
      type: 'depot',
      info: 'Lucky Gas Headquarters'
    });
    
    return markers;
  };

  const handleOptimizeRoutes = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    setOptimizing(true);
    try {
      const response = await apiWithCancel.post(
        '/routes/optimize',
        {
          date: selectedDate.format('YYYY-MM-DD'),
          drivers: (drivers || []).filter(d => d.status === 'available').map(d => d.id),
        },
        'route-planning-optimize'
      );
      
      // Only update state if component is still mounted
      if (isMountedRef.current && response.data) {
        setRoutes(response.data.routes || []);
        setUnassignedOrders(response.data.unassigned || []);
        message.success(t('routes.optimizeSuccess'));
        
        calculateStatistics(response.data.routes || [], response.data.unassigned || []);
      }
    } catch (error: any) {
      // Only show error if component is mounted and it's not a cancellation
      if (isMountedRef.current && error.message !== 'Request cancelled') {
        message.error(t('routes.optimizeError'));
        console.error('Failed to optimize routes:', error);
      }
    } finally {
      // Only update optimizing state if component is mounted
      if (isMountedRef.current) {
        setOptimizing(false);
      }
    }
  }, [drivers, selectedDate, t]);

  const handleAssignToRoute = (routeId: string, orderIds: string[]) => {
    const ordersToAssign = unassignedOrders.filter(order => orderIds.includes(order.id));
    
    const updatedRoutes = routes.map(route => {
      if (route.id === routeId) {
        const newStops = [...route.stops, ...ordersToAssign.map((order, index) => ({
          ...order,
          sequence: route.stops.length + index + 1,
        }))];
        return { ...route, stops: newStops };
      }
      return route;
    });
    
    const updatedUnassigned = unassignedOrders.filter(order => !orderIds.includes(order.id));
    
    setRoutes(updatedRoutes);
    setUnassignedOrders(updatedUnassigned);
  };

  const handleRemoveFromRoute = (routeId: string, stopId: string) => {
    let removedStop: RouteStop | null = null;
    
    const updatedRoutes = routes.map(route => {
      if (route.id === routeId) {
        const stopIndex = route.stops.findIndex(stop => stop.id === stopId);
        if (stopIndex !== -1) {
          removedStop = route.stops[stopIndex];
          const newStops = route.stops.filter(stop => stop.id !== stopId);
          // Update sequences
          newStops.forEach((stop, index) => {
            stop.sequence = index + 1;
          });
          return { ...route, stops: newStops };
        }
      }
      return route;
    });
    
    if (removedStop) {
      setUnassignedOrders([...unassignedOrders, removedStop]);
    }
    
    setRoutes(updatedRoutes);
  };

  const handleAssignDriver = useCallback(async (values: any) => {
    if (!isMountedRef.current) return;
    
    try {
      const response = await apiWithCancel.post(
        '/routes',
        {
          driverId: values.driverId,
          date: selectedDate.format('YYYY-MM-DD'),
          routeNumber: values.routeNumber,
        },
        'route-planning-assign-driver'
      );
      
      // Only update state if component is still mounted
      if (isMountedRef.current && response.data) {
        setRoutes([...routes, response.data]);
        setIsAssignDriverModalVisible(false);
        form.resetFields();
        message.success(t('routes.createSuccess'));
      }
    } catch (error: any) {
      // Only show error if component is mounted and it's not a cancellation
      if (isMountedRef.current && error.message !== 'Request cancelled') {
        message.error(t('routes.createError'));
        console.error('Failed to assign driver:', error);
      }
    }
  }, [routes, selectedDate, form, t]);

  const handlePublishRoutes = useCallback(async () => {
    Modal.confirm({
      title: t('routes.publishConfirm'),
      content: t('routes.publishWarning'),
      onOk: async () => {
        if (!isMountedRef.current) return;
        
        try {
          await apiWithCancel.post(
            '/routes/publish',
            {
              date: selectedDate.format('YYYY-MM-DD'),
              routeIds: routes.map(r => r.id),
            },
            'route-planning-publish'
          );
          
          // Only update if component is still mounted
          if (isMountedRef.current) {
            message.success(t('routes.publishSuccess'));
            fetchData();
          }
        } catch (error: any) {
          // Only show error if component is mounted and it's not a cancellation
          if (isMountedRef.current && error.message !== 'Request cancelled') {
            message.error(t('routes.publishError'));
            console.error('Failed to publish routes:', error);
          }
        }
      },
    });
  }, [routes, selectedDate, t, fetchData]);

  const getDriverStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      available: 'green',
      on_route: 'blue',
      offline: 'default',
    };
    return colors[status] || 'default';
  };

  const renderRouteCard = (route: Route) => (
    <Card
      key={route.id}
      title={
        <Space>
          <CarOutlined />
          <span>{route.routeNumber}</span>
          <Tag color={route.status === 'in_progress' ? 'blue' : 'default'}>
            {route.driverName}
          </Tag>
        </Space>
      }
      extra={
        <Space>
          <Tooltip title={t('routes.viewDetail')}>
            <Button
              type="text"
              icon={<EnvironmentOutlined />}
              onClick={() => {
                setSelectedRoute(route);
                setIsRouteDetailDrawerVisible(true);
              }}
            />
          </Tooltip>
          <Badge count={route.stops.length} showZero />
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <Row gutter={[16, 8]} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Statistic
            title={t('routes.distance')}
            value={route.totalDistance}
            suffix="km"
            valueStyle={{ fontSize: '14px' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={t('routes.duration')}
            value={route.estimatedDuration}
            suffix={t('common.minutes')}
            valueStyle={{ fontSize: '14px' }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={t('routes.optimization')}
            value={route.optimizationScore}
            suffix="%"
            valueStyle={{ fontSize: '14px', color: route.optimizationScore > 80 ? '#3f8600' : '#faad14' }}
          />
        </Col>
      </Row>

      <List
        dataSource={route.stops}
        renderItem={(stop, index) => (
          <Card
            size="small"
            style={{ marginBottom: 8 }}
            bodyStyle={{ padding: 8 }}
          >
            <Row align="middle" gutter={8}>
              <Col span={2}>
                <Badge count={stop.sequence} style={{ backgroundColor: '#1890ff' }} />
              </Col>
              <Col span={14}>
                <Space direction="vertical" size={0}>
                  <span style={{ fontWeight: 500 }}>{stop.customerName}</span>
                  <span style={{ fontSize: '12px', color: '#999' }}>
                    {stop.address}
                  </span>
                </Space>
              </Col>
              <Col span={4}>
                <Tag>{stop.cylinderType} x{stop.quantity}</Tag>
              </Col>
              <Col span={4}>
                {stop.priority === 'urgent' && (
                  <Tag color="red">{t('orders.priority.urgent')}</Tag>
                )}
                {stop.estimatedTime && (
                  <span style={{ fontSize: '12px' }}>
                    {dayjs(stop.estimatedTime).format('HH:mm')}
                  </span>
                )}
              </Col>
            </Row>
          </Card>
        )}
      />
    </Card>
  );

  return (
    <div className="route-planning">
      <Card title={t('routes.title')}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('routes.stats.totalOrders')}
                value={stats.totalOrders}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('routes.stats.assigned')}
                value={`${stats.assignedOrders}/${stats.totalOrders}`}
                valueStyle={{ color: stats.assignedOrders === stats.totalOrders ? '#3f8600' : '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('routes.stats.totalDistance')}
                value={stats.totalDistance}
                suffix="km"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('routes.stats.avgStops')}
                value={stats.averageStopsPerRoute}
                prefix={<EnvironmentOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Space style={{ marginBottom: 16 }}>
          <DatePicker
            value={selectedDate}
            onChange={(date) => date && setSelectedDate(date)}
            style={{ width: 200 }}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchData}
            loading={loading}
          >
            {t('common.refresh')}
          </Button>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleOptimizeRoutes}
            loading={optimizing}
          >
            {t('routes.optimizeRoutes')}
          </Button>
          <Button
            icon={<UserOutlined />}
            onClick={() => setIsAssignDriverModalVisible(true)}
          >
            {t('routes.createRoute')}
          </Button>
          <Button
            type="primary"
            danger
            onClick={handlePublishRoutes}
            disabled={routes.length === 0}
          >
            {t('routes.publishRoutes')}
          </Button>
        </Space>

        <Row gutter={16}>
          <Col span={18}>
            <Row gutter={16}>
              <Col span={6}>
                <Card
                  title={
                    <Space>
                      <ExclamationCircleOutlined />
                      {t('routes.unassignedOrders')}
                      <Badge count={unassignedOrders.length} />
                    </Space>
                  }
                  bodyStyle={{ padding: 8 }}
                >
                  <List
                    dataSource={unassignedOrders}
                    renderItem={(order) => (
                      <Card
                        size="small"
                        style={{ marginBottom: 8 }}
                        bodyStyle={{ padding: 8 }}
                      >
                        <Space direction="vertical" size={0} style={{ width: '100%' }}>
                          <span style={{ fontWeight: 500 }}>{order.customerName}</span>
                          <span style={{ fontSize: '12px', color: '#999' }}>
                            {order.address}
                          </span>
                          <Space>
                            <Tag>{order.cylinderType} x{order.quantity}</Tag>
                            {order.priority === 'urgent' && (
                              <Tag color="red">{t('orders.priority.urgent')}</Tag>
                            )}
                          </Space>
                        </Space>
                      </Card>
                    )}
                  />
                </Card>
              </Col>

              <Col span={18}>
                <Spin spinning={loading}>
                  {routes.map(route => renderRouteCard(route))}
                </Spin>
              </Col>
            </Row>
          </Col>

          <Col span={6}>
            <Card title={
              <Space>
                {t('routes.availableDrivers')}
                <Badge 
                  status="processing" 
                  text={`${driverLocations.size} 追蹤中`}
                  style={{ fontSize: 12 }}
                />
              </Space>
            }>
              <List
                dataSource={drivers}
                renderItem={(driver) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Badge 
                          dot={!!driver.currentLocation} 
                          status={driver.currentLocation ? "success" : "default"}
                        >
                          <UserOutlined />
                        </Badge>
                      }
                      title={driver.name}
                      description={
                        <Space direction="vertical" size={0}>
                          <span>{driver.vehicleNumber}</span>
                          <Tag color={getDriverStatusColor(driver.status)}>
                            {t(`drivers.status.${driver.status}`)}
                          </Tag>
                          {driver.currentLocation && (
                            <span style={{ fontSize: 12, color: '#52c41a' }}>
                              <EnvironmentOutlined /> 定位中
                            </span>
                          )}
                        </Space>
                      }
                    />
                    <div>
                      <Progress
                        percent={(driver.currentLoad / driver.maxCapacity) * 100}
                        size="small"
                        format={() => `${driver.currentLoad}/${driver.maxCapacity}`}
                      />
                    </div>
                  </List.Item>
                )}
              />
            </Card>

            <Card title={t('routes.map')} style={{ marginTop: 16 }}>
              <GoogleMapsPlaceholder
                center={{ lat: 25.0330, lng: 121.5654 }}
                zoom={13}
                markers={prepareMapMarkers()}
                height={350}
                showControls={true}
                onMarkerClick={(marker) => {
                  if (marker.type === 'driver') {
                    message.info(`司機位置: ${marker.title}`);
                  } else if (marker.type === 'customer') {
                    message.info(`客戶: ${marker.title}`);
                  }
                }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      <Modal
        title={t('routes.createRoute')}
        open={isAssignDriverModalVisible}
        onCancel={() => setIsAssignDriverModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAssignDriver}
        >
          <Form.Item
            name="driverId"
            label={t('routes.selectDriver')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Select>
              {drivers
                .filter(d => d.status === 'available')
                .map(driver => (
                  <Select.Option key={driver.id} value={driver.id}>
                    {driver.name} - {driver.vehicleNumber}
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="routeNumber"
            label={t('routes.routeNumber')}
            rules={[{ required: true, message: t('validation.required') }]}
          >
            <Input placeholder={`R-${selectedDate.format('YYYYMMDD')}-01`} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {t('common.create')}
              </Button>
              <Button onClick={() => setIsAssignDriverModalVisible(false)}>
                {t('common.cancel')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={t('routes.routeDetail')}
        placement="right"
        width={600}
        open={isRouteDetailDrawerVisible}
        onClose={() => setIsRouteDetailDrawerVisible(false)}
      >
        {selectedRoute && (
          <>
            <Card title={t('routes.routeInfo')} style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <strong>{t('routes.routeNumber')}:</strong> {selectedRoute.routeNumber}
                </Col>
                <Col span={12}>
                  <strong>{t('routes.driver')}:</strong> {selectedRoute.driverName}
                </Col>
                <Col span={12}>
                  <strong>{t('routes.date')}:</strong> {dayjs(selectedRoute.date).format('YYYY/MM/DD')}
                </Col>
                <Col span={12}>
                  <strong>{t('routes.status')}:</strong>{' '}
                  <Tag>{t(`routes.status.${selectedRoute.status}`)}</Tag>
                </Col>
                <Col span={12}>
                  <strong>{t('routes.totalStops')}:</strong> {selectedRoute.stops.length}
                </Col>
                <Col span={12}>
                  <strong>{t('routes.totalDistance')}:</strong> {selectedRoute.totalDistance} km
                </Col>
              </Row>
            </Card>

            <Card title={t('routes.stops')}>
              <Timeline>
                {selectedRoute.stops
                  .sort((a, b) => a.sequence - b.sequence)
                  .map((stop, index) => (
                    <Timeline.Item
                      key={stop.id}
                      color={stop.status === 'completed' ? 'green' : 'blue'}
                      dot={stop.status === 'completed' ? <CheckCircleOutlined /> : undefined}
                    >
                      <Row gutter={[16, 8]}>
                        <Col span={24}>
                          <strong>{stop.customerName}</strong>
                        </Col>
                        <Col span={24}>
                          <span style={{ color: '#666' }}>{stop.address}</span>
                        </Col>
                        <Col span={12}>
                          <Tag>{stop.cylinderType} x{stop.quantity}</Tag>
                        </Col>
                        <Col span={12}>
                          {stop.estimatedTime && (
                            <><ClockCircleOutlined /> {dayjs(stop.estimatedTime).format('HH:mm')}</>
                          )}
                        </Col>
                        {stop.deliveryNotes && (
                          <Col span={24}>
                            <span style={{ fontSize: '12px', color: '#999' }}>
                              {t('common.notes')}: {stop.deliveryNotes}
                            </span>
                          </Col>
                        )}
                      </Row>
                    </Timeline.Item>
                  ))}
              </Timeline>
            </Card>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default RoutePlanning;