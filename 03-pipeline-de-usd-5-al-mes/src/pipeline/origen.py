"""El sistema de ventas: cuatro tablas en Postgres que reciben las ventas del dataset día a día.

Cada fila lleva `actualizado_en` con la hora del evento en el dataset (2009 a 2011), no la del reloj:
así la simulación se puede repetir y da lo mismo.
"""
from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path

import duckdb
import psycopg2

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
  id_cliente integer PRIMARY KEY, pais text NOT NULL, actualizado_en timestamp NOT NULL);
CREATE TABLE IF NOT EXISTS productos (
  codigo text PRIMARY KEY, descripcion text, precio numeric(12,4) NOT NULL, actualizado_en timestamp NOT NULL);
CREATE TABLE IF NOT EXISTS facturas (
  id_factura text PRIMARY KEY, id_cliente integer, fecha timestamp NOT NULL, anulada boolean NOT NULL,
  actualizado_en timestamp NOT NULL);
CREATE TABLE IF NOT EXISTS lineas (
  id_linea bigint PRIMARY KEY, id_factura text NOT NULL, codigo text NOT NULL, cantidad integer NOT NULL,
  precio_unitario numeric(12,4) NOT NULL, actualizado_en timestamp NOT NULL);
CREATE INDEX IF NOT EXISTS clientes_act ON clientes (actualizado_en);
CREATE INDEX IF NOT EXISTS productos_act ON productos (actualizado_en);
CREATE INDEX IF NOT EXISTS facturas_act ON facturas (actualizado_en);
CREATE INDEX IF NOT EXISTS lineas_act ON lineas (actualizado_en);
"""

# Lo que un período de ventas le hace a cada tabla. {ventas} es el Parquet y el período va en $1 y $2.
PERIODO = "fecha >= CAST($1 AS TIMESTAMP) AND fecha < CAST($2 AS TIMESTAMP) + INTERVAL 1 DAY"
EXTRACTOS = {
    "clientes": f"""
        SELECT id_cliente, arg_max(pais, fecha) AS pais, max(fecha) AS actualizado_en
        FROM read_parquet('{{ventas}}') WHERE {PERIODO} AND id_cliente IS NOT NULL GROUP BY id_cliente""",
    # El precio de lista de un producto es el más repetido de su último día con ventas en el período.
    "productos": f"""
        WITH v AS (SELECT * FROM read_parquet('{{ventas}}') WHERE {PERIODO}),
             ultimo AS (SELECT codigo, max(CAST(fecha AS DATE)) AS dia FROM v GROUP BY codigo)
        SELECT v.codigo, arg_max(v.descripcion, v.fecha) AS descripcion, mode(v.precio_unitario) AS precio,
               max(v.fecha) AS actualizado_en
        FROM v JOIN ultimo u ON v.codigo = u.codigo AND CAST(v.fecha AS DATE) = u.dia GROUP BY v.codigo""",
    "facturas": f"""
        SELECT id_factura, any_value(id_cliente) AS id_cliente, min(fecha) AS fecha,
               id_factura LIKE 'C%' AS anulada, min(fecha) AS actualizado_en
        FROM read_parquet('{{ventas}}') WHERE {PERIODO} GROUP BY id_factura""",
    "lineas": f"""
        SELECT id_linea, id_factura, codigo, cantidad, precio_unitario, fecha AS actualizado_en
        FROM read_parquet('{{ventas}}') WHERE {PERIODO}""",
}
COLUMNAS = {
    "clientes": ("id_cliente", "pais", "actualizado_en"),
    "productos": ("codigo", "descripcion", "precio", "actualizado_en"),
    "facturas": ("id_factura", "id_cliente", "fecha", "anulada", "actualizado_en"),
    "lineas": ("id_linea", "id_factura", "codigo", "cantidad", "precio_unitario", "actualizado_en"),
}
# Qué columnas, al cambiar, hacen que una fila existente se actualice. Facturas y líneas solo se insertan.
CAMBIAN = {"clientes": ("pais",), "productos": ("descripcion", "precio")}


def conectar(dsn: str = config.DSN_LOCAL):
    try:
        return psycopg2.connect(dsn)
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"No pude conectar a Postgres: {str(e).strip().splitlines()[0]}") from e


def crear_esquema(con) -> None:
    with con, con.cursor() as cur:
        cur.execute(ESQUEMA)


def _sql_carga(tabla: str) -> str:
    llave, cols = config.LLAVES[tabla], COLUMNAS[tabla]
    lista = ", ".join(cols)
    if tabla not in CAMBIAN:
        return f"INSERT INTO {tabla} ({lista}) SELECT {lista} FROM _nuevo ON CONFLICT ({llave}) DO NOTHING"
    cambian = CAMBIAN[tabla]
    asigna = ", ".join(f"{c} = EXCLUDED.{c}" for c in (*cambian, "actualizado_en"))
    distinto = " OR ".join(f"{tabla}.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in cambian)
    return (f"INSERT INTO {tabla} ({lista}) SELECT {lista} FROM _nuevo "
            f"ON CONFLICT ({llave}) DO UPDATE SET {asigna} WHERE {distinto}")


def aplicar(con, desde: dt.date, hasta: dt.date, ventas: Path = config.VENTAS) -> dict[str, int]:
    """Lleva al origen las ventas entre dos fechas (inclusive). Devuelve las filas nuevas o cambiadas por tabla."""
    duck = duckdb.connect()
    tocadas: dict[str, int] = {}
    with tempfile.TemporaryDirectory() as tmp, con, con.cursor() as cur:
        for tabla, consulta in EXTRACTOS.items():
            csv = Path(tmp) / f"{tabla}.csv"
            duck.execute(f"COPY ({consulta.format(ventas=ventas)}) TO '{csv}' (FORMAT csv, HEADER)",
                         [desde.isoformat(), hasta.isoformat()])
            lista = ", ".join(COLUMNAS[tabla])
            cur.execute(f"CREATE TEMP TABLE _nuevo ON COMMIT DROP AS SELECT {lista} FROM {tabla} LIMIT 0")
            with csv.open(encoding="utf-8") as f:
                cur.copy_expert(f"COPY _nuevo ({lista}) FROM STDIN WITH (FORMAT csv, HEADER)", f)
            cur.execute(_sql_carga(tabla))
            tocadas[tabla] = cur.rowcount
            cur.execute("DROP TABLE _nuevo")
    return tocadas


def contar(con) -> dict[str, int]:
    with con, con.cursor() as cur:
        filas = {}
        for tabla in config.TABLAS_ORIGEN:
            cur.execute(f"SELECT count(*) FROM {tabla}")
            filas[tabla] = cur.fetchone()[0]
        return filas


# Lo que suma la huella además de filas y fechas, para ver también los montos.
MONTOS = {"productos": "precio", "lineas": "cantidad * precio_unitario"}


def huella(con) -> dict[str, list[int]]:
    """Por tabla: filas, suma de las horas de actualización y suma de los montos, en centavos.
    Se compara con destino.huella."""
    with con, con.cursor() as cur:
        out = {}
        for tabla in config.TABLAS_ORIGEN:
            cur.execute(f"SELECT count(*), coalesce(sum(extract(epoch FROM actualizado_en)), 0)::bigint, "
                        f"coalesce(round(sum({MONTOS.get(tabla, '0')}) * 100), 0)::bigint FROM {tabla}")
            out[tabla] = [int(x) for x in cur.fetchone()]
        return out


def volumen_desde(con, desde: dt.date) -> dict[str, int]:
    """Lo que cambió desde una fecha: filas distintas (lo que cobra por fila una herramienta administrada),
    sus bytes en Postgres y el tamaño total de las tablas."""
    with con, con.cursor() as cur:
        filas = bytes_tocados = bytes_tablas = 0
        for tabla in config.TABLAS_ORIGEN:
            cur.execute(f"SELECT count(*), coalesce(sum(pg_column_size(t.*)), 0) FROM {tabla} t "
                        "WHERE actualizado_en >= %s", (desde,))
            n, b = cur.fetchone()
            cur.execute("SELECT pg_table_size(%s)", (tabla,))
            filas, bytes_tocados, bytes_tablas = filas + n, bytes_tocados + int(b), bytes_tablas + cur.fetchone()[0]
        return {"filas": filas, "bytes_tocados": bytes_tocados, "bytes_tablas": bytes_tablas}


def version(con) -> str:
    with con, con.cursor() as cur:
        cur.execute("SHOW server_version")
        return cur.fetchone()[0].split()[0]


def dias_con_ventas(desde: dt.date, cuantos: int, ventas: Path = config.VENTAS) -> list[dt.date]:
    filas = duckdb.connect().execute(
        f"SELECT DISTINCT CAST(fecha AS DATE) d FROM read_parquet('{ventas}') WHERE fecha >= CAST(? AS TIMESTAMP) "
        "ORDER BY d LIMIT ?", [desde.isoformat(), cuantos]).fetchall()
    return [f[0] for f in filas]


# --- Lo que le pasa al origen en las pruebas -------------------------------------------------------

def agregar_columna(con) -> int:
    """Prueba 4: el sistema de ventas estrena una columna con valor por defecto, como se agrega en la vida real.
    Postgres la llena en todas las filas sin tocar su fecha de actualización. Devuelve cuántas quedaron llenas."""
    with con, con.cursor() as cur:
        cur.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS segmento text DEFAULT 'tienda'")
        cur.execute("SELECT count(segmento) FROM clientes")
        return cur.fetchone()[0]


def meter_dato_malo(con, dia: dt.date) -> int:
    """Prueba 5: una línea de una venta normal del día queda con precio negativo. Devuelve su id."""
    with con, con.cursor() as cur:
        cur.execute("""UPDATE lineas SET precio_unitario = -precio_unitario
                       WHERE id_linea = (SELECT l.id_linea FROM lineas l JOIN facturas f USING (id_factura)
                                         WHERE l.actualizado_en >= %s AND NOT f.anulada AND l.precio_unitario > 0
                                         ORDER BY l.id_linea LIMIT 1) RETURNING id_linea""", (dia,))
        return cur.fetchone()[0]


def arreglar_dato_malo(con, id_linea: int, dia: dt.date) -> None:
    """Alguien corrige la línea esa noche: el precio vuelve a ser positivo y la fila cambia de hora."""
    with con, con.cursor() as cur:
        cur.execute("UPDATE lineas SET precio_unitario = abs(precio_unitario), actualizado_en = %s "
                    "WHERE id_linea = %s", (dt.datetime.combine(dia, dt.time(23, 0)), id_linea))


def borrar_fila(con) -> int:
    """Prueba 6: alguien borra una línea antigua directamente en la base. Devuelve su id."""
    with con, con.cursor() as cur:
        cur.execute("DELETE FROM lineas WHERE id_linea = (SELECT min(id_linea) FROM lineas) RETURNING id_linea")
        return cur.fetchone()[0]
