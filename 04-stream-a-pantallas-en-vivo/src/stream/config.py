"""Rutas del experimento y lo que el lector puede cambiar (ver .env.example)."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
MEDICION = DATOS / "medicion.json"
RESULTADOS = RAIZ / "docs" / "resultados.md"
TABLAS = RAIZ / "docs" / "tablas.toml"
RUTAS = RAIZ / "rutas.toml"
ESCENARIO = RAIZ / "escenario.toml"
ESCENARIO_LOCAL = RAIZ / "escenario.local.toml"
COSTOS_LOCALES = DATOS / "costos-locales.md"

ETIQUETAS = ("medido", "estimado", "simulado", "modelo")

# Cómo llega cada pieza a su transporte dentro de la red de Docker.
DESTINOS = {
    "redpanda": "redpanda:9092",
    "nats": "nats://nats:4222",
    "kinesis": "http://kinesis:4568",
    "sqs": "http://sqs:9324",
}
# Particiones del tópico de Redpanda y shards del stream de Kinesis.
PARTICIONES = {"redpanda": 12, "kinesis": 4}
# Por dónde se conecta la sonda a cada pieza de entrega: (servicio de compose, protocolo, URL).
ENTREGAS = {
    "go": ("consumidor-go", "propio", "ws://consumidor-go:8080/ws"),
    "node": ("consumidor-node", "propio", "ws://consumidor-node:8080/ws"),
    "centrifugo": ("centrifugo", "centrifugo", "ws://centrifugo:8000/connection/websocket"),
    "centrifugo-redis": ("centrifugo-redis", "centrifugo", "ws://centrifugo-redis:8000/connection/websocket"),
    "zilla": ("zilla", "sse", "http://zilla:7114/eventos"),
    "emqx": ("emqx", "mqtt", "ws://emqx:8083/mqtt"),
}
# Qué archivos tendría que escribir y mantener el equipo en cada pieza de entrega.
CODIGO = {
    "go": ["servicios/go/cmd/consumidor/main.go", "servicios/go/cmd/consumidor/central.go",
           "servicios/go/cmd/consumidor/lector_{transporte}.go"],
    "node": ["servicios/node/src/consumidor.ts", "servicios/node/src/central.ts",
             "servicios/node/src/lector_{transporte}.ts"],
    "centrifugo": [],
    "centrifugo-redis": [],
    "zilla": [],
    "emqx": [],
}
CONFIGURACION = {"centrifugo": ["servicios/centrifugo/{transporte}.json"],
                 "centrifugo-redis": ["servicios/centrifugo/{transporte}-redis.json"],
                 "zilla": ["servicios/zilla/zilla.yaml"], "emqx": ["servicios/emqx/base.hocon"]}


@dataclass(frozen=True)
class Ruta:
    id: str
    corto: str            # nombre para el resumen de la terminal, de 24 caracteres como máximo
    transporte: str
    entrega: str
    nombre: str
    etiqueta: str
    sesion_ms: str = ""   # tiempo de sesión del grupo de Kafka para esta ruta; vacío = el de fábrica
    tasa: int = 0         # eventos por segundo solo para esta ruta; 0 = la tasa general
    sin_comprimir: bool = False   # el productor de Kafka escribe sin comprimir (de fábrica usa snappy)

    @property
    def simulada(self) -> bool:
        return self.etiqueta == "simulado"


@dataclass(frozen=True)
class Parametros:
    tasa: int
    tasa_simulada: int
    emisores: int
    cuentas: int
    pantallas: int
    bytes: int
    p99_max_ms: int
    cortes: int
    sesion_ms: str
    rapido: bool
    # Pantallas que miran cada cuenta. Con 1, cada evento llega a una sola pantalla.
    espectadores: int = 1

    @property
    def segundos_nominal(self) -> int:
        return 10 if self.rapido else 30

    @property
    def segundos_corte(self) -> int:
        """La carga sigue este tiempo; el corte ocurre a los CORTE_A_LOS segundos."""
        return 25 if self.rapido else 75

    @property
    def segundos_escalon(self) -> int:
        return 6 if self.rapido else 12


LARGO_CORTO = 23            # ancho de la columna de rutas en el resumen de la terminal
CORTE_A_LOS = 10            # segundos de carga antes de matar la pieza de entrega
MARGEN_SONDA = 8            # segundos que la sonda sigue escuchando después de la carga
MARGEN_CORTE = 20           # lo mismo en la prueba de corte, para alcanzar a ver lo que llega tarde
FACTORES_RAMPA = (2, 4, 8)  # la rampa prueba 2, 4 y 8 veces la tasa nominal


def _entero(nombre: str, defecto: int) -> int:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        return defecto
    if not valor.isdigit() or int(valor) <= 0:
        raise ValueError(f"{nombre} debe ser un entero positivo, no '{valor}'")
    return int(valor)


def parametros() -> Parametros:
    return Parametros(
        tasa=_entero("TASA", 10_000), tasa_simulada=_entero("TASA_SIMULADA", 1_000),
        emisores=_entero("EMISORES", 100_000), cuentas=_entero("CUENTAS", 1_000),
        pantallas=_entero("PANTALLAS", 100), bytes=_entero("BYTES", 300),
        p99_max_ms=_entero("P99_MAX_MS", 1_000), cortes=_entero("CORTES", 2),
        sesion_ms=os.environ.get("SESION_MS", "").strip(),
        rapido=os.environ.get("RAPIDO", "").strip() == "1",
        espectadores=_entero("ESPECTADORES", 1))


def rutas(todas: bool = False) -> list[Ruta]:
    """Las rutas de rutas.toml, filtradas por RUTAS si viene (salvo que se pidan todas)."""
    lista = [Ruta(**r) for r in tomllib.loads(RUTAS.read_text(encoding="utf-8"))["ruta"]]
    for r in lista:
        if r.transporte not in DESTINOS or r.entrega not in ENTREGAS or r.etiqueta not in ETIQUETAS:
            raise ValueError(f"rutas.toml: la ruta '{r.id}' tiene un transporte, entrega o etiqueta desconocidos")
        if len(r.corto) > LARGO_CORTO:
            raise ValueError(f"rutas.toml: el nombre corto de '{r.id}' pasa de {LARGO_CORTO} caracteres")
    pedidas = [x.strip() for x in os.environ.get("RUTAS", "").split(",") if x.strip()]
    if todas or not pedidas:
        return lista
    desconocidas = set(pedidas) - {r.id for r in lista}
    if desconocidas:
        raise ValueError(f"RUTAS nombra rutas que no están en rutas.toml: {', '.join(sorted(desconocidas))}")
    return [r for r in lista if r.id in pedidas]
