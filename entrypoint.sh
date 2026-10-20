#!/bin/sh
set -e

echo "Esperando a PostgreSQL en ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-app}" -d "${POSTGRES_DB:-restaurant_database}" -q; do
  sleep 1
done
echo "PostgreSQL está listo."

if [ -d /opt/static-dist ]; then
  echo "Sincronizando archivos estáticos para NGINX..."
  cp -r /opt/static-dist/. /app/config/restaurante/app/static/ 2>/dev/null || true
fi

# Django es el único dueño de las migraciones en producción. Flask solo lee las tablas.
exec "$@"
