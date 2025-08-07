import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './utils/i18n' // Initialize i18n
import App from './App.tsx'
import * as serviceWorkerRegistration from './serviceWorkerRegistration'
import { setupErrorMonitoring } from './services/errorMonitoring'
import { initPerformanceMonitoring } from './utils/performance'

// Setup error monitoring
setupErrorMonitoring()

// Initialize performance monitoring
if (typeof window !== 'undefined') {
  initPerformanceMonitoring();
  
  // Report performance metrics after page load
  window.addEventListener('load', () => {
    // Log performance budget status
    const navigationEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (navigationEntry) {
      const loadTime = navigationEntry.loadEventEnd - navigationEntry.fetchStart;
      console.log(`📊 Page Load Time: ${loadTime.toFixed(0)}ms ${loadTime < 3000 ? '✅' : '⚠️'}`);
    }
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Register service worker for offline functionality
serviceWorkerRegistration.register({
  onSuccess: () => {
    console.log('Service Worker registered successfully for offline mode');
  },
  onUpdate: () => {
    console.log('New version available! Please refresh the page.');
  },
});
