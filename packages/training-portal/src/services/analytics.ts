import axios from 'axios';
import { API_URL } from '@/config';
import { authService } from './auth';

export interface AnalyticsFilters {
  start_date: string;
  end_date: string;
  department?: string;
  course_id?: string;
}

export interface OverviewMetrics {
  active_users: number;
  active_users_change: number;
  total_learning_hours: number;
  learning_hours_change: number;
  courses_completed: number;
  completion_change: number;
  avg_completion_rate: number;
  achievements_unlocked: number;
  achievements_change: number;
  quiz_pass_rate: number;
  avg_learning_speed: number;
  certifications_earned: number;
  certifications_change: number;
  summary: string;
}

export interface CourseAnalyticsData {
  courses: CourseMetric[];
  total_courses: number;
  avg_completion_rate: number;
  category_distribution: CategoryDistribution[];
  difficulty_distribution: DifficultyDistribution[];
  enrollment_trend: TrendData[];
  courses_change: number;
}

export interface CourseMetric {
  course_id: string;
  title_zh: string;
  title_en: string;
  difficulty: string;
  category: string;
  department: string;
  duration_hours: number;
  is_active: boolean;
  enrollments: number;
  completions: number;
  completion_rate: number;
  avg_score: number;
  avg_time_hours: number;
}

export interface CategoryDistribution {
  category: string;
  count: number;
  percentage: number;
}

export interface DifficultyDistribution {
  difficulty: string;
  count: number;
  enrollments: number;
  avg_completion_rate: number;
}

export interface TrendData {
  date: string;
  enrollments: number;
  completions: number;
}

export interface UserEngagementData {
  daily_active_users: number;
  dau_change: number;
  avg_session_duration: number;
  engagement_rate: number;
  activity_score: number;
  activity_level: string;
  daily_engagement: EngagementTrend[];
  weekly_engagement: EngagementTrend[];
  monthly_engagement: EngagementTrend[];
  hourly_distribution: HourlyDistribution[];
  device_distribution: DeviceDistribution[];
  department_hours: DepartmentHours[];
  activity_levels: ActivityLevel[];
  user_patterns: UserPattern[];
  learning_preferences: LearningPreference[];
  completion_distribution: CompletionDistribution[];
  top_learners: TopLearner[];
  achievement_leaders: AchievementLeader[];
  total_users: number;
}

export interface EngagementTrend {
  date: string;
  active_users: number;
  avg_duration: number;
}

export interface HourlyDistribution {
  hour: number;
  logins: number;
}

export interface DeviceDistribution {
  name: string;
  value: number;
}

export interface DepartmentHours {
  department: string;
  hours: number;
}

export interface ActivityLevel {
  level: string;
  count: number;
}

export interface UserPattern {
  learning_hours: number;
  courses_completed: number;
}

export interface LearningPreference {
  type: string;
  count: number;
  percentage: number;
}

export interface CompletionDistribution {
  range: string;
  count: number;
}

export interface TopLearner {
  user_id: string;
  name: string;
  department: string;
  learning_hours: number;
  courses_completed: number;
}

export interface AchievementLeader {
  user_id: string;
  name: string;
  achievements: number;
  points: number;
}

class AnalyticsService {
  private api = axios.create({
    baseURL: `${API_URL}/api/v1/analytics`,
  });

  constructor() {
    // Add auth interceptor
    this.api.interceptors.request.use(
      (config) => {
        const token = authService.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          await authService.refreshToken();
          return this.api(error.config);
        }
        return Promise.reject(error);
      }
    );
  }

  async getOverviewMetrics(filters: AnalyticsFilters): Promise<OverviewMetrics> {
    const response = await this.api.get('/overview', { params: filters });
    return response.data;
  }

  async getCourseAnalytics(filters: AnalyticsFilters): Promise<CourseAnalyticsData> {
    const response = await this.api.get('/courses', { params: filters });
    return response.data;
  }

  async getUserEngagement(filters: AnalyticsFilters): Promise<UserEngagementData> {
    const response = await this.api.get('/user-engagement', { params: filters });
    return response.data;
  }

  async getDepartmentAnalytics(filters: AnalyticsFilters): Promise<any> {
    const response = await this.api.get('/departments', { params: filters });
    return response.data;
  }

  async getCompletionRates(filters: AnalyticsFilters): Promise<any> {
    const response = await this.api.get('/completion-rates', { params: filters });
    return response.data;
  }

  async getLearningPathAnalytics(filters: AnalyticsFilters): Promise<any> {
    const response = await this.api.get('/learning-paths', { params: filters });
    return response.data;
  }

  async getQuizPerformance(filters: AnalyticsFilters): Promise<any> {
    const response = await this.api.get('/quiz-performance', { params: filters });
    return response.data;
  }

  async getTimeAnalytics(filters: AnalyticsFilters): Promise<any> {
    const response = await this.api.get('/time-analytics', { params: filters });
    return response.data;
  }

  async exportAnalytics(config: {
    data_types: string[];
    format: 'csv' | 'json' | 'excel';
    start_date: string;
    end_date: string;
    department?: string;
  }): Promise<any> {
    const response = await this.api.post('/export', config, {
      responseType: config.format === 'json' ? 'json' : 'blob',
    });
    return response.data;
  }

  async getRealtimeSummary(): Promise<any> {
    const response = await this.api.get('/realtime/summary');
    return response.data;
  }

  async getCustomReport(
    reportId: string,
    startDate: string,
    endDate: string
  ): Promise<any> {
    const response = await this.api.get(`/custom-report/${reportId}`, {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  }
}

export const analyticsService = new AnalyticsService();