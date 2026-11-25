"""Matriz de concurrencia: miles de pantallas, varias mirando la misma cuenta.

En `make demo` cada cuenta la mira una sola pantalla, así que cada evento se entrega una vez. Acá
cada cuenta la miran varias: lo que carga a la pieza de entrega ya no son los eventos que entran
sino las entregas que salen (eventos x espectadores). Por cada escenario y ruta corre carga
nominal, rampa (2, 4 y 8 veces) y un corte con todas las pantallas reconectando a la vez.

No toca data/medicion.json ni docs/: escribe data/concurrencia.json y muestra cada fase en la terminal.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, replace

from . import analisis, config, medir
from .contenedores import Compose, ErrorDocker, bajar_todo
from .formato import entero

SALIDA = config.DATOS / "concurrencia.json"
COMPOSE = "compose.yaml:compose.concurrencia.yaml"   # le da más núcleos a la sonda
RUTAS = ("nats-centrifugo", "nats-centrifugo-redis", "nats-go")
FACTORES_RAMPA = (2, 4, 8)
SEGUNDOS_NOMINAL, SEGUNDOS_ESCALON, SEGUNDOS_CORTE = 30, 12, 40
ENTREGA_COMPLETA = 0.999   # fracción de las entregas esperadas para decir que una fase aguantó


@dataclass(frozen=True)
class Escenario:
    """Cada pantalla mira una cuenta: pantallas = cuentas x espectadores."""
    nombre: str
    tasa: int
    emisores: int
    cuentas: int
    espectadores: int

    @property
    def pantallas(self) -> int:
        return self.cuentas * self.espectadores

    @property
    def entregas_s(self) -> int:
        return self.tasa * self.espectadores


# Un emisor emite cada 30 s: 10.000 emisores son 333 eventos por segundo.
ESCENARIOS = (
    Escenario("10.000 emisores, 1.000 pantallas", 333, 10_000, 100, 10),
    Escenario("50.000 emisores, 2.000 pantallas", 1_667, 50_000, 100, 20),
    Escenario("50.000 emisores, 5.000 pantallas", 1_667, 50_000, 100, 50),
    Escenario("200.000 emisores, 5.000 pantallas", 6_667, 200_000, 200, 25),
)
# Con RAPIDO=1: una sola combinación chica, para comprobar que todo levanta.
ESCENARIO_RAPIDO = Escenario("prueba", 200, 2_000, 20, 5)


def parametros_de(base: config.Parametros, e: Escenario) -> config.Parametros:
    return replace(base, tasa=e.tasa, emisores=e.emisores, cuentas=e.cuentas, pantallas=e.pantallas,
                   espectadores=e.espectadores, rapido=False)


def con_entregas(fase: dict, espectadores: int) -> dict:
    """Agrega a una fase cuántas entregas debían llegar y cuántas llegaron, sumando todos los espectadores."""
    fase["entregas_esperadas"] = fase["confirmados"] * espectadores
    fase["entregas"] = fase["unicos"] + fase["copias"]
    return fase


def aguanta(fase: dict, tasa: int, segundos: int, p99_max_ms: int) -> bool:
    """Como analisis.aguanta, y además todos los espectadores recibieron (casi) todo."""
    return (analisis.aguanta(fase, tasa, segundos, p99_max_ms)
            and fase["entregas"] >= ENTREGA_COMPLETA * fase["entregas_esperadas"])


def linea(fase: dict) -> str:
    nucleos = fase.get("nucleos", {})
    return (f"{entero(fase['tasa'])}/s  entregas {entero(fase['entregas'])} de {entero(fase['entregas_esperadas'])} "
            f"({100 * fase['entregas'] / max(1, fase['entregas_esperadas']):.1f} %)  "
            f"p50 {fase['latencia_ms']['p50']:.1f} ms  p99 {fase['latencia_ms']['p99']:.1f} ms  "
            f"núcleos de la entrega {nucleos.get('entrega', '-')}  reconexiones {fase['reconexiones']}")


def medir_escenario(ruta: config.Ruta, e: Escenario, base: config.Parametros, avisar=print) -> dict:
    """Levanta la ruta, corre nominal, rampa y corte, y la baja. Un fallo queda escrito en el resultado."""
    p = parametros_de(base, e)
    compose = Compose(ruta, p.sesion_ms)
    servicio = config.ENTREGAS[ruta.entrega][0]
    resultado: dict = {"escenario": e.nombre, "ruta": ruta.id, "tasa": e.tasa, "emisores": e.emisores,
                       "cuentas": e.cuentas, "espectadores": e.espectadores, "pantallas": e.pantallas,
                       "entregas_s": e.entregas_s, "bytes": p.bytes}
    inicio = time.monotonic()
    bajar_todo()
    try:
        compose.correr("up", "-d", ruta.transporte)
        medir._preparar(compose)
        compose.correr("up", "-d", servicio)
        medir._estabilizar(compose, p, "calentar", e.tasa)
        resultado["nominal"] = con_entregas(medir.corrida(compose, p, "nominal", e.tasa, SEGUNDOS_NOMINAL), e.espectadores)
        avisar(f"      nominal   {linea(resultado['nominal'])}")
        resultado["rampa"] = []
        for factor in FACTORES_RAMPA:
            tasa = e.tasa * factor
            fase = con_entregas(medir.corrida(compose, p, f"rampa{factor}", tasa, SEGUNDOS_ESCALON), e.espectadores)
            fase["aguanta"] = aguanta(fase, tasa, SEGUNDOS_ESCALON, p.p99_max_ms)
            resultado["rampa"].append(fase)
            avisar(f"      rampa x{factor}  {linea(fase)}  {'aguanta' if fase['aguanta'] else 'NO aguanta'}")
            if not fase["aguanta"]:
                break
        medir._estabilizar(compose, p, "asentar", e.tasa)
        resultado["corte"] = con_entregas(
            medir.corrida(compose, p, "corte", e.tasa, SEGUNDOS_CORTE, cortar_a_los=config.CORTE_A_LOS), e.espectadores)
        avisar(f"      corte     {linea(resultado['corte'])}")
    except (medir.RutaFallida, ErrorDocker) as error:
        resultado["error"] = str(error)
        avisar(f"      no terminó: {error}")
    finally:
        bajar_todo()
    resultado["minutos"] = round((time.monotonic() - inicio) / 60, 1)
    return resultado


def correr() -> None:
    os.environ.setdefault("COMPOSE_FILE", COMPOSE)
    base = config.parametros()
    todas = {r.id: r for r in config.rutas(todas=True)}
    pedidas = [r.strip() for r in os.environ.get("RUTAS", "").split(",") if r.strip()] or list(RUTAS)
    desconocidas = [r for r in pedidas if r not in todas]
    if desconocidas:
        raise ValueError(f"rutas desconocidas: {', '.join(desconocidas)}")
    escenarios = (ESCENARIO_RAPIDO,) if base.rapido else ESCENARIOS
    resultados: list[dict] = []
    for e in escenarios:
        for rid in pedidas:
            print(f"\n{e.nombre} · {todas[rid].corto} · {e.espectadores} pantallas por cuenta, "
                  f"{entero(e.entregas_s)} entregas/s", flush=True)
            resultados.append(medir_escenario(todas[rid], e, base, lambda texto: print(texto, flush=True)))
            if not base.rapido:
                config.DATOS.mkdir(exist_ok=True)
                SALIDA.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    if not base.rapido:
        print(f"\nResultados en {SALIDA.relative_to(config.RAIZ)}")
