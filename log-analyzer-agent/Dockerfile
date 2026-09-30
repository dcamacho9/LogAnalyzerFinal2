ROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requeriments.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requeriments.txt

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --timeout 120 api_optimized:app"]
