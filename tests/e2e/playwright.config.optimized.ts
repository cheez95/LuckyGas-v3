import { defineConfig, devices } from '@playwright/test';

/**
 * Optimized Playwright configuration for faster test execution
 */
export default defineConfig({
  testDir: './specs',
  timeout: 30 * 1000, // Reduced from 60s
  globalSetup: require.resolve('./fixtures/global-setup.ts'),
  expect: {
    timeout: 5000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0, // Reduced retries
  workers: process.env.CI ? 2 : 8, // Increased workers for local
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list']
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5174',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000, // Reduced from 15s
    
    // Speed optimizations
    launchOptions: {
      args: [
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=IsolateOrigins',
        '--disable-site-isolation-trials'
      ],
    },
  },

  // Optimized project configuration - only essential viewports
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // Conditional server configuration
  webServer: process.env.CI ? undefined : [
    {
      command: 'cd ../../frontend && npm run dev',
      port: 5174,
      reuseExistingServer: true,
      timeout: 60 * 1000,
    },
    {
      command: 'cd ../../backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload',
      port: 8000,
      reuseExistingServer: true,
      timeout: 60 * 1000,
      env: {
        ENVIRONMENT: 'test',
        TESTING: 'true',
        DEVELOPMENT_MODE: 'true',
      },
    },
  ],
});