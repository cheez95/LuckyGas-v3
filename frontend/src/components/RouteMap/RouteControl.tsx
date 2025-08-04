import React, { useState } from 'react';
import { 
  Card, 
  Button, 
  Select, 
  Badge, 
  Space, 
  Statistic, 
  Row, 
  Col,
  Divider,
  Switch,
  Tooltip,
  Drawer,
} from 'antd';
import {
  FilterOutlined,
  SyncOutlined,
  EnvironmentOutlined,
  UserOutlined,
  DashboardOutlined,
  CloseOutlined,
  RocketOutlined,
  CarOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type { Route, RouteFilter, RouteStats } from '../../types/maps.types';

const { Option } = Select;

interface RouteControlProps {
  routes: Route[];
  filter: RouteFilter;
  onFilterChange: (filter: RouteFilter) => void;
  onOptimize: () => void;
  onCenterDriver: (driverId: string) => void;
}

const RouteControl: React.FC<RouteControlProps> = ({
  routes,
  filter,
  onFilterChange,
  onOptimize,
  onCenterDriver,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  
  // Calculate statistics
  const stats = calculateRouteStats(routes);
  
  // Get unique drivers
  const drivers = Array.from(new Set(routes.map(r => ({ 
    id: r.driverId, 
    name: r.driverName 
  }))));
  
  const handleDriverFilterChange = (driverIds: string[]) => {
    onFilterChange({ ...filter, driverIds });
  };
  
  const handleStatusFilterChange = (statuses: Route['status'][]) => {
    onFilterChange({ ...filter, statuses });
  };
  
  const handleClearFilters = () => {
    onFilterChange({});
  };
  
  const hasActiveFilters = filter.driverIds?.length || filter.statuses?.length;
  
  if (!isExpanded) {
    return (
      <div className="route-control route-control-collapsed">
        <Button 
          icon={<DashboardOutlined />}
          onClick={() => setIsExpanded(true)}
          type="primary"
        >
          路線控制台
        </Button>
      </div>
    );
  }
  
  return (
    <>
      <Card 
        className="route-control"
        title={
          <div className="route-control-header">
            <Space>
              <DashboardOutlined />
              <span>路線控制台</span>
            </Space>
            <Button
              type="text"
              icon={<CloseOutlined />}
              size="small"
              onClick={() => setIsExpanded(false)}
            />
          </div>
        }
        size="small"
      >
        {/* Statistics */}
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic
              title="總路線"
              value={stats.totalRoutes}
              prefix={<EnvironmentOutlined />}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="配送中"
              value={stats.inProgressRoutes}
              prefix={<CarOutlined />}
              valueStyle={{ fontSize: 20, color: '#1890ff' }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="已完成"
              value={stats.completedRoutes}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ fontSize: 20, color: '#52c41a' }}
              suffix={`/ ${stats.totalStops}`}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="延誤"
              value={stats.delayedRoutes}
              valueStyle={{ fontSize: 20, color: stats.delayedRoutes > 0 ? '#f5222d' : '#52c41a' }}
            />
          </Col>
        </Row>
        
        <Divider style={{ margin: '16px 0' }} />
        
        {/* Quick Actions */}
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button
            type="primary"
            icon={<RocketOutlined />}
            onClick={onOptimize}
            block
          >
            優化路線
          </Button>
          
          <Button
            icon={<FilterOutlined />}
            onClick={() => setShowFilters(true)}
            block
            badge={hasActiveFilters ? { dot: true } : undefined}
          >
            篩選條件 {hasActiveFilters && `(${getActiveFilterCount(filter)})`}
          </Button>
        </Space>
        
        <Divider style={{ margin: '16px 0' }} />
        
        {/* Driver Quick Access */}
        <div className="driver-quick-access">
          <div style={{ marginBottom: 8, fontWeight: 500 }}>快速定位司機</div>
          <Select
            placeholder="選擇司機"
            style={{ width: '100%' }}
            onChange={onCenterDriver}
            allowClear
          >
            {drivers.map(driver => {
              const driverRoute = routes.find(r => r.driverId === driver.id);
              const isActive = driverRoute?.status === 'in-progress';
              
              return (
                <Option key={driver.id} value={driver.id}>
                  <Space>
                    <Badge 
                      status={isActive ? 'processing' : 'default'} 
                      text={driver.name}
                    />
                  </Space>
                </Option>
              );
            })}
          </Select>
        </div>
        
        {/* Display Options */}
        <Divider style={{ margin: '16px 0' }} />
        
        <div className="display-options">
          <div style={{ marginBottom: 8, fontWeight: 500 }}>顯示選項</div>
          <Space direction="vertical">
            <Switch
              checkedChildren="顯示即時路況"
              unCheckedChildren="隱藏路況"
              defaultChecked={false}
            />
            <Switch
              checkedChildren="顯示標籤"
              unCheckedChildren="隱藏標籤"
              defaultChecked={true}
            />
          </Space>
        </div>
      </Card>
      
      {/* Filter Drawer */}
      <Drawer
        title="篩選條件"
        placement="left"
        onClose={() => setShowFilters(false)}
        visible={showFilters}
        width={300}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* Driver Filter */}
          <div>
            <div style={{ marginBottom: 8 }}>司機</div>
            <Select
              mode="multiple"
              placeholder="選擇司機"
              style={{ width: '100%' }}
              value={filter.driverIds || []}
              onChange={handleDriverFilterChange}
            >
              {drivers.map(driver => (
                <Option key={driver.id} value={driver.id}>
                  {driver.name}
                </Option>
              ))}
            </Select>
          </div>
          
          {/* Status Filter */}
          <div>
            <div style={{ marginBottom: 8 }}>狀態</div>
            <Select
              mode="multiple"
              placeholder="選擇狀態"
              style={{ width: '100%' }}
              value={filter.statuses || []}
              onChange={handleStatusFilterChange}
            >
              <Option value="not-started">未開始</Option>
              <Option value="in-progress">配送中</Option>
              <Option value="completed">已完成</Option>
              <Option value="delayed">延誤</Option>
            </Select>
          </div>
          
          <Divider />
          
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Button onClick={handleClearFilters}>清除篩選</Button>
            <Button type="primary" onClick={() => setShowFilters(false)}>
              套用
            </Button>
          </Space>
        </Space>
      </Drawer>
    </>
  );
};

function calculateRouteStats(routes: Route[]): RouteStats {
  const stats: RouteStats = {
    totalRoutes: routes.length,
    completedRoutes: 0,
    inProgressRoutes: 0,
    delayedRoutes: 0,
    totalStops: 0,
    completedStops: 0,
    averageDelay: 0,
    totalDistance: 0,
    fuelSaved: 0,
  };
  
  let totalDelay = 0;
  let delayCount = 0;
  
  routes.forEach(route => {
    // Route status
    if (route.status === 'completed') stats.completedRoutes++;
    if (route.status === 'in-progress') stats.inProgressRoutes++;
    if (route.status === 'delayed') stats.delayedRoutes++;
    
    // Distance
    stats.totalDistance += route.totalDistance;
    
    // Stops
    stats.totalStops += route.stops.length;
    route.stops.forEach(stop => {
      if (stop.status === 'completed') {
        stats.completedStops++;
        
        // Calculate delay
        if (stop.actualArrival && stop.estimatedArrival) {
          const delay = stop.actualArrival.getTime() - stop.estimatedArrival.getTime();
          if (delay > 0) {
            totalDelay += delay;
            delayCount++;
          }
        }
      }
    });
  });
  
  // Average delay in minutes
  stats.averageDelay = delayCount > 0 ? Math.round(totalDelay / delayCount / 60000) : 0;
  
  // Estimate fuel saved (mock calculation)
  stats.fuelSaved = Math.round(stats.totalDistance * 0.25); // 25% savings
  
  return stats;
}

function getActiveFilterCount(filter: RouteFilter): number {
  let count = 0;
  if (filter.driverIds?.length) count += filter.driverIds.length;
  if (filter.statuses?.length) count += filter.statuses.length;
  return count;
}

export default RouteControl;