import React, { useState, useMemo } from 'react';
import { Grid, Paper, Box, Typography, Tab, Tabs, Select, MenuItem, FormControl, InputLabel, IconButton, Tooltip } from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { zhTW } from 'date-fns/locale';
import { startOfMonth, endOfMonth, subMonths, format } from 'date-fns';
import { 
  TrendingUp, 
  People, 
  School, 
  Timer, 
  EmojiEvents,
  Download,
  Refresh,
  FilterList
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';

import { analyticsService } from '@/services/analytics';
import { OverviewMetrics } from './OverviewMetrics';
import { CourseAnalytics } from './CourseAnalytics';
import { UserEngagement } from './UserEngagement';
import { DepartmentAnalytics } from './DepartmentAnalytics';
import { CompletionRates } from './CompletionRates';
import { LearningPathAnalytics } from './LearningPathAnalytics';
import { QuizPerformance } from './QuizPerformance';
import { TimeAnalytics } from './TimeAnalytics';
import { ExportDialog } from './ExportDialog';
import { useAuth } from '@/contexts/AuthContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export function AnalyticsDashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(0);
  const [dateRange, setDateRange] = useState({
    start: startOfMonth(subMonths(new Date(), 1)),
    end: endOfMonth(new Date()),
  });
  const [department, setDepartment] = useState<string>('all');
  const [showExportDialog, setShowExportDialog] = useState(false);

  // Fetch analytics data
  const { data: overview, isLoading: overviewLoading, refetch: refetchOverview } = useQuery({
    queryKey: ['analytics-overview', dateRange, department],
    queryFn: () => analyticsService.getOverviewMetrics({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const { data: courseData, isLoading: courseLoading } = useQuery({
    queryKey: ['analytics-courses', dateRange, department],
    queryFn: () => analyticsService.getCourseAnalytics({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const { data: userEngagement, isLoading: engagementLoading } = useQuery({
    queryKey: ['analytics-engagement', dateRange, department],
    queryFn: () => analyticsService.getUserEngagement({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const { data: departmentData, isLoading: deptLoading } = useQuery({
    queryKey: ['analytics-departments', dateRange],
    queryFn: () => analyticsService.getDepartmentAnalytics({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
    }),
    enabled: department === 'all',
  });

  const { data: completionData, isLoading: completionLoading } = useQuery({
    queryKey: ['analytics-completion', dateRange, department],
    queryFn: () => analyticsService.getCompletionRates({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const { data: learningPaths, isLoading: pathsLoading } = useQuery({
    queryKey: ['analytics-paths', dateRange, department],
    queryFn: () => analyticsService.getLearningPathAnalytics({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const { data: quizData, isLoading: quizLoading } = useQuery({
    queryKey: ['analytics-quiz', dateRange, department],
    queryFn: () => analyticsService.getQuizPerformance({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const { data: timeData, isLoading: timeLoading } = useQuery({
    queryKey: ['analytics-time', dateRange, department],
    queryFn: () => analyticsService.getTimeAnalytics({
      start_date: format(dateRange.start, 'yyyy-MM-dd'),
      end_date: format(dateRange.end, 'yyyy-MM-dd'),
      department: department !== 'all' ? department : undefined,
    }),
  });

  const handleRefresh = () => {
    refetchOverview();
  };

  const handleExport = async (exportConfig: any) => {
    try {
      const data = await analyticsService.exportAnalytics({
        ...exportConfig,
        start_date: format(dateRange.start, 'yyyy-MM-dd'),
        end_date: format(dateRange.end, 'yyyy-MM-dd'),
        department: department !== 'all' ? department : undefined,
      });
      
      // Download the file
      const blob = new Blob([data], { type: exportConfig.format === 'csv' ? 'text/csv' : 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_${format(new Date(), 'yyyyMMdd_HHmmss')}.${exportConfig.format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const isLoading = overviewLoading || courseLoading || engagementLoading || 
                   deptLoading || completionLoading || pathsLoading || 
                   quizLoading || timeLoading;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={zhTW}>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4" component="h1">
            培訓數據分析
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Tooltip title="重新整理">
              <IconButton onClick={handleRefresh} disabled={isLoading}>
                <Refresh />
              </IconButton>
            </Tooltip>
            
            <Tooltip title="匯出報表">
              <IconButton onClick={() => setShowExportDialog(true)}>
                <Download />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Filters */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={3}>
              <DatePicker
                label="開始日期"
                value={dateRange.start}
                onChange={(date) => date && setDateRange({ ...dateRange, start: date })}
                slotProps={{ textField: { fullWidth: true, size: 'small' } }}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <DatePicker
                label="結束日期"
                value={dateRange.end}
                onChange={(date) => date && setDateRange({ ...dateRange, end: date })}
                slotProps={{ textField: { fullWidth: true, size: 'small' } }}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>部門</InputLabel>
                <Select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  label="部門"
                >
                  <MenuItem value="all">全部部門</MenuItem>
                  <MenuItem value="office">辦公室</MenuItem>
                  <MenuItem value="warehouse">倉儲部</MenuItem>
                  <MenuItem value="delivery">配送部</MenuItem>
                  <MenuItem value="customer_service">客服部</MenuItem>
                  <MenuItem value="maintenance">維修部</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <FilterList />
                <Typography variant="body2" color="text.secondary">
                  {format(dateRange.start, 'yyyy/MM/dd')} - {format(dateRange.end, 'yyyy/MM/dd')}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        {/* Overview Metrics */}
        {overview && <OverviewMetrics data={overview} loading={overviewLoading} />}

        {/* Tabs */}
        <Paper sx={{ mt: 3 }}>
          <Tabs
            value={activeTab}
            onChange={(e, v) => setActiveTab(v)}
            indicatorColor="primary"
            textColor="primary"
            variant="scrollable"
            scrollButtons="auto"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="課程分析" icon={<School />} iconPosition="start" />
            <Tab label="用戶參與度" icon={<People />} iconPosition="start" />
            <Tab label="完成率" icon={<TrendingUp />} iconPosition="start" />
            <Tab label="測驗成績" icon={<EmojiEvents />} iconPosition="start" />
            <Tab label="學習時間" icon={<Timer />} iconPosition="start" />
            {department === 'all' && <Tab label="部門比較" icon={<People />} iconPosition="start" />}
            <Tab label="學習路徑" icon={<School />} iconPosition="start" />
          </Tabs>

          <Box sx={{ p: 3 }}>
            <TabPanel value={activeTab} index={0}>
              {courseData && <CourseAnalytics data={courseData} loading={courseLoading} />}
            </TabPanel>
            
            <TabPanel value={activeTab} index={1}>
              {userEngagement && <UserEngagement data={userEngagement} loading={engagementLoading} />}
            </TabPanel>
            
            <TabPanel value={activeTab} index={2}>
              {completionData && <CompletionRates data={completionData} loading={completionLoading} />}
            </TabPanel>
            
            <TabPanel value={activeTab} index={3}>
              {quizData && <QuizPerformance data={quizData} loading={quizLoading} />}
            </TabPanel>
            
            <TabPanel value={activeTab} index={4}>
              {timeData && <TimeAnalytics data={timeData} loading={timeLoading} />}
            </TabPanel>
            
            {department === 'all' && (
              <TabPanel value={activeTab} index={5}>
                {departmentData && <DepartmentAnalytics data={departmentData} loading={deptLoading} />}
              </TabPanel>
            )}
            
            <TabPanel value={activeTab} index={department === 'all' ? 6 : 5}>
              {learningPaths && <LearningPathAnalytics data={learningPaths} loading={pathsLoading} />}
            </TabPanel>
          </Box>
        </Paper>

        {/* Export Dialog */}
        <ExportDialog
          open={showExportDialog}
          onClose={() => setShowExportDialog(false)}
          onExport={handleExport}
        />
      </Box>
    </LocalizationProvider>
  );
}