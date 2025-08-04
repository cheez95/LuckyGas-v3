import React, { useState } from 'react';
import { 
  Card, 
  Button, 
  Timeline, 
  Tag, 
  Space, 
  Divider, 
  Progress,
  Typography,
  Tooltip,
  Badge,
  Empty,
} from 'antd';
import {
  CloseOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CarOutlined,
  PhoneOutlined,
  ExclamationCircleOutlined,
  RightOutlined,
  LeftOutlined,
} from '@ant-design/icons';
import type { Route, RouteStop } from '../../types/maps.types';

const { Text, Title } = Typography;

interface RouteInfoPanelProps {
  route: Route;
  selectedStop: RouteStop | null;
  onClose: () => void;
  onStopClick: (stop: RouteStop) => void;
  onUpdate?: (routeId: string, updates: Partial<Route>) => void;
}

const RouteInfoPanel: React.FC<RouteInfoPanelProps> = ({
  route,
  selectedStop,
  onClose,
  onStopClick,
  onUpdate,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  // Calculate progress
  const completedStops = route.stops.filter(s => s.status === 'completed').length;
  const progress = Math.round((completedStops / route.stops.length) * 100);
  
  // Calculate total packages
  const totalPackages = route.stops.reduce((sum, stop) => 
    sum + stop.packages.reduce((pkgSum, pkg) => pkgSum + pkg.quantity, 0), 0
  );
  
  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };
  
  return (
    <Card 
      className={`route-info-panel ${isCollapsed ? 'collapsed' : ''}`}
      size="small"
      title={
        <div className="route-info-header">
          <Space>
            <CarOutlined />
            <Text strong>{route.driverName}</Text>
          </Space>
          <Space>
            <Button
              type="text"
              icon={isCollapsed ? <LeftOutlined /> : <RightOutlined />}
              size="small"
              onClick={handleToggleCollapse}
            />
            <Button
              type="text"
              icon={<CloseOutlined />}
              size="small"
              onClick={onClose}
            />
          </Space>
        </div>
      }
    >
      {!isCollapsed && (
        <div className="route-info-content">
          {/* Route Statistics */}
          <div className="route-info-stats">
            <div className="route-info-stat">
              <Text type="secondary">總距離</Text>
              <div className="route-info-stat-value">{route.totalDistance.toFixed(1)} km</div>
            </div>
            <div className="route-info-stat">
              <Text type="secondary">配送點</Text>
              <div className="route-info-stat-value">{completedStops}/{route.stops.length}</div>
            </div>
            <div className="route-info-stat">
              <Text type="secondary">包裹數</Text>
              <div className="route-info-stat-value">{totalPackages}</div>
            </div>
            <div className="route-info-stat">
              <Text type="secondary">預計時間</Text>
              <div className="route-info-stat-value">{route.totalDuration} 分鐘</div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <Progress 
            percent={progress} 
            status={route.status === 'completed' ? 'success' : 'active'}
            strokeColor={getProgressColor(route.status)}
          />
          
          <Divider style={{ margin: '16px 0' }} />
          
          {/* Status and Time */}
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">狀態</Text>
              <Tag color={getStatusColor(route.status)}>
                {getStatusText(route.status)}
              </Tag>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">開始時間</Text>
              <Text>{formatTime(route.startTime)}</Text>
            </div>
            {route.endTime && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary">結束時間</Text>
                <Text>{formatTime(route.endTime)}</Text>
              </div>
            )}
          </Space>
          
          <Divider style={{ margin: '16px 0' }} />
          
          {/* Stops Timeline */}
          <div style={{ marginBottom: 8 }}>
            <Text strong>配送路線</Text>
          </div>
          
          {route.stops.length > 0 ? (
            <Timeline mode="left">
              {route.stops.map((stop, index) => (
                <Timeline.Item
                  key={stop.id}
                  color={getStopTimelineColor(stop)}
                  dot={getStopTimelineDot(stop)}
                >
                  <div 
                    className={`stop-item ${selectedStop?.id === stop.id ? 'selected' : ''} ${stop.status}`}
                    onClick={() => onStopClick(stop)}
                  >
                    <div className="stop-item-header">
                      <Space>
                        <span className="stop-item-sequence">{stop.sequence}</span>
                        <Text strong>{stop.customerName}</Text>
                      </Space>
                      {stop.priority === 'urgent' && (
                        <Tag color="red" icon={<ExclamationCircleOutlined />}>
                          緊急
                        </Tag>
                      )}
                    </div>
                    
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {stop.address}
                    </Text>
                    
                    <div className="stop-item-packages">
                      {stop.packages.map((pkg, idx) => (
                        <Tag key={idx} style={{ marginTop: 4 }}>
                          {pkg.quantity}x {pkg.cylinderType}
                        </Tag>
                      ))}
                    </div>
                    
                    <div className="stop-item-status">
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {stop.actualArrival 
                        ? `到達: ${formatTime(stop.actualArrival)}`
                        : `預計: ${formatTime(stop.estimatedArrival)}`
                      }
                    </div>
                    
                    {stop.notes && (
                      <div style={{ marginTop: 8 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          備註: {stop.notes}
                        </Text>
                      </div>
                    )}
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          ) : (
            <Empty description="無配送點" />
          )}
          
          {/* Contact Driver */}
          {route.driverName && (
            <>
              <Divider style={{ margin: '16px 0' }} />
              <Button 
                icon={<PhoneOutlined />} 
                block
                onClick={() => {
                  // In real app, this would make a call
                  console.log('Calling driver:', route.driverId);
                }}
              >
                聯絡司機
              </Button>
            </>
          )}
        </div>
      )}
    </Card>
  );
};

function getProgressColor(status: Route['status']): string {
  const colors = {
    'not-started': '#1890ff',
    'in-progress': '#1890ff',
    'completed': '#52c41a',
    'delayed': '#f5222d',
  };
  return colors[status] || '#1890ff';
}

function getStatusColor(status: Route['status']): string {
  const colors = {
    'not-started': 'blue',
    'in-progress': 'processing',
    'completed': 'success',
    'delayed': 'error',
  };
  return colors[status] || 'default';
}

function getStatusText(status: Route['status']): string {
  const texts = {
    'not-started': '未開始',
    'in-progress': '配送中',
    'completed': '已完成',
    'delayed': '延誤',
  };
  return texts[status] || status;
}

function getStopTimelineColor(stop: RouteStop): string {
  if (stop.status === 'completed') return 'green';
  if (stop.status === 'in-progress') return 'blue';
  if (stop.status === 'skipped') return 'red';
  
  // Check if delayed
  const now = new Date();
  if (stop.estimatedArrival < now && stop.status === 'pending') {
    return 'red';
  }
  
  return 'gray';
}

function getStopTimelineDot(stop: RouteStop): React.ReactNode {
  if (stop.status === 'completed') {
    return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
  }
  if (stop.status === 'in-progress') {
    return <CarOutlined style={{ color: '#1890ff' }} />;
  }
  if (stop.priority === 'urgent') {
    return <ExclamationCircleOutlined style={{ color: '#f5222d' }} />;
  }
  return <EnvironmentOutlined />;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default RouteInfoPanel;