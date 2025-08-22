// CRITICAL: Force all HTTP URLs to HTTPS globally
// This must be at the very top before any other imports
(() => {
  // Override fetch to force HTTPS
  const originalFetch = window.fetch;
  window.fetch = function(...args: Parameters<typeof fetch>) {
    let url = args[0];
    if (typeof url === 'string' && url.includes('http://luckygas-backend')) {
      console.warn(`[HTTPS Override] Converting HTTP to HTTPS: ${url}`);
      args[0] = url.replace('http://', 'https://');
    } else if (url instanceof Request && url.url.includes('http://luckygas-backend')) {
      console.warn(`[HTTPS Override] Converting HTTP to HTTPS: ${url.url}`);
      const newUrl = url.url.replace('http://', 'https://');
      args[0] = new Request(newUrl, url);
    }
    return originalFetch.apply(this, args);
  };
  
  // Override XMLHttpRequest to force HTTPS
  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method: string, url: string | URL, ...rest: any[]) {
    if (typeof url === 'string' && url.includes('http://luckygas-backend')) {
      console.warn(`[HTTPS Override] Converting HTTP to HTTPS in XMLHttpRequest: ${url}`);
      url = url.replace('http://', 'https://');
    }
    return originalOpen.apply(this, [method, url, ...rest] as any);
  };
  
  console.info('✅ [HTTPS Override] Global HTTP to HTTPS conversion enabled');
})();

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './utils/i18n' // Initialize i18n
import App from './App.tsx'
import * as serviceWorkerRegistration from './serviceWorkerRegistration'
import { setupSafeErrorMonitoring } from './services/safeErrorMonitor'
import { initPerformanceMonitoring } from './utils/performance'

// Import API test utility (runs automatically in dev mode)
if (import.meta.env.DEV) {
  import('./utils/api-test')
}

// Initialize safe error monitoring with circuit breaker protection
setupSafeErrorMonitoring()
console.info('[MAIN] Safe error monitoring enabled with circuit breaker protection')

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
