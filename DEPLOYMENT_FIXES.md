# LuckyGas Deployment Fixes - Summary

## 🎯 Issues Fixed

### 1. Frontend Docker Build Issues ✅
**Problem**: Frontend Docker build was failing due to missing devDependencies (TypeScript, Vite, dotenv)

**Solution**:
- Created optimized multi-stage Dockerfile with proper dependency management
- Added `--include=dev` flag to npm ci to install all dependencies during build
- Created `docker-build.sh` script that bypasses env validation in CI/CD environments
- Added `build:docker` npm script for Docker-specific builds

**Files Modified**:
- `frontend/Dockerfile` - Optimized multi-stage build
- `frontend/package.json` - Added build:docker script
- `frontend/scripts/docker-build.sh` - New Docker build script

### 2. GCP Project ID Updates ✅
**Problem**: Hardcoded references to "luckygas-staging" instead of actual project ID

**Solution**:
- Updated all references from `luckygas-staging` to `vast-tributary-466619-m8`
- Fixed Kubernetes configurations, Terraform files, and environment files
- Created `update-project-id.sh` script for bulk updates

**Files Modified**:
- `k8s/overlays/staging/kustomization.yaml`
- `k8s/overlays/staging/ingress-patch.yaml`
- `backend/k8s/base/*.yaml` (all K8s manifests)
- `backend/.env.staging`
- `infrastructure/environments/staging.tfvars`
- `backend/infrastructure/terraform/environments/staging.tfvars`

### 3. Optimized Build Strategy ✅
**Features**:
- Multi-stage Docker builds for smaller images
- Dependency caching for faster rebuilds
- Separate build and runtime stages
- Non-root user for security
- Health checks included

### 4. Simplified Deployment Script ✅
**Features**:
- Better error handling with colored output
- Progress indicators for each step
- Prerequisite checks
- Flexible options (--skip-build, --skip-push, etc.)
- Automatic URL discovery after deployment
- Timeout protection for builds

**New Scripts**:
- `scripts/deploy-staging.sh` - Main deployment script
- `scripts/validate-deployment.sh` - Pre-deployment validation
- `scripts/update-project-id.sh` - Project ID migration helper

## 🚀 Quick Deployment Guide

### 1. Validate Deployment Readiness
```bash
./scripts/validate-deployment.sh
```

### 2. Deploy to Staging
```bash
# Full deployment (build + push + deploy)
./scripts/deploy-staging.sh

# Skip build if images already exist
./scripts/deploy-staging.sh --skip-build

# Deploy only frontend or backend
./scripts/deploy-staging.sh --frontend-only
./scripts/deploy-staging.sh --backend-only
```

### 3. Manual Docker Build (if needed)
```bash
# Frontend
cd frontend
docker build \
  --build-arg VITE_API_URL="https://api-staging.luckygas.com.tw" \
  --build-arg VITE_WS_URL="wss://api-staging.luckygas.com.tw/ws" \
  --build-arg VITE_ENV="staging" \
  -t gcr.io/vast-tributary-466619-m8/luckygas-frontend:staging-latest .

# Backend
cd backend
docker build -t gcr.io/vast-tributary-466619-m8/luckygas-backend:staging-latest .
```

## 📋 Remaining Tasks

### Still Need Manual Updates
Some files still contain "luckygas-staging" references in documentation and scripts:
- Various .md files (documentation only)
- Some test configuration files
- Integration test scripts

Run this to find remaining references:
```bash
grep -r "luckygas-staging" . --exclude-dir=.git --exclude-dir=node_modules
```

### Next Steps
1. Set up Cloud SQL instance in the new project
2. Create service accounts with proper permissions
3. Configure Secret Manager for sensitive values
4. Set up Cloud Storage buckets
5. Configure domain/DNS if using custom domains

## 🔧 Environment Variables

### Frontend Build Args
- `VITE_API_URL` - Backend API URL
- `VITE_WS_URL` - WebSocket URL
- `VITE_ENV` - Environment (staging/production)
- `VITE_GOOGLE_MAPS_API_KEY` - Optional
- `VITE_SENTRY_DSN` - Optional

### Backend Environment
See `backend/.env.staging` for full list. Key variables:
- `GCP_PROJECT_ID=vast-tributary-466619-m8`
- `CLOUD_SQL_CONNECTION_NAME` - Update after creating Cloud SQL
- `GCS_BUCKET_NAME` - Update after creating bucket

## ⚡ Performance Optimizations

1. **Docker Build Caching**:
   - Separate dependency installation stage
   - Copy only package files first
   - Leverage Docker layer caching

2. **Build Time Reduction**:
   - Skip env validation in CI/CD
   - Use npm ci for faster installs
   - Parallel build stages where possible

3. **Image Size Optimization**:
   - Multi-stage builds
   - Alpine-based images
   - Remove build dependencies from final image

## 🛡️ Security Improvements

1. Non-root user in containers
2. Read-only root filesystem
3. Minimal base images
4. No hardcoded secrets
5. Health check endpoints

## 📝 Notes

- The project ID `vast-tributary-466619-m8` is now used consistently
- All deployment scripts use the new project ID
- Frontend build handles missing env vars gracefully in CI/CD
- Deployment script has timeout protection (10 minutes for builds)

## 🆘 Troubleshooting

### Build Failures
1. Check Docker daemon is running
2. Ensure sufficient disk space
3. Verify all dependencies in package.json
4. Check build args are provided

### Deployment Failures
1. Verify GCP authentication: `gcloud auth list`
2. Check project is set: `gcloud config get-value project`
3. Ensure service accounts exist
4. Check Cloud Run API is enabled

### Runtime Errors
1. Check Cloud Run logs: `gcloud run logs read`
2. Verify environment variables are set
3. Check database connectivity
4. Verify CORS settings