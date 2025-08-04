import React, { useEffect, useRef, useState } from 'react';
import { MARKER_CONFIGS, getRouteColorByStatus } from '../../services/maps/googleMapsConfig';
import type { RouteStop, Route, DragDropEvent } from '../../types/maps.types';

interface StopMarkerProps {
  map: google.maps.Map;
  stop: RouteStop;
  route: Route;
  isSelected: boolean;
  showLabel: boolean;
  showInfoWindow: boolean;
  draggable?: boolean;
  onDragEnd?: (event: DragDropEvent) => void;
  onClick?: () => void;
}

const StopMarker: React.FC<StopMarkerProps> = ({
  map,
  stop,
  route,
  isSelected,
  showLabel,
  showInfoWindow,
  draggable = false,
  onDragEnd,
  onClick,
}) => {
  const markerRef = useRef<google.maps.Marker | null>(null);
  const infoWindowRef = useRef<google.maps.InfoWindow | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  // Create marker
  useEffect(() => {
    const markerConfig = stop.priority === 'urgent' 
      ? MARKER_CONFIGS.priority 
      : MARKER_CONFIGS.customer;
      
    const marker = new google.maps.Marker({
      position: stop.position,
      map,
      title: stop.customerName,
      draggable: draggable && stop.status !== 'completed',
      animation: stop.priority === 'urgent' 
        ? google.maps.Animation.BOUNCE 
        : undefined,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        fillColor: getStopColor(stop),
        fillOpacity: stop.status === 'completed' ? 0.5 : 0.8,
        strokeColor: '#fff',
        strokeWeight: markerConfig.strokeWeight,
        scale: markerConfig.scale,
      },
      label: showLabel ? {
        text: stop.sequence.toString(),
        color: '#fff',
        fontSize: '12px',
        fontWeight: '600',
      } : undefined,
      zIndex: isSelected ? 1000 : 100 + stop.sequence,
    });
    
    // Add click listener
    if (onClick) {
      marker.addListener('click', onClick);
    }
    
    // Add drag listeners
    if (draggable && onDragEnd) {
      marker.addListener('dragstart', () => {
        setIsDragging(true);
        if (infoWindowRef.current) {
          infoWindowRef.current.close();
        }
      });
      
      marker.addListener('dragend', () => {
        setIsDragging(false);
        const newPosition = marker.getPosition();
        if (newPosition) {
          // Find new route and index based on drop position
          // This is simplified - in real implementation, you'd check proximity to routes
          onDragEnd({
            stopId: stop.id,
            fromRouteId: route.id,
            toRouteId: route.id, // Same route for now
            fromIndex: stop.sequence - 1,
            toIndex: stop.sequence - 1, // Will be calculated based on drop position
          });
        }
      });
    }
    
    markerRef.current = marker;
    
    return () => {
      if (markerRef.current) {
        google.maps.event.clearInstanceListeners(markerRef.current);
        markerRef.current.setMap(null);
        markerRef.current = null;
      }
    };
  }, [map, stop.position, stop.sequence, draggable, onClick, onDragEnd]);
  
  // Create info window
  useEffect(() => {
    if (!markerRef.current || !showInfoWindow) return;
    
    const infoContent = createInfoWindowContent(stop, route);
    
    const infoWindow = new google.maps.InfoWindow({
      content: infoContent,
      maxWidth: 300,
    });
    
    infoWindowRef.current = infoWindow;
    
    // Show on hover
    markerRef.current.addListener('mouseover', () => {
      if (!isDragging) {
        infoWindow.open(map, markerRef.current!);
      }
    });
    
    markerRef.current.addListener('mouseout', () => {
      infoWindow.close();
    });
    
    // Keep open if selected
    if (isSelected) {
      infoWindow.open(map, markerRef.current);
    }
    
    return () => {
      if (infoWindowRef.current) {
        infoWindowRef.current.close();
        infoWindowRef.current = null;
      }
    };
  }, [map, stop, route, showInfoWindow, isSelected, isDragging]);
  
  // Update marker appearance
  useEffect(() => {
    if (!markerRef.current) return;
    
    const markerConfig = stop.priority === 'urgent' 
      ? MARKER_CONFIGS.priority 
      : MARKER_CONFIGS.customer;
      
    markerRef.current.setIcon({
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: getStopColor(stop),
      fillOpacity: stop.status === 'completed' ? 0.5 : 0.8,
      strokeColor: isSelected ? '#1890ff' : '#fff',
      strokeWeight: isSelected ? 3 : markerConfig.strokeWeight,
      scale: isSelected ? markerConfig.scale + 2 : markerConfig.scale,
    });
    
    // Update animation
    if (stop.priority === 'urgent' && stop.status !== 'completed') {
      markerRef.current.setAnimation(google.maps.Animation.BOUNCE);
    } else {
      markerRef.current.setAnimation(null);
    }
  }, [stop.status, stop.priority, isSelected]);
  
  return null;
};

function getStopColor(stop: RouteStop): string {
  if (stop.status === 'completed') {
    return '#52c41a'; // Green
  }
  
  if (stop.status === 'in-progress') {
    return '#1890ff'; // Blue
  }
  
  if (stop.priority === 'urgent') {
    return '#f5222d'; // Red
  }
  
  if (stop.priority === 'high') {
    return '#fa8c16'; // Orange
  }
  
  // Check if delayed
  const now = new Date();
  if (stop.estimatedArrival < now && stop.status === 'pending') {
    return '#f5222d'; // Red for delayed
  }
  
  return '#8c8c8c'; // Grey for pending
}

function createInfoWindowContent(stop: RouteStop, route: Route): string {
  const statusText = getStatusText(stop.status);
  const statusClass = `status-${stop.status}`;
  
  const packagesHtml = stop.packages
    .map(pkg => `<span class="package-tag">${pkg.quantity}x ${pkg.cylinderType}</span>`)
    .join(' ');
    
  const timeInfo = stop.actualArrival 
    ? `實際到達: ${formatTime(stop.actualArrival)}`
    : `預計到達: ${formatTime(stop.estimatedArrival)}`;
    
  return `
    <div class="stop-info-window">
      <div class="stop-info-header">
        <span class="stop-sequence">#${stop.sequence}</span>
        <span class="stop-status ${statusClass}">${statusText}</span>
      </div>
      <h4 class="stop-customer-name">${stop.customerName}</h4>
      <p class="stop-address">${stop.address}</p>
      <div class="stop-packages">${packagesHtml}</div>
      <div class="stop-time">${timeInfo}</div>
      ${stop.notes ? `<p class="stop-notes">${stop.notes}</p>` : ''}
      <div class="stop-driver">司機: ${route.driverName}</div>
    </div>
    <style>
      .stop-info-window {
        padding: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang TC', sans-serif;
      }
      .stop-info-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      .stop-sequence {
        background: #1890ff;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
      }
      .stop-status {
        font-size: 12px;
        font-weight: 500;
      }
      .status-completed { color: #52c41a; }
      .status-in-progress { color: #1890ff; }
      .status-pending { color: #8c8c8c; }
      .status-skipped { color: #f5222d; }
      .stop-customer-name {
        margin: 0 0 4px 0;
        font-size: 16px;
        font-weight: 600;
        color: #262626;
      }
      .stop-address {
        margin: 0 0 8px 0;
        font-size: 13px;
        color: #595959;
      }
      .stop-packages {
        margin-bottom: 8px;
      }
      .package-tag {
        display: inline-block;
        padding: 2px 8px;
        margin-right: 4px;
        background: #f0f0f0;
        border-radius: 4px;
        font-size: 12px;
      }
      .stop-time {
        font-size: 12px;
        color: #8c8c8c;
        margin-bottom: 4px;
      }
      .stop-notes {
        margin: 8px 0 4px 0;
        padding: 8px;
        background: #fafafa;
        border-radius: 4px;
        font-size: 12px;
        color: #595959;
      }
      .stop-driver {
        font-size: 12px;
        color: #1890ff;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #f0f0f0;
      }
    </style>
  `;
}

function getStatusText(status: RouteStop['status']): string {
  const statusMap = {
    'pending': '待配送',
    'in-progress': '配送中',
    'completed': '已完成',
    'skipped': '已跳過',
  };
  return statusMap[status] || status;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default StopMarker;