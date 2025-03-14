FROM pgvector/pgvector:pg15

# Instalar PostGIS
RUN apt-get update \
    && apt-get install -y postgresql-15-postgis-3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* 