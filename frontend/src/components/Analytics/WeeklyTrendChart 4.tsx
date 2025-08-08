import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
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

  const handleMetricChange = (
    event: React.MouseEvent<HTMLElement>,
    newMetric: 'routes' | 'fuel' | 'ontime' | null,
  ) => {
    if (newMetric !== null) {
      setSelectedMetric(newMetric);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
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
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h6">
            週趨勢分析
          </Typography>
          
          <ToggleButtonGroup
            value={selectedMetric}
            exclusive
            onChange={handleMetricChange}
            size="small"
          >
            <ToggleButton value="routes">
              路線數
            </ToggleButton>
            <ToggleButton value="fuel">
              燃料節省
            </ToggleButton>
            <ToggleButton value="ontime">
              準時率
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        <Box height={detailed ? 400 : 300}>
          <Line data={chartData} options={options} />
        </Box>

        {detailed && (
          <Box mt={3} p={2} bgcolor="grey.50" borderRadius={1}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              趨勢分析：
            </Typography>
            <Typography variant="body2">
              • {selectedMetric === 'routes' && '本週路線數較上週增加 8.5%'}
              • {selectedMetric === 'fuel' && '燃料節省效率提升 12%，主要來自路線優化'}
              • {selectedMetric === 'ontime' && '準時率保持穩定在 90% 以上'}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default WeeklyTrendChart;