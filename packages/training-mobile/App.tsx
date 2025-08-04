import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { NavigationContainer } from '@react-navigation/native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider as PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import Toast from 'react-native-toast-message';
import { NetworkProvider } from 'react-native-offline';

import { AuthProvider } from './src/contexts/AuthContext';
import { ThemeProvider } from './src/contexts/ThemeContext';
import { NotificationProvider } from './src/contexts/NotificationContext';
import { OfflineProvider } from './src/contexts/OfflineContext';
import RootNavigator from './src/navigation/RootNavigator';
import { theme } from './src/constants/theme';
import { toastConfig } from './src/config/toast';
import { setupNotifications } from './src/services/notifications';

// Keep the splash screen visible while we fetch resources
SplashScreen.preventAutoHideAsync();

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

export default function App() {
  useEffect(() => {
    async function prepare() {
      try {
        // Setup notifications
        await setupNotifications();
        
        // Artificially delay for two seconds to simulate a slow loading
        // experience. Remove this in production!
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (e) {
        console.warn(e);
      } finally {
        // Tell the application to render
        await SplashScreen.hideAsync();
      }
    }

    prepare();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <NetworkProvider>
        <SafeAreaProvider>
          <PaperProvider theme={theme}>
            <ThemeProvider>
              <AuthProvider>
                <NotificationProvider>
                  <OfflineProvider>
                    <NavigationContainer>
                      <RootNavigator />
                      <StatusBar style="auto" />
                    </NavigationContainer>
                  </OfflineProvider>
                </NotificationProvider>
              </AuthProvider>
            </ThemeProvider>
          </PaperProvider>
        </SafeAreaProvider>
      </NetworkProvider>
      <Toast config={toastConfig} />
    </QueryClientProvider>
  );
}