import axios, { AxiosInstance, AxiosError } from 'axios';
import { toast } from 'react-hot-toast';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://training-api.luckygas.com.tw/v1';

class ApiService {
  private instance: AxiosInstance;

  constructor() {
    this.instance = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.instance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('training_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.instance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('training_token');
          window.location.href = '/login';
          toast.error('Session expired. Please login again.');
        } else if (error.response?.status === 403) {
          toast.error('You do not have permission to perform this action.');
        } else if (error.response?.status === 500) {
          toast.error('Server error. Please try again later.');
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(email: string, password: string) {
    const response = await this.instance.post('/auth/login', { email, password });
    const { token, refreshToken, user } = response.data;
    localStorage.setItem('training_token', token);
    localStorage.setItem('training_refresh_token', refreshToken);
    return { token, user };
  }

  async logout() {
    await this.instance.post('/auth/logout');
    localStorage.removeItem('training_token');
    localStorage.removeItem('training_refresh_token');
  }

  async refreshToken() {
    const refreshToken = localStorage.getItem('training_refresh_token');
    const response = await this.instance.post('/auth/refresh', { refreshToken });
    const { token } = response.data;
    localStorage.setItem('training_token', token);
    return token;
  }

  // Dashboard
  async getDashboard() {
    const response = await this.instance.get('/training/dashboard');
    return response.data;
  }

  // Learning Paths
  async getLearningPaths(role: string) {
    const response = await this.instance.get(`/training/paths/${role}`);
    return response.data;
  }

  // Courses
  async getCourses(params?: {
    category?: string;
    difficulty?: string;
    language?: string;
    page?: number;
    limit?: number;
  }) {
    const response = await this.instance.get('/training/courses', { params });
    return response.data;
  }

  async getCourse(courseId: string) {
    const response = await this.instance.get(`/training/courses/${courseId}`);
    return response.data;
  }

  async enrollInCourse(courseId: string, schedulePreference?: 'immediate' | 'scheduled', scheduledDate?: string) {
    const response = await this.instance.post('/training/enroll', {
      course_id: courseId,
      schedule_preference: schedulePreference || 'immediate',
      scheduled_date: scheduledDate,
    });
    return response.data;
  }

  // Progress
  async getProgress(courseId: string) {
    const response = await this.instance.get(`/training/progress/${courseId}`);
    return response.data;
  }

  async updateProgress(courseId: string, moduleId: string, progressPercentage: number, timeSpent: number) {
    const response = await this.instance.post(`/training/progress/${courseId}`, {
      module_id: moduleId,
      progress_percentage: progressPercentage,
      time_spent: timeSpent,
    });
    return response.data;
  }

  async updateVideoProgress(courseId: string, moduleId: string, currentTime: number, duration: number) {
    const progressPercentage = (currentTime / duration) * 100;
    return this.updateProgress(courseId, moduleId, progressPercentage, Math.floor(currentTime / 60));
  }

  // Assessments
  async startAssessment(assessmentId: string, courseId: string) {
    const response = await this.instance.post('/assessments/start', {
      assessment_id: assessmentId,
      course_id: courseId,
    });
    return response.data;
  }

  async submitAssessment(sessionId: string, answers: Array<{ question_id: string; answer: string }>, timeTaken: number) {
    const response = await this.instance.post('/assessments/submit', {
      session_id: sessionId,
      answers,
      time_taken: timeTaken,
    });
    return response.data;
  }

  async getAssessmentHistory(courseId: string) {
    const response = await this.instance.get(`/assessments/history/${courseId}`);
    return response.data;
  }

  // Certificates
  async getCertificates() {
    const response = await this.instance.get('/certificates');
    return response.data;
  }

  async downloadCertificate(certificateId: string) {
    const response = await this.instance.get(`/certificates/${certificateId}/download`, {
      responseType: 'blob',
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `certificate-${certificateId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
  }

  async verifyCertificate(verificationCode: string) {
    const response = await this.instance.get(`/certificates/verify/${verificationCode}`);
    return response.data;
  }

  // Achievements
  async getAchievements() {
    const response = await this.instance.get('/achievements');
    return response.data;
  }

  // Notifications
  async getNotifications() {
    const response = await this.instance.get('/notifications');
    return response.data;
  }

  async markNotificationRead(notificationId: string) {
    await this.instance.patch(`/notifications/${notificationId}/read`);
  }

  async markAllNotificationsRead() {
    await this.instance.patch('/notifications/read-all');
  }

  // Feedback
  async submitFeedback(enrollmentId: string, courseId: string, rating: number, comments?: string, wouldRecommend?: boolean, tags?: string[]) {
    const response = await this.instance.post('/feedback', {
      enrollment_id: enrollmentId,
      course_id: courseId,
      rating,
      comments,
      would_recommend: wouldRecommend,
      tags,
    });
    return response.data;
  }

  // Team Management (for managers)
  async getTeamProgress() {
    const response = await this.instance.get('/team/progress');
    return response.data;
  }

  async assignCourseToTeam(courseId: string, userIds: string[], dueDate?: string) {
    const response = await this.instance.post('/team/assign', {
      course_id: courseId,
      user_ids: userIds,
      due_date: dueDate,
    });
    return response.data;
  }

  // Analytics
  async getAnalytics(type: 'personal' | 'team' | 'course', params?: any) {
    const response = await this.instance.get(`/analytics/${type}`, { params });
    return response.data;
  }

  // Practice Environment
  async createPracticeSession(scenario: string) {
    const response = await this.instance.post('/practice/provision', { scenario });
    return response.data;
  }

  async resetPracticeSession(sessionId: string) {
    await this.instance.post(`/practice/${sessionId}/reset`);
  }

  async validatePracticeExercise(sessionId: string, exerciseId: string) {
    const response = await this.instance.post(`/practice/${sessionId}/validate`, { exercise_id: exerciseId });
    return response.data;
  }

  // Search
  async searchCourses(query: string, filters?: any) {
    const response = await this.instance.get('/search/courses', {
      params: { q: query, ...filters },
    });
    return response.data;
  }

  // User Profile
  async getProfile() {
    const response = await this.instance.get('/profile');
    return response.data;
  }

  async updateProfile(data: {
    languagePreference?: string;
    learningStyle?: string;
    notificationPreferences?: any;
  }) {
    const response = await this.instance.patch('/profile', data);
    return response.data;
  }
}

export const api = new ApiService();