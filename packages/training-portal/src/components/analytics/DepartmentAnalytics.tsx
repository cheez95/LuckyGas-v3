import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Chip,
  Avatar,
  Card,
  CardContent,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  Business,
  Warehouse,
  LocalShipping,
  SupportAgent,
  Build,
  EmojiEvents,
  TrendingUp,
  Info,
} from '@mui/icons-material';

interface DepartmentAnalyticsProps {
  data: any;
  loading?: boolean;
}

const DEPARTMENT_ICONS: Record<string, React.ReactNode> = {
  office: <Business />,
  warehouse: <Warehouse />,
  delivery: <LocalShipping />,
  customer_service: <SupportAgent />,
  maintenance: <Build />,
};

const DEPARTMENT_NAMES: Record<string, string> = {
  office: '辦公室',
  warehouse: '倉儲部',
  delivery: '配送部',
  customer_service: '客服部',
  maintenance: '維修部',
};

const COLORS = ['#FF6B35', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'];

export function DepartmentAnalytics({ data, loading = false }: DepartmentAnalyticsProps) {
  const [selectedMetric, setSelectedMetric] = useState<string>('learning_hours');

  if (loading || !data) {
    return (
      <Box>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>載入中...</Typography>
      </Box>
    );
  }

  // Prepare radar chart data
  const radarData = data.departments.map((dept: any) => ({
    department: DEPARTMENT_NAMES[dept.department],
    參與率: dept.participation_rate,
    完成率: dept.avg_completion_rate,
    測驗通過率: dept.quiz_pass_rate,
    活躍度: (dept.active_users / dept.total_users * 100) || 0,
    學習時數: Math.min(100, (dept.learning_hours / 100) * 100), // Normalize to 100
  }));

  // Prepare comparison data
  const comparisonData = data.departments.map((dept: any) => ({
    name: DEPARTMENT_NAMES[dept.department],
    ...dept,
  }));

  const getMetricLabel = (metric: string) => {
    const labels: Record<string, string> = {
      learning_hours: '學習時數',
      courses_completed: '完成課程數',
      participation_rate: '參與率',
      avg_completion_rate: '平均完成率',
      quiz_pass_rate: '測驗通過率',
      achievements: '獲得成就',
    };
    return labels[metric] || metric;
  };

  const topDepartment = data.departments[0];

  return (
    <Box>
      {/* Summary Card */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card sx={{ bgcolor: 'primary.main', color: 'primary.contrastText' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <EmojiEvents sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h5">
                    本月最佳部門：{DEPARTMENT_NAMES[topDepartment.department]}
                  </Typography>
                  <Typography variant="body1">
                    總學習時數 {topDepartment.learning_hours} 小時 · 
                    參與率 {topDepartment.participation_rate.toFixed(1)}% · 
                    {topDepartment.courses_completed} 門課程完成
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Department Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {data.departments.map((dept: any, index: number) => (
          <Grid item xs={12} sm={6} md={4} lg={2.4} key={dept.department}>
            <Card 
              sx={{ 
                height: '100%',
                position: 'relative',
                overflow: 'visible',
              }}
            >
              {index === 0 && (
                <Chip
                  label="冠軍"
                  color="primary"
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: -10,
                    right: 10,
                    zIndex: 1,
                  }}
                />
              )}
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar sx={{ bgcolor: COLORS[index % COLORS.length], mr: 2 }}>
                    {DEPARTMENT_ICONS[dept.department]}
                  </Avatar>
                  <Typography variant="h6">
                    {DEPARTMENT_NAMES[dept.department]}
                  </Typography>
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    參與率
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography variant="h5">
                      {dept.participation_rate.toFixed(1)}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                      ({dept.active_users}/{dept.total_users})
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={dept.participation_rate} 
                    sx={{ mt: 1 }}
                  />
                </Box>
                
                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      學習時數
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {dept.learning_hours}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      完成課程
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {dept.courses_completed}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      測驗通過率
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {dept.quiz_pass_rate.toFixed(1)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      成就獲得
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {dept.achievements}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Radar Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              部門能力雷達圖
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="department" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                {Object.keys(radarData[0])
                  .filter(key => key !== 'department')
                  .map((key, index) => (
                    <Radar
                      key={key}
                      name={key}
                      dataKey={key}
                      stroke={COLORS[index % COLORS.length]}
                      fill={COLORS[index % COLORS.length]}
                      fillOpacity={0.3}
                    />
                  ))}
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Comparison Bar Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                部門比較 - {getMetricLabel(selectedMetric)}
              </Typography>
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid #ccc',
                }}
              >
                <option value="learning_hours">學習時數</option>
                <option value="courses_completed">完成課程數</option>
                <option value="participation_rate">參與率</option>
                <option value="avg_completion_rate">平均完成率</option>
                <option value="quiz_pass_rate">測驗通過率</option>
                <option value="achievements">獲得成就</option>
              </select>
            </Box>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <ChartTooltip />
                <Bar dataKey={selectedMetric} fill="#FF6B35">
                  {comparisonData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Department Trends */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              部門學習趨勢
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <ChartTooltip />
                <Legend />
                {data.departments.map((dept: any, index: number) => (
                  <Line
                    key={dept.department}
                    type="monotone"
                    dataKey={dept.department}
                    name={DEPARTMENT_NAMES[dept.department]}
                    stroke={COLORS[index % COLORS.length]}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Detailed Table */}
        <Grid item xs={12}>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>部門</TableCell>
                  <TableCell align="right">總人數</TableCell>
                  <TableCell align="right">活躍用戶</TableCell>
                  <TableCell align="right">參與率</TableCell>
                  <TableCell align="right">學習時數</TableCell>
                  <TableCell align="right">完成課程</TableCell>
                  <TableCell align="right">平均完成率</TableCell>
                  <TableCell align="right">測驗通過率</TableCell>
                  <TableCell align="right">成就數</TableCell>
                  <TableCell align="center">狀態</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.departments.map((dept: any, index: number) => (
                  <TableRow key={dept.department} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Avatar 
                          sx={{ 
                            bgcolor: COLORS[index % COLORS.length], 
                            width: 32, 
                            height: 32,
                            mr: 1,
                          }}
                        >
                          {DEPARTMENT_ICONS[dept.department]}
                        </Avatar>
                        {DEPARTMENT_NAMES[dept.department]}
                      </Box>
                    </TableCell>
                    <TableCell align="right">{dept.total_users}</TableCell>
                    <TableCell align="right">{dept.active_users}</TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={dept.participation_rate} 
                          sx={{ width: 60, mr: 1 }}
                        />
                        {dept.participation_rate.toFixed(1)}%
                      </Box>
                    </TableCell>
                    <TableCell align="right">{dept.learning_hours} 小時</TableCell>
                    <TableCell align="right">{dept.courses_completed}</TableCell>
                    <TableCell align="right">{dept.avg_completion_rate.toFixed(1)}%</TableCell>
                    <TableCell align="right">{dept.quiz_pass_rate.toFixed(1)}%</TableCell>
                    <TableCell align="right">{dept.achievements}</TableCell>
                    <TableCell align="center">
                      {dept.participation_rate > 80 ? (
                        <Chip label="優秀" color="success" size="small" />
                      ) : dept.participation_rate > 60 ? (
                        <Chip label="良好" color="warning" size="small" />
                      ) : (
                        <Chip label="待改善" color="error" size="small" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>
    </Box>
  );
}