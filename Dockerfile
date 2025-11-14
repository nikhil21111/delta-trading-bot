# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files
COPY *.py ./

# Create data directory for persistence
RUN mkdir -p /data

# Set environment variable for production mode
ENV PYTHONUNBUFFERED=1
ENV PRODUCTION=true

# Expose port for Render health checks
EXPOSE 8080

# Run the bot in LIVE mode
CMD ["python", "main.py", "LIVE"]
