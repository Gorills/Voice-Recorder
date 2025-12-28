#!/bin/bash
set -e

# Использовать переменные из окружения или значения по умолчанию
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

echo "Waiting for PostgreSQL..."
while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Creating media directories..."
mkdir -p /app/media/audio
chmod -R 777 /app/media || true

echo "Starting application..."
exec "$@"

