# Node 24 corre TypeScript directo (quita los tipos al cargar), así que no hay paso de compilación.
# Node 24 y no 26 (el LTS vigente): el cliente de Kafka de Confluent 1.11.0 no publica binario para
# Node 26 y la instalación falla al intentar compilarlo.
FROM node:24-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY src ./src
USER node
CMD ["node", "src/consumidor.ts"]
