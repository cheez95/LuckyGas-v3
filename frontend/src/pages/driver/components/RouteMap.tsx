import React, { useEffect, useRef } from 'react';
import { Spin } from 'antd';
import { EnvironmentOutlined, CarOutlined } from '@ant-design/icons';

interface RouteMapProps {
  route: {
    deliveries: Array<{
      customer: {
        name: string;
        coordinates: {
          lat: number;
          lng: number;
        };
      };
      status: string;
    }>;
    optimizedPath: Array<{
      lat: number;
      lng: number;
    }>;
  };
  currentDeliveryIndex?: number;
}

declare global {
  interface Window {
    google: any;
    initMap: () => void;
  }
}

const RouteMap: React.FC<RouteMapProps> = ({ route, currentDeliveryIndex = 0 }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const routeLineRef = useRef<any>(null);

  useEffect(() => {
    // Load Google Maps script if not already loaded
    if (!window.google) {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${process.env.REACT_APP_GOOGLE_MAPS_API_KEY}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = initializeMap;
      document.head.appendChild(script);
    } else {
      initializeMap();
    }

    return () => {
      // Cleanup markers
      markersRef.current.forEach(marker => marker.setMap(null));
      markersRef.current = [];
      if (routeLineRef.current) {
        routeLineRef.current.setMap(null);
      }
    };
  }, []);

  const initializeMap = () => {
    if (!mapRef.current || !window.google) return;

    // Default center (Taiwan)
    const defaultCenter = { lat: 25.0330, lng: 121.5654 };
    
    // Initialize map
    const map = new window.google.maps.Map(mapRef.current, {
      zoom: 13,
      center: route.deliveries[0]?.customer.coordinates || defaultCenter,
      mapTypeControl: false,
      fullscreenControl: false,
      streetViewControl: false,
    });

    mapInstanceRef.current = map;

    // Add current location marker
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((position) => {
        const currentPos = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };

        const currentMarker = new window.google.maps.Marker({
          position: currentPos,
          map: map,
          icon: {
            path: window.google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: '#4285F4',
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
          },
          title: 'Current Location',
          'data-testid': 'current-location-marker',
        });

        markersRef.current.push(currentMarker);
      });
    }

    // Add delivery markers
    route.deliveries.forEach((delivery, index) => {
      const marker = new window.google.maps.Marker({
        position: delivery.customer.coordinates,
        map: map,
        label: {
          text: (index + 1).toString(),
          color: 'white',
          fontWeight: 'bold',
        },
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale: 20,
          fillColor: getMarkerColor(delivery.status, index === currentDeliveryIndex),
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
        title: delivery.customer.name,
        'data-testid': 'delivery-marker',
      });

      // Add info window
      const infoWindow = new window.google.maps.InfoWindow({
        content: `
          <div style="padding: 8px;">
            <h4 style="margin: 0 0 8px 0;">${delivery.customer.name}</h4>
            <p style="margin: 0; color: #666;">Stop ${index + 1}</p>
          </div>
        `,
      });

      marker.addListener('click', () => {
        infoWindow.open(map, marker);
      });

      markersRef.current.push(marker);
    });

    // Draw route polyline
    if (route.optimizedPath && route.optimizedPath.length > 0) {
      routeLineRef.current = new window.google.maps.Polyline({
        path: route.optimizedPath,
        geodesic: true,
        strokeColor: '#1890ff',
        strokeOpacity: 0.8,
        strokeWeight: 4,
        'data-testid': 'route-polyline',
      });
      routeLineRef.current.setMap(map);
    }

    // Fit bounds to show all markers
    const bounds = new window.google.maps.LatLngBounds();
    route.deliveries.forEach(delivery => {
      bounds.extend(delivery.customer.coordinates);
    });
    map.fitBounds(bounds);
  };

  const getMarkerColor = (status: string, isCurrent: boolean) => {
    if (isCurrent) return '#ff4d4f';
    switch (status) {
      case 'delivered':
        return '#52c41a';
      case 'failed':
        return '#ff4d4f';
      default:
        return '#1890ff';
    }
  };

  return (
    <div 
      ref={mapRef} 
      data-testid="route-map-container"
      style={{ width: '100%', height: '100%', minHeight: '400px' }}
    >
      {!window.google && (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100%' 
        }}>
          <Spin size="large" tip="Loading map..." />
        </div>
      )}
    </div>
  );
};

export default RouteMap;