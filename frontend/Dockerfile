# Frontend Dockerfile - Optimized multi-stage build for production
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Install system dependencies needed for some npm packages
RUN apk add --no-cache python3 make g++ git

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies) needed for build
# We use npm ci to ensure reproducible builds
RUN npm ci --include=dev

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache python3 make g++

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy package files and source code
COPY package*.json ./
COPY . .

# Set build arguments and environment variables
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
ARG VITE_API_URL
ARG VITE_WS_URL 
ARG VITE_ENV=production
ARG VITE_GOOGLE_MAPS_API_KEY
ARG VITE_SENTRY_DSN

# Set environment variables for build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_ENV=${VITE_ENV}
ENV VITE_GOOGLE_MAPS_API_KEY=${VITE_GOOGLE_MAPS_API_KEY}
ENV VITE_SENTRY_DSN=${VITE_SENTRY_DSN}

# Build the application
# Set CI environment variable to skip validation in docker-build.sh
ENV CI=true
RUN npm run build:docker

# Stage 3: Production
FROM nginx:alpine AS production

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