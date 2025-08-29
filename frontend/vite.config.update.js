// Add this to vite.config.ts to load from root .env
import { defineConfig, loadEnv } from 'vite'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load env from project root
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  
  return {
    // ... rest of config
    envDir: '..',  // Look for .env in parent directory
  }
})
