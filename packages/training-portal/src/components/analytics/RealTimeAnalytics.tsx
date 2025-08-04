import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  IconButton,
  Tooltip,
  Badge,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';
import {
  FiberManualRecord,
  Person,
  PlayArrow,
  School,
  EmojiEvents,
  Refresh,
  Speed,
} from '@mui/icons-material';
import { animated, useSpring } from '@react-spring/web';
import { format } from 'date-fns';
import { zhTW } from 'date-fns/locale';
import useWebSocket from 'react-use-websocket';

import { useAuth } from '@/contexts/AuthContext';
import { API_URL } from '@/config';

interface RealTimeData {
  active_users: number;
  active_sessions: Session[];
  recent_completions: Completion[];
  recent_achievements: Achievement[];
  current_stats: {
    videos_playing: number;
    quizzes_in_progress: number;
    modules_completed_today: number;
    avg_session_duration: number;
  };
}

interface Session {
  user_id: string;
  user_name: string;
  department: string;
  current_activity: string;
  duration_minutes: number;
  progress: number;
}

interface Completion {
  user_id: string;
  user_name: string;
  course_title: string;
  completed_at: string;
  score?: number;
}

interface Achievement {
  user_id: string;
  user_name: string;
  achievement_title: string;
  points: number;
  timestamp: string;
}

export function RealTimeAnalytics() {
  const { user } = useAuth();
  const [data, setData] = useState<RealTimeData>({
    active_users: 0,
    active_sessions: [],
    recent_completions: [],
    recent_achievements: [],
    current_stats: {
      videos_playing: 0,
      quizzes_in_progress: 0,
      modules_completed_today: 0,
      avg_session_duration: 0,
    },
  });

  const socketUrl = `${API_URL.replace('http', 'ws')}/ws/analytics?token=${user?.access_token}`;
  
  const { sendMessage, lastMessage, readyState } = useWebSocket(socketUrl, {
    shouldReconnect: () => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
  });

  useEffect(() => {
    if (lastMessage !== null) {
      const update = JSON.parse(lastMessage.data);
      setData(prevData => ({
        ...prevData,
        ...update,
      }));
    }
  }, [lastMessage]);

  const pulseAnimation = useSpring({
    from: { scale: 0.95, opacity: 0.8 },
    to: { scale: 1, opacity: 1 },
    loop: true,
    config: { duration: 2000 },
  });

  const handleRefresh = () => {
    sendMessage(JSON.stringify({ action: 'refresh' }));
  };

  const getActivityIcon = (activity: string) => {
    if (activity.includes('video')) return <PlayArrow />;
    if (activity.includes('quiz')) return <School />;
    if (activity.includes('course')) return <School />;
    return <Person />;
  };

  const getActivityColor = (activity: string) => {
    if (activity.includes('video')) return 'primary';
    if (activity.includes('quiz')) return 'secondary';
    if (activity.includes('course')) return 'success';
    return 'default';
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h5">即時監控面板</Typography>
          <animated.div style={pulseAnimation}>
            <Chip
              icon={<FiberManualRecord />}
              label={readyState === 1 ? '已連線' : '連線中...'}
              color={readyState === 1 ? 'success' : 'warning'}
              size="small"
            />
          </animated.div>
        </Box>
        
        <IconButton onClick={handleRefresh}>
          <Refresh />
        </IconButton>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    線上用戶
                  </Typography>
                  <Typography variant="h3">
                    {data.active_users}
                  </Typography>
                </Box>
                <Badge badgeContent={data.active_users} color="success" max={999}>
                  <Person sx={{ fontSize: 40, color: 'success.main' }} />
                </Badge>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    播放中影片
                  </Typography>
                  <Typography variant="h3">
                    {data.current_stats.videos_playing}
                  </Typography>
                </Box>
                <PlayArrow sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    進行中測驗
                  </Typography>
                  <Typography variant="h3">
                    {data.current_stats.quizzes_in_progress}
                  </Typography>
                </Box>
                <School sx={{ fontSize: 40, color: 'secondary.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography color="text.secondary" gutterBottom>
                    今日完成
                  </Typography>
                  <Typography variant="h3">
                    {data.current_stats.modules_completed_today}
                  </Typography>
                </Box>
                <EmojiEvents sx={{ fontSize: 40, color: 'warning.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Active Sessions */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400, overflow: 'hidden' }}>
            <Typography variant="h6" gutterBottom>
              目前活動
            </Typography>
            
            <List sx={{ overflow: 'auto', maxHeight: 320 }}>
              {data.active_sessions.map((session) => (
                <ListItem key={session.user_id}>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: `${getActivityColor(session.current_activity)}.main` }}>
                      {getActivityIcon(session.current_activity)}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1">{session.user_name}</Typography>
                        <Chip label={session.department} size="small" />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          {session.current_activity}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                          <LinearProgress 
                            variant="determinate" 
                            value={session.progress} 
                            sx={{ flexGrow: 1, height: 6, borderRadius: 3 }}
                          />
                          <Typography variant="caption">{session.progress}%</Typography>
                        </Box>
                      </Box>
                    }
                  />
                  <Box sx={{ textAlign: 'right' }}>
                    <Chip 
                      icon={<Speed />}
                      label={`${session.duration_minutes} 分鐘`}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Recent Activities */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400, overflow: 'hidden' }}>
            <Typography variant="h6" gutterBottom>
              最新動態
            </Typography>
            
            <List sx={{ overflow: 'auto', maxHeight: 320 }}>
              {/* Recent Completions */}
              {data.recent_completions.map((completion, index) => (
                <ListItem key={`completion-${index}`} sx={{ py: 1 }}>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'success.main', width: 32, height: 32 }}>
                      ✓
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Typography variant="body2">
                        <strong>{completion.user_name}</strong> 完成了
                      </Typography>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="primary">
                          {completion.course_title}
                        </Typography>
                        {completion.score && (
                          <Chip 
                            label={`${completion.score} 分`} 
                            size="small" 
                            color="success"
                            sx={{ ml: 1 }}
                          />
                        )}
                        <Typography variant="caption" display="block" color="text.secondary">
                          {format(new Date(completion.completed_at), 'HH:mm', { locale: zhTW })}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}

              {/* Recent Achievements */}
              {data.recent_achievements.map((achievement, index) => (
                <ListItem key={`achievement-${index}`} sx={{ py: 1 }}>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'warning.main', width: 32, height: 32 }}>
                      🏆
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Typography variant="body2">
                        <strong>{achievement.user_name}</strong> 獲得成就
                      </Typography>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="warning.dark">
                          {achievement.achievement_title}
                        </Typography>
                        <Chip 
                          label={`+${achievement.points} 點`} 
                          size="small" 
                          color="warning"
                          sx={{ ml: 1 }}
                        />
                        <Typography variant="caption" display="block" color="text.secondary">
                          {format(new Date(achievement.timestamp), 'HH:mm', { locale: zhTW })}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>
      </Grid>

      {/* Average Session Duration */}
      <Paper sx={{ mt: 3, p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body1">
            平均學習時長: <strong>{data.current_stats.avg_session_duration} 分鐘</strong>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            即時更新 · 最後更新: {format(new Date(), 'HH:mm:ss', { locale: zhTW })}
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}