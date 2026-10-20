FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py

WORKDIR /app

# Instalar postgresql-client (comando pg_isready)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Caché de capas: instalar dependencias primero
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código completo del proyecto
COPY . .

# Guardar copia de estáticos para sincronizar con NGINX al arrancar
RUN mkdir -p /opt/static-dist && cp -r /app/config/restaurante/app/static/. /opt/static-dist/ 2>/dev/null || true

RUN chmod +x /app/entrypoint.sh

WORKDIR /app/config/restaurante

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]