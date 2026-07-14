FROM python:3.12-slim

WORKDIR /app

# system deps (curl for healthcheck, ca-certs for HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY . .

# non-root user + data volume
RUN useradd -u 1000 -m -s /usr/sbin/nologin forager \
    && mkdir -p /app/data \
    && chown -R forager:forager /app
USER forager
VOLUME ["/app/data"]

EXPOSE 5000

# 0.0.0.0 dentro il container è necessario per il port mapping; la porta
# è pubblicata SOLO su 127.0.0.1 dell'host (vedi docker-compose.yml).
ENV FORAGER_HOST=0.0.0.0 \
    FORAGER_PORT=5000 \
    FORAGER_DEBUG=0

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD test -f /app/data/crm.db && curl -fsS http://127.0.0.1:5000/ > /dev/null || exit 1

CMD ["python", "app.py"]
