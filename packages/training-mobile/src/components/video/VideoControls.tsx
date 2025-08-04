import React from 'react';
import {
  StyleSheet,
  View,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import {
  Text,
  IconButton,
  Slider,
} from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatDuration } from '@/utils/format';

const { width: screenWidth } = Dimensions.get('window');

interface VideoControlsProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  isFullscreen: boolean;
  playbackRate: number;
  onPlayPause: () => void;
  onSeek: (time: number) => void;
  onFullscreen: () => void;
  onBack: () => void;
  onPlaybackRate: () => void;
  onSkipBack?: () => void;
  onSkipForward?: () => void;
}

export function VideoControls({
  isPlaying,
  currentTime,
  duration,
  isFullscreen,
  playbackRate,
  onPlayPause,
  onSeek,
  onFullscreen,
  onBack,
  onPlaybackRate,
  onSkipBack,
  onSkipForward,
}: VideoControlsProps) {
  const handleSliderChange = (value: number) => {
    onSeek(value);
  };

  const skipBackward = () => {
    const newTime = Math.max(0, currentTime - 10);
    onSeek(newTime);
  };

  const skipForward = () => {
    const newTime = Math.min(duration, currentTime + 10);
    onSeek(newTime);
  };

  return (
    <View style={styles.container}>
      {/* Top Controls */}
      <View style={styles.topControls}>
        <IconButton
          icon="arrow-left"
          iconColor="#FFFFFF"
          size={28}
          onPress={onBack}
        />
        
        <View style={styles.topRight}>
          <TouchableOpacity
            onPress={onPlaybackRate}
            style={styles.playbackRateButton}
          >
            <Text style={styles.playbackRateText}>
              {playbackRate}x
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Center Controls */}
      <View style={styles.centerControls}>
        <IconButton
          icon="rewind-10"
          iconColor="#FFFFFF"
          size={36}
          onPress={onSkipBack || skipBackward}
        />
        
        <IconButton
          icon={isPlaying ? 'pause' : 'play'}
          iconColor="#FFFFFF"
          size={48}
          onPress={onPlayPause}
          style={styles.playButton}
        />
        
        <IconButton
          icon="fast-forward-10"
          iconColor="#FFFFFF"
          size={36}
          onPress={onSkipForward || skipForward}
        />
      </View>

      {/* Bottom Controls */}
      <View style={styles.bottomControls}>
        <View style={styles.progressContainer}>
          <Text style={styles.timeText}>
            {formatDuration(currentTime)}
          </Text>
          
          <Slider
            style={styles.slider}
            value={currentTime}
            minimumValue={0}
            maximumValue={duration}
            onValueChange={handleSliderChange}
            thumbColor="#FFFFFF"
            minimumTrackTintColor="#FF6B35"
            maximumTrackTintColor="rgba(255, 255, 255, 0.3)"
          />
          
          <Text style={styles.timeText}>
            {formatDuration(duration)}
          </Text>
        </View>
        
        <IconButton
          icon={isFullscreen ? 'fullscreen-exit' : 'fullscreen'}
          iconColor="#FFFFFF"
          size={28}
          onPress={onFullscreen}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
    padding: 16,
  },
  topControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  topRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  playbackRateButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  playbackRateText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  centerControls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    marginHorizontal: 24,
  },
  bottomControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 8,
  },
  slider: {
    flex: 1,
    marginHorizontal: 12,
    height: 40,
  },
  timeText: {
    color: '#FFFFFF',
    fontSize: 12,
    minWidth: 45,
    textAlign: 'center',
  },
});