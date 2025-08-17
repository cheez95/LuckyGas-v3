import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Spin, message, Button, Space } from 'antd';
import { AimOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { mapsLoader } from '../../../services/mapLoader.service';

interface Location {
  lat: number;
  lng: number;
  address?: string;
}

interface RouteStop {
  id: string;
  location: Location;
  orderNumber: string;
  customerName: string;
  products: string;
  isUrgent?: boolean;
  sequence?: number;
}

interface RoutePlanningMapProps {
  stops: RouteStop[];
  depotLocation?: Location;
  onStopsReordered?: (stops: RouteStop[]) => void;
  onMapClick?: (location: Location) => void;
  height?: string;
  showOptimizeButton?: boolean;
  isOptimizing?: boolean;
  onOptimizeRoute?: () => void;
}

// WeakMap to store component instances and their resources
const componentResources = new WeakMap<React.MutableRefObject<HTMLDivElement | null>, {
  map?: google.maps.Map;
  markers: google.maps.Marker[];
  infoWindows: google.maps.InfoWindow[];
  listeners: google.maps.MapsEventListener[];
  directionsRenderer?: google.maps.DirectionsRenderer;
  geocoderRequests: AbortController[];
}>();

const SafeRoutePlanningMap: React.FC<RoutePlanningMapProps> = ({
  stops,
  depotLocation = { lat: 25.0330, lng: 121.5654 }, // Default to Taipei
  onMapClick,
  height = '600px',
  showOptimizeButton = true,
  isOptimizing = false,
  onOptimizeRoute,
}) => {
  const { t } = useTranslation();
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [directionsService, setDirectionsService] = useState<google.maps.DirectionsService | null>(null);
  const [directionsRenderer, setDirectionsRenderer] = useState<google.maps.DirectionsRenderer | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isMountedRef = useRef(true);
  const activeRequestRef = useRef<AbortController | null>(null);
  const cleanupTimeoutRef = useRef<number | null>(null);

  // Initialize component resources in WeakMap
  const getResources = useCallback(() => {
    if (!mapRef.current) return null;
    
    if (!componentResources.has(mapRef)) {
      componentResources.set(mapRef, {
        markers: [],
        infoWindows: [],
        listeners: [],
        geocoderRequests: [],
      });
    }
    return componentResources.get(mapRef);
  }, []);

  // Enhanced cleanup with resource tracking
  const cleanupResources = useCallback(() => {
    console.log('[SafeRoutePlanningMap] Starting resource cleanup...');
    const resources = getResources();
    if (!resources) return;

    // Abort all pending geocoder requests
    resources.geocoderRequests.forEach(controller => {
      controller.abort();
    });
    resources.geocoderRequests = [];

    // Clear all markers with proper disposal
    resources.markers.forEach(marker => {
      try {
        google.maps.event.clearInstanceListeners(marker);
        marker.setMap(null);
        // Force garbage collection hint
        (marker as any).map = null;
        (marker as any).position = null;
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error clearing marker:', e);
      }
    });
    resources.markers = [];

    // Clear all info windows with proper disposal
    resources.infoWindows.forEach(infoWindow => {
      try {
        infoWindow.close();
        (infoWindow as any).content = null;
        (infoWindow as any).map = null;
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error clearing info window:', e);
      }
    });
    resources.infoWindows = [];

    // Remove all event listeners
    resources.listeners.forEach(listener => {
      try {
        google.maps.event.removeListener(listener);
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error removing listener:', e);
      }
    });
    resources.listeners = [];

    // Clear directions renderer
    if (resources.directionsRenderer) {
      try {
        resources.directionsRenderer.setMap(null);
        resources.directionsRenderer.setDirections({ routes: [] } as any);
        (resources.directionsRenderer as any).map = null;
        resources.directionsRenderer = undefined;
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error clearing directions renderer:', e);
      }
    }

    // Clear map instance
    if (resources.map) {
      try {
        google.maps.event.clearInstanceListeners(resources.map);
        // Clear overlays
        (resources.map as any).overlayMapTypes?.clear();
        // Null out references
        (resources.map as any).data = null;
        (resources.map as any).mapTypes = null;
        resources.map = undefined;
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error clearing map:', e);
      }
    }

    console.log('[SafeRoutePlanningMap] Resource cleanup completed');
  }, [getResources]);

  // Initialize Google Maps with resource tracking
  useEffect(() => {
    const initializeMap = async () => {
      try {
        await mapsLoader.load({
          libraries: ['places', 'drawing', 'geometry'],
          language: 'zh-TW',
          region: 'TW',
          version: 'weekly'
        });
        
        if (!mapRef.current || !isMountedRef.current) return;

        const resources = getResources();
        if (!resources) return;

        const mapInstance = await mapsLoader.createMap(mapRef.current, {
          center: depotLocation,
          zoom: 13,
          mapTypeControl: true,
          streetViewControl: false,
          fullscreenControl: true,
          zoomControl: true,
          styles: [
            {
              featureType: 'poi.business',
              elementType: 'labels',
              stylers: [{ visibility: 'on' }],
            },
          ],
        });

        resources.map = mapInstance;

        const service = await mapsLoader.getDirectionsService();
        const renderer = await mapsLoader.getDirectionsRenderer({
          map: mapInstance,
          suppressMarkers: false,
          polylineOptions: {
            strokeColor: '#1890ff',
            strokeWeight: 4,
            strokeOpacity: 0.8,
          },
        });

        resources.directionsRenderer = renderer;

        if (isMountedRef.current) {
          setMap(mapInstance);
          setDirectionsService(service);
          setDirectionsRenderer(renderer);
          setIsLoading(false);
        }

        // Add click listener with tracking
        if (onMapClick) {
          const clickListener = mapInstance.addListener('click', (event: google.maps.MapMouseEvent) => {
            if (event.latLng && isMountedRef.current) {
              onMapClick({
                lat: event.latLng.lat(),
                lng: event.latLng.lng(),
              });
            }
          });
          resources.listeners.push(clickListener);
        }
      } catch (error) {
        console.error('[SafeRoutePlanningMap] Error loading Google Maps:', error);
        if (isMountedRef.current) {
          message.error(t('dispatch.map.loadError'));
          setIsLoading(false);
        }
      }
    };

    initializeMap();
    
    // Cleanup function with timeout for safety
    return () => {
      console.log('[SafeRoutePlanningMap] Component unmounting...');
      isMountedRef.current = false;
      
      // Cancel any active requests
      if (activeRequestRef.current) {
        activeRequestRef.current.abort();
      }
      
      // Clear cleanup timeout if exists
      if (cleanupTimeoutRef.current) {
        clearTimeout(cleanupTimeoutRef.current);
      }
      
      // Immediate cleanup
      cleanupResources();
      
      // Delayed cleanup for safety
      cleanupTimeoutRef.current = window.setTimeout(() => {
        cleanupResources();
        // Clear the map div
        if (mapRef.current) {
          mapRef.current.innerHTML = '';
        }
        // Remove from WeakMap
        if (mapRef.current) {
          componentResources.delete(mapRef);
        }
      }, 100);
    };
  }, [depotLocation, onMapClick, t, getResources, cleanupResources]);

  // Clear markers with resource tracking
  const clearMarkers = useCallback(() => {
    const resources = getResources();
    if (!resources) return;

    console.log('[SafeRoutePlanningMap] Clearing markers and info windows');
    
    resources.markers.forEach(marker => {
      try {
        google.maps.event.clearInstanceListeners(marker);
        marker.setMap(null);
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error clearing marker:', e);
      }
    });
    resources.markers = [];
    
    resources.infoWindows.forEach(infoWindow => {
      try {
        infoWindow.close();
      } catch (e) {
        console.warn('[SafeRoutePlanningMap] Error clearing info window:', e);
      }
    });
    resources.infoWindows = [];
  }, [getResources]);

  // Create marker with resource tracking
  const createMarker = useCallback((
    position: google.maps.LatLngLiteral,
    label: string,
    title: string,
    isDepot: boolean = false,
    isUrgent: boolean = false
  ): google.maps.Marker | null => {
    if (!map || !isMountedRef.current) return null;
    
    const resources = getResources();
    if (!resources) return null;

    const marker = new google.maps.Marker({
      position,
      map,
      title,
      label: isDepot ? '倉' : label,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: isDepot ? 12 : 10,
        fillColor: isDepot ? '#ff4d4f' : (isUrgent ? '#faad14' : '#1890ff'),
        fillOpacity: 0.9,
        strokeColor: '#ffffff',
        strokeWeight: 2,
      },
      animation: isUrgent ? google.maps.Animation.BOUNCE : undefined,
      zIndex: isDepot ? 1000 : (isUrgent ? 900 : 100),
    });

    resources.markers.push(marker);

    // Add info window with resource tracking
    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 8px;">
          <h4 style="margin: 0 0 8px 0;">${title}</h4>
          ${!isDepot ? `<p style="margin: 0;">${position.lat.toFixed(6)}, ${position.lng.toFixed(6)}</p>` : ''}
        </div>
      `,
    });
    
    resources.infoWindows.push(infoWindow);

    const clickListener = marker.addListener('click', () => {
      if (isMountedRef.current) {
        infoWindow.open(map, marker);
      }
    });
    resources.listeners.push(clickListener);

    return marker;
  }, [map, getResources]);

  // Update route with abort controller
  const updateRoute = useCallback(async () => {
    if (!map || !directionsService || !directionsRenderer || stops.length === 0 || !isMountedRef.current) {
      return;
    }

    // Cancel previous request
    if (activeRequestRef.current) {
      activeRequestRef.current.abort();
    }
    
    activeRequestRef.current = new AbortController();

    clearMarkers();

    // Add depot marker
    const depotMarker = createMarker(
      depotLocation,
      '',
      t('dispatch.map.depot'),
      true
    );

    if (stops.length === 1) {
      // Single stop - just show markers
      const stop = stops[0];
      createMarker(
        {
          lat: stop.location.lat,
          lng: stop.location.lng,
        },
        '1',
        `${stop.customerName} - ${stop.products}`,
        false,
        stop.isUrgent
      );

      // Center map to show both depot and stop
      if (map && isMountedRef.current) {
        const bounds = new google.maps.LatLngBounds();
        bounds.extend(depotLocation);
        bounds.extend(stop.location);
        map.fitBounds(bounds);
      }
    } else {
      // Multiple stops - calculate route
      const waypoints = stops.slice(0, -1).map(stop => ({
        location: new google.maps.LatLng(stop.location.lat, stop.location.lng),
        stopover: true,
      }));

      const lastStop = stops[stops.length - 1];

      const request: google.maps.DirectionsRequest = {
        origin: depotLocation,
        destination: new google.maps.LatLng(lastStop.location.lat, lastStop.location.lng),
        waypoints,
        optimizeWaypoints: false,
        travelMode: google.maps.TravelMode.DRIVING,
        unitSystem: google.maps.UnitSystem.METRIC,
        avoidHighways: false,
        avoidTolls: true,
      };

      try {
        const result = await directionsService.route(request);
        if (isMountedRef.current && !activeRequestRef.current?.signal.aborted) {
          directionsRenderer.setDirections(result);

          // Add custom markers for each stop
          stops.forEach((stop, index) => {
            createMarker(
              {
                lat: stop.location.lat,
                lng: stop.location.lng,
              },
              `${index + 1}`,
              `${stop.customerName} - ${stop.products}`,
              false,
              stop.isUrgent
            );
          });
        }
      } catch (error: any) {
        if (error.name !== 'AbortError' && isMountedRef.current) {
          console.error('[SafeRoutePlanningMap] Error calculating route:', error);
          message.error(t('dispatch.map.routeError'));
        }
      }
    }
  }, [map, directionsService, directionsRenderer, stops, depotLocation, clearMarkers, createMarker, t]);

  // Update route when stops change
  useEffect(() => {
    if (isMountedRef.current) {
      updateRoute();
    }
    
    return () => {
      // Cancel any pending route calculations
      if (activeRequestRef.current) {
        activeRequestRef.current.abort();
      }
    };
  }, [stops, updateRoute]);

  // Center map on all stops
  const centerMap = useCallback(() => {
    if (!map || !isMountedRef.current || stops.length === 0) return;

    const bounds = new google.maps.LatLngBounds();
    bounds.extend(depotLocation);
    stops.forEach(stop => {
      bounds.extend({
        lat: stop.location.lat,
        lng: stop.location.lng,
      });
    });
    map.fitBounds(bounds);
  }, [map, stops, depotLocation]);

  return (
    <Card
      title={
        <Space>
          <span>{t('dispatch.map.title')}</span>
          {stops.length > 0 && (
            <span style={{ fontSize: '14px', fontWeight: 'normal', color: '#666' }}>
              ({stops.length} {t('dispatch.map.stops')})
            </span>
          )}
        </Space>
      }
      extra={
        <Space>
          <Button
            icon={<AimOutlined />}
            onClick={centerMap}
            disabled={!map || stops.length === 0}
          >
            {t('dispatch.map.center')}
          </Button>
          {showOptimizeButton && onOptimizeRoute && (
            <Button
              type="primary"
              icon={<ReloadOutlined spin={isOptimizing} />}
              onClick={onOptimizeRoute}
              loading={isOptimizing}
              disabled={!map || stops.length < 2}
            >
              {t('dispatch.map.optimize')}
            </Button>
          )}
        </Space>
      }
      style={{ height: '100%' }}
      bodyStyle={{ padding: 0, height: '100%' }}
    >
      <Spin spinning={isLoading} tip={t('dispatch.map.loading')}>
        <div ref={mapRef} style={{ width: '100%', height }} />
      </Spin>
    </Card>
  );
};

export default SafeRoutePlanningMap;