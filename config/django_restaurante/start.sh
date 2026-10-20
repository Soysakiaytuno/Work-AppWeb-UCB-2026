#!/bin/sh
set -e

echo "Aplicando migraciones de Django..."
python manage.py migrate --noinput

echo "Inicializando superusuario por defecto..."
python manage.py initadmin

echo "Iniciando servidor Django Admin en 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000
