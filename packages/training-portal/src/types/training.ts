export interface User {
  id: string;
  name: string;
  email: string;
  role: 'office_staff' | 'driver' | 'manager' | 'admin';
  department: string;
  avatar?: string;
}

export interface TrainingProfile {
  userId: string;
  languagePreference: 'zh-TW' | 'en';
  learningStyle: 'visual' | 'auditory' | 'kinesthetic' | 'mixed';
  totalLearningHours: number;
  currentStreak: number;
  longestStreak: number;
  pointsEarned: number;
  level: number;
  completedCourses: number;
  certificatesEarned: number;
  skills: Record<string, number>;
}

export interface Course {
  courseId: string;
  code: string;
  title: LocalizedText;
  description: LocalizedText;
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  durationMinutes: number;
  modules: Module[];
  prerequisites: string[];
  tags: string[];
  rating: number;
  enrollmentCount: number;
  thumbnailUrl?: string;
}

export interface Module {
  moduleId: string;
  title: LocalizedText;
  type: 'video' | 'reading' | 'quiz' | 'exercise' | 'discussion';
  contentUrl?: string;
  durationMinutes: number;
  order: number;
  isMandatory: boolean;
}

export interface LocalizedText {
  'zh-TW': string;
  en?: string;
}

export interface Enrollment {
  enrollmentId: string;
  courseId: string;
  userId: string;
  enrolledDate: string;
  status: 'enrolled' | 'in_progress' | 'completed' | 'failed' | 'expired';
  progressPercentage: number;
  lastAccessed?: string;
  completedDate?: string;
  finalScore?: number;
  course?: Course;
}

export interface LearningPath {
  pathId: string;
  name: LocalizedText;
  description: LocalizedText;
  targetRole: string;
  courses: LearningPathCourse[];
  totalDurationHours: number;
  isMandatory: boolean;
}

export interface LearningPathCourse {
  courseId: string;
  order: number;
  isMandatory: boolean;
  daysToComplete?: number;
  course?: Course;
}

export interface Assessment {
  assessmentId: string;
  courseId: string;
  moduleId?: string;
  title: LocalizedText;
  type: 'quiz' | 'exam' | 'assignment' | 'practical';
  timeLimitMinutes?: number;
  passPercentage: number;
  maxAttempts: number;
  questionCount: number;
}

export interface AssessmentSession {
  sessionId: string;
  assessmentId: string;
  questions: Question[];
  timeLimit?: number;
  startedAt: string;
}

export interface Question {
  questionId: string;
  questionText: LocalizedText;
  type: 'multiple_choice' | 'true_false' | 'short_answer' | 'essay' | 'matching';
  options?: string[];
  points: number;
  mediaUrl?: string;
}

export interface AssessmentResult {
  sessionId: string;
  score: number;
  passed: boolean;
  feedback?: string;
  incorrectQuestions: string[];
  timeTaken: number;
  attemptNumber: number;
}

export interface Certificate {
  certificateId: string;
  courseId: string;
  userId: string;
  certificateNumber: string;
  issuedDate: string;
  expiryDate?: string;
  pdfUrl: string;
  verificationCode: string;
  courseName?: LocalizedText;
}

export interface Achievement {
  achievementId: string;
  name: LocalizedText;
  description: LocalizedText;
  type: 'course_completion' | 'streak' | 'milestone' | 'special';
  earnedDate: string;
  iconUrl?: string;
  points: number;
}

export interface Progress {
  userId: string;
  courseId: string;
  modulesCompleted: string[];
  currentModule?: string;
  totalTimeSpent: number;
  lastActivity: string;
  bookmarks: Bookmark[];
}

export interface Bookmark {
  moduleId: string;
  timestamp: number;
  note?: string;
}

export interface Notification {
  notificationId: string;
  type: 'course_assigned' | 'deadline_reminder' | 'achievement_earned' | 'certificate_issued' | 'system';
  title: string;
  message: string;
  actionUrl?: string;
  isRead: boolean;
  createdAt: string;
  priority: 'low' | 'normal' | 'high';
}

export interface DashboardData {
  profile: TrainingProfile;
  enrollments: Enrollment[];
  recommendations: Course[];
  achievements: Achievement[];
  upcomingDeadlines: Enrollment[];
  learningStreak: {
    current: number;
    longest: number;
    todayCompleted: boolean;
  };
  teamProgress?: TeamProgress;
}

export interface TeamProgress {
  teamSize: number;
  averageProgress: number;
  completionRate: number;
  topPerformers: TeamMember[];
  courseStats: CourseStats[];
}

export interface TeamMember {
  userId: string;
  name: string;
  coursesCompleted: number;
  averageScore: number;
  totalHours: number;
}

export interface CourseStats {
  courseId: string;
  courseName: LocalizedText;
  enrolledCount: number;
  completedCount: number;
  averageScore: number;
  averageTime: number;
}

export interface VideoProgress {
  videoUrl: string;
  currentTime: number;
  duration: number;
  completed: boolean;
  lastWatched: string;
}

export interface LearningActivity {
  activityId: string;
  userId: string;
  activityType: string;
  resourceType: string;
  resourceId: string;
  action: string;
  durationSeconds: number;
  createdAt: string;
}

export interface Feedback {
  feedbackId: string;
  enrollmentId: string;
  courseId: string;
  rating: number;
  comments?: string;
  wouldRecommend: boolean;
  tags: string[];
  createdAt: string;
}