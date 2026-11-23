"""Las pruebas que se le hacen a cada ruta: carga nominal, corte de la pieza de entrega y rampa.

Cada prueba es una "corrida": la sonda se suscribe, el generador emite a una tasa fija y al final
se compara lo que el transporte confirmó con lo que las pantallas recibieron.
"""
from __future__ import annotations

import json
import threading
import time

from . import analisis, config
from .contenedores import Compose, ErrorDocker, bajar_todo, leer_uso, matar_y_levantar, nucleos_usados
from .formato import entero

INTENTOS_PREPARAR = 30
INTENTOS_ESTABILIZAR = 12
TASA_ESTABILIZAR = 1_000   # eventos por segundo de las corridas cortas, o la tasa de la ruta si es menor


class RutaFallida(RuntimeError):
    pass


def _ultima_linea_json(texto: str, quien: str) -> dict:
    lineas = [l for l in texto.splitlines() if l.startswith("{")]
    if not lineas:
        raise RutaFallida(f"{quien} no entregó resultados")
    return json.loads(lineas[-1])


def corrida(compose: Compose, p: config.Parametros, nombre: str, tasa: int, segundos: int,
            cortar_a_los: int | None = None) -> dict:
    """Una corrida completa. Con cortar_a_los, mata la pieza de entrega a esos segundos de carga."""
    ruta = compose.ruta
    servicio, protocolo, url = config.ENTREGAS[ruta.entrega]
    margen = config.MARGEN_SONDA if cortar_a_los is None else config.MARGEN_CORTE
    sonda = compose.abrir(*compose.herramienta(
        "sonda", "-protocolo", protocolo, "-destino", url, "-corrida", nombre,
        "-pantallas", str(p.pantallas), "-cuentas", str(p.cuentas), "-duracion", f"{segundos + margen}s"))
    try:
        if sonda.stdout.readline().strip() != "LISTO":
            raise RutaFallida(f"las pantallas no lograron suscribirse: {sonda.stderr.read().strip()[-300:]}")
        listo = time.monotonic()
        ids = {"transporte": compose.id(ruta.transporte), "entrega": compose.id(servicio)}
        uso: dict[str, dict] = {"antes": {}, "despues": {}}
        momento_corte: list[float] = []

        def leer(cuando: str) -> None:
            for pieza, identificador in ids.items():
                uso[cuando][pieza] = leer_uso(identificador)

        def cortar() -> None:
            momento_corte.append(time.monotonic())
            matar_y_levantar(ids["entrega"])

        # El uso de CPU se lee dentro de la carga, lejos del arranque y del cierre del generador.
        relojes = [threading.Timer(3, leer, ["antes"]), threading.Timer(segundos - 1, leer, ["despues"])]
        if cortar_a_los is not None:
            relojes = [threading.Timer(cortar_a_los, cortar)]
        for r in relojes:
            r.start()
        salida = compose.correr(*compose.herramienta(
            "generador", "-transporte", ruta.transporte, "-destino", config.DESTINOS[ruta.transporte],
            "-corrida", nombre, "-tasa", str(tasa), "-duracion", f"{segundos}s", "-emisores", str(p.emisores),
            "-cuentas", str(p.cuentas), "-bytes", str(p.bytes),
            *(["-sin-comprimir"] if ruta.sin_comprimir else [])), timeout=segundos + 180)
        fin_carga = time.monotonic()
        for r in relojes:
            r.join()
        if cortar_a_los is not None and not momento_corte:
            raise RutaFallida("no se pudo matar la pieza de entrega")
        generado = _ultima_linea_json(salida, "el generador")
        medido, errores = sonda.communicate(timeout=margen + 120)
        if sonda.returncode != 0:
            raise RutaFallida(f"la sonda terminó con error: {errores.strip()[-300:]}")
        visto = _ultima_linea_json(medido, "la sonda")
    finally:
        if sonda.poll() is None:
            sonda.kill()

    fase = {
        "tasa": tasa, "segundos": segundos, "confirmados": generado["confirmados"],
        "fallidos_al_enviar": generado["fallidos"], "atraso_generador_ms": generado["atraso_max_ms"],
        "unicos": visto["unicos"], "perdidos": analisis.perdidos(generado["confirmados"], visto["unicos"]),
        "duplicados": visto["duplicados"], "desordenados": visto["desordenados"],
        "sin_recuperar": visto["sin_recuperar"], "reconexiones": visto["reconexiones"],
        "latencia_ms": visto["latencia_ms"],
    }
    if uso["antes"] and uso["despues"]:
        fase["nucleos"] = {k: round(nucleos_usados(uso["antes"][k], uso["despues"][k]), 3) for k in ids}
        fase["memoria_mb"] = {k: round(uso["despues"][k].memoria_bytes / 1e6) for k in ids}
    if momento_corte:
        fase["corte"] = analisis.corte(visto["serie"], (momento_corte[0] - listo) * 1000,
                                       (fin_carga - listo) * 1000, visto["tramo_ms"], p.p99_max_ms)
    return fase


def _preparar(compose: Compose) -> None:
    """Crea el tópico, stream o cola. Reintenta porque el transporte tarda unos segundos en aceptar conexiones."""
    ruta = compose.ruta
    ultimo = ""
    for _ in range(INTENTOS_PREPARAR):
        try:
            compose.correr(*compose.herramienta("generador", "-transporte", ruta.transporte,
                                                "-destino", config.DESTINOS[ruta.transporte], "-preparar",
                                                "-particiones", str(config.PARTICIONES.get(ruta.transporte, 1))))
            return
        except ErrorDocker as e:
            ultimo = str(e)
            time.sleep(2)
    raise RutaFallida(f"el transporte {ruta.transporte} no quedó listo: {ultimo}")


def _estabilizar(compose: Compose, p: config.Parametros, prefijo: str, tasa: int) -> None:
    """Corridas cortas hasta que una llega completa y a tiempo: ahí la ruta está leyendo al día.

    Se usa al partir (el consumidor tarda en unirse) y después del corte (queda atraso por drenar).
    """
    ultimo = "sin intentos"
    for i in range(INTENTOS_ESTABILIZAR):
        try:
            fase = corrida(compose, p, f"{prefijo}{i}", min(TASA_ESTABILIZAR, tasa), 4)
            if fase["unicos"] > 0 and fase["perdidos"] == 0 and fase["latencia_ms"]["p99"] <= p.p99_max_ms:
                return
            ultimo = f"llegaron {fase['unicos']} de {fase['confirmados']} eventos, p99 de {fase['latencia_ms']['p99']:.0f} ms"
        except (RutaFallida, ErrorDocker) as e:
            ultimo = str(e)
        time.sleep(2)
    raise RutaFallida(f"la ruta no entrega todo a tiempo ni con carga baja ({ultimo})")


def medir_ruta(ruta: config.Ruta, p: config.Parametros, avisar=print) -> dict:
    """Levanta la ruta, corre las tres pruebas y la baja. Un fallo queda escrito en el resultado."""
    compose = Compose(ruta, p.sesion_ms)
    servicio = config.ENTREGAS[ruta.entrega][0]
    tasa = ruta.tasa or (p.tasa_simulada if ruta.simulada else p.tasa)
    resultado: dict = {"id": ruta.id, "nombre": ruta.nombre, "corto": ruta.corto, "transporte": ruta.transporte,
                       "entrega": ruta.entrega, "etiqueta": ruta.etiqueta, "tasa": tasa,
                       "lineas_codigo": analisis.lineas_de(config.RAIZ, config.CODIGO[ruta.entrega], ruta.transporte),
                       "lineas_configuracion": analisis.lineas_de(
                           config.RAIZ, config.CONFIGURACION.get(ruta.entrega, []), ruta.transporte)}
    bajar_todo()
    try:
        compose.correr("up", "-d", ruta.transporte)
        _preparar(compose)
        compose.correr("up", "-d", servicio)
        _estabilizar(compose, p, "calentar", tasa)
        avisar(f"      carga nominal: {entero(tasa)} eventos/s por {p.segundos_nominal} s")
        resultado["nominal"] = corrida(compose, p, "nominal", tasa, p.segundos_nominal)
        resultado["cortes"] = []
        for i in range(p.cortes):
            avisar(f"      corte {i + 1} de {p.cortes}: se mata la pieza de entrega a los {config.CORTE_A_LOS} s")
            if i:
                _estabilizar(compose, p, f"entrecortes{i}", tasa)
            resultado["cortes"].append(corrida(compose, p, f"corte{i}", tasa, p.segundos_corte,
                                               cortar_a_los=config.CORTE_A_LOS))
        resultado["corte"] = analisis.peor_corte(resultado["cortes"])
        if not ruta.simulada:
            _estabilizar(compose, p, "asentar", tasa)
            resultado["rampa"] = _rampa(compose, p, resultado["nominal"], avisar)
    except (RutaFallida, ErrorDocker) as e:
        resultado["error"] = str(e)
        avisar(f"      no terminó: {e}")
    finally:
        bajar_todo()
    return resultado


def _rampa(compose: Compose, p: config.Parametros, nominal: dict, avisar) -> dict:
    """Sube la tasa por escalones hasta que la ruta deja de cumplir. Devuelve la mayor tasa que aguantó."""
    aguanto = p.tasa if analisis.aguanta(nominal, p.tasa, nominal["segundos"], p.p99_max_ms) else 0
    escalones = []
    if aguanto:
        for factor in config.FACTORES_RAMPA:
            tasa = p.tasa * factor
            avisar(f"      rampa: {entero(tasa)} eventos/s")
            fase = corrida(compose, p, f"rampa{factor}", tasa, p.segundos_escalon)
            fase["aguanta"] = analisis.aguanta(fase, tasa, p.segundos_escalon, p.p99_max_ms)
            escalones.append(fase)
            if not fase["aguanta"]:
                break
            aguanto = tasa
    tope = p.tasa * config.FACTORES_RAMPA[-1]
    return {"aguanta_hasta": aguanto, "llego_al_tope": aguanto == tope, "tope": tope, "escalones": escalones}
