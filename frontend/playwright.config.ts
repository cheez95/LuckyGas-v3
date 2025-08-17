import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
dotenv.config({ path: '.env.test' });

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  // Run tests in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 1,
  
  // Parallel workers
  workers: process.env.CI ? 1 : 3,
  
  // Reporter to use
  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list'],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  
  // Shared settings for all projects
  use: {
    // Base URL to use in actions - test deployed app
    baseURL: 'https://vast-tributary-466619-m8.web.app',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'retain-on-failure',
    
    // Maximum time per action
    actionTimeout: 15000,
    
    // Test against real browsers
    headless: true,
    
    // Viewport
    viewport: { width: 1280, height: 720 },
    
    // Locale
    locale: 'zh-TW',
    
    // Timezone
    timezoneId: 'Asia/Taipei',
  },

  // Configure projects for test suites
  projects: [
    // Test suites
    {
      name: 'critical',
      testMatch: /critical\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    
    {
      name: 'visual',
      testMatch: /visual\/.*\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        // Visual tests need consistent viewport
        viewport: { width: 1920, height: 1080 },
      },
    },
    
    {
      name: 'performance',
      testMatch: /performance\/.*\.spec\.ts/,
      use: { 
        ...devices['Desktop Chrome'],
        // Performance tests need real browser context
        launchOptions: {
          args: ['--enable-precise-memory-info'],
        },
      },
    },
    
    {
      name: 'api',
      testMatch: /api\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    
    {
      name: 'resilience',
      testMatch: /resilience\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Original comprehensive test
    {
      name: 'comprehensive',
      testMatch: /comprehensive-frontend-test\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Cross-browser testing for critical paths
    {
      name: 'critical-firefox',
      testMatch: /critical\/.*\.spec\.ts/,
      use: { ...devices['Desktop Firefox'] },
    },
    
    {
      name: 'critical-webkit',
      testMatch: /critical\/.*\.spec\.ts/,
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile testing
    {
      name: 'mobile-critical',
      testMatch: /critical\/.*\.spec\.ts/,
      use: { ...devices['iPhone 13'] },
    },
  ],

  // Timeout settings
  timeout: 30000, // 30 seconds per test
  expect: {
    timeout: 5000, // 5 seconds for expect assertions
  },

  // Output folder for test artifacts
  outputDir: 'test-results/',

  // Folder for test artifacts such as screenshots, videos, traces, etc.
  snapshotDir: './e2e/screenshots',
  snapshotPathTemplate: '{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}{-projectName}{-snapshotSuffix}{ext}',

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    env: {
      VITE_API_URL: 'http://localhost:8000',
    },
  },
});