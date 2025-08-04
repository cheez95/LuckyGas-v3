import { useState, useEffect, useCallback } from 'react';
import { message } from 'antd';
import axios from 'axios';
import type { Route, RouteFilter } from '../../../types/maps.types';

interface UseRouteDataReturn {
  routes: Route[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useRouteData(
  date: Date,
  filter?: RouteFilter
): UseRouteDataReturn {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchRoutes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params: any = {
        date: date.toISOString().split('T')[0],
      };
      
      // Apply filters
      if (filter?.driverIds?.length) {
        params.driver_ids = filter.driverIds.join(',');
      }
      
      if (filter?.statuses?.length) {
        params.statuses = filter.statuses.join(',');
      }
      
      const response = await axios.get('/api/v1/routes', { params });
      
      // Transform API response to Route type
      const transformedRoutes: Route[] = response.data.map((apiRoute: any) => ({
        id: apiRoute.id,
        driverId: apiRoute.driver_id,
        driverName: apiRoute.driver_name,
        vehicleId: apiRoute.vehicle_id,
        date: new Date(apiRoute.route_date),
        status: apiRoute.status,
        stops: apiRoute.stops.map((stop: any) => ({
          id: stop.id,
          customerId: stop.customer_id,
          customerName: stop.customer_name,
          address: stop.address,
          position: {
            lat: stop.latitude,
            lng: stop.longitude,
          },
          sequence: stop.sequence,
          estimatedArrival: new Date(stop.estimated_arrival),
          actualArrival: stop.actual_arrival ? new Date(stop.actual_arrival) : undefined,
          estimatedDuration: stop.estimated_duration,
          status: stop.status,
          packages: stop.packages || [],
          notes: stop.notes,
          priority: stop.priority,
        })),
        polyline: apiRoute.polyline,
        totalDistance: apiRoute.total_distance_km,
        totalDuration: apiRoute.total_duration_minutes,
        startTime: new Date(apiRoute.start_time),
        endTime: apiRoute.end_time ? new Date(apiRoute.end_time) : undefined,
        optimizationMode: apiRoute.optimization_mode,
        color: apiRoute.color,
      }));
      
      setRoutes(transformedRoutes);
    } catch (err) {
      console.error('Failed to fetch routes:', err);
      setError('無法載入路線資料');
      message.error('載入路線失敗');
    } finally {
      setLoading(false);
    }
  }, [date, filter]);
  
  useEffect(() => {
    fetchRoutes();
  }, [fetchRoutes]);
  
  // Subscribe to WebSocket updates
  useEffect(() => {
    const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/ws/routes`);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'route-update') {
          setRoutes(prevRoutes => 
            prevRoutes.map(route => 
              route.id === data.routeId
                ? { ...route, ...data.updates }
                : route
            )
          );
        }
      } catch (err) {
        console.error('WebSocket message error:', err);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      ws.close();
    };
  }, []);
  
  return {
    routes,
    loading,
    error,
    refetch: fetchRoutes,
  };
}