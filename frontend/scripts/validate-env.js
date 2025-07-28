#!/usr/bin/env node

/**
 * Environment validation script for build time
 * Ensures required environment variables are set before building
 */

// Load environment variables from .env files
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env files in the same order as Vite
dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '../.env.local') });

const requiredEnvVars = {
  VITE_API_URL: {
    required: true,
    pattern: /^https?:\/\/.+/,
    description: 'Backend API URL (e.g., https://api.luckygas.tw)',
  },
  VITE_WS_URL: {
    required: true,
    pattern: /^wss?:\/\/.+/,
    description: 'WebSocket URL for real-time updates',
  },
  VITE_ENV: {
    required: true,
    pattern: /^(development|staging|production)$/,
    description: 'Environment name',
  },
  VITE_GOOGLE_MAPS_API_KEY: {
    required: false,
    pattern: /^AIza[0-9A-Za-z-_]{35}$/,
    description: 'Google Maps API key (optional)',
  },
  VITE_SENTRY_DSN: {
    required: false,
    pattern: /^https:\/\/.+@.+\.ingest\.sentry\.io\/.+$/,
    description: 'Sentry DSN for error tracking (optional)',
  },
};

function validateEnvironment() {
  console.log('🔍 Validating environment variables...\n');
  
  let hasErrors = false;
  const environment = process.env.VITE_ENV || 'development';
  
  console.log(`Environment: ${environment}\n`);
  
  Object.entries(requiredEnvVars).forEach(([varName, config]) => {
    const value = process.env[varName];
    
    if (config.required && !value) {
      console.error(`❌ ${varName}: Missing required variable`);
      console.error(`   Description: ${config.description}\n`);
      hasErrors = true;
      return;
    }
    
    if (value && config.pattern && !config.pattern.test(value)) {
      console.error(`❌ ${varName}: Invalid format`);
      console.error(`   Current value: ${value}`);
      console.error(`   Expected pattern: ${config.pattern}`);
      console.error(`   Description: ${config.description}\n`);
      hasErrors = true;
      return;
    }
    
    if (value) {
      // Mask sensitive values
      const displayValue = varName.includes('KEY') || varName.includes('DSN')
        ? value.substring(0, 10) + '...'
        : value;
      console.log(`✅ ${varName}: ${displayValue}`);
    }
  });
  
  console.log('\n' + '='.repeat(50) + '\n');
  
  if (hasErrors) {
    console.error('❌ Environment validation failed!');
    console.error('Please check your .env file and ensure all required variables are set correctly.\n');
    process.exit(1);
  } else {
    console.log('✅ Environment validation passed!');
    console.log('Ready to build for', environment, '\n');
  }
}

// Run validation
validateEnvironment();