import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Spin,
  Alert,
} from 'antd';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';
import axios from 'axios';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface FuelSavingsData {
  period: {
    start: string;
    end: string;
  };
  daily_breakdown: Array<{
    date: string;
    fuel_saved: number;
    cost_saved: number;
    distance_saved: number;
  }>;
  total_fuel_saved: number;
  total_cost_saved: number;
}

const { Title, Text } = Typography;

const FuelSavingsChart: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FuelSavingsData | null>(null);

  useEffect(() => {
    fetchFuelSavings();
  }, []);

  const fetchFuelSavings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get<FuelSavingsData>(
        '/api/v1/analytics/fuel-savings/weekly'
      );
      
      setData(response.data);
    } catch (err) {
      console.error('Error fetching fuel savings:', err);
      setError('無法載入燃料節省資料');
    } finally {
      setLoading(false);
    }
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

  if (!data) {
    return null;
  }

  const chartData = {
    labels: data.daily_breakdown.map(d => 
      format(new Date(d.date), 'MM/dd (E)', { locale: zhTW })
    ),
    datasets: [
      {
        label: '節省燃料 (公升)',
        data: data.daily_breakdown.map(d => d.fuel_saved),
        backgroundColor: 'rgba(76, 175, 80, 0.6)',
        borderColor: 'rgba(76, 175, 80, 1)',
        borderWidth: 1,
        yAxisID: 'y',
      },
      {
        label: '節省成本 (TWD)',
        data: data.daily_breakdown.map(d => d.cost_saved),
        backgroundColor: 'rgba(33, 150, 243, 0.6)',
        borderColor: 'rgba(33, 150, 243, 1)',
        borderWidth: 1,
        yAxisID: 'y1',
      },
    ],
  };

  const options: ChartOptions<'bar'> = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          font: {
            size: 14,
          },
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              if (context.datasetIndex === 0) {
                label += context.parsed.y.toFixed(1) + ' 公升';
              } else {
                label += '$' + context.parsed.y.toLocaleString();
              }
            }
            return label;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: '燃料 (公升)',
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: '成本 (TWD)',
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  return (
    <Card>
      <div style={{ padding: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>
          週燃料節省分析
        </Title>
        
        <div style={{ marginBottom: 24 }}>
          <Bar data={chartData} options={options} height={100} />
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: 24 }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={2} style={{ color: '#52c41a', margin: 0 }}>
              {data.total_fuel_saved.toFixed(1)}
            </Title>
            <Text type="secondary">
              總節省燃料 (公升)
            </Text>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <Title level={2} style={{ color: '#1890ff', margin: 0 }}>
              ${data.total_cost_saved.toLocaleString()}
            </Title>
            <Text type="secondary">
              總節省成本 (TWD)
            </Text>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <Title level={2} style={{ color: '#722ed1', margin: 0 }}>
              {(data.total_fuel_saved * 2.31).toFixed(1)}
            </Title>
            <Text type="secondary">
              減少 CO₂ (公斤)
            </Text>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default FuelSavingsChart;