import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { Card, Spin, Alert, message, Badge } from 'antd';
import { useGoogleMaps } from './GoogleMapsProvider';
import RouteLayer from './RouteLayer';
import DriverMarker from './DriverMarker';
import StopMarker from './StopMarker';
import RouteControl from './RouteControl';
import RouteInfoPanel from './RouteInfoPanel';
import DragDropHandler from './DragDropHandler';
import { useRouteData } from './hooks/useRouteData';
import { useDriverTracking } from './hooks/useDriverTracking';
import { useMapControls } from './hooks/useMapControls';
import { useViewportStops } from './hooks/useViewportMarkers';
import { useOptimizedWebSocket } from './hooks/useOptimizedWebSocket';
import { MarkerClusterer } from './utils/markerClusterer';
import { DEFAULT_MAP_CONFIG } from '../../services/maps/googleMapsConfig';
import { createRouteBounds } from '../../services/maps/routeHelpers';
import type { 
  Route, 
  Driver, 
  RouteStop, 
  MapCallbacks,
  RouteVisualizationOptions,
  RouteFilter,
  DragDropEvent,
  WebSocketMessage
} from '../../types/maps.types';
import './styles/RouteMap.module.css';

interface RouteMapProps {
  date?: Date;
  height?: string | number;
  showControls?: boolean;
  visualizationOptions?: Partial<RouteVisualizationOptions>;
  onRouteUpdate?: (routeId: string, updates: Partial<Route>) => void;
  onStopReorder?: (event: DragDropEvent) => void;
}

const defaultVisualizationOptions: RouteVisualizationOptions = {
  showStops: true,
  showDrivers: true,
  showLabels: true,
  showInfoWindows: true,
  clusterStops: true,
  animateDrivers: true,
  showTraffic: false,
};

const RouteMapOptimized: React.FC<RouteMapProps> = ({
  date = new Date(),
  height = '600px',
  showControls = true,
  visualizationOptions = {},
  onRouteUpdate,
  onStopReorder,
}) => {
  const { isLoaded, loadError, google } = useGoogleMaps();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const clustererRef = useRef<MarkerClusterer | null>(null);
  const stopMarkersRef = useRef<Map<string, google.maps.Marker>>(new Map());
  
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [selectedStop, setSelectedStop] = useState<RouteStop | null>(null);
  const [hoveredRoute, setHoveredRoute] = useState<Route | null>(null);
  const [filter, setFilter] = useState<RouteFilter>({});
  const [mapReady, setMapReady] = useState(false);
  
  const options = { ...defaultVisualizationOptions, ...visualizationOptions };
  
  // Custom hooks
  const { routes, loading: routesLoading, error: routesError, refetch } = useRouteData(date, filter);
  const { drivers, updateDriverLocation } = useDriverTracking(routes);
  const { fitBounds, panToLocation } = useMapControls(mapRef.current);
  
  // Viewport-based rendering for stops
  const { visibleStops, totalStops } = useViewportStops(routes, mapRef.current, {
    bufferRatio: 0.3,
    debounceMs: 150,
    maxMarkers: options.clusterStops ? 500 : 200,
  });
  
  // Optimized WebSocket connection
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'driver-location':
        updateDriverLocation(message.driverId, message.position);
        break;
      case 'route-update':
        // Handle route updates
        refetch();
        break;
      case 'stop-status':
        // Handle stop status updates
        refetch();
        break;
    }
  }, [updateDriverLocation, refetch]);
  
  const { isConnected } = useOptimizedWebSocket({
    url: `${import.meta.env.VITE_WS_URL}/ws/routes`,
    channels: ['routes', 'drivers'],
    onMessage: handleWebSocketMessage,
    batchMessages: true,
    batchInterval: 100,
  });
  
  // Initialize map
  useEffect(() => {
    if (!isLoaded || !mapContainerRef.current || mapRef.current) return;
    
    const map = new google.maps.Map(mapContainerRef.current, {
      ...DEFAULT_MAP_CONFIG.mapOptions,
      center: DEFAULT_MAP_CONFIG.defaultCenter,
      zoom: DEFAULT_MAP_CONFIG.defaultZoom,
    });
    
    mapRef.current = map;
    
    // Initialize marker clusterer
    if (options.clusterStops) {
      clustererRef.current = new MarkerClusterer(map, {
        gridSize: 60,
        maxZoom: 15,
        minimumClusterSize: 3,
      });
    }
    
    // Add traffic layer if enabled
    if (options.showTraffic) {
      const trafficLayer = new google.maps.TrafficLayer();
      trafficLayer.setMap(map);
    }
    
    // Add map click handler
    map.addListener('click', () => {
      setSelectedRoute(null);
      setSelectedStop(null);
    });
    
    setMapReady(true);
  }, [isLoaded, google, options.showTraffic, options.clusterStops]);
  
  // Fit bounds when routes change
  useEffect(() => {
    if (!mapRef.current || routes.length === 0) return;
    
    const allPoints = routes.flatMap(route => 
      route.stops.map(stop => stop.position)
    );
    
    const bounds = createRouteBounds(allPoints);
    if (bounds) {
      fitBounds(bounds);
    }
  }, [routes, fitBounds]);
  
  // Map callbacks
  const mapCallbacks: MapCallbacks = useMemo(() => ({
    onRouteClick: (route) => {
      setSelectedRoute(route);
      setSelectedStop(null);
    },
    onMarkerClick: (marker) => {
      const stop = visibleStops.find(s => s.id === marker.id);
      
      if (stop) {
        setSelectedStop(stop);
        const route = routes.find(r => r.id === stop.routeId);
        if (route) {
          setSelectedRoute(route);
        }
      }
    },
    onStopDragEnd: (event) => {
      if (onStopReorder) {
        onStopReorder(event);
      }
    },
    onRouteHover: (route) => {
      setHoveredRoute(route);
    },
  }), [visibleStops, routes, onStopReorder]);
  
  const handleFilterChange = (newFilter: RouteFilter) => {
    setFilter(newFilter);
  };
  
  const handleRouteOptimize = async () => {
    try {
      message.loading('正在優化路線...', 0);
      await refetch();
      message.destroy();
      message.success('路線優化完成');
    } catch (error) {
      message.destroy();
      message.error('路線優化失敗');
    }
  };
  
  const handleCenterOnDriver = (driverId: string) => {
    const driver = drivers.find(d => d.id === driverId);
    if (driver?.currentPosition) {
      panToLocation(driver.currentPosition);
    }
  };
  
  // Render stop markers (with clustering or viewport optimization)
  const renderStopMarkers = useCallback(() => {
    if (!mapRef.current || !mapReady) return null;
    
    // Clear existing markers
    stopMarkersRef.current.forEach(marker => marker.setMap(null));
    stopMarkersRef.current.clear();
    
    if (options.clusterStops && clustererRef.current) {
      // Use clustering
      const markerData = visibleStops.map(stop => ({
        id: stop.id,
        position: new google.maps.LatLng(stop.position.lat, stop.position.lng),
        stop,
        routeId: stop.routeId,
      }));
      
      clustererRef.current.clearMarkers();
      clustererRef.current.addMarkers(markerData);
      
      return null; // Clustering handles rendering
    }
    
    // Render individual markers (viewport-optimized)
    return visibleStops.map((stop) => {
      const route = routes.find(r => r.id === stop.routeId);
      if (!route) return null;
      
      return (
        <StopMarker
          key={stop.id}
          map={mapRef.current!}
          stop={stop}
          route={route}
          isSelected={selectedStop?.id === stop.id}
          showLabel={options.showLabels}
          showInfoWindow={options.showInfoWindows}
          draggable={selectedRoute?.id === route.id}
          onDragEnd={mapCallbacks.onStopDragEnd}
          onClick={() => mapCallbacks.onMarkerClick?.({
            id: stop.id,
            position: stop.position,
            type: stop.priority === 'urgent' ? 'priority' : 'customer',
            title: stop.customerName,
          })}
        />
      );
    });
  }, [visibleStops, routes, selectedStop, selectedRoute, options, mapCallbacks, mapReady]);
  
  if (loadError) {
    return (
      <Alert
        message="地圖載入失敗"
        description={loadError.message}
        type="error"
        showIcon
      />
    );
  }
  
  if (!isLoaded) {
    return (
      <Card style={{ height }}>
        <div className="map-loading">
          <Spin size="large" tip="載入地圖中..." />
        </div>
      </Card>
    );
  }
  
  return (
    <div className="route-map-container" style={{ height }}>
      {showControls && (
        <RouteControl
          routes={routes}
          filter={filter}
          onFilterChange={handleFilterChange}
          onOptimize={handleRouteOptimize}
          onCenterDriver={handleCenterOnDriver}
        />
      )}
      
      <div className="map-wrapper">
        <div ref={mapContainerRef} className="map-container" />
        
        {/* Performance indicator */}
        {options.clusterStops && totalStops > 50 && (
          <div className="performance-indicator">
            <Badge 
              count={`${totalStops} 個配送點`} 
              style={{ backgroundColor: '#52c41a' }} 
            />
          </div>
        )}
        
        {/* WebSocket status */}
        <div className="websocket-status">
          <Badge 
            status={isConnected ? 'success' : 'error'} 
            text={isConnected ? '即時更新中' : '離線'} 
          />
        </div>
        
        {mapRef.current && mapReady && (
          <>
            {/* Route polylines */}
            {routes.map((route) => (
              <RouteLayer
                key={route.id}
                map={mapRef.current!}
                route={route}
                isSelected={selectedRoute?.id === route.id}
                isHovered={hoveredRoute?.id === route.id}
                options={options}
                onClick={() => mapCallbacks.onRouteClick?.(route)}
                onHover={(hovered) => mapCallbacks.onRouteHover?.(hovered ? route : null)}
              />
            ))}
            
            {/* Driver markers */}
            {options.showDrivers && drivers.map((driver) => (
              <DriverMarker
                key={driver.id}
                map={mapRef.current!}
                driver={driver}
                route={routes.find(r => r.driverId === driver.id)}
                animate={options.animateDrivers}
                onClick={() => handleCenterOnDriver(driver.id)}
              />
            ))}
            
            {/* Stop markers */}
            {options.showStops && renderStopMarkers()}
            
            {/* Drag-drop handler */}
            {onStopReorder && (
              <DragDropHandler
                map={mapRef.current}
                routes={routes}
                onStopReorder={onStopReorder}
              />
            )}
          </>
        )}
        
        {selectedRoute && (
          <RouteInfoPanel
            route={selectedRoute}
            selectedStop={selectedStop}
            onClose={() => {
              setSelectedRoute(null);
              setSelectedStop(null);
            }}
            onStopClick={(stop) => setSelectedStop(stop)}
            onUpdate={onRouteUpdate}
          />
        )}
      </div>
      
      {routesError && (
        <Alert
          message="載入路線失敗"
          description={routesError}
          type="error"
          showIcon
          closable
          style={{ position: 'absolute', top: 16, right: 16, zIndex: 1000 }}
        />
      )}
    </div>
  );
};

export default RouteMapOptimized;