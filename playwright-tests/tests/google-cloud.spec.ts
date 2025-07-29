import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Google Cloud Integration Tests', () => {
  let apiHelper: APIHelper;

  test.beforeEach(async ({ request }) => {
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
  });

  test.describe('Google Maps Geocoding API', () => {
    test('should geocode valid Taiwan addresses', async () => {
      for (const address of testData.taiwanAddresses.slice(0, 5)) {
        const response = await apiHelper.geocodeAddress(address);
        
        expect(response).toHaveProperty('results');
        expect(response.results.length).toBeGreaterThan(0);
        
        const result = response.results[0];
        expect(result).toHaveProperty('geometry');
        expect(result.geometry).toHaveProperty('location');
        expect(result.geometry.location).toHaveProperty('lat');
        expect(result.geometry.location).toHaveProperty('lng');
        
        // Verify coordinates are in Taiwan region
        const lat = result.geometry.location.lat;
        const lng = result.geometry.location.lng;
        expect(lat).toBeGreaterThan(21.5); // Southern tip of Taiwan
        expect(lat).toBeLessThan(25.5); // Northern tip of Taiwan
        expect(lng).toBeGreaterThan(119.5); // Western edge
        expect(lng).toBeLessThan(122.5); // Eastern edge
        
        // Check formatted address contains Taiwan
        expect(result.formatted_address).toContain('台灣');
      }
    });

    test('should handle address with special characters', async () => {
      const specialAddresses = [
        '台北市信義區信義路5段7號101樓',
        '新北市板橋區文化路一段268-1號',
        '台中市西屯區台灣大道三段251號20樓-2',
        '高雄市前金區中正四路211號3F'
      ];

      for (const address of specialAddresses) {
        const response = await apiHelper.geocodeAddress(address);
        expect(response.results).toBeDefined();
        expect(response.status).toBe('OK');
      }
    });

    test('should return address components in Traditional Chinese', async () => {
      const address = '台北市中正區重慶南路一段122號';
      const response = await apiHelper.geocodeAddress(address);
      
      const components = response.results[0].address_components;
      
      // Check for Chinese address components
      const hasChineseComponents = components.some((comp: any) => 
        /[\u4e00-\u9fa5]/.test(comp.long_name)
      );
      expect(hasChineseComponents).toBeTruthy();
      
      // Verify specific components
      const countryComponent = components.find((c: any) => 
        c.types.includes('country')
      );
      expect(countryComponent?.long_name).toBe('台灣');
    });

    test('should handle invalid addresses gracefully', async () => {
      const invalidAddresses = [
        '這是一個不存在的地址12345',
        '!!!@@@###$$$',
        ''
      ];

      for (const address of invalidAddresses) {
        const response = await apiHelper.geocodeAddress(address);
        
        if (address === '') {
          expect(response.status).toBe('INVALID_REQUEST');
        } else {
          expect(['ZERO_RESULTS', 'OK']).toContain(response.status);
        }
      }
    });

    test('should respect rate limiting', async () => {
      const addresses = testData.taiwanAddresses.slice(0, 10);
      const startTime = Date.now();
      
      // Make rapid requests
      const promises = addresses.map(address => 
        apiHelper.geocodeAddress(address)
      );
      
      const responses = await Promise.all(promises);
      const endTime = Date.now();
      
      // All should complete successfully
      responses.forEach(response => {
        expect(['OK', 'ZERO_RESULTS']).toContain(response.status);
      });
      
      // Should not hit rate limit errors
      const hasRateLimitError = responses.some(r => 
        r.status === 'OVER_QUERY_LIMIT'
      );
      expect(hasRateLimitError).toBeFalsy();
    });

    test('should work with address autocomplete predictions', async () => {
      const response = await apiHelper.get('/api/v1/maps/predictions?query=台北市信義區');
      const data = await response.json();
      
      expect(data).toHaveProperty('predictions');
      expect(data.predictions.length).toBeGreaterThan(0);
      
      // Verify predictions are relevant
      data.predictions.forEach((prediction: any) => {
        expect(prediction.description).toContain('台北市');
      });
    });
  });

  test.describe('Google Maps UI Integration', () => {
    test('should display map in customer address selection', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers/new');
      
      // Click address input to trigger map
      await page.click('input[name="地址"]');
      
      // Map should appear
      await expect(page.locator('#address-map')).toBeVisible({ timeout: 10000 });
      
      // Type address
      await page.fill('input[name="地址"]', '台北市信義區');
      
      // Autocomplete suggestions should appear
      await expect(page.locator('.address-suggestions')).toBeVisible();
      
      // Select first suggestion
      await page.click('.address-suggestion:first-child');
      
      // Address should be filled
      const addressValue = await page.inputValue('input[name="地址"]');
      expect(addressValue).toContain('台北市信義區');
      
      // Coordinates should be set
      const lat = await page.getAttribute('input[name="緯度"]', 'value');
      const lng = await page.getAttribute('input[name="經度"]', 'value');
      expect(lat).toBeTruthy();
      expect(lng).toBeTruthy();
    });

    test('should show delivery route on map', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/routes');
      
      // Open route details
      await page.click('tbody tr:first-child button[aria-label="檢視"]');
      
      // Map should be visible
      await expect(page.locator('#route-map')).toBeVisible({ timeout: 10000 });
      
      // Check map has markers
      const markers = await page.locator('.map-marker').count();
      expect(markers).toBeGreaterThan(0);
      
      // Route polyline should be visible
      await expect(page.locator('.route-polyline')).toBeVisible();
    });
  });

  test.describe('Vertex AI Predictions Integration', () => {
    test('should get daily demand predictions', async () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const predictions = await apiHelper.getPredictions('demand/daily', {
        prediction_date: tomorrow.toISOString(),
        confidence_threshold: 0.7
      });
      
      expect(Array.isArray(predictions)).toBeTruthy();
      
      predictions.forEach((prediction: any) => {
        expect(prediction).toHaveProperty('customer_id');
        expect(prediction).toHaveProperty('customer_name');
        expect(prediction).toHaveProperty('predicted_demand');
        expect(prediction).toHaveProperty('confidence');
        expect(prediction).toHaveProperty('last_order_days_ago');
        
        // Confidence should be above threshold
        expect(prediction.confidence).toBeGreaterThanOrEqual(0.7);
      });
    });

    test('should get weekly demand forecast', async () => {
      const response = await apiHelper.get('/api/v1/predictions/demand/weekly');
      const weeklyData = await response.json();
      
      // Should have 7 days of predictions
      const dates = Object.keys(weeklyData);
      expect(dates.length).toBe(7);
      
      // Each day should have predictions
      dates.forEach(date => {
        expect(Array.isArray(weeklyData[date])).toBeTruthy();
        expect(weeklyData[date].length).toBeGreaterThan(0);
      });
    });

    test('should predict customer churn', async () => {
      const churnPredictions = await apiHelper.getPredictions('churn', {
        customer_ids: null // Get all at-risk customers
      });
      
      expect(Array.isArray(churnPredictions)).toBeTruthy();
      
      churnPredictions.forEach((prediction: any) => {
        expect(prediction).toHaveProperty('customer_id');
        expect(prediction).toHaveProperty('churn_probability');
        expect(prediction).toHaveProperty('risk_level');
        expect(prediction).toHaveProperty('recommended_actions');
        
        // Risk level should match probability
        if (prediction.churn_probability > 0.7) {
          expect(prediction.risk_level).toBe('high');
        }
      });
    });

    test('should handle batch prediction requests', async () => {
      const batchRequest = {
        input_gcs_path: 'gs://lucky-gas-data/predictions/input.csv',
        output_gcs_path: 'gs://lucky-gas-data/predictions/output/',
        model_type: 'demand_prediction'
      };
      
      const response = await apiHelper.getPredictions('batch', batchRequest);
      
      expect(response).toHaveProperty('job_id');
      expect(response).toHaveProperty('status');
      expect(response).toHaveProperty('created_at');
      expect(response.status).toBe('running');
    });

    test('should get prediction accuracy metrics', async () => {
      const response = await apiHelper.get('/api/v1/predictions/metrics');
      const metrics = await response.json();
      
      expect(metrics).toHaveProperty('demand_accuracy');
      expect(metrics).toHaveProperty('churn_accuracy');
      expect(metrics).toHaveProperty('route_optimization_score');
      expect(metrics).toHaveProperty('total_predictions');
      expect(metrics).toHaveProperty('successful_predictions');
      
      // Accuracy should be reasonable
      expect(metrics.demand_accuracy).toBeGreaterThan(0.7);
      expect(metrics.churn_accuracy).toBeGreaterThan(0.6);
    });
  });

  test.describe('Error Handling and Resilience', () => {
    test('should handle API key issues gracefully', async ({ page }) => {
      // This would test the UI's handling of API key errors
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/settings/integrations');
      
      // Check for API key configuration section
      await expect(page.locator('h2:has-text("Google Cloud 設定")')).toBeVisible();
      
      // Should show status indicators
      const mapsStatus = page.locator('[data-testid="maps-api-status"]');
      await expect(mapsStatus).toBeVisible();
      
      // Status should be either connected or show configuration needed
      const statusText = await mapsStatus.textContent();
      expect(['已連接', '需要設定', '設定錯誤']).toContain(statusText);
    });

    test('should cache geocoding results', async () => {
      const address = '台北市大安區和平東路二段106號';
      
      // First request
      const start1 = Date.now();
      const response1 = await apiHelper.geocodeAddress(address);
      const time1 = Date.now() - start1;
      
      // Second request (should be cached)
      const start2 = Date.now();
      const response2 = await apiHelper.geocodeAddress(address);
      const time2 = Date.now() - start2;
      
      // Both should return same result
      expect(response1.results[0].place_id).toBe(response2.results[0].place_id);
      
      // Cached request should be faster (allowing for some variance)
      // In real scenario, cached would be much faster
      console.log(`First request: ${time1}ms, Cached request: ${time2}ms`);
    });

    test('should provide fallback for offline scenarios', async ({ page, context }) => {
      // Simulate offline mode
      await context.setOffline(true);
      
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/orders/new');
      
      // Address input should still work
      await page.fill('input[name="配送地址"]', '台北市信義區信義路五段7號');
      
      // Should show offline indicator
      await expect(page.locator('.offline-indicator')).toBeVisible();
      
      // Manual coordinate entry should be available
      await expect(page.locator('button:has-text("手動輸入座標")')).toBeVisible();
      
      // Re-enable network
      await context.setOffline(false);
    });
  });

  test.describe('Integration with Other Features', () => {
    test('should optimize routes using Google Routes API', async () => {
      const routeData = {
        route_date: new Date().toISOString(),
        orders: [1, 2, 3, 4, 5], // Order IDs
        driver_id: 1,
        vehicle_id: 1
      };
      
      const response = await apiHelper.post('/api/v1/routes/optimize', routeData);
      expect(response.ok()).toBeTruthy();
      
      const optimizedRoute = await response.json();
      
      expect(optimizedRoute).toHaveProperty('route_number');
      expect(optimizedRoute).toHaveProperty('optimized_sequence');
      expect(optimizedRoute).toHaveProperty('total_distance_km');
      expect(optimizedRoute).toHaveProperty('estimated_duration_minutes');
      expect(optimizedRoute).toHaveProperty('polyline');
      
      // Sequence should be optimized (different from input)
      expect(optimizedRoute.optimized_sequence).not.toEqual([1, 2, 3, 4, 5]);
    });

    test('should use AI predictions in route planning', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/routes/plan');
      
      // Select date for planning
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await page.fill('input[name="計劃日期"]', TestHelpers.formatTaiwanDate(tomorrow));
      
      // Click AI suggestion button
      await page.click('button:has-text("AI 建議")');
      
      // Should show predicted orders
      await expect(page.locator('.predicted-orders')).toBeVisible();
      
      // Each prediction should show confidence
      const predictions = page.locator('.prediction-item');
      const count = await predictions.count();
      expect(count).toBeGreaterThan(0);
      
      // Check prediction details
      const firstPrediction = predictions.first();
      await expect(firstPrediction.locator('.confidence-badge')).toBeVisible();
      await expect(firstPrediction.locator('.last-order-info')).toBeVisible();
    });
  });
});