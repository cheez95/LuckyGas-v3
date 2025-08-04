import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useAuth, useRequireAuth } from '@/hooks/useAuth';
import Head from 'next/head';
import { 
  Clock, 
  Users, 
  Star, 
  Award,
  BookOpen,
  PlayCircle,
  FileText,
  CheckCircle,
  Lock,
  ChevronRight,
  Download,
  Share2,
  Calendar
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { VideoPlayer } from '@/components/video/VideoPlayer';
import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { Button } from '@/components/ui/Button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

export default function CoursePage() {
  const router = useRouter();
  const { id } = router.query;
  const isAuthenticated = useRequireAuth();
  const { user } = useAuth();
  const [activeModuleId, setActiveModuleId] = useState<string | null>(null);

  // Fetch course details
  const { data: course, isLoading: courseLoading } = useQuery({
    queryKey: ['course', id],
    queryFn: () => api.getCourse(id as string),
    enabled: !!id && isAuthenticated,
  });

  // Fetch enrollment status
  const { data: enrollment, refetch: refetchEnrollment } = useQuery({
    queryKey: ['enrollment', id],
    queryFn: () => api.getEnrollment(id as string),
    enabled: !!id && isAuthenticated,
  });

  // Fetch progress
  const { data: progress, refetch: refetchProgress } = useQuery({
    queryKey: ['progress', id],
    queryFn: () => api.getProgress(id as string),
    enabled: !!id && !!enrollment,
  });

  // Enroll mutation
  const enrollMutation = useMutation({
    mutationFn: () => api.enrollInCourse(id as string),
    onSuccess: () => {
      toast.success('成功報名課程！');
      refetchEnrollment();
    },
    onError: () => {
      toast.error('報名失敗，請稍後再試');
    },
  });

  if (!isAuthenticated || courseLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="space-y-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-gray-500">載入中...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-gray-900">找不到課程</h2>
        <p className="text-gray-600 mt-2">請確認課程連結是否正確</p>
        <Button onClick={() => router.push('/courses')} className="mt-4">
          返回課程列表
        </Button>
      </div>
    );
  }

  const isEnrolled = !!enrollment;
  const currentModule = course.modules.find(m => m.moduleId === activeModuleId);
  const completedModules = progress?.modulesCompleted || [];
  const progressPercentage = enrollment?.progressPercentage || 0;

  const getModuleIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <PlayCircle size={16} />;
      case 'reading':
        return <FileText size={16} />;
      case 'quiz':
        return <CheckCircle size={16} />;
      default:
        return <BookOpen size={16} />;
    }
  };

  return (
    <>
      <Head>
        <title>{course.title['zh-TW']} - 幸福氣培訓中心</title>
      </Head>

      <div className="max-w-7xl mx-auto">
        {/* Course Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-8 text-white mb-6">
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-3 py-1 bg-white/20 rounded-full text-sm">
                  {course.category}
                </span>
                <span className="px-3 py-1 bg-white/20 rounded-full text-sm">
                  {course.difficulty === 'beginner' ? '初級' : 
                   course.difficulty === 'intermediate' ? '中級' : '高級'}
                </span>
              </div>
              
              <h1 className="text-3xl font-bold mb-3">{course.title['zh-TW']}</h1>
              <p className="text-primary-100 mb-4">{course.description['zh-TW']}</p>
              
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <span className="flex items-center gap-1">
                  <Clock size={16} />
                  {Math.floor(course.durationMinutes / 60)}小時
                  {course.durationMinutes % 60 > 0 && `${course.durationMinutes % 60}分`}
                </span>
                <span className="flex items-center gap-1">
                  <BookOpen size={16} />
                  {course.modules.length} 個單元
                </span>
                <span className="flex items-center gap-1">
                  <Users size={16} />
                  {course.enrollmentCount} 位學員
                </span>
                <span className="flex items-center gap-1">
                  <Star size={16} className="text-yellow-400" />
                  {course.rating.toFixed(1)}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              {!isEnrolled ? (
                <Button
                  size="lg"
                  onClick={() => enrollMutation.mutate()}
                  disabled={enrollMutation.isPending}
                  className="bg-white text-primary-600 hover:bg-gray-100"
                >
                  立即報名
                </Button>
              ) : (
                <>
                  <div className="bg-white/20 rounded-lg p-4">
                    <div className="text-sm mb-2">學習進度</div>
                    <Progress value={progressPercentage} className="h-2 bg-white/30" />
                    <div className="text-right text-sm mt-1">
                      {Math.round(progressPercentage)}%
                    </div>
                  </div>
                  {enrollment.status === 'completed' && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-white text-white hover:bg-white/20"
                      onClick={() => router.push('/certificates')}
                    >
                      <Award size={16} className="mr-2" />
                      查看證書
                    </Button>
                  )}
                </>
              )}
              
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-white hover:bg-white/20"
                >
                  <Share2 size={16} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-white hover:bg-white/20"
                >
                  <Download size={16} />
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Course Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content Area */}
          <div className="lg:col-span-2">
            <Tabs defaultValue="content" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="content">課程內容</TabsTrigger>
                <TabsTrigger value="resources">資源下載</TabsTrigger>
                <TabsTrigger value="discussion">討論區</TabsTrigger>
              </TabsList>

              <TabsContent value="content" className="mt-4">
                {currentModule ? (
                  <Card className="p-6">
                    <h2 className="text-xl font-semibold mb-4">
                      {currentModule.title['zh-TW']}
                    </h2>
                    
                    {currentModule.type === 'video' && currentModule.contentUrl && (
                      <VideoPlayer
                        url={currentModule.contentUrl}
                        courseId={course.courseId}
                        moduleId={currentModule.moduleId}
                        onProgress={(progress) => {
                          // Handle progress update
                          if (progress >= 90 && !completedModules.includes(currentModule.moduleId)) {
                            refetchProgress();
                          }
                        }}
                      />
                    )}
                    
                    {currentModule.type === 'reading' && (
                      <div className="prose prose-gray max-w-none">
                        <p>閱讀內容載入中...</p>
                      </div>
                    )}
                    
                    {currentModule.type === 'quiz' && (
                      <div className="text-center py-12">
                        <CheckCircle size={48} className="mx-auto text-primary-600 mb-4" />
                        <h3 className="text-lg font-semibold mb-2">準備好進行測驗了嗎？</h3>
                        <p className="text-gray-600 mb-4">
                          這個測驗包含 10 個問題，時限 20 分鐘
                        </p>
                        <Button onClick={() => router.push(`/assessments/${currentModule.moduleId}`)}>
                          開始測驗
                        </Button>
                      </div>
                    )}
                  </Card>
                ) : (
                  <Card className="p-12 text-center">
                    <BookOpen size={48} className="mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      歡迎來到 {course.title['zh-TW']}
                    </h3>
                    <p className="text-gray-600">
                      {isEnrolled ? '請從右側選擇一個單元開始學習' : '請先報名課程以開始學習'}
                    </p>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="resources" className="mt-4">
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">課程資源</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileText size={20} className="text-gray-600" />
                        <div>
                          <p className="font-medium">課程講義</p>
                          <p className="text-sm text-gray-600">PDF, 2.5MB</p>
                        </div>
                      </div>
                      <Button size="sm" variant="outline">
                        <Download size={16} className="mr-2" />
                        下載
                      </Button>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileText size={20} className="text-gray-600" />
                        <div>
                          <p className="font-medium">練習檔案</p>
                          <p className="text-sm text-gray-600">ZIP, 5.1MB</p>
                        </div>
                      </div>
                      <Button size="sm" variant="outline">
                        <Download size={16} className="mr-2" />
                        下載
                      </Button>
                    </div>
                  </div>
                </Card>
              </TabsContent>

              <TabsContent value="discussion" className="mt-4">
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">課程討論</h3>
                  <p className="text-gray-600">討論區功能即將推出...</p>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar - Module List */}
          <div>
            <Card className="p-4">
              <h3 className="font-semibold mb-4">課程大綱</h3>
              <div className="space-y-2">
                {course.modules.map((module, index) => {
                  const isCompleted = completedModules.includes(module.moduleId);
                  const isLocked = !isEnrolled || (index > 0 && !completedModules.includes(course.modules[index - 1].moduleId));
                  const isActive = module.moduleId === activeModuleId;

                  return (
                    <button
                      key={module.moduleId}
                      onClick={() => !isLocked && setActiveModuleId(module.moduleId)}
                      disabled={isLocked}
                      className={`w-full text-left p-3 rounded-lg transition-all ${
                        isActive
                          ? 'bg-primary-50 border-2 border-primary-500'
                          : isLocked
                          ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                          : 'hover:bg-gray-50 border-2 border-transparent'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`flex-shrink-0 mt-0.5 ${
                          isCompleted ? 'text-green-600' : 
                          isActive ? 'text-primary-600' : 
                          'text-gray-400'
                        }`}>
                          {isLocked ? (
                            <Lock size={16} />
                          ) : isCompleted ? (
                            <CheckCircle size={16} />
                          ) : (
                            getModuleIcon(module.type)
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`font-medium ${isLocked ? 'text-gray-400' : ''}`}>
                            {index + 1}. {module.title['zh-TW']}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {module.durationMinutes} 分鐘
                          </p>
                        </div>
                        {isActive && (
                          <ChevronRight size={16} className="text-primary-600 flex-shrink-0" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>

            {/* Course Info */}
            <Card className="p-4 mt-4">
              <h3 className="font-semibold mb-4">課程資訊</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">講師</p>
                  <p className="font-medium">王大明 資深培訓師</p>
                </div>
                <div>
                  <p className="text-gray-600">最後更新</p>
                  <p className="font-medium">
                    {format(new Date(course.updatedAt), 'yyyy年MM月dd日', { locale: zhTW })}
                  </p>
                </div>
                <div>
                  <p className="text-gray-600">證書要求</p>
                  <p className="font-medium">完成所有單元，測驗達 {course.passPercentage}% 以上</p>
                </div>
                {isEnrolled && enrollment.dueDate && (
                  <div>
                    <p className="text-gray-600">完成期限</p>
                    <p className="font-medium flex items-center gap-1">
                      <Calendar size={14} />
                      {format(new Date(enrollment.dueDate), 'yyyy年MM月dd日', { locale: zhTW })}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}