from stream import reporte, reporte_concurrencia as rc

MAQUINA = {"sistema": "Darwin 25", "cpu": "Apple M4 Pro", "nucleos": 14, "docker": "29.0",
           "docker_nucleos": 12, "docker_memoria_gb": 7.7}


def _fase(tasa: int, espectadores: int, segundos: int, entregadas: float = 1.0, aguanta: bool = True, **extra) -> dict:
    confirmados = tasa * segundos
    return {"tasa": tasa, "segundos": segundos, "confirmados": confirmados, "unicos": confirmados, "perdidos": 0,
            "atraso_generador_ms": 0, "duplicados": 0, "copias": 0, "reconexiones": 0, "latencia_ms": {"p50": 2.0, "p99": 12.0},
            "entregas_esperadas": confirmados * espectadores,
            "entregas": round(confirmados * espectadores * entregadas), "aguanta": aguanta, **extra}


def _resultado(ruta: str, escenario: str = "50.000 emisores, 2.000 pantallas", tasa: int = 1_667,
               espectadores: int = 20, rampa: tuple = (True, True, True), nominal_ok: bool = True,
               entregadas_corte: float = 1.0, congelada: float | None = 0.0) -> dict:
    return {"escenario": escenario, "ruta": ruta, "tasa": tasa, "emisores": 50_000, "cuentas": 100,
            "espectadores": espectadores, "pantallas": 100 * espectadores, "entregas_s": tasa * espectadores,
            "nominal": _fase(tasa, espectadores, 30, 1.0 if nominal_ok else 0.9, nominal_ok,
                             nucleos={"transporte": 0.3, "entrega": 0.412}),
            "rampa": [_fase(tasa * f, espectadores, 12, aguanta=ok) for f, ok in zip((2, 4, 8), rampa)],
            "corte": _fase(tasa, espectadores, 40, entregadas_corte,
                           corte={"congelada_s": congelada, "al_dia_s": 1.0, "atraso_max_s": 1.0})}


def _datos(*resultados: dict) -> dict:
    return {"fecha": "2026-11-25", "maquina": MAQUINA, "bytes": 1_000, "p99_max_ms": 1_000,
            "decorador": [{"destinos": d, "reglas": r, "eventos_s": 160_271.4 / d, "bytes_entrada": 1_001,
                           "bytes_salida": 576} for d in (1, 3) for r in (0, 100)],
            "resultados": list(resultados)}


def test_sin_medicion_de_concurrencia_no_hay_tablas():
    assert rc.armar_tablas(None) == []


def test_el_techo_es_la_mayor_carga_que_aguanto():
    assert rc.techo(_resultado("nats-go")) == ">= 266.720/s"           # pasó toda la rampa
    assert rc.techo(_resultado("nats-go", rampa=(True, False))) == "66.680/s"
    assert rc.techo(_resultado("nats-go", rampa=(False,))) == "33.340/s"  # solo la carga del escenario
    assert rc.techo(_resultado("nats-go", nominal_ok=False)) == "entrega el 90 %"
    assert rc.techo({"escenario": "x", "ruta": "nats-go", "error": "falló"}) == "no terminó"
    assert rc.techo(None) == "sin medir"


def test_una_rampa_que_no_termino_no_es_un_techo():
    cortada = {**_resultado("nats-go", rampa=(True,)), "error": "las pantallas no lograron suscribirse"}
    assert rc.techo(cortada) == "no terminó"
    # Si el error llegó después de un escalón que falló, el techo sí se encontró.
    assert rc.techo({**_resultado("nats-go", rampa=(True, False)), "error": "falló el corte"}) == "66.680/s"


def test_si_el_generador_no_alcanza_la_tasa_no_se_culpa_a_la_pieza():
    lento = _resultado("nats-go", rampa=(True, False))
    lento["rampa"][1]["atraso_generador_ms"] = 4_000
    assert rc.techo(lento) == ">= 66.680/s"
    sin_carga = _resultado("nats-go", nominal_ok=False)
    sin_carga["nominal"]["atraso_generador_ms"] = 4_000
    assert rc.techo(sin_carga) == "sin carga"


def test_el_motivo_de_no_aguantar_no_se_inventa():
    pierde = _resultado("nats-go", nominal_ok=False)
    pierde["nominal"] |= {"entregas": pierde["nominal"]["entregas_esperadas"], "perdidos": 12}
    assert rc.techo(pierde) == "pierde 12"
    tarde = _resultado("nats-go", nominal_ok=False)
    tarde["nominal"] |= {"entregas": tarde["nominal"]["entregas_esperadas"], "latencia_ms": {"p50": 900.0, "p99": 3_200.0}}
    assert rc.techo(tarde) == "p99 de 3,2 s"


def test_los_nucleos_solo_se_informan_si_la_carga_se_aguanta():
    assert rc.nucleos(_resultado("nats-go")) == "0,41"
    assert rc.nucleos(_resultado("nats-go", nominal_ok=False)) == "no aguanta"


def test_el_corte_muestra_la_parte_que_no_llego():
    assert rc.corte(_resultado("nats-go")) == "0"
    assert rc.corte(_resultado("nats-go", entregadas_corte=0.985)) == "1,5 %"
    assert rc.corte(_resultado("nats-go", entregadas_corte=0.9999)) == "menos de 0,1 %"
    assert rc.corte(_resultado("nats-go", nominal_ok=False, entregadas_corte=0.5)) == "ya no aguantaba"


def test_tablas_con_una_columna_por_ruta_y_una_fila_por_escenario():
    datos = _datos(_resultado("nats-centrifugo", congelada=0.2), _resultado("nats-go", rampa=(True, False)),
                   _resultado("nats-go", escenario="10.000 emisores, 1.000 pantallas", tasa=333, espectadores=10))
    tablas = {t["id"]: t for t in rc.armar_tablas(datos)}

    assert list(tablas) == ["techo", "nucleos-concurrencia", "corte-concurrencia", "enriquecer"]
    techo = tablas["techo"]
    # Todas las rutas van sobre NATS: el encabezado lleva solo la pieza de entrega.
    assert techo["columnas"] == ["Escenario", "Entregas/s", "Centrifugo", "Go"]
    assert techo["filas"] == [
        ["2.000 pantallas, 20 por cuenta", "33.340", ">= 266.720/s", "66.680/s"],
        ["1.000 pantallas, 10 por cuenta", "3.330", "sin medir", ">= 26.640/s"]]
    assert "Emisores de cada escenario, en orden: 50.000, 50.000." in techo["nota"]
    assert "25 de noviembre de 2026 en Apple M4 Pro" in techo["nota"] and "NATS JetStream" in techo["nota"]
    assert "cada 30 s" in techo["nota"] and "1.000 bytes" in techo["nota"]
    assert "se congeló 0,2 s" in tablas["corte-concurrencia"]["nota"]
    assert tablas["enriquecer"]["filas"] == [["1", "160.300", "160.300"], ["3", "53.400", "53.400"]]
    for t in tablas.values():
        assert all(len(f) == len(t["columnas"]) == len(t["etiquetas"]) for f in t["filas"])


def test_el_reporte_incluye_la_concurrencia_solo_si_se_midio():
    base = {"fecha": "2026-11-21", "maquina": MAQUINA, "versiones": {}, "rutas": [],
            "parametros": {"tasa": 10_000, "emisores": 100_000, "cuentas": 1_000, "pantallas": 100, "bytes": 300}}
    assert "varias pantallas por cuenta" not in reporte.markdown(base)
    con = reporte.markdown({**base, "concurrencia": _datos(_resultado("nats-go"))})
    assert "Varias pantallas por cuenta: hasta dónde aguanta" in con
    assert "que se midió aparte el 25 de noviembre de 2026" in con
    dibujadas = reporte.tablas({**base, "concurrencia": _datos(_resultado("nats-go"))})
    assert 'id = "techo"' in dibujadas
    # La fuente de las imágenes no trae «≥»: en todas las salidas va «>=».
    assert '">= 266.720/s"' in dibujadas and "≥" not in dibujadas and "≥" not in con
