import React, { useEffect, useRef, useState } from 'react';
import { Card, Button, Space, Tag, Spin } from 'antd';
import { EnvironmentOutlined, AimOutlined } from '@ant-design/icons';

interface MapMarker {
  id: string;
  position: { lat: number; lng: number };
  title: string;
  type: 'depot' | 'customer' | 'driver';
  info?: string;
}

interface GoogleMapsPlaceholderProps {
  center?: { lat: number; lng: number };
  zoom?: number;
  markers?: MapMarker[];
  route?: Array<{ lat: number; lng: number }>;
  height?: string | number;
  showControls?: boolean;
  onMarkerClick?: (marker: MapMarker) => void;
}

const GoogleMapsPlaceholder: React.FC<GoogleMapsPlaceholderProps> = ({
  center = { lat: 25.0330, lng: 121.5654 }, // Default to Taipei
  zoom = 13,
  markers = [],
  route = [],
  height = 400,
  showControls = true,
  onMarkerClick,
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [currentZoom, setCurrentZoom] = useState(zoom);

  useEffect(() => {
    // Simulate map loading
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const handleZoomIn = () => {
    setCurrentZoom(prev => Math.min(prev + 1, 20));
  };

  const handleZoomOut = () => {
    setCurrentZoom(prev => Math.max(prev - 1, 1));
  };

  const handleCenterMap = () => {
    // In real implementation, this would center the map
    console.log('Centering map to:', center);
  };

  const getMarkerIcon = (type: string) => {
    switch (type) {
      case 'depot':
        return '🏭';
      case 'driver':
        return '🚚';
      case 'customer':
      default:
        return '📍';
    }
  };

  const getMarkerColor = (type: string) => {
    switch (type) {
      case 'depot':
        return '#1890ff';
      case 'driver':
        return '#52c41a';
      case 'customer':
      default:
        return '#ff4d4f';
    }
  };

  return (
    <Card
      className="google-maps-placeholder"
      bodyStyle={{ padding: 0 }}
      style={{ height: typeof height === 'number' ? `${height}px` : height }}
    >
      <div
        ref={mapRef}
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          background: 'linear-gradient(to bottom, #e6f7ff 0%, #bae7ff 100%)',
          overflow: 'hidden',
        }}
      >
        {loading ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            <Spin size="large" tip="載入地圖中..." />
          </div>
        ) : (
          <>
            {/* Placeholder map background */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: `
                  repeating-linear-gradient(
                    0deg,
                    rgba(0, 0, 0, 0.03),
                    rgba(0, 0, 0, 0.03) 50px,
                    transparent 50px,
                    transparent 100px
                  ),
                  repeating-linear-gradient(
                    90deg,
                    rgba(0, 0, 0, 0.03),
                    rgba(0, 0, 0, 0.03) 50px,
                    transparent 50px,
                    transparent 100px
                  )
                `,
              }}
            />

            {/* Center indicator */}
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: 24,
                color: '#1890ff',
              }}
            >
              <AimOutlined />
            </div>

            {/* Markers */}
            {markers.map((marker, index) => (
              <div
                key={marker.id}
                style={{
                  position: 'absolute',
                  top: `${40 + (index * 60) % 200}px`,
                  left: `${50 + (index * 80) % 300}px`,
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
                onClick={() => onMarkerClick?.(marker)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'scale(1.2)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                <div
                  style={{
                    fontSize: 32,
                    filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.3))',
                  }}
                >
                  {getMarkerIcon(marker.type)}
                </div>
                <Tag
                  color={getMarkerColor(marker.type)}
                  style={{
                    position: 'absolute',
                    top: 35,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {marker.title}
                </Tag>
              </div>
            ))}

            {/* Route polyline visualization */}
            {route.length > 1 && (
              <svg
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  pointerEvents: 'none',
                }}
              >
                <polyline
                  fill="none"
                  stroke="#1890ff"
                  strokeWidth="3"
                  strokeDasharray="5,5"
                  points={route
                    .map((_, index) => `${100 + index * 50},${150 + Math.sin(index) * 50}`)
                    .join(' ')}
                />
              </svg>
            )}

            {/* Map controls */}
            {showControls && (
              <div
                style={{
                  position: 'absolute',
                  top: 10,
                  right: 10,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <Button
                  size="small"
                  icon={<span>+</span>}
                  onClick={handleZoomIn}
                  title="放大"
                />
                <Button
                  size="small"
                  icon={<span>-</span>}
                  onClick={handleZoomOut}
                  title="縮小"
                />
                <Button
                  size="small"
                  icon={<AimOutlined />}
                  onClick={handleCenterMap}
                  title="置中"
                />
              </div>
            )}

            {/* Map info */}
            <div
              style={{
                position: 'absolute',
                bottom: 10,
                left: 10,
                background: 'rgba(255, 255, 255, 0.9)',
                padding: '4px 8px',
                borderRadius: 4,
                fontSize: 12,
              }}
            >
              <Space size="small">
                <span>縮放等級: {currentZoom}</span>
                <span>|</span>
                <span>中心: {center.lat.toFixed(4)}, {center.lng.toFixed(4)}</span>
              </Space>
            </div>

            {/* Placeholder message */}
            <div
              style={{
                position: 'absolute',
                bottom: 10,
                right: 10,
                background: 'rgba(255, 255, 255, 0.9)',
                padding: '8px 12px',
                borderRadius: 4,
                border: '1px solid #d9d9d9',
              }}
            >
              <Space>
                <EnvironmentOutlined />
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>
                  Google Maps 預覽模式
                </span>
              </Space>
            </div>
          </>
        )}
      </div>
    </Card>
  );
};

export default GoogleMapsPlaceholder;

// Export types for reuse
export type { MapMarker, GoogleMapsPlaceholderProps };