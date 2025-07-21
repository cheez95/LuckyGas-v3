#!/bin/bash
# Parallel Execution Commands for FE-INT & GCP-SETUP Epics
# Execute these in separate terminal windows or sessions

echo "🚀 Lucky Gas Production Deployment - Parallel Epic Execution"
echo "==========================================================="
echo ""
echo "📋 Epic 1: Frontend-Backend Integration (FE-INT)"
echo "Execute in Terminal 1:"
echo ""
cat << 'EOF'
/sc:spawn --parallel "Execute Frontend-Backend Integration epic FE-INT for Lucky Gas Production Deployment PROD-DEPLOY-001. 

Context:
- Backend API is running and secured at http://localhost:8000
- Frontend location: /Users/lgee258/Desktop/LuckyGas-v3/frontend
- Backend has JWT authentication already implemented
- Need to connect React frontend to FastAPI backend

Tasks to complete:
1. API Client Configuration (Story FE-INT-01):
   - Create axios instance with base URL configuration
   - Add request/response interceptors for auth tokens
   - Handle token refresh on 401 responses
   - Create service layer for all API endpoints
   - Test with existing /health and /api/v1/auth/login endpoints

2. Authentication Flow (Story FE-INT-02):
   - Build login/logout UI components
   - Implement protected route wrapper using React Router
   - Store JWT tokens securely (consider security implications)
   - Add automatic token refresh before expiry
   - Implement role-based component rendering

3. Environment Configuration (Story FE-INT-03):
   - Set up .env files for dev/staging/prod
   - Configure API URLs for each environment
   - Add build-time validation
   - Create deployment configurations

CORS domains to configure:
- Development: http://localhost:5173, http://localhost:3000
- Production: https://app.luckygas.tw, https://www.luckygas.tw

Update task status in /Users/lgee258/Desktop/LuckyGas-v3/backend/TASK_TRACKING.json as you progress." --strategy systematic --validate
EOF

echo ""
echo "==========================================================="
echo ""
echo "☁️ Epic 2: Google Cloud Setup (GCP-SETUP)"
echo "Execute in Terminal 2:"
echo ""
cat << 'EOF'
/sc:spawn --parallel "Execute Google Cloud Setup epic GCP-SETUP for Lucky Gas Production Deployment PROD-DEPLOY-001.

Context:
- Backend configuration: /Users/lgee258/Desktop/LuckyGas-v3/backend
- Security requirements from CRITICAL_ACTIONS_CHECKLIST.md completed
- Need production GCP project setup
- Must follow principle of least privilege

Tasks to complete:
1. Service Account Configuration (Story GCP-SETUP-01):
   - Create service account: lucky-gas-prod@[PROJECT_ID].iam.gserviceaccount.com
   - Assign minimal IAM roles:
     * Routes API: roles/routes.viewer
     * Vertex AI: roles/aiplatform.user
     * Cloud Storage: roles/storage.objectAdmin (bucket-specific)
     * Secret Manager: roles/secretmanager.secretAccessor
   - Generate and download JSON key
   - Document key rotation schedule (90 days)
   - Set up workload identity if using GKE

2. API Services Setup (Story GCP-SETUP-02):
   - Enable required APIs:
     * Routes API (routes.googleapis.com)
     * Vertex AI API (aiplatform.googleapis.com)
     * Cloud Storage API (storage.googleapis.com)
     * Secret Manager API (secretmanager.googleapis.com)
   - Configure quotas:
     * Routes API: 10 requests/second
     * Vertex AI: 5 requests/second
   - Create storage bucket: gs://lucky-gas-storage
   - Set up cost alerts at $50 warning, $100 critical

3. Security Configuration (Story GCP-SETUP-03):
   - Enable Security Command Center
   - Configure VPC Service Controls perimeter
   - Set up Cloud Armor WAF rules
   - Enable comprehensive audit logging
   - Configure DLP scanning for PII

Create setup documentation in /Users/lgee258/Desktop/LuckyGas-v3/backend/GCP_SETUP_GUIDE.md
Update task status in TASK_TRACKING.json as you progress." --strategy systematic --validate
EOF

echo ""
echo "==========================================================="
echo ""
echo "📊 Monitoring Commands:"
echo ""
echo "# Check FE-INT progress"
echo "/sc:task status FE-INT"
echo ""
echo "# Check GCP-SETUP progress"
echo "/sc:task status GCP-SETUP"
echo ""
echo "# View overall project analytics"
echo "/sc:task analytics PROD-DEPLOY-001"
echo ""
echo "# Validate epic completion"
echo "/sc:task validate FE-INT --evidence"
echo "/sc:task validate GCP-SETUP --evidence"
echo ""
echo "⚡ Pro tip: Run both spawn commands in separate terminals for true parallel execution!"