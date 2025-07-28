import React from 'react';
import { Card, Tag, Space, Typography, Badge, Divider, Empty, Button } from 'antd';
import {
  EnvironmentOutlined,
  ClockCircleOutlined,
  ShoppingCartOutlined,
  ExclamationCircleOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useTranslation } from 'react-i18next';
import DriverCard, { DriverData } from './DriverCard';

const { Text, Title } = Typography;

export interface RouteData {
  id: number;
  routeNumber: string;
  routeDate: string;
  totalStops: number;
  totalDistance: number;
  totalDuration: number;
  estimatedWeight: number;
  hasUrgentOrders: boolean;
  area: string;
  startTime?: string;
  assignedDriver?: DriverData;
  status: 'unassigned' | 'assigned' | 'in_progress' | 'completed';
}

interface RouteColumnProps {
  route: RouteData;
  onAssign?: (routeId: number, driverId: number) => void;
  onUnassign?: (routeId: number) => void;
  isHighlighted?: boolean;
}

const RouteColumn: React.FC<RouteColumnProps> = ({
  route,
  onUnassign,
  isHighlighted,
}) => {
  const { t } = useTranslation();
  const { setNodeRef, isOver } = useDroppable({
    id: `route-${route.id}`,
  });

  const getStatusColor = () => {
    switch (route.status) {
      case 'unassigned':
        return '#ff4d4f';
      case 'assigned':
        return '#1890ff';
      case 'in_progress':
        return '#52c41a';
      case 'completed':
        return '#8c8c8c';
      default:
        return '#d9d9d9';
    }
  };

  const getStatusText = () => {
    switch (route.status) {
      case 'unassigned':
        return t('dispatch.route.unassigned');
      case 'assigned':
        return t('dispatch.route.assigned');
      case 'in_progress':
        return t('dispatch.route.inProgress');
      case 'completed':
        return t('dispatch.route.completed');
      default:
        return route.status;
    }
  };

  return (
    <Card
      ref={setNodeRef}
      title={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Title level={5} style={{ margin: 0 }}>
              {route.routeNumber}
            </Title>
            <Tag color={route.area === '信義區' ? 'blue' : route.area === '大安區' ? 'green' : 'orange'}>
              {route.area}
            </Tag>
            {route.hasUrgentOrders && (
              <Tag color="red" icon={<ExclamationCircleOutlined />}>
                {t('dispatch.route.urgent')}
              </Tag>
            )}
          </Space>
          <Badge
            status={route.status === 'unassigned' ? 'error' : route.status === 'in_progress' ? 'processing' : 'default'}
            text={getStatusText()}
          />
        </Space>
      }
      style={{
        marginBottom: 16,
        border: isOver ? '2px dashed #1890ff' : isHighlighted ? '2px solid #1890ff' : '1px solid #e8e8e8',
        backgroundColor: isOver ? '#f0f8ff' : '#ffffff',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Route Statistics */}
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <Space split={<Divider type="vertical" />}>
          <Space size="small">
            <ShoppingCartOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">{route.totalStops} {t('dispatch.route.stops')}</Text>
          </Space>
          <Space size="small">
            <EnvironmentOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">{route.totalDistance} km</Text>
          </Space>
          <Space size="small">
            <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">{Math.round(route.totalDuration / 60)} {t('dispatch.route.hours')}</Text>
          </Space>
        </Space>

        <Text type="secondary" style={{ fontSize: 12 }}>
          {t('dispatch.route.estimatedWeight')}: {route.estimatedWeight} kg
        </Text>

        {route.startTime && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('dispatch.route.plannedStart')}: {route.startTime}
          </Text>
        )}

        <Divider style={{ margin: '12px 0' }} />

        {/* Assigned Driver Section */}
        <div style={{ minHeight: 100 }}>
          {route.assignedDriver ? (
            <SortableContext
              items={[route.assignedDriver.id]}
              strategy={verticalListSortingStrategy}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text strong>{t('dispatch.route.assignedDriver')}</Text>
                  {onUnassign && route.status === 'assigned' && (
                    <Button
                      type="link"
                      size="small"
                      danger
                      onClick={() => onUnassign(route.id)}
                    >
                      {t('dispatch.route.removeDriver')}
                    </Button>
                  )}
                </Space>
                <DriverCard driver={route.assignedDriver} />
              </Space>
            </SortableContext>
          ) : (
            <Empty
              image={<UserOutlined style={{ fontSize: 32, color: '#d9d9d9' }} />}
              imageStyle={{ height: 40 }}
              description={
                <Space direction="vertical" size="small">
                  <Text type="secondary">{t('dispatch.route.noDriverAssigned')}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {t('dispatch.route.dragDriverHere')}
                  </Text>
                </Space>
              }
            />
          )}
        </div>
      </Space>
    </Card>
  );
};

export default RouteColumn;
