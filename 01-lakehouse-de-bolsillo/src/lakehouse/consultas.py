"""Corre las consultas en DuckDB sobre la tabla Iceberg y estima lo que cobraría BigQuery."""
from __future__ import annotations

import statistics
import time
from pathlib import Path

import duckdb

from . import config, costos
from .tabla import rango_mes

VISTA = "viajes"


def conectar(metadata: str, hilos: int, memoria_gib: int) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL iceberg")
    con.execute("LOAD iceberg")
    con.execute(f"SET threads = {int(hilos)}")
    con.execute(f"SET memory_limit = '{int(memoria_gib)}GB'")
    con.execute(f"CREATE VIEW {VISTA} AS SELECT * FROM iceberg_scan('{metadata}')")
    return con


def sql_de(consulta: config.Consulta, motor: str, tabla: str, primer_mes: str,
           carpeta: Path = config.SQL) -> str:
    inicio, fin = rango_mes(primer_mes)
    plantilla = (carpeta / motor / f"{consulta.nombre}.sql").read_text(encoding="utf-8")
    return plantilla.format(tabla=tabla, mes_inicio=f"{inicio:%Y-%m-%d}", mes_fin=f"{fin:%Y-%m-%d}")


def medir(con: duckdb.DuckDBPyConnection, consultas: list[config.Consulta], primer_mes: str,
          repeticiones: int = 5) -> list[dict]:
    """Primera corrida ("en frío") y mediana de las siguientes, en segundos."""
    resultados = []
    for consulta in consultas:
        sql = sql_de(consulta, "duckdb", VISTA, primer_mes)
        tiempos = []
        filas = 0
        for _ in range(repeticiones + 1):
            t0 = time.perf_counter()
            filas = len(con.execute(sql).fetchall())
            tiempos.append(time.perf_counter() - t0)
        resultados.append({"nombre": consulta.nombre, "descripcion": consulta.descripcion,
                           "filas_resultado": filas, "frio_s": tiempos[0],
                           "mediana_s": statistics.median(tiempos[1:])})
    return resultados


def perfil_bytes(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, int]]:
    """Bytes lógicos de BigQuery por mes y por columna, calculados sobre los datos reales."""
    partes = []
    for campo in config.ESQUEMA:
        partes.append(f"count({campo.name}) AS n_{campo.name}")
        if str(campo.type) == "string":
            partes.append(f"coalesce(sum(strlen({campo.name})), 0) AS b_{campo.name}")
    cursor = con.execute(f"SELECT strftime(inicio, '%Y-%m') AS mes, {', '.join(partes)} "
                         f"FROM {VISTA} GROUP BY 1 ORDER BY 1")
    nombres = [d[0] for d in cursor.description]
    perfil = {}
    for fila in cursor.fetchall():
        valores = dict(zip(nombres, fila))
        perfil[valores["mes"]] = {
            campo.name: costos.bytes_logicos(str(campo.type), valores[f"n_{campo.name}"],
                                             valores.get(f"b_{campo.name}", 0))
            for campo in config.ESQUEMA}
    return perfil


def bytes_escaneados(consulta: config.Consulta, perfil: dict[str, dict[str, int]],
                     primer_mes: str) -> int:
    """Bytes que BigQuery leería: columnas referenciadas, en las particiones que no puede podar."""
    meses = [primer_mes] if consulta.solo_primer_mes else list(perfil)
    return sum(perfil[mes][col] for mes in meses for col in consulta.columnas)


def filas_totales(con: duckdb.DuckDBPyConnection) -> int:
    return con.execute(f"SELECT count(*) FROM {VISTA}").fetchone()[0]
