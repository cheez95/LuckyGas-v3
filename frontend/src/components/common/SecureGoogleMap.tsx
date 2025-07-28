import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Spin, Alert, Button, Space, message } from 'antd';
import { 
  EnvironmentOutlined, 
  AimOutlined, 
  ReloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined 
} from '@ant-design/icons';
import { mapsService } from '../../services/maps.service';
import './SecureGoogleMap.css';

interface MapMarker {
  id: string;
  position: { lat: number; lng: number };
  title: string;
  type: 'depot' | 'customer' | 'driver' | 'destination';
  info?: string;
  color?: string;
  icon?: string;
}

interface SecureGoogleMapProps {
  center?: { lat: number; lng: number };
  zoom?: number;
  markers?: MapMarker[];
  route?: Array<{ lat: number; lng: number }>;
  height?: string | number;
  showControls?: boolean;
  showSearch?: boolean;
  onMarkerClick?: (marker: MapMarker) => void;
  onLocationSelect?: (location: { lat: number; lng: number; address?: string }) => void;
  className?: string;
}

const SecureGoogleMap: React.FC<SecureGoogleMapProps> = ({
  center = { lat: 25.0330, lng: 121.5654 }, // Default to Taipei
  zoom = 13,
  markers = [],
  route = [],
  height = 400,
  showControls = true,
  showSearch = false,
  onMarkerClick,
  onLocationSelect,
  className = '',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  // Initialize map
  const initializeMap = useCallback(async () => {
    if (!mapContainerRef.current || mapRef.current) return;

    try {
      setLoading(true);
      setError(null);

      // Check if Google Maps is already loaded
      if (!window.google || !window.google.maps) {
        // Load Google Maps script through backend proxy
        await loadGoogleMapsScript();
      }

      // Create map instance
      const mapOptions: google.maps.MapOptions = {
        center,
        zoom,
        mapTypeControl: showControls,
        streetViewControl: showControls,
        fullscreenControl: false, // We'll use our own fullscreen control
        zoomControl: showControls,
        styles: [
          {
            featureType: 'poi.business',
            elementType: 'labels',
            stylers: [{ visibility: 'off' }],
          },
        ],
      };

      mapRef.current = new google.maps.Map(mapContainerRef.current, mapOptions);
      
      // Add click listener for location selection
      if (onLocationSelect) {
        mapRef.current.addListener('click', async (event: google.maps.MapMouseEvent) => {
          if (event.latLng) {
            const lat = event.latLng.lat();
            const lng = event.latLng.lng();
            
            // Reverse geocode to get address
            const geocoder = new google.maps.Geocoder();
            geocoder.geocode({ location: { lat, lng } }, (results, status) => {
              if (status === 'OK' && results && results[0]) {
                onLocationSelect({
                  lat,
                  lng,
                  address: results[0].formatted_address,
                });
              } else {
                onLocationSelect({ lat, lng });
              }
            });
          }
        });
      }

      setMapReady(true);
      setLoading(false);
    } catch (err) {
      console.error('Map initialization error:', err);
      setError('無法載入地圖，請稍後再試');
      setLoading(false);
    }
  }, [center, zoom, showControls, onLocationSelect]);

  // Load Google Maps script
  const loadGoogleMapsScript = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      // Check if already loading
      if (window.googleMapsCallback) {
        window.googleMapsCallbacks.push(resolve);
        return;
      }

      // Setup callbacks
      window.googleMapsCallbacks = [resolve];
      window.googleMapsCallback = () => {
        window.googleMapsCallbacks.forEach(cb => cb());
        delete window.googleMapsCallback;
        delete window.googleMapsCallbacks;
      };

      // Create script element
      const script = document.createElement('script');
      script.src = `/api/v1/maps/script?libraries=places,geometry&callback=googleMapsCallback`;
      script.async = true;
      script.defer = true;
      script.onerror = () => {
        delete window.googleMapsCallback;
        delete window.googleMapsCallbacks;
        reject(new Error('Failed to load Google Maps'));
      };

      document.head.appendChild(script);
    });
  };

  // Update markers
  const updateMarkers = useCallback(() => {
    if (!mapRef.current || !mapReady) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.setMap(null));
    markersRef.current = [];

    // Add new markers
    markers.forEach(markerData => {
      const marker = new google.maps.Marker({
        position: markerData.position,
        map: mapRef.current!,
        title: markerData.title,
        icon: getMarkerIcon(markerData),
      });

      // Add click listener
      if (onMarkerClick) {
        marker.addListener('click', () => onMarkerClick(markerData));
      }

      // Add info window
      if (markerData.info) {
        const infoWindow = new google.maps.InfoWindow({
          content: `
            <div style="padding: 8px;">
              <h4 style="margin: 0 0 4px 0;">${markerData.title}</h4>
              <p style="margin: 0; color: #666;">${markerData.info}</p>
            </div>
          `,
        });

        marker.addListener('click', () => {
          infoWindow.open(mapRef.current!, marker);
        });
      }

      markersRef.current.push(marker);
    });

    // Fit bounds to show all markers
    if (markers.length > 0) {
      const bounds = new google.maps.LatLngBounds();
      markers.forEach(marker => bounds.extend(marker.position));
      mapRef.current.fitBounds(bounds);
    }
  }, [markers, mapReady, onMarkerClick]);

  // Get marker icon configuration
  const getMarkerIcon = (marker: MapMarker): google.maps.Icon | google.maps.Symbol => {
    const colors = {
      depot: '#1890ff',
      customer: '#52c41a',
      driver: '#fa8c16',
      destination: '#f5222d',
    };

    const color = marker.color || colors[marker.type] || '#666';

    if (marker.icon) {
      return {
        url: marker.icon,
        scaledSize: new google.maps.Size(32, 32),
      };
    }

    // Use default circle marker
    return {
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: color,
      fillOpacity: 0.8,
      strokeColor: '#fff',
      strokeWeight: 2,
      scale: 10,
    };
  };

  // Update route
  const updateRoute = useCallback(() => {
    if (!mapRef.current || !mapReady || route.length === 0) return;

    // Clear existing polyline
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
    }

    // Create new polyline
    polylineRef.current = new google.maps.Polyline({
      path: route,
      geodesic: true,
      strokeColor: '#1890ff',
      strokeOpacity: 0.8,
      strokeWeight: 4,
      map: mapRef.current,
    });

    // Fit bounds to show entire route
    const bounds = new google.maps.LatLngBounds();
    route.forEach(point => bounds.extend(point));
    mapRef.current.fitBounds(bounds);
  }, [route, mapReady]);

  // Handle fullscreen
  const toggleFullscreen = () => {
    if (!mapContainerRef.current) return;

    if (!isFullscreen) {
      if (mapContainerRef.current.requestFullscreen) {
        mapContainerRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  // Center map on current location
  const centerOnCurrentLocation = () => {
    if (!mapRef.current) return;

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const pos = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };
          mapRef.current!.setCenter(pos);
          mapRef.current!.setZoom(15);
          
          // Add current location marker
          new google.maps.Marker({
            position: pos,
            map: mapRef.current!,
            icon: {
              path: google.maps.SymbolPath.CIRCLE,
              fillColor: '#4285F4',
              fillOpacity: 0.8,
              strokeColor: '#fff',
              strokeWeight: 2,
              scale: 8,
            },
            title: '您的位置',
          });
          
          message.success('已定位到您的位置');
        },
        () => {
          message.error('無法取得您的位置');
        }
      );
    } else {
      message.error('您的瀏覽器不支援定位功能');
    }
  };

  // Refresh map
  const refreshMap = () => {
    if (mapRef.current) {
      google.maps.event.trigger(mapRef.current, 'resize');
      mapRef.current.setCenter(center);
      mapRef.current.setZoom(zoom);
    }
  };

  // Initialize map on mount
  useEffect(() => {
    initializeMap();

    return () => {
      // Cleanup
      markersRef.current.forEach(marker => marker.setMap(null));
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
      }
      mapRef.current = null;
    };
  }, [initializeMap]);

  // Update markers when they change
  useEffect(() => {
    updateMarkers();
  }, [updateMarkers]);

  // Update route when it changes
  useEffect(() => {
    updateRoute();
  }, [updateRoute]);

  // Update center and zoom
  useEffect(() => {
    if (mapRef.current && mapReady) {
      mapRef.current.setCenter(center);
      mapRef.current.setZoom(zoom);
    }
  }, [center, zoom, mapReady]);

  return (
    <Card
      className={`secure-google-map ${className}`}
      bodyStyle={{ padding: 0 }}
      style={{ height: typeof height === 'number' ? `${height}px` : height }}
    >
      {error && (
        <Alert
          message="地圖載入錯誤"
          description={error}
          type="error"
          showIcon
          closable
          style={{ margin: 16 }}
        />
      )}
      
      <div
        ref={mapContainerRef}
        className="map-container"
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
        }}
      >
        {loading && (
          <div className="map-loading">
            <Spin size="large" tip="載入地圖中..." />
          </div>
        )}
        
        {/* Custom controls */}
        {!loading && showControls && (
          <div className="map-controls">
            <Space direction="vertical">
              <Button
                icon={<AimOutlined />}
                onClick={centerOnCurrentLocation}
                title="定位到我的位置"
              />
              <Button
                icon={<ReloadOutlined />}
                onClick={refreshMap}
                title="重新整理地圖"
              />
              <Button
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={toggleFullscreen}
                title={isFullscreen ? '退出全螢幕' : '全螢幕'}
              />
            </Space>
          </div>
        )}
        
        {/* Map info */}
        {!loading && (
          <div className="map-info">
            <Space size="small">
              <EnvironmentOutlined />
              <span>安全地圖模式</span>
            </Space>
          </div>
        )}
      </div>
    </Card>
  );
};

export default SecureGoogleMap;

// Type declarations for window
declare global {
  interface Window {
    google: any;
    googleMapsCallback: (() => void) | undefined;
    googleMapsCallbacks: (() => void)[];
  }
}