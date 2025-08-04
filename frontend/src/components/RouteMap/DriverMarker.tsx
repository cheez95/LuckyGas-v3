import React, { useEffect, useRef, useState } from 'react';
import { MARKER_CONFIGS, ANIMATION_DURATIONS } from '../../services/maps/googleMapsConfig';
import { animateMarkerAlongPath } from '../../services/maps/routeHelpers';
import type { Driver, Route } from '../../types/maps.types';

interface DriverMarkerProps {
  map: google.maps.Map;
  driver: Driver;
  route?: Route;
  animate?: boolean;
  onClick?: () => void;
}

const DriverMarker: React.FC<DriverMarkerProps> = ({
  map,
  driver,
  route,
  animate = true,
  onClick,
}) => {
  const markerRef = useRef<google.maps.Marker | null>(null);
  const infoWindowRef = useRef<google.maps.InfoWindow | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [currentPosition, setCurrentPosition] = useState(driver.currentPosition);
  
  // Create driver marker
  useEffect(() => {
    if (!driver.currentPosition) return;
    
    const marker = new google.maps.Marker({
      position: driver.currentPosition,
      map,
      title: driver.name,
      icon: createDriverIcon(driver),
      zIndex: 2000, // Drivers always on top
      optimized: false, // Needed for smooth animation
    });
    
    // Add click listener
    if (onClick) {
      marker.addListener('click', onClick);
    }
    
    // Create info window
    const infoWindow = new google.maps.InfoWindow({
      content: createDriverInfoContent(driver, route),
      maxWidth: 250,
    });
    
    // Show info on hover
    marker.addListener('mouseover', () => {
      infoWindow.open(map, marker);
    });
    
    marker.addListener('mouseout', () => {
      infoWindow.close();
    });
    
    markerRef.current = marker;
    infoWindowRef.current = infoWindow;
    
    return () => {
      if (markerRef.current) {
        google.maps.event.clearInstanceListeners(markerRef.current);
        markerRef.current.setMap(null);
        markerRef.current = null;
      }
      if (infoWindowRef.current) {
        infoWindowRef.current.close();
        infoWindowRef.current = null;
      }
    };
  }, [map, driver.id]);
  
  // Animate position changes
  useEffect(() => {
    if (!markerRef.current || !driver.currentPosition) return;
    
    if (animate && currentPosition && driver.currentPosition !== currentPosition) {
      animateMarkerMovement(
        markerRef.current,
        currentPosition,
        driver.currentPosition,
        ANIMATION_DURATIONS.markerMove
      );
    } else {
      markerRef.current.setPosition(driver.currentPosition);
    }
    
    setCurrentPosition(driver.currentPosition);
  }, [driver.currentPosition, animate]);
  
  // Update marker icon based on status
  useEffect(() => {
    if (!markerRef.current) return;
    
    markerRef.current.setIcon(createDriverIcon(driver));
    
    // Update info window content
    if (infoWindowRef.current) {
      infoWindowRef.current.setContent(createDriverInfoContent(driver, route));
    }
  }, [driver.status, driver.lastUpdate, route]);
  
  // Add direction indicator based on movement
  useEffect(() => {
    if (!markerRef.current || !route || route.status !== 'in-progress') return;
    
    // Find next stop
    const nextStop = route.stops.find(stop => stop.status === 'pending');
    if (!nextStop || !driver.currentPosition) return;
    
    // Calculate bearing to next stop
    const bearing = calculateBearing(driver.currentPosition, nextStop.position);
    
    // Update icon with rotation
    const icon = markerRef.current.getIcon() as google.maps.Symbol;
    if (icon && typeof icon === 'object') {
      icon.rotation = bearing;
      markerRef.current.setIcon(icon);
    }
  }, [driver.currentPosition, route]);
  
  return null;
};

function createDriverIcon(driver: Driver): google.maps.Symbol {
  const config = MARKER_CONFIGS.driver;
  const color = getDriverColor(driver.status);
  
  return {
    path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z',
    fillColor: color,
    fillOpacity: 0.9,
    strokeColor: '#fff',
    strokeWeight: 2,
    scale: 1.5,
    anchor: new google.maps.Point(12, 12),
  };
}

function getDriverColor(status: Driver['status']): string {
  const colors = {
    'offline': '#8c8c8c',
    'available': '#52c41a',
    'on-route': '#1890ff',
    'break': '#fadb14',
  };
  return colors[status] || '#8c8c8c';
}

function createDriverInfoContent(driver: Driver, route?: Route): string {
  const statusText = getDriverStatusText(driver.status);
  const statusClass = `driver-status-${driver.status}`;
  const lastUpdateText = driver.lastUpdate 
    ? `更新於 ${formatTimeDiff(driver.lastUpdate)}` 
    : '無位置更新';
    
  const routeInfo = route 
    ? `<div class="driver-route">路線: ${route.stops.length} 個配送點</div>` 
    : '';
    
  const nextStop = route?.stops.find(s => s.status === 'pending');
  const nextStopInfo = nextStop 
    ? `<div class="driver-next-stop">下一站: ${nextStop.customerName}</div>` 
    : '';
  
  return `
    <div class="driver-info-window">
      <div class="driver-header">
        <h4 class="driver-name">${driver.name}</h4>
        <span class="driver-status ${statusClass}">${statusText}</span>
      </div>
      <div class="driver-vehicle">車輛: ${driver.vehicleId}</div>
      ${routeInfo}
      ${nextStopInfo}
      <div class="driver-update">${lastUpdateText}</div>
      ${driver.phoneNumber ? `<a href="tel:${driver.phoneNumber}" class="driver-phone">📞 ${driver.phoneNumber}</a>` : ''}
    </div>
    <style>
      .driver-info-window {
        padding: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang TC', sans-serif;
      }
      .driver-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      .driver-name {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #262626;
      }
      .driver-status {
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 500;
      }
      .driver-status-offline {
        background: #f0f0f0;
        color: #8c8c8c;
      }
      .driver-status-available {
        background: #f6ffed;
        color: #52c41a;
      }
      .driver-status-on-route {
        background: #e6f7ff;
        color: #1890ff;
      }
      .driver-status-break {
        background: #fffbe6;
        color: #faad14;
      }
      .driver-vehicle,
      .driver-route,
      .driver-next-stop,
      .driver-update {
        font-size: 13px;
        color: #595959;
        margin: 4px 0;
      }
      .driver-phone {
        display: inline-block;
        margin-top: 8px;
        padding: 4px 12px;
        background: #1890ff;
        color: white;
        text-decoration: none;
        border-radius: 4px;
        font-size: 13px;
      }
      .driver-phone:hover {
        background: #40a9ff;
      }
    </style>
  `;
}

function getDriverStatusText(status: Driver['status']): string {
  const statusMap = {
    'offline': '離線',
    'available': '待命中',
    'on-route': '配送中',
    'break': '休息中',
  };
  return statusMap[status] || status;
}

function formatTimeDiff(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  
  if (diffMinutes < 1) return '剛剛';
  if (diffMinutes < 60) return `${diffMinutes} 分鐘前`;
  
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} 小時前`;
  
  return date.toLocaleString('zh-TW');
}

function animateMarkerMovement(
  marker: google.maps.Marker,
  from: { lat: number; lng: number },
  to: { lat: number; lng: number },
  duration: number
): void {
  const start = Date.now();
  
  const animate = () => {
    const elapsed = Date.now() - start;
    const progress = Math.min(elapsed / duration, 1);
    
    // Ease-in-out
    const easeProgress = progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;
    
    const lat = from.lat + (to.lat - from.lat) * easeProgress;
    const lng = from.lng + (to.lng - from.lng) * easeProgress;
    
    marker.setPosition({ lat, lng });
    
    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  };
  
  animate();
}

function calculateBearing(
  from: { lat: number; lng: number },
  to: { lat: number; lng: number }
): number {
  const dLng = (to.lng - from.lng) * Math.PI / 180;
  const fromLat = from.lat * Math.PI / 180;
  const toLat = to.lat * Math.PI / 180;
  
  const y = Math.sin(dLng) * Math.cos(toLat);
  const x = Math.cos(fromLat) * Math.sin(toLat) -
    Math.sin(fromLat) * Math.cos(toLat) * Math.cos(dLng);
  
  const bearing = Math.atan2(y, x) * 180 / Math.PI;
  return (bearing + 360) % 360;
}

export default DriverMarker;