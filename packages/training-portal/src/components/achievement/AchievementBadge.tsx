import React from 'react';
import { Achievement } from '@/types/training';
import { Trophy, Target, Flame, Star, Award, TrendingUp, Users, BookOpen } from 'lucide-react';
import { cn } from '@/utils/cn';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

interface AchievementBadgeProps {
  achievement: Achievement;
  compact?: boolean;
  showDate?: boolean;
  animated?: boolean;
}

export const AchievementBadge: React.FC<AchievementBadgeProps> = ({
  achievement,
  compact = false,
  showDate = true,
  animated = true
}) => {
  const getIcon = () => {
    const iconProps = { size: compact ? 20 : 24 };
    
    switch (achievement.type) {
      case 'course_completion':
        return <BookOpen {...iconProps} />;
      case 'streak':
        return <Flame {...iconProps} />;
      case 'milestone':
        return <Target {...iconProps} />;
      case 'special':
        return <Star {...iconProps} />;
      default:
        return <Trophy {...iconProps} />;
    }
  };

  const getBackgroundColor = () => {
    switch (achievement.type) {
      case 'course_completion':
        return 'from-blue-400 to-blue-600';
      case 'streak':
        return 'from-orange-400 to-red-600';
      case 'milestone':
        return 'from-purple-400 to-purple-600';
      case 'special':
        return 'from-yellow-400 to-yellow-600';
      default:
        return 'from-gray-400 to-gray-600';
    }
  };

  const getBorderColor = () => {
    switch (achievement.type) {
      case 'course_completion':
        return 'border-blue-300';
      case 'streak':
        return 'border-orange-300';
      case 'milestone':
        return 'border-purple-300';
      case 'special':
        return 'border-yellow-300';
      default:
        return 'border-gray-300';
    }
  };

  const content = (
    <div className={cn(
      'flex items-center gap-3 p-3 rounded-lg border-2 bg-white',
      getBorderColor(),
      !compact && 'p-4',
      animated && 'achievement-glow'
    )}>
      {/* Icon Badge */}
      <div className={cn(
        'flex-shrink-0 rounded-full bg-gradient-to-br text-white p-2',
        getBackgroundColor(),
        !compact && 'p-3'
      )}>
        {getIcon()}
      </div>

      {/* Achievement Info */}
      <div className="flex-1 min-w-0">
        <h4 className={cn(
          'font-semibold text-gray-900',
          compact ? 'text-sm' : 'text-base'
        )}>
          {achievement.name['zh-TW']}
        </h4>
        {!compact && (
          <p className="text-sm text-gray-600 mt-0.5">
            {achievement.description['zh-TW']}
          </p>
        )}
        {showDate && (
          <p className="text-xs text-gray-500 mt-1">
            {format(new Date(achievement.earnedDate), 'yyyy年MM月dd日', { locale: zhTW })}
          </p>
        )}
      </div>

      {/* Points Badge */}
      {achievement.points > 0 && (
        <div className={cn(
          'flex-shrink-0 text-right',
          compact && 'text-sm'
        )}>
          <div className="font-bold text-primary-600">
            +{achievement.points}
          </div>
          <div className="text-xs text-gray-500">積分</div>
        </div>
      )}
    </div>
  );

  if (animated) {
    return (
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        whileHover={{ scale: 1.02 }}
        transition={{ type: 'spring', stiffness: 300 }}
      >
        {content}
      </motion.div>
    );
  }

  return content;
};

// Achievement Gallery Component
export const AchievementGallery: React.FC<{
  achievements: Achievement[];
  columns?: number;
}> = ({ achievements, columns = 3 }) => {
  const sortedAchievements = [...achievements].sort(
    (a, b) => new Date(b.earnedDate).getTime() - new Date(a.earnedDate).getTime()
  );

  return (
    <div className={cn(
      'grid gap-4',
      columns === 2 && 'grid-cols-1 md:grid-cols-2',
      columns === 3 && 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
      columns === 4 && 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
    )}>
      {sortedAchievements.map((achievement, index) => (
        <motion.div
          key={achievement.achievementId}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <AchievementBadge achievement={achievement} />
        </motion.div>
      ))}
    </div>
  );
};

// Achievement Progress Component
export const AchievementProgress: React.FC<{
  totalPoints: number;
  nextLevelPoints: number;
  currentLevel: number;
}> = ({ totalPoints, nextLevelPoints, currentLevel }) => {
  const progress = (totalPoints % 1000) / 10;
  
  return (
    <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            等級 {currentLevel}
          </h3>
          <p className="text-sm text-gray-600">
            總積分：{totalPoints}
          </p>
        </div>
        <div className="text-right">
          <Award size={32} className="text-primary-600 mb-1" />
          <p className="text-xs text-gray-600">
            下一等級：{nextLevelPoints} 分
          </p>
        </div>
      </div>
      
      <div className="space-y-2">
        <Progress value={progress} className="h-3" />
        <div className="flex justify-between text-xs text-gray-600">
          <span>{totalPoints % 1000} / 1000</span>
          <span>{Math.round(progress)}%</span>
        </div>
      </div>
    </div>
  );
};