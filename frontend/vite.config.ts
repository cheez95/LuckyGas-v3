import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import viteCompression from 'vite-plugin-compression'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env from current directory
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    // Use absolute paths for Firebase hosting with SPA
    base: '/',
    // Load .env from current directory
    envDir: '.',
    plugins: [
    // Force HTTPS plugin - MUST be first to process all code
    {
      name: 'force-https',
      enforce: 'pre',
      transform(code, id) {
        // Skip node_modules
        if (id.includes('node_modules')) {
          return null;
        }
        
        // Replace any HTTP URLs with HTTPS for luckygas-backend
        let modified = false;
        let newCode = code;
        
        // Replace http:// with https:// for luckygas-backend URLs
        if (code.includes('http://luckygas-backend')) {
          newCode = newCode.replace(/http:\/\/luckygas-backend/g, 'https://luckygas-backend');
          modified = true;
          console.log(`[force-https] Replaced HTTP with HTTPS in ${id}`);
        }
        
        // Also check for any staging URLs with HTTP
        if (code.includes('http://') && code.includes('staging')) {
          newCode = newCode.replace(/http:\/\/([^\/\s'"]+staging[^\/\s'"]*)/g, 'https://$1');
          modified = true;
          console.log(`[force-https] Replaced staging HTTP URL in ${id}`);
        }
        
        return modified ? newCode : null;
      },
      // Also process HTML
      transformIndexHtml(html) {
        return html.replace(/http:\/\/luckygas-backend/g, 'https://luckygas-backend');
      }
    },
    react(),
    // Bundle size analysis
    visualizer({
      filename: './dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
    // Gzip compression
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    // Brotli compression
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
  ],
  build: {
    // Enable source maps for production debugging
    sourcemap: false,
    // Increase chunk size warning limit
    chunkSizeWarningLimit: 1000,
    // Rollup options for code splitting
    rollupOptions: {
      output: {
        // Manual chunk splitting strategy
        manualChunks: {
          // Vendor chunks - rarely changing libraries
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-ui': ['antd', '@ant-design/icons'],
          'vendor-utils': ['axios', 'dayjs', 'lodash-es'],
          'vendor-charts': ['recharts'],
          // Feature chunks - split by feature
          'feature-maps': ['@react-google-maps/api'],
        },
        // Optimize chunk names
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/').pop() : 'chunk';
          return `js/[name]-${facadeModuleId}-[hash].js`;
        },
        // Optimize entry file names
        entryFileNames: 'js/[name]-[hash].js',
        // Optimize asset file names
        assetFileNames: (assetInfo) => {
          const extType = assetInfo.name?.split('.').pop() || 'asset';
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return `images/[name]-[hash][extname]`;
          }
          if (/css/i.test(extType)) {
            return `css/[name]-[hash][extname]`;
          }
          if (/woff|woff2|eot|ttf|otf/i.test(extType)) {
            return `fonts/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
      },
    },
    // Terser minification options
    terserOptions: {
      compress: {
        drop_console: true, // Remove console logs in production
        drop_debugger: true, // Remove debugger statements
      },
    },
    // Asset size optimization
    assetsInlineLimit: 4096, // Inline assets smaller than 4kb
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['react', 'react-dom', 'antd', 'axios', 'dayjs'],
    exclude: ['@react-google-maps/api'], // Exclude heavy deps from pre-bundling
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
        ws: true, // Enable WebSocket proxy
      }
    }
  }
  }
})
