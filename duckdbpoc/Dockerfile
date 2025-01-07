FROM debian:bullseye-slim

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    default-jre \
    libstdc++6 \
    libc6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Descargar Metabase
WORKDIR /app
RUN curl -L https://downloads.metabase.com/v0.51.10/metabase.jar -o metabase.jar

# Exponer el puerto 3000
EXPOSE 3000

# Agregar punto de entrada
CMD ["java", "-jar", "metabase.jar"]
