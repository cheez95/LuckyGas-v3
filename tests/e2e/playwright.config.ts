import { defineConfig, devices } from '@playwright/test';

/**
 * Comprehensive Playwright configuration for LuckyGas E2E tests
 * Supports multiple browsers, viewports, and test scenarios
 */
export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 4,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'junit-results.xml' }],
    ['list'],
  ],
  
  // Global test timeout
  timeout: 60 * 1000,
  
  // Global setup to pre-authenticate users
  globalSetup: require.resolve('./fixtures/global-setup'),
  
  // Global test configuration
  use: {
    // Base URL for the application
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    
    // Collect trace on test failure
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video recording
    video: 'retain-on-failure',
    
    // Traditional Chinese locale
    locale: 'zh-TW',
    
    // Timezone for Taiwan
    timezoneId: 'Asia/Taipei',
    
    // Global timeout for actions
    actionTimeout: 30 * 1000,
    
    // Network timeout
    navigationTimeout: 30 * 1000,
  },

  // Configure projects for different browsers and viewports
  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'edge',
      use: { ...devices['Desktop Edge'] },
    },

    // Mobile viewports for driver interface
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },

    // Tablet viewports
    {
      name: 'tablet',
      use: { ...devices['iPad (gen 7)'] },
    },

    // Performance testing configuration
    {
      name: 'performance',
      use: {
        ...devices['Desktop Chrome'],
        // Throttle CPU to simulate slower devices
        launchOptions: {
          args: ['--enable-precise-memory-info'],
        },
      },
    },

    // Visual regression testing
    {
      name: 'visual',
      use: {
        ...devices['Desktop Chrome'],
        // Consistent viewport for visual tests
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],

  // Web server configuration to start services
  // NOTE: Commented out for now - services should be started manually
  // webServer: [
  //   {
  //     command: 'cd ../../backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000',
  //     port: 8000,
  //     timeout: 120 * 1000,
  //     reuseExistingServer: !process.env.CI,
  //     env: {
  //       TESTING: '1',
  //       DATABASE_URL: process.env.TEST_DATABASE_URL || 'postgresql://test:test@localhost:5432/luckygas_test',
  //     },
  //   },
  //   {
  //     command: 'cd ../../frontend && npm run dev',
  //     port: 3000,
  //     timeout: 120 * 1000,
  //     reuseExistingServer: !process.env.CI,
  //     env: {
  //       VITE_API_URL: 'http://localhost:8000',
  //     },
  //   },
  // ],
});