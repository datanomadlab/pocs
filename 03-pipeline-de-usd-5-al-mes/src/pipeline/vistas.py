"""Las vistas de DuckDB sobre lo que cargó dlt. Las usa el job y también quien revisa el destino."""
from __future__ import annotations

from pathlib import Path

import duckdb

SQL = Path(__file__).resolve().parents[2] / "sql"
LLAVES = {"clientes": "id_cliente", "productos": "codigo", "facturas": "id_factura", "lineas": "id_linea"}


def conectar(memoria_mb: int = 256, temporal: str = "/tmp/duckdb") -> duckdb.DuckDBPyConnection:
    """Un hilo y poca memoria: el job corre con 1 vCPU y 512 MB, y su disco temporal también es memoria."""
    con = duckdb.connect()
    con.execute(f"SET threads = 1; SET memory_limit = '{memoria_mb}MB'; SET temp_directory = '{temporal}'")
    return con


def crear(con: duckdb.DuckDBPyConnection, crudo: str) -> None:
    plantilla = (SQL / "vigente.sql").read_text(encoding="utf-8")
    for tabla, llave in LLAVES.items():
        con.execute(plantilla.format(tabla=tabla, llave=llave, crudo=crudo))


def consultas(carpeta: str) -> dict[str, str]:
    """Los .sql de sql/<carpeta>, por nombre y sin el punto y coma final."""
    return {p.stem: p.read_text(encoding="utf-8").strip().rstrip(";")
            for p in sorted((SQL / carpeta).glob("*.sql"))}
