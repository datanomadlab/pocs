import duckdb
import pytest

from lakehouse import simulacion


def test_dia_de_la_semana_conserva_la_numeracion_de_bigquery():
    # BigQuery: domingo = 1. DuckDB: domingo = 0. 2024-01-07 fue domingo.
    sql = simulacion.traducir("SELECT EXTRACT(DAYOFWEEK FROM DATETIME '2024-01-07 10:00:00') AS d")
    assert duckdb.connect().execute(sql).fetchone()[0] == 1


def test_traduce_funciones_de_bigquery_a_duckdb():
    sql = simulacion.traducir(
        "SELECT DATETIME_DIFF(DATETIME '2024-01-01 00:10:00', DATETIME '2024-01-01 00:00:00', SECOND) AS s")
    assert duckdb.connect().execute(sql).fetchone()[0] == 600


def test_sql_que_bigquery_no_acepta_es_un_error():
    with pytest.raises(ValueError, match="no es SQL válido de BigQuery"):
        simulacion.traducir("SELECT FROM WHERE")


def test_columnas_salen_del_sql_y_no_de_los_alias():
    sql = "SELECT tipo_pago, AVG(propina / tarifa) AS p FROM `p.d.viajes` WHERE tarifa > 0 GROUP BY 1 ORDER BY p"
    assert simulacion.columnas_de(sql) == {"tipo_pago", "propina", "tarifa"}


def test_detecta_el_filtro_que_permite_podar_particiones():
    con_filtro = "SELECT COUNT(*) FROM t WHERE inicio >= DATETIME '2024-01-01' AND inicio < DATETIME '2024-02-01'"
    sin_filtro = "SELECT COUNT(*) FROM t WHERE tarifa > 0"
    assert simulacion.poda_particiones(con_filtro, "inicio")
    assert not simulacion.poda_particiones(sin_filtro, "inicio")


def test_resultados_iguales_dan_diferencia_cero():
    assert simulacion.comparar([(1, 2.5, "a")], [(1, 2.5, "a")]) == (True, 0.0)


def test_numeros_dentro_de_la_tolerancia_cuentan_como_iguales():
    iguales, dif = simulacion.comparar([(0, 11.22)], [(0, 11.25)], tolerancia=0.01)
    assert iguales and dif == pytest.approx(0.03 / 11.25)


def test_numeros_fuera_de_tolerancia_o_textos_distintos_no_son_iguales():
    assert not simulacion.comparar([(0, 10.0)], [(0, 12.0)], tolerancia=0.01)[0]
    assert not simulacion.comparar([("a",)], [("b",)])[0]


def test_distinta_cantidad_de_filas_no_es_igual():
    assert simulacion.comparar([(1,)], [(1,), (2,)]) == (False, None)
