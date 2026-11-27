"""El job del camino que se prueba: dlt carga lo nuevo, DuckDB revisa los datos y publica los reportes.

Lee tres variables: ORIGEN (la base Postgres), BUCKET (la carpeta o el bucket de destino) y CORRIDA
(el nombre de esta corrida, normalmente la fecha). No guarda nada fuera del destino.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import dlt
from dlt.sources.sql_database import sql_database

from . import vistas


def cargar(origen: str, destino: str) -> dict[str, int]:
    """De Postgres a Parquet, solo lo que cambió desde la última carga. Devuelve las filas por tabla."""
    # SQLAlchemy 2.1 entiende "postgresql://" como psycopg 3; dlt documenta psycopg2, así que se pide.
    fuente = sql_database(origen.replace("postgresql://", "postgresql+psycopg2://", 1),
                          table_names=list(vistas.LLAVES), backend="pyarrow", chunk_size=50_000)
    for tabla, llave in vistas.LLAVES.items():
        fuente.resources[tabla].apply_hints(primary_key=llave,
                                            incremental=dlt.sources.incremental("actualizado_en"))
    # El avance de la carga se guarda en el propio destino: el job parte cada vez sin disco.
    tuberia = dlt.pipeline("ventas", destination=dlt.destinations.filesystem(bucket_url=destino),
                           dataset_name="crudo", pipelines_dir="/tmp/dlt/pipelines")
    carga = tuberia.run(fuente, write_disposition="append", loader_file_format="parquet")
    carga.raise_on_failed_jobs()
    cuentas = tuberia.last_trace.last_normalize_info.row_counts
    return {tabla: cuentas.get(tabla, 0) for tabla in vistas.LLAVES}


def publicar(destino: str, corrida: str) -> dict[str, int]:
    """Corre las pruebas de datos; si pasan, escribe los reportes y recién entonces mueve el puntero.

    Devuelve las pruebas que fallaron con su número de filas. Si alguna falla no se publica nada y
    `reportes/actual.json` sigue apuntando a la última corrida buena.
    """
    con = vistas.conectar()
    vistas.crear(con, f"{destino}/crudo")
    fallas = {}
    for nombre, sql in vistas.consultas("pruebas").items():
        filas = con.execute(f"SELECT count(*) FROM ({sql})").fetchall()[0][0]
        if filas:
            fallas[nombre] = filas
    if fallas:
        return fallas
    carpeta = Path(destino) / "reportes" / corrida
    carpeta.mkdir(parents=True, exist_ok=True)
    reportes = vistas.consultas("reportes")
    for nombre, sql in reportes.items():
        con.execute(f"COPY ({sql}) TO '{carpeta / nombre}.parquet' (FORMAT parquet)")
    puntero = Path(destino) / "reportes" / "actual.json"
    parcial = puntero.with_suffix(".parcial")
    parcial.write_text(json.dumps({"corrida": corrida, "reportes": sorted(reportes)}), encoding="utf-8")
    parcial.replace(puntero)
    return {}


def _memoria_max_mb() -> float | None:
    pico = Path("/sys/fs/cgroup/memory.peak")
    return round(int(pico.read_text()) / 2**20, 1) if pico.exists() else None


def main() -> int:
    destino = os.environ["BUCKET"].rstrip("/") + "/dlt"
    corrida = os.environ["CORRIDA"]
    inicio = time.perf_counter()
    rastro: dict = {"corrida": corrida, "resultado": "error"}
    try:
        rastro["filas"] = cargar(os.environ["ORIGEN"], destino)
        rastro["segundos_carga"] = round(time.perf_counter() - inicio, 2)
        rastro["pruebas_fallidas"] = publicar(destino, corrida)
        rastro["segundos_publicar"] = round(time.perf_counter() - inicio - rastro["segundos_carga"], 2)
        rastro["resultado"] = "detenido" if rastro["pruebas_fallidas"] else "publicado"
    finally:
        rastro["segundos"] = round(time.perf_counter() - inicio, 2)
        rastro["memoria_max_mb"] = _memoria_max_mb()
        carpeta = Path(destino) / "corridas"
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / f"{corrida}.json").write_text(json.dumps(rastro), encoding="utf-8")
        print(json.dumps(rastro))
    return 0 if rastro["resultado"] == "publicado" else 1


if __name__ == "__main__":
    sys.exit(main())
