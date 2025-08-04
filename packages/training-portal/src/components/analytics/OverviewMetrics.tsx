import React from 'react';
import { Grid, Paper, Box, Typography, Skeleton, Chip } from '@mui/material';
import { 
  People, 
  School, 
  Timer, 
  TrendingUp,
  EmojiEvents,
  Assignment,
  Speed,
  CheckCircle
} from '@mui/icons-material';
import { animated, useSpring } from '@react-spring/web';
import CountUp from 'react-countup';

interface MetricCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
  change?: number;
  loading?: boolean;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

function MetricCard({ 
  title, 
  value, 
  icon, 
  color, 
  subtitle, 
  change, 
  loading = false,
  prefix = '',
  suffix = '',
  decimals = 0
}: MetricCardProps) {
  const animation = useSpring({
    from: { opacity: 0, transform: 'scale(0.9)' },
    to: { opacity: 1, transform: 'scale(1)' },
    config: { tension: 300, friction: 20 },
  });

  if (loading) {
    return (
      <Paper sx={{ p: 3, height: '100%' }}>
        <Skeleton variant="circular" width={48} height={48} sx={{ mb: 2 }} />
        <Skeleton variant="text" width="60%" />
        <Skeleton variant="text" width="80%" height={32} />
        <Skeleton variant="text" width="40%" />
      </Paper>
    );
  }

  const numericValue = typeof value === 'string' ? parseFloat(value) : value;

  return (
    <animated.div style={animation}>
      <Paper 
        sx={{ 
          p: 3, 
          height: '100%',
          position: 'relative',
          overflow: 'hidden',
          '&:hover': {
            boxShadow: 4,
            transform: 'translateY(-2px)',
            transition: 'all 0.3s ease',
          }
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            top: -20,
            right: -20,
            width: 100,
            height: 100,
            borderRadius: '50%',
            bgcolor: `${color}20`,
            zIndex: 0,
          }}
        />
        
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                bgcolor: `${color}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: color,
                mr: 2,
              }}
            >
              {icon}
            </Box>
            
            {change !== undefined && (
              <Chip
                size="small"
                label={`${change > 0 ? '+' : ''}${change}%`}
                color={change > 0 ? 'success' : 'error'}
                sx={{ ml: 'auto' }}
              />
            )}
          </Box>
          
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          
          <Typography variant="h4" component="div" fontWeight="bold">
            {prefix}
            <CountUp
              end={numericValue}
              duration={1.5}
              separator=","
              decimals={decimals}
            />
            {suffix}
          </Typography>
          
          {subtitle && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {subtitle}
            </Typography>
          )}
        </Box>
      </Paper>
    </animated.div>
  );
}

interface OverviewMetricsProps {
  data: any;
  loading?: boolean;
}

export function OverviewMetrics({ data, loading = false }: OverviewMetricsProps) {
  const metrics = [
    {
      title: '活躍用戶',
      value: data?.active_users || 0,
      icon: <People />,
      color: '#2196F3',
      subtitle: '本月登入用戶',
      change: data?.active_users_change,
    },
    {
      title: '總學習時數',
      value: data?.total_learning_hours || 0,
      icon: <Timer />,
      color: '#4CAF50',
      subtitle: '累計學習時間',
      change: data?.learning_hours_change,
      suffix: ' 小時',
    },
    {
      title: '課程完成數',
      value: data?.courses_completed || 0,
      icon: <School />,
      color: '#FF9800',
      subtitle: '已完成課程',
      change: data?.completion_change,
    },
    {
      title: '平均完成率',
      value: data?.avg_completion_rate || 0,
      icon: <TrendingUp />,
      color: '#9C27B0',
      subtitle: '所有課程平均',
      suffix: '%',
      decimals: 1,
    },
    {
      title: '成就解鎖',
      value: data?.achievements_unlocked || 0,
      icon: <EmojiEvents />,
      color: '#F44336',
      subtitle: '總成就數',
      change: data?.achievements_change,
    },
    {
      title: '測驗通過率',
      value: data?.quiz_pass_rate || 0,
      icon: <Assignment />,
      color: '#00BCD4',
      subtitle: '平均通過率',
      suffix: '%',
      decimals: 1,
    },
    {
      title: '平均學習速度',
      value: data?.avg_learning_speed || 1.0,
      icon: <Speed />,
      color: '#795548',
      subtitle: '相對標準速度',
      suffix: 'x',
      decimals: 2,
    },
    {
      title: '認證獲得',
      value: data?.certifications_earned || 0,
      icon: <CheckCircle />,
      color: '#607D8B',
      subtitle: '本月新增',
      change: data?.certifications_change,
    },
  ];

  return (
    <Grid container spacing={3}>
      {metrics.map((metric, index) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={index}>
          <MetricCard {...metric} loading={loading} />
        </Grid>
      ))}
      
      {/* Summary Box */}
      <Grid item xs={12}>
        <Paper sx={{ p: 3, bgcolor: 'primary.main', color: 'primary.contrastText' }}>
          <Typography variant="h6" gutterBottom>
            📊 培訓概況摘要
          </Typography>
          <Typography variant="body1">
            {data?.summary || `本月共有 ${data?.active_users || 0} 位活躍學員，累計學習 ${data?.total_learning_hours || 0} 小時，完成 ${data?.courses_completed || 0} 門課程。整體學習參與度較上月${(data?.active_users_change || 0) > 0 ? '提升' : '下降'} ${Math.abs(data?.active_users_change || 0)}%。`}
          </Typography>
        </Paper>
      </Grid>
    </Grid>
  );
}