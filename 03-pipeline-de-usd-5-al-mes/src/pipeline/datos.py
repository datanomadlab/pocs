"""Descarga Online Retail II (UCI, CC BY 4.0) y lo deja limpio en data/ventas.parquet. No se versiona."""
from __future__ import annotations

import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

import duckdb

from . import config

# El Excel trae dos hojas que se pisan nueve días (1 al 9 de diciembre de 2010), facturas "A" que son
# ajustes contables y movimientos de bodega con cantidad negativa. Cada filtro cuenta lo que saca.
FILTROS = {
    "repetidas entre las dos hojas": "hoja = 1 AND fecha >= TIMESTAMP '2010-12-01'",
    "ajustes contables (facturas A)": "id_factura LIKE 'A%'",
    "movimientos de bodega (cantidad negativa sin anulación)": "cantidad < 0 AND id_factura NOT LIKE 'C%'",
}


def descargar(url: str = config.URL_DATOS, destino: Path = config.ZIP) -> Path:
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(".parcial")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp, parcial.open("wb") as f:
            shutil.copyfileobj(resp, f)
    except OSError as e:
        parcial.unlink(missing_ok=True)
        raise RuntimeError(f"No pude descargar {url}: {e}") from e
    parcial.rename(destino)
    return destino


def descomprimir(archivo: Path = config.ZIP, destino: Path = config.EXCEL) -> Path:
    if not destino.exists():
        with zipfile.ZipFile(archivo) as z:
            z.extract(destino.name, destino.parent)
    return destino


def _leer_hojas(con: duckdb.DuckDBPyConnection, excel: Path, hojas: tuple[str, ...]) -> None:
    """Todo como texto: la columna de factura mezcla números y códigos como C489449, y adivinando falla.

    Así las fechas llegan como número de serie de Excel (días desde el 30-12-1899).
    """
    con.execute("INSTALL excel")
    con.execute("LOAD excel")
    partes = [f"SELECT {i + 1} AS hoja, * FROM read_xlsx('{excel}', sheet = '{hoja}', all_varchar = true)"
              for i, hoja in enumerate(hojas)]
    con.execute(f"""
        CREATE OR REPLACE TABLE crudo AS
        SELECT hoja,
               Invoice AS id_factura,
               StockCode AS codigo,
               trim(Description) AS descripcion,
               CAST(Quantity AS INTEGER) AS cantidad,
               TIMESTAMP '1899-12-30' + to_seconds(round(CAST(InvoiceDate AS DOUBLE) * 86400)) AS fecha,
               round(CAST(Price AS DOUBLE), 4) AS precio_unitario,
               CAST(CAST("Customer ID" AS DOUBLE) AS INTEGER) AS id_cliente,
               Country AS pais
        FROM ({' UNION ALL '.join(partes)})""")


def _comprobar_repetidas(con: duckdb.DuckDBPyConnection) -> None:
    """Las líneas de la hoja 1 que se descartan por repetidas tienen que estar, idénticas, en la hoja 2."""
    sobran = con.execute(f"""
        SELECT count(*) FROM (
          SELECT * EXCLUDE (hoja) FROM crudo WHERE {FILTROS["repetidas entre las dos hojas"]}
          EXCEPT ALL
          SELECT * EXCLUDE (hoja) FROM crudo WHERE hoja = 2)""").fetchall()[0][0]
    if sobran:
        raise ValueError(f"{sobran} líneas de la hoja 1 posteriores al 1 de diciembre de 2010 no están en la hoja 2: "
                         "no se pueden descartar como repetidas")


def limpiar(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Aplica los filtros en orden sobre la tabla `crudo` y deja `ventas`. Devuelve lo que sacó cada uno."""
    _comprobar_repetidas(con)
    descartes = {"filas del archivo": con.execute("SELECT count(*) FROM crudo").fetchall()[0][0]}
    for motivo, condicion in FILTROS.items():
        descartes[motivo] = con.execute(f"SELECT count(*) FROM crudo WHERE {condicion}").fetchall()[0][0]
        con.execute(f"DELETE FROM crudo WHERE {condicion}")
    con.execute("""
        CREATE OR REPLACE TABLE ventas AS
        SELECT row_number() OVER (ORDER BY fecha, id_factura, codigo, cantidad, precio_unitario) AS id_linea,
               id_factura, codigo, descripcion, cantidad, fecha, precio_unitario, id_cliente, pais
        FROM crudo""")
    descartes["filas que quedan"] = con.execute("SELECT count(*) FROM ventas").fetchall()[0][0]
    return descartes


def preparar(excel: Path = config.EXCEL, destino: Path = config.VENTAS,
             hojas: tuple[str, ...] = config.HOJAS) -> dict[str, int]:
    """Del Excel a un Parquet limpio. Si ya existe, no lo rehace."""
    registro = destino.with_name("descartes.json")
    if destino.exists() and registro.exists():
        return json.loads(registro.read_text(encoding="utf-8"))
    con = duckdb.connect()
    _leer_hojas(con, excel, hojas)
    descartes = limpiar(con)
    con.execute(f"COPY ventas TO '{destino}' (FORMAT parquet)")
    registro.write_text(json.dumps(descartes, indent=2, ensure_ascii=False), encoding="utf-8")
    return descartes
