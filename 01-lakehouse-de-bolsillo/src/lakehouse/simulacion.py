"""BigQuery simulado: comprueba el SQL de BigQuery sin una cuenta de GCP.

Lee cada sql/bigquery/*.sql con el analizador de dialecto BigQuery de sqlglot, lo traduce a DuckDB
y lo corre sobre la misma tabla Iceberg. Responde tres preguntas:

1. ¿El SQL de BigQuery se puede leer como BigQuery? (si no, `make bq` fallaría)
2. ¿Da el mismo resultado que la versión DuckDB de la consulta?
3. ¿Qué columnas lee y si filtra por la columna de partición? De ahí salen los bytes que
   BigQuery facturaría, sin depender de la lista escrita a mano en consultas.toml.

No mide tiempos ni bytes facturados de BigQuery: eso solo lo da `make bq` con una cuenta real.
"""
from __future__ import annotations

import math

import duckdb
import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from . import config, consultas

COLUMNA_PARTICION = "inicio"
TOLERANCIA = 0.01   # APPROX_QUANTILES de BigQuery es aproximado; DuckDB calcula percentiles exactos


def _arbol(sql_bq: str) -> exp.Expression:
    try:
        return sqlglot.parse_one(sql_bq, read="bigquery")
    except ParseError as e:
        raise ValueError(f"no es SQL válido de BigQuery: {e}") from e


def traducir(sql_bq: str) -> str:
    """SQL de BigQuery -> SQL de DuckDB.

    sqlglot traduce EXTRACT(DAYOFWEEK) tal cual, pero BigQuery numera el domingo como 1 y DuckDB
    como 0: aquí se suma 1 para conservar el significado de BigQuery.
    """
    def dia_semana(nodo: exp.Expression) -> exp.Expression:
        if isinstance(nodo, exp.Extract) and nodo.name.upper() == "DAYOFWEEK":
            return exp.paren(exp.Add(this=nodo.copy(), expression=exp.Literal.number(1)))
        return nodo

    arbol = _arbol(sql_bq)
    arbol = arbol.transform(dia_semana, copy=True) if arbol.find(exp.Extract) else arbol
    return arbol.sql(dialect="duckdb")


def columnas_de(sql_bq: str) -> set[str]:
    """Columnas de la tabla que la consulta lee (BigQuery cobra cada una completa)."""
    arbol = _arbol(sql_bq)
    alias = {a.alias for a in arbol.find_all(exp.Alias)}
    return {c.name for c in arbol.find_all(exp.Column) if c.name not in alias or c.table}


def poda_particiones(sql_bq: str, columna: str = COLUMNA_PARTICION) -> bool:
    """True si el WHERE compara la columna de partición, así BigQuery puede saltarse meses."""
    donde = _arbol(sql_bq).find(exp.Where)
    if donde is None:
        return False
    comparaciones = (exp.GT, exp.GTE, exp.LT, exp.LTE, exp.EQ, exp.Between)
    return any(c.name == columna for comp in donde.find_all(*comparaciones) for c in comp.find_all(exp.Column))


def comparar(a: list[tuple], b: list[tuple], tolerancia: float = 0.0) -> tuple[bool, float | None]:
    """Compara dos resultados fila a fila. Devuelve si son iguales y la mayor diferencia relativa."""
    if len(a) != len(b):
        return False, None
    peor = 0.0
    for fila_a, fila_b in zip(a, b):
        if len(fila_a) != len(fila_b):
            return False, None
        for x, y in zip(fila_a, fila_b):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                base = max(abs(x), abs(y))
                peor = max(peor, abs(x - y) / base if base else 0.0)
            elif x != y:
                return False, None
    return (math.isclose(peor, 0.0) or peor <= tolerancia), peor


def simular(con: duckdb.DuckDBPyConnection, lista: list[config.Consulta], primer_mes: str,
            perfil: dict[str, dict[str, int]]) -> list[dict]:
    resultado = []
    for consulta in lista:
        sql_bq = consultas.sql_de(consulta, "bigquery", consultas.VISTA, primer_mes)
        columnas = columnas_de(sql_bq)
        poda = poda_particiones(sql_bq)
        filas_bq = con.execute(traducir(sql_bq)).fetchall()
        filas_duck = con.execute(consultas.sql_de(consulta, "duckdb", consultas.VISTA, primer_mes)).fetchall()
        iguales, diferencia = comparar(filas_bq, filas_duck, TOLERANCIA)
        meses = [primer_mes] if poda else list(perfil)
        resultado.append({
            "nombre": consulta.nombre,
            "columnas_sql": sorted(columnas),
            "columnas_coinciden": columnas == set(consulta.columnas),
            "poda_particiones": poda,
            "poda_coincide": poda == consulta.solo_primer_mes,
            "bytes_simulados": sum(perfil[m][c] for m in meses for c in columnas if c in perfil[m]),
            "filas": len(filas_bq),
            "mismo_resultado": iguales,
            "diferencia_max": diferencia,
        })
    return resultado
