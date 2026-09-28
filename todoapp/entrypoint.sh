#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-todo}" -d "${POSTGRES_DB:-todoapp}"; do
  sleep 1
done
echo "PostgreSQL is ready."

if [ -d /opt/static-dist ]; then
  echo "Syncing static files for nginx..."
  cp -r /opt/static-dist/. /app/app/static/
fi

if [ -f migrations/env.py ]; then
  echo "Applying database migrations..."
  flask db upgrade
fi

exec "$@"
