import api from './api';

export interface RouteStop {
  id: number;
  route_id: number;
  order_id: number;
  stop_sequence: number;
  latitude: number;
  longitude: number;
  address: string;
  estimated_arrival: string;
  actual_arrival?: string;
  estimated_duration_minutes: number;
  actual_duration_minutes?: number;
  is_completed: boolean;
  delivery_notes?: string;
}

export interface Route {
  id: number;
  route_number: string;
  route_date: string;
  driver_id?: number;
  driver_name?: string;
  vehicle_id?: number;
  vehicle_plate?: string;
  area?: string;
  status: 'planned' | 'optimized' | 'in_progress' | 'completed' | 'cancelled';
  total_stops: number;
  completed_stops: number;
  total_distance_km?: number;
  actual_distance_km?: number;
  estimated_duration_minutes?: number;
  actual_duration_minutes?: number;
  started_at?: string;
  completed_at?: string;
  is_optimized: boolean;
  optimization_score?: number;
  stops?: RouteStop[];
}

export interface RouteWithDetails extends Route {
  total_orders: number;
  completed_orders: number;
  total_cylinders: number;
}

export interface RouteOptimizationRequest {
  date: string;
  area?: string;
}

export interface RouteOptimizationResponse {
  optimization_id: string;
  routes_created: number;
  orders_assigned: number;
  unassigned_orders: any[];
  total_distance_km: number;
  optimization_score: number;
  cost_savings_percentage: number;
  created_routes: any[];
}

export interface RouteNavigation {
  route_id: number;
  navigation_steps: Array<{
    instruction: string;
    distance: string;
    duration: string;
  }>;
  polyline: string;
  bounds: {
    northeast: { lat: number; lng: number };
    southwest: { lat: number; lng: number };
  };
}

export interface LocationUpdate {
  latitude: number;
  longitude: number;
}

export interface ETAResponse {
  distance_km: number;
  duration_minutes: number;
  eta: string;
  traffic_condition: 'light' | 'moderate' | 'heavy';
}

class RouteService {
  // Get all routes with filters
  async getRoutes(params?: {
    skip?: number;
    limit?: number;
    date_from?: string;
    date_to?: string;
    driver_id?: number;
    area?: string;
    status?: string;
  }): Promise<RouteWithDetails[]> {
    const response = await api.get('/routes', { params });
    return response.data;
  }

  // Get specific route details
  async getRoute(routeId: number): Promise<RouteWithDetails> {
    const response = await api.get(`/routes/${routeId}`);
    return response.data;
  }

  // Get driver's current route
  async getDriverRoute(driverId: number, date?: string): Promise<RouteWithDetails | null> {
    const params = {
      driver_id: driverId,
      date_from: date || new Date().toISOString().split('T')[0],
      date_to: date || new Date().toISOString().split('T')[0],
      limit: 1,
    };
    const routes = await this.getRoutes(params);
    return routes.length > 0 ? routes[0] : null;
  }

  // Create new route
  async createRoute(route: {
    route_date: string;
    driver_id?: number;
    vehicle_id?: number;
    area?: string;
    stops?: Array<{
      order_id: number;
      stop_sequence: number;
      latitude?: number;
      longitude?: number;
      address?: string;
      estimated_arrival?: string;
      estimated_duration_minutes?: number;
    }>;
  }): Promise<Route> {
    const response = await api.post('/routes', route);
    return response.data;
  }

  // Update route
  async updateRoute(routeId: number, update: Partial<Route>): Promise<Route> {
    const response = await api.put(`/routes/${routeId}`, update);
    return response.data;
  }

  // Cancel route
  async cancelRoute(routeId: number): Promise<{ message: string }> {
    const response = await api.delete(`/routes/${routeId}`);
    return response.data;
  }

  // Add stop to route
  async addStop(routeId: number, stop: {
    order_id: number;
    stop_sequence: number;
    latitude?: number;
    longitude?: number;
    address?: string;
    estimated_arrival?: string;
    estimated_duration_minutes?: number;
  }): Promise<RouteStop> {
    const response = await api.post(`/routes/${routeId}/stops`, stop);
    return response.data;
  }

  // Update route stop
  async updateStop(stopId: number, update: {
    stop_sequence?: number;
    estimated_arrival?: string;
    actual_arrival?: string;
    estimated_duration_minutes?: number;
    actual_duration_minutes?: number;
    is_completed?: boolean;
    delivery_notes?: string;
  }): Promise<RouteStop> {
    const response = await api.put(`/routes/stops/${stopId}`, update);
    return response.data;
  }

  // Mark stop as completed
  async completeStop(stopId: number, notes?: string): Promise<RouteStop> {
    return this.updateStop(stopId, {
      is_completed: true,
      actual_arrival: new Date().toISOString(),
      delivery_notes: notes,
    });
  }

  // Remove stop from route
  async removeStop(stopId: number): Promise<{ message: string }> {
    const response = await api.delete(`/routes/stops/${stopId}`);
    return response.data;
  }

  // Optimize existing route
  async optimizeRoute(routeId: number): Promise<{
    route_id: number;
    original_distance_km: number;
    optimized_distance_km: number;
    distance_saved_km: number;
    distance_saved_percent: number;
    original_duration_minutes: number;
    optimized_duration_minutes: number;
    time_saved_minutes: number;
    optimization_score: number;
    optimized_stops: RouteStop[];
  }> {
    const response = await api.post(`/routes/${routeId}/optimize`, {});
    return response.data;
  }

  // Batch optimize routes
  async optimizeRoutesBatch(request: RouteOptimizationRequest): Promise<RouteOptimizationResponse> {
    const response = await api.post('/routes/optimize-batch', null, {
      params: {
        optimization_date: request.date,
        area: request.area,
      },
    });
    return response.data;
  }

  // Get route navigation
  async getRouteNavigation(routeId: number): Promise<RouteNavigation> {
    const response = await api.get(`/routes/${routeId}/navigation`);
    return response.data;
  }

  // Update driver location
  async updateDriverLocation(location: LocationUpdate): Promise<{
    driver_id: number;
    location: { lat: number; lng: number };
    timestamp: string;
    speed_kmh: number;
    heading: number;
    accuracy_meters: number;
  }> {
    const response = await api.post('/routes/driver-location', null, {
      params: {
        latitude: location.latitude,
        longitude: location.longitude,
      },
    });
    return response.data;
  }

  // Calculate ETA
  async calculateETA(
    from: { lat: number; lng: number },
    to: { lat: number; lng: number }
  ): Promise<ETAResponse> {
    const response = await api.get('/routes/calculate-eta', {
      params: {
        from_lat: from.lat,
        from_lng: from.lng,
        to_lat: to.lat,
        to_lng: to.lng,
      },
    });
    return response.data;
  }

  // Start route
  async startRoute(routeId: number): Promise<Route> {
    return this.updateRoute(routeId, { status: 'in_progress' });
  }

  // Complete route
  async completeRoute(routeId: number): Promise<Route> {
    return this.updateRoute(routeId, { status: 'completed' });
  }
}

export const routeService = new RouteService();