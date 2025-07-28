import React from 'react';
import { Card } from 'antd';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface RevenueChartProps {
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      borderColor?: string;
      backgroundColor?: string;
      type?: 'line' | 'bar';
      yAxisID?: string;
      fill?: boolean;
      tension?: number;
    }>;
  };
  title?: string;
  height?: number;
  showLegend?: boolean;
  currency?: boolean;
  stacked?: boolean;
}

const RevenueChart: React.FC<RevenueChartProps> = ({
  data,
  title,
  height = 300,
  showLegend = true,
  currency = true,
  stacked = false,
}) => {
  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `NT$ ${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `NT$ ${(value / 1000).toFixed(0)}K`;
    }
    return `NT$ ${value.toFixed(0)}`;
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: showLegend,
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const label = context.dataset.label || '';
            const value = currency ? formatCurrency(context.parsed.y) : context.parsed.y;
            return `${label}: ${value}`;
          },
        },
      },
    },
    scales: {
      x: {
        stacked: stacked,
      },
      y: {
        stacked: stacked,
        beginAtZero: true,
        ticks: {
          callback: currency ? (value: any) => formatCurrency(value) : undefined,
        },
      },
    },
  };

  // Check if it's a mixed chart (both line and bar)
  const hasBar = data.datasets.some(d => d.type === 'bar' || !d.type);
  const hasLine = data.datasets.some(d => d.type === 'line');

  const ChartComponent = hasBar && !hasLine ? Bar : Line;

  return title ? (
    <Card title={title} bodyStyle={{ padding: '12px' }}>
      <div style={{ height }}>
        <ChartComponent data={data} options={options} />
      </div>
    </Card>
  ) : (
    <div style={{ height }}>
      <ChartComponent data={data} options={options} />
    </div>
  );
};

export default RevenueChart;