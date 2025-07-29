#!/bin/bash

# Lucky Gas Production Environment Setup Helper
# This script helps generate secure values for production deployment

echo "=== Lucky Gas Production Environment Setup ==="
echo ""
echo "This script will help you generate secure values for production."
echo "Copy the generated values to your .env file."
echo ""

# Generate SECRET_KEY
echo "1. Generating SECRET_KEY..."
SECRET_KEY=$(openssl rand -base64 32)
echo "   SECRET_KEY=$SECRET_KEY"
echo ""

# Generate POSTGRES_PASSWORD
echo "2. Generating POSTGRES_PASSWORD..."
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | head -c 32)
echo "   POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo ""

# Generate REDIS_PASSWORD
echo "3. Generating REDIS_PASSWORD..."
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | head -c 32)
echo "   REDIS_PASSWORD=$REDIS_PASSWORD"
echo ""

# Reminder for manual configurations
echo "=== Manual Configuration Required ==="
echo ""
echo "4. Google Cloud Setup:"
echo "   - Create a GCP project and note the project ID"
echo "   - Enable Google Maps API and get an API key"
echo "   - Create a service account with required permissions"
echo "   - Download the service account JSON key"
echo "   - Place it in backend/credentials/prod-service-account.json"
echo ""
echo "5. Domain Configuration:"
echo "   - Update BACKEND_CORS_ORIGINS with your domains"
echo "   - Update VITE_API_URL with your API domain"
echo "   - Update VITE_WS_URL with your WebSocket domain"
echo ""
echo "6. Email Configuration:"
echo "   - Set up SMTP credentials for email notifications"
echo ""
echo "7. Monitoring (Optional):"
echo "   - Set up Sentry for error tracking"
echo "   - Configure New Relic for performance monitoring"
echo ""

# Create example docker-compose production override
echo "=== Creating docker-compose.prod.yml ==="
cat > docker-compose.prod.yml << 'EOF'
# Production overrides for docker-compose
version: '3.8'

services:
  backend:
    restart: always
    environment:
      ENVIRONMENT: production
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  frontend:
    restart: always
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl:ro
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  postgres:
    restart: always
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  redis:
    restart: always
    volumes:
      - redis_data_prod:/data
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  postgres_data_prod:
  redis_data_prod:
EOF

echo "   Created docker-compose.prod.yml"
echo ""

echo "=== Production Deployment Commands ==="
echo ""
echo "# To run in production mode:"
echo "docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
echo ""
echo "# To view logs:"
echo "docker-compose logs -f [service_name]"
echo ""
echo "# To backup database:"
echo "docker exec luckygas-postgres pg_dump -U luckygas_prod luckygas_production > backup_\$(date +%Y%m%d).sql"
echo ""
echo "=== Setup Complete ==="
echo "Remember to:"
echo "1. Copy generated values to your .env file"
echo "2. Complete manual configuration steps"
echo "3. Test thoroughly before going live"
echo "4. Set up regular backups"
echo "5. Monitor system health"