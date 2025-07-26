import React, { useState, useEffect, useCallback } from 'react';
import { Alert, Badge, Button, Space, Spin, Typography } from 'antd';
import { 
  EnvironmentOutlined, 
  LoadingOutlined, 
  ReloadOutlined,
  CheckCircleOutlined,
  WarningOutlined 
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { gpsService, Position } from '../../../services/gps.service';
import './GPSTracker.css';

const { Text } = Typography;

interface GPSTrackerProps {
  onPositionUpdate?: (position: Position) => void;
  autoStart?: boolean;
  showDetails?: boolean;
}

const GPSTracker: React.FC<GPSTrackerProps> = ({ 
  onPositionUpdate, 
  autoStart = false,
  showDetails = false 
}) => {
  const { t } = useTranslation();
  const [isTracking, setIsTracking] = useState(false);
  const [position, setPosition] = useState<Position | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [accuracy, setAccuracy] = useState<'high' | 'medium' | 'low'>('high');

  const updateAccuracy = useCallback((position: Position) => {
    if (position.accuracy <= 10) {
      setAccuracy('high');
    } else if (position.accuracy <= 50) {
      setAccuracy('medium');
    } else {
      setAccuracy('low');
    }
  }, []);

  const handlePositionUpdate = useCallback((newPosition: Position) => {
    setPosition(newPosition);
    updateAccuracy(newPosition);
    setError(null);
    
    if (onPositionUpdate) {
      onPositionUpdate(newPosition);
    }

    // Store position in localStorage for offline support
    localStorage.setItem('lastDriverPosition', JSON.stringify(newPosition));
  }, [onPositionUpdate, updateAccuracy]);

  const handleError = useCallback((gpsError: { code: number; message: string }) => {
    setError(gpsError.message);
    setIsTracking(false);
    setLoading(false);
  }, []);

  const startTracking = useCallback(async () => {
    if (!gpsService.isAvailable()) {
      setError(t('driver.gps.notSupported'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Get initial position
      const initialPosition = await gpsService.getCurrentPosition();
      handlePositionUpdate(initialPosition);

      // Start continuous tracking
      const success = gpsService.startTracking(handlePositionUpdate, handleError);
      if (success) {
        setIsTracking(true);
        setLoading(false);
      } else {
        setError(t('driver.gps.startError'));
        setLoading(false);
      }
    } catch (err: any) {
      setError(err.message || t('driver.gps.error'));
      setLoading(false);
    }
  }, [handlePositionUpdate, handleError, t]);

  const stopTracking = useCallback(() => {
    gpsService.stopTracking();
    setIsTracking(false);
  }, []);

  const refreshPosition = useCallback(async () => {
    setLoading(true);
    try {
      const newPosition = await gpsService.getCurrentPosition();
      handlePositionUpdate(newPosition);
    } catch (err: any) {
      setError(err.message || t('driver.gps.error'));
    } finally {
      setLoading(false);
    }
  }, [handlePositionUpdate, t]);

  useEffect(() => {
    // Load last position from localStorage
    const lastPosition = localStorage.getItem('lastDriverPosition');
    if (lastPosition) {
      try {
        const parsed = JSON.parse(lastPosition);
        setPosition(parsed);
        updateAccuracy(parsed);
      } catch (e) {
        console.error('Failed to parse last position:', e);
      }
    }

    // Auto-start if requested
    if (autoStart) {
      startTracking();
    }

    // Cleanup on unmount
    return () => {
      if (isTracking) {
        gpsService.stopTracking();
      }
    };
  }, [autoStart]); // Only run on mount

  const getAccuracyColor = () => {
    switch (accuracy) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  const getAccuracyIcon = () => {
    switch (accuracy) {
      case 'high': return <CheckCircleOutlined />;
      case 'medium': return <WarningOutlined />;
      case 'low': return <WarningOutlined />;
      default: return <EnvironmentOutlined />;
    }
  };

  if (error) {
    return (
      <Alert
        message={t('driver.gps.error')}
        description={error}
        type="error"
        showIcon
        action={
          <Button size="small" onClick={startTracking}>
            {t('common.retry')}
          </Button>
        }
      />
    );
  }

  return (
    <div className="gps-tracker">
      <div className="gps-status">
        <Space align="center">
          {loading ? (
            <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
          ) : (
            <Badge
              status={isTracking ? 'processing' : 'default'}
              text={
                <Space>
                  <EnvironmentOutlined style={{ fontSize: 18 }} />
                  <Text strong>
                    {isTracking ? t('driver.gps.tracking') : t('driver.gps.notTracking')}
                  </Text>
                </Space>
              }
            />
          )}
        </Space>

        <Space>
          {!isTracking ? (
            <Button
              type="primary"
              icon={<EnvironmentOutlined />}
              onClick={startTracking}
              loading={loading}
              data-testid="start-gps-button"
            >
              {t('driver.gps.startTracking')}
            </Button>
          ) : (
            <>
              <Button
                icon={<ReloadOutlined />}
                onClick={refreshPosition}
                loading={loading}
              >
                {t('driver.gps.refresh')}
              </Button>
              <Button
                danger
                onClick={stopTracking}
                data-testid="stop-gps-button"
              >
                {t('driver.gps.stopTracking')}
              </Button>
            </>
          )}
        </Space>
      </div>

      {position && showDetails && (
        <div className="gps-details">
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div className="gps-detail-item">
              <Text type="secondary">{t('driver.gps.accuracy')}:</Text>
              <Badge
                status={getAccuracyColor()}
                text={
                  <Space>
                    {getAccuracyIcon()}
                    <Text>{position.accuracy.toFixed(0)}m</Text>
                  </Space>
                }
              />
            </div>
            
            <div className="gps-detail-item">
              <Text type="secondary">{t('driver.gps.coordinates')}:</Text>
              <Text copyable>
                {gpsService.formatPosition(position)}
              </Text>
            </div>

            {position.speed !== undefined && (
              <div className="gps-detail-item">
                <Text type="secondary">{t('driver.gps.speed')}:</Text>
                <Text>{(position.speed * 3.6).toFixed(1)} km/h</Text>
              </div>
            )}

            <div className="gps-detail-item">
              <Text type="secondary">{t('driver.gps.lastUpdate')}:</Text>
              <Text>{new Date(position.timestamp).toLocaleTimeString('zh-TW')}</Text>
            </div>
          </Space>
        </div>
      )}
    </div>
  );
};

export default GPSTracker;