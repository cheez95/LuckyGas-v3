import React from 'react';
import { StyleSheet, View, Pressable } from 'react-native';
import {
  Card,
  Text,
  Chip,
  ProgressBar,
  IconButton,
  Badge,
  Surface,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

import { Course, Enrollment } from '@/types/training';
import { useTheme } from '@/contexts/ThemeContext';

interface CourseCardProps {
  course: Course;
  enrollment?: Enrollment;
  onPress: () => void;
}

export function CourseCard({ course, enrollment, onPress }: CourseCardProps) {
  const { theme } = useTheme();

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner':
        return theme.colors.success;
      case 'intermediate':
        return theme.colors.warning;
      case 'advanced':
        return theme.colors.error;
      default:
        return theme.colors.primary;
    }
  };

  const getDifficultyLabel = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner':
        return '初級';
      case 'intermediate':
        return '中級';
      case 'advanced':
        return '高級';
      default:
        return difficulty;
    }
  };

  const getStatusIcon = () => {
    if (!enrollment) return null;
    
    switch (enrollment.status) {
      case 'completed':
        return (
          <MaterialCommunityIcons
            name="check-circle"
            size={24}
            color={theme.colors.success}
          />
        );
      case 'in_progress':
        return (
          <MaterialCommunityIcons
            name="progress-clock"
            size={24}
            color={theme.colors.primary}
          />
        );
      default:
        return null;
    }
  };

  const formatDuration = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} 分鐘`;
    }
    return `${hours} 小時`;
  };

  return (
    <Pressable onPress={onPress}>
      <Card style={styles.card} mode="elevated">
        <Card.Content>
          <View style={styles.header}>
            <View style={styles.titleContainer}>
              <View style={styles.titleRow}>
                <Text variant="titleMedium" style={styles.title}>
                  {course.title_zh}
                </Text>
                {course.is_required && (
                  <Badge style={styles.requiredBadge}>必修</Badge>
                )}
              </View>
              {course.title_en && (
                <Text variant="bodySmall" style={styles.subtitle}>
                  {course.title_en}
                </Text>
              )}
            </View>
            {getStatusIcon()}
          </View>

          <Text
            variant="bodyMedium"
            style={styles.description}
            numberOfLines={2}
          >
            {course.description_zh}
          </Text>

          <View style={styles.chips}>
            <Chip
              compact
              style={[
                styles.chip,
                { backgroundColor: getDifficultyColor(course.difficulty) },
              ]}
              textStyle={styles.chipText}
            >
              {getDifficultyLabel(course.difficulty)}
            </Chip>
            
            <Chip compact style={styles.chip} textStyle={styles.chipText}>
              {course.department}
            </Chip>
            
            <Chip compact style={styles.chip} textStyle={styles.chipText}>
              {course.category}
            </Chip>
            
            <Chip
              compact
              style={styles.chip}
              textStyle={styles.chipText}
              icon="clock-outline"
            >
              {formatDuration(course.duration_hours)}
            </Chip>
          </View>

          {enrollment && enrollment.status === 'in_progress' && (
            <View style={styles.progressContainer}>
              <View style={styles.progressHeader}>
                <Text variant="bodySmall">學習進度</Text>
                <Text variant="bodySmall" style={styles.progressText}>
                  {enrollment.progress_percentage}%
                </Text>
              </View>
              <ProgressBar
                progress={enrollment.progress_percentage / 100}
                color={theme.colors.primary}
                style={styles.progressBar}
              />
            </View>
          )}

          {enrollment?.completed_at && (
            <View style={styles.completedInfo}>
              <MaterialCommunityIcons
                name="calendar-check"
                size={16}
                color={theme.colors.onSurfaceVariant}
              />
              <Text variant="bodySmall" style={styles.completedText}>
                完成於 {format(new Date(enrollment.completed_at), 'yyyy年MM月dd日', { locale: zhTW })}
              </Text>
            </View>
          )}

          <View style={styles.footer}>
            <View style={styles.stats}>
              <View style={styles.stat}>
                <MaterialCommunityIcons
                  name="book-open-variant"
                  size={16}
                  color={theme.colors.onSurfaceVariant}
                />
                <Text variant="bodySmall" style={styles.statText}>
                  {course.module_count || 0} 個模組
                </Text>
              </View>
              
              {course.passing_score && (
                <View style={styles.stat}>
                  <MaterialCommunityIcons
                    name="target"
                    size={16}
                    color={theme.colors.onSurfaceVariant}
                  />
                  <Text variant="bodySmall" style={styles.statText}>
                    及格分數: {course.passing_score}
                  </Text>
                </View>
              )}
            </View>

            <MaterialCommunityIcons
              name="chevron-right"
              size={24}
              color={theme.colors.onSurfaceVariant}
            />
          </View>
        </Card.Content>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 16,
    marginVertical: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  titleContainer: {
    flex: 1,
    marginRight: 8,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontWeight: '600',
  },
  subtitle: {
    opacity: 0.7,
    marginTop: 2,
  },
  requiredBadge: {
    backgroundColor: '#FF5252',
  },
  description: {
    marginBottom: 12,
    opacity: 0.8,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  chip: {
    height: 28,
  },
  chipText: {
    fontSize: 12,
    color: '#FFFFFF',
  },
  progressContainer: {
    marginTop: 12,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  progressText: {
    fontWeight: '600',
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
  },
  completedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
  },
  completedText: {
    opacity: 0.7,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
  },
  stats: {
    flexDirection: 'row',
    gap: 16,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    opacity: 0.7,
  },
});