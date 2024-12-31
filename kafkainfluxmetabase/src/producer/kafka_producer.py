from kafka import KafkaProducer
import json
import time
from datetime import datetime, timedelta
import random
from config import KAFKA_BROKER, TOPIC

# Configuración del productor
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


def generate_pos_event():
    store_id = random.choice(["001", "002", "003"])
    pos_id = random.choice(["A12", "B34", "C56"])
    # Generar timestamp aleatorio dentro de los últimos 30 días
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    random_timestamp = start_date + timedelta(
        seconds=random.randint(0, int((end_date - start_date).total_seconds()))
    )
    timestamp = random_timestamp.isoformat()

    # Generar ítems vendidos
    num_items = random.randint(1, 5)
    items_desc = [
        {
            "name": f"item_{i}",
            "amount": round(random.uniform(10, 100), 2),  # Precio por unidad
            "quantity": random.randint(1, 5),  # Cantidad de unidades
        }
        for i in range(num_items)
    ]

    # Calcular total_sales y items_sold basados en los ítems
    total_sales = sum(item["amount"] * item["quantity"] for item in items_desc)
    items_sold = sum(item["quantity"] for item in items_desc)

    # Número de transacciones (podemos mantenerlo independiente si aplica)
    transaction_count = random.randint(1, 3)

    return {
        "store_id": store_id,
        "pos_id": pos_id,
        "timestamp": timestamp,
        "total_sales": round(
            total_sales, 2
        ),  # Redondeamos para evitar errores de precisión
        "items_sold": items_sold,
        "transaction_count": transaction_count,
        "items_desc": items_desc,
    }


if __name__ == "__main__":
    print(f"Enviando datos al tópico {TOPIC}...")
    while True:
        event = generate_pos_event()
        producer.send(TOPIC, event)
        print(f"Evento enviado: {event}")
        time.sleep(2)
