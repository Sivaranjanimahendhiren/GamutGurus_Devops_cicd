# Use lightweight official Python image
FROM python:3.9-slim

# Environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better cache usage)
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose Flask app port
EXPOSE 5000

# Run app with Gunicorn (2 workers, can increase for production)
CMD ["gunicorn", "--workers=2", "--threads=2", "--timeout=120", "-b", "0.0.0.0:5000", "app:app"]
