"""Lo que hace el job después de cargar, sobre una carpeta armada en la prueba: sin Docker ni Postgres."""
import duckdb

from pipeline import destino, job_dlt

TABLAS = {
    "clientes": "SELECT 1 AS id_cliente, 'United Kingdom' AS pais, TIMESTAMP '2010-12-01 08:00' AS actualizado_en",
    "productos": "SELECT 'A' AS codigo, 'vela' AS descripcion, 2.5 AS precio, TIMESTAMP '2010-12-01 08:00' AS actualizado_en",
    "facturas": "SELECT '536365' AS id_factura, 1 AS id_cliente, TIMESTAMP '2010-12-01 08:00' AS fecha, "
                "false AS anulada, TIMESTAMP '2010-12-01 08:00' AS actualizado_en",
}


def _linea(precio: float, hora: str) -> str:
    return (f"SELECT 1::BIGINT AS id_linea, '536365' AS id_factura, 'A' AS codigo, 6 AS cantidad, "
            f"{precio} AS precio_unitario, TIMESTAMP '2010-12-01 {hora}' AS actualizado_en")


def _escribir(bucket, tabla, carga, sql):
    carpeta = bucket / "dlt" / "crudo" / tabla
    carpeta.mkdir(parents=True, exist_ok=True)
    duckdb.connect().execute(f"COPY ({sql}) TO '{carpeta / f'{carga}.abcdef0123.parquet'}' (FORMAT parquet)")


def test_un_precio_negativo_detiene_la_publicacion_y_deja_la_de_ayer(tmp_path):
    for tabla, sql in TABLAS.items():
        _escribir(tmp_path, tabla, "1795743298.832166", sql)
    _escribir(tmp_path, "lineas", "1795743298.832166", _linea(2.5, "08:00"))
    dlt = str(tmp_path / "dlt")

    assert job_dlt.publicar(dlt, "ayer") == {}
    assert destino.corrida_publicada(tmp_path) == "ayer"
    assert (tmp_path / "dlt" / "reportes" / "ayer" / "ventas_por_dia.parquet").exists()

    _escribir(tmp_path, "lineas", "1795743312.482830", _linea(-2.5, "09:00"))
    assert job_dlt.publicar(dlt, "hoy") == {"precios_negativos": 1}
    assert destino.corrida_publicada(tmp_path) == "ayer"
    assert not (tmp_path / "dlt" / "reportes" / "hoy").exists()

    _escribir(tmp_path, "lineas", "1795743314.452142", _linea(2.5, "23:00"))
    assert job_dlt.publicar(dlt, "corregido") == {}
    assert destino.corrida_publicada(tmp_path) == "corregido"
    assert destino.filas("dlt", tmp_path) == {"clientes": 1, "productos": 1, "facturas": 1, "lineas": 1}
    assert destino.huella("dlt", tmp_path)["lineas"][0] == 1
