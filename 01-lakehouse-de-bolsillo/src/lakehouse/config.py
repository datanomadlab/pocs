"""Rutas, meses y esquema del experimento. Todo lo configurable vive aquí o en escenario.toml."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
CRUDOS = DATOS / "crudos"
BODEGA = DATOS / "bodega"
CATALOGO = DATOS / "catalogo.db"
MEDICION_LOCAL = DATOS / "medicion_local.json"
MEDICION_BQ = DATOS / "medicion_bigquery.json"
RESULTADOS = RAIZ / "docs" / "resultados.md"
ESCENARIO = RAIZ / "escenario.toml"
CONSULTAS = RAIZ / "consultas.toml"
SQL = RAIZ / "sql"

URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
MESES_POR_DEFECTO = "2024-01,2024-02,2024-03"
TABLA = "taxi.viajes"

# nombre en el Parquet de origen -> (nombre en la tabla, tipo)
COLUMNAS: dict[str, tuple[str, pa.DataType]] = {
    "VendorID": ("vendor_id", pa.int64()),
    "tpep_pickup_datetime": ("inicio", pa.timestamp("us")),
    "tpep_dropoff_datetime": ("fin", pa.timestamp("us")),
    "passenger_count": ("pasajeros", pa.int64()),
    "trip_distance": ("distancia_millas", pa.float64()),
    "RatecodeID": ("tarifa_id", pa.int64()),
    "store_and_fwd_flag": ("guardado_y_reenviado", pa.string()),
    "PULocationID": ("zona_origen", pa.int64()),
    "DOLocationID": ("zona_destino", pa.int64()),
    "payment_type": ("tipo_pago", pa.int64()),
    "fare_amount": ("tarifa", pa.float64()),
    "extra": ("extra", pa.float64()),
    "mta_tax": ("impuesto_mta", pa.float64()),
    "tip_amount": ("propina", pa.float64()),
    "tolls_amount": ("peajes", pa.float64()),
    "improvement_surcharge": ("recargo_mejora", pa.float64()),
    "total_amount": ("total", pa.float64()),
    "congestion_surcharge": ("recargo_congestion", pa.float64()),
    "Airport_fee": ("tasa_aeropuerto", pa.float64()),
}

ESQUEMA = pa.schema([pa.field(nombre, tipo) for nombre, tipo in COLUMNAS.values()])


@dataclass(frozen=True)
class Consulta:
    nombre: str
    descripcion: str
    columnas: tuple[str, ...]
    solo_primer_mes: bool = False


def meses() -> list[str]:
    """Meses a cargar, en formato AAAA-MM. Se cambia con la variable MESES."""
    valor = os.environ.get("MESES", MESES_POR_DEFECTO)
    lista = [m.strip() for m in valor.split(",") if m.strip()]
    for mes in lista:
        anio, _, numero = mes.partition("-")
        if not (len(anio) == 4 and anio.isdigit() and numero.isdigit() and 1 <= int(numero) <= 12):
            raise ValueError(f"Mes inválido en MESES: {mes!r}. Formato esperado: AAAA-MM")
    if not lista:
        raise ValueError("MESES está vacío")
    return lista


def cargar_consultas(ruta: Path = CONSULTAS) -> list[Consulta]:
    validas = {nombre for nombre, _ in COLUMNAS.values()}
    with ruta.open("rb") as f:
        crudo = tomllib.load(f)
    consultas = []
    for c in crudo["consulta"]:
        desconocidas = set(c["columnas"]) - validas
        if desconocidas:
            raise ValueError(f"Consulta {c['nombre']}: columnas desconocidas {sorted(desconocidas)}")
        consultas.append(Consulta(c["nombre"], c["descripcion"], tuple(c["columnas"]),
                                  c.get("solo_primer_mes", False)))
    return consultas


def cargar_escenario(ruta: Path = ESCENARIO) -> dict:
    with ruta.open("rb") as f:
        return tomllib.load(f)
