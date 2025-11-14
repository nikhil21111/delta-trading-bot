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

# Copy all Python files and web dashboard
COPY *.py ./
COPY web_dashboard ./web_dashboard

# Create data directory for persistence
RUN mkdir -p /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PRODUCTION=true

# Expose port 8080 for web dashboard
EXPOSE 8080

# Run both bot and web server
CMD ["python", "start_all.py", "LIVE"]
