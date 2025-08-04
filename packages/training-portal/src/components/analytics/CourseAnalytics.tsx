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
  TableSortLabel,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { Info, TrendingUp, TrendingDown } from '@mui/icons-material';

interface CourseAnalyticsProps {
  data: any;
  loading?: boolean;
}

const COLORS = ['#FF6B35', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'];

export function CourseAnalytics({ data, loading = false }: CourseAnalyticsProps) {
  const [sortBy, setSortBy] = useState<string>('enrollments');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('chart');
  const [chartType, setChartType] = useState<'bar' | 'pie' | 'radar'>('bar');

  if (loading || !data) {
    return (
      <Box>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>載入中...</Typography>
      </Box>
    );
  }

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const sortedCourses = [...(data.courses || [])].sort((a, b) => {
    const aValue = a[sortBy] || 0;
    const bValue = b[sortBy] || 0;
    return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
  });

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'success';
      case 'intermediate': return 'warning';
      case 'advanced': return 'error';
      default: return 'default';
    }
  };

  const getDifficultyLabel = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return '初級';
      case 'intermediate': return '中級';
      case 'advanced': return '高級';
      default: return difficulty;
    }
  };

  // Prepare chart data
  const chartData = data.courses?.slice(0, 10).map((course: any) => ({
    name: course.title_zh,
    enrollments: course.enrollments,
    completions: course.completions,
    completion_rate: course.completion_rate,
    avg_score: course.avg_score,
    avg_time: course.avg_time_hours,
  }));

  const radarData = data.difficulty_distribution?.map((item: any) => ({
    difficulty: getDifficultyLabel(item.difficulty),
    courses: item.count,
    enrollments: item.enrollments,
    completion_rate: item.avg_completion_rate,
  }));

  return (
    <Box>
      {/* Controls */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(e, v) => v && setViewMode(v)}
          size="small"
        >
          <ToggleButton value="chart">圖表</ToggleButton>
          <ToggleButton value="table">表格</ToggleButton>
        </ToggleButtonGroup>

        {viewMode === 'chart' && (
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>圖表類型</InputLabel>
            <Select
              value={chartType}
              onChange={(e) => setChartType(e.target.value as any)}
              label="圖表類型"
            >
              <MenuItem value="bar">長條圖</MenuItem>
              <MenuItem value="pie">圓餅圖</MenuItem>
              <MenuItem value="radar">雷達圖</MenuItem>
            </Select>
          </FormControl>
        )}
      </Box>

      {viewMode === 'chart' ? (
        <Grid container spacing={3}>
          {/* Main Chart */}
          <Grid item xs={12} lg={8}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                熱門課程分析
              </Typography>
              
              {chartType === 'bar' && (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                    <YAxis />
                    <ChartTooltip />
                    <Legend />
                    <Bar dataKey="enrollments" fill="#FF6B35" name="報名人數" />
                    <Bar dataKey="completions" fill="#4ECDC4" name="完成人數" />
                  </BarChart>
                </ResponsiveContainer>
              )}
              
              {chartType === 'pie' && (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.category_distribution}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.category}: ${entry.percentage}%`}
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="count"
                    >
                      {data.category_distribution?.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <ChartTooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
              
              {chartType === 'radar' && (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="difficulty" />
                    <PolarRadiusAxis />
                    <Radar name="課程數" dataKey="courses" stroke="#FF6B35" fill="#FF6B35" fillOpacity={0.6} />
                    <Radar name="報名數" dataKey="enrollments" stroke="#4ECDC4" fill="#4ECDC4" fillOpacity={0.6} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              )}
            </Paper>
          </Grid>

          {/* Side Stats */}
          <Grid item xs={12} lg={4}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    總課程數
                  </Typography>
                  <Typography variant="h4">
                    {data.total_courses}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    {data.courses_change > 0 ? (
                      <TrendingUp color="success" sx={{ mr: 1 }} />
                    ) : (
                      <TrendingDown color="error" sx={{ mr: 1 }} />
                    )}
                    <Typography variant="body2" color={data.courses_change > 0 ? 'success.main' : 'error.main'}>
                      {data.courses_change > 0 ? '+' : ''}{data.courses_change}% vs 上月
                    </Typography>
                  </Box>
                </Paper>
              </Grid>

              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    平均完成率
                  </Typography>
                  <Typography variant="h4">
                    {data.avg_completion_rate?.toFixed(1)}%
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={data.avg_completion_rate} 
                    sx={{ mt: 2, height: 8, borderRadius: 1 }}
                  />
                </Paper>
              </Grid>

              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    課程類別分布
                  </Typography>
                  {data.category_distribution?.slice(0, 5).map((cat: any) => (
                    <Box key={cat.category} sx={{ mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2">{cat.category}</Typography>
                        <Typography variant="body2">{cat.percentage}%</Typography>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={cat.percentage} 
                        sx={{ height: 4, borderRadius: 1 }}
                      />
                    </Box>
                  ))}
                </Paper>
              </Grid>
            </Grid>
          </Grid>

          {/* Trend Chart */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3, height: 300 }}>
              <Typography variant="h6" gutterBottom>
                報名趨勢
              </Typography>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.enrollment_trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <ChartTooltip />
                  <Area type="monotone" dataKey="enrollments" stroke="#FF6B35" fill="#FF6B35" fillOpacity={0.3} />
                  <Area type="monotone" dataKey="completions" stroke="#4ECDC4" fill="#4ECDC4" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      ) : (
        /* Table View */
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortBy === 'title_zh'}
                    direction={sortBy === 'title_zh' ? sortOrder : 'asc'}
                    onClick={() => handleSort('title_zh')}
                  >
                    課程名稱
                  </TableSortLabel>
                </TableCell>
                <TableCell>難度</TableCell>
                <TableCell>類別</TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortBy === 'enrollments'}
                    direction={sortBy === 'enrollments' ? sortOrder : 'asc'}
                    onClick={() => handleSort('enrollments')}
                  >
                    報名數
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortBy === 'completions'}
                    direction={sortBy === 'completions' ? sortOrder : 'asc'}
                    onClick={() => handleSort('completions')}
                  >
                    完成數
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortBy === 'completion_rate'}
                    direction={sortBy === 'completion_rate' ? sortOrder : 'asc'}
                    onClick={() => handleSort('completion_rate')}
                  >
                    完成率
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortBy === 'avg_score'}
                    direction={sortBy === 'avg_score' ? sortOrder : 'asc'}
                    onClick={() => handleSort('avg_score')}
                  >
                    平均分數
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={sortBy === 'avg_time_hours'}
                    direction={sortBy === 'avg_time_hours' ? sortOrder : 'asc'}
                    onClick={() => handleSort('avg_time_hours')}
                  >
                    平均時長
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">狀態</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedCourses.map((course: any) => (
                <TableRow key={course.course_id} hover>
                  <TableCell>{course.title_zh}</TableCell>
                  <TableCell>
                    <Chip 
                      label={getDifficultyLabel(course.difficulty)} 
                      color={getDifficultyColor(course.difficulty)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{course.category}</TableCell>
                  <TableCell align="right">{course.enrollments}</TableCell>
                  <TableCell align="right">{course.completions}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={course.completion_rate} 
                        sx={{ width: 60, mr: 1 }}
                      />
                      {course.completion_rate.toFixed(1)}%
                    </Box>
                  </TableCell>
                  <TableCell align="right">{course.avg_score?.toFixed(1) || '-'}</TableCell>
                  <TableCell align="right">{course.avg_time_hours?.toFixed(1) || '-'} 小時</TableCell>
                  <TableCell align="center">
                    {course.is_active ? (
                      <Chip label="啟用" color="success" size="small" />
                    ) : (
                      <Chip label="停用" color="default" size="small" />
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}