# Sahay Backend - Production Dockerfile for Google Cloud Run

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (includes .env.production, firebase credentials, etc.)
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs

# Set environment variable for production
ENV ENVIRONMENT=production

# Cloud Run provides PORT environment variable (default 8080)
# We'll use ${PORT:-8080} to support both Cloud Run and local testing
ENV PORT=8080

# Health check (for local testing, Cloud Run has its own)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run with Uvicorn - use PORT env var and single worker for hackathon
# Single worker is fine for demo and reduces memory usage
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 300

