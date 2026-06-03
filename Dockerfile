# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend /app/backend
COPY data /app/data

# Expose port
EXPOSE 8000

# Run uvicorn server
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}

# NOTE: Using SQLite inside an ephemeral container is a trap.
# When the container restarts, all database changes are wiped.
# For real usage, either mount a docker volume to persist study_scheduler.db
# or swap the DATABASE_URL to a PostgreSQL instance.
