# Dockerfile for Race Fuel & Pacing Planner
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Copy known races to a static location (not affected by volume mounts)
COPY data/known_races/ /app/static_data/known_races/

# Create default data directories (can be overridden by env)
RUN mkdir -p /app/data/uploads /app/data/saved_plans

# Expose port
EXPOSE 5000

# Run the application with Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} app:app"]
