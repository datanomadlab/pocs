#!/usr/bin/env python3
import time
import random
import threading
from uuid import uuid4
from kafka import KafkaProducer

# Lista de usuarios simulados
users = ['user1', 'user2', 'user3', 'user4', 'user5']

# Configurar el productor de Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: v.encode('utf-8')
)

def simulate_session(user, session_duration):
    """Simula una sesión de usuario con múltiples eventos durante un tiempo determinado"""
    session_id = str(uuid4())
    start_time = time.time()
    
    while (time.time() - start_time) < session_duration:
        timestamp = int(time.time() * 1000)
        data = f"event-{random.randint(1,100)}"
        event = f"{session_id},{user},{timestamp},{data}"
        producer.send('session-topic', event)
        print(f"Enviado: {event}")
        time.sleep(random.uniform(0.3, 1.5))  # Intervalos entre eventos en la misma sesión

def session_thread():
    """Hilo independiente para cada sesión de usuario"""
    user = random.choice(users)
    session_duration = random.randint(5, 120)  # Duración de sesión entre 5 y 120 segundos
    simulate_session(user, session_duration)

if __name__ == "__main__":
    print("Iniciando generación de sesiones...")
    active_threads = []
    
    while True:
        # Limpiar hilos completados
        active_threads = [t for t in active_threads if t.is_alive()]
        
        # Iniciar nueva sesión si hay capacidad
        if len(active_threads) < 10:  # Máximo 10 sesiones concurrentes
            t = threading.Thread(target=session_thread)
            t.start()
            active_threads.append(t)
        
        # Espera aleatoria entre inicios de nuevas sesiones (1-10 segundos)
        time.sleep(random.uniform(1, 10))
