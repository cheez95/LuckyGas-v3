import React from 'react';
import { Card, Row, Col, Statistic, Typography } from 'antd';
import {
  ShoppingCartOutlined,
  UserOutlined,
  CarOutlined,
  DollarOutlined,
} from '@ant-design/icons';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  // TODO: Fetch actual statistics from API
  const stats = {
    todayOrders: 45,
    activeCustomers: 1267,
    driversOnRoute: 8,
    todayRevenue: 68500,
  };

  return (
    <div>
      <Title level={2}>總覽</Title>
      <Row gutter={[16, 16]} className="dashboard-stats">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日訂單"
              value={stats.todayOrders}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活躍客戶"
              value={stats.activeCustomers}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="配送中司機"
              value={stats.driversOnRoute}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日營收"
              value={stats.todayRevenue}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#cf1322' }}
              suffix="元"
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="即將實現功能">
            <ul>
              <li>即時訂單狀態追蹤</li>
              <li>每日需求預測圖表</li>
              <li>司機配送路線地圖</li>
              <li>客戶滿意度統計</li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;