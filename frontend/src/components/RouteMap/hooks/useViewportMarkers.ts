import { useState, useEffect, useCallback, useRef } from 'react';
import type { MapBounds, RouteStop, Route } from '../../../types/maps.types';

interface UseViewportMarkersOptions {
  bufferRatio?: number; // How much to expand viewport for buffering
  debounceMs?: number; // Debounce time for viewport changes
  maxMarkers?: number; // Maximum markers to render
}

interface UseViewportMarkersReturn<T> {
  visibleItems: T[];
  totalItems: number;
  isFiltering: boolean;
}

export function useViewportMarkers<T extends { position: { lat: number; lng: number } }>(
  items: T[],
  map: google.maps.Map | null,
  options: UseViewportMarkersOptions = {}
): UseViewportMarkersReturn<T> {
  const {
    bufferRatio = 0.2, // 20% buffer around viewport
    debounceMs = 200,
    maxMarkers = 200,
  } = options;
  
  const [visibleItems, setVisibleItems] = useState<T[]>(items);
  const [isFiltering, setIsFiltering] = useState(false);
  const boundsRef = useRef<MapBounds | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  
  // Get expanded bounds with buffer
  const getExpandedBounds = useCallback((bounds: google.maps.LatLngBounds): MapBounds => {
    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    
    const latBuffer = (ne.lat() - sw.lat()) * bufferRatio;
    const lngBuffer = (ne.lng() - sw.lng()) * bufferRatio;
    
    return {
      north: ne.lat() + latBuffer,
      south: sw.lat() - latBuffer,
      east: ne.lng() + lngBuffer,
      west: sw.lng() - lngBuffer,
    };
  }, [bufferRatio]);
  
  // Check if position is within bounds
  const isInBounds = useCallback((position: { lat: number; lng: number }, bounds: MapBounds): boolean => {
    return position.lat >= bounds.south &&
           position.lat <= bounds.north &&
           position.lng >= bounds.west &&
           position.lng <= bounds.east;
  }, []);
  
  // Filter items by viewport
  const filterByViewport = useCallback(() => {
    if (!map) {
      setVisibleItems(items);
      return;
    }
    
    const mapBounds = map.getBounds();
    if (!mapBounds) {
      setVisibleItems(items);
      return;
    }
    
    setIsFiltering(true);
    
    const expandedBounds = getExpandedBounds(mapBounds);
    boundsRef.current = expandedBounds;
    
    // Filter items within viewport
    const filtered = items.filter(item => isInBounds(item.position, expandedBounds));
    
    // Apply max markers limit if needed
    const limited = filtered.length > maxMarkers 
      ? filtered.slice(0, maxMarkers)
      : filtered;
    
    setVisibleItems(limited);
    setIsFiltering(false);
  }, [items, map, getExpandedBounds, isInBounds, maxMarkers]);
  
  // Debounced viewport change handler
  const handleViewportChange = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    debounceTimerRef.current = window.setTimeout(() => {
      filterByViewport();
    }, debounceMs);
  }, [filterByViewport, debounceMs]);
  
  // Setup map listeners
  useEffect(() => {
    if (!map) return;
    
    // Initial filter
    filterByViewport();
    
    // Add listeners
    const listeners = [
      map.addListener('bounds_changed', handleViewportChange),
      map.addListener('zoom_changed', handleViewportChange),
    ];
    
    return () => {
      listeners.forEach(listener => google.maps.event.removeListener(listener));
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [map, handleViewportChange, filterByViewport]);
  
  // Re-filter when items change
  useEffect(() => {
    filterByViewport();
  }, [items, filterByViewport]);
  
  return {
    visibleItems,
    totalItems: items.length,
    isFiltering,
  };
}

// Specialized hook for route stops
export function useViewportStops(
  routes: Route[],
  map: google.maps.Map | null,
  options?: UseViewportMarkersOptions
): { visibleStops: Array<RouteStop & { routeId: string }>, totalStops: number, isFiltering: boolean } {
  // Flatten all stops with route reference
  const allStops = routes.flatMap(route => 
    route.stops.map(stop => ({ ...stop, routeId: route.id }))
  );
  
  const result = useViewportMarkers(allStops, map, options);
  
  return {
    visibleStops: result.visibleItems,
    totalStops: result.totalItems,
    isFiltering: result.isFiltering,
  };
}