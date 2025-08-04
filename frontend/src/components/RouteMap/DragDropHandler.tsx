import { useEffect, useRef, useState } from 'react';
import type { Route, RouteStop, DragDropEvent } from '../../types/maps.types';

interface DragDropHandlerProps {
  map: google.maps.Map;
  routes: Route[];
  onStopReorder: (event: DragDropEvent) => void;
}

interface DragState {
  isDragging: boolean;
  draggedStop?: RouteStop;
  draggedRoute?: Route;
  dropZones: google.maps.Polyline[];
  highlightedRoute?: Route;
}

export const DragDropHandler: React.FC<DragDropHandlerProps> = ({
  map,
  routes,
  onStopReorder,
}) => {
  const [dragState, setDragState] = useState<DragState>({
    isDragging: false,
    dropZones: [],
  });
  
  const dropZonesRef = useRef<google.maps.Polyline[]>([]);
  
  // Create drop zones for routes when dragging starts
  useEffect(() => {
    if (!dragState.isDragging) {
      // Clear drop zones
      dropZonesRef.current.forEach(zone => zone.setMap(null));
      dropZonesRef.current = [];
      return;
    }
    
    // Create thick invisible polylines as drop zones
    routes.forEach(route => {
      if (route.polyline) {
        const polyline = new google.maps.Polyline({
          path: decodePolyline(route.polyline),
          strokeColor: '#1890ff',
          strokeOpacity: 0,
          strokeWeight: 30, // Thick for easy dropping
          map,
          zIndex: 500,
        });
        
        // Add hover effects
        polyline.addListener('mouseover', () => {
          if (dragState.isDragging) {
            polyline.setOptions({
              strokeOpacity: 0.3,
              strokeColor: '#52c41a',
            });
            setDragState(prev => ({ ...prev, highlightedRoute: route }));
          }
        });
        
        polyline.addListener('mouseout', () => {
          polyline.setOptions({ strokeOpacity: 0 });
          setDragState(prev => ({ ...prev, highlightedRoute: undefined }));
        });
        
        dropZonesRef.current.push(polyline);
      }
    });
  }, [dragState.isDragging, routes, map]);
  
  // Handle global drag events
  useEffect(() => {
    const handleDragStart = (e: CustomEvent<{ stop: RouteStop; route: Route }>) => {
      setDragState({
        isDragging: true,
        draggedStop: e.detail.stop,
        draggedRoute: e.detail.route,
        dropZones: [],
      });
    };
    
    const handleDragEnd = (e: CustomEvent<{ position: google.maps.LatLng }>) => {
      if (!dragState.draggedStop || !dragState.draggedRoute) return;
      
      // Find closest route and position
      const dropTarget = findDropTarget(
        e.detail.position,
        routes,
        dragState.highlightedRoute
      );
      
      if (dropTarget) {
        onStopReorder({
          stopId: dragState.draggedStop.id,
          fromRouteId: dragState.draggedRoute.id,
          toRouteId: dropTarget.route.id,
          fromIndex: dragState.draggedStop.sequence - 1,
          toIndex: dropTarget.index,
        });
      }
      
      setDragState({
        isDragging: false,
        dropZones: [],
      });
    };
    
    window.addEventListener('stopDragStart', handleDragStart as EventListener);
    window.addEventListener('stopDragEnd', handleDragEnd as EventListener);
    
    return () => {
      window.removeEventListener('stopDragStart', handleDragStart as EventListener);
      window.removeEventListener('stopDragEnd', handleDragEnd as EventListener);
    };
  }, [dragState, routes, onStopReorder]);
  
  return null;
};

// Helper function to find the best drop position
function findDropTarget(
  position: google.maps.LatLng,
  routes: Route[],
  highlightedRoute?: Route
): { route: Route; index: number } | null {
  // If hovering over a route, use that
  if (highlightedRoute) {
    const index = findBestInsertionPoint(position, highlightedRoute);
    return { route: highlightedRoute, index };
  }
  
  // Otherwise find closest route
  let closestRoute: Route | null = null;
  let closestDistance = Infinity;
  
  routes.forEach(route => {
    route.stops.forEach(stop => {
      const stopLatLng = new google.maps.LatLng(stop.position.lat, stop.position.lng);
      const distance = google.maps.geometry.spherical.computeDistanceBetween(
        position,
        stopLatLng
      );
      
      if (distance < closestDistance) {
        closestDistance = distance;
        closestRoute = route;
      }
    });
  });
  
  if (closestRoute && closestDistance < 500) { // Within 500 meters
    const index = findBestInsertionPoint(position, closestRoute);
    return { route: closestRoute, index };
  }
  
  return null;
}

// Find the best position to insert a stop in a route
function findBestInsertionPoint(
  position: google.maps.LatLng,
  route: Route
): number {
  if (route.stops.length === 0) return 0;
  
  let bestIndex = 0;
  let minDetour = Infinity;
  
  // Check each possible insertion point
  for (let i = 0; i <= route.stops.length; i++) {
    const detour = calculateDetour(position, route.stops, i);
    if (detour < minDetour) {
      minDetour = detour;
      bestIndex = i;
    }
  }
  
  return bestIndex;
}

// Calculate the detour distance for inserting at a specific index
function calculateDetour(
  position: google.maps.LatLng,
  stops: RouteStop[],
  insertIndex: number
): number {
  if (stops.length === 0) return 0;
  
  const posBefore = insertIndex > 0 
    ? new google.maps.LatLng(stops[insertIndex - 1].position.lat, stops[insertIndex - 1].position.lng)
    : null;
    
  const posAfter = insertIndex < stops.length
    ? new google.maps.LatLng(stops[insertIndex].position.lat, stops[insertIndex].position.lng)
    : null;
    
  let detour = 0;
  
  if (posBefore && posAfter) {
    // Calculate original distance
    const originalDistance = google.maps.geometry.spherical.computeDistanceBetween(
      posBefore,
      posAfter
    );
    
    // Calculate new distance with insertion
    const newDistance = 
      google.maps.geometry.spherical.computeDistanceBetween(posBefore, position) +
      google.maps.geometry.spherical.computeDistanceBetween(position, posAfter);
      
    detour = newDistance - originalDistance;
  } else if (posBefore) {
    detour = google.maps.geometry.spherical.computeDistanceBetween(posBefore, position);
  } else if (posAfter) {
    detour = google.maps.geometry.spherical.computeDistanceBetween(position, posAfter);
  }
  
  return detour;
}

// Simple polyline decoder (duplicated from routeHelpers for now)
function decodePolyline(encoded: string): google.maps.LatLng[] {
  const points: google.maps.LatLng[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte: number;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlat = (result & 1) ? ~(result >> 1) : (result >> 1);
    lat += dlat;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlng = (result & 1) ? ~(result >> 1) : (result >> 1);
    lng += dlng;

    points.push(new google.maps.LatLng(lat / 1e5, lng / 1e5));
  }

  return points;
}

export default DragDropHandler;