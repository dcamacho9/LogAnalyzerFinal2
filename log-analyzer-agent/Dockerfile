# ==============================================
# Dockerfile para Log Analyzer Agent + API
# Optimizado para Producción
# ==============================================

FROM docker.m.daocloud.io/library/python:3.11-slim as builder

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
COPY requeriments.txt .

# Compilar wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/wheels -r requeriments.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pandas

COPY . .

# ==============================================
# Stage 2: Runtime
# ==============================================

FROM docker.m.daocloud.io/library/python:3.11-slim

LABEL maintainer="DevOps Team"
LABEL description="Log Analyzer Agent + API with OLLAMA Integration"
LABEL version="2.0"

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=api.py \
    FLASK_ENV=production \
    PORT=5000

# Instalar solo dependencias de runtime necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar wheels desde builder
COPY --from=builder /tmp/wheels /tmp/wheels
COPY requeriments.txt .

# Instalar dependencias Python desde wheels
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache /tmp/wheels/* && \
    rm -rf /tmp/wheels

# Copiar código de la aplicación
COPY . .

# Crear usuario no-root (seguridad)
RUN groupadd -r agentuser && \
    useradd -r -g agentuser -u 1000 agentuser && \
    chown -R agentuser:agentuser /app

USER agentuser

# Exponer puerto (Render asignará dinámicamente)
EXPOSE 5000

# Usar tini para manejar señales correctamente
ENTRYPOINT ["/usr/bin/tini", "--"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Comando por defecto: ejecutar API con modo unbuffered
CMD ["python", "-u", "api.py"]
