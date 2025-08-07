import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Spin,
  Alert,
  Radio,
} from 'antd';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { format, subDays } from 'date-fns';
import { zhTW } from 'date-fns/locale';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface WeeklyTrendChartProps {
  detailed?: boolean;
}

const { Title: TypographyTitle, Text } = Typography;

const WeeklyTrendChart: React.FC<WeeklyTrendChartProps> = ({ detailed = false }) => {
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState<'routes' | 'fuel' | 'ontime'>('routes');

  // Mock data - in real app, fetch from API
  const mockData = {
    routes: Array.from({ length: 7 }, (_, i) => ({
      date: format(subDays(new Date(), 6 - i), 'MM/dd'),
      value: 45 + Math.floor(Math.random() * 15),
    })),
    fuel: Array.from({ length: 7 }, (_, i) => ({
      date: format(subDays(new Date(), 6 - i), 'MM/dd'),
      value: 120 + Math.floor(Math.random() * 30),
    })),
    ontime: Array.from({ length: 7 }, (_, i) => ({
      date: format(subDays(new Date(), 6 - i), 'MM/dd'),
      value: 85 + Math.floor(Math.random() * 10),
    })),
  };

  useEffect(() => {
    // Simulate loading
    setTimeout(() => setLoading(false), 1000);
  }, []);

  const handleMetricChange = (e: any) => {
    setSelectedMetric(e.target.value);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" />
      </div>
    );
  }

  const currentData = mockData[selectedMetric];
  
  const chartData = {
    labels: currentData.map(d => d.date),
    datasets: [
      {
        label: selectedMetric === 'routes' ? '路線數' : 
                selectedMetric === 'fuel' ? '節省燃料 (L)' : '準時率 (%)',
        data: currentData.map(d => d.value),
        borderColor: selectedMetric === 'routes' ? 'rgb(33, 150, 243)' : 
                     selectedMetric === 'fuel' ? 'rgb(76, 175, 80)' : 'rgb(255, 152, 0)',
        backgroundColor: selectedMetric === 'routes' ? 'rgba(33, 150, 243, 0.1)' : 
                         selectedMetric === 'fuel' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(255, 152, 0, 0.1)',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${value}${selectedMetric === 'fuel' ? ' L' : selectedMetric === 'ontime' ? '%' : ''}`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: selectedMetric !== 'ontime',
        max: selectedMetric === 'ontime' ? 100 : undefined,
        ticks: {
          callback: (value) => {
            return `${value}${selectedMetric === 'fuel' ? ' L' : selectedMetric === 'ontime' ? '%' : ''}`;
          },
        },
      },
    },
  };

  return (
    <Card>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <TypographyTitle level={5} style={{ margin: 0 }}>
            週趨勢分析
          </TypographyTitle>
          
          <Radio.Group
            value={selectedMetric}
            onChange={handleMetricChange}
            size="small"
            buttonStyle="solid"
          >
            <Radio.Button value="routes">
              路線數
            </Radio.Button>
            <Radio.Button value="fuel">
              燃料節省
            </Radio.Button>
            <Radio.Button value="ontime">
              準時率
            </Radio.Button>
          </Radio.Group>
        </div>

        <div style={{ height: detailed ? 400 : 300 }}>
          <Line data={chartData} options={options} />
        </div>

        {detailed && (
          <div style={{ marginTop: 24, padding: 16, backgroundColor: '#fafafa', borderRadius: 4 }}>
            <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
              趨勢分析：
            </Text>
            <Text>
              • {selectedMetric === 'routes' && '本週路線數較上週增加 8.5%'}<br/>
              • {selectedMetric === 'fuel' && '燃料節省效率提升 12%，主要來自路線優化'}<br/>
              • {selectedMetric === 'ontime' && '準時率保持穩定在 90% 以上'}
            </Text>
          </div>
        )}
      </div>
    </Card>
  );
};

export default WeeklyTrendChart;