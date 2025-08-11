import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import viteCompression from 'vite-plugin-compression'

// https://vite.dev/config/
export default defineConfig({
  // Use relative paths for Cloud Storage deployment
  base: './',
  plugins: [
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
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true, // Enable WebSocket proxy
      }
    }
  }
})
