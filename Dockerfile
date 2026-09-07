FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del proyecto
COPY . .

# Directorio de trabajo en el módulo activo de restaurante
WORKDIR /app/config/restaurante

EXPOSE 5000

CMD ["python3", "main.py"]