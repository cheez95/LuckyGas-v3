import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Dimensions,
  StatusBar,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import {
  Text,
  IconButton,
  Surface,
  Button,
  ProgressBar,
  Portal,
  Dialog,
  RadioButton,
} from 'react-native-paper';
import Video, { OnLoadData, OnProgressData } from 'react-native-video';
import Orientation from 'react-native-orientation-locker';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Toast from 'react-native-toast-message';

import { useAuth } from '@/contexts/AuthContext';
import { useOffline } from '@/contexts/OfflineContext';
import { trainingService } from '@/services/training';
import { VideoControls } from '@/components/video/VideoControls';
import { VideoOverlay } from '@/components/video/VideoOverlay';
import { formatDuration } from '@/utils/format';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

interface VideoPlayerScreenProps {
  moduleId: string;
  videoUrl: string;
  title: string;
  nextModuleId?: string;
}

export function VideoPlayerScreen() {
  const navigation = useNavigation();
  const route = useRoute();
  const { moduleId, videoUrl, title, nextModuleId } = route.params as VideoPlayerScreenProps;
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const { isOffline } = useOffline();
  const queryClient = useQueryClient();
  
  const videoRef = useRef<Video>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isBuffering, setIsBuffering] = useState(false);
  const [showPlaybackDialog, setShowPlaybackDialog] = useState(false);
  const [lastWatchedPosition, setLastWatchedPosition] = useState(0);
  const [hasCompletedOnce, setHasCompletedOnce] = useState(false);

  // Auto-hide controls
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (showControls && isPlaying) {
      timer = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
    return () => clearTimeout(timer);
  }, [showControls, isPlaying]);

  // Update progress mutation
  const updateProgressMutation = useMutation({
    mutationFn: async (data: { progress: number; completed: boolean }) => {
      if (isOffline) {
        // Queue for later sync
        return;
      }
      return trainingService.updateModuleProgress(moduleId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['progress', moduleId]);
      queryClient.invalidateQueries(['enrollments', user?.id]);
    },
  });

  // Save progress periodically
  useEffect(() => {
    const interval = setInterval(() => {
      if (isPlaying && currentTime > 0) {
        const progress = Math.round((currentTime / duration) * 100);
        updateProgressMutation.mutate({ progress, completed: false });
        setLastWatchedPosition(currentTime);
      }
    }, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, [currentTime, duration, isPlaying]);

  const handleLoad = useCallback((data: OnLoadData) => {
    setDuration(data.duration);
    setIsLoading(false);
    
    // Resume from last position if available
    if (lastWatchedPosition > 0 && videoRef.current) {
      videoRef.current.seek(lastWatchedPosition);
    }
  }, [lastWatchedPosition]);

  const handleProgress = useCallback((data: OnProgressData) => {
    setCurrentTime(data.currentTime);
    
    // Check if video is completed (within last 5 seconds)
    if (!hasCompletedOnce && data.currentTime > duration - 5) {
      setHasCompletedOnce(true);
      updateProgressMutation.mutate({ progress: 100, completed: true });
      
      // Show completion toast
      Toast.show({
        type: 'success',
        text1: '模組完成！',
        text2: nextModuleId ? '準備進入下一個模組' : '恭喜完成本課程！',
      });
    }
  }, [duration, hasCompletedOnce, nextModuleId]);

  const handleBuffer = useCallback((data: { isBuffering: boolean }) => {
    setIsBuffering(data.isBuffering);
  }, []);

  const handleError = useCallback((error: any) => {
    console.error('Video error:', error);
    Alert.alert(
      '播放錯誤',
      '無法播放影片，請檢查網路連線或稍後再試。',
      [
        { text: '重試', onPress: () => videoRef.current?.seek(0) },
        { text: '返回', onPress: () => navigation.goBack() },
      ]
    );
  }, [navigation]);

  const togglePlayPause = useCallback(() => {
    setIsPlaying(!isPlaying);
    setShowControls(true);
  }, [isPlaying]);

  const handleSeek = useCallback((time: number) => {
    videoRef.current?.seek(time);
    setCurrentTime(time);
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) {
      Orientation.lockToPortrait();
      StatusBar.setHidden(false);
    } else {
      Orientation.lockToLandscape();
      StatusBar.setHidden(true);
    }
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  const handlePlaybackRateChange = useCallback((rate: string) => {
    const numRate = parseFloat(rate);
    setPlaybackRate(numRate);
    setShowPlaybackDialog(false);
  }, []);

  const handleBack = useCallback(() => {
    if (isFullscreen) {
      toggleFullscreen();
    } else {
      // Save current progress before leaving
      const progress = Math.round((currentTime / duration) * 100);
      updateProgressMutation.mutate({ progress, completed: false });
      navigation.goBack();
    }
  }, [isFullscreen, currentTime, duration, navigation, toggleFullscreen]);

  const handleNext = useCallback(() => {
    if (nextModuleId) {
      navigation.replace('VideoPlayer', {
        moduleId: nextModuleId,
        // Fetch next module details
      });
    }
  }, [nextModuleId, navigation]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      Orientation.lockToPortrait();
      StatusBar.setHidden(false);
      
      // Save final progress
      if (currentTime > 0) {
        const progress = Math.round((currentTime / duration) * 100);
        updateProgressMutation.mutate({ progress, completed: progress >= 95 });
      }
    };
  }, [currentTime, duration]);

  const videoStyle = isFullscreen
    ? styles.fullscreenVideo
    : styles.video;

  return (
    <View style={[styles.container, isFullscreen && styles.fullscreenContainer]}>
      <StatusBar hidden={isFullscreen} />
      
      <View style={videoStyle}>
        <Video
          ref={videoRef}
          source={{ uri: videoUrl }}
          style={StyleSheet.absoluteFillObject}
          paused={!isPlaying}
          rate={playbackRate}
          volume={1.0}
          resizeMode={isFullscreen ? 'contain' : 'contain'}
          onLoad={handleLoad}
          onProgress={handleProgress}
          onBuffer={handleBuffer}
          onError={handleError}
          onEnd={() => setIsPlaying(false)}
          progressUpdateInterval={1000}
          playInBackground={false}
          playWhenInactive={false}
        />

        {isLoading && (
          <View style={styles.loadingOverlay}>
            <ActivityIndicator size="large" color="#FFFFFF" />
            <Text style={styles.loadingText}>載入影片中...</Text>
          </View>
        )}

        {isBuffering && !isLoading && (
          <View style={styles.bufferingOverlay}>
            <ActivityIndicator size="small" color="#FFFFFF" />
          </View>
        )}

        <VideoOverlay
          visible={showControls}
          onPress={() => setShowControls(!showControls)}
        >
          <VideoControls
            isPlaying={isPlaying}
            currentTime={currentTime}
            duration={duration}
            isFullscreen={isFullscreen}
            playbackRate={playbackRate}
            onPlayPause={togglePlayPause}
            onSeek={handleSeek}
            onFullscreen={toggleFullscreen}
            onBack={handleBack}
            onPlaybackRate={() => setShowPlaybackDialog(true)}
          />
        </VideoOverlay>
      </View>

      {!isFullscreen && (
        <Surface style={styles.infoSection} elevation={2}>
          <Text variant="titleLarge" style={styles.title}>
            {title}
          </Text>
          
          <View style={styles.progressInfo}>
            <Text variant="bodyMedium">
              學習進度: {Math.round((currentTime / duration) * 100)}%
            </Text>
            <ProgressBar
              progress={currentTime / duration}
              style={styles.progressBar}
            />
          </View>

          {nextModuleId && (
            <Button
              mode="contained"
              onPress={handleNext}
              style={styles.nextButton}
              disabled={!hasCompletedOnce}
            >
              下一個模組
            </Button>
          )}
        </Surface>
      )}

      <Portal>
        <Dialog
          visible={showPlaybackDialog}
          onDismiss={() => setShowPlaybackDialog(false)}
        >
          <Dialog.Title>播放速度</Dialog.Title>
          <Dialog.Content>
            <RadioButton.Group
              onValueChange={handlePlaybackRateChange}
              value={playbackRate.toString()}
            >
              <RadioButton.Item label="0.5x" value="0.5" />
              <RadioButton.Item label="0.75x" value="0.75" />
              <RadioButton.Item label="正常" value="1.0" />
              <RadioButton.Item label="1.25x" value="1.25" />
              <RadioButton.Item label="1.5x" value="1.5" />
              <RadioButton.Item label="2x" value="2.0" />
            </RadioButton.Group>
          </Dialog.Content>
        </Dialog>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  fullscreenContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 999,
  },
  video: {
    width: screenWidth,
    height: screenWidth * (9 / 16),
    backgroundColor: '#000000',
  },
  fullscreenVideo: {
    width: screenHeight,
    height: screenWidth,
    backgroundColor: '#000000',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  loadingText: {
    color: '#FFFFFF',
    marginTop: 8,
  },
  bufferingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  infoSection: {
    flex: 1,
    padding: 16,
    backgroundColor: '#FFFFFF',
  },
  title: {
    marginBottom: 16,
  },
  progressInfo: {
    marginBottom: 24,
  },
  progressBar: {
    marginTop: 8,
    height: 8,
    borderRadius: 4,
  },
  nextButton: {
    marginTop: 16,
  },
});