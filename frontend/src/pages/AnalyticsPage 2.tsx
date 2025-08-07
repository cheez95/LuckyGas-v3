import React from 'react';
import { Card } from 'antd';
import AnalyticsDashboard from '../components/Analytics/AnalyticsDashboard';

const AnalyticsPage: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <AnalyticsDashboard />
      </Card>
    </div>
  );
};

export default AnalyticsPage;