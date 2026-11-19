import pytest

from lakehouse import costos

PRECIOS_BQ = {"usd_por_tib": 6.25, "tib_gratis_mes": 1.0, "usd_por_gib_mes": 0.02, "gib_gratis_mes": 10.0}
PRECIOS_BUCKET = {"usd_por_gb_mes": 0.02}
PRECIOS_COMPUTO = {"vcpu": 4, "memoria_gib": 8, "usd_por_vcpu_s": 0.000024, "usd_por_gib_s": 0.0000025,
                   "vcpu_s_gratis_mes": 180_000, "gib_s_gratis_mes": 360_000}


def test_columna_numerica_pesa_8_bytes_por_valor_no_nulo():
    assert costos.bytes_logicos("int64", 1_000) == 8_000
    assert costos.bytes_logicos("timestamp[us]", 10) == 80


def test_string_pesa_2_bytes_mas_su_largo_utf8():
    assert costos.bytes_logicos("string", no_nulos=3, bytes_utf8=3) == 9


def test_tipo_desconocido_falla_en_vez_de_inventar_un_tamano():
    with pytest.raises(ValueError, match="Tipo sin tamaño"):
        costos.bytes_logicos("decimal", 1)


def test_conteo_negativo_es_un_error():
    with pytest.raises(ValueError):
        costos.bytes_logicos("int64", -1)


def test_consulta_chica_paga_el_minimo_por_tabla():
    assert costos.bytes_facturados(1_000, minimo_por_tabla=10_485_760) == 10_485_760
    assert costos.bytes_facturados(50_000_000, minimo_por_tabla=10_485_760) == 50_000_000


def test_un_tib_cuesta_el_precio_por_tib():
    assert costos.costo_bq_consulta(costos.TIB, 6.25) == pytest.approx(6.25)


def test_bigquery_bajo_la_capa_gratuita_cuesta_cero():
    costo = costos.mensual_bigquery(bytes_por_ejecucion=costos.GIB, ejecuciones_dia=1,
                                    bytes_almacenados=costos.GIB, precios=PRECIOS_BQ)
    assert costo.total == 0


def test_bigquery_sin_capa_gratuita_cobra_computo_y_almacenamiento():
    costo = costos.mensual_bigquery(bytes_por_ejecucion=costos.TIB, ejecuciones_dia=1,
                                    bytes_almacenados=100 * costos.GIB, precios=PRECIOS_BQ,
                                    con_capa_gratuita=False)
    assert costo.computo == pytest.approx(30 * 6.25)
    assert costo.almacenamiento == pytest.approx(2.0)
    assert costo.total == pytest.approx(189.5)


def test_bigquery_descuenta_solo_el_primer_tib():
    costo = costos.mensual_bigquery(bytes_por_ejecucion=costos.TIB, ejecuciones_dia=1,
                                    bytes_almacenados=0, precios=PRECIOS_BQ)
    assert costo.computo == pytest.approx(29 * 6.25)


def test_lakehouse_cobra_por_segundo_de_contenedor_y_por_gb_de_bucket():
    costo = costos.mensual_lakehouse(segundos_por_ejecucion=100, ejecuciones_dia=10,
                                     bytes_almacenados=50 * costos.GB, precios_bucket=PRECIOS_BUCKET,
                                     precios_computo=PRECIOS_COMPUTO, con_capa_gratuita=False)
    segundos = 100 * 10 * 30
    assert costo.computo == pytest.approx(segundos * 4 * 0.000024 + segundos * 8 * 0.0000025)
    assert costo.almacenamiento == pytest.approx(1.0)


def test_lakehouse_bajo_la_capa_gratuita_solo_paga_el_bucket():
    costo = costos.mensual_lakehouse(segundos_por_ejecucion=1, ejecuciones_dia=24,
                                     bytes_almacenados=costos.GB, precios_bucket=PRECIOS_BUCKET,
                                     precios_computo=PRECIOS_COMPUTO)
    assert costo.computo == 0
    assert costo.almacenamiento == pytest.approx(0.02)


def test_ahorro_es_none_cuando_no_hay_costo_base():
    assert costos.ahorro_pct(0, 5) is None


def test_ahorro_puede_ser_negativo_si_el_lakehouse_sale_mas_caro():
    assert costos.ahorro_pct(10, 15) == pytest.approx(-50)
    assert costos.ahorro_pct(100, 25) == pytest.approx(75)
