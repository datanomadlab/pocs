import tomllib

import pytest

from {{paquete}} import formato, reporte

MEDICION = {"fecha": "2026-11-19", "maquina": {"sistema": "X", "cpu": "Apple M4 Pro", "nucleos": 8},
            "metricas": [{"nombre": "Las 5 consultas", "valor": "0,33 s", "etiqueta": "medido"},
                         {"nombre": "Costo mensual", "valor": "USD 1.200", "etiqueta": "modelo"}]}


def test_numeros_en_formato_espanol():
    assert formato.entero(9_554_722) == "9.554.722"
    assert formato.ms(0.0894) == "89 ms"
    assert formato.usd_corto(1199.99) == "USD 1.200"
    assert formato.usd_corto(0.0033) == "USD 0,003"
    assert formato.fecha_larga("2026-11-19") == "19 de noviembre de 2026"


def test_resumen_lleva_cada_cifra_con_su_etiqueta_y_cabe_en_la_terminal():
    lineas = reporte.resumen(MEDICION).splitlines()
    assert any("0,33 s" in l and l.endswith("medido") for l in lineas)
    assert max(len(l) for l in lineas) <= reporte.ANCHO_RESUMEN


def test_una_etiqueta_desconocida_no_se_publica():
    malo = {**MEDICION, "metricas": [{"nombre": "x", "valor": "1", "etiqueta": "a ojo"}]}
    with pytest.raises(ValueError):
        reporte.resumen(malo)


def test_tablas_y_reporte_dicen_lo_mismo():
    t = tomllib.loads(reporte.tablas(MEDICION))["tabla"][0]
    texto = reporte.markdown(MEDICION)
    assert all(fila[1] in texto for fila in t["filas"])
