import tomllib

import pytest

from pipeline import config, costos, formato, reporte

PRECIOS = costos.cargar(config.ESCENARIO)


def test_numeros_en_formato_espanol():
    assert formato.entero(9_554_722) == "9.554.722"
    assert formato.seg(2.57) == "2,6 s"
    assert formato.porcentaje(0.153) == "15 %"
    assert formato.usd(0.0342) == "USD 0,03"
    assert formato.usd(0.004) == "menos de USD 0,01"
    assert formato.usd(1199.99) == "USD 1.200"
    assert formato.usd(0) == "USD 0"
    assert formato.fecha_larga("2026-11-19") == "19 de noviembre de 2026"


def test_resumen_lleva_cada_cifra_con_su_etiqueta_y_cabe_en_la_terminal(medicion):
    lineas = reporte.resumen(medicion, PRECIOS).splitlines()
    assert max(len(l) for l in lineas) <= reporte.ANCHO_RESUMEN
    assert any(l.startswith("  Pasa dlt + DuckDB") and "6 de 7" in l and l.endswith("medido") for l in lineas)
    assert any(l.startswith("  Nube al mes") and l.endswith("estimado") for l in lineas)


def test_una_etiqueta_desconocida_no_se_publica():
    with pytest.raises(ValueError):
        reporte.linea("x", "1", "a ojo")


def test_tablas_y_reporte_dicen_lo_mismo(medicion):
    texto = reporte.markdown(medicion, PRECIOS)
    for tabla in tomllib.loads(reporte.tablas(medicion, PRECIOS))["tabla"]:
        assert len(tabla["etiquetas"]) == len(tabla["columnas"])
        for fila in tabla["filas"]:
            assert len(fila) == len(tabla["columnas"])
            assert all(celda in texto for celda in fila[1:])


def test_el_resumen_y_el_reporte_usan_el_mismo_costo(medicion):
    base = costos.escenarios(medicion, PRECIOS)[0]["nuestra"]["sin_capa"]["total"]
    assert formato.usd(base) in reporte.resumen(medicion, PRECIOS)
    assert formato.usd(base) in reporte.markdown(medicion, PRECIOS)
