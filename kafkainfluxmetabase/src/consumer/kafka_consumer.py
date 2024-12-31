from kafka import KafkaConsumer
import json
from influxdb_client import InfluxDBClient, Point
from config import (
    KAFKA_BROKER,
    TOPIC,
    INFLUXDB_URL,
    INFLUXDB_TOKEN,
    INFLUXDB_ORG,
    INFLUXDB_BUCKET,
)

# Configuración del consumidor Kafka
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    auto_offset_reset="earliest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
)

# Configuración del cliente de InfluxDB
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api()


def process_event(event):
    """
    Procesa un evento de Kafka y lo escribe en InfluxDB.
    """
    try:
        # Construir el punto para InfluxDB
        point = (
            Point("pos_data")
            .tag("store_id", event["store_id"])
            .tag("pos_id", event["pos_id"])
            .time(event["timestamp"])
            .field("total_sales", event["total_sales"])
            .field("items_sold", event["items_sold"])
            .field("transaction_count", event["transaction_count"])
        )

        # Escribir el punto en el bucket
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        print(f"Evento procesado y escrito en InfluxDB: {event}")
    except Exception as e:
        print(f"Error al procesar el evento: {e}")


# Escuchar los eventos
if __name__ == "__main__":
    print(f"Consumiendo mensajes del tópico {TOPIC} en {KAFKA_BROKER}...")
    for message in consumer:
        event = message.value
        process_event(event)
