import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
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
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
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
      <CardContent>
        <Typography variant="h6" gutterBottom>
          週燃料節省分析
        </Typography>
        
        <Box sx={{ mb: 3 }}>
          <Bar data={chartData} options={options} height={100} />
        </Box>
        
        <Box display="flex" justifyContent="space-around" mt={3}>
          <Box textAlign="center">
            <Typography variant="h4" color="success.main" fontWeight="bold">
              {data.total_fuel_saved.toFixed(1)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              總節省燃料 (公升)
            </Typography>
          </Box>
          
          <Box textAlign="center">
            <Typography variant="h4" color="primary.main" fontWeight="bold">
              ${data.total_cost_saved.toLocaleString()}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              總節省成本 (TWD)
            </Typography>
          </Box>
          
          <Box textAlign="center">
            <Typography variant="h4" color="secondary.main" fontWeight="bold">
              {(data.total_fuel_saved * 2.31).toFixed(1)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              減少 CO₂ (公斤)
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default FuelSavingsChart;