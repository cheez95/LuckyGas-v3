import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { Clock, Users, Star, BookOpen, Award } from 'lucide-react';
import { Course, Enrollment } from '@/types/training';
import { cn } from '@/utils/cn';

interface CourseCardProps {
  course?: Course;
  enrollment?: Enrollment;
  showProgress?: boolean;
  compact?: boolean;
}

export const CourseCard: React.FC<CourseCardProps> = ({
  course,
  enrollment,
  showProgress = false,
  compact = false
}) => {
  const displayCourse = course || enrollment?.course;
  
  if (!displayCourse) return null;

  const difficultyColors = {
    beginner: 'bg-green-100 text-green-700',
    intermediate: 'bg-yellow-100 text-yellow-700',
    advanced: 'bg-red-100 text-red-700'
  };

  const difficultyLabels = {
    beginner: '初級',
    intermediate: '中級',
    advanced: '高級'
  };

  const statusColors = {
    enrolled: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    expired: 'bg-gray-100 text-gray-700'
  };

  const statusLabels = {
    enrolled: '已報名',
    in_progress: '學習中',
    completed: '已完成',
    failed: '未通過',
    expired: '已過期'
  };

  return (
    <Card className="hover:shadow-lg transition-all duration-200 overflow-hidden group">
      <Link href={`/courses/${displayCourse.courseId}`}>
        <div className={cn('p-4', compact && 'p-3')}>
          {/* Course Thumbnail */}
          {displayCourse.thumbnailUrl && !compact && (
            <div className="relative w-full h-48 mb-4 overflow-hidden rounded-lg">
              <img
                src={displayCourse.thumbnailUrl}
                alt={displayCourse.title['zh-TW']}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
              <div className="absolute top-2 right-2">
                <span className={cn(
                  'px-2 py-1 rounded-full text-xs font-medium',
                  difficultyColors[displayCourse.difficulty]
                )}>
                  {difficultyLabels[displayCourse.difficulty]}
                </span>
              </div>
            </div>
          )}

          {/* Course Info */}
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <h3 className={cn(
                'font-semibold text-gray-900 group-hover:text-primary-600 transition-colors',
                compact ? 'text-sm' : 'text-base'
              )}>
                {displayCourse.title['zh-TW']}
              </h3>
              {enrollment && (
                <span className={cn(
                  'px-2 py-1 rounded-full text-xs font-medium ml-2 flex-shrink-0',
                  statusColors[enrollment.status]
                )}>
                  {statusLabels[enrollment.status]}
                </span>
              )}
            </div>

            {!compact && (
              <p className="text-sm text-gray-600 line-clamp-2">
                {displayCourse.description['zh-TW']}
              </p>
            )}

            {/* Course Metadata */}
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center">
                <Clock size={12} className="mr-1" />
                {Math.floor(displayCourse.durationMinutes / 60)}小時
                {displayCourse.durationMinutes % 60 > 0 && `${displayCourse.durationMinutes % 60}分`}
              </span>
              <span className="flex items-center">
                <BookOpen size={12} className="mr-1" />
                {displayCourse.modules?.length || 0} 個單元
              </span>
              {displayCourse.enrollmentCount > 0 && (
                <span className="flex items-center">
                  <Users size={12} className="mr-1" />
                  {displayCourse.enrollmentCount}
                </span>
              )}
              {displayCourse.rating > 0 && (
                <span className="flex items-center">
                  <Star size={12} className="mr-1 text-yellow-500" />
                  {displayCourse.rating.toFixed(1)}
                </span>
              )}
            </div>

            {/* Tags */}
            {!compact && displayCourse.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {displayCourse.tags.slice(0, 3).map((tag, index) => (
                  <span
                    key={index}
                    className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                  >
                    {tag}
                  </span>
                ))}
                {displayCourse.tags.length > 3 && (
                  <span className="px-2 py-0.5 text-gray-500 text-xs">
                    +{displayCourse.tags.length - 3}
                  </span>
                )}
              </div>
            )}

            {/* Progress Bar */}
            {showProgress && enrollment && (
              <div className="mt-3 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">學習進度</span>
                  <span className="font-medium">
                    {Math.round(enrollment.progressPercentage)}%
                  </span>
                </div>
                <Progress 
                  value={enrollment.progressPercentage} 
                  className="h-2"
                  indicatorClassName={
                    enrollment.progressPercentage === 100 
                      ? 'bg-green-500' 
                      : 'bg-primary-500'
                  }
                />
                {enrollment.completedDate && (
                  <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
                    <Award size={12} />
                    <span>已獲得證書</span>
                  </div>
                )}
              </div>
            )}

            {/* Prerequisites */}
            {!compact && displayCourse.prerequisites?.length > 0 && (
              <div className="pt-2 border-t">
                <p className="text-xs text-gray-500">
                  先修課程：{displayCourse.prerequisites.length} 門
                </p>
              </div>
            )}
          </div>
        </div>
      </Link>
    </Card>
  );
};