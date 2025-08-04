import React, { useState, useCallback, useMemo } from 'react';
import {
  StyleSheet,
  View,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import {
  Text,
  Searchbar,
  Chip,
  FAB,
  Card,
  Badge,
  IconButton,
  Divider,
  Surface,
} from 'react-native-paper';
import { FlashList } from '@shopify/flash-list';
import { useQuery } from '@tanstack/react-query';
import { useNavigation } from '@react-navigation/native';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';

import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { trainingService } from '@/services/training';
import { Course, CourseFilters } from '@/types/training';
import { CourseCard } from '@/components/training/CourseCard';
import { FilterModal } from '@/components/training/FilterModal';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';

export function CourseListScreen() {
  const navigation = useNavigation();
  const { user } = useAuth();
  const { theme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<CourseFilters>({
    department: user?.department || 'all',
    difficulty: undefined,
    category: undefined,
    isRequired: undefined,
  });
  const [isFilterModalVisible, setIsFilterModalVisible] = useState(false);

  // Fetch courses
  const {
    data: courses = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['courses', filters, searchQuery],
    queryFn: () => trainingService.getCourses({ ...filters, search: searchQuery }),
  });

  // Fetch user's enrollments
  const { data: enrollments = [] } = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => trainingService.getUserEnrollments(user!.id),
    enabled: !!user,
  });

  // Create enrollment map for quick lookup
  const enrollmentMap = useMemo(() => {
    const map = new Map();
    enrollments.forEach(enrollment => {
      map.set(enrollment.course_id, enrollment);
    });
    return map;
  }, [enrollments]);

  const handleCoursePress = useCallback((course: Course) => {
    navigation.navigate('CourseDetail', { courseId: course.course_id });
  }, [navigation]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const handleFilterChange = useCallback((newFilters: CourseFilters) => {
    setFilters(newFilters);
    setIsFilterModalVisible(false);
  }, []);

  const renderCourse = useCallback(({ item }: { item: Course }) => {
    const enrollment = enrollmentMap.get(item.course_id);
    
    return (
      <CourseCard
        course={item}
        enrollment={enrollment}
        onPress={() => handleCoursePress(item)}
      />
    );
  }, [enrollmentMap, handleCoursePress]);

  const ListHeaderComponent = useMemo(() => (
    <View style={styles.header}>
      <Searchbar
        placeholder="搜尋課程..."
        onChangeText={handleSearch}
        value={searchQuery}
        style={styles.searchbar}
        icon="magnify"
        clearIcon="close"
      />
      
      <View style={styles.filterChips}>
        {filters.department !== 'all' && (
          <Chip
            style={styles.chip}
            onClose={() => setFilters({ ...filters, department: 'all' })}
          >
            部門: {filters.department}
          </Chip>
        )}
        {filters.difficulty && (
          <Chip
            style={styles.chip}
            onClose={() => setFilters({ ...filters, difficulty: undefined })}
          >
            難度: {filters.difficulty}
          </Chip>
        )}
        {filters.category && (
          <Chip
            style={styles.chip}
            onClose={() => setFilters({ ...filters, category: undefined })}
          >
            類別: {filters.category}
          </Chip>
        )}
        {filters.isRequired !== undefined && (
          <Chip
            style={styles.chip}
            onClose={() => setFilters({ ...filters, isRequired: undefined })}
          >
            {filters.isRequired ? '必修' : '選修'}
          </Chip>
        )}
      </View>

      <View style={styles.stats}>
        <Surface style={styles.statCard} elevation={1}>
          <Text variant="headlineSmall" style={styles.statNumber}>
            {courses.length}
          </Text>
          <Text variant="bodySmall" style={styles.statLabel}>
            總課程數
          </Text>
        </Surface>
        
        <Surface style={styles.statCard} elevation={1}>
          <Text variant="headlineSmall" style={styles.statNumber}>
            {enrollments.filter(e => e.status === 'completed').length}
          </Text>
          <Text variant="bodySmall" style={styles.statLabel}>
            已完成
          </Text>
        </Surface>
        
        <Surface style={styles.statCard} elevation={1}>
          <Text variant="headlineSmall" style={styles.statNumber}>
            {enrollments.filter(e => e.status === 'in_progress').length}
          </Text>
          <Text variant="bodySmall" style={styles.statLabel}>
            進行中
          </Text>
        </Surface>
      </View>
    </View>
  ), [searchQuery, filters, courses.length, enrollments, handleSearch]);

  const ListEmptyComponent = useMemo(() => {
    if (isLoading) {
      return (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          <Text style={styles.loadingText}>載入課程中...</Text>
        </View>
      );
    }

    if (error) {
      return (
        <ErrorState
          message="無法載入課程"
          onRetry={refetch}
        />
      );
    }

    return (
      <EmptyState
        icon="school"
        title="沒有找到課程"
        message={searchQuery ? "試試其他搜尋關鍵字" : "目前沒有可用的課程"}
      />
    );
  }, [isLoading, error, searchQuery, theme.colors.primary, refetch]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.department !== 'all') count++;
    if (filters.difficulty) count++;
    if (filters.category) count++;
    if (filters.isRequired !== undefined) count++;
    return count;
  }, [filters]);

  return (
    <View style={styles.container}>
      <FlashList
        data={courses}
        renderItem={renderCourse}
        estimatedItemSize={200}
        ListHeaderComponent={ListHeaderComponent}
        ListEmptyComponent={ListEmptyComponent}
        refreshControl={
          <RefreshControl
            refreshing={isLoading}
            onRefresh={refetch}
            colors={[theme.colors.primary]}
          />
        }
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />

      <FAB
        icon="filter"
        style={[styles.fab, { backgroundColor: theme.colors.primary }]}
        onPress={() => setIsFilterModalVisible(true)}
        label={activeFilterCount > 0 ? `篩選 (${activeFilterCount})` : '篩選'}
        extended={activeFilterCount > 0}
      />

      <FilterModal
        visible={isFilterModalVisible}
        filters={filters}
        onApply={handleFilterChange}
        onDismiss={() => setIsFilterModalVisible(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  listContent: {
    paddingBottom: 80,
  },
  header: {
    backgroundColor: '#FFFFFF',
    paddingBottom: 16,
  },
  searchbar: {
    margin: 16,
    elevation: 2,
  },
  filterChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  chip: {
    marginRight: 8,
    marginBottom: 8,
  },
  stats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 16,
  },
  statCard: {
    flex: 1,
    padding: 16,
    marginHorizontal: 4,
    borderRadius: 8,
    alignItems: 'center',
  },
  statNumber: {
    fontWeight: 'bold',
  },
  statLabel: {
    marginTop: 4,
    opacity: 0.7,
  },
  separator: {
    height: 8,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  loadingText: {
    marginTop: 16,
    opacity: 0.7,
  },
  fab: {
    position: 'absolute',
    right: 16,
    bottom: 16,
  },
});