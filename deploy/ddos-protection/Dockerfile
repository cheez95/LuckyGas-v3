# DDoS Protection Service for LuckyGas
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 ddos-monitor

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ddos_protection.py .
COPY config.yaml .

# Change ownership
RUN chown -R ddos-monitor:ddos-monitor /app

# Switch to non-root user
USER ddos-monitor

# Expose metrics port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Run the service
CMD ["python", "ddos_protection.py"]