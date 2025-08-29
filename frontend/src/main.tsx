// Force all HTTP URLs to HTTPS globally (security requirement)
(() => {
  const originalFetch = window.fetch;
  window.fetch = function(...args: Parameters<typeof fetch>) {
    const url = args[0];
    if (typeof url === 'string' && url.includes('http://luckygas-backend') && !url.includes('localhost')) {
      console.warn(`[HTTPS Override] Converting HTTP to HTTPS: ${url}`);
      args[0] = url.replace('http://', 'https://');
    } else if (url instanceof Request && url.url.includes('http://luckygas-backend') && !url.url.includes('localhost')) {
      console.warn(`[HTTPS Override] Converting HTTP to HTTPS: ${url.url}`);
      const newUrl = url.url.replace('http://', 'https://');
      args[0] = new Request(newUrl, url);
    }
    return originalFetch.apply(this, args);
  };
  
  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method: string, url: string | URL, ...rest: any[]) {
    if (typeof url === 'string' && url.includes('http://luckygas-backend') && !url.includes('localhost')) {
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
import './utils/i18n'
import App from './App.tsx'
import * as serviceWorkerRegistration from './serviceWorkerRegistration'
import { setupSafeErrorMonitoring } from './services/safeErrorMonitor'
import { initPerformanceMonitoring } from './utils/performance'

if (import.meta.env.DEV) {
  import('./utils/api-test')
}

setupSafeErrorMonitoring()
console.info('[MAIN] Safe error monitoring enabled with circuit breaker protection')

if (typeof window !== 'undefined') {
  initPerformanceMonitoring();
  
  window.addEventListener('load', () => {
    const navigationEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (navigationEntry) {
      const loadTime = navigationEntry.loadEventEnd - navigationEntry.fetchStart;
    }
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

serviceWorkerRegistration.register({
  onSuccess: () => {
  },
  onUpdate: () => {
  },
});
