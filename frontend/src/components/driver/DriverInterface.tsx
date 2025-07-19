import React from 'react';
import { Card, Typography, List, Button, Space, Tag } from 'antd';
import { EnvironmentOutlined, PhoneOutlined, CheckCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const DriverInterface: React.FC = () => {
  // TODO: Fetch actual route data from API
  const mockRoute = {
    routeId: 'R001',
    date: '2025-01-20',
    totalStops: 12,
    completedStops: 5,
    deliveries: [
      {
        id: 1,
        customerName: '張三',
        address: '台北市大安區和平東路100號',
        phone: '0912-345-678',
        quantity: 2,
        status: 'completed',
      },
      {
        id: 2,
        customerName: '李四',
        address: '台北市信義區信義路200號',
        phone: '0923-456-789',
        quantity: 1,
        status: 'pending',
      },
    ],
  };

  return (
    <div className="driver-interface">
      <Title level={3}>今日配送路線</Title>
      <Card>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text type="secondary">路線編號：</Text>
            <Text strong>{mockRoute.routeId}</Text>
          </div>
          <div>
            <Text type="secondary">配送進度：</Text>
            <Text strong>{mockRoute.completedStops} / {mockRoute.totalStops}</Text>
          </div>
        </Space>
      </Card>
      
      <div style={{ marginTop: 16 }}>
        <Title level={4}>配送清單</Title>
        <List
          dataSource={mockRoute.deliveries}
          renderItem={(item) => (
            <Card 
              style={{ marginBottom: 16 }}
              actions={[
                <Button 
                  type="link" 
                  icon={<PhoneOutlined />}
                  href={`tel:${item.phone}`}
                >
                  撥打電話
                </Button>,
                <Button 
                  type="link" 
                  icon={<EnvironmentOutlined />}
                >
                  導航
                </Button>,
                item.status === 'pending' ? (
                  <Button type="primary" icon={<CheckCircleOutlined />}>
                    完成配送
                  </Button>
                ) : (
                  <Tag color="green">已完成</Tag>
                ),
              ]}
            >
              <Card.Meta
                title={item.customerName}
                description={
                  <Space direction="vertical">
                    <Text>{item.address}</Text>
                    <Text>數量：{item.quantity} 桶</Text>
                  </Space>
                }
              />
            </Card>
          )}
        />
      </div>
    </div>
  );
};

export default DriverInterface;