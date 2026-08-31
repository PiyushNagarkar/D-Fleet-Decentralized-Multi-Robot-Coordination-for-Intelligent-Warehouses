# Backend Dockerfile for D-Fleet Simulation Environment & Telemetry Gateway
FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt pyproject.toml /app/

# Install python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and scenarios
COPY app /app/app
COPY database /app/database
COPY scenarios /app/scenarios
COPY backend /app/backend

# Create data directory for SQLite persistence
RUN mkdir -p /app/data

ENV PYTHONPATH=/app/app:/app
ENV DATABASE_URL=sqlite:////app/data/dfleet.db
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

# Run FastAPI simulation server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
