import React, { useRef, useEffect, useState, useCallback } from 'react';
import ReactPlayer from 'react-player';
import { api } from '@/services/api';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize, 
  Settings,
  SkipBack,
  SkipForward,
  Loader2
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { useDebounce } from '@/hooks/useDebounce';

interface VideoPlayerProps {
  url: string;
  courseId: string;
  moduleId: string;
  onProgress?: (progress: number) => void;
  onComplete?: () => void;
  startTime?: number;
  autoplay?: boolean;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  url,
  courseId,
  moduleId,
  onProgress,
  onComplete,
  startTime = 0,
  autoplay = false
}) => {
  const playerRef = useRef<ReactPlayer>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastUpdateRef = useRef(0);
  
  const [playing, setPlaying] = useState(autoplay);
  const [volume, setVolume] = useState(0.8);
  const [muted, setMuted] = useState(false);
  const [played, setPlayed] = useState(0);
  const [loaded, setLoaded] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seeking, setSeeking] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [buffering, setBuffering] = useState(false);
  const [ready, setReady] = useState(false);

  const debouncedProgress = useDebounce(played, 1000);

  // Hide controls after inactivity
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    const handleMouseMove = () => {
      setShowControls(true);
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        if (playing) setShowControls(false);
      }, 3000);
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('mousemove', handleMouseMove);
      container.addEventListener('touchstart', handleMouseMove);
    }

    return () => {
      if (container) {
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('touchstart', handleMouseMove);
      }
      clearTimeout(timeout);
    };
  }, [playing]);

  // Update progress on server
  useEffect(() => {
    if (debouncedProgress > 0 && duration > 0 && ready) {
      const currentTime = debouncedProgress * duration;
      
      // Update every 10 seconds
      if (currentTime - lastUpdateRef.current >= 10) {
        lastUpdateRef.current = currentTime;
        
        api.updateVideoProgress(
          courseId,
          moduleId,
          currentTime,
          duration
        ).catch(console.error);
        
        onProgress?.(debouncedProgress * 100);
      }
    }
  }, [debouncedProgress, duration, courseId, moduleId, onProgress, ready]);

  const handleReady = useCallback(() => {
    setReady(true);
    if (startTime > 0 && playerRef.current) {
      playerRef.current.seekTo(startTime, 'seconds');
    }
  }, [startTime]);

  const handleProgress = (state: { played: number; loaded: number }) => {
    if (!seeking) {
      setPlayed(state.played);
      setLoaded(state.loaded);
    }
  };

  const handleDuration = (dur: number) => {
    setDuration(dur);
  };

  const handleEnded = () => {
    setPlaying(false);
    if (played >= 0.9) {
      onComplete?.();
    }
  };

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPlayed(parseFloat(e.target.value));
  };

  const handleSeekMouseDown = () => {
    setSeeking(true);
  };

  const handleSeekMouseUp = (e: React.MouseEvent<HTMLInputElement>) => {
    setSeeking(false);
    if (playerRef.current) {
      playerRef.current.seekTo(parseFloat(e.currentTarget.value));
    }
  };

  const handleSkip = (seconds: number) => {
    if (playerRef.current && duration) {
      const currentTime = played * duration;
      const newTime = Math.max(0, Math.min(duration, currentTime + seconds));
      playerRef.current.seekTo(newTime, 'seconds');
    }
  };

  const handlePlaybackRateChange = () => {
    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2];
    const currentIndex = rates.indexOf(playbackRate);
    const nextIndex = (currentIndex + 1) % rates.length;
    setPlaybackRate(rates[nextIndex]);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement && containerRef.current) {
      containerRef.current.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div 
      ref={containerRef}
      className="relative bg-black rounded-lg overflow-hidden group"
      style={{ paddingTop: '56.25%' }}
    >
      <div className="absolute inset-0">
        <ReactPlayer
          ref={playerRef}
          url={url}
          playing={playing}
          volume={volume}
          muted={muted}
          playbackRate={playbackRate}
          width="100%"
          height="100%"
          onReady={handleReady}
          onProgress={handleProgress}
          onDuration={handleDuration}
          onEnded={handleEnded}
          onBuffer={() => setBuffering(true)}
          onBufferEnd={() => setBuffering(false)}
          onError={(e) => console.error('Video error:', e)}
          config={{
            file: {
              attributes: {
                controlsList: 'nodownload',
                playsInline: true
              }
            }
          }}
        />

        {/* Loading Indicator */}
        {(buffering || !ready) && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <Loader2 className="w-12 h-12 text-white animate-spin" />
          </div>
        )}

        {/* Custom Controls */}
        <div className={cn(
          'absolute inset-0 flex flex-col justify-end transition-opacity duration-300',
          showControls ? 'opacity-100' : 'opacity-0'
        )}>
          {/* Gradient Background */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent pointer-events-none" />

          {/* Control Bar */}
          <div className="relative p-4 space-y-2">
            {/* Progress Bar */}
            <div className="relative group/progress">
              <input
                type="range"
                min={0}
                max={0.999999}
                step="any"
                value={played}
                onChange={handleSeekChange}
                onMouseDown={handleSeekMouseDown}
                onMouseUp={handleSeekMouseUp}
                className="w-full h-1 bg-white/30 rounded-lg appearance-none cursor-pointer 
                         [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 
                         [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-primary-500 
                         [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer
                         group-hover/progress:[&::-webkit-slider-thumb]:w-4 
                         group-hover/progress:[&::-webkit-slider-thumb]:h-4
                         transition-all duration-200"
                style={{
                  background: `linear-gradient(to right, #FF6B35 0%, #FF6B35 ${played * 100}%, rgba(255, 255, 255, 0.3) ${played * 100}%, rgba(255, 255, 255, 0.3) 100%)`
                }}
              />
              <div 
                className="absolute top-0 left-0 h-1 bg-white/20 rounded-lg pointer-events-none"
                style={{ width: `${loaded * 100}%` }}
              />
            </div>

            {/* Control Buttons */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {/* Play/Pause */}
                <button
                  onClick={() => setPlaying(!playing)}
                  className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  {playing ? <Pause size={20} /> : <Play size={20} />}
                </button>

                {/* Skip Buttons */}
                <button
                  onClick={() => handleSkip(-10)}
                  className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  <SkipBack size={20} />
                </button>
                <button
                  onClick={() => handleSkip(10)}
                  className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  <SkipForward size={20} />
                </button>

                {/* Volume */}
                <button
                  onClick={() => setMuted(!muted)}
                  className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  {muted || volume === 0 ? <VolumeX size={20} /> : <Volume2 size={20} />}
                </button>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={muted ? 0 : volume}
                  onChange={(e) => {
                    setVolume(parseFloat(e.target.value));
                    setMuted(false);
                  }}
                  className="w-20 h-1 bg-white/30 rounded-lg appearance-none cursor-pointer 
                           [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 
                           [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white 
                           [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer"
                />

                {/* Time Display */}
                <div className="text-white text-sm font-mono">
                  {formatTime(played * duration)} / {formatTime(duration)}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Playback Speed */}
                <button
                  onClick={handlePlaybackRateChange}
                  className="px-2 py-1 text-white text-sm hover:bg-white/20 rounded transition-colors"
                >
                  {playbackRate}x
                </button>

                {/* Settings */}
                <button
                  className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  <Settings size={20} />
                </button>

                {/* Fullscreen */}
                <button
                  onClick={toggleFullscreen}
                  className="p-2 text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  <Maximize size={20} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};