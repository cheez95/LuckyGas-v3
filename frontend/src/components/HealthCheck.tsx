import { useEffect, useState } from 'react';
import axios from 'axios';

interface HealthStatus {
  frontend: {
    status: 'healthy' | 'unhealthy' | 'checking';
    version: string;
    buildTime?: string;
  };
  backend: {
    status: 'healthy' | 'unhealthy' | 'checking';
    version?: string;
    database?: boolean;
    redis?: boolean;
  };
  connectivity: {
    api: boolean;
    websocket: boolean;
  };
}

export const HealthCheck = () => {
  const [health, setHealth] = useState<HealthStatus>({
    frontend: { status: 'checking', version: '1.0.0' },
    backend: { status: 'checking' },
    connectivity: { api: false, websocket: false },
  });

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    // Check frontend
    setHealth(prev => ({
      ...prev,
      frontend: {
        status: 'healthy',
        version: import.meta.env.VITE_APP_VERSION || '1.0.0',
        buildTime: new Date().toISOString(),
      },
    }));

    // Check backend API
    try {
      const response = await axios.get('/api/v1/health', {
        timeout: 5000,
      });
      
      setHealth(prev => ({
        ...prev,
        backend: {
          status: 'healthy',
          version: response.data.version,
          database: response.data.database_status === 'healthy',
          redis: response.data.redis_status === 'healthy',
        },
        connectivity: {
          ...prev.connectivity,
          api: true,
        },
      }));
    } catch (error) {
      setHealth(prev => ({
        ...prev,
        backend: { status: 'unhealthy' },
        connectivity: {
          ...prev.connectivity,
          api: false,
        },
      }));
    }

    // Check WebSocket
    try {
      const ws = new WebSocket(
        `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws`
      );
      
      ws.onopen = () => {
        setHealth(prev => ({
          ...prev,
          connectivity: {
            ...prev.connectivity,
            websocket: true,
          },
        }));
        ws.close();
      };
      
      ws.onerror = () => {
        setHealth(prev => ({
          ...prev,
          connectivity: {
            ...prev.connectivity,
            websocket: false,
          },
        }));
      };
      
      setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          ws.close();
          setHealth(prev => ({
            ...prev,
            connectivity: {
              ...prev.connectivity,
              websocket: false,
            },
          }));
        }
      }, 5000);
    } catch (error) {
      setHealth(prev => ({
        ...prev,
        connectivity: {
          ...prev.connectivity,
          websocket: false,
        },
      }));
    }
  };

  // This component is for testing purposes
  return import.meta.env.DEV ? (
    <div
      style={{
        position: 'fixed',
        bottom: 10,
        right: 10,
        padding: '10px',
        background: 'rgba(0, 0, 0, 0.8)',
        color: 'white',
        borderRadius: '5px',
        fontSize: '12px',
        zIndex: 9999,
      }}
    >
      <div>Frontend: {health.frontend.status}</div>
      <div>Backend: {health.backend.status}</div>
      <div>API: {health.connectivity.api ? '✓' : '✗'}</div>
      <div>WebSocket: {health.connectivity.websocket ? '✓' : '✗'}</div>
    </div>
  ) : null;
};

// Export health check function for external use
export const performHealthCheck = async (): Promise<HealthStatus> => {
  const health: HealthStatus = {
    frontend: {
      status: 'healthy',
      version: import.meta.env.VITE_APP_VERSION || '1.0.0',
      buildTime: new Date().toISOString(),
    },
    backend: { status: 'checking' },
    connectivity: { api: false, websocket: false },
  };

  // Check backend
  try {
    const response = await axios.get('/api/v1/health', { timeout: 5000 });
    health.backend = {
      status: 'healthy',
      version: response.data.version,
      database: response.data.database_status === 'healthy',
      redis: response.data.redis_status === 'healthy',
    };
    health.connectivity.api = true;
  } catch {
    health.backend.status = 'unhealthy';
  }

  // Check WebSocket
  await new Promise<void>((resolve) => {
    try {
      const ws = new WebSocket(
        `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws`
      );
      
      const timeout = setTimeout(() => {
        ws.close();
        resolve();
      }, 5000);
      
      ws.onopen = () => {
        health.connectivity.websocket = true;
        clearTimeout(timeout);
        ws.close();
        resolve();
      };
      
      ws.onerror = () => {
        clearTimeout(timeout);
        resolve();
      };
    } catch {
      resolve();
    }
  });

  return health;
};