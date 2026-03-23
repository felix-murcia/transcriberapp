FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Madrid

WORKDIR /app

# Copiamos el código
COPY . .

# Limpiar pycache
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} +

# Instalamos dependencias Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Instalamos el paquete en modo editable
RUN pip install --no-cache-dir -e .

EXPOSE 9000
