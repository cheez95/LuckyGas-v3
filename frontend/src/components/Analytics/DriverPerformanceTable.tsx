import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Table,
  Tag,
  Avatar,
  Spin,
  Alert,
  Progress,
} from 'antd';
import {
  TrophyOutlined,
  RiseOutlined,
  TruckOutlined,
} from '@ant-design/icons';
import axios from 'axios';

interface DriverMetrics {
  driver_id: string;
  driver_name: string;
  today_on_time_pct: number;
  weekly_metrics: {
    total_routes: number;
    total_deliveries: number;
    average_on_time_pct: number;
    fuel_efficiency_score: number;
    overall_score: number;
  };
}

interface TopDriversResponse {
  date: string;
  top_drivers: DriverMetrics[];
}

const { Text, Title } = Typography;

const DriverPerformanceTable: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<DriverMetrics[]>([]);

  useEffect(() => {
    fetchTopDrivers();
  }, []);

  const fetchTopDrivers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get<TopDriversResponse>(
        '/api/v1/analytics/drivers/top-performers'
      );
      
      setDrivers(response.data.top_drivers);
    } catch (err) {
      console.error('Error fetching top drivers:', err);
      setError('無法載入司機績效資料');
    } finally {
      setLoading(false);
    }
  };

  const getPerformanceColor = (score: number): string => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'error';
  };

  const getPerformanceColorHex = (score: number): string => {
    if (score >= 90) return '#52c41a';
    if (score >= 70) return '#faad14';
    return '#ff4d4f';
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) {
      return <TrophyOutlined style={{ color: '#ffd700', fontSize: 20 }} />;
    }
    if (rank === 2) {
      return <TrophyOutlined style={{ color: '#c0c0c0', fontSize: 18 }} />;
    }
    if (rank === 3) {
      return <TrophyOutlined style={{ color: '#CD7F32', fontSize: 16 }} />;
    }
    return null;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert type="error" message={error} style={{ marginBottom: 16 }} />
    );
  }

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {rank}
          {getRankIcon(rank)}
        </div>
      ),
    },
    {
      title: '司機',
      dataIndex: 'driver',
      key: 'driver',
      render: (driver: DriverMetrics) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Avatar size={32}>{driver.driver_name.charAt(0)}</Avatar>
          <Text strong>{driver.driver_name}</Text>
        </div>
      ),
    },
    {
      title: '今日準時率',
      dataIndex: 'today_on_time_pct',
      key: 'today_on_time_pct',
      align: 'center' as const,
      render: (pct: number) => (
        <Tag color={getPerformanceColor(pct)}>
          {pct.toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: '週平均準時率',
      dataIndex: 'weekly_avg',
      key: 'weekly_avg',
      align: 'center' as const,
      render: (avg: number, record: any) => (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
          <Text>{avg.toFixed(1)}%</Text>
          {avg > record.today_on_time_pct && (
            <RiseOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          )}
        </div>
      ),
    },
    {
      title: '本週路線',
      dataIndex: 'total_routes',
      key: 'total_routes',
      align: 'center' as const,
    },
    {
      title: '本週配送',
      dataIndex: 'total_deliveries',
      key: 'total_deliveries',
      align: 'center' as const,
    },
    {
      title: '燃料效率',
      dataIndex: 'fuel_efficiency_score',
      key: 'fuel_efficiency_score',
      align: 'center' as const,
      render: (score: number) => (
        <div style={{ width: 80, margin: '0 auto' }}>
          <Progress
            percent={score}
            size="small"
            strokeColor={getPerformanceColorHex(score)}
            showInfo={false}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {score.toFixed(0)}%
          </Text>
        </div>
      ),
    },
    {
      title: '綜合評分',
      dataIndex: 'overall_score',
      key: 'overall_score',
      align: 'center' as const,
      render: (score: number) => (
        <Text strong style={{ color: getPerformanceColorHex(score) }}>
          {score.toFixed(1)}
        </Text>
      ),
    },
  ];

  const dataSource = drivers.map((driver, index) => ({
    key: driver.driver_id,
    rank: index + 1,
    driver,
    today_on_time_pct: driver.today_on_time_pct,
    weekly_avg: driver.weekly_metrics.average_on_time_pct,
    total_routes: driver.weekly_metrics.total_routes,
    total_deliveries: driver.weekly_metrics.total_deliveries,
    fuel_efficiency_score: driver.weekly_metrics.fuel_efficiency_score,
    overall_score: driver.weekly_metrics.overall_score,
  }));

  return (
    <Card>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={5} style={{ margin: 0 }}>
            司機績效排行榜
          </Title>
          <Tag
            icon={<TruckOutlined />}
            color="blue"
          >
            {drivers.length} 位司機
          </Tag>
        </div>

        <Table
          columns={columns}
          dataSource={dataSource}
          pagination={false}
          size="middle"
          rowClassName={(record, index) => index === 0 ? 'ant-table-row-selected' : ''}
        />

        <div style={{ marginTop: 24, padding: 16, backgroundColor: '#fafafa', borderRadius: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            * 綜合評分基於準時率(30%)、燃料效率(20%)、客戶滿意度(30%)、平均延遲時間(20%)計算
          </Text>
        </div>
      </div>
    </Card>
  );
};

export default DriverPerformanceTable;