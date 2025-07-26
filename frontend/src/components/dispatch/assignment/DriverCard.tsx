import React from 'react';
import { Card, Avatar, Tag, Space, Typography, Badge } from 'antd';
import { UserOutlined, CarOutlined, PhoneOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { CSS } from '@dnd-kit/utilities';
import { useSortable } from '@dnd-kit/sortable';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

export interface DriverData {
  id: number;
  fullName: string;
  username: string;
  vehicleNumber?: string;
  vehicleType?: string;
  phoneNumber?: string;
  isAvailable: boolean;
  assignedRoutes?: number;
  todayDeliveries?: number;
  currentLocation?: {
    latitude: number;
    longitude: number;
    updatedAt: string;
  };
}

interface DriverCardProps {
  driver: DriverData;
  isDragging?: boolean;
}

const DriverCard: React.FC<DriverCardProps> = ({ driver, isDragging }) => {
  const { t } = useTranslation();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: driver.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    cursor: 'grab',
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        size="small"
        style={{
          marginBottom: 8,
          border: '1px solid #e8e8e8',
          borderRadius: 8,
          boxShadow: isDragging ? '0 4px 8px rgba(0,0,0,0.15)' : '0 1px 2px rgba(0,0,0,0.05)',
        }}
        hoverable
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {/* Driver Header */}
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space>
              <Avatar
                size="small"
                icon={<UserOutlined />}
                style={{ backgroundColor: driver.isAvailable ? '#52c41a' : '#d9d9d9' }}
              />
              <Text strong>{driver.fullName}</Text>
            </Space>
            {driver.isAvailable ? (
              <Tag color="green" icon={<CheckCircleOutlined />}>
                {t('dispatch.driver.available')}
              </Tag>
            ) : (
              <Tag color="default">
                {t('dispatch.driver.busy')}
              </Tag>
            )}
          </Space>

          {/* Vehicle Info */}
          {driver.vehicleNumber && (
            <Space size="small">
              <CarOutlined style={{ color: '#8c8c8c' }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {driver.vehicleNumber}
                {driver.vehicleType && ` (${driver.vehicleType})`}
              </Text>
            </Space>
          )}

          {/* Phone */}
          {driver.phoneNumber && (
            <Space size="small">
              <PhoneOutlined style={{ color: '#8c8c8c' }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {driver.phoneNumber}
              </Text>
            </Space>
          )}

          {/* Stats */}
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {t('dispatch.driver.assignedRoutes')}: {driver.assignedRoutes || 0}
            </Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {t('dispatch.driver.todayDeliveries')}: {driver.todayDeliveries || 0}
            </Text>
          </Space>

          {/* Current Location Status */}
          {driver.currentLocation && (
            <Badge
              status="processing"
              text={
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {t('dispatch.driver.locationUpdated')}: {new Date(driver.currentLocation.updatedAt).toLocaleTimeString('zh-TW')}
                </Text>
              }
            />
          )}
        </Space>
      </Card>
    </div>
  );
};

export default DriverCard;