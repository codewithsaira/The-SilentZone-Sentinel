# Multi-stage lightweight production image for The SilentZone Sentinel
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose ports: 8000 for backend API, 8501 for frontend UI
EXPOSE 8000 8501

# Run unified launcher
CMD ["python", "run_server.py"]
