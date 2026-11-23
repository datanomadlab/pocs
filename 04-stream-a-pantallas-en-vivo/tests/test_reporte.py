import tomllib

import pytest

from stream import config, costos, formato, reporte

E = tomllib.loads(config.ESCENARIO.read_text(encoding="utf-8"))


def _fase(**cambios) -> dict:
    base = {"tasa": 10_000, "segundos": 30, "confirmados": 300_000, "fallidos_al_enviar": 0, "atraso_generador_ms": 0,
            "unicos": 300_000, "perdidos": 0, "duplicados": 0, "desordenados": 0, "sin_recuperar": 0,
            "reconexiones": 0, "latencia_ms": {"p50": 11.0, "p95": 15.0, "p99": 19.4, "max": 48.0},
            "nucleos": {"transporte": 0.157, "entrega": 0.217}, "memoria_mb": {"transporte": 470, "entrega": 59}}
    return {**base, **cambios}


def _ruta(id_: str, transporte: str, entrega: str, etiqueta: str = "medido", **extra) -> dict:
    nombres = {"go": "consumidor en Go", "node": "consumidor en Node", "centrifugo": "Centrifugo"}
    cortos = {"redpanda": "Redpanda", "nats": "NATS", "sqs": "SQS FIFO"}
    ruta = {"id": id_, "nombre": f"{cortos[transporte]} + {nombres[entrega]}",
            "corto": f"{cortos[transporte]} + {entrega.capitalize()}", "transporte": transporte,
            "entrega": entrega, "etiqueta": etiqueta, "tasa": 10_000,
            "lineas_codigo": 0 if entrega == "centrifugo" else 135,
            "lineas_configuracion": 28 if entrega == "centrifugo" else 0, "nominal": _fase(),
            "cortes": [_fase(perdidos=151_100, duplicados=420,
                             corte={"congelada_s": 45.6, "al_dia_s": 52.0, "atraso_max_s": 46.2}),
                       _fase(perdidos=90, duplicados=24_000, desordenados=7,
                             corte={"congelada_s": 44.0, "al_dia_s": 50.0, "atraso_max_s": 45.0})]}
    if etiqueta == "medido":
        ruta["rampa"] = {"aguanta_hasta": 80_000, "llego_al_tope": True, "tope": 80_000, "escalones": []}
    return {**ruta, **extra}


RUTAS = [_ruta("redpanda-go", "redpanda", "go"), _ruta("redpanda-centrifugo", "redpanda", "centrifugo"),
         _ruta("nats-go", "nats", "go"),
         _ruta("sqs-centrifugo", "sqs", "centrifugo", "simulado",
               cortes=[_fase(corte={"congelada_s": None, "al_dia_s": None, "atraso_max_s": 0.0})])]
MEDIDOS = {"tasa": 10_000, "entrega": {"go": 0.217, "centrifugo": 0.4}, "transporte": {"redpanda": 0.157, "nats": 0.3}}
MEDICION = {"fecha": "2026-11-21", "rapido": False,
            "maquina": {"sistema": "X", "cpu": "Apple M4 Pro", "nucleos": 14, "docker": "29.9.3", "docker_nucleos": 12,
                        "docker_memoria_gb": 7.7},
            "parametros": {"tasa": 10_000, "tasa_simulada": 1_000, "emisores": 100_000, "cuentas": 1_000,
                           "pantallas": 100, "bytes": 300, "p99_max_ms": 1_000, "cortes": 2, "sesion_ms": ""},
            "versiones": {"Redpanda": "26.3.1", "NATS": "2.15.3"}, "rutas": RUTAS,
            "costos": costos.modelo(E, MEDIDOS)}


def test_numeros_en_formato_espanol():
    assert formato.entero(9_554_722) == "9.554.722"
    assert formato.usd_corto(1199.99) == "USD 1.200"
    assert formato.fecha_larga("2026-11-19") == "19 de noviembre de 2026"
    assert formato.latencia(3.52) == "3,5 ms"
    assert formato.latencia(19.4) == "19 ms"
    assert formato.latencia(45_600) == "46 s"
    assert formato.latencia(2_558) == "2,6 s"
    assert formato.segundos(0.3) == "0,3 s"
    assert formato.por_segundo(80_000) == "80.000/s"


def test_celdas():
    ruta = RUTAS[0]
    assert reporte.p99(ruta) == "19 ms"
    assert reporte.aguanta(ruta) == "≥ 80.000/s"
    assert reporte.nucleos(ruta) == "0,16 + 0,22"
    assert reporte.codigo(ruta) == "135 líneas"
    assert reporte.codigo(RUTAS[1]) == "28 de config."
    assert reporte.congelada(ruta) == "46 s"
    assert reporte.atraso_maximo(ruta) == "46 s"
    assert reporte.no_llegaron(ruta) == "151.100"
    assert reporte.repetidos(ruta) == "24.000"            # el peor de cada columna, no un solo corte
    assert reporte.fuera_de_orden(ruta) == "7"
    sin_hueco = {**ruta, "cortes": [_fase(corte={"congelada_s": 0.0, "al_dia_s": 0.0, "atraso_max_s": 0.1})]}
    assert reporte.congelada(sin_hueco) == "< 0,4 s"
    assert reporte.congelada(RUTAS[3]) == "no volvió"
    assert reporte.orden(ruta) == "sin fallas"
    assert reporte.orden({**ruta, "nominal": _fase(perdidos=3, desordenados=12)}) == "3 perdidos, 12 fuera de orden"


def test_una_ruta_sin_medir_no_lleva_un_numero_de_relleno():
    sin_medir = {k: v for k, v in RUTAS[0].items() if k not in ("nominal", "cortes", "rampa")}
    assert reporte.p99(sin_medir) == reporte.aguanta(sin_medir) == reporte.congelada(sin_medir) == "sin medir"


def test_horas_de_equilibrio_con_signo():
    assert reporte.horas(2.04) == "+2,0 h"
    assert reporte.horas(-0.52) == "−0,5 h"
    assert reporte.horas(0.01) == "igual"


def test_resumen_lleva_cada_ruta_con_su_etiqueta_y_cabe_en_la_terminal():
    lineas = reporte.resumen(MEDICION).splitlines()
    assert any("Redpanda + Go" in l and "19 ms" in l and l.endswith("medido") for l in lineas)
    assert any("SQS FIFO + Centrifugo" in l and l.endswith("simulado") for l in lineas)
    assert any(l.startswith("Costo al mes") and l.endswith("modelo") for l in lineas)
    assert max(len(l) for l in lineas) <= reporte.ANCHO_RESUMEN


def test_una_etiqueta_desconocida_no_se_publica():
    malo = {**MEDICION, "rutas": [{**RUTAS[0], "etiqueta": "a ojo"}]}
    with pytest.raises(ValueError):
        reporte.resumen(malo)


def test_medido_y_simulado_no_comparten_tabla():
    tablas = {t["id"]: t for t in reporte.armar_tablas(MEDICION)}
    assert [f[0] for f in tablas["simuladas"]["filas"]] == ["SQS FIFO + Centrifugo"]
    assert all("SQS" not in f[0] for f in tablas["pantalla"]["filas"] + tablas["corte"]["filas"])
    assert set(tablas["simuladas"]["etiquetas"]) == {"", "simulado", "medido"}
    assert "todas entregaron todo" in tablas["simuladas"]["nota"]


def test_tablas_y_reporte_dicen_lo_mismo():
    texto = reporte.markdown(MEDICION)
    for t in tomllib.loads(reporte.tablas(MEDICION))["tabla"]:
        assert len(t["columnas"]) == len(t["etiquetas"])
        for fila in t["filas"]:
            assert len(fila) == len(t["columnas"])
            assert all(celda in texto for celda in fila)


def test_el_equilibrio_usa_el_escenario_de_la_tasa_medida():
    tabla = next(t for t in reporte.armar_tablas(MEDICION) if t["id"] == "equilibrio")
    assert "10.000 eventos por segundo" in tabla["nota"]
    assert all(f[0] != "Kinesis + Flink" for f in tabla["filas"])


def test_una_ruta_que_fallo_queda_escrita():
    fallida = {k: v for k, v in RUTAS[0].items() if k not in ("nominal", "cortes", "rampa")} | {"error": "no levantó"}
    medicion = {**MEDICION, "rutas": [*RUTAS, fallida]}
    assert "no levantó" in reporte.markdown(medicion)
    assert any("no terminó" in l for l in reporte.resumen(medicion).splitlines())


def test_corrida_rapida_se_avisa():
    assert "no se publican" in reporte.markdown({**MEDICION, "rapido": True})


def test_costos_locales_solo_llevan_las_tablas_de_costos():
    texto = reporte.costos_markdown(MEDICION)
    assert "Costo mensual de cada camino" in texto and "horas caídas" in texto
    assert "p99" not in texto
