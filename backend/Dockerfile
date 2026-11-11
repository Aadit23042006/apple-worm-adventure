
FROM python:3.12-slim

# Python production settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    WEB_CONCURRENCY=1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app

# Copy application files
COPY --chown=app:app . .

# Run as non-root user
USER app

# Render web service port
EXPOSE 8000

# Start Django with Gunicorn
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --timeout 120 --graceful-timeout 30 --access-logfile - --error-logfile -"]
