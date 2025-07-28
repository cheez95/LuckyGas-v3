# Frontend Dockerfile - Multi-stage build for production
# Build stage
FROM node:20-alpine AS builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
ARG NODE_ENV=production

# Install build dependencies
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with exact versions for reproducibility
RUN npm ci --only=production && \
    npm cache clean --force

# Copy source code
COPY . .

# Build the application with production optimizations
ENV NODE_ENV=production
RUN npm run build

# Production stage
FROM nginx:alpine

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    tzdata \
    curl

# Create non-root user
RUN addgroup -g 1000 -S appuser && \
    adduser -u 1000 -S appuser -G appuser

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Create necessary directories and set permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx /var/log/nginx /usr/share/nginx/html && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

# Copy built files from builder stage
COPY --from=builder --chown=appuser:appuser /app/dist /usr/share/nginx/html

# Add metadata labels
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="LuckyGas Frontend" \
      org.opencontainers.image.description="LuckyGas Delivery Management System - Web Frontend" \
      org.opencontainers.image.vendor="Lucky Gas"

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]