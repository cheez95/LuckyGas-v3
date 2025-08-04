import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  LinearProgress,
  Tab,
  Tabs,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Treemap,
} from 'recharts';
import {
  TrendingUp,
  AccessTime,
  EmojiEvents,
  School,
  People,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

interface UserEngagementProps {
  data: any;
  loading?: boolean;
}

const COLORS = ['#FF6B35', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'];

export function UserEngagement({ data, loading = false }: UserEngagementProps) {
  const [timeRange, setTimeRange] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [activeTab, setActiveTab] = useState(0);

  if (loading || !data) {
    return (
      <Box>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>載入中...</Typography>
      </Box>
    );
  }

  // Format engagement data based on time range
  const getEngagementData = () => {
    switch (timeRange) {
      case 'daily':
        return data.daily_engagement;
      case 'weekly':
        return data.weekly_engagement;
      case 'monthly':
        return data.monthly_engagement;
      default:
        return data.daily_engagement;
    }
  };

  const engagementData = getEngagementData();

  // Custom label for treemap
  const CustomizedContent = (props: any) => {
    const { x, y, width, height, name, value } = props;
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          style={{
            fill: COLORS[Math.floor(Math.random() * COLORS.length)],
            stroke: '#fff',
            strokeWidth: 2,
            strokeOpacity: 1,
          }}
        />
        <text
          x={x + width / 2}
          y={y + height / 2}
          fill="#fff"
          textAnchor="middle"
          dominantBaseline="central"
        >
          <tspan fontSize="14" fontWeight="bold">{name}</tspan>
          <tspan x={x + width / 2} y={y + height / 2 + 20} fontSize="12">
            {value} 小時
          </tspan>
        </text>
      </g>
    );
  };

  return (
    <Box>
      {/* Controls */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">用戶參與度分析</Typography>
        <ToggleButtonGroup
          value={timeRange}
          exclusive
          onChange={(e, v) => v && setTimeRange(v)}
          size="small"
        >
          <ToggleButton value="daily">每日</ToggleButton>
          <ToggleButton value="weekly">每週</ToggleButton>
          <ToggleButton value="monthly">每月</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <People color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  日活躍用戶
                </Typography>
              </Box>
              <Typography variant="h4">{data.daily_active_users}</Typography>
              <Typography variant="body2" color="success.main">
                +{data.dau_change}% vs 昨日
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <AccessTime color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  平均學習時長
                </Typography>
              </Box>
              <Typography variant="h4">{data.avg_session_duration} 分鐘</Typography>
              <Typography variant="body2" color="text.secondary">
                每次登入
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <School color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  參與率
                </Typography>
              </Box>
              <Typography variant="h4">{data.engagement_rate}%</Typography>
              <LinearProgress 
                variant="determinate" 
                value={data.engagement_rate} 
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <EmojiEvents color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  活躍度分數
                </Typography>
              </Box>
              <Typography variant="h4">{data.activity_score}/100</Typography>
              <Chip 
                label={data.activity_level} 
                color={data.activity_score > 80 ? 'success' : data.activity_score > 50 ? 'warning' : 'error'}
                size="small"
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="活躍度趨勢" />
          <Tab label="用戶分布" />
          <Tab label="學習模式" />
          <Tab label="排行榜" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                用戶活躍度趨勢
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={engagementData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Line 
                    yAxisId="left"
                    type="monotone" 
                    dataKey="active_users" 
                    stroke="#FF6B35" 
                    name="活躍用戶"
                    strokeWidth={2}
                  />
                  <Line 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="avg_duration" 
                    stroke="#4ECDC4" 
                    name="平均時長(分)"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: 300 }}>
              <Typography variant="h6" gutterBottom>
                登入時段分布
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.hourly_distribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" />
                  <YAxis />
                  <Tooltip />
                  <Area 
                    type="monotone" 
                    dataKey="logins" 
                    stroke="#45B7D1" 
                    fill="#45B7D1" 
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: 300 }}>
              <Typography variant="h6" gutterBottom>
                裝置使用分布
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.device_distribution}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label
                  >
                    {data.device_distribution?.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                部門學習時數分布
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <Treemap
                  data={data.department_hours}
                  dataKey="hours"
                  aspectRatio={4 / 3}
                  stroke="#fff"
                  content={<CustomizedContent />}
                />
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                活躍度分級
              </Typography>
              <List>
                {data.activity_levels?.map((level: any) => (
                  <ListItem key={level.level}>
                    <ListItemText
                      primary={level.level}
                      secondary={`${level.count} 位用戶`}
                    />
                    <Box sx={{ minWidth: 100 }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={(level.count / data.total_users) * 100} 
                        color={
                          level.level === '高度活躍' ? 'success' :
                          level.level === '中度活躍' ? 'warning' : 'error'
                        }
                      />
                    </Box>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        </Grid>
      )}

      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                學習模式分析
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="learning_hours" name="學習時數" />
                  <YAxis dataKey="courses_completed" name="完成課程數" />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                  <Scatter 
                    name="用戶" 
                    data={data.user_patterns} 
                    fill="#FF6B35"
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                學習偏好
              </Typography>
              <List>
                {data.learning_preferences?.map((pref: any) => (
                  <ListItem key={pref.type}>
                    <ListItemText
                      primary={pref.type}
                      secondary={`${pref.percentage}% 用戶偏好`}
                    />
                    <Chip label={`${pref.count} 人`} size="small" />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                完成率分布
              </Typography>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={data.completion_distribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="range" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#4ECDC4" />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      )}

      {activeTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                本月學習冠軍
              </Typography>
              <List>
                {data.top_learners?.map((user: any, index: number) => (
                  <ListItem key={user.user_id}>
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: COLORS[index] }}>
                        {index + 1}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={user.name}
                      secondary={`${user.department} · ${user.learning_hours} 小時`}
                    />
                    <Chip 
                      label={`${user.courses_completed} 門課程`} 
                      size="small"
                      color={index === 0 ? 'primary' : 'default'}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                成就達人
              </Typography>
              <List>
                {data.achievement_leaders?.map((user: any, index: number) => (
                  <ListItem key={user.user_id}>
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: COLORS[index] }}>
                        <EmojiEvents />
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={user.name}
                      secondary={`${user.achievements} 個成就`}
                    />
                    <Typography variant="h6" color="primary">
                      {user.points} 點
                    </Typography>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}