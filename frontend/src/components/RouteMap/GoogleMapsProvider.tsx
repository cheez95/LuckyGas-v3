import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { message } from 'antd';
import { mapsLoader } from '../../services/mapLoader.service';

interface GoogleMapsContextType {
  isLoaded: boolean;
  loadError: Error | null;
  google: typeof window.google | null;
}

const GoogleMapsContext = createContext<GoogleMapsContextType>({
  isLoaded: false,
  loadError: null,
  google: null,
});

export const useGoogleMaps = () => {
  const context = useContext(GoogleMapsContext);
  if (!context) {
    throw new Error('useGoogleMaps must be used within a GoogleMapsProvider');
  }
  return context;
};

interface GoogleMapsProviderProps {
  children: ReactNode;
}

export const GoogleMapsProvider: React.FC<GoogleMapsProviderProps> = ({ children }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadError, setLoadError] = useState<Error | null>(null);

  useEffect(() => {
    const loadMaps = async () => {
      try {
        await mapsLoader.load({
          libraries: ['places', 'geometry', 'drawing', 'visualization'],
          language: 'zh-TW',
          region: 'TW',
          version: 'weekly',
        });
        setIsLoaded(true);
      } catch (error) {
        console.error('Failed to load Google Maps:', error);
        setLoadError(error as Error);
        message.error('無法載入地圖服務，請檢查網路連線');
      }
    };

    if (!mapsLoader.isGoogleMapsLoaded()) {
      loadMaps();
    } else {
      setIsLoaded(true);
    }
  }, []);

  const contextValue: GoogleMapsContextType = {
    isLoaded,
    loadError,
    google: isLoaded ? window.google : null,
  };

  return (
    <GoogleMapsContext.Provider value={contextValue}>
      {children}
    </GoogleMapsContext.Provider>
  );
};

export default GoogleMapsProvider;