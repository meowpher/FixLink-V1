FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Python optimization and virtual env isolation
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for WebPush/Cryptography and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies. We use Gunicorn with Eventlet for Socket.IO support
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn eventlet

# Ensure the database instance and upload directories exist
RUN mkdir -p /app/instance
RUN mkdir -p /app/app/static/uploads

# Copy application files
COPY . /app/

# Expose port
EXPOSE 5000

# Set environment variable defaults
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Run migrations and start the server using gunicorn with eventlet worker
CMD ["sh", "-c", "flask db upgrade && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 run:app"]
