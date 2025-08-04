import React from 'react';
import { StyleSheet, View, Pressable } from 'react-native';
import {
  Card,
  Text,
  Avatar,
  ProgressBar,
  Chip,
  Badge,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import LottieView from 'lottie-react-native';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

import { Achievement, UserAchievement } from '@/types/training';
import { useTheme } from '@/contexts/ThemeContext';

interface AchievementCardProps {
  achievement: Achievement;
  userAchievement?: UserAchievement;
  onPress?: () => void;
}

export function AchievementCard({
  achievement,
  userAchievement,
  onPress,
}: AchievementCardProps) {
  const { theme } = useTheme();
  const isUnlocked = !!userAchievement?.unlocked_at;
  const progress = userAchievement?.progress || 0;

  const getIcon = () => {
    if (isUnlocked && achievement.animation_url) {
      return (
        <LottieView
          source={{ uri: achievement.animation_url }}
          autoPlay
          loop={false}
          style={styles.animation}
        />
      );
    }

    return (
      <Avatar.Icon
        size={60}
        icon={achievement.icon || 'trophy'}
        style={[
          styles.avatar,
          {
            backgroundColor: isUnlocked
              ? theme.colors.primary
              : theme.colors.surfaceVariant,
          },
        ]}
        color={isUnlocked ? '#FFFFFF' : theme.colors.onSurfaceVariant}
      />
    );
  };

  const getRarityColor = (rarity: string) => {
    switch (rarity) {
      case 'common':
        return '#9E9E9E';
      case 'rare':
        return '#2196F3';
      case 'epic':
        return '#9C27B0';
      case 'legendary':
        return '#FF9800';
      default:
        return theme.colors.primary;
    }
  };

  const getRarityLabel = (rarity: string) => {
    switch (rarity) {
      case 'common':
        return '普通';
      case 'rare':
        return '稀有';
      case 'epic':
        return '史詩';
      case 'legendary':
        return '傳奇';
      default:
        return rarity;
    }
  };

  return (
    <Pressable onPress={onPress} disabled={!isUnlocked}>
      <Card
        style={[
          styles.card,
          !isUnlocked && styles.lockedCard,
        ]}
        mode="elevated"
      >
        <Card.Content>
          <View style={styles.header}>
            {getIcon()}
            
            <View style={styles.info}>
              <View style={styles.titleRow}>
                <Text
                  variant="titleMedium"
                  style={[
                    styles.title,
                    !isUnlocked && styles.lockedText,
                  ]}
                >
                  {achievement.title_zh}
                </Text>
                
                {achievement.points > 0 && (
                  <Badge
                    style={[
                      styles.pointsBadge,
                      { backgroundColor: theme.colors.tertiary },
                    ]}
                  >
                    +{achievement.points}
                  </Badge>
                )}
              </View>

              <Text
                variant="bodySmall"
                style={[
                  styles.description,
                  !isUnlocked && styles.lockedText,
                ]}
                numberOfLines={2}
              >
                {achievement.description_zh}
              </Text>

              <View style={styles.tags}>
                <Chip
                  compact
                  style={[
                    styles.rarityChip,
                    { backgroundColor: getRarityColor(achievement.rarity) },
                  ]}
                  textStyle={styles.chipText}
                >
                  {getRarityLabel(achievement.rarity)}
                </Chip>

                <Chip
                  compact
                  style={styles.categoryChip}
                  textStyle={styles.chipText}
                >
                  {achievement.category}
                </Chip>
              </View>
            </View>
          </View>

          {!isUnlocked && achievement.max_progress && (
            <View style={styles.progressSection}>
              <View style={styles.progressHeader}>
                <Text variant="bodySmall" style={styles.progressLabel}>
                  進度
                </Text>
                <Text variant="bodySmall" style={styles.progressText}>
                  {progress} / {achievement.max_progress}
                </Text>
              </View>
              <ProgressBar
                progress={progress / achievement.max_progress}
                color={theme.colors.primary}
                style={styles.progressBar}
              />
            </View>
          )}

          {isUnlocked && userAchievement && (
            <View style={styles.unlockedInfo}>
              <MaterialCommunityIcons
                name="calendar-check"
                size={14}
                color={theme.colors.onSurfaceVariant}
              />
              <Text variant="bodySmall" style={styles.unlockedText}>
                解鎖於 {format(
                  new Date(userAchievement.unlocked_at!),
                  'yyyy年MM月dd日',
                  { locale: zhTW }
                )}
              </Text>
            </View>
          )}

          {!isUnlocked && achievement.hint && (
            <View style={styles.hintSection}>
              <MaterialCommunityIcons
                name="lightbulb-outline"
                size={16}
                color={theme.colors.primary}
              />
              <Text variant="bodySmall" style={styles.hintText}>
                提示: {achievement.hint}
              </Text>
            </View>
          )}
        </Card.Content>
      </Card>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  lockedCard: {
    opacity: 0.7,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  avatar: {
    marginRight: 12,
  },
  animation: {
    width: 60,
    height: 60,
    marginRight: 12,
  },
  info: {
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  title: {
    flex: 1,
    fontWeight: '600',
  },
  lockedText: {
    opacity: 0.6,
  },
  pointsBadge: {
    marginLeft: 8,
  },
  description: {
    marginBottom: 8,
    lineHeight: 18,
  },
  tags: {
    flexDirection: 'row',
    gap: 8,
  },
  rarityChip: {
    height: 24,
  },
  categoryChip: {
    height: 24,
    backgroundColor: 'rgba(0, 0, 0, 0.08)',
  },
  chipText: {
    fontSize: 11,
    color: '#FFFFFF',
  },
  progressSection: {
    marginTop: 12,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  progressLabel: {
    opacity: 0.7,
  },
  progressText: {
    fontWeight: '600',
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
  },
  unlockedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 8,
  },
  unlockedText: {
    opacity: 0.7,
  },
  hintSection: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 8,
    padding: 8,
    backgroundColor: 'rgba(255, 107, 53, 0.1)',
    borderRadius: 8,
  },
  hintText: {
    flex: 1,
    fontStyle: 'italic',
  },
});