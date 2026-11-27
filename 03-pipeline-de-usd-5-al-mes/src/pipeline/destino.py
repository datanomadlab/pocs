"""Mira lo que cada camino dejó en el destino. Solo lee: es lo que usan las pruebas para comparar."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from . import config, vistas


def conexion(camino: str, bucket: Path = config.BUCKET) -> duckdb.DuckDBPyConnection:
    """DuckDB con una vista por tabla: lo vigente según dlt, o los CSV del script tal como quedaron."""
    con = vistas.conectar(memoria_mb=2048, temporal=str(config.DATOS / "tmp"))
    if camino == "dlt":
        vistas.crear(con, str(bucket / "dlt" / "crudo"))
        return con
    for tabla in config.TABLAS_ORIGEN:
        archivo = bucket / "script" / f"{tabla}.csv"
        # ignore_errors: un CSV cortado termina en una línea a medias, y se cuentan las que sí se leen.
        con.execute(f"CREATE OR REPLACE VIEW {tabla} AS "
                    f"SELECT * FROM read_csv('{archivo}', header = true, ignore_errors = true)")
    return con


def uno(con: duckdb.DuckDBPyConnection, sql: str, parametros: list | None = None):
    return con.execute(sql, parametros or []).fetchall()[0][0]


def filas(camino: str, bucket: Path = config.BUCKET) -> dict[str, int]:
    """Filas disponibles por tabla. Si el destino no existe o no se puede leer, cero."""
    cuentas = {}
    for tabla in config.TABLAS_ORIGEN:
        try:
            cuentas[tabla] = uno(conexion(camino, bucket), f"SELECT count(*) FROM {tabla}")
        except duckdb.Error:
            cuentas[tabla] = 0
    return cuentas


def filas_crudas(bucket: Path = config.BUCKET) -> dict[str, int]:
    """Todas las filas que dlt ha escrito, repetidas incluidas."""
    con = duckdb.connect()
    return {tabla: uno(con, f"SELECT count(*) FROM read_parquet('{bucket}/dlt/crudo/{tabla}/*.parquet', "
                            "union_by_name = true)") for tabla in config.TABLAS_ORIGEN}


def columnas(camino: str, tabla: str, bucket: Path = config.BUCKET) -> list[str]:
    return [f[0] for f in conexion(camino, bucket).execute(f"DESCRIBE {tabla}").fetchall()]


def existe(camino: str, tabla: str, valor, bucket: Path = config.BUCKET) -> bool:
    llave = config.LLAVES[tabla]
    return uno(conexion(camino, bucket), f"SELECT count(*) FROM {tabla} WHERE {llave} = ?", [valor]) > 0


def huella(camino: str, bucket: Path = config.BUCKET) -> dict[str, list[int]]:
    """Por tabla: filas, suma de las horas de actualización y suma de los montos en centavos. Si coincide con
    la del origen, están las mismas filas con sus fechas y montos. La calcula igual origen.huella en Postgres."""
    con = conexion(camino, bucket)
    return {t: list(con.execute(
        f"SELECT count(*), coalesce(sum(epoch(TRY_CAST(actualizado_en AS TIMESTAMP))), 0)::BIGINT, "
        f"coalesce(round(sum({origen_montos(t)}) * 100), 0)::BIGINT FROM {t}").fetchall()[0])
        for t in config.TABLAS_ORIGEN}


def origen_montos(tabla: str) -> str:
    """La misma expresión de montos que origen.MONTOS. Con decimales exactos, como en Postgres, para que la suma
    no difiera en un centavo por redondeo; la conversión hace falta porque los CSV llegan sin tipos fijos."""
    return {"productos": "TRY_CAST(precio AS DECIMAL(18, 4))",
            "lineas": "TRY_CAST(cantidad AS BIGINT) * TRY_CAST(precio_unitario AS DECIMAL(18, 4))"}.get(tabla, "0")


def filas_si_solo_cargas_registradas(bucket: Path = config.BUCKET) -> dict[str, int]:
    """Lo que vería una vista que solo lee las cargas que dlt anotó en _dlt_loads, la forma obvia de no
    mostrar cargas a medias. Sirve para contar qué esconde esa vista después de un corte."""
    con = duckdb.connect()
    crudo = bucket / "dlt" / "crudo"
    cuentas = {}
    for tabla, llave in config.LLAVES.items():
        cuentas[tabla] = uno(con, f"""
            WITH cargas AS (SELECT load_id FROM read_json('{crudo}/_dlt_loads/*.jsonl',
                                                          columns = {{load_id: 'VARCHAR', status: 'INTEGER'}})),
                 filas AS (SELECT {llave}, regexp_extract(filename, '([0-9]+\\.[0-9]+)\\.[0-9a-f]+\\.parquet$', 1) AS carga
                           FROM read_parquet('{crudo}/{tabla}/*.parquet', union_by_name = true, filename = true))
            SELECT count(DISTINCT {llave}) FROM filas WHERE carga IN (SELECT load_id FROM cargas)""")
    return cuentas


def corrida_publicada(bucket: Path = config.BUCKET) -> str | None:
    puntero = bucket / "dlt" / "reportes" / "actual.json"
    return json.loads(puntero.read_text(encoding="utf-8"))["corrida"] if puntero.exists() else None


def rastro(corrida: str, bucket: Path = config.BUCKET) -> dict | None:
    archivo = bucket / "dlt" / "corridas" / f"{corrida}.json"
    return json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else None


def archivos_dlt(carpeta: str, bucket: Path = config.BUCKET) -> list[Path]:
    """Archivos de una carpeta de dlt (_dlt_loads, _dlt_pipeline_state, _dlt_version), del más viejo al más nuevo."""
    return sorted((bucket / "dlt" / "crudo" / carpeta).glob("*.jsonl"), key=_id_de_carga)


def _id_de_carga(archivo: Path) -> float:
    """sql_database__1795743298.832166.jsonl o ventas__1795743298.832166__hash.jsonl -> 1795743298.832166"""
    return float(archivo.name.removesuffix(".jsonl").split("__")[1])


def peso(camino: str, bucket: Path = config.BUCKET) -> dict[str, int]:
    archivos = [a for a in (bucket / camino).rglob("*") if a.is_file()]
    return {"archivos": len(archivos), "bytes": sum(a.stat().st_size for a in archivos)}
