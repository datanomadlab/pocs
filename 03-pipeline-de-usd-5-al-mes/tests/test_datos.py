"""La limpieza y la vista de lo vigente, con muestras chicas armadas en la prueba. No descarga nada."""
import datetime as dt

import duckdb
import pytest

from pipeline import datos, origen, vistas


def _crudo(con, filas):
    con.execute("""CREATE TABLE crudo (hoja INTEGER, id_factura VARCHAR, codigo VARCHAR, descripcion VARCHAR,
                   cantidad INTEGER, fecha TIMESTAMP, precio_unitario DOUBLE, id_cliente INTEGER, pais VARCHAR)""")
    con.executemany("INSERT INTO crudo VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", filas)


def test_limpiar_saca_y_cuenta_cada_descarte():
    con = duckdb.connect()
    t = dt.datetime
    _crudo(con, [
        (1, "489434", "85048", "LUZ", 12, t(2009, 12, 1, 7, 45), 6.95, 13085, "United Kingdom"),
        (1, "536365", "85123A", "VELA", 6, t(2010, 12, 1, 8, 26), 2.55, 17850, "United Kingdom"),   # repetida
        (2, "536365", "85123A", "VELA", 6, t(2010, 12, 1, 8, 26), 2.55, 17850, "United Kingdom"),
        (2, "A563185", "B", "Adjust bad debt", 1, t(2011, 8, 12, 14, 50), 11062.06, None, "United Kingdom"),
        (2, "536589", "21777", "?", -10, t(2010, 12, 1, 16, 50), 0.0, None, "United Kingdom"),     # bodega
        (2, "C536379", "D", "Discount", -1, t(2010, 12, 1, 9, 41), 27.5, 14527, "United Kingdom"),  # anulación
    ])
    descartes = datos.limpiar(con)
    assert descartes == {"filas del archivo": 6, "repetidas entre las dos hojas": 1,
                         "ajustes contables (facturas A)": 1,
                         "movimientos de bodega (cantidad negativa sin anulación)": 1, "filas que quedan": 3}
    ids = con.execute("SELECT id_linea, id_factura FROM ventas ORDER BY id_linea").fetchall()
    assert ids == [(1, "489434"), (2, "536365"), (3, "C536379")]


def test_no_descarta_como_repetida_una_linea_que_la_hoja_2_no_tiene():
    con = duckdb.connect()
    _crudo(con, [(1, "536365", "85123A", "VELA", 6, dt.datetime(2010, 12, 1, 8, 26), 2.55, 17850, "United Kingdom")])
    with pytest.raises(ValueError):
        datos.limpiar(con)


def _parquet(carpeta, tabla, carga, sql):
    (carpeta / tabla).mkdir(parents=True, exist_ok=True)
    duckdb.connect().execute(f"COPY ({sql}) TO '{carpeta / tabla / f'{carga}.abcdef0123.parquet'}' (FORMAT parquet)")


def test_la_vista_deja_la_ultima_version_de_cada_fila_aunque_una_carga_se_repita(tmp_path):
    crudo = tmp_path / "crudo"
    _parquet(crudo, "productos", "1795743298.832166",
             "SELECT * FROM (VALUES ('A', 'vela', 2.5, TIMESTAMP '2010-12-01 08:00'),"
             " ('B', 'luz', 6.9, TIMESTAMP '2010-12-01 09:00')) t(codigo, descripcion, precio, actualizado_en)")
    # Una carga cortada y repetida: la misma fila de B dos veces. A cambia de precio y trae una columna nueva.
    _parquet(crudo, "productos", "1795743312.482830",
             "SELECT * FROM (VALUES ('A', 'vela', 2.9, TIMESTAMP '2010-12-02 10:00', 'x'),"
             " ('B', 'luz', 6.9, TIMESTAMP '2010-12-01 09:00', NULL))"
             " t(codigo, descripcion, precio, actualizado_en, segmento)")
    con = duckdb.connect()
    plantilla = (vistas.SQL / "vigente.sql").read_text(encoding="utf-8")
    con.execute(plantilla.format(tabla="productos", llave="codigo", crudo=crudo))
    filas = con.execute("SELECT codigo, precio, segmento FROM productos ORDER BY codigo").fetchall()
    assert [(c, float(p), s) for c, p, s in filas] == [("A", 2.9, "x"), ("B", 6.9, None)]


def test_las_consultas_salen_de_sus_archivos_sin_punto_y_coma():
    pruebas = vistas.consultas("pruebas")
    assert set(pruebas) == {"precios_negativos", "cantidades_imposibles", "lineas_sin_factura"}
    assert not any(sql.endswith(";") for sql in pruebas.values())
    assert len(vistas.consultas("reportes")) == 5


def test_facturas_solo_se_insertan_y_productos_se_actualizan_si_cambian():
    assert origen._sql_carga("facturas").endswith("ON CONFLICT (id_factura) DO NOTHING")
    productos = origen._sql_carga("productos")
    assert "DO UPDATE SET descripcion = EXCLUDED.descripcion, precio = EXCLUDED.precio" in productos
    assert "WHERE productos.descripcion IS DISTINCT FROM EXCLUDED.descripcion OR" in productos
