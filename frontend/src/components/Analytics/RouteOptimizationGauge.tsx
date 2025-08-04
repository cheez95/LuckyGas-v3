import React from 'react';
import {
  Card,
  Typography,
} from 'antd';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface RouteOptimizationGaugeProps {
  value: number; // 0-100
}

const { Title, Text } = Typography;

const RouteOptimizationGauge: React.FC<RouteOptimizationGaugeProps> = ({ value }) => {
  // Create data for the gauge chart
  const data = [
    { name: 'Score', value: value },
    { name: 'Remaining', value: 100 - value },
  ];

  // Determine color based on value
  const getColor = () => {
    if (value >= 90) return '#4caf50'; // Green
    if (value >= 70) return '#ff9800'; // Orange
    return '#f44336'; // Red
  };

  const getStatus = () => {
    if (value >= 90) return '優秀';
    if (value >= 70) return '良好';
    if (value >= 50) return '尚可';
    return '需改進';
  };

  const getRecommendation = () => {
    if (value >= 90) return '路線優化效果卓越，繼續保持！';
    if (value >= 70) return '優化效果良好，可考慮增加配送點密度';
    if (value >= 50) return '仍有改進空間，建議檢視路線規劃演算法';
    return '需要重新評估優化策略';
  };

  return (
    <Card style={{ height: '100%' }}>
      <div style={{ padding: 16 }}>
        <Title level={5} style={{ textAlign: 'center', marginBottom: 16 }}>
          路線優化效率
        </Title>

        <div style={{ position: 'relative', height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                startAngle={180}
                endAngle={0}
                innerRadius={60}
                outerRadius={80}
                dataKey="value"
              >
                <Cell fill={getColor()} />
                <Cell fill="#e0e0e0" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
            }}
          >
            <Title level={1} style={{ color: getColor(), margin: 0 }}>
              {value}%
            </Title>
            <Text type="secondary">
              {getStatus()}
            </Text>
          </div>
        </div>

        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <Text type="secondary">
            {getRecommendation()}
          </Text>
        </div>

        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-around' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={5} type="secondary" style={{ margin: 0 }}>
              目標
            </Title>
            <Title level={3} style={{ margin: 0 }}>
              90%
            </Title>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Title level={5} type="secondary" style={{ margin: 0 }}>
              差距
            </Title>
            <Title 
              level={3}
              style={{ 
                color: value >= 90 ? '#52c41a' : '#faad14',
                margin: 0
              }}
            >
              {value >= 90 ? '+' : ''}{value - 90}%
            </Title>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default RouteOptimizationGauge;