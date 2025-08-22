/**
 * Optimized Components with React.memo
 * Prevents unnecessary re-renders of expensive components
 */

import React from 'react';
import { Card, List, Table, Tag, Progress, Statistic } from 'antd';
import type { ColumnsType } from 'antd/es/table';

// Optimized Card Component
export const OptimizedCard = React.memo(Card, (prevProps, nextProps) => {
  // Custom comparison - only re-render if specific props change
  return (
    prevProps.title === nextProps.title &&
    prevProps.loading === nextProps.loading &&
    JSON.stringify(prevProps.children) === JSON.stringify(nextProps.children)
  );
});

// Optimized List Item
interface ListItemProps {
  item: any;
  renderItem: (item: any) => React.ReactNode;
}

export const OptimizedListItem = React.memo<ListItemProps>(
  ({ item, renderItem }) => {
    return <>{renderItem(item)}</>;
  },
  (prevProps, nextProps) => {
    // Deep comparison for objects
    return JSON.stringify(prevProps.item) === JSON.stringify(nextProps.item);
  }
);

// Optimized Table Component
interface OptimizedTableProps<T = any> {
  columns: ColumnsType<T>;
  dataSource: T[];
  loading?: boolean;
  pagination?: any;
  rowKey?: string | ((record: T) => string);
  onChange?: (pagination: any, filters: any, sorter: any) => void;
}

export const OptimizedTable = React.memo(
  <T extends object>(props: OptimizedTableProps<T>) => {
    return <Table {...props} />;
  },
  (prevProps, nextProps) => {
    // Only re-render if data or loading state changes
    return (
      prevProps.loading === nextProps.loading &&
      prevProps.dataSource.length === nextProps.dataSource.length &&
      JSON.stringify(prevProps.dataSource) === JSON.stringify(nextProps.dataSource) &&
      JSON.stringify(prevProps.pagination) === JSON.stringify(nextProps.pagination)
    );
  }
);

// Optimized Statistic Component
interface StatisticProps {
  title: string;
  value: number | string;
  prefix?: React.ReactNode;
  suffix?: string;
  valueStyle?: React.CSSProperties;
}

export const OptimizedStatistic = React.memo<StatisticProps>(
  ({ title, value, prefix, suffix, valueStyle }) => {
    return (
      <Statistic
        title={title}
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={valueStyle}
      />
    );
  },
  (prevProps, nextProps) => {
    return (
      prevProps.title === nextProps.title &&
      prevProps.value === nextProps.value &&
      prevProps.suffix === nextProps.suffix
    );
  }
);

// Optimized Progress Component
interface ProgressProps {
  percent: number;
  status?: 'success' | 'exception' | 'normal' | 'active';
  strokeColor?: string;
  showInfo?: boolean;
}

export const OptimizedProgress = React.memo<ProgressProps>(
  ({ percent, status, strokeColor, showInfo = true }) => {
    return (
      <Progress
        percent={percent}
        status={status}
        strokeColor={strokeColor}
        showInfo={showInfo}
      />
    );
  },
  (prevProps, nextProps) => {
    return (
      prevProps.percent === nextProps.percent &&
      prevProps.status === nextProps.status
    );
  }
);

// Optimized Tag Component
interface TagProps {
  color?: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}

export const OptimizedTag = React.memo<TagProps>(
  ({ color, children, icon }) => {
    return (
      <Tag color={color} icon={icon}>
        {children}
      </Tag>
    );
  },
  (prevProps, nextProps) => {
    return (
      prevProps.color === nextProps.color &&
      prevProps.children === nextProps.children
    );
  }
);

// Optimized Route List Item (specific to Lucky Gas)
interface RouteItemProps {
  route: {
    id: number;
    routeNumber: string;
    status: string;
    totalOrders: number;
    completedOrders: number;
    driverName?: string;
    progressPercentage: number;
  };
}

export const OptimizedRouteItem = React.memo<RouteItemProps>(
  ({ route }) => {
    return (
      <List.Item>
        <div style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <div>
              <strong>{route.routeNumber}</strong>
              <Tag color={route.status === '進行中' ? 'processing' : 'default'} style={{ marginLeft: 8 }}>
                {route.status}
              </Tag>
              {route.driverName && <span style={{ marginLeft: 8 }}>{route.driverName}</span>}
            </div>
            <div>{route.completedOrders}/{route.totalOrders} 完成</div>
          </div>
          <Progress
            percent={route.progressPercentage}
            status={route.progressPercentage === 100 ? 'success' : 'active'}
          />
        </div>
      </List.Item>
    );
  },
  (prevProps, nextProps) => {
    return JSON.stringify(prevProps.route) === JSON.stringify(nextProps.route);
  }
);

// Optimized Order List Item
interface OrderItemProps {
  order: {
    id: string;
    orderNumber: string;
    customerName: string;
    status: string;
    priority: string;
    deliveryDate?: string;
  };
  onClick?: (order: any) => void;
}

export const OptimizedOrderItem = React.memo<OrderItemProps>(
  ({ order, onClick }) => {
    const handleClick = React.useCallback(() => {
      if (onClick) {
        onClick(order);
      }
    }, [order, onClick]);

    return (
      <List.Item
        onClick={handleClick}
        style={{ cursor: onClick ? 'pointer' : 'default' }}
      >
        <List.Item.Meta
          title={`${order.orderNumber} - ${order.customerName}`}
          description={
            <div>
              <Tag color={order.priority === 'urgent' ? 'red' : 'default'}>
                {order.priority}
              </Tag>
              <Tag color={order.status === 'pending' ? 'orange' : 'green'}>
                {order.status}
              </Tag>
              {order.deliveryDate && <span>配送日期: {order.deliveryDate}</span>}
            </div>
          }
        />
      </List.Item>
    );
  },
  (prevProps, nextProps) => {
    return (
      JSON.stringify(prevProps.order) === JSON.stringify(nextProps.order) &&
      prevProps.onClick === nextProps.onClick
    );
  }
);

// Utility function to wrap any component with React.memo
export function withMemo<P extends object>(
  Component: React.ComponentType<P>,
  propsAreEqual?: (prevProps: P, nextProps: P) => boolean
): React.MemoExoticComponent<React.ComponentType<P>> {
  return React.memo(Component, propsAreEqual);
}

// Export all optimized components
export default {
  Card: OptimizedCard,
  ListItem: OptimizedListItem,
  Table: OptimizedTable,
  Statistic: OptimizedStatistic,
  Progress: OptimizedProgress,
  Tag: OptimizedTag,
  RouteItem: OptimizedRouteItem,
  OrderItem: OptimizedOrderItem,
  withMemo,
};