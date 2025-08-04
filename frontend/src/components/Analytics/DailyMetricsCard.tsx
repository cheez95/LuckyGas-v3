import React from 'react';
import { Card, Tag, Typography } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface DailyMetricsCardProps {
  title: string;
  value: number | string;
  change?: number;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning';
  showChange?: boolean;
}

const DailyMetricsCard: React.FC<DailyMetricsCardProps> = ({
  title,
  value,
  change,
  icon,
  color,
  showChange = true,
}) => {
  const getChangeColor = () => {
    if (!change) return 'default';
    return change > 0 ? 'success' : 'error';
  };

  const getChangeIcon = () => {
    if (!change) return null;
    return change > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />;
  };

  const formatChange = () => {
    if (!change) return '';
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
  };

  // Map MUI colors to Ant Design colors
  const colorMap = {
    primary: '#1890ff',
    secondary: '#722ed1',
    success: '#52c41a',
    error: '#f5222d',
    info: '#1890ff',
    warning: '#faad14',
  };

  return (
    <Card style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div
          style={{
            backgroundColor: `${colorMap[color]}20`,
            borderRadius: 4,
            padding: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: colorMap[color],
          }}
        >
          {icon}
        </div>
        {showChange && change !== undefined && (
          <Tag
            icon={getChangeIcon()}
            color={getChangeColor()}
          >
            {formatChange()}
          </Tag>
        )}
      </div>
      
      <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
        {title}
      </Text>
      
      <div style={{ fontSize: '28px', fontWeight: 'bold' }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </Card>
  );
};

export default DailyMetricsCard;