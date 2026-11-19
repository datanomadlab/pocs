"""Lado BigQuery, medido de verdad. Opcional: necesita una cuenta propia de GCP.

    uv sync --group bq
    gcloud auth application-default login
    GCP_PROYECTO=mi-proyecto make bq

Crea el dataset BQ_DATASET (por defecto lakehouse_de_bolsillo), carga los mismos Parquet de la
tabla Iceberg en una tabla particionada por mes y corre las 5 consultas sin caché.
Los timestamps de la tabla Iceberg no llevan zona horaria, así que en BigQuery son DATETIME.
`make destroy` borra el dataset solo si lo creó este experimento (lo reconoce por una etiqueta).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from . import config, consultas

TABLA_BQ = "viajes"
ETIQUETA = ("creado_por", "lakehouse-de-bolsillo")
TIPOS_BQ = {"int64": "INT64", "double": "FLOAT64", "string": "STRING", "timestamp[us]": "DATETIME"}


def _cliente():
    try:
        from google.cloud import bigquery
    except ImportError as e:
        raise RuntimeError("Falta google-cloud-bigquery. Corre: uv sync --group bq") from e
    proyecto = os.environ.get("GCP_PROYECTO")
    if not proyecto:
        raise RuntimeError("Define GCP_PROYECTO con el id de tu proyecto de GCP")
    return bigquery, bigquery.Client(project=proyecto)


def _dataset(cliente) -> str:
    return f"{cliente.project}.{os.environ.get('BQ_DATASET', 'lakehouse_de_bolsillo')}"


def cargar_y_medir(archivos: list[Path], lista: list[config.Consulta], primer_mes: str) -> dict:
    bigquery, cliente = _cliente()
    dataset = _preparar_dataset(bigquery, cliente)
    destino = f"{dataset}.{TABLA_BQ}"
    carga = bigquery.LoadJobConfig(
        schema=[bigquery.SchemaField(c.name, TIPOS_BQ[str(c.type)]) for c in config.ESQUEMA],
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.MONTH,
                                                    field="inicio"))
    for i, archivo in enumerate(archivos):
        if i > 0:
            carga.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
        with archivo.open("rb") as f:
            cliente.load_table_from_file(f, destino, job_config=carga).result()
        print(f"  cargado {archivo.name}")
    medidas = []
    sin_cache = bigquery.QueryJobConfig(use_query_cache=False)
    for consulta in lista:
        sql = consultas.sql_de(consulta, "bigquery", f"`{destino}`", primer_mes)
        t0 = time.perf_counter()
        trabajo = cliente.query(sql, job_config=sin_cache)
        trabajo.result()
        medidas.append({"nombre": consulta.nombre, "segundos": time.perf_counter() - t0,
                        "bytes_procesados": trabajo.total_bytes_processed,
                        "bytes_facturados": trabajo.total_bytes_billed})
    return {"tabla": destino, "consultas": medidas}


def _es_nuestro(dataset) -> bool:
    return dataset.labels.get(ETIQUETA[0]) == ETIQUETA[1]


def _preparar_dataset(bigquery, cliente) -> str:
    """Crea el dataset con una etiqueta propia. Si ya existía sin esa etiqueta, no lo toca."""
    from google.api_core.exceptions import NotFound
    nombre = _dataset(cliente)
    try:
        existente = cliente.get_dataset(nombre)
    except NotFound:
        nuevo = bigquery.Dataset(nombre)
        nuevo.labels = dict([ETIQUETA])
        cliente.create_dataset(nuevo)
        return nombre
    if not _es_nuestro(existente):
        raise RuntimeError(f"El dataset {nombre} ya existe y no lo creó este experimento. "
                           "Elige otro nombre con BQ_DATASET.")
    return nombre


def borrar() -> bool:
    """Borra el dataset solo si lleva la etiqueta de este experimento. Devuelve si borró algo."""
    from google.api_core.exceptions import NotFound
    _, cliente = _cliente()
    nombre = _dataset(cliente)
    try:
        existente = cliente.get_dataset(nombre)
    except NotFound:
        return False
    if not _es_nuestro(existente):
        raise RuntimeError(f"No borro {nombre}: no lo creó este experimento.")
    cliente.delete_dataset(nombre, delete_contents=True)
    return True
