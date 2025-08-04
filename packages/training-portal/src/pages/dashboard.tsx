import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useAuth, useRequireAuth } from '@/hooks/useAuth';
import { 
  BookOpen, 
  Clock, 
  Trophy, 
  TrendingUp,
  Calendar,
  Target,
  Award,
  Users,
  ChevronRight,
  Flame
} from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';
import { Progress } from '@/components/ui/Progress';
import { Card } from '@/components/ui/Card';
import { CourseCard } from '@/components/course/CourseCard';
import { AchievementBadge } from '@/components/achievement/AchievementBadge';
import Head from 'next/head';

export default function Dashboard() {
  const isAuthenticated = useRequireAuth();
  const { user } = useAuth();
  
  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.getDashboard(),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="space-y-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-gray-500">載入中...</p>
        </div>
      </div>
    );
  }

  const stats = [
    {
      title: '總學習時數',
      value: `${dashboardData?.profile.totalLearningHours || 0}`,
      unit: '小時',
      icon: Clock,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: '完成課程',
      value: `${dashboardData?.profile.completedCourses || 0}`,
      unit: '門',
      icon: BookOpen,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: '獲得證書',
      value: `${dashboardData?.profile.certificatesEarned || 0}`,
      unit: '張',
      icon: Award,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      title: '學習積分',
      value: `${dashboardData?.profile.pointsEarned || 0}`,
      unit: '分',
      icon: Trophy,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
    },
  ];

  return (
    <>
      <Head>
        <title>學習儀表板 - 幸福氣培訓中心</title>
      </Head>

      <div className="space-y-6">
        {/* Welcome Section */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold mb-2">
                歡迎回來，{user?.name}！
              </h1>
              <p className="text-primary-100">
                今天是 {format(new Date(), 'yyyy年MM月dd日 EEEE', { locale: zhTW })}
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <Flame size={24} />
              <div className="text-right">
                <p className="text-3xl font-bold">{dashboardData?.learningStreak.current || 0}</p>
                <p className="text-sm text-primary-100">天連續學習</p>
              </div>
            </div>
          </div>

          {/* Level Progress */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">等級 {dashboardData?.profile.level || 1}</span>
              <span className="text-sm">
                {dashboardData?.profile.pointsEarned || 0} / {((dashboardData?.profile.level || 1) + 1) * 1000} 積分
              </span>
            </div>
            <Progress 
              value={((dashboardData?.profile.pointsEarned || 0) % 1000) / 10} 
              className="h-2 bg-primary-300"
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">{stat.title}</p>
                      <p className="text-2xl font-bold mt-1">
                        {stat.value}
                        <span className="text-sm font-normal text-gray-500 ml-1">
                          {stat.unit}
                        </span>
                      </p>
                    </div>
                    <div className={`${stat.bgColor} p-3 rounded-lg`}>
                      <Icon size={24} className={stat.color} />
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - 2/3 width */}
          <div className="lg:col-span-2 space-y-6">
            {/* Continue Learning */}
            {dashboardData?.enrollments.filter(e => e.status === 'in_progress').length > 0 && (
              <Card>
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">繼續學習</h2>
                    <Link href="/courses" className="text-sm text-primary-600 hover:text-primary-700">
                      查看全部 <ChevronRight className="inline" size={16} />
                    </Link>
                  </div>
                  <div className="space-y-4">
                    {dashboardData.enrollments
                      .filter(e => e.status === 'in_progress')
                      .slice(0, 3)
                      .map((enrollment) => (
                        <CourseCard
                          key={enrollment.enrollmentId}
                          enrollment={enrollment}
                          showProgress
                        />
                      ))}
                  </div>
                </div>
              </Card>
            )}

            {/* Recommended Courses */}
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">推薦課程</h2>
                  <Link href="/courses/browse" className="text-sm text-primary-600 hover:text-primary-700">
                    探索更多 <ChevronRight className="inline" size={16} />
                  </Link>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {dashboardData?.recommendations.slice(0, 4).map((course) => (
                    <CourseCard
                      key={course.courseId}
                      course={course}
                      compact
                    />
                  ))}
                </div>
              </div>
            </Card>

            {/* Team Progress (for managers) */}
            {user?.role === 'manager' && dashboardData?.teamProgress && (
              <Card>
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold flex items-center">
                      <Users size={20} className="mr-2" />
                      團隊學習概況
                    </h2>
                    <Link href="/team" className="text-sm text-primary-600 hover:text-primary-700">
                      詳細報告 <ChevronRight className="inline" size={16} />
                    </Link>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-2xl font-bold text-green-600">
                        {Math.round(dashboardData.teamProgress.averageProgress)}%
                      </p>
                      <p className="text-sm text-gray-600">平均完成率</p>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-2xl font-bold text-blue-600">
                        {dashboardData.teamProgress.completionRate}%
                      </p>
                      <p className="text-sm text-gray-600">課程完成率</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-gray-700">表現優異成員</h3>
                    {dashboardData.teamProgress.topPerformers.slice(0, 3).map((member) => (
                      <div key={member.userId} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <span className="text-sm font-medium">{member.name}</span>
                        <span className="text-sm text-gray-600">
                          {member.coursesCompleted} 門課程 | {member.totalHours} 小時
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Right Column - 1/3 width */}
          <div className="space-y-6">
            {/* Upcoming Deadlines */}
            <Card>
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center">
                  <Calendar size={20} className="mr-2" />
                  即將到期
                </h2>
                {dashboardData?.upcomingDeadlines.length > 0 ? (
                  <div className="space-y-3">
                    {dashboardData.upcomingDeadlines.map((enrollment) => (
                      <div key={enrollment.enrollmentId} className="p-3 bg-yellow-50 rounded-lg">
                        <p className="font-medium text-sm">{enrollment.course?.title['zh-TW']}</p>
                        <p className="text-xs text-gray-600 mt-1">
                          截止日期：{format(new Date(enrollment.enrolledDate), 'MM月dd日')}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">目前沒有即將到期的課程</p>
                )}
              </div>
            </Card>

            {/* Recent Achievements */}
            <Card>
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center">
                  <Trophy size={20} className="mr-2" />
                  最新成就
                </h2>
                {dashboardData?.achievements.length > 0 ? (
                  <div className="space-y-3">
                    {dashboardData.achievements.slice(0, 3).map((achievement) => (
                      <AchievementBadge
                        key={achievement.achievementId}
                        achievement={achievement}
                        compact
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">完成課程以獲得成就！</p>
                )}
                <Link 
                  href="/achievements" 
                  className="block mt-4 text-center text-sm text-primary-600 hover:text-primary-700"
                >
                  查看所有成就
                </Link>
              </div>
            </Card>

            {/* Skills Overview */}
            <Card>
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center">
                  <Target size={20} className="mr-2" />
                  技能概覽
                </h2>
                <div className="space-y-3">
                  {Object.entries(dashboardData?.profile.skills || {}).map(([skill, level]) => (
                    <div key={skill}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="font-medium">{skill}</span>
                        <span className="text-gray-600">{level}%</span>
                      </div>
                      <Progress value={level} className="h-2" />
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}