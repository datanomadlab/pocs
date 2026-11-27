import tomllib

from lakehouse import config, reporte

LOCAL = {"fecha": "2026-11-19", "meses": ["2024-01"], "filas": 1000, "hilos": 4, "memoria_gib": 8,
         "maquina": {"sistema": "X", "cpu": "Apple M4 Pro", "nucleos": 8},
         "versiones": {"duckdb": "2.0.0", "pyiceberg": "0.12.0"},
         "crudos_bytes": 10**6, "bodega_bytes": 10**6, "bq_bytes_logicos_total": 10**7,
         "consultas": [{"nombre": "q1", "descripcion": "Consulta uno", "filas_resultado": 1,
                        "frio_s": 0.0894, "mediana_s": 0.05, "bq_bytes_estimados": 152_900_000},
                       {"nombre": "q2", "descripcion": "Consulta dos", "filas_resultado": 1,
                        "frio_s": 0.2, "mediana_s": 0.1, "bq_bytes_estimados": 47_400_000}]}
SIM = {"sqlglot": "30", "tolerancia": 0.01,
       "consultas": [{"nombre": "q1", "mismo_resultado": True, "diferencia_max": 0.0},
                     {"nombre": "q2", "mismo_resultado": True, "diferencia_max": 0.004}]}


def _tablas(sim=SIM):
    return {t["id"]: t for t in tomllib.loads(reporte.tablas(LOCAL, config.cargar_escenario(), sim))["tabla"]}


def test_tabla_de_consultas_redondea_y_suma_el_total():
    t = _tablas()["consultas"]
    assert t["filas"][0] == ["Consulta uno", "89 ms", "153 MB", "igual"]
    assert t["filas"][1][3] == "igual (±0,4 %)"
    assert t["total"] == ["Total", "0,29 s", "200 MB", "2 de 2 iguales"]
    assert t["etiquetas"] == ["", "medido", "estimado", "simulado"]


def test_sin_simulacion_la_tabla_no_lleva_esa_columna():
    t = _tablas(sim=None)["consultas"]
    assert len(t["columnas"]) == 3 and all(len(f) == 3 for f in t["filas"])


def test_tabla_de_escenarios_es_modelo_y_lleva_dolares_redondeados():
    t = _tablas()["escenarios"]
    assert t["etiquetas"] == ["", "modelo", "modelo"]
    assert len(t["filas"]) == len(config.cargar_escenario()["escenario"])
    assert all(v.startswith("USD ") for fila in t["filas"] for v in fila[1:])


def test_dolares_en_formato_espanol():
    assert reporte.usd_corto(0) == "USD 0"
    assert reporte.usd_corto(0.003286) == "USD 0,003"
    assert reporte.usd_corto(10.82) == "USD 11"
    assert reporte.usd_corto(12057.95) == "USD 12.058"


def test_fecha_en_palabras():
    assert reporte.fecha_larga("2026-11-19") == "19 de noviembre de 2026"


def _resumen(sim=SIM):
    return reporte.resumen(LOCAL, config.cargar_escenario(), sim).splitlines()


def test_resumen_usa_las_mismas_cifras_que_las_imagenes():
    t = _tablas()
    texto = "\n".join(_resumen())
    assert t["consultas"]["total"][1] in texto and t["consultas"]["total"][2] in texto
    for fila in t["escenarios"]["filas"]:
        assert any(fila[0] in linea and fila[1] in linea and fila[2] in linea for linea in _resumen())


def test_resumen_marca_cada_cifra_con_su_etiqueta():
    lineas = _resumen()
    assert any("0,29 s" in linea and linea.endswith("medido") for linea in lineas)
    assert any("200 MB" in linea and linea.endswith("estimado") for linea in lineas)
    assert any("2 de 2 iguales" in linea and linea.endswith("simulado") for linea in lineas)
    assert any("Costo mensual" in linea and "modelo" in linea for linea in lineas)


def test_resumen_sin_simulacion_no_inventa_esa_linea():
    assert not any("simulado" in linea for linea in _resumen(sim=None))


def test_resumen_cabe_en_una_terminal_angosta():
    assert max(len(linea) for linea in _resumen()) <= reporte.ANCHO_RESUMEN
