import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Users, BookOpen, Clock, Trophy, TrendingUp, Download,
  Calendar, Filter, RefreshCw
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { TrainingService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

export default function AnalyticsDashboard() {
  const { user } = useAuth();
  const [dateRange, setDateRange] = useState(30);
  const [department, setDepartment] = useState(user?.department || 'all');
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch dashboard metrics
  const { data: metrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ['analytics-metrics', department],
    queryFn: () => TrainingService.getAnalytics({
      department: department === 'all' ? undefined : department
    }),
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch trends data
  const { data: trends, isLoading: trendsLoading } = useQuery({
    queryKey: ['analytics-trends', dateRange, department],
    queryFn: () => TrainingService.getLearningTrends({
      days: dateRange,
      department: department === 'all' ? undefined : department
    }),
  });

  // Fetch department analytics
  const { data: deptAnalytics, isLoading: deptLoading } = useQuery({
    queryKey: ['department-analytics', department],
    queryFn: () => TrainingService.getDepartmentAnalytics(department),
    enabled: department !== 'all',
  });

  // Fetch recommendations
  const { data: recommendations } = useQuery({
    queryKey: ['training-recommendations'],
    queryFn: () => TrainingService.getTrainingRecommendations(),
    enabled: user?.roles?.includes('admin') || user?.roles?.includes('training_manager'),
  });

  const handleExportReport = async (reportType: string) => {
    try {
      const blob = await TrainingService.generateReport({
        type: reportType,
        department: department === 'all' ? undefined : department,
        startDate: new Date(Date.now() - dateRange * 24 * 60 * 60 * 1000),
        endDate: new Date(),
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `training_report_${reportType}_${format(new Date(), 'yyyyMMdd')}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export report:', error);
    }
  };

  // Prepare chart data
  const enrollmentChartData = trends ? Object.entries(trends.enrollments_by_date).map(([date, count]) => ({
    date: format(new Date(date), 'MM/dd', { locale: zhTW }),
    enrollments: count,
    completions: trends.completions_by_date[date] || 0,
  })) : [];

  const activeUsersChartData = trends ? Object.entries(trends.active_users_by_date).map(([date, count]) => ({
    date: format(new Date(date), 'MM/dd', { locale: zhTW }),
    activeUsers: count,
  })) : [];

  const categoryData = deptAnalytics ? Object.entries(deptAnalytics.category_completion).map(([category, stats]: [string, any]) => ({
    name: category,
    value: stats.completions,
    completion_rate: stats.completion_rate,
  })) : [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">培訓數據分析</h1>
              <p className="mt-2 text-gray-600">追蹤學習成效與培訓進度</p>
            </div>
            <Button
              onClick={() => refetchMetrics()}
              variant="outline"
              className="flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              更新數據
            </Button>
          </div>

          {/* Filters */}
          <div className="mt-6 flex flex-wrap gap-4">
            <Select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-48"
            >
              <option value="all">所有部門</option>
              <option value="office">辦公室</option>
              <option value="delivery">配送</option>
              <option value="management">管理</option>
            </Select>

            <Select
              value={dateRange.toString()}
              onChange={(e) => setDateRange(parseInt(e.target.value))}
              className="w-48"
            >
              <option value="7">過去 7 天</option>
              <option value="30">過去 30 天</option>
              <option value="90">過去 90 天</option>
              <option value="365">過去一年</option>
            </Select>

            <div className="ml-auto flex gap-2">
              <Button
                variant="outline"
                onClick={() => handleExportReport('user_progress')}
              >
                <Download className="w-4 h-4 mr-2" />
                匯出用戶進度
              </Button>
              <Button
                variant="outline"
                onClick={() => handleExportReport('course_completion')}
              >
                <Download className="w-4 h-4 mr-2" />
                匯出課程完成
              </Button>
            </div>
          </div>
        </div>

        {/* Metrics Cards */}
        {metricsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <Card key={i} className="p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-16"></div>
              </Card>
            ))}
          </div>
        ) : metrics ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <MetricCard
              title="活躍學習者"
              value={metrics.active_learners}
              total={metrics.total_users}
              icon={<Users className="w-6 h-6 text-blue-600" />}
              trend={`${metrics.engagement_rate.toFixed(1)}% 參與率`}
              color="blue"
            />
            <MetricCard
              title="平均完成率"
              value={`${metrics.average_completion_rate.toFixed(1)}%`}
              icon={<BookOpen className="w-6 h-6 text-green-600" />}
              trend={`${metrics.total_completions} 完成`}
              color="green"
            />
            <MetricCard
              title="總學習時數"
              value={`${metrics.total_learning_hours}`}
              icon={<Clock className="w-6 h-6 text-orange-600" />}
              trend="小時"
              color="orange"
            />
            <MetricCard
              title="總課程數"
              value={metrics.total_courses}
              icon={<Trophy className="w-6 h-6 text-purple-600" />}
              trend="可用課程"
              color="purple"
            />
          </div>
        ) : null}

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="overview">總覽</TabsTrigger>
            <TabsTrigger value="trends">趨勢分析</TabsTrigger>
            <TabsTrigger value="performance">成效分析</TabsTrigger>
            {(user?.roles?.includes('admin') || user?.roles?.includes('training_manager')) && (
              <TabsTrigger value="insights">洞察建議</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Enrollment Trends */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">註冊與完成趨勢</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={enrollmentChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="enrollments"
                      stroke="#3B82F6"
                      name="註冊"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="completions"
                      stroke="#10B981"
                      name="完成"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Card>

              {/* Active Users */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">活躍用戶</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={activeUsersChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="activeUsers" fill="#8B5CF6" name="活躍用戶" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              {/* Popular Courses */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">熱門課程</h3>
                <div className="space-y-3">
                  {trends?.popular_courses.map((course, index) => (
                    <div key={course.course_id} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-gray-400">
                          {index + 1}
                        </span>
                        <span className="text-sm font-medium">{course.title}</span>
                      </div>
                      <span className="text-sm text-gray-600">
                        {course.enrollments} 人註冊
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Category Distribution */}
              {categoryData.length > 0 && (
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">課程類別分布</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {categoryData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>
              )}
            </div>
          </TabsContent>

          <TabsContent value="trends">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">學習趨勢分析</h3>
              {/* Add more detailed trend analysis */}
              <p className="text-gray-600">詳細趨勢分析開發中...</p>
            </Card>
          </TabsContent>

          <TabsContent value="performance">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">成效分析</h3>
              {deptAnalytics && (
                <div className="space-y-6">
                  {/* Top Performers */}
                  <div>
                    <h4 className="font-medium mb-3">表現優異學員</h4>
                    <div className="space-y-2">
                      {deptAnalytics.top_performers.map((performer: any, index: number) => (
                        <div key={performer.user_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <span className="text-lg font-bold text-gray-400">
                              #{index + 1}
                            </span>
                            <span className="font-medium">{performer.name}</span>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium">{performer.points} 積分</div>
                            <div className="text-xs text-gray-600">{performer.completed_courses} 課程完成</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Compliance Status */}
                  {deptAnalytics.compliance_status && (
                    <div>
                      <h4 className="font-medium mb-3">必修課程合規狀態</h4>
                      <div className="mb-4">
                        <div className="flex justify-between text-sm mb-1">
                          <span>整體合規率</span>
                          <span className="font-medium">
                            {deptAnalytics.compliance_status.overall_compliance_rate.toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full"
                            style={{ width: `${deptAnalytics.compliance_status.overall_compliance_rate}%` }}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        {deptAnalytics.compliance_status.required_courses.map((course: any) => (
                          <div key={course.course_id} className="flex justify-between text-sm">
                            <span>{course.title}</span>
                            <span className={course.compliance_rate >= 80 ? "text-green-600" : "text-red-600"}>
                              {course.compliance_rate.toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="insights">
            {recommendations && (
              <div className="space-y-6">
                {/* Recommendations */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">建議事項</h3>
                  <div className="space-y-4">
                    {recommendations.recommendations.map((rec: any, index: number) => (
                      <Card key={index} className={`p-4 border-l-4 ${
                        rec.priority === 'high' ? 'border-l-red-500' :
                        rec.priority === 'medium' ? 'border-l-yellow-500' :
                        'border-l-blue-500'
                      }`}>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium">{rec.title}</h4>
                            <p className="text-sm text-gray-600 mt-1">{rec.description}</p>
                            <div className="mt-3">
                              <p className="text-sm font-medium mb-1">建議行動：</p>
                              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                                {rec.actions.map((action: string, i: number) => (
                                  <li key={i}>{action}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            rec.priority === 'high' ? 'bg-red-100 text-red-600' :
                            rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-600' :
                            'bg-blue-100 text-blue-600'
                          }`}>
                            {rec.priority === 'high' ? '高' :
                             rec.priority === 'medium' ? '中' : '低'}優先級
                          </span>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>

                {/* Insights */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">深入洞察</h3>
                  <Card className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-medium mb-3">熱門學習主題</h4>
                        <div className="space-y-2">
                          {recommendations.insights.popular_topics.slice(0, 5).map((topic: any, index: number) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span>{topic.title}</span>
                              <span className="text-gray-600">{topic.enrollments} 人</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function MetricCard({ title, value, total, icon, trend, color }: any) {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg bg-${color}-50`}>
          {icon}
        </div>
        {trend && (
          <span className="text-sm text-gray-600">{trend}</span>
        )}
      </div>
      <div>
        <p className="text-sm text-gray-600">{title}</p>
        <p className="text-2xl font-bold">
          {value}
          {total && (
            <span className="text-sm font-normal text-gray-600">
              {' '}/ {total}
            </span>
          )}
        </p>
      </div>
    </Card>
  );
}