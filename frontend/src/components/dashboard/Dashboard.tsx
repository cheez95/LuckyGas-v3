import React from 'react';
import { Card, Row, Col, Statistic, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ShoppingCartOutlined,
  UserOutlined,
  CarOutlined,
  DollarOutlined,
} from '@ant-design/icons';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  
  // TODO: Fetch actual statistics from API
  const stats = {
    todayOrders: 45,
    activeCustomers: 1267,
    driversOnRoute: 8,
    todayRevenue: 68500,
  };

  return (
    <div>
      <Title level={2}>{t('navigation.dashboard')}</Title>
      <Row gutter={[16, 16]} className="dashboard-stats">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('dashboard.todayOrders')}
              value={stats.todayOrders}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('dashboard.activeCustomers')}
              value={stats.activeCustomers}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('dashboard.driversOnRoute')}
              value={stats.driversOnRoute}
              prefix={<CarOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('dashboard.todayRevenue')}
              value={stats.todayRevenue}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#cf1322' }}
              suffix={t('dashboard.yuan')}
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title={t('dashboard.upcomingFeatures')}>
            <ul>
              <li>{t('dashboard.features.realTimeTracking')}</li>
              <li>{t('dashboard.features.demandPrediction')}</li>
              <li>{t('dashboard.features.routeMap')}</li>
              <li>{t('dashboard.features.satisfaction')}</li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;