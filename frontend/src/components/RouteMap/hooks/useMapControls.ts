import { useCallback, useRef } from 'react';
import { ANIMATION_DURATIONS } from '../../../services/maps/googleMapsConfig';
import type { MapPosition, MapBounds } from '../../../types/maps.types';

interface UseMapControlsReturn {
  panToLocation: (position: MapPosition, zoom?: number) => void;
  fitBounds: (bounds: MapBounds, padding?: number) => void;
  setZoom: (zoom: number) => void;
  getZoom: () => number | undefined;
  getBounds: () => MapBounds | undefined;
  addControl: (control: HTMLElement, position: google.maps.ControlPosition) => void;
  removeControl: (control: HTMLElement) => void;
}

export function useMapControls(map: google.maps.Map | null): UseMapControlsReturn {
  const animationRef = useRef<number | null>(null);
  
  const panToLocation = useCallback((position: MapPosition, zoom?: number) => {
    if (!map) return;
    
    // Cancel any ongoing animation
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    
    const targetLatLng = new google.maps.LatLng(position.lat, position.lng);
    
    // Smooth pan animation
    const startLatLng = map.getCenter();
    const startZoom = map.getZoom() || 12;
    const targetZoom = zoom || startZoom;
    
    const duration = ANIMATION_DURATIONS.panTo;
    const startTime = Date.now();
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Ease-in-out cubic
      const easeProgress = progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;
      
      if (startLatLng) {
        const currentLat = startLatLng.lat() + 
          (targetLatLng.lat() - startLatLng.lat()) * easeProgress;
        const currentLng = startLatLng.lng() + 
          (targetLatLng.lng() - startLatLng.lng()) * easeProgress;
        const currentZoom = startZoom + (targetZoom - startZoom) * easeProgress;
        
        map.setCenter({ lat: currentLat, lng: currentLng });
        map.setZoom(currentZoom);
      }
      
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };
    
    animate();
  }, [map]);
  
  const fitBounds = useCallback((bounds: MapBounds, padding: number = 50) => {
    if (!map) return;
    
    const googleBounds = new google.maps.LatLngBounds(
      { lat: bounds.south, lng: bounds.west },
      { lat: bounds.north, lng: bounds.east }
    );
    
    map.fitBounds(googleBounds, padding);
  }, [map]);
  
  const setZoom = useCallback((zoom: number) => {
    if (!map) return;
    map.setZoom(zoom);
  }, [map]);
  
  const getZoom = useCallback((): number | undefined => {
    if (!map) return undefined;
    return map.getZoom();
  }, [map]);
  
  const getBounds = useCallback((): MapBounds | undefined => {
    if (!map) return undefined;
    
    const bounds = map.getBounds();
    if (!bounds) return undefined;
    
    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    
    return {
      north: ne.lat(),
      south: sw.lat(),
      east: ne.lng(),
      west: sw.lng(),
    };
  }, [map]);
  
  const addControl = useCallback((
    control: HTMLElement, 
    position: google.maps.ControlPosition
  ) => {
    if (!map) return;
    map.controls[position].push(control);
  }, [map]);
  
  const removeControl = useCallback((control: HTMLElement) => {
    if (!map) return;
    
    // Search all control positions
    const positions = [
      google.maps.ControlPosition.TOP_LEFT,
      google.maps.ControlPosition.TOP_CENTER,
      google.maps.ControlPosition.TOP_RIGHT,
      google.maps.ControlPosition.LEFT_TOP,
      google.maps.ControlPosition.LEFT_CENTER,
      google.maps.ControlPosition.LEFT_BOTTOM,
      google.maps.ControlPosition.RIGHT_TOP,
      google.maps.ControlPosition.RIGHT_CENTER,
      google.maps.ControlPosition.RIGHT_BOTTOM,
      google.maps.ControlPosition.BOTTOM_LEFT,
      google.maps.ControlPosition.BOTTOM_CENTER,
      google.maps.ControlPosition.BOTTOM_RIGHT,
    ];
    
    positions.forEach(position => {
      const controls = map.controls[position];
      const index = controls.getArray().indexOf(control);
      if (index !== -1) {
        controls.removeAt(index);
      }
    });
  }, [map]);
  
  return {
    panToLocation,
    fitBounds,
    setZoom,
    getZoom,
    getBounds,
    addControl,
    removeControl,
  };
}