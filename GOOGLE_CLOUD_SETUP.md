# Google Cloud Services Setup Guide

## Issue with Current API Key

The current Google Maps API key (`AIzaSyApXfqNpz9fgaf8_S7hXBpG3bXmhc28a5o`) is configured with **HTTP referrer restrictions** which only allow it to be used from browsers. This causes the error:

```
"API keys with referer restrictions cannot be used with this API."
```

## Solution: Create a Server-Side API Key

### Option 1: Create a New API Key for Server Use

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** → **Credentials**
3. Click **+ CREATE CREDENTIALS** → **API key**
4. Name it "Lucky Gas Backend API Key"
5. Under **Application restrictions**, select **IP addresses**
6. Add your server's IP addresses:
   - For development: `127.0.0.1`, `::1`
   - For production: Your server's public IP
7. Under **API restrictions**, select **Restrict key**
8. Select these APIs:
   - Google Maps Geocoding API
   - Google Maps Directions API
   - Google Maps Distance Matrix API
   - Google Maps Places API

### Option 2: Modify Existing Key (Not Recommended)

1. Change the existing key from **HTTP referrers** to **IP addresses**
2. This will break any frontend usage of the same key

### Option 3: Use Two Keys (Recommended)

1. Keep current key for frontend (browser) use
2. Create new key for backend (server) use
3. Update backend `.env`:
   ```env
   GOOGLE_MAPS_API_KEY=your-new-server-key
   GOOGLE_MAPS_FRONTEND_KEY=AIzaSyApXfqNpz9fgaf8_S7hXBpG3bXmhc28a5o
   ```

## Vertex AI Predictions Setup

The predictions endpoint is returning 404 because it's not implemented. To enable AI predictions:

### 1. Enable Vertex AI API
```bash
gcloud services enable aiplatform.googleapis.com
```

### 2. Create Service Account
```bash
gcloud iam service-accounts create luckygas-backend \
    --display-name="Lucky Gas Backend Service"
```

### 3. Grant Permissions
```bash
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:luckygas-backend@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### 4. Download Service Account Key
```bash
gcloud iam service-accounts keys create \
    backend/credentials/prod-service-account.json \
    --iam-account=luckygas-backend@YOUR-PROJECT-ID.iam.gserviceaccount.com
```

### 5. Update Backend Environment
```env
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/prod-service-account.json
HOST_GOOGLE_CREDENTIALS=./backend/credentials/prod-service-account.json
VERTEX_AI_LOCATION=asia-east1
VERTEX_AI_MODEL_NAME=your-model-name
```

## Testing After Setup

### Test Geocoding
```bash
curl -X GET "http://localhost:8000/api/v1/maps/geocode?address=台北市大安區和平東路二段123號" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Expected Response
```json
{
  "results": [{
    "formatted_address": "No. 123, Section 2, Heping E Rd, Da'an District, Taipei City, Taiwan 106",
    "geometry": {
      "location": {
        "lat": 25.0263,
        "lng": 121.5438
      }
    }
  }],
  "status": "OK"
}
```

## Current Status
- ✅ Geocoding API URL fixed (was `/geocoding/json`, now `/geocode/json`)
- ❌ API key has referer restrictions - needs server-side key
- ❌ Predictions endpoint not implemented - needs Vertex AI setup