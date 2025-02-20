# FlinkSessionPOC

Esta PoC demuestra cómo utilizar Scala y Apache Flink para procesar eventos de usuario en tiempo casi real usando session windows, y cómo almacenar los resultados en InfluxDB 2.7.

La infraestructura completa (Kafka, Zookeeper e InfluxDB) se levanta con Docker Compose para facilitar el despliegue local.

## Requisitos

- Docker y Docker Compose instalados.
- Java JDK (versión 8 o superior).
- Scala y SBT instalados.
- Conocimientos básicos sobre Kafka, Flink y manejo de contenedores Docker.

## Estructura del Proyecto

```
FlinkSessionPOC/
├── build.sbt                        # Configuración del proyecto y dependencias
├── project/                         # Configuración de SBT
├── docker-compose.yml               # Infraestructura: Zookeeper, Kafka e InfluxDB
├── README.md                        # Este archivo
└── src/
    ├── main/
    │   ├── resources/
    │   └── scala/
    │       └── com/
    │           └── yourcompany/
    │               └── flinksession/
    │                   ├── models/
    │                   ├── sink/
    │                   └── FlinkSessionWindowPOC.scala
    └── test/ (opcional)
```

## Levantando la Infraestructura con Docker Compose

El archivo `docker-compose.yml` levanta:
- **Zookeeper** (requerido para Kafka)
- **Kafka** (broker que recibe los eventos en el topic `session-topic`)
- **InfluxDB 2.7** (base de datos para series temporales)

### Pasos:

1. Guardar el archivo `docker-compose.yml` en la raíz del proyecto.
2. Ejecutar:
   ```bash
   docker-compose up -d
   ```
3. Verificar:
   ```bash
   docker-compose ps
   ```
   
   - Kafka estará disponible en `localhost:9092`.
   - InfluxDB en `http://localhost:8086`.

## Configuración y Ejecución del Proyecto Scala

1. **Configurar el proyecto Scala:**
   - Asegurarse de que `build.sbt` incluya dependencias para Flink, Kafka e InfluxDB.
2. **Compilar y ejecutar el job de Flink:**
   - Desde la raíz del proyecto, ejecutar:
     ```bash
     sbt run
     ```
   - Esto compila el proyecto y lanza el job en modo local.
   - El job:
     - Lee mensajes del topic `session-topic`.
     - Usa session windows (ventanas de inactividad de 30s).
     - Escribe los resultados en InfluxDB.

## Generar Datos de Prueba (Opcional)

Puedes usar un script externo o herramienta para enviar mensajes en formato CSV (`userId,timestamp,data`) a Kafka:

- Enviar datos a `session-topic`.
- Verificar que Flink los procese.
   ```python
   python3 generate_session_events.py
   ```

## Configuración Adicional

- **Kafka**:
  - Crear el topic si no existe:
    ```bash
    docker exec -it kafka kafka-topics --create --topic session-topic --bootstrap-server localhost:9092 --replication-factor 1 --partitions 3
    ```
- **InfluxDB**:
  - Usa las credenciales definidas en `docker-compose.yml` para el sink en Scala (usuario, contraseña, organización, bucket, token).

