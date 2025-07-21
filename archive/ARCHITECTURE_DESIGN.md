# Lucky Gas v3 - Production Architecture Design

## Executive Summary

This document provides comprehensive technical designs for completing the Lucky Gas v3 system, addressing critical issues identified in the progress analysis and implementing remaining features for production readiness.

## 1. Google Cloud Integration Architecture

### 1.1 Overall Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Lucky Gas Application                      │
├───────────────────┬───────────────────┬─────────────────────────┤
│   Frontend (React)│  Backend (FastAPI)│   Mobile (React PWA)    │
└───────────────────┴────────┬──────────┴─────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │   Google Cloud   │
                    │  Service Layer   │
                    └────────┬────────┘
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────┴─────┐     ┌─────┴──────┐    ┌─────┴──────┐
    │Vertex AI │     │ Routes API  │    │Cloud Storage│
    │(Predict) │     │(Optimize)  │    │  (Media)   │
    └──────────┘     └────────────┘    └────────────┘
```

### 1.2 Service Integration Design

#### Vertex AI Integration
```python
# backend/app/services/google_cloud/vertex_ai_service.py
from google.cloud import aiplatform
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta

class VertexAIService:
    def __init__(self, project_id: str, location: str, model_id: str):
        aiplatform.init(project=project_id, location=location)
        self.model_id = model_id
        self.endpoint = None
        
    async def initialize_endpoint(self):
        """Initialize Vertex AI endpoint for predictions"""
        self.endpoint = aiplatform.Endpoint(self.model_id)
        
    async def predict_demand(
        self, 
        customer_data: Dict,
        historical_data: pd.DataFrame,
        weather_data: Optional[Dict] = None
    ) -> Dict:
        """Generate demand predictions for a customer"""
        # Feature engineering
        features = self._prepare_features(customer_data, historical_data, weather_data)
        
        # Make prediction
        prediction = self.endpoint.predict(instances=[features])
        
        # Process results
        return {
            "customer_id": customer_data["id"],
            "predictions": self._process_predictions(prediction),
            "confidence_score": prediction.predictions[0].get("confidence", 0.0),
            "model_version": self.endpoint.display_name
        }
    
    def _prepare_features(self, customer_data, historical_data, weather_data):
        """Prepare features for ML model"""
        features = {
            # Customer features
            "customer_type": customer_data.get("customer_type"),
            "location_lat": customer_data.get("latitude"),
            "location_lng": customer_data.get("longitude"),
            
            # Historical features
            "avg_order_frequency": self._calculate_order_frequency(historical_data),
            "avg_order_size": historical_data["quantity"].mean(),
            "days_since_last_order": self._days_since_last_order(historical_data),
            
            # Temporal features
            "day_of_week": datetime.now().weekday(),
            "month": datetime.now().month,
            "is_holiday": self._is_taiwan_holiday(),
            
            # Weather features (if available)
            "temperature": weather_data.get("temperature") if weather_data else None,
            "humidity": weather_data.get("humidity") if weather_data else None
        }
        return features
```

#### Google Routes API Integration
```python
# backend/app/services/google_cloud/routes_service.py
from google.maps import routing_v2
from typing import List, Dict, Tuple
import asyncio

class GoogleRoutesService:
    def __init__(self, api_key: str):
        self.client = routing_v2.RoutesClient(
            credentials={"api_key": api_key}
        )
        
    async def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int,
        time_windows: Dict
    ) -> Dict:
        """Optimize delivery route using Google Routes API"""
        
        # Build optimization request
        request = routing_v2.ComputeRoutesRequest(
            origin=self._create_waypoint(depot),
            destination=self._create_waypoint(depot),  # Return to depot
            intermediates=[self._create_waypoint((s["lat"], s["lng"])) for s in stops],
            travel_mode=routing_v2.RouteTravelMode.DRIVE,
            routing_preference=routing_v2.RoutingPreference.TRAFFIC_AWARE,
            compute_alternative_routes=False,
            route_modifiers=routing_v2.RouteModifiers(
                avoid_tolls=True,
                avoid_highways=False
            ),
            optimize_waypoint_order=True,
            language_code="zh-TW",
            region_code="TW"
        )
        
        # Get optimized route
        response = await self.client.compute_routes(request)
        
        # Process response
        return self._process_route_response(response, stops)
    
    def _create_waypoint(self, location: Tuple[float, float]):
        """Create waypoint from coordinates"""
        return routing_v2.Waypoint(
            location=routing_v2.Location(
                lat_lng=routing_v2.LatLng(
                    latitude=location[0],
                    longitude=location[1]
                )
            )
        )
```

### 1.3 Configuration Management

```python
# backend/app/core/google_cloud_config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class GoogleCloudSettings(BaseSettings):
    # Project settings
    GCP_PROJECT_ID: str
    GCP_LOCATION: str = "asia-east1"
    
    # Service-specific settings
    VERTEX_MODEL_ID: str
    VERTEX_ENDPOINT_ID: Optional[str] = None
    
    # APIs
    GOOGLE_MAPS_API_KEY: str
    
    # Storage
    GCS_BUCKET_NAME: str = "lucky-gas-storage"
    GCS_MEDIA_PREFIX: str = "delivery-photos"
    
    # Service accounts (optional, for production)
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_gcp_settings():
    return GoogleCloudSettings()
```

## 2. Predictions API CORS Fix

### 2.1 Backend CORS Configuration

```python
# backend/app/core/config.py - Updated CORS settings
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Updated CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Default CORS origins for development
    DEFAULT_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:5174",  # Vite alternative port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    
    def get_all_cors_origins(self) -> List[str]:
        """Get all CORS origins including defaults"""
        all_origins = self.DEFAULT_CORS_ORIGINS.copy()
        if self.BACKEND_CORS_ORIGINS:
            all_origins.extend(self.BACKEND_CORS_ORIGINS)
        return list(set(all_origins))  # Remove duplicates
```

```python
# backend/app/main.py - Updated CORS middleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Configure CORS with all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_all_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
```

### 2.2 Frontend API Error Handling

```typescript
// frontend/src/services/prediction.service.ts
import { api } from './api';
import { message } from 'antd';

class PredictionService {
  private handleApiError(error: any, context: string) {
    console.error(`Prediction API Error (${context}):`, error);
    
    if (error.response?.status === 403) {
      message.error('CORS錯誤：請檢查後端配置');
    } else if (error.response?.status === 401) {
      message.error('認證失敗：請重新登入');
    } else if (error.response?.status === 500) {
      message.error('伺服器錯誤：請稍後再試');
    } else if (error.code === 'ERR_NETWORK') {
      message.error('網路錯誤：無法連接到伺服器');
    } else {
      message.error(`預測服務錯誤：${error.message}`);
    }
    
    throw error;
  }
  
  async generateBatchPredictions() {
    try {
      const response = await api.post('/predictions/batch');
      return response.data;
    } catch (error) {
      this.handleApiError(error, 'generateBatchPredictions');
    }
  }
  
  async getCustomerPrediction(customerId: number) {
    try {
      const response = await api.get(`/predictions/customers/${customerId}`);
      return response.data;
    } catch (error) {
      this.handleApiError(error, 'getCustomerPrediction');
    }
  }
}

export const predictionService = new PredictionService();
```

## 3. Driver Mobile Interface Architecture

### 3.1 Progressive Web App (PWA) Design

```typescript
// frontend/src/components/driver/mobile/MobileDriverInterface.tsx
import React, { useState, useEffect } from 'react';
import { 
  Layout, Card, Button, List, Space, Tag, Progress,
  Modal, message, Drawer, Badge
} from 'antd';
import {
  CheckCircleOutlined, NavigationOutlined,
  CameraOutlined, EditOutlined, PhoneOutlined
} from '@ant-design/icons';
import SignatureCapture from './SignatureCapture';
import PhotoCapture from './PhotoCapture';
import OfflineIndicator from './OfflineIndicator';
import { useOfflineSync } from '../../../hooks/useOfflineSync';

const { Header, Content } = Layout;

interface MobileDriverInterfaceProps {
  route: RouteWithDetails;
  onDeliveryComplete: (stopId: number, data: DeliveryCompletionData) => Promise<void>;
}

const MobileDriverInterface: React.FC<MobileDriverInterfaceProps> = ({
  route,
  onDeliveryComplete
}) => {
  const { isOnline, syncPending, syncData } = useOfflineSync();
  const [activeStop, setActiveStop] = useState<RouteStop | null>(null);
  const [completionDrawerVisible, setCompletionDrawerVisible] = useState(false);
  
  // Touch-optimized UI with larger tap targets
  return (
    <Layout className="mobile-driver-interface">
      <Header className="mobile-header">
        <div className="header-content">
          <h2>路線 #{route.route_number}</h2>
          <Space>
            <OfflineIndicator isOnline={isOnline} pendingSync={syncPending} />
            <Badge count={route.total_stops - route.completed_stops}>
              <Progress
                type="circle"
                percent={Math.round((route.completed_stops / route.total_stops) * 100)}
                width={40}
              />
            </Badge>
          </Space>
        </div>
      </Header>
      
      <Content className="mobile-content">
        <List
          dataSource={route.stops}
          renderItem={(stop) => (
            <Card
              className={`stop-card ${stop.is_completed ? 'completed' : ''}`}
              onClick={() => !stop.is_completed && setActiveStop(stop)}
            >
              <div className="stop-header">
                <Tag color={stop.is_completed ? 'success' : 'processing'}>
                  #{stop.stop_sequence}
                </Tag>
                <h3>{stop.customer_name}</h3>
                {stop.is_completed && <CheckCircleOutlined />}
              </div>
              
              <p className="stop-address">{stop.address}</p>
              
              <div className="stop-actions">
                <Button
                  type="link"
                  icon={<PhoneOutlined />}
                  href={`tel:${stop.customer_phone}`}
                  onClick={(e) => e.stopPropagation()}
                >
                  撥打
                </Button>
                <Button
                  type="link"
                  icon={<NavigationOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    openNavigation(stop);
                  }}
                >
                  導航
                </Button>
                {!stop.is_completed && (
                  <Button
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeliveryStart(stop);
                    }}
                  >
                    開始配送
                  </Button>
                )}
              </div>
            </Card>
          )}
        />
      </Content>
      
      {/* Delivery Completion Drawer */}
      <DeliveryCompletionDrawer
        visible={completionDrawerVisible}
        stop={activeStop}
        onComplete={handleDeliveryComplete}
        onClose={() => {
          setCompletionDrawerVisible(false);
          setActiveStop(null);
        }}
      />
    </Layout>
  );
};
```

### 3.2 Signature Capture Component

```typescript
// frontend/src/components/driver/mobile/SignatureCapture.tsx
import React, { useRef, useState } from 'react';
import SignatureCanvas from 'react-signature-canvas';
import { Button, Space } from 'antd';
import { ClearOutlined, CheckOutlined } from '@ant-design/icons';

interface SignatureCaptureProps {
  onCapture: (signatureData: string) => void;
  onCancel: () => void;
}

const SignatureCapture: React.FC<SignatureCaptureProps> = ({
  onCapture,
  onCancel
}) => {
  const sigCanvas = useRef<SignatureCanvas>(null);
  const [isEmpty, setIsEmpty] = useState(true);
  
  const handleClear = () => {
    sigCanvas.current?.clear();
    setIsEmpty(true);
  };
  
  const handleSave = () => {
    if (sigCanvas.current && !isEmpty) {
      const dataURL = sigCanvas.current.toDataURL('image/png');
      onCapture(dataURL);
    }
  };
  
  return (
    <div className="signature-capture">
      <div className="signature-header">
        <h3>客戶簽名</h3>
        <p>請在下方區域簽名</p>
      </div>
      
      <div className="signature-pad-container">
        <SignatureCanvas
          ref={sigCanvas}
          penColor="black"
          canvasProps={{
            className: 'signature-pad',
            width: window.innerWidth - 40,
            height: 200
          }}
          onBegin={() => setIsEmpty(false)}
        />
      </div>
      
      <Space className="signature-actions" size="large">
        <Button
          size="large"
          icon={<ClearOutlined />}
          onClick={handleClear}
          disabled={isEmpty}
        >
          清除
        </Button>
        <Button
          type="default"
          size="large"
          onClick={onCancel}
        >
          取消
        </Button>
        <Button
          type="primary"
          size="large"
          icon={<CheckOutlined />}
          onClick={handleSave}
          disabled={isEmpty}
        >
          確認
        </Button>
      </Space>
    </div>
  );
};

export default SignatureCapture;
```

### 3.3 Photo Capture with Compression

```typescript
// frontend/src/components/driver/mobile/PhotoCapture.tsx
import React, { useRef, useState } from 'react';
import { Upload, Button, Image, message } from 'antd';
import { CameraOutlined, DeleteOutlined } from '@ant-design/icons';
import imageCompression from 'browser-image-compression';

interface PhotoCaptureProps {
  onCapture: (photos: string[]) => void;
  maxPhotos?: number;
}

const PhotoCapture: React.FC<PhotoCaptureProps> = ({
  onCapture,
  maxPhotos = 3
}) => {
  const [photos, setPhotos] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const compressImage = async (file: File): Promise<string> => {
    const options = {
      maxSizeMB: 1,
      maxWidthOrHeight: 1920,
      useWebWorker: true
    };
    
    try {
      const compressedFile = await imageCompression(file, options);
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(compressedFile);
      });
    } catch (error) {
      message.error('圖片壓縮失敗');
      throw error;
    }
  };
  
  const handleCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    const newPhotos: string[] = [];
    for (let i = 0; i < files.length && photos.length + i < maxPhotos; i++) {
      try {
        const compressed = await compressImage(files[i]);
        newPhotos.push(compressed);
      } catch (error) {
        console.error('Failed to process photo:', error);
      }
    }
    
    const updatedPhotos = [...photos, ...newPhotos];
    setPhotos(updatedPhotos);
    onCapture(updatedPhotos);
  };
  
  return (
    <div className="photo-capture">
      <div className="photo-grid">
        {photos.map((photo, index) => (
          <div key={index} className="photo-item">
            <Image src={photo} alt={`配送照片 ${index + 1}`} />
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                const updated = photos.filter((_, i) => i !== index);
                setPhotos(updated);
                onCapture(updated);
              }}
            />
          </div>
        ))}
        
        {photos.length < maxPhotos && (
          <div className="photo-add">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              multiple
              onChange={handleCapture}
              style={{ display: 'none' }}
            />
            <Button
              type="dashed"
              icon={<CameraOutlined />}
              onClick={() => fileInputRef.current?.click()}
              size="large"
              block
            >
              拍攝照片 ({photos.length}/{maxPhotos})
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PhotoCapture;
```

### 3.4 Offline Sync Hook

```typescript
// frontend/src/hooks/useOfflineSync.ts
import { useState, useEffect, useCallback } from 'react';
import { message } from 'antd';

interface SyncQueue {
  id: string;
  type: 'delivery_completion' | 'location_update';
  data: any;
  timestamp: number;
}

export const useOfflineSync = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncQueue, setSyncQueue] = useState<SyncQueue[]>([]);
  const [syncPending, setSyncPending] = useState(0);
  
  // Monitor online status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      message.success('已連接網路，開始同步資料');
      syncPendingData();
    };
    
    const handleOffline = () => {
      setIsOnline(false);
      message.warning('網路斷線，資料將在恢復連線後同步');
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  // Load queue from localStorage
  useEffect(() => {
    const savedQueue = localStorage.getItem('syncQueue');
    if (savedQueue) {
      const queue = JSON.parse(savedQueue);
      setSyncQueue(queue);
      setSyncPending(queue.length);
    }
  }, []);
  
  // Save queue to localStorage
  const saveQueue = useCallback((queue: SyncQueue[]) => {
    localStorage.setItem('syncQueue', JSON.stringify(queue));
    setSyncQueue(queue);
    setSyncPending(queue.length);
  }, []);
  
  // Add item to sync queue
  const addToQueue = useCallback((type: SyncQueue['type'], data: any) => {
    const item: SyncQueue = {
      id: `${Date.now()}-${Math.random()}`,
      type,
      data,
      timestamp: Date.now()
    };
    
    const newQueue = [...syncQueue, item];
    saveQueue(newQueue);
    
    if (isOnline) {
      syncPendingData();
    }
  }, [syncQueue, isOnline, saveQueue]);
  
  // Sync pending data
  const syncPendingData = useCallback(async () => {
    if (!isOnline || syncQueue.length === 0) return;
    
    const processed: string[] = [];
    
    for (const item of syncQueue) {
      try {
        switch (item.type) {
          case 'delivery_completion':
            await syncDeliveryCompletion(item.data);
            break;
          case 'location_update':
            await syncLocationUpdate(item.data);
            break;
        }
        processed.push(item.id);
      } catch (error) {
        console.error('Sync failed for item:', item, error);
      }
    }
    
    // Remove processed items
    const remainingQueue = syncQueue.filter(item => !processed.includes(item.id));
    saveQueue(remainingQueue);
    
    if (processed.length > 0) {
      message.success(`已同步 ${processed.length} 筆資料`);
    }
  }, [isOnline, syncQueue, saveQueue]);
  
  return {
    isOnline,
    syncPending,
    syncQueue,
    addToQueue,
    syncData: syncPendingData
  };
};
```

## 4. Route Optimization Integration

### 4.1 Route Optimization Service

```python
# backend/app/services/route_optimization.py
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import asyncio
from app.services.google_cloud.routes_service import GoogleRoutesService
from app.models.delivery import DeliveryRoute, RouteStop
from app.models.order import Order
from app.core.config import settings

class RouteOptimizationService:
    def __init__(self):
        self.routes_service = GoogleRoutesService(settings.GOOGLE_MAPS_API_KEY)
        self.depot = (settings.DEPOT_LAT, settings.DEPOT_LNG)
        
    async def optimize_routes(
        self,
        orders: List[Order],
        drivers: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """Optimize routes for multiple drivers"""
        
        # Group orders by area using k-means clustering
        clusters = self._cluster_orders_by_location(orders, len(drivers))
        
        # Optimize each cluster
        optimized_routes = []
        for i, (driver, cluster) in enumerate(zip(drivers, clusters)):
            route = await self._optimize_single_route(
                driver=driver,
                orders=cluster,
                route_number=f"R{date.strftime('%Y%m%d')}-{i+1:02d}"
            )
            optimized_routes.append(route)
            
        return optimized_routes
    
    async def _optimize_single_route(
        self,
        driver: Dict,
        orders: List[Order],
        route_number: str
    ) -> Dict:
        """Optimize a single driver's route"""
        
        # Prepare stops for optimization
        stops = [
            {
                "order_id": order.id,
                "lat": order.customer.latitude,
                "lng": order.customer.longitude,
                "priority": order.priority,
                "time_window": self._get_time_window(order),
                "service_time": self._estimate_service_time(order)
            }
            for order in orders
        ]
        
        # Call Google Routes API
        optimized = await self.routes_service.optimize_route(
            depot=self.depot,
            stops=stops,
            vehicle_capacity=driver.get("vehicle_capacity", 100),
            time_windows={
                "start": "08:00",
                "end": "18:00"
            }
        )
        
        # Build route response
        return {
            "route_number": route_number,
            "driver_id": driver["id"],
            "vehicle_id": driver.get("vehicle_id"),
            "stops": optimized["stops"],
            "total_distance_km": optimized["total_distance"] / 1000,
            "estimated_duration_minutes": optimized["total_duration"] / 60,
            "polyline": optimized["polyline"],
            "warnings": optimized.get("warnings", [])
        }
    
    def _cluster_orders_by_location(
        self,
        orders: List[Order],
        n_clusters: int
    ) -> List[List[Order]]:
        """Cluster orders by geographic location"""
        from sklearn.cluster import KMeans
        import numpy as np
        
        # Extract coordinates
        coords = np.array([
            [order.customer.latitude, order.customer.longitude]
            for order in orders
        ])
        
        # Perform k-means clustering
        kmeans = KMeans(n_clusters=min(n_clusters, len(orders)))
        labels = kmeans.fit_predict(coords)
        
        # Group orders by cluster
        clusters = [[] for _ in range(n_clusters)]
        for order, label in zip(orders, labels):
            clusters[label].append(order)
            
        # Balance clusters if needed
        return self._balance_clusters(clusters)
```

### 4.2 Real-time Route Tracking

```typescript
// frontend/src/components/office/RouteMonitor.tsx
import React, { useState, useEffect } from 'react';
import { GoogleMap, DirectionsRenderer, Marker, InfoWindow } from '@react-google-maps/api';
import { Card, List, Tag, Progress, Space, Avatar, Badge } from 'antd';
import { EnvironmentOutlined, UserOutlined, TruckOutlined } from '@ant-design/icons';
import { useWebSocket } from '../../hooks/useWebSocket';

interface RouteMonitorProps {
  routeId: number;
}

const RouteMonitor: React.FC<RouteMonitorProps> = ({ routeId }) => {
  const [route, setRoute] = useState<RouteWithDetails | null>(null);
  const [driverLocation, setDriverLocation] = useState<google.maps.LatLng | null>(null);
  const [directions, setDirections] = useState<google.maps.DirectionsResult | null>(null);
  const { on } = useWebSocket();
  
  // Real-time updates
  useEffect(() => {
    const unsubscribe = on('driver_location_update', (data) => {
      if (data.route_id === routeId) {
        setDriverLocation(new google.maps.LatLng(data.latitude, data.longitude));
      }
    });
    
    return unsubscribe;
  }, [routeId, on]);
  
  // Load and display route
  useEffect(() => {
    if (route?.polyline) {
      // Decode polyline and display on map
      const directionsService = new google.maps.DirectionsService();
      directionsService.route({
        origin: new google.maps.LatLng(settings.DEPOT_LAT, settings.DEPOT_LNG),
        destination: new google.maps.LatLng(settings.DEPOT_LAT, settings.DEPOT_LNG),
        waypoints: route.stops.map(stop => ({
          location: new google.maps.LatLng(stop.latitude, stop.longitude),
          stopover: true
        })),
        optimizeWaypoints: false,  // Already optimized by backend
        travelMode: google.maps.TravelMode.DRIVING
      }, (result, status) => {
        if (status === 'OK' && result) {
          setDirections(result);
        }
      });
    }
  }, [route]);
  
  return (
    <div className="route-monitor">
      <GoogleMap
        mapContainerStyle={{ width: '100%', height: '600px' }}
        center={driverLocation || { lat: settings.DEPOT_LAT, lng: settings.DEPOT_LNG }}
        zoom={13}
      >
        {/* Route polyline */}
        {directions && (
          <DirectionsRenderer
            directions={directions}
            options={{
              suppressMarkers: false,
              polylineOptions: {
                strokeColor: '#1890ff',
                strokeWeight: 4
              }
            }}
          />
        )}
        
        {/* Driver marker */}
        {driverLocation && (
          <Marker
            position={driverLocation}
            icon={{
              url: '/icons/delivery-truck.svg',
              scaledSize: new google.maps.Size(40, 40)
            }}
            title="司機位置"
          />
        )}
        
        {/* Stop markers */}
        {route?.stops.map((stop, index) => (
          <Marker
            key={stop.id}
            position={{ lat: stop.latitude, lng: stop.longitude }}
            label={{
              text: (index + 1).toString(),
              color: stop.is_completed ? 'white' : 'black',
              fontWeight: 'bold'
            }}
            icon={{
              url: stop.is_completed 
                ? '/icons/marker-complete.svg' 
                : '/icons/marker-pending.svg',
              scaledSize: new google.maps.Size(30, 40)
            }}
          />
        ))}
      </GoogleMap>
    </div>
  );
};
```

## 5. Performance Optimization Strategy

### 5.1 Database Optimization

```sql
-- backend/alembic/versions/performance_indexes.py
"""Add performance indexes

Revision ID: performance_001
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Customer search indexes
    op.create_index('idx_customers_short_name', 'customers', ['short_name'])
    op.create_index('idx_customers_phone', 'customers', ['phone'])
    op.create_index('idx_customers_area', 'customers', ['area'])
    op.create_index('idx_customers_active_area', 'customers', ['is_active', 'area'])
    
    # Order performance indexes
    op.create_index('idx_orders_customer_date', 'orders', ['customer_id', 'order_date'])
    op.create_index('idx_orders_status_date', 'orders', ['status', 'order_date'])
    op.create_index('idx_orders_delivery_date', 'orders', ['delivery_date', 'status'])
    
    # Route optimization indexes
    op.create_index('idx_routes_date_status', 'routes', ['date', 'status'])
    op.create_index('idx_routes_driver_date', 'routes', ['driver_id', 'date'])
    
    # Prediction indexes
    op.create_index('idx_predictions_customer_date', 'delivery_predictions', 
                   ['customer_id', 'predicted_date'])
    op.create_index('idx_predictions_confidence', 'delivery_predictions', 
                   ['confidence_score', 'is_converted_to_order'])
```

### 5.2 Redis Caching Layer

```python
# backend/app/core/cache.py
from typing import Optional, Any, Callable
import json
import asyncio
from datetime import timedelta
from redis import asyncio as aioredis
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis = None
        
    async def connect(self):
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None
            
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
        
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[timedelta] = None
    ):
        """Set value in cache"""
        if not self.redis:
            return
            
        serialized = json.dumps(value, default=str)
        if expire:
            await self.redis.setex(key, expire, serialized)
        else:
            await self.redis.set(key, serialized)
            
    async def invalidate(self, pattern: str):
        """Invalidate cache keys matching pattern"""
        if not self.redis:
            return
            
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
            
    async def cached(
        self,
        key: str,
        func: Callable,
        expire: Optional[timedelta] = None
    ):
        """Cache decorator for async functions"""
        # Try to get from cache
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
            
        # Execute function and cache result
        result = await func()
        await self.set(key, result, expire)
        return result

# Global cache instance
cache = CacheService()

# Usage example
async def get_customer_stats(customer_id: int):
    return await cache.cached(
        key=f"customer_stats:{customer_id}",
        func=lambda: calculate_customer_stats(customer_id),
        expire=timedelta(hours=1)
    )
```

### 5.3 Frontend Performance Optimization

```typescript
// frontend/src/utils/performance.ts
import { lazy, Suspense } from 'react';
import { Spin } from 'antd';

// Lazy load heavy components
export const lazyLoadComponent = (
  importFunc: () => Promise<any>,
  fallback = <Spin size="large" />
) => {
  const LazyComponent = lazy(importFunc);
  return (props: any) => (
    <Suspense fallback={fallback}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

// Image optimization hook
export const useImageOptimization = () => {
  const optimizeImage = (url: string, width: number) => {
    // Use image CDN if available
    if (process.env.REACT_APP_IMAGE_CDN) {
      return `${process.env.REACT_APP_IMAGE_CDN}/${url}?w=${width}&q=80`;
    }
    return url;
  };
  
  const lazyLoadImage = (src: string, placeholder: string) => {
    return {
      src: placeholder,
      'data-src': src,
      onLoad: (e: React.SyntheticEvent<HTMLImageElement>) => {
        const img = e.target as HTMLImageElement;
        img.src = img.dataset.src || src;
      }
    };
  };
  
  return { optimizeImage, lazyLoadImage };
};

// API request debouncing
export const useDebounce = <T extends (...args: any[]) => any>(
  func: T,
  delay: number = 300
) => {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

// Virtual scrolling for large lists
export { FixedSizeList as VirtualList } from 'react-window';
```

## 6. Deployment Architecture

### 6.1 Docker Configuration

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 6.2 Cloud Run Deployment

```yaml
# cloudbuild.yaml
steps:
  # Build backend image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/lucky-gas-backend:$COMMIT_SHA', './backend']
  
  # Build frontend image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/lucky-gas-frontend:$COMMIT_SHA', './frontend']
  
  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/lucky-gas-backend:$COMMIT_SHA']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/lucky-gas-frontend:$COMMIT_SHA']
  
  # Deploy backend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'lucky-gas-backend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/lucky-gas-backend:$COMMIT_SHA'
      - '--region'
      - 'asia-east1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'GCP_PROJECT_ID=$PROJECT_ID'
  
  # Deploy frontend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'lucky-gas-frontend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/lucky-gas-frontend:$COMMIT_SHA'
      - '--region'
      - 'asia-east1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/lucky-gas-backend:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/lucky-gas-frontend:$COMMIT_SHA'
```

### 6.3 Monitoring and Logging

```python
# backend/app/core/monitoring.py
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import logging
from pythonjsonlogger import jsonlogger

def setup_monitoring(app):
    """Setup Google Cloud monitoring and logging"""
    
    # Configure structured logging
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter()
    logHandler.setFormatter(formatter)
    logging.getLogger().addHandler(logHandler)
    logging.getLogger().setLevel(logging.INFO)
    
    # Setup tracing
    tracer_provider = TracerProvider()
    cloud_trace_exporter = CloudTraceSpanExporter()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(cloud_trace_exporter)
    )
    trace.set_tracer_provider(tracer_provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument(
        engine=app.state.db_engine,
        service="lucky-gas-backend"
    )
    
    # Add custom metrics
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        import time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request metrics
        logging.info("request_processed", extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "process_time": process_time,
            "client_host": request.client.host
        })
        
        return response
```

## Implementation Timeline

### Week 1: Critical Fixes and Integration
- **Day 1**: Fix CORS and setup Google Cloud project
- **Day 2**: Implement Vertex AI integration
- **Day 3-4**: Google Routes API integration
- **Day 5-7**: Mobile driver interface with signature/photo

### Week 2: Production Readiness
- **Day 8-9**: Performance optimization and caching
- **Day 10-11**: Docker setup and CI/CD pipeline
- **Day 12-13**: Testing and monitoring setup
- **Day 14**: Documentation and deployment

## Success Metrics

### Technical Metrics
- API response time < 200ms (p95)
- Page load time < 3s on 3G
- 100% test coverage for critical paths
- Zero critical security vulnerabilities

### Business Metrics
- 80%+ prediction accuracy
- 20% route time reduction
- Support 100+ concurrent users
- 99.9% uptime

## Risk Mitigation

1. **Google Cloud Costs**: Implement budget alerts and usage quotas
2. **Performance Issues**: Load test before production, implement caching
3. **Mobile Compatibility**: Test on actual devices, implement PWA
4. **Data Security**: Encrypt sensitive data, implement audit logs
5. **System Reliability**: Implement health checks, automatic failover

## Conclusion

This architecture design provides a comprehensive roadmap for completing the Lucky Gas v3 system. The design focuses on:

1. **Integration**: Seamless Google Cloud service integration
2. **Performance**: Optimized for Taiwan's network conditions
3. **Usability**: Mobile-first design for drivers
4. **Reliability**: Production-ready with monitoring and failover
5. **Scalability**: Cloud-native architecture for growth

Following this design will enable Lucky Gas to achieve its goal of a modern, efficient gas delivery management system that leverages AI for predictive ordering and optimized routing.