import React, { useEffect, useRef, useState } from 'react';
import { decodePolyline, createRoutePolylineOptions } from '../../services/maps/routeHelpers';
import { ROUTE_COLORS } from '../../services/maps/googleMapsConfig';
import type { Route, RouteVisualizationOptions } from '../../types/maps.types';

interface RouteLayerProps {
  map: google.maps.Map;
  route: Route;
  isSelected: boolean;
  isHovered: boolean;
  options: RouteVisualizationOptions;
  onClick?: () => void;
  onHover?: (hovered: boolean) => void;
}

const RouteLayer: React.FC<RouteLayerProps> = ({
  map,
  route,
  isSelected,
  isHovered,
  options,
  onClick,
  onHover,
}) => {
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  const [isVisible, setIsVisible] = useState(true);
  
  useEffect(() => {
    if (!route.polyline) return;
    
    // Decode polyline
    const path = decodePolyline(route.polyline);
    
    // Create polyline options
    const polylineOptions = createRoutePolylineOptions(
      route.status,
      isSelected || isHovered
    );
    
    // Create polyline
    const polyline = new google.maps.Polyline({
      ...polylineOptions,
      path,
      map,
    });
    
    // Add click listener
    if (onClick) {
      polyline.addListener('click', onClick);
    }
    
    // Add hover listeners
    if (onHover) {
      polyline.addListener('mouseover', () => onHover(true));
      polyline.addListener('mouseout', () => onHover(false));
    }
    
    polylineRef.current = polyline;
    
    return () => {
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
        google.maps.event.clearInstanceListeners(polylineRef.current);
        polylineRef.current = null;
      }
    };
  }, [map, route.polyline]);
  
  // Update polyline appearance when selection/hover changes
  useEffect(() => {
    if (!polylineRef.current) return;
    
    const options = createRoutePolylineOptions(
      route.status,
      isSelected || isHovered
    );
    
    polylineRef.current.setOptions(options);
  }, [route.status, isSelected, isHovered]);
  
  // Handle visibility
  useEffect(() => {
    if (!polylineRef.current) return;
    
    polylineRef.current.setVisible(isVisible);
  }, [isVisible]);
  
  // Add direction arrows
  useEffect(() => {
    if (!polylineRef.current || !options.showLabels) return;
    
    const path = polylineRef.current.getPath();
    const icons: google.maps.IconSequence[] = [{
      icon: {
        path: google.maps.SymbolPath.FORWARD_OPEN_ARROW,
        scale: 2,
        strokeColor: getArrowColor(route.status),
        strokeWeight: 2,
      },
      offset: '25%',
      repeat: '50%',
    }];
    
    polylineRef.current.setOptions({ icons });
  }, [route.status, options.showLabels]);
  
  return null;
};

function getArrowColor(status: string): string {
  const colorMap: { [key: string]: string } = {
    'completed': ROUTE_COLORS.onTime,
    'in-progress': '#fff',
    'delayed': ROUTE_COLORS.severeDelay,
    'not-started': ROUTE_COLORS.notStarted,
  };
  
  return colorMap[status] || '#666';
}

export default RouteLayer;