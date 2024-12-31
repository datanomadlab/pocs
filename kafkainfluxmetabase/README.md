# IoT POS POC

Este proyecto implementa una prueba de concepto (POC) que integra Kafka e InfluxDB para analizar datos IoT provenientes de puntos de venta (POS). El sistema permite procesar datos en tiempo real y almacenarlos para análisis temporal.

## **Estructura del Proyecto**

```
iot-pos-poc/
├── docker-compose.yml
├── src/
│   ├── producer/
│   │   ├── __init__.py
│   │   ├── kafka_producer.py
│   │   ├── config.py
│   └── consumer/
│       ├── __init__.py
│       ├── kafka_consumer.py
│       ├── influxdb_writer.py
│       ├── config.py
├── requirements.txt
└── README.md
```

### **Componentes Principales**
- **Kafka**: Broker de mensajería para recibir y distribuir eventos.
- **InfluxDB**: Base de datos para almacenar métricas temporales de los puntos de venta.

### **Módulos del Proyecto**
1. **Productor (Producer):**
   - Genera datos simulados de puntos de venta en formato JSON.
   - Envía los datos al tópico de Kafka.

2. **Consumidor (Consumer):**
   - Escucha los datos enviados al tópico de Kafka.
   - Procesa y almacena los datos en InfluxDB.

## **Instrucciones para Ejecutar el Proyecto**

### **1. Levantar los Servicios**
Levanta los servicios definidos en el archivo `docker-compose.yml`:
```bash
docker-compose up -d
```
Esto iniciará los contenedores para Kafka e InfluxDB.

### **2. Crear el Tópico en Kafka**
Asegúrate de crear el tópico `pos-events` en Kafka antes de enviar datos:
```bash
docker exec -it <kafka-container-name> kafka-topics --create \
  --topic pos-events \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
```

### **3. Configurar InfluxDB**
Crea una configuración predeterminada en InfluxDB CLI para evitar tener que especificar la organización y el token en cada consulta:
```bash
influx config create \
  --config-name default \
  --host-url http://localhost:8086 \
  --org <your-org-name> \
  --token <your-token>
```

### **4. Crear el Bucket en InfluxDB**
Crea un bucket llamado `pos_metrics` con un periodo de retención de 30 días:
```bash
influx bucket create --name pos_metrics --retention 30d --org <your-org-name> --token <your-token>
```

### **5. Instalar Dependencias**
Instala las dependencias necesarias en tu entorno local:
```bash
pip install -r requirements.txt
```

### **6. Ejecutar el Productor**
Inicia el productor para generar y enviar eventos al tópico:
```bash
python src/producer/kafka_producer.py
```

### **7. Ejecutar el Consumidor**
Inicia el consumidor para procesar los eventos y almacenarlos en InfluxDB:
```bash
python src/consumer/kafka_consumer.py
```

### **8. Validar los Datos en InfluxDB**
Accede a la CLI de InfluxDB y verifica los datos:
```bash
influx query 'from(bucket:"pos_metrics") |> range(start: -30m)'
```

## **Comandos Útiles**

### **Kafka**
- Listar tópicos:
  ```bash
  docker exec -it <kafka-container-name> kafka-topics --list --bootstrap-server localhost:9092
  ```

- Consumir mensajes desde el inicio:
  ```bash
  docker exec -it <kafka-container-name> kafka-console-consumer --bootstrap-server localhost:9092 --topic pos-events --from-beginning
  ```

- Verificar grupos de consumidores:
  ```bash
  docker exec -it <kafka-container-name> kafka-consumer-groups --bootstrap-server localhost:9092 --list
  ```

- Ver detalles de un grupo de consumidores:
  ```bash
  docker exec -it <kafka-container-name> kafka-consumer-groups --bootstrap-server localhost:9092 --group <consumer-group-id> --describe
  ```

### **InfluxDB**
- Listar buckets:
  ```bash
  influx bucket list
  ```

- Consultar datos:
  ```bash
  influx query 'from(bucket:"pos_metrics") |> range(start: -30m)'
  ```

- Crear un bucket:
  ```bash
  influx bucket create --name pos_metrics --retention 30d --org <your-org-name> --token <your-token>
  ```

### **General**
- Verificar logs de contenedores:
  ```bash
  docker logs -f <container-name>
  ```

- Reiniciar servicios:
  ```bash
  docker-compose restart
  ```

## **Notas**
- Asegúrate de que los tokens y configuraciones de InfluxDB sean correctos en el archivo `config.py`.
- Si hay problemas de conexión, verifica que los contenedores estén en la misma red de Docker.
- Elimina datos persistentes solo si estás seguro de que no necesitas conservarlos:
  ```bash
  docker volume rm <volume-name>
  ```

---
¡Ahora estás listo para explorar y analizar los datos de puntos de venta en tiempo real!

