FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias de Python desde la raíz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del proyecto
COPY . .

# Situarse donde vive manage.py de Django
WORKDIR /app/config/django_restaurante

EXPOSE 8000

# Arrancar Django escuchando peticiones en el puerto 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
