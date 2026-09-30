# 1. Imagen base oficial de Python (ligera y optimizada)
FROM python:3.11-slim

# 2. Evita que Python escriba archivos .pyc en el disco y asegura que los logs salgan inmediatamente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Instala dependencias del sistema necesarias (si usas paquetes como gcc, curl, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Copia solo los archivos de dependencias primero para aprovechar la caché de capas de Docker
COPY requirements.txt .

# 6. Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copia el resto del código del proyecto al contenedor
COPY . .

# 8. Expón el puerto por defecto (Render asignará la variable $PORT automáticamente)
EXPOSE 5000

# 9. Comando de arranque usando Gunicorn (servidor de producción)
# Importante: Reemplaza "app:app" por "nombre_de_tu_archivo:variable_flask"
# Por ejemplo, si tu archivo se llama main.py y la app es app = Flask(__name__), usa: main:app
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120"]
