import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authService } from './auth';

// Configure notification handler
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

interface NotificationConfig {
  dailyReminder: boolean;
  courseUpdates: boolean;
  achievementUnlocked: boolean;
  weeklyReport: boolean;
  reminderTime: string; // HH:MM format
}

const DEFAULT_CONFIG: NotificationConfig = {
  dailyReminder: true,
  courseUpdates: true,
  achievementUnlocked: true,
  weeklyReport: true,
  reminderTime: '09:00',
};

class NotificationService {
  private config: NotificationConfig = DEFAULT_CONFIG;
  private notificationListener: any;
  private responseListener: any;

  async initialize() {
    // Load saved configuration
    await this.loadConfig();

    // Request permissions
    const hasPermission = await this.requestPermissions();
    if (!hasPermission) {
      console.log('Notification permissions not granted');
      return;
    }

    // Get push token
    const token = await this.registerForPushNotifications();
    if (token) {
      // Send token to backend
      await this.updatePushToken(token);
    }

    // Setup listeners
    this.setupListeners();

    // Schedule notifications
    await this.scheduleNotifications();
  }

  async requestPermissions(): Promise<boolean> {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    return finalStatus === 'granted';
  }

  async registerForPushNotifications(): Promise<string | null> {
    if (!Device.isDevice) {
      console.log('Must use physical device for Push Notifications');
      return null;
    }

    try {
      const token = await Notifications.getExpoPushTokenAsync({
        projectId: 'your-project-id', // Replace with your project ID
      });
      return token.data;
    } catch (error) {
      console.error('Error getting push token:', error);
      return null;
    }
  }

  async updatePushToken(token: string) {
    try {
      await authService.updatePushToken(token);
    } catch (error) {
      console.error('Error updating push token:', error);
    }
  }

  setupListeners() {
    // Handle incoming notifications when app is in foreground
    this.notificationListener = Notifications.addNotificationReceivedListener(
      notification => {
        console.log('Notification received:', notification);
      }
    );

    // Handle notification responses (when user taps on notification)
    this.responseListener = Notifications.addNotificationResponseReceivedListener(
      response => {
        const { notification } = response;
        this.handleNotificationResponse(notification);
      }
    );
  }

  handleNotificationResponse(notification: Notifications.Notification) {
    const { data } = notification.request.content;
    
    // Navigate based on notification type
    if (data.type === 'course_update') {
      // Navigate to course
      // navigationRef.navigate('CourseDetail', { courseId: data.courseId });
    } else if (data.type === 'achievement_unlocked') {
      // Navigate to achievements
      // navigationRef.navigate('Achievements');
    } else if (data.type === 'weekly_report') {
      // Navigate to progress
      // navigationRef.navigate('Progress');
    }
  }

  async scheduleNotifications() {
    // Cancel all existing scheduled notifications
    await Notifications.cancelAllScheduledNotificationsAsync();

    if (this.config.dailyReminder) {
      await this.scheduleDailyReminder();
    }

    if (this.config.weeklyReport) {
      await this.scheduleWeeklyReport();
    }
  }

  async scheduleDailyReminder() {
    const [hours, minutes] = this.config.reminderTime.split(':').map(Number);
    
    await Notifications.scheduleNotificationAsync({
      content: {
        title: '學習提醒 📚',
        body: '別忘了今天的學習目標！繼續保持學習動力 💪',
        data: { type: 'daily_reminder' },
        sound: true,
      },
      trigger: {
        hour: hours,
        minute: minutes,
        repeats: true,
      },
    });
  }

  async scheduleWeeklyReport() {
    // Schedule for every Sunday at 6 PM
    await Notifications.scheduleNotificationAsync({
      content: {
        title: '本週學習報告 📊',
        body: '查看您本週的學習成果和進度！',
        data: { type: 'weekly_report' },
        sound: true,
      },
      trigger: {
        weekday: 1, // Sunday
        hour: 18,
        minute: 0,
        repeats: true,
      },
    });
  }

  async sendLocalNotification(
    title: string,
    body: string,
    data?: any,
    delay?: number
  ) {
    const content: Notifications.NotificationContentInput = {
      title,
      body,
      data,
      sound: true,
    };

    if (delay) {
      await Notifications.scheduleNotificationAsync({
        content,
        trigger: {
          seconds: delay,
        },
      });
    } else {
      await Notifications.presentNotificationAsync(content);
    }
  }

  async sendCourseCompletionNotification(courseName: string, nextCourse?: string) {
    const body = nextCourse
      ? `恭喜完成「${courseName}」！準備好開始「${nextCourse}」了嗎？`
      : `恭喜完成「${courseName}」！繼續探索更多課程吧！`;

    await this.sendLocalNotification(
      '課程完成！🎉',
      body,
      { type: 'course_completed' }
    );
  }

  async sendAchievementNotification(achievementName: string, points: number) {
    await this.sendLocalNotification(
      '成就解鎖！🏆',
      `恭喜獲得「${achievementName}」成就，獲得 ${points} 點數！`,
      { type: 'achievement_unlocked' }
    );
  }

  async sendStreakNotification(streakDays: number) {
    const milestones = [7, 30, 100, 365];
    if (milestones.includes(streakDays)) {
      await this.sendLocalNotification(
        '連續學習里程碑！🔥',
        `太棒了！您已經連續學習 ${streakDays} 天了！`,
        { type: 'streak_milestone' }
      );
    }
  }

  async updateConfig(config: Partial<NotificationConfig>) {
    this.config = { ...this.config, ...config };
    await this.saveConfig();
    await this.scheduleNotifications();
  }

  async loadConfig() {
    try {
      const saved = await AsyncStorage.getItem('notification_config');
      if (saved) {
        this.config = JSON.parse(saved);
      }
    } catch (error) {
      console.error('Error loading notification config:', error);
    }
  }

  async saveConfig() {
    try {
      await AsyncStorage.setItem(
        'notification_config',
        JSON.stringify(this.config)
      );
    } catch (error) {
      console.error('Error saving notification config:', error);
    }
  }

  getConfig(): NotificationConfig {
    return this.config;
  }

  cleanup() {
    if (this.notificationListener) {
      Notifications.removeNotificationSubscription(this.notificationListener);
    }
    if (this.responseListener) {
      Notifications.removeNotificationSubscription(this.responseListener);
    }
  }
}

export const notificationService = new NotificationService();

export async function setupNotifications() {
  await notificationService.initialize();
}