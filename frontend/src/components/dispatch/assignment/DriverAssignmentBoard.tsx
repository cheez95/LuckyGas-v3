import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Space,
  Typography,
  DatePicker,
  Select,
  Button,
  message,
  Spin,
  Badge,
  Alert,
  Divider,
} from 'antd';
import {
  ReloadOutlined,
  SaveOutlined,
  TeamOutlined,
  CarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useTranslation } from 'react-i18next';
import dayjs, { Dayjs } from 'dayjs';
import DriverCard, { DriverData } from './DriverCard';
import RouteColumn, { RouteData } from './RouteColumn';
import { driverService } from '../../../services/driver.service';
import { routeService } from '../../../services/route.service';

const { Title, Text } = Typography;

interface DriverAssignmentBoardProps {
  selectedDate?: Dayjs;
  onDateChange?: (date: Dayjs) => void;
}

const DriverAssignmentBoard: React.FC<DriverAssignmentBoardProps> = ({
  selectedDate = dayjs(),
  onDateChange,
}) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedArea, setSelectedArea] = useState<string>('all');
  const [availableDrivers, setAvailableDrivers] = useState<DriverData[]>([]);
  const [routes, setRoutes] = useState<RouteData[]>([]);
  const [activeDriver, setActiveDriver] = useState<DriverData | null>(null);
  const [assignments, setAssignments] = useState<Map<number, number>>(new Map());
  const [unsavedChanges, setUnsavedChanges] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Fetch data
  const fetchData = async () => {
    setIsLoading(true);
    try {
      // Fetch available drivers
      const driversResponse = await driverService.getAvailableDrivers(
        selectedDate.format('YYYY-MM-DD')
      );

      // Fetch routes for the date
      const routesResponse = await routeService.searchRoutePlans({
        dateFrom: selectedDate.format('YYYY-MM-DD'),
        dateTo: selectedDate.format('YYYY-MM-DD'),
        area: selectedArea !== 'all' ? selectedArea : undefined,
      });

      // Process drivers data
      const driversData: DriverData[] = driversResponse.map((driver: any) => ({
        id: driver.id,
        fullName: driver.fullName,
        username: driver.username,
        vehicleNumber: driver.vehicleNumber,
        vehicleType: driver.vehicleType,
        phoneNumber: driver.phoneNumber,
        isAvailable: driver.isAvailable,
        assignedRoutes: 0, // Will be calculated
        todayDeliveries: 0, // Will be calculated
        currentLocation: driver.currentLocation,
      }));

      // Process routes data and existing assignments
      const routesData: RouteData[] = routesResponse.routes.map((route: any) => {
        const routeData: RouteData = {
          id: route.id,
          routeNumber: route.routeNumber,
          routeDate: route.routeDate,
          totalStops: route.totalStops,
          totalDistance: route.totalDistance,
          totalDuration: route.totalDuration,
          estimatedWeight: route.totalWeight || 0,
          hasUrgentOrders: route.hasUrgentOrders || false,
          area: route.area || 'Unknown',
          startTime: route.startTime,
          status: route.status || 'unassigned',
          assignedDriver: undefined,
        };

        // If route has assigned driver, find and attach driver data
        if (route.driverId) {
          const assignedDriver = driversData.find(d => d.id === route.driverId);
          if (assignedDriver) {
            routeData.assignedDriver = assignedDriver;
            routeData.status = 'assigned';
            assignedDriver.assignedRoutes = (assignedDriver.assignedRoutes || 0) + 1;
          }
        }

        return routeData;
      });

      // Filter out drivers that are already assigned to routes
      const assignedDriverIds = new Set(
        routesData
          .filter(r => r.assignedDriver)
          .map(r => r.assignedDriver!.id)
      );

      const unassignedDrivers = driversData.filter(
        driver => !assignedDriverIds.has(driver.id)
      );

      setAvailableDrivers(unassignedDrivers);
      setRoutes(routesData);
      setUnsavedChanges(false);
    } catch (error) {
      message.error(t('dispatch.assignment.fetchError'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedDate, selectedArea]);

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const driver = availableDrivers.find(d => d.id === active.id);
    if (driver) {
      setActiveDriver(driver);
    }
  };

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveDriver(null);

    if (!over) return;

    const driverId = active.id as number;
    const routeId = parseInt(over.id.toString().replace('route-', ''));

    // Find the driver and route
    const driver = availableDrivers.find(d => d.id === driverId);
    const routeIndex = routes.findIndex(r => r.id === routeId);

    if (!driver || routeIndex === -1) return;

    // Check if route already has a driver
    if (routes[routeIndex].assignedDriver) {
      message.warning(t('dispatch.assignment.routeAlreadyAssigned'));
      return;
    }

    // Update the assignment
    const updatedRoutes = [...routes];
    updatedRoutes[routeIndex] = {
      ...updatedRoutes[routeIndex],
      assignedDriver: driver,
      status: 'assigned',
    };

    // Remove driver from available list
    setAvailableDrivers(availableDrivers.filter(d => d.id !== driverId));
    setRoutes(updatedRoutes);
    setAssignments(new Map(assignments).set(routeId, driverId));
    setUnsavedChanges(true);

    message.success(
      t('dispatch.assignment.driverAssigned', {
        driver: driver.fullName,
        route: updatedRoutes[routeIndex].routeNumber,
      })
    );
  };

  // Handle unassigning a driver
  const handleUnassign = (routeId: number) => {
    const routeIndex = routes.findIndex(r => r.id === routeId);
    if (routeIndex === -1 || !routes[routeIndex].assignedDriver) return;

    const driver = routes[routeIndex].assignedDriver!;
    const updatedRoutes = [...routes];
    updatedRoutes[routeIndex] = {
      ...updatedRoutes[routeIndex],
      assignedDriver: undefined,
      status: 'unassigned',
    };

    // Add driver back to available list
    setAvailableDrivers([...availableDrivers, driver]);
    setRoutes(updatedRoutes);
    const newAssignments = new Map(assignments);
    newAssignments.delete(routeId);
    setAssignments(newAssignments);
    setUnsavedChanges(true);

    message.info(
      t('dispatch.assignment.driverUnassigned', {
        driver: driver.fullName,
        route: routes[routeIndex].routeNumber,
      })
    );
  };

  // Save assignments
  const handleSaveAssignments = async () => {
    if (assignments.size === 0) {
      message.warning(t('dispatch.assignment.noAssignments'));
      return;
    }

    setIsSaving(true);
    try {
      const assignmentData = Array.from(assignments.entries()).map(([routeId, driverId]) => ({
        routeId,
        driverId,
      }));

      await routeService.bulkAssignRoutes(assignmentData);
      message.success(t('dispatch.assignment.saveSuccess'));
      setAssignments(new Map());
      setUnsavedChanges(false);
      // Refresh data
      fetchData();
    } catch (error) {
      message.error(t('dispatch.assignment.saveError'));
    } finally {
      setIsSaving(false);
    }
  };

  // Calculate statistics
  const stats = {
    totalRoutes: routes.length,
    assignedRoutes: routes.filter(r => r.assignedDriver).length,
    unassignedRoutes: routes.filter(r => !r.assignedDriver).length,
    availableDrivers: availableDrivers.length,
    totalStops: routes.reduce((sum, r) => sum + r.totalStops, 0),
    totalDistance: routes.reduce((sum, r) => sum + r.totalDistance, 0),
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={12}>
            <Title level={4} style={{ margin: 0 }}>
              {t('dispatch.assignment.title')}
            </Title>
          </Col>
          <Col span={12}>
            <Space style={{ float: 'right' }}>
              <DatePicker
                value={selectedDate}
                onChange={(date) => onDateChange?.(date || dayjs())}
                format="YYYY-MM-DD"
              />
              <Select
                value={selectedArea}
                onChange={setSelectedArea}
                style={{ width: 150 }}
              >
                <Select.Option value="all">{t('dispatch.route.allAreas')}</Select.Option>
                <Select.Option value="信義區">信義區</Select.Option>
                <Select.Option value="大安區">大安區</Select.Option>
                <Select.Option value="中山區">中山區</Select.Option>
                <Select.Option value="松山區">松山區</Select.Option>
                <Select.Option value="內湖區">內湖區</Select.Option>
              </Select>
              <Button icon={<ReloadOutlined />} onClick={fetchData}>
                {t('common.action.refresh')}
              </Button>
              {unsavedChanges && (
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSaveAssignments}
                  loading={isSaving}
                >
                  {t('common.action.save')}
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Statistics */}
      <Card style={{ marginBottom: 16 }}>
        <Space split={<Divider type="vertical" />}>
          <Badge
            count={stats.totalRoutes}
            showZero
            color="blue"
            overflowCount={999}
          >
            <Space>
              <CarOutlined style={{ fontSize: 20, color: '#1890ff' }} />
              <Text>{t('dispatch.assignment.totalRoutes')}</Text>
            </Space>
          </Badge>
          <Badge
            count={stats.assignedRoutes}
            showZero
            color="green"
            overflowCount={999}
          >
            <Space>
              <CheckCircleOutlined style={{ fontSize: 20, color: '#52c41a' }} />
              <Text>{t('dispatch.assignment.assignedRoutes')}</Text>
            </Space>
          </Badge>
          <Badge
            count={stats.unassignedRoutes}
            showZero
            color="red"
            overflowCount={999}
          >
            <Space>
              <ClockCircleOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />
              <Text>{t('dispatch.assignment.unassignedRoutes')}</Text>
            </Space>
          </Badge>
          <Badge
            count={stats.availableDrivers}
            showZero
            color="cyan"
            overflowCount={999}
          >
            <Space>
              <TeamOutlined style={{ fontSize: 20, color: '#13c2c2' }} />
              <Text>{t('dispatch.assignment.availableDrivers')}</Text>
            </Space>
          </Badge>
        </Space>
      </Card>

      {unsavedChanges && (
        <Alert
          message={t('dispatch.assignment.unsavedChanges')}
          description={t('dispatch.assignment.unsavedChangesDesc')}
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      <Spin spinning={isLoading}>
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <Row gutter={16}>
            {/* Available Drivers */}
            <Col span={6}>
              <Card
                title={
                  <Space>
                    <TeamOutlined />
                    <span>{t('dispatch.assignment.availableDrivers')}</span>
                  </Space>
                }
                style={{ height: 'calc(100vh - 400px)' }}
                bodyStyle={{ height: 'calc(100% - 57px)', overflow: 'auto' }}
              >
                <SortableContext
                  items={availableDrivers.map(d => d.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {availableDrivers.length === 0 ? (
                    <Alert
                      message={t('dispatch.assignment.noAvailableDrivers')}
                      description={t('dispatch.assignment.allDriversAssigned')}
                      type="info"
                      showIcon
                    />
                  ) : (
                    availableDrivers.map(driver => (
                      <DriverCard key={driver.id} driver={driver} />
                    ))
                  )}
                </SortableContext>
              </Card>
            </Col>

            {/* Routes */}
            <Col span={18}>
              <Card
                title={
                  <Space>
                    <CarOutlined />
                    <span>{t('dispatch.assignment.routes')}</span>
                  </Space>
                }
                style={{ height: 'calc(100vh - 400px)' }}
                bodyStyle={{
                  height: 'calc(100% - 57px)',
                  overflow: 'auto',
                  padding: '16px',
                }}
              >
                {routes.length === 0 ? (
                  <Alert
                    message={t('dispatch.assignment.noRoutes')}
                    description={t('dispatch.assignment.createRoutesFirst')}
                    type="info"
                    showIcon
                  />
                ) : (
                  <Row gutter={[16, 16]}>
                    {routes.map(route => (
                      <Col key={route.id} span={8}>
                        <RouteColumn
                          route={route}
                          onUnassign={handleUnassign}
                          isHighlighted={assignments.has(route.id)}
                        />
                      </Col>
                    ))}
                  </Row>
                )}
              </Card>
            </Col>
          </Row>

          <DragOverlay>
            {activeDriver ? <DriverCard driver={activeDriver} isDragging /> : null}
          </DragOverlay>
        </DndContext>
      </Spin>
    </div>
  );
};

export default DriverAssignmentBoard;