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

const RoutePlanningMap: React.FC<RoutePlanningMapProps> = ({
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
  const markersRef = useRef<google.maps.Marker[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const clickListenerRef = useRef<google.maps.MapsEventListener | null>(null);
  const infoWindowsRef = useRef<google.maps.InfoWindow[]>([]);
  const isMountedRef = useRef(true);

  // Initialize Google Maps
  useEffect(() => {
    const initializeMap = async () => {
      try {
        // Load Google Maps securely through our service
        await mapsLoader.load({
          libraries: ['places', 'drawing', 'geometry'],
          language: 'zh-TW',
          region: 'TW',
          version: 'weekly'
        });
        
        if (!mapRef.current) return;

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

        const service = await mapsLoader.getDirectionsService();
        const renderer = await mapsLoader.getDirectionsRenderer({
          map: mapInstance,
          suppressMarkers: false,
          polylineOptions: {
            strokeColor: '#1890ff',
            strokeWeight: 4,
            strokeOpacity: 0.8,
          },
          markerOptions: {
            zIndex: 100,
          },
        });

        setMap(mapInstance);
        setDirectionsService(service);
        setDirectionsRenderer(renderer);
        setIsLoading(false);

        // Add click listener
        if (onMapClick) {
          clickListenerRef.current = mapInstance.addListener('click', (event: google.maps.MapMouseEvent) => {
            if (event.latLng && isMountedRef.current) {
              onMapClick({
                lat: event.latLng.lat(),
                lng: event.latLng.lng(),
              });
            }
          });
        }
      } catch (error) {
        console.error('Error loading Google Maps:', error);
        message.error(t('dispatch.map.loadError'));
        setIsLoading(false);
      }
    };

    initializeMap();
    
    // Cleanup function
    return () => {
      // console.log('[RoutePlanningMap] Starting cleanup...');
      isMountedRef.current = false;
      
      // Clear all markers and info windows
      clearMarkers();
      
      // Remove click listener
      if (clickListenerRef.current) {
        google.maps.event.removeListener(clickListenerRef.current);
        clickListenerRef.current = null;
      }
      
      // Clear directions renderer
      if (directionsRenderer) {
        directionsRenderer.setMap(null);
        directionsRenderer.setDirections({ routes: [] } as any);
      }
      
      // Clear map instance
      if (map) {
        // Remove all listeners from map
        google.maps.event.clearInstanceListeners(map);
        // Clear the map div
        if (mapRef.current) {
          mapRef.current.innerHTML = '';
        }
      }
      
      // console.log('[RoutePlanningMap] Cleanup completed');
    };
  }, [depotLocation, onMapClick, t]);

  // Clear existing markers and info windows
  const clearMarkers = useCallback(() => {
    // console.log('[RoutePlanningMap] Clearing markers and info windows');
    // Clear all markers
    markersRef.current.forEach(marker => {
      // Remove all listeners from marker
      google.maps.event.clearInstanceListeners(marker);
      marker.setMap(null);
    });
    markersRef.current = [];
    
    // Clear all info windows
    infoWindowsRef.current.forEach(infoWindow => {
      infoWindow.close();
    });
    infoWindowsRef.current = [];
  }, []);

  // Create custom marker
  const createMarker = useCallback((
    position: google.maps.LatLngLiteral,
    label: string,
    title: string,
    isDepot: boolean = false,
    isUrgent: boolean = false
  ): google.maps.Marker => {
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

    // Add info window
    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 8px;">
          <h4 style="margin: 0 0 8px 0;">${title}</h4>
          ${!isDepot ? `<p style="margin: 0;">${position.lat.toFixed(6)}, ${position.lng.toFixed(6)}</p>` : ''}
        </div>
      `,
    });
    
    // Store info window reference for cleanup
    infoWindowsRef.current.push(infoWindow);

    marker.addListener('click', () => {
      if (isMountedRef.current) {
        infoWindow.open(map, marker);
      }
    });

    return marker;
  }, [map]);

  // Update route display
  const updateRoute = useCallback(async () => {
    if (!map || !directionsService || !directionsRenderer || stops.length === 0 || !isMountedRef.current) {
      return;
    }

    clearMarkers();

    // Add depot marker
    const depotMarker = createMarker(
      depotLocation,
      '',
      t('dispatch.map.depot'),
      true
    );
    markersRef.current.push(depotMarker);

    if (stops.length === 1) {
      // Single stop - just show markers
      const stop = stops[0];
      const marker = createMarker(
        {
          lat: stop.location.lat,
          lng: stop.location.lng,
        },
        '1',
        `${stop.customerName} - ${stop.products}`,
        false,
        stop.isUrgent
      );
      markersRef.current.push(marker);

      // Center map to show both depot and stop
      const bounds = new google.maps.LatLngBounds();
      bounds.extend(depotLocation);
      bounds.extend(stop.location);
      map.fitBounds(bounds);
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
        optimizeWaypoints: false, // We'll handle optimization separately
        travelMode: google.maps.TravelMode.DRIVING,
        unitSystem: google.maps.UnitSystem.METRIC,
        avoidHighways: false,
        avoidTolls: true,
      };

      try {
        const result = await directionsService.route(request);
        if (isMountedRef.current) {
          directionsRenderer.setDirections(result);
        }

        // Add custom markers for each stop
        stops.forEach((stop, index) => {
          const marker = createMarker(
            {
              lat: stop.location.lat,
              lng: stop.location.lng,
            },
            `${index + 1}`,
            `${stop.customerName} - ${stop.products}`,
            false,
            stop.isUrgent
          );
          markersRef.current.push(marker);
        });
      } catch (error) {
        console.error('Error calculating route:', error);
        message.error(t('dispatch.map.routeError'));
      }
    }
  }, [map, directionsService, directionsRenderer, stops, depotLocation, clearMarkers, createMarker, t]);

  // Update route when stops change
  useEffect(() => {
    if (isMountedRef.current) {
      updateRoute();
    }
  }, [stops, updateRoute]);

  // Center map on all stops
  const centerMap = useCallback(() => {
    if (!map || stops.length === 0) return;

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
              icon={<ReloadOutlined />}
              onClick={onOptimizeRoute}
              loading={isOptimizing}
              disabled={stops.length < 2}
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
        <div
          ref={mapRef}
          style={{
            width: '100%',
            height: height,
            minHeight: '400px',
          }}
        />
      </Spin>
    </Card>
  );
};

export default RoutePlanningMap;