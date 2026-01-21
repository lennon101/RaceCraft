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

# Create directories for uploads and saved plans
RUN mkdir -p static/uploads saved_plans

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
