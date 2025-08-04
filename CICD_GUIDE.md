# 🚀 Lucky Gas CI/CD Pipeline Guide

## 📋 Overview

Lucky Gas uses GitHub Actions for continuous integration and deployment with automated testing, security scanning, and progressive rollouts.

## 🏗️ Pipeline Architecture

```mermaid
graph TD
    A[Developer Push] --> B[CI Pipeline]
    B --> C{Tests Pass?}
    C -->|Yes| D[Build Images]
    C -->|No| E[Notify Failure]
    D --> F[Deploy to Staging]
    F --> G[Smoke Tests]
    G --> H{Staging OK?}
    H -->|Yes| I[Manual Approval]
    H -->|No| J[Rollback Staging]
    I --> K[Deploy to Production]
    K --> L[Canary 10%]
    L --> M{Metrics OK?}
    M -->|Yes| N[Full Rollout]
    M -->|No| O[Rollback Production]
```

## 📁 Workflow Files

### Core Workflows

1. **`.github/workflows/ci.yml`** - Continuous Integration
   - Linting and type checking
   - Unit and integration tests
   - Security scanning
   - API contract validation
   - Performance tests (main branch)

2. **`.github/workflows/cd.yml`** - Continuous Deployment
   - Staging deployment
   - Production approval
   - Canary deployments
   - Automatic rollback

3. **`.github/workflows/release.yml`** - Release Management
   - Changelog generation
   - GitHub release creation
   - Artifact building
   - Production triggers

4. **`.github/workflows/scheduled.yml`** - Scheduled Tasks
   - Daily backups
   - Old data cleanup
   - Prediction generation
   - Report creation

5. **`.github/workflows/dependencies.yml`** - Dependency Management
   - Weekly updates
   - Security patches
   - Automated PRs

## 🔧 Configuration

### Required Secrets

Configure these in GitHub Settings → Secrets:

```yaml
# Google Cloud Platform
GCP_PROJECT_ID: "luckygas-production"
GCP_PROJECT_ID_STAGING: "luckygas-staging"
GCP_SA_KEY_PRODUCTION: <base64-encoded-service-account-key>
GCP_SA_KEY_STAGING: <base64-encoded-service-account-key>

# Database
DATABASE_URL_PRODUCTION: "postgresql://user:pass@host/db"
DATABASE_URL_STAGING: "postgresql://user:pass@host/db"
CLOUD_SQL_INSTANCE_PRODUCTION: "project:region:instance"
CLOUD_SQL_INSTANCE_STAGING: "project:region:instance"

# APIs
GOOGLE_MAPS_API_KEY: "your-api-key"
PREDICTION_API_KEY: "internal-api-key"

# Notifications
SLACK_WEBHOOK: "https://hooks.slack.com/services/..."
```

### Environment Configuration

Create these environments in GitHub Settings → Environments:

1. **staging**
   - No approval required
   - Auto-deploy from main/develop

2. **production-approval**
   - Requires 2 reviewers
   - Engineering leads or CTO

3. **production**
   - 30-minute wait timer
   - Protected branch only

## 🚦 CI Pipeline Details

### Backend Testing

```yaml
# Runs on every push
- Linting: flake8, black, mypy, isort
- Security: bandit
- Unit tests: pytest with coverage
- Integration tests: with PostgreSQL and Redis
```

### Frontend Testing

```yaml
# Runs on every push
- Linting: ESLint
- Type checking: TypeScript
- Unit tests: Jest with coverage
- Build validation
```

### Security Scanning

```yaml
# Trivy scanning for vulnerabilities
- Backend dependencies
- Frontend dependencies
- Docker images
- Infrastructure as code
```

## 🚀 CD Pipeline Details

### Staging Deployment

1. **Trigger**: Successful CI on main branch
2. **Process**:
   ```bash
   # Build and push Docker image
   docker build -t gcr.io/project/service:staging-$SHA
   docker push
   
   # Deploy to Cloud Run
   gcloud run deploy service-staging
   
   # Run migrations
   alembic upgrade head
   
   # Deploy frontend
   npm run build
   gsutil rsync dist/ gs://bucket-staging/
   ```
3. **Validation**: Smoke tests with Newman

### Production Deployment

1. **Trigger**: Manual approval after staging
2. **Pre-deployment**:
   - Database backup
   - Current image backup
3. **Canary Deployment**:
   ```bash
   # Deploy with no traffic
   gcloud run deploy --tag canary --no-traffic
   
   # Route 10% traffic
   gcloud run services update-traffic --to-tags canary=10
   
   # Monitor for 5 minutes
   # If OK, route 100%
   ```
4. **Rollback**: Automatic on failure

## 📊 Monitoring Integration

### Deployment Metrics

- Deployment frequency
- Lead time for changes
- Mean time to recovery
- Change failure rate

### Health Checks

```yaml
# Backend health endpoint
GET /api/v1/health
Response: {"status": "healthy", "version": "1.2.3"}

# Frontend health
GET /health.json
Response: {"status": "ok", "timestamp": "..."}
```

## 🔄 Rollback Procedures

### Automatic Rollback

Triggered when:
- Health checks fail
- Error rate > 5%
- Response time > 2s (p95)

### Manual Rollback

```bash
# Get previous revision
PREVIOUS=$(gcloud run revisions list --limit=2 | tail -1)

# Route traffic to previous
gcloud run services update-traffic \
  --to-revisions=$PREVIOUS=100
```

## 🏷️ Release Process

### Creating a Release

```bash
# 1. Update version
npm version patch  # or minor/major

# 2. Create tag
git tag -a v1.2.3 -m "Release v1.2.3"

# 3. Push tag
git push origin v1.2.3
```

### Release Workflow

1. Changelog auto-generated from commits
2. GitHub release created
3. Artifacts built and attached
4. Production deployment triggered (if not pre-release)

## 📅 Scheduled Tasks

### Daily Tasks (2 AM Taiwan Time)

1. **Database Backup**
   - Cloud SQL automated backup
   - Export to Cloud Storage
   - 30-day retention

2. **Cleanup**
   - Old backups (>30 days)
   - Old logs (>90 days)
   - Old container images (keep latest 10)

3. **Predictions**
   - Generate daily demand predictions
   - Optimize delivery routes
   - Customer churn analysis

4. **Reports**
   - Daily operations summary
   - Performance metrics
   - Revenue analytics

## 🔒 Security Practices

### Dependency Scanning

- Weekly automated updates
- Security vulnerability checks
- Automated fix PRs

### Secret Management

- All secrets in GitHub Secrets
- Rotated every 90 days
- Never in code or logs

### Access Control

- Service accounts with minimal permissions
- Separate accounts for staging/production
- Audit logging enabled

## 📈 Performance Optimization

### CI Optimization

- Dependency caching
- Parallel job execution
- Docker layer caching
- Conditional workflows

### CD Optimization

- Blue-green deployments
- Progressive rollouts
- CDN cache warming
- Database connection pooling

## 🐛 Troubleshooting

### Common Issues

1. **CI Failures**
   ```bash
   # Check specific job logs
   # Verify dependencies installed
   # Check for flaky tests
   ```

2. **Deployment Failures**
   ```bash
   # Check service account permissions
   # Verify secrets are set
   # Check resource quotas
   ```

3. **Rollback Issues**
   ```bash
   # Manually specify revision
   # Check traffic splitting
   # Verify health checks
   ```

## 🛠️ Local Testing

### Running CI Locally

```bash
# Backend
cd backend
black --check app tests
flake8 app tests
mypy app
pytest

# Frontend
cd frontend
npm run lint
npm run type-check
npm test
```

### Testing Workflows

```bash
# Install act
brew install act

# Run CI workflow
act -W .github/workflows/ci.yml

# Run with secrets
act -W .github/workflows/cd.yml --secret-file .env.secrets
```

## 📚 Best Practices

1. **Commit Messages**
   - Use conventional commits
   - Include ticket numbers
   - Be descriptive

2. **Branch Protection**
   - Require PR reviews
   - Require status checks
   - No force pushes

3. **Testing**
   - Write tests for new features
   - Maintain >80% coverage
   - Include E2E tests

4. **Deployment**
   - Always deploy to staging first
   - Monitor canary deployments
   - Have rollback plan ready

## 🔗 Related Documentation

- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT_GUIDE.md)
- [Testing Guide](./TESTING_GUIDE.md)
- [Disaster Recovery Playbook](./DISASTER_RECOVERY_PLAYBOOK.md)
- [API Documentation](./API_DOCUMENTATION.md)