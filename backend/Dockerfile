# Production Dockerfile for LuckyGas Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cloud Run sets the PORT environment variable
EXPOSE 8080

# Run the application on the port specified by Cloud Run
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}